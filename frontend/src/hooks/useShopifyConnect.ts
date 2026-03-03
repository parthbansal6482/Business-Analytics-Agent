import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import { getShopifyStatus, triggerShopifySync } from "../lib/api"
import type { ShopifyStatus } from "../lib/types"

export function useShopifyConnect() {
    const queryClient = useQueryClient()

    const statusQuery = useQuery<ShopifyStatus>({
        queryKey: ["shopify-status"],
        queryFn: getShopifyStatus,
        retry: false,
        refetchOnWindowFocus: false,
    })

    const syncMutation = useMutation({
        mutationFn: triggerShopifySync,
        onSuccess: () =>
            queryClient.invalidateQueries({ queryKey: ["shopify-status"] }),
    })

    return {
        status: statusQuery.data,
        isLoading: statusQuery.isLoading,
        isConnected: statusQuery.data?.connected ?? false,
        syncCounts: {
            products: statusQuery.data?.products_synced ?? 0,
            orders: statusQuery.data?.orders_synced ?? 0,
            reviews: statusQuery.data?.reviews_synced ?? 0,
        },
        triggerSync: syncMutation.mutate,
        isSyncing: syncMutation.isPending,
    }
}
