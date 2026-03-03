import type { SentimentBreakdown, KeyMetrics } from "../../lib/types"
import SentimentBar from "../shared/SentimentBar"
import MetricPill from "../shared/MetricPill"

interface SentimentSectionProps {
    sentiment: SentimentBreakdown
    metrics: KeyMetrics
}

export default function SentimentSection({ sentiment, metrics }: SentimentSectionProps) {
    const revenueTrend = metrics.revenue_impact.startsWith("-") ? "down" : "up"
    const ratingTrend = metrics.rating_change.startsWith("-") ? "down" : "up"
    const priceTrend = metrics.price_gap_pct > 0 ? "up" : "down"

    return (
        <div className="p-6 md:p-8">
            <div className="flex items-center gap-2 mb-6">
                <span className="material-symbols-outlined text-[#b7860b]" style={{ fontSize: 20 }}>sentiment_satisfied</span>
                <h3 className="text-sm font-semibold uppercase tracking-widest text-[#8a7e60]">Sentiment Overview</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
                {/* Sentiment bar — 3/5 width on md */}
                <div className="md:col-span-3">
                    <div className="flex justify-between mb-2 text-xs text-[#8a7e60] font-medium">
                        <span>Review Sentiment Distribution</span>
                        <span className={`font-bold ${sentiment.positive_pct >= 60 ? "text-[#15803d]" : sentiment.positive_pct >= 40 ? "text-[#b45309]" : "text-[#b91c1c]"}`}>
                            {sentiment.positive_pct}% Positive
                        </span>
                    </div>
                    <SentimentBar
                        positive={sentiment.positive_pct}
                        neutral={sentiment.neutral_pct}
                        negative={sentiment.negative_pct}
                    />
                </div>

                {/* Key metrics — 2/5 width */}
                <div className="md:col-span-2 space-y-2">
                    <MetricPill label="Revenue Impact" value={metrics.revenue_impact} trend={revenueTrend} />
                    <MetricPill label="Rating Change" value={metrics.rating_change} trend={ratingTrend} />
                    <MetricPill
                        label="Price Gap"
                        value={`${metrics.price_gap_pct > 0 ? "+" : ""}${metrics.price_gap_pct}%`}
                        trend={priceTrend}
                    />
                </div>
            </div>
        </div>
    )
}
