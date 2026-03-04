import { useEffect, useRef, useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getShopifyStatus, triggerShopifySync, connectShopify, disconnectShopify } from "../../lib/api"
import { useUserStore } from "../../store/useUserStore"
import LoadingSpinner from "../shared/LoadingSpinner"
import type { ShopifyStatus } from "../../lib/types"

export default function ShopifyConnectCard() {
    const queryClient = useQueryClient()
    const userId = useUserStore((s) => s.userId)
    const setShopifyConnected = useUserStore((s) => s.setShopifyConnected)
    const popupPollRef = useRef<number | null>(null)
    const syncPollRef = useRef<number | null>(null)
    const [isSyncing, setIsSyncing] = useState(false)
    const [syncStatusText, setSyncStatusText] = useState<"idle" | "success" | "error">("idle")

    const { data: status, isLoading } = useQuery({
        queryKey: ["shopify-status"],
        queryFn: getShopifyStatus,
        retry: false,
        refetchOnWindowFocus: true,
    })

    useEffect(() => {
        if (status) {
            setShopifyConnected(status.connected)
        }
    }, [status, setShopifyConnected])

    useEffect(() => {
        const handleMessage = (event: MessageEvent) => {
            if (event.data?.type === "shopify-auth-success") {
                const current = queryClient.getQueryData<{ last_sync?: string | null }>(["shopify-status"])
                setShopifyConnected(true)
                queryClient.invalidateQueries({ queryKey: ["shopify-status"] })
                startSyncPolling(current?.last_sync ?? null)
            }
        }
        window.addEventListener("message", handleMessage)
        return () => window.removeEventListener("message", handleMessage)
    }, [queryClient, setShopifyConnected])

    useEffect(() => {
        return () => {
            if (popupPollRef.current) {
                window.clearInterval(popupPollRef.current)
            }
            if (syncPollRef.current) {
                window.clearInterval(syncPollRef.current)
            }
            setIsSyncing(false)
        }
    }, [])

    const syncMutation = useMutation({
        mutationFn: triggerShopifySync,
        onMutate: () => {
            setIsSyncing(true)
            setSyncStatusText("idle")
        },
        onSuccess: async (data) => {
            queryClient.setQueryData<ShopifyStatus>(["shopify-status"], data)
            await queryClient.invalidateQueries({ queryKey: ["shopify-status"] })
            setSyncStatusText("success")
        },
        onError: () => {
            setSyncStatusText("error")
        },
        onSettled: () => {
            setIsSyncing(false)
        },
    })

    const disconnectMutation = useMutation({
        mutationFn: disconnectShopify,
        onSuccess: async () => {
            setShopifyConnected(false)
            if (syncPollRef.current) {
                window.clearInterval(syncPollRef.current)
                syncPollRef.current = null
            }
            setIsSyncing(false)
            await queryClient.invalidateQueries({ queryKey: ["shopify-status"] })
        },
    })

    const [shopDomain, setShopDomain] = useState("")

    const stopSyncPolling = () => {
        if (syncPollRef.current) {
            window.clearInterval(syncPollRef.current)
            syncPollRef.current = null
        }
        setIsSyncing(false)
    }

    const startSyncPolling = (previousLastSync: string | null) => {
        stopSyncPolling()
        setIsSyncing(true)

        let attempts = 0
        syncPollRef.current = window.setInterval(async () => {
            attempts += 1
            const latest = await queryClient.fetchQuery({
                queryKey: ["shopify-status"],
                queryFn: getShopifyStatus,
            })
            const hasNewSync =
                !!latest?.last_sync && (!previousLastSync || latest.last_sync !== previousLastSync)

            if (hasNewSync || latest?.connected === false || attempts >= 20) {
                stopSyncPolling()
            }
        }, 1500)
    }

    const handleConnect = () => {
        if (!shopDomain) return
        const normalized = shopDomain.trim().replace(/^https?:\/\//, "").replace(/\/.*$/, "")
        // Ensure it ends with .myshopify.com if just a name is provided
        const fullDomain = normalized.includes(".") ? normalized : `${normalized}.myshopify.com`
        const popup = connectShopify(fullDomain, userId)
        if (!popup) return

        if (popupPollRef.current) {
            window.clearInterval(popupPollRef.current)
            popupPollRef.current = null
        }

        popupPollRef.current = window.setInterval(() => {
            if (popup.closed) {
                if (popupPollRef.current) {
                    window.clearInterval(popupPollRef.current)
                    popupPollRef.current = null
                }
                const current = queryClient.getQueryData<{ last_sync?: string | null }>(["shopify-status"])
                queryClient.invalidateQueries({ queryKey: ["shopify-status"] })
                startSyncPolling(current?.last_sync ?? null)
            }
        }, 500)
    }

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
                                Connected
                            </span>
                        </div>
                        <p className="text-sm text-[#8a7e60]">
                            {isSyncing && "Syncing: Products, Orders, Customers."}
                            {!isSyncing && syncStatusText === "success" && "Sync Completed"}
                            {!isSyncing && syncStatusText === "error" && "Sync Failed"}
                            {(isSyncing || syncStatusText !== "idle") && <br />}
                            Last synced: {isSyncing ? "Syncing..." : (status?.last_sync ? new Date(status.last_sync).toLocaleString() : "Recently")}
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
                            <p className="text-xs text-[#8a7e60]">Customers</p>
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3">
                        <button
                            onClick={() => syncMutation.mutate()}
                            disabled={syncMutation.isPending || isSyncing}
                            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[#b7860b] text-white text-sm font-semibold hover:bg-[#9a7009] transition-colors disabled:opacity-60"
                        >
                            {syncMutation.isPending || isSyncing ? (
                                <LoadingSpinner size={16} />
                            ) : (
                                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>refresh</span>
                            )}
                            {isSyncing ? "Syncing..." : "Sync Now"}
                        </button>
                        <button
                            onClick={() => disconnectMutation.mutate()}
                            disabled={disconnectMutation.isPending}
                            className="px-4 py-2 rounded-lg border border-[#e5e2db] text-sm font-medium text-[#8a7e60] hover:text-[#181611] hover:border-[#b7860b]/50 transition-colors disabled:opacity-60"
                        >
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
                    <p className="text-sm text-[#8a7e60] leading-relaxed mb-4">
                        Connect your main store to sync product catalog, sales history, and customer behavior data automatically.
                    </p>

                    <div className="flex flex-col gap-2">
                        <label className="text-xs font-bold text-[#181611] uppercase tracking-wider">Store Domain</label>
                        <div className="flex gap-2">
                            <input
                                type="text"
                                placeholder="my-store.myshopify.com"
                                value={shopDomain}
                                onChange={(e) => setShopDomain(e.target.value)}
                                className="flex-1 px-4 py-2 rounded-lg border border-[#e5e2db] text-sm focus:outline-none focus:border-[#b7860b] transition-colors"
                            />
                            <button
                                onClick={handleConnect}
                                disabled={!shopDomain}
                                className="flex items-center justify-center gap-2 px-5 py-2.5 rounded-lg bg-[#b7860b] text-white text-sm font-semibold hover:bg-[#9a7009] transition-colors shadow-sm disabled:opacity-50"
                            >
                                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>link</span>
                                Connect
                            </button>
                        </div>
                        <p className="text-[10px] text-[#8a7e60]">Enter your full .myshopify.com domain</p>
                    </div>
                </div>
            </div>
        </div>
    )
}
