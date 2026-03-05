import { useSessionStore } from "../store/useSessionStore"
import { startResearch, getReport } from "../lib/api"
import { API_URL } from "../config"
import type { ResearchMode, ProgressEvent } from "../lib/types"

export function useResearch() {
    const store = useSessionStore()

    const runQuery = async (query: string, mode: ResearchMode) => {
        store.reset()
        store.setLoading(true)
        store.setQuery(query)
        store.setMode(mode)
        store.setError(null)

        let session_id: string | null = null

        try {
            const res = await startResearch(query, mode)
            if (res.needs_clarification) {
                store.setLoading(false)
                store.setClarification(res.clarification_question || "Please upload data before running analysis.")
                return
            }
            session_id = res.session_id
            if (!session_id) {
                store.setLoading(false)
                store.setError("Failed to initialize research session. Please check your data sources.")
                return
            }
        } catch (err: any) {
            store.setLoading(false)
            store.setError(err?.response?.data?.detail || "Could not connect to the research agent. Make sure the backend is running.")
            return
        }

        const es = new EventSource(`${API_URL}/api/research/stream/${session_id}`)

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
                    store.setError("Failed to load the generated report from backend.")
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
            es.close()
            // The agent may have finished even though the stream dropped.
            // Try fetching the report before showing an error.
            if (session_id) {
                getReport(session_id).then((session) => {
                    if (session.report) {
                        store.setReport(session.report)
                        store.addTokens(session.report.tokens_used || 0)
                        store.addCost(session.report.cost_usd || 0)
                    }
                    store.setLoading(false)
                }).catch(() => {
                    store.setError("Lost connection to the research agent. The report may still be processing — try refreshing in a moment.")
                    store.setLoading(false)
                })
            } else {
                store.setError("Lost connection to the research agent. Please try again.")
                store.setLoading(false)
            }
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
