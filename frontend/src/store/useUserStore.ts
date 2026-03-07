import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { UserPreferences } from "../lib/types"

interface UploadStatus {
    catalog: boolean
    reviews: boolean
    pricing: boolean
    competitors: boolean
}

interface UserStore {
    userId: string
    preferences: UserPreferences
    dataReady: boolean
    uploadStatus: UploadStatus
    filenames: Record<string, string | null>
    shopifyConnected: boolean
    setPreferences: (p: Partial<UserPreferences>) => void
    setDataReady: (v: boolean) => void
    setUploadStatus: (type: keyof UploadStatus, ready: boolean) => void
    setFilename: (type: keyof UploadStatus, name: string | null) => void
    setShopifyConnected: (v: boolean) => void
    clearManualUploads: () => void
    syncUploadStatus: () => Promise<void>
}

export const useUserStore = create<UserStore>()(
    persist(
        (set, get) => ({
            userId: typeof crypto !== "undefined" && typeof crypto.randomUUID === "function"
                ? crypto.randomUUID()
                : Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15),
            dataReady: false,
            shopifyConnected: false,
            uploadStatus: {
                catalog: false,
                reviews: false,
                pricing: false,
                competitors: false,
            },
            filenames: {
                catalog: null,
                reviews: null,
                pricing: null,
                competitors: null,
            },
            preferences: {
                preferred_kpis: ["Conversion Rate", "Customer Retention"],
                marketplaces: ["Amazon US", "Google Shopping"],
                categories_of_interest: [],
                analysis_style: "growth-focused",
            },
            setPreferences: (p) =>
                set((s) => ({ preferences: { ...s.preferences, ...p } })),
            setDataReady: (dataReady) => set({ dataReady }),
            setFilename: (type, name) =>
                set((s) => ({ filenames: { ...s.filenames, [type]: name } })),
            setShopifyConnected: (v) => {
                set((s) => ({
                    shopifyConnected: v,
                    // If connecting Shopify, clear all manual uploads
                    uploadStatus: v ? {
                        catalog: false,
                        reviews: false,
                        pricing: false,
                        competitors: false,
                    } : s.uploadStatus,
                    filenames: v ? {
                        catalog: null,
                        reviews: null,
                        pricing: null,
                        competitors: null,
                    } : s.filenames,
                    dataReady: v || (!v && Object.values(s.uploadStatus).some(Boolean))
                }))
            },
            setUploadStatus: (type, ready) => {
                set((s) => {
                    const newStatus = { ...s.uploadStatus, [type]: ready }
                    // If adding a manual upload, disconnect Shopify
                    const shouldDisconnectShopify = ready && s.shopifyConnected
                    const anyReady = ready || Object.values(newStatus).some(Boolean)

                    return {
                        uploadStatus: newStatus,
                        shopifyConnected: shouldDisconnectShopify ? false : s.shopifyConnected,
                        dataReady: anyReady
                    }
                })
            },
            clearManualUploads: () => {
                set({
                    uploadStatus: {
                        catalog: false,
                        reviews: false,
                        pricing: false,
                        competitors: false,
                    },
                    filenames: {
                        catalog: null,
                        reviews: null,
                        pricing: null,
                        competitors: null,
                    },
                    dataReady: get().shopifyConnected
                })
            },
            syncUploadStatus: async () => {
                try {
                    const { getUploadStatus } = await import("../lib/api")
                    const status = await getUploadStatus()
                    set((s) => {
                        const anyReady = s.shopifyConnected || Object.values(status).some(Boolean)
                        return { uploadStatus: status as any, dataReady: anyReady }
                    })
                } catch {
                    // ignore if backend down
                }
            },
        }),
        { name: "user-store" }
    )
)
