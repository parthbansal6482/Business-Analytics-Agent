import { useQuery } from "@tanstack/react-query"
import { getHistory } from "../lib/api"
import type { ResearchSession } from "../lib/types"

export function useHistory() {
    const query = useQuery<ResearchSession[]>({
        queryKey: ["research-history"],
        queryFn: getHistory,
        retry: false,
        refetchOnWindowFocus: false,
        staleTime: 30_000,
    })

    return {
        sessions: query.data ?? [],
        isLoading: query.isLoading,
        error: query.error,
        refetch: query.refetch,
    }
}
