interface CompetitiveGapsProps {
    gaps: string[]
}

function getSignalForGap(gap: string): { label: string; color: string } {
    const lower = gap.toLowerCase()
    if (lower.includes("ahead")) return { label: "Ahead", color: "bg-green-100 text-green-800" }
    if (lower.includes("missing")) return { label: "Missing", color: "bg-red-100 text-red-800" }
    if (lower.includes("outdated")) return { label: "Outdated", color: "bg-orange-100 text-orange-800" }
    return { label: "Behind", color: "bg-red-100 text-red-800" }
}

export default function CompetitiveGaps({ gaps }: CompetitiveGapsProps) {
    return (
        <div className="p-6 md:p-8">
            <div className="flex items-center gap-2 mb-5">
                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>group</span>
                <h3 className="text-sm font-semibold uppercase tracking-widest text-[#8a7e60]">Competitive Gaps</h3>
            </div>

            {gaps.length === 0 ? (
                <p className="text-sm text-[#8a7e60] italic">No competitive gaps identified.</p>
            ) : (
                <div className="rounded-xl border border-[#e5e2db] overflow-hidden">
                    <table className="w-full text-sm text-left">
                        <thead className="bg-[#FAFAF7] border-b border-[#e5e2db]">
                            <tr>
                                {["#", "Gap", "Signal"].map((h) => (
                                    <th key={h} className="px-5 py-3 text-xs font-semibold uppercase tracking-wide text-[#8a7e60]">
                                        {h}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-[#e5e2db]">
                            {gaps.map((gap, i) => {
                                const sig = getSignalForGap(gap)
                                return (
                                    <tr key={i} className="hover:bg-[#FAFAF7] transition-colors">
                                        <td className="px-5 py-4 font-mono text-[#8a7e60] text-xs w-8">
                                            {String(i + 1).padStart(2, "0")}
                                        </td>
                                        <td className="px-5 py-4 text-[#181611]">{gap}</td>
                                        <td className="px-5 py-4">
                                            <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-bold ${sig.color}`}>
                                                {sig.label}
                                            </span>
                                        </td>
                                    </tr>
                                )
                            })}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}
