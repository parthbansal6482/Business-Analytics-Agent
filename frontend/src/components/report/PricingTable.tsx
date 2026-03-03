import type { PricingAnalysis } from "../../lib/types"

interface PricingTableProps {
    pricing: PricingAnalysis
}

export default function PricingTable({ pricing }: PricingTableProps) {
    const gapPositive = pricing.gap_pct > 0

    return (
        <div className="p-6 md:p-8">
            <div className="flex items-center gap-2 mb-5">
                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>payments</span>
                <h3 className="text-sm font-semibold uppercase tracking-widest text-[#8a7e60]">Pricing Analysis</h3>
            </div>

            {/* Table */}
            <div className="rounded-xl border border-[#e5e2db] overflow-x-auto mb-5">
                <table className="w-full text-sm text-left whitespace-nowrap">
                    <thead className="bg-[#FAFAF7] border-b border-[#e5e2db]">
                        <tr>
                            {["Product", "Price", "Comp. Avg", "Gap", "Signal"].map((h) => (
                                <th key={h} className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-[#8a7e60]">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-[#e5e2db]">
                        <tr className="bg-[#b7860b]/5">
                            <td className="px-5 py-4 font-bold text-[#181611]">Your Product</td>
                            <td className="px-5 py-4 font-mono font-medium text-[#181611]">
                                ${pricing.your_price.toFixed(2)}
                            </td>
                            <td className="px-5 py-4 font-mono text-[#8a7e60]">
                                ${pricing.competitor_avg.toFixed(2)}
                            </td>
                            <td className={`px-5 py-4 font-mono font-bold ${gapPositive ? "text-[#b91c1c]" : "text-[#15803d]"}`}>
                                {gapPositive ? "+" : ""}{pricing.gap_pct.toFixed(1)}%
                            </td>
                            <td className="px-5 py-4">
                                <span className={`inline-flex items-center gap-1 text-xs font-medium ${gapPositive ? "text-[#b91c1c]" : "text-[#15803d]"}`}>
                                    <span className="material-symbols-outlined" style={{ fontSize: 16 }}>
                                        {gapPositive ? "warning" : "trending_up"}
                                    </span>
                                    {gapPositive ? "Above Market" : "Competitive"}
                                </span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            {/* Recommendation box */}
            <div className="bg-[#F0E6C8] border-l-4 border-[#b7860b] rounded-r-lg p-4">
                <div className="flex items-start gap-2">
                    <span className="material-symbols-outlined text-[#b7860b] shrink-0 mt-0.5" style={{ fontSize: 18 }}>lightbulb</span>
                    <div>
                        <p className="text-xs font-semibold uppercase tracking-wide text-[#b7860b] mb-1">Recommendation</p>
                        <p className="text-sm text-[#181611] leading-relaxed">{pricing.recommendation}</p>
                    </div>
                </div>
            </div>
        </div>
    )
}
