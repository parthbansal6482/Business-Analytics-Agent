import { create } from "zustand"
import type { ResearchMode, ResearchReport, ProgressEvent, AgentStep, StepStatus } from "../lib/types"

interface SessionStore {
    query: string
    mode: ResearchMode
    sessionId: string | null
    isLoading: boolean
    progress: Record<AgentStep, StepStatus>
    progressLabels: Record<AgentStep, string>
    report: ResearchReport | null
    needsClarification: boolean
    clarificationQuestion: string
    totalTokensUsed: number
    totalCost: number
    error: string | null

    setQuery: (q: string) => void
    setMode: (m: ResearchMode) => void
    setLoading: (v: boolean) => void
    updateProgress: (event: ProgressEvent) => void
    setReport: (r: ResearchReport) => void
    setClarification: (question: string) => void
    addTokens: (n: number) => void
    addCost: (c: number) => void
    setError: (msg: string | null) => void
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
    analyze: "pending",
    report: "pending",
    __done__: "pending",
}

const defaultProgressLabels: Record<AgentStep, string> = {
    intent: "",
    clarify: "",
    memory: "",
    retrieve: "",
    sentiment: "",
    pricing: "",
    competitor: "",
    synthesize: "",
    analyze: "",
    report: "",
    __done__: "",
}

export const useSessionStore = create<SessionStore>((set) => ({
    query: "",
    mode: "quick",
    sessionId: null,
    isLoading: false,
    progress: defaultProgress,
    progressLabels: defaultProgressLabels,
    report: null,
    needsClarification: false,
    clarificationQuestion: "",
    totalTokensUsed: 0,
    totalCost: 0,
    error: null,

    setQuery: (query) => set({ query }),
    setMode: (mode) => set({ mode }),
    setLoading: (isLoading) => set({ isLoading }),
    updateProgress: ({ step, status, label }) =>
        set((s) => ({
            progress: { ...s.progress, [step]: status },
            progressLabels: { ...s.progressLabels, [step]: label || s.progressLabels[step] },
        })),
    setReport: (report) => set({ report, isLoading: false }),
    setClarification: (q) => set({ needsClarification: true, clarificationQuestion: q }),
    addTokens: (n) => set((s) => ({ totalTokensUsed: s.totalTokensUsed + n })),
    addCost: (c) => set((s) => ({ totalCost: s.totalCost + c })),
    setError: (error) => set({ error }),
    reset: () =>
        set({
            progress: defaultProgress,
            progressLabels: defaultProgressLabels,
            report: null,
            isLoading: false,
            needsClarification: false,
            clarificationQuestion: "",
            error: null,
        }),
}))
