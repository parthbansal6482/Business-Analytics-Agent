interface RootCauseBlockProps {
    rootCause: string
}

export default function RootCauseBlock({ rootCause }: RootCauseBlockProps) {
    return (
        <div className="relative overflow-hidden">
            {/* Gold background */}
            <div className="absolute inset-0 bg-[#F0E6C8]">
                <div
                    className="absolute inset-0 opacity-10"
                    style={{ backgroundImage: "radial-gradient(#A0522D 1px, transparent 1px)", backgroundSize: "20px 20px" }}
                />
            </div>

            <div className="relative z-10 p-6 md:p-8">
                <div className="flex items-start gap-4 mb-5">
                    <div className="bg-white p-2 rounded-lg shadow-sm text-[#A0522D] shrink-0">
                        <span className="material-symbols-outlined" style={{ fontSize: 24 }}>psychology</span>
                    </div>
                    <div>
                        <h3 className="text-xl font-serif font-bold text-[#4A3728]">Root Cause Analysis</h3>
                        <p className="text-sm text-[#8B7355] mt-0.5">Deep dive into sentiment drivers</p>
                    </div>
                </div>

                <div className="bg-white/80 backdrop-blur-sm rounded-xl p-5 border border-[#E6D7B0]">
                    <p className="text-sm text-[#5D4037] leading-relaxed">{rootCause}</p>
                </div>
            </div>
        </div>
    )
}
