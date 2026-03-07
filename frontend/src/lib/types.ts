export type ResearchMode = "quick" | "deep"
export type Priority = "High" | "Medium" | "Low"
export type DataCompleteness = "High" | "Moderate" | "Low"
export type AnalysisStyle = "margin-focused" | "growth-focused" | "gmv-focused"

export interface ActionItem {
    action: string
    priority: Priority
    expected_impact: string
}

export interface SentimentBreakdown {
    positive_pct: number
    neutral_pct: number
    negative_pct: number
    top_complaints: string[]
    feature_requests: string[]
}

export interface PricingAnalysis {
    your_price: number
    competitor_avg: number
    gap_pct: number
    recommendation: string
}

export interface KeyMetrics {
    revenue_impact: string
    rating_change: string
    price_gap_pct: number
}

export interface ResearchReport {
    executive_summary: string
    mode: ResearchMode
    key_metrics: KeyMetrics
    sentiment_breakdown: SentimentBreakdown
    pricing_analysis: PricingAnalysis
    competitive_gaps: string[]
    root_cause: string
    recommended_actions: ActionItem[]
    confidence_score: number
    data_completeness: DataCompleteness
    cost_usd: number
    tokens_used: number
    follow_up_suggestions: string[]
    duration_seconds: number
    error?: string
    is_simple?: boolean
    reasoning_trace?: string[]
}

export interface ResearchSession {
    id: string
    session_id: string
    query: string
    mode: ResearchMode
    report: ResearchReport
    created_at: string
}

export interface UserPreferences {
    preferred_kpis: string[]
    marketplaces: string[]
    categories_of_interest: string[]
    analysis_style: AnalysisStyle
}

export interface ShopifyStatus {
    connected: boolean
    shop_domain: string
    products_synced: number
    orders_synced: number
    reviews_synced: number
    last_sync: string
}

export interface UploadResult {
    rows_loaded: number
    data_type: string
}

export type AgentStep =
    | "intent"
    | "clarify"
    | "memory"
    | "retrieve"
    | "sentiment"
    | "pricing"
    | "competitor"
    | "synthesize"
    | "report"
    | "__done__"

export type StepStatus = "pending" | "running" | "done" | "error"

export interface ProgressEvent {
    step: AgentStep
    status: StepStatus
    label: string
}
