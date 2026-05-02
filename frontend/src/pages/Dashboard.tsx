import { useState, useEffect } from "react"
import { useSessionStore } from "../store/useSessionStore"
import { useUserStore } from "../store/useUserStore"
import { useResearch } from "../hooks/useResearch"
import type { ResearchMode } from "../lib/types"
import ModeToggle from "../components/dashboard/ModeToggle"
import QueryInput from "../components/dashboard/QueryInput"
import ExampleChips from "../components/dashboard/ExampleChips"
import AgentProgress from "../components/dashboard/AgentProgress"
import ClarificationModal from "../components/dashboard/ClarificationModal"
import FollowUpChips from "../components/dashboard/FollowUpChips"
import ReportCard from "../components/report/ReportCard"
import ChatPanel from "../components/chat/ChatPanel"
import { useNavigate } from "react-router-dom"

export default function Dashboard() {
    const navigate = useNavigate()
    const [mode, setMode] = useState<ResearchMode>("quick")
    const [queryText, setQueryText] = useState("")

    const { isLoading, report, needsClarification, query, error, sessionId } = useSessionStore()
    const { runQuery, runWithClarification } = useResearch()
    const { userId, syncUploadStatus } = useUserStore()

    useEffect(() => {
        console.log("System Build Date:", __BUILD_DATE__)
        syncUploadStatus()
    }, [syncUploadStatus])

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

    const handleReportUpdate = (newReport: Record<string, unknown>) => {
        useSessionStore.getState().setReport(newReport as any)
    }

    return (
        <div className="flex-1 w-full px-6 pt-10 pb-32">
            {/* Header / Back action */}
            <div className="max-w-4xl mx-auto flex items-center justify-between mb-8">
                <button
                    onClick={() => navigate("/connect")}
                    className="flex items-center gap-2 text-[#8a7e60] hover:text-[#b7860b] transition-colors group"
                >
                    <span className="material-symbols-outlined transition-transform group-hover:-translate-x-1" style={{ fontSize: 20 }}>arrow_back_ios</span>
                    <span className="text-sm font-medium">Back to Data Sources</span>
                </button>
            </div>

            <div className="max-w-4xl mx-auto space-y-6">
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

                {/* Real backend/agent error */}
                {error && !isLoading && (
                    <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                        {error}
                    </div>
                )}

                {/* Clarification modal */}
                {needsClarification && !isLoading && (
                    <ClarificationModal onSubmit={handleClarificationSubmit} />
                )}
            </div>

            {/* Report + Chat split layout */}
            {report && !isLoading && (
                <div className="flex gap-0 mt-6" style={{ maxWidth: "100%" }}>
                    {/* Left: Report */}
                    <div className="flex-1 overflow-y-auto max-w-4xl mx-auto">
                        <div className="space-y-6">
                            <ReportCard report={report} />
                            <FollowUpChips
                                suggestions={report.follow_up_suggestions}
                                onSelect={handleFollowUp}
                            />
                        </div>
                    </div>

                    {/* Right: Chat Panel */}
                    <div className="w-96 border-l border-[#e5e2db] sticky top-0 h-screen overflow-hidden flex-col hidden lg:flex">
                        <ChatPanel
                            sessionId={sessionId || ""}
                            userId={userId}
                            initialReport={report as unknown as Record<string, unknown>}
                            onReportUpdate={handleReportUpdate}
                        />
                    </div>
                </div>
            )}

            {/* Idle empty state when no report and not loading */}
            {!isLoading && !report && !needsClarification && !error && queryText === "" && (
                <div className="max-w-4xl mx-auto flex flex-col items-center justify-center py-16 text-center">
                    <div className="w-16 h-16 bg-[#b7860b]/10 rounded-2xl flex items-center justify-center mb-5">
                        <span className="material-symbols-outlined text-[#b7860b]" style={{ fontSize: 32 }}>psychology_alt</span>
                    </div>
                    <h3 className="text-xl font-serif text-[#181611] mb-2">Ask anything about your business</h3>
                    <p className="text-sm text-[#8a7e60] max-w-md">
                        Ask about product performance, customer sentiment, competitor pricing, or what actions to take next.
                    </p>
                </div>
            )}

            {/* System Footer Info */}
            <div className="max-w-4xl mx-auto mt-12 pt-6 border-t border-[#e5e2db] flex items-center justify-between text-[10px] text-[#8a7e60] uppercase tracking-widest font-medium">
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                    <span>System Status: Online</span>
                </div>
                <div>
                    Last Rebuild: {new Date(__BUILD_DATE__).toLocaleString('en-US', {
                        day: '2-digit',
                        month: 'short',
                        hour: '2-digit',
                        minute: '2-digit',
                        hour12: true
                    })}
                </div>
            </div>
        </div>
    )
}
