"""
LangGraph agent graph wiring.
Quick mode: intent → clarify → memory → retrieve → report → save  (2 LLM calls)
Deep mode:  intent → clarify → memory → retrieve → combined_analyze → synthesize → report → save  (6 LLM calls)
"""

import logging
from langgraph.graph import StateGraph, END

from agent.state import AgentState
from agent.nodes.intent_classifier import intent_classifier
from agent.nodes.clarification_check import clarification_check
from agent.nodes.memory_loader import memory_loader
from agent.nodes.data_retriever import data_retriever
from agent.nodes.global_stats_aggregator import global_stats_aggregator
from agent.nodes.combined_analyzer import combined_analyzer
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
    if state.get("needs_clarification", False):
        return END
    if state.get("error"):
        return "fallback"
    if state.get("mode", "quick") == "deep":
        return "combined_analyzer"
    return "report_generator"


def route_after_node(next_node: str):
    def _route(state: AgentState) -> str:
        if state.get("error"):
            return "fallback"
        return next_node
    return _route


def build_graph():
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("intent_classifier",   intent_classifier)
    graph.add_node("clarification_check", clarification_check)
    graph.add_node("memory_loader",       memory_loader)
    graph.add_node("data_retriever",      data_retriever)
    graph.add_node("global_stats_aggregator", global_stats_aggregator)
    graph.add_node("combined_analyzer",   combined_analyzer)   # replaces 3 separate nodes
    graph.add_node("business_synthesizer", business_synthesizer)
    graph.add_node("report_generator",    report_generator)
    graph.add_node("memory_saver",        memory_saver)
    graph.add_node("fallback",            fallback_node)

    # Entry
    graph.set_entry_point("intent_classifier")

    # intent → clarify
    graph.add_conditional_edges("intent_classifier", route_after_node("clarification_check"), {
        "clarification_check": "clarification_check",
        "fallback": "fallback",
    })

    # clarify → memory or end
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

    # retriever → global_stats_aggregator
    graph.add_conditional_edges("data_retriever", route_after_node("global_stats_aggregator"), {
        "global_stats_aggregator": "global_stats_aggregator",
        "fallback": "fallback",
    })

    # global_stats → quick: report | deep: combined_analyzer
    graph.add_conditional_edges("global_stats_aggregator", route_after_retrieval, {
        "combined_analyzer": "combined_analyzer",
        "report_generator": "report_generator",
        "fallback": "fallback",
        END: END,
    })

    # Deep mode: combined_analyzer → synthesizer → report
    graph.add_conditional_edges("combined_analyzer", route_after_node("business_synthesizer"), {
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
