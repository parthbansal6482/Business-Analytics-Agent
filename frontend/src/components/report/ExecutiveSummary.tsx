import type { ResearchMode } from "../../lib/types"
import Badge from "../shared/Badge"

interface ExecutiveSummaryProps {
    summary: string
    mode: ResearchMode
    duration: number
}

export default function ExecutiveSummary({ summary, mode, duration }: ExecutiveSummaryProps) {
    return (
        <div className="p-6 md:p-8 relative overflow-hidden">
            <div className="absolute top-0 left-0 w-1 h-full bg-[#b7860b]" />
            <p className="text-xs font-semibold text-[#8a7e60] uppercase tracking-widest mb-4">
                Executive Summary
            </p>
            <p className="text-[#181611] text-xl md:text-2xl font-serif leading-relaxed mb-5">
                {summary}
            </p>
            <div className="flex items-center gap-3 flex-wrap">
                <Badge variant={mode === "quick" ? "quick" : "deep"} />
                <span className="flex items-center gap-1.5 text-xs text-[#8a7e60] font-mono bg-[#FAFAF7] border border-[#e5e2db] px-3 py-1.5 rounded-lg">
                    <span className="material-symbols-outlined" style={{ fontSize: 14 }}>timer</span>
                    {duration}s
                </span>
            </div>
        </div>
    )
}
