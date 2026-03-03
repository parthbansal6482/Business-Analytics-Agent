import { useSessionStore } from "../../store/useSessionStore"

export default function CostBadge() {
    const { totalTokensUsed, totalCost } = useSessionStore()

    const costDisplay = totalCost === 0 ? "$0.00" : `$${totalCost.toFixed(2)}`
    const isZero = totalCost === 0

    return (
        <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-mono ${isZero
                    ? "bg-[#e6f4ea] border-[#bceac5] text-[#137333]"
                    : "bg-white border-[#e5e2db] text-[#181611]"
                }`}
        >
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                {isZero ? "monetization_on" : "payments"}
            </span>
            <span>
                {costDisplay}
                {totalTokensUsed > 0 && (
                    <span className="text-[#8a7e60] ml-1.5">· {totalTokensUsed.toLocaleString()} tokens</span>
                )}
            </span>
        </div>
    )
}
