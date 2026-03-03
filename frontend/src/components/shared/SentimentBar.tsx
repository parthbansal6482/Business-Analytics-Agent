interface SentimentBarProps {
    positive: number
    neutral: number
    negative: number
}

export default function SentimentBar({ positive, neutral, negative }: SentimentBarProps) {
    return (
        <div className="space-y-3">
            {/* Stacked bar */}
            <div className="h-3 w-full rounded-full overflow-hidden flex bg-stone-100">
                <div
                    className="h-full bg-[#15803d]"
                    style={{ width: `${positive}%` }}
                    title={`Positive: ${positive}%`}
                />
                <div
                    className="h-full bg-stone-300"
                    style={{ width: `${neutral}%` }}
                    title={`Neutral: ${neutral}%`}
                />
                <div
                    className="h-full bg-[#b91c1c]"
                    style={{ width: `${negative}%` }}
                    title={`Negative: ${negative}%`}
                />
            </div>
            {/* Legend */}
            <div className="flex items-center justify-between text-xs text-[#8a7e60]">
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-[#15803d]" />
                    <span>Positive ({positive}%)</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-stone-300" />
                    <span>Neutral ({neutral}%)</span>
                </div>
                <div className="flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-[#b91c1c]" />
                    <span>Negative ({negative}%)</span>
                </div>
            </div>
        </div>
    )
}
