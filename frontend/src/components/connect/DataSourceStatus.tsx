import { useUserStore } from "../../store/useUserStore"

const SOURCE_LABELS = {
    catalog: "Product Catalog",
    reviews: "Customer Reviews",
    pricing: "Pricing Strategy",
    competitors: "Competitor Listings",
}

const SOURCE_ICONS = {
    catalog: "inventory_2",
    reviews: "rate_review",
    pricing: "price_change",
    competitors: "manage_search",
}

export default function DataSourceStatus() {
    const { uploadStatus, filenames } = useUserStore()
    const readyCount = Object.values(uploadStatus).filter(Boolean).length
    const totalCount = 4 // 4 manual uploads

    return (
        <div className="bg-white border border-[#e5e2db] rounded-xl p-5">
            <div className="flex items-center justify-between mb-4">
                <h4 className="text-sm font-semibold text-[#181611]">Manual Data Status</h4>
                <span className={`font-mono text-sm font-bold ${readyCount >= 1 ? "text-[#15803d]" : "text-[#8a7e60]"}`}>
                    {readyCount} of {totalCount} ready
                </span>
            </div>
            <div className="flex flex-wrap gap-3">
                {/* Manual uploads */}
                {(Object.keys(uploadStatus) as Array<keyof typeof uploadStatus>).map((key) => (
                    <SourceDot
                        key={key}
                        label={filenames[key] || SOURCE_LABELS[key]}
                        icon={SOURCE_ICONS[key]}
                        ready={uploadStatus[key]}
                        isManual={true}
                    />
                ))}
            </div>
        </div>
    )
}

function SourceDot({ label, icon, ready, isManual }: { label: string; icon: string; ready: boolean; isManual?: boolean }) {
    return (
        <div className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-all ${ready ? "bg-green-50 border-green-200" : "bg-[#FAFAF7] border-[#e5e2db]"}`}>
            <div className={`w-2 h-2 rounded-full ${ready ? "bg-[#15803d]" : "bg-stone-300"}`} />
            <span className={`material-symbols-outlined ${ready ? "text-[#15803d]" : "text-[#8a7e60]"}`} style={{ fontSize: 16 }}>{icon}</span>
            <span className={`text-xs font-medium ${ready ? "text-[#15803d]" : "text-[#181611]"} ${isManual && ready ? "max-w-[120px] truncate" : ""}`}>{label}</span>
        </div>
    )
}
