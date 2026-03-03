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
    shopifyConnected: boolean
    setPreferences: (p: Partial<UserPreferences>) => void
    setDataReady: (v: boolean) => void
    setUploadStatus: (type: keyof UploadStatus, ready: boolean) => void
    setShopifyConnected: (v: boolean) => void
}

export const useUserStore = create<UserStore>()(
    persist(
        (set, get) => ({
            userId: crypto.randomUUID(),
            dataReady: false,
            shopifyConnected: false,
            uploadStatus: {
                catalog: false,
                reviews: false,
                pricing: false,
                competitors: false,
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
            setShopifyConnected: (v) => {
                set({ shopifyConnected: v })
                // check if any data source available
                const s = get()
                const anyReady = v || Object.values(s.uploadStatus).some(Boolean)
                set({ dataReady: anyReady })
            },
            setUploadStatus: (type, ready) => {
                set((s) => {
                    const newStatus = { ...s.uploadStatus, [type]: ready }
                    const anyReady = s.shopifyConnected || Object.values(newStatus).some(Boolean)
                    return { uploadStatus: newStatus, dataReady: anyReady }
                })
            },
        }),
        { name: "user-store" }
    )
)
