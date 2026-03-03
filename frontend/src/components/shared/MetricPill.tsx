interface MetricPillProps {
    label: string
    value: string
    trend: "up" | "down" | "neutral"
}

export default function MetricPill({ label, value, trend }: MetricPillProps) {
    const trendColor =
        trend === "up"
            ? "text-[#15803d]"
            : trend === "down"
                ? "text-[#b91c1c]"
                : "text-[#8a7e60]"

    const trendIcon =
        trend === "up"
            ? "trending_up"
            : trend === "down"
                ? "trending_down"
                : "trending_flat"

    return (
        <div className="flex items-center justify-between p-3 rounded-lg bg-[#FAFAF7] border border-[#e5e2db]">
            <span className="text-xs text-[#8a7e60] font-medium uppercase tracking-wide">{label}</span>
            <div className={`flex items-center gap-1 font-mono text-sm font-bold ${trendColor}`}>
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{trendIcon}</span>
                {value}
            </div>
        </div>
    )
}
