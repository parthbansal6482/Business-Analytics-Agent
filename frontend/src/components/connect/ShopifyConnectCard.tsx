import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getShopifyStatus, triggerShopifySync, connectShopify } from "../../lib/api"
import { useUserStore } from "../../store/useUserStore"
import LoadingSpinner from "../shared/LoadingSpinner"

export default function ShopifyConnectCard() {
    const queryClient = useQueryClient()
    const setShopifyConnected = useUserStore((s) => s.setShopifyConnected)

    const { data: status, isLoading } = useQuery({
        queryKey: ["shopify-status"],
        queryFn: getShopifyStatus,
        retry: false,
        refetchOnWindowFocus: false,
        // In dev mode without backend, treat errors as disconnected
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        select: (data: any) => {
            setShopifyConnected(data.connected)
            return data
        },
    })

    const syncMutation = useMutation({
        mutationFn: triggerShopifySync,
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["shopify-status"] }),
    })

    const isConnected = status?.connected ?? false

    if (isLoading) {
        return (
            <div className="flex gap-6 p-6 rounded-xl border border-[#e5e2db] bg-white shadow-sm items-center justify-center h-40">
                <LoadingSpinner size={24} />
                <span className="text-sm text-[#8a7e60]">Checking connection…</span>
            </div>
        )
    }

    if (isConnected) {
        return (
            <div className="group flex flex-col md:flex-row gap-6 p-6 rounded-xl border border-[#b7860b]/30 bg-[#b7860b]/5 shadow-sm relative overflow-hidden">
                {/* Green checkmark */}
                <div className="absolute top-3 right-3">
                    <span className="material-symbols-outlined text-[#15803d]">check_circle</span>
                </div>

                {/* Store thumbnail */}
                <div className="w-full md:w-48 aspect-video md:aspect-auto bg-white rounded-lg flex items-center justify-center border border-[#b7860b]/20 overflow-hidden shrink-0">
                    <span className="material-symbols-outlined text-[#b7860b]" style={{ fontSize: 40 }}>storefront</span>
                </div>

                {/* Info */}
                <div className="flex-1 flex flex-col justify-between gap-4">
                    <div>
                        <div className="flex items-center gap-2 mb-1">
                            <h4 className="text-lg font-bold text-[#181611]">{status?.shop_domain || "Your Store"}</h4>
                            <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-green-100 text-green-700 text-xs font-medium">
                                <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                                Active
                            </span>
                        </div>
                        <p className="text-sm text-[#8a7e60]">
                            Syncing: Products, Orders, Customers.<br />
                            Last synced: {status?.last_sync ? new Date(status.last_sync).toLocaleString() : "Recently"}
                        </p>
                    </div>

                    {/* Stats */}
                    <div className="flex gap-6">
                        <div>
                            <p className="font-mono text-sm font-bold text-[#181611]">{status?.products_synced?.toLocaleString() ?? "—"}</p>
                            <p className="text-xs text-[#8a7e60]">Products</p>
                        </div>
                        <div>
                            <p className="font-mono text-sm font-bold text-[#181611]">{status?.orders_synced?.toLocaleString() ?? "—"}</p>
                            <p className="text-xs text-[#8a7e60]">Orders</p>
                        </div>
                        <div>
                            <p className="font-mono text-sm font-bold text-[#181611]">{status?.reviews_synced?.toLocaleString() ?? "—"}</p>
                            <p className="text-xs text-[#8a7e60]">Reviews</p>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3">
                        <button
                            onClick={() => syncMutation.mutate()}
                            disabled={syncMutation.isPending}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#b7860b] text-white text-sm font-semibold hover:bg-[#9a7009] transition-colors disabled:opacity-60"
                        >
                            {syncMutation.isPending ? (
                                <LoadingSpinner size={16} />
                            ) : (
                                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>refresh</span>
                            )}
                            Sync Now
                        </button>
                        <button className="px-4 py-2 rounded-lg border border-[#e5e2db] text-sm font-medium text-[#8a7e60] hover:text-[#181611] hover:border-[#b7860b]/50 transition-colors">
                            Disconnect
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    // Disconnected state
    return (
        <div className="group flex flex-col md:flex-row gap-6 p-6 rounded-xl border border-[#e5e2db] bg-white shadow-sm hover:shadow-md transition-shadow">
            {/* Storefront icon */}
            <div className="w-full md:w-48 aspect-video md:aspect-auto bg-stone-50 rounded-lg flex items-center justify-center relative overflow-hidden shrink-0">
                <span className="material-symbols-outlined text-stone-300" style={{ fontSize: 56 }}>storefront</span>
                <div className="absolute inset-0 bg-gradient-to-tr from-black/5 to-transparent" />
            </div>

            {/* Info */}
            <div className="flex-1 flex flex-col justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2 mb-2">
                        <h4 className="text-lg font-bold text-[#181611]">Shopify Store</h4>
                        <span className="px-2 py-0.5 rounded-full bg-stone-100 text-stone-600 text-xs font-medium">Disconnected</span>
                    </div>
                    <p className="text-sm text-[#8a7e60] leading-relaxed">
                        Connect your main store to sync product catalog, sales history, and customer behavior data automatically.
                    </p>
                </div>
                <button
                    onClick={connectShopify}
                    className="flex items-center justify-center gap-2 w-full md:w-fit px-5 py-2.5 rounded-lg bg-[#b7860b] text-white text-sm font-semibold hover:bg-[#9a7009] transition-colors shadow-sm"
                >
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>link</span>
                    Connect Store
                </button>
            </div>
        </div>
    )
}
