import { useSessionStore } from "../../store/useSessionStore"
import type { AgentStep } from "../../lib/types"
import LoadingSpinner from "../shared/LoadingSpinner"

const STEP_LABELS: Record<AgentStep, string> = {
    intent: "Understanding your question",
    clarify: "Checking for clarifications",
    memory: "Loading your preferences",
    retrieve: "Searching your data",
    sentiment: "Analyzing reviews",
    pricing: "Analyzing pricing",
    competitor: "Analyzing competitors",
    synthesize: "Synthesizing insights",
    report: "Generating report",
    __done__: "Done",
}

const STEP_ORDER: AgentStep[] = [
    "intent", "clarify", "memory", "retrieve",
    "sentiment", "pricing", "competitor", "synthesize", "report",
]

export default function AgentProgress() {
    const { progress, progressLabels, query } = useSessionStore()

    return (
        <div className="bg-white border border-[#e5e2db] rounded-xl p-8 animate-fade-in">
            {/* Header */}
            <div className="flex items-center gap-3 mb-8">
                <div className="w-3 h-3 rounded-full bg-[#b7860b] animate-pulse" />
                <h3 className="text-lg font-semibold text-[#181611] font-serif">Analyzing your query…</h3>
            </div>

            {query && (
                <div className="mb-6 p-3 bg-[#f5f0e8] rounded-lg border border-[#e5e2db]">
                    <p className="text-sm text-[#8a7e60] italic">"{query}"</p>
                </div>
            )}

            {/* Steps */}
            <div className="space-y-4">
                {STEP_ORDER.map((step) => {
                    const status = progress[step]
                    return (
                        <div key={step} className="flex items-center gap-4">
                            {/* Status icon */}
                            <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
                                {status === "done" && (
                                    <div className="w-6 h-6 rounded-full bg-[#15803d] flex items-center justify-center">
                                        <span className="material-symbols-outlined text-white" style={{ fontSize: 14 }}>check</span>
                                    </div>
                                )}
                                {status === "running" && <LoadingSpinner size={22} />}
                                {status === "pending" && (
                                    <div className="w-6 h-6 rounded-full border-2 border-[#e5e2db]" />
                                )}
                                {status === "error" && (
                                    <div className="w-6 h-6 rounded-full bg-[#b91c1c] flex items-center justify-center">
                                        <span className="material-symbols-outlined text-white" style={{ fontSize: 14 }}>close</span>
                                    </div>
                                )}
                            </div>

                            {/* Label */}
                            <span className={`text-sm transition-colors ${status === "done"
                                    ? "text-[#15803d] font-medium"
                                    : status === "running"
                                        ? "text-[#181611] font-semibold"
                                        : status === "error"
                                            ? "text-[#b91c1c]"
                                            : "text-[#8a7e60]"
                                }`}>
                                {progressLabels[step] || STEP_LABELS[step]}
                                {status === "running" && (
                                    <span className="ml-1 animate-pulse">…</span>
                                )}
                            </span>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
