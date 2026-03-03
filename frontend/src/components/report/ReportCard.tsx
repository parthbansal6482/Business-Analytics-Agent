import type { ResearchReport } from "../../lib/types"
import ExecutiveSummary from "./ExecutiveSummary"
import SentimentSection from "./SentimentSection"
import ComplaintsSection from "./ComplaintsSection"
import PricingTable from "./PricingTable"
import CompetitiveGaps from "./CompetitiveGaps"
import RootCauseBlock from "./RootCauseBlock"
import ActionItems from "./ActionItems"
import ReportFooter from "./ReportFooter"

interface ReportCardProps {
    report: ResearchReport
}

export default function ReportCard({ report }: ReportCardProps) {
    return (
        <div className="bg-white border border-[#e5e2db] rounded-xl shadow-sm overflow-hidden animate-fade-in">
            {report.error && (
                <div className="bg-red-50 border-b border-red-200 p-4 flex items-start gap-3">
                    <span className="material-symbols-outlined text-red-600 mt-0.5" style={{ fontSize: 20 }}>warning</span>
                    <div>
                        <h4 className="text-sm font-semibold text-red-900">Analysis Interrupted</h4>
                        <p className="text-sm text-red-700 mt-1">{report.error}</p>
                    </div>
                </div>
            )}

            {/* 1. Executive Summary */}
            <ExecutiveSummary
                summary={report.executive_summary}
                mode={report.mode}
                duration={report.duration_seconds}
            />

            <div className="border-t border-[#e5e2db]" />

            {/* 2. Sentiment Overview */}
            <SentimentSection
                sentiment={report.sentiment_breakdown}
                metrics={report.key_metrics}
            />

            <div className="border-t border-[#e5e2db]" />

            {/* 3. Complaints & Feature Requests */}
            <ComplaintsSection
                complaints={report.sentiment_breakdown.top_complaints}
                featureRequests={report.sentiment_breakdown.feature_requests}
            />

            <div className="border-t border-[#e5e2db]" />

            {/* 4. Pricing Analysis */}
            <PricingTable pricing={report.pricing_analysis} />

            <div className="border-t border-[#e5e2db]" />

            {/* 5. Competitive Gaps */}
            <CompetitiveGaps gaps={report.competitive_gaps} />

            <div className="border-t border-[#e5e2db]" />

            {/* 6. Root Cause (gold section) */}
            <RootCauseBlock rootCause={report.root_cause} />

            <div className="border-t border-[#e5e2db]" />

            {/* 7. Recommended Actions */}
            <ActionItems actions={report.recommended_actions} />

            {/* 8. Footer */}
            <ReportFooter report={report} />
        </div>
    )
}
