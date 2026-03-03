interface ComplaintsSectionProps {
    complaints: string[]
    featureRequests: string[]
}

export default function ComplaintsSection({ complaints, featureRequests }: ComplaintsSectionProps) {
    return (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
            {/* Top Complaints */}
            <div className="p-6 md:p-8 border-b lg:border-b-0 lg:border-r border-[#e5e2db]">
                <div className="flex items-center gap-2 mb-4">
                    <span className="material-symbols-outlined text-[#b91c1c]" style={{ fontSize: 20 }}>warning</span>
                    <h3 className="text-sm font-semibold uppercase tracking-widest text-[#8a7e60]">Top Complaints</h3>
                </div>
                <div className="space-y-3">
                    {complaints.map((complaint, i) => (
                        <div key={i} className="flex items-start gap-3">
                            <span className="font-mono text-[#b91c1c] font-bold text-sm shrink-0 mt-0.5">
                                {String(i + 1).padStart(2, "0")}
                            </span>
                            <p className="text-[#181611] text-sm leading-relaxed">{complaint}</p>
                        </div>
                    ))}
                    {complaints.length === 0 && (
                        <p className="text-sm text-[#8a7e60] italic">No major complaints detected</p>
                    )}
                </div>
            </div>

            {/* Feature Requests */}
            <div className="p-6 md:p-8">
                <div className="flex items-center gap-2 mb-4">
                    <span className="material-symbols-outlined text-[#b7860b]" style={{ fontSize: 20 }}>favorite</span>
                    <h3 className="text-sm font-semibold uppercase tracking-widest text-[#8a7e60]">Customer Wishlist</h3>
                </div>
                <div className="space-y-3">
                    {featureRequests.map((req, i) => (
                        <div key={i} className="flex items-start gap-3">
                            <span className="bg-[#b7860b]/10 text-[#b7860b] rounded-full p-1 material-symbols-outlined shrink-0 mt-0.5" style={{ fontSize: 14 }}>
                                check
                            </span>
                            <p className="text-[#181611] text-sm leading-relaxed">{req}</p>
                        </div>
                    ))}
                    {featureRequests.length === 0 && (
                        <p className="text-sm text-[#8a7e60] italic">No feature requests detected</p>
                    )}
                </div>
            </div>
        </div>
    )
}
