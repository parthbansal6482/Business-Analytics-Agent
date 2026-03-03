"""
LangGraph agent graph wiring.
Quick mode: intent → clarify → memory → retrieve → report → save
Deep mode:  intent → clarify → memory → retrieve → sentiment + pricing + competitor → synthesize → report → save
"""

import logging
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes.intent_classifier import intent_classifier
from agent.nodes.clarification_check import clarification_check
from agent.nodes.memory_loader import memory_loader
from agent.nodes.data_retriever import data_retriever
from agent.nodes.sentiment_analyzer import sentiment_analyzer
from agent.nodes.pricing_analyst import pricing_analyst
from agent.nodes.competitor_analyzer import competitor_analyzer
from agent.nodes.business_synthesizer import business_synthesizer
from agent.nodes.report_generator import report_generator
from agent.nodes.memory_saver import memory_saver
from agent.nodes.fallback_node import fallback_node

logger = logging.getLogger(__name__)


def route_after_clarification(state: AgentState) -> str:
    if state.get("needs_clarification", False):
        return END
    if state.get("error"):
        return "fallback"
    return "memory_loader"


def route_after_retrieval(state: AgentState) -> str:
    if state.get("error"):
        return "fallback"
    if state.get("mode", "quick") == "deep":
        return "sentiment_analyzer"
    return "report_generator"


def route_after_analysis(state: AgentState) -> str:
    if state.get("error"):
        return "fallback"
    return "business_synthesizer"


def route_after_node(next_node: str):
    def _route(state: AgentState) -> str:
        if state.get("error"):
            return "fallback"
        return next_node
    return _route


def build_graph():
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("intent_classifier",    intent_classifier)
    graph.add_node("clarification_check",  clarification_check)
    graph.add_node("memory_loader",        memory_loader)
    graph.add_node("data_retriever",       data_retriever)
    graph.add_node("sentiment_analyzer",   sentiment_analyzer)
    graph.add_node("pricing_analyst",      pricing_analyst)
    graph.add_node("competitor_analyzer",  competitor_analyzer)
    graph.add_node("business_synthesizer", business_synthesizer)
    graph.add_node("report_generator",     report_generator)
    graph.add_node("memory_saver",         memory_saver)
    graph.add_node("fallback",             fallback_node)

    # Entry
    graph.set_entry_point("intent_classifier")

    # intent → clarify
    graph.add_conditional_edges("intent_classifier", route_after_node("clarification_check"), {
        "clarification_check": "clarification_check",
        "fallback": "fallback",
    })

    # clarify → (end if needs clarification) or memory
    graph.add_conditional_edges("clarification_check", route_after_clarification, {
        "memory_loader": "memory_loader",
        "fallback": "fallback",
        END: END,
    })

    # memory → retriever
    graph.add_conditional_edges("memory_loader", route_after_node("data_retriever"), {
        "data_retriever": "data_retriever",
        "fallback": "fallback",
    })

    # retriever → quick mode: report | deep mode: sentiment
    graph.add_conditional_edges("data_retriever", route_after_retrieval, {
        "report_generator": "report_generator",
        "sentiment_analyzer": "sentiment_analyzer",
        "fallback": "fallback",
    })

    # Deep mode analysis chain (sequential for simplicity — LangGraph parallelism needs Send API)
    graph.add_conditional_edges("sentiment_analyzer", route_after_node("pricing_analyst"), {
        "pricing_analyst": "pricing_analyst",
        "fallback": "fallback",
    })
    graph.add_conditional_edges("pricing_analyst", route_after_node("competitor_analyzer"), {
        "competitor_analyzer": "competitor_analyzer",
        "fallback": "fallback",
    })
    graph.add_conditional_edges("competitor_analyzer", route_after_node("business_synthesizer"), {
        "business_synthesizer": "business_synthesizer",
        "fallback": "fallback",
    })
    graph.add_conditional_edges("business_synthesizer", route_after_node("report_generator"), {
        "report_generator": "report_generator",
        "fallback": "fallback",
    })

    # report → memory save → end
    graph.add_conditional_edges("report_generator", route_after_node("memory_saver"), {
        "memory_saver": "memory_saver",
        "fallback": "fallback",
    })
    graph.add_edge("memory_saver", END)
    graph.add_edge("fallback", END)

    return graph.compile()


# Singleton compiled graph
_agent_graph = None


def get_agent_graph():
    global _agent_graph
    if _agent_graph is None:
        _agent_graph = build_graph()
        logger.info("LangGraph agent compiled.")
    return _agent_graph
