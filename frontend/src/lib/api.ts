import axios from "axios"
import type {
    ResearchSession, UserPreferences,
    ShopifyStatus, UploadResult
} from "./types"
import { API_URL } from "../config"

import { useUserStore } from "../store/useUserStore"

const api = axios.create({
    baseURL: `${API_URL}/api`,
    headers: { "Content-Type": "application/json" },
})

// Inject X-User-ID header from store
api.interceptors.request.use((config) => {
    const userId = useUserStore.getState().userId
    if (userId) {
        config.headers["X-User-ID"] = userId
    }
    return config
})

// Uploads
export const uploadCatalog = (file: File) => uploadFile(file, "catalog")
export const uploadReviews = (file: File) => uploadFile(file, "reviews")
export const uploadPricing = (file: File) => uploadFile(file, "pricing")
export const uploadCompetitors = (file: File) => uploadFile(file, "competitors")

export const getUploadStatus = (): Promise<Record<string, boolean>> =>
    api.get("/upload/status").then(r => r.data)

function uploadFile(file: File, type: string): Promise<UploadResult> {
    const form = new FormData()
    form.append("file", file)
    return api.post(`/upload/${type}`, form, {
        headers: { "Content-Type": "multipart/form-data" },
    }).then(r => r.data)
}

// Research
export const startResearch = (
    query: string,
    mode: string
): Promise<{
    session_id: string | null
    user_id?: string
    needs_clarification?: boolean
    clarification_question?: string
}> =>
    api.post("/research/query", { query, mode }).then(r => r.data)

export const getHistory = (): Promise<ResearchSession[]> =>
    api.get("/research/history").then(r => r.data)

export const getReport = (id: string): Promise<ResearchSession> =>
    api.get(`/research/report/${id}`).then(r => r.data)

// Memory
export const getPreferences = (): Promise<UserPreferences> =>
    api.get("/memory/preferences").then(r => r.data)

export const updatePreferences = (prefs: Partial<UserPreferences>): Promise<UserPreferences> =>
    api.patch("/memory/preferences", prefs).then(r => r.data)

// Shopify
export const getShopifyStatus = (): Promise<ShopifyStatus> =>
    api.get("/shopify/status").then(r => r.data)

export const triggerShopifySync = (): Promise<ShopifyStatus> =>
    api.post("/shopify/sync").then(r => r.data)

export const disconnectShopify = () =>
    api.delete("/shopify/disconnect").then(r => r.data)

export const connectShopify = (shop: string, userId: string) => {
    const width = 600
    const height = 800
    const left = window.screenX + (window.outerWidth - width) / 2
    const top = window.screenY + (window.outerHeight - height) / 2
    const popup = window.open(
        `${API_URL}/api/shopify/auth?shop=${encodeURIComponent(shop)}&user_id=${encodeURIComponent(userId)}`,
        "shopify-auth",
        `width=${width},height=${height},left=${left},top=${top},status=no,menubar=no,toolbar=no,popup=yes,scrollbars=yes`
    )
    popup?.focus()
    return popup
}
