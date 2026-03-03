import type { ResearchSession } from "../../lib/types"
import Badge from "../shared/Badge"

interface HistoryItemProps {
    session: ResearchSession
    onClick: () => void
}

export default function HistoryItem({ session, onClick }: HistoryItemProps) {
    const date = new Date(session.created_at)
    const dateStr = date.toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
    })
    const timeStr = date.toLocaleTimeString("en-US", {
        hour: "numeric",
        minute: "2-digit",
        hour12: true,
    })

    return (
        <div
            onClick={onClick}
            className="flex items-center gap-4 px-6 py-4 hover:bg-[#FAFAF7] cursor-pointer transition-colors border-b border-[#e5e2db] last:border-b-0"
        >
            <div className="flex-1 min-w-0">
                <p className="text-[#181611] font-medium text-sm truncate">{session.query}</p>
                <div className="flex items-center gap-3 mt-1">
                    <span className="text-xs text-[#8a7e60]">{dateStr} · {timeStr}</span>
                    {session.report && (
                        <span className="font-mono text-xs text-[#8a7e60]">
                            {session.report.tokens_used.toLocaleString()} tokens
                        </span>
                    )}
                </div>
            </div>
            <div className="flex items-center gap-3 shrink-0">
                <Badge variant={session.mode === "quick" ? "quick" : "deep"} />
                <span className="material-symbols-outlined text-[#8a7e60]" style={{ fontSize: 20 }}>
                    chevron_right
                </span>
            </div>
        </div>
    )
}
