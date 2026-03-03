import type { ResearchReport } from "../../lib/types"
import Badge from "../shared/Badge"

interface ReportFooterProps {
    report: ResearchReport
}

export default function ReportFooter({ report }: ReportFooterProps) {
    return (
        <div className="bg-[#FAFAF7] border-t border-[#e5e2db] px-6 md:px-8 py-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                {/* Left: meta stats */}
                <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-[#8a7e60]">
                    <div className="flex items-center gap-1.5">
                        <div className={`w-2 h-2 rounded-full ${report.confidence_score >= 80 ? "bg-[#15803d]" : "bg-[#b45309]"}`} />
                        <span>Confidence: {report.confidence_score}%</span>
                    </div>
                    <span className="hidden sm:inline">•</span>
                    <span>Data: {report.data_completeness}</span>
                    <span className="hidden sm:inline">•</span>
                    <div className="flex items-center gap-1">
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>token</span>
                        <span>{report.tokens_used.toLocaleString()} tokens</span>
                    </div>
                </div>

                {/* Right: cost + mode + duration */}
                <div className="flex items-center gap-4 text-xs font-mono">
                    {/* Cost in success green — always */}
                    <span className="text-[#15803d] font-bold">
                        ${report.cost_usd === 0 ? "0.00" : report.cost_usd.toFixed(2)}
                    </span>
                    <Badge variant={report.mode === "quick" ? "quick" : "deep"} />
                    <span className="text-[#8a7e60]">{report.duration_seconds}s</span>
                </div>
            </div>
        </div>
    )
}
