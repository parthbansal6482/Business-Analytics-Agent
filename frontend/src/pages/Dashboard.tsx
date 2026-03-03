import { useState } from "react"
import { useSessionStore } from "../store/useSessionStore"
import { useResearch } from "../hooks/useResearch"
import type { ResearchMode } from "../lib/types"
import ModeToggle from "../components/dashboard/ModeToggle"
import QueryInput from "../components/dashboard/QueryInput"
import ExampleChips from "../components/dashboard/ExampleChips"
import AgentProgress from "../components/dashboard/AgentProgress"
import ClarificationModal from "../components/dashboard/ClarificationModal"
import FollowUpChips from "../components/dashboard/FollowUpChips"
import ReportCard from "../components/report/ReportCard"

export default function Dashboard() {
    const [mode, setMode] = useState<ResearchMode>("quick")
    const [queryText, setQueryText] = useState("")

    const { isLoading, report, needsClarification, query } = useSessionStore()
    const { runQuery, runWithClarification } = useResearch()

    const handleSubmit = () => {
        if (!queryText.trim() || isLoading) return
        runQuery(queryText, mode)
    }

    const handleExampleSelect = (text: string) => {
        setQueryText(text)
    }

    const handleFollowUp = (text: string) => {
        setQueryText(text)
        runQuery(text, mode)
    }

    const handleClarificationSubmit = (answer: string) => {
        runWithClarification(query, mode, answer)
    }

    return (
        <div className="flex-1 w-full max-w-4xl mx-auto px-6 py-10">
            <div className="space-y-6">
                {/* Mode Toggle */}
                <div className="flex justify-center">
                    <ModeToggle mode={mode} onChange={setMode} />
                </div>

                {/* Query Input */}
                <QueryInput
                    value={queryText}
                    onChange={setQueryText}
                    onSubmit={handleSubmit}
                    disabled={isLoading}
                />

                {/* Example chips — show when idle */}
                {!isLoading && !report && (
                    <ExampleChips onSelect={handleExampleSelect} />
                )}

                {/* Progress — show when loading */}
                {isLoading && <AgentProgress />}

                {/* Clarification modal */}
                {needsClarification && !isLoading && (
                    <ClarificationModal onSubmit={handleClarificationSubmit} />
                )}

                {/* Report */}
                {report && !isLoading && (
                    <div className="space-y-6">
                        <ReportCard report={report} />
                        <FollowUpChips
                            suggestions={report.follow_up_suggestions}
                            onSelect={handleFollowUp}
                        />
                    </div>
                )}

                {/* Idle empty state when no report and not loading */}
                {!isLoading && !report && !needsClarification && queryText === "" && (
                    <div className="flex flex-col items-center justify-center py-16 text-center">
                        <div className="w-16 h-16 bg-[#b7860b]/10 rounded-2xl flex items-center justify-center mb-5">
                            <span className="material-symbols-outlined text-[#b7860b]" style={{ fontSize: 32 }}>psychology_alt</span>
                        </div>
                        <h3 className="text-xl font-serif text-[#181611] mb-2">Ask anything about your business</h3>
                        <p className="text-sm text-[#8a7e60] max-w-md">
                            Ask about product performance, customer sentiment, competitor pricing, or what actions to take next.
                        </p>
                    </div>
                )}
            </div>
        </div>
    )
}
