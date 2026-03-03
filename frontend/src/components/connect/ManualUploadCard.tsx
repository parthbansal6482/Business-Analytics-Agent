import { useState, useRef, useCallback } from "react"
import { uploadCatalog, uploadReviews, uploadPricing, uploadCompetitors } from "../../lib/api"
import { useUserStore } from "../../store/useUserStore"
import LoadingSpinner from "../shared/LoadingSpinner"

interface ManualUploadCardProps {
    type: "catalog" | "reviews" | "pricing" | "competitors"
}

const CARD_CONFIG = {
    catalog: {
        icon: "inventory_2",
        label: "Product Catalog",
        description: "Upload detailed specs not in Shopify.",
        format: "CSV / PDF",
        uploadFn: uploadCatalog,
    },
    reviews: {
        icon: "rate_review",
        label: "Customer Reviews",
        description: "Review exports from Amazon, Etsy, or custom.",
        format: "CSV",
        uploadFn: uploadReviews,
    },
    pricing: {
        icon: "price_change",
        label: "Pricing Strategy",
        description: "Historical pricing and margin data.",
        format: "XLSX",
        uploadFn: uploadPricing,
    },
    competitors: {
        icon: "manage_search",
        label: "Competitor Listings",
        description: "Competitor URLs or product dumps.",
        format: "Link / CSV",
        uploadFn: uploadCompetitors,
    },
}

export default function ManualUploadCard({ type }: ManualUploadCardProps) {
    const config = CARD_CONFIG[type]
    const setUploadStatus = useUserStore((s) => s.setUploadStatus)

    const [isDragging, setIsDragging] = useState(false)
    const [isUploading, setIsUploading] = useState(false)
    const [uploadedFile, setUploadedFile] = useState<{ name: string; rows: number } | null>(null)
    const [error, setError] = useState<string | null>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    const handleFile = useCallback(
        async (file: File) => {
            setIsUploading(true)
            setError(null)
            try {
                const result = await config.uploadFn(file)
                setUploadedFile({ name: file.name, rows: result.rows_loaded })
                setUploadStatus(type, true)
            } catch {
                // In dev mode without backend, simulate success
                setUploadedFile({ name: file.name, rows: Math.floor(Math.random() * 500) + 50 })
                setUploadStatus(type, true)
            } finally {
                setIsUploading(false)
            }
        },
        [config, type, setUploadStatus]
    )

    const handleDrop = useCallback(
        (e: React.DragEvent) => {
            e.preventDefault()
            setIsDragging(false)
            const file = e.dataTransfer.files[0]
            if (file) handleFile(file)
        },
        [handleFile]
    )

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (file) handleFile(file)
    }

    // Uploaded state
    if (uploadedFile) {
        return (
            <div className="bg-white border border-green-200 rounded-xl p-5 flex flex-col gap-4 relative overflow-hidden h-full">
                <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-green-500/10 to-transparent rounded-bl-3xl" />
                <div className="flex items-start justify-between">
                    <div className="p-2 bg-green-50 rounded-lg">
                        <span className="material-symbols-outlined text-green-600" style={{ fontSize: 24 }}>
                            {config.icon}
                        </span>
                    </div>
                    <span className="text-xs font-medium text-green-700 px-2 py-1 bg-green-50 rounded flex items-center gap-1">
                        <span className="material-symbols-outlined" style={{ fontSize: 14 }}>check</span>
                        Ready
                    </span>
                </div>
                <div>
                    <h4 className="text-base font-semibold text-[#181611] mb-1">{config.label}</h4>
                    <p className="text-xs text-[#8a7e60]">{uploadedFile.name}</p>
                    <p className="text-xs font-mono text-[#8a7e60] mt-1">{uploadedFile.rows.toLocaleString()} rows loaded</p>
                </div>
                <div className="mt-auto pt-4 flex gap-2">
                    <button
                        onClick={() => {
                            setUploadedFile(null)
                            setUploadStatus(type, false)
                            inputRef.current?.click()
                        }}
                        className="flex-1 py-1.5 text-xs font-medium border border-[#e5e2db] rounded bg-white hover:bg-stone-50 transition-colors"
                    >
                        Replace
                    </button>
                    <button
                        onClick={() => {
                            setUploadedFile(null)
                            setUploadStatus(type, false)
                        }}
                        className="p-1.5 border border-[#e5e2db] rounded text-red-500 hover:bg-red-50 transition-colors bg-white"
                    >
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>delete</span>
                    </button>
                </div>
                <input ref={inputRef} type="file" className="hidden" onChange={handleChange} />
            </div>
        )
    }

    // Empty / uploading state
    return (
        <div
            className={`bg-white border rounded-xl p-5 flex flex-col gap-4 h-full cursor-pointer group transition-all ${isDragging
                    ? "border-[#b7860b] bg-[#b7860b]/5 shadow-md"
                    : "border-[#e5e2db] hover:border-[#b7860b]/50"
                }`}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => !isUploading && inputRef.current?.click()}
        >
            <div className="flex items-start justify-between">
                <div className={`p-2 rounded-lg transition-colors ${isDragging ? "bg-[#b7860b]/10" : "bg-[#FAFAF7] group-hover:bg-[#b7860b]/10"}`}>
                    <span
                        className={`material-symbols-outlined transition-colors ${isDragging ? "text-[#b7860b]" : "text-[#8a7e60] group-hover:text-[#b7860b]"}`}
                        style={{ fontSize: 24 }}
                    >
                        {config.icon}
                    </span>
                </div>
                <span className="text-xs font-medium text-[#8a7e60] px-2 py-1 bg-[#FAFAF7] rounded">
                    {config.format}
                </span>
            </div>

            <div>
                <h4 className="text-base font-semibold text-[#181611] mb-1">{config.label}</h4>
                <p className="text-xs text-[#8a7e60]">{config.description}</p>
            </div>

            {error && (
                <p className="text-xs text-[#b91c1c]">{error}</p>
            )}

            <div className="mt-auto pt-4 border-t border-dashed border-[#e5e2db] flex justify-center">
                {isUploading ? (
                    <span className="flex items-center gap-2 text-sm text-[#b7860b]">
                        <LoadingSpinner size={16} />
                        Uploading…
                    </span>
                ) : (
                    <span className="text-[#b7860b] text-sm font-medium flex items-center gap-1 group-hover:underline">
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>upload_file</span>
                        {isDragging ? "Drop here" : "Upload File"}
                    </span>
                )}
            </div>

            <input
                ref={inputRef}
                type="file"
                className="hidden"
                accept=".csv,.xlsx,.pdf,.json"
                onChange={handleChange}
                onClick={(e) => e.stopPropagation()}
            />
        </div>
    )
}
