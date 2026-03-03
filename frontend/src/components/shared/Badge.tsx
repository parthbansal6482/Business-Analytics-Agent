interface BadgeProps {
    variant: "high" | "medium" | "low" | "quick" | "deep" | "connected" | "error" | "disconnected"
    label?: string
}

const BADGE_STYLES: Record<BadgeProps["variant"], string> = {
    high: "bg-red-100 text-red-800 border-red-200",
    medium: "bg-orange-100 text-orange-800 border-orange-200",
    low: "bg-green-100 text-green-800 border-green-200",
    quick: "bg-[#b7860b]/10 text-[#b7860b] border-[#b7860b]/20",
    deep: "bg-purple-50 text-purple-700 border-purple-100",
    connected: "bg-green-50 text-green-700 border-green-200",
    error: "bg-red-50 text-red-600 border-red-100",
    disconnected: "bg-stone-100 text-stone-600 border-stone-200",
}

const BADGE_ICONS: Record<BadgeProps["variant"], string> = {
    high: "arrow_upward",
    medium: "arrow_forward",
    low: "arrow_downward",
    quick: "bolt",
    deep: "database",
    connected: "link",
    error: "error",
    disconnected: "link_off",
}

const DEFAULT_LABELS: Record<BadgeProps["variant"], string> = {
    high: "High",
    medium: "Medium",
    low: "Low",
    quick: "Quick Scan",
    deep: "Deep Dive",
    connected: "Connected",
    error: "Error",
    disconnected: "Disconnected",
}

export default function Badge({ variant, label }: BadgeProps) {
    const styles = BADGE_STYLES[variant]
    const icon = BADGE_ICONS[variant]
    const text = label ?? DEFAULT_LABELS[variant]

    return (
        <span
            className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-sm font-medium ${styles}`}
        >
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>{icon}</span>
            {text}
        </span>
    )
}
