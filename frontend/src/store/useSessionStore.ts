import { create } from "zustand"
import type { ResearchMode, ResearchReport, ProgressEvent, AgentStep, StepStatus } from "../lib/types"

interface SessionStore {
    query: string
    mode: ResearchMode
    sessionId: string | null
    isLoading: boolean
    progress: Record<AgentStep, StepStatus>
    report: ResearchReport | null
    needsClarification: boolean
    clarificationQuestion: string
    totalTokensUsed: number
    totalCost: number

    setQuery: (q: string) => void
    setMode: (m: ResearchMode) => void
    setLoading: (v: boolean) => void
    updateProgress: (event: ProgressEvent) => void
    setReport: (r: ResearchReport) => void
    setClarification: (question: string) => void
    addTokens: (n: number) => void
    addCost: (c: number) => void
    reset: () => void
}

const defaultProgress: Record<AgentStep, StepStatus> = {
    intent: "pending",
    clarify: "pending",
    memory: "pending",
    retrieve: "pending",
    sentiment: "pending",
    pricing: "pending",
    competitor: "pending",
    synthesize: "pending",
    report: "pending",
}

export const useSessionStore = create<SessionStore>((set) => ({
    query: "",
    mode: "quick",
    sessionId: null,
    isLoading: false,
    progress: defaultProgress,
    report: null,
    needsClarification: false,
    clarificationQuestion: "",
    totalTokensUsed: 0,
    totalCost: 0,

    setQuery: (query) => set({ query }),
    setMode: (mode) => set({ mode }),
    setLoading: (isLoading) => set({ isLoading }),
    updateProgress: ({ step, status }) =>
        set((s) => ({ progress: { ...s.progress, [step]: status } })),
    setReport: (report) => set({ report, isLoading: false }),
    setClarification: (q) => set({ needsClarification: true, clarificationQuestion: q }),
    addTokens: (n) => set((s) => ({ totalTokensUsed: s.totalTokensUsed + n })),
    addCost: (c) => set((s) => ({ totalCost: s.totalCost + c })),
    reset: () =>
        set({
            progress: defaultProgress,
            report: null,
            isLoading: false,
            needsClarification: false,
            clarificationQuestion: "",
        }),
}))
