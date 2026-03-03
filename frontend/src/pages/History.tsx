import { useState } from "react"
import { useHistory } from "../hooks/useHistory"
import HistoryItem from "../components/history/HistoryItem"
import ReportCard from "../components/report/ReportCard"
import type { ResearchSession } from "../lib/types"
import LoadingSpinner from "../components/shared/LoadingSpinner"

export default function History() {
    const { sessions, isLoading, error } = useHistory()
    const [selectedSession, setSelectedSession] = useState<ResearchSession | null>(null)

    // Recommendation card: find most common query theme
    const showRecommendation = sessions.length >= 2

    return (
        <div className="flex-1 w-full max-w-5xl mx-auto px-6 py-10">
            {/* Page header */}
            <div className="flex items-center justify-between mb-8">
                <div>
                    <h1 className="text-3xl font-serif font-bold text-[#181611]">Research History</h1>
                    <p className="text-[#8a7e60] mt-1 text-sm">
                        {sessions.length > 0 ? `${sessions.length} sessions saved` : "Your research sessions appear here"}
                    </p>
                </div>
                {sessions.length > 0 && (
                    <span className="font-mono text-xs text-[#8a7e60] bg-[#FAFAF7] border border-[#e5e2db] px-3 py-2 rounded-lg">
                        {sessions.reduce((acc, s) => acc + (s.report?.tokens_used ?? 0), 0).toLocaleString()} total tokens
                    </span>
                )}
            </div>

            {/* Recommendation card */}
            {showRecommendation && (
                <div className="mb-6 p-5 bg-[#F0E6C8] border border-[#b7860b]/30 rounded-xl flex items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                        <span className="material-symbols-outlined text-[#b7860b] shrink-0 mt-0.5" style={{ fontSize: 22 }}>lightbulb</span>
                        <div>
                            <h3 className="font-semibold text-[#181611] mb-1">Based on your research patterns</h3>
                            <p className="text-sm text-[#8a7e60]">
                                You frequently analyze sentiment and pricing. Try a deep dive analysis to uncover root causes.
                            </p>
                        </div>
                    </div>
                    <button
                        onClick={() => window.location.href = "/dashboard"}
                        className="shrink-0 px-4 py-2 flex items-center gap-1.5 text-sm font-medium text-[#b7860b] bg-white border border-[#b7860b]/30 rounded-lg hover:bg-[#b7860b]/5 transition-colors"
                    >
                        Explore
                        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>arrow_forward</span>
                    </button>
                </div>
            )}

            {/* Loading state */}
            {isLoading && (
                <div className="flex items-center justify-center py-20">
                    <LoadingSpinner size={32} />
                </div>
            )}

            {/* Error state */}
            {error && !isLoading && sessions.length === 0 && (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                    <span className="material-symbols-outlined text-[#b91c1c] mb-4" style={{ fontSize: 40 }}>error_outline</span>
                    <p className="text-[#181611] font-medium">Could not load history</p>
                    <p className="text-sm text-[#8a7e60] mt-1">Backend is unavailable. Run a query to see it here.</p>
                </div>
            )}

            {/* Session list */}
            {sessions.length > 0 && (
                <div className="bg-white border border-[#e5e2db] rounded-xl overflow-hidden shadow-sm">
                    {sessions.map((session) => (
                        <HistoryItem
                            key={session.id}
                            session={session}
                            onClick={() => setSelectedSession(session)}
                        />
                    ))}
                </div>
            )}

            {/* Empty state */}
            {!isLoading && sessions.length === 0 && !error && (
                <div className="flex flex-col items-center justify-center py-20 text-center">
                    <div className="w-16 h-16 bg-[#b7860b]/10 rounded-2xl flex items-center justify-center mb-5">
                        <span className="material-symbols-outlined text-[#b7860b]" style={{ fontSize: 32 }}>history</span>
                    </div>
                    <h3 className="text-xl font-serif text-[#181611] mb-2">No research history yet</h3>
                    <p className="text-sm text-[#8a7e60] max-w-sm">
                        Your completed research sessions will appear here. Head to the Dashboard to run your first query.
                    </p>
                    <a
                        href="/dashboard"
                        className="mt-5 px-5 py-2.5 rounded-xl bg-[#b7860b] text-white text-sm font-semibold hover:bg-[#9a7009] transition-colors"
                    >
                        Start Researching
                    </a>
                </div>
            )}

            {/* Report Drawer */}
            {selectedSession && (
                <>
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 z-40 bg-black/30 backdrop-blur-sm"
                        onClick={() => setSelectedSession(null)}
                    />
                    {/* Drawer */}
                    <div className="fixed right-0 top-0 h-full z-50 w-full max-w-2xl bg-[#FAFAF7] shadow-2xl overflow-y-auto animate-slide-in-right">
                        {/* Drawer header */}
                        <div className="sticky top-0 bg-white border-b border-[#e5e2db] px-6 py-4 flex items-center justify-between">
                            <div>
                                <h2 className="font-serif font-bold text-lg text-[#181611]">Research Report</h2>
                                <p className="text-xs text-[#8a7e60] mt-0.5 truncate max-w-xs">{selectedSession.query}</p>
                            </div>
                            <button
                                onClick={() => setSelectedSession(null)}
                                className="p-2 rounded-lg hover:bg-[#FAFAF7] transition-colors text-[#8a7e60] hover:text-[#181611]"
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: 22 }}>close</span>
                            </button>
                        </div>
                        {/* Drawer content */}
                        <div className="p-6">
                            {selectedSession.report ? (
                                <ReportCard report={selectedSession.report} />
                            ) : (
                                <div className="py-20 text-center text-[#8a7e60]">
                                    <p>Report data not available for this session.</p>
                                </div>
                            )}
                        </div>
                    </div>
                </>
            )}
        </div>
    )
}
