import { useSessionStore } from "../store/useSessionStore"
import { startResearch, getReport } from "../lib/api"
import type { ResearchMode, ProgressEvent } from "../lib/types"

export function useResearch() {
    const store = useSessionStore()

    const runQuery = async (query: string, mode: ResearchMode) => {
        store.reset()
        store.setLoading(true)
        store.setQuery(query)
        store.setMode(mode)

        let session_id: string

        try {
            const res = await startResearch(query, mode)
            session_id = res.session_id
        } catch {
            // Backend unavailable: simulate with mock data
            simulateMockResearch(query, store)
            return
        }

        const es = new EventSource(
            `http://127.0.0.1:8000/api/research/stream/${session_id}`
        )

        es.onmessage = (e) => {
            let event: ProgressEvent
            try {
                event = JSON.parse(e.data)
            } catch {
                return
            }

            store.updateProgress(event)

            if (event.step === "__done__") {
                getReport(session_id).then((session) => {
                    if (session.report) {
                        store.setReport(session.report)
                        store.addTokens(session.report.tokens_used || 0)
                        store.addCost(session.report.cost_usd || 0)
                    }
                    store.setLoading(false)
                    es.close()
                }).catch(() => {
                    store.setLoading(false)
                    es.close()
                })
            }

            if ((event.status as string) === "clarification") {
                store.setClarification(event.label)
                es.close()
            }
        }

        es.onerror = () => {
            store.setLoading(false)
            es.close()
        }
    }

    const runWithClarification = async (originalQuery: string, mode: ResearchMode, clarification: string) => {
        const combinedQuery = clarification
            ? `${originalQuery} [Clarification: ${clarification}]`
            : originalQuery
        await runQuery(combinedQuery, mode)
    }

    return { runQuery, runWithClarification }
}

// Mock simulation for when backend is unavailable
function simulateMockResearch(query: string, store: ReturnType<typeof useSessionStore.getState>) {
    const stepNames: Array<import("../lib/types").AgentStep> = [
        "intent", "clarify", "memory", "retrieve",
        "sentiment", "pricing", "competitor", "synthesize", "report"
    ]

    let i = 0
    const interval = setInterval(() => {
        if (i > 0) {
            store.updateProgress({ step: stepNames[i - 1], status: "done", label: "" })
        }
        if (i < stepNames.length) {
            store.updateProgress({ step: stepNames[i], status: "running", label: "" })
            i++
        } else {
            clearInterval(interval)
            store.updateProgress({ step: "report", status: "done", label: "" })

            const mockReport = generateMockReport(query)
            store.setReport(mockReport)
            store.addTokens(mockReport.tokens_used)
        }
    }, 600)
}

function generateMockReport(query: string): import("../lib/types").ResearchReport {
    return {
        executive_summary: `Based on analysis of your store data for "${query}", we identified strong market fit but found key friction points in pricing competitiveness and shipping experience. Customer sentiment is trending positive (65%) due to recent quality improvements, though 22% of customers mention pricing as a barrier compared to key competitors.`,
        mode: "quick",
        key_metrics: {
            revenue_impact: "-22% Sales",
            rating_change: "+0.3 Stars",
            price_gap_pct: 16.7,
        },
        sentiment_breakdown: {
            positive_pct: 65,
            neutral_pct: 20,
            negative_pct: 15,
            top_complaints: [
                "Shipping delays exceeding 5 business days",
                "Inconsistent sizing — products run small",
                "Packaging damaged on arrival",
            ],
            feature_requests: [
                "More color options requested by 85% of reviewers",
                "Faster returns and exchange process",
                "Eco-friendly packaging options",
            ],
        },
        pricing_analysis: {
            your_price: 125.00,
            competitor_avg: 108.50,
            gap_pct: 15.2,
            recommendation: "Consider a 10-15% promotional discount during peak season to close the price gap with key competitors while maintaining margin targets. Bundle with complementary products to justify the premium pricing.",
        },
        competitive_gaps: [
            "Competitors offer 2-day Prime shipping — you are Behind",
            "Color variety: competitors have 12+ options vs your 4 — Missing",
            "Loyalty program: 3 of 5 competitors have one — Missing",
            "Mobile app for order tracking — Behind",
        ],
        root_cause: "The primary performance issue stems from a logistics bottleneck affecting last-mile delivery in 3 key regions, accounting for 78% of negative shipping reviews. Secondary drivers include price anchoring against premium competitors causing cart abandonment at checkout. The product quality itself is strong — customers who receive orders on time rate the product 4.6/5 stars on average.",
        recommended_actions: [
            { action: "Switch to regional carrier for Northeast shipping zone", priority: "High", expected_impact: "+18% review score" },
            { action: "Run 15% discount campaign for 2 weeks", priority: "Medium", expected_impact: "+22% conversion" },
            { action: "Update size guide with 'Runs Small' badge", priority: "Medium", expected_impact: "-30% returns" },
            { action: "Launch loyalty rewards program", priority: "Low", expected_impact: "+12% LTV" },
        ],
        confidence_score: 87,
        data_completeness: "Moderate",
        cost_usd: 0,
        tokens_used: 2847,
        follow_up_suggestions: [
            "Which SKUs have the worst shipping complaints?",
            "What's the ROI of switching carriers?",
            "Show me competitor pricing trends over 90 days",
        ],
        duration_seconds: 28,
    }
}
