import { useState } from "react"
import { useUserStore } from "../../store/useUserStore"
import { updatePreferences } from "../../lib/api"

const KPI_OPTIONS = [
    "Conversion Rate", "AOV", "Customer Retention", "Profit Margin",
    "CAC", "LTV", "Return Rate", "GMV",
]

const MARKETPLACE_OPTIONS = [
    "Amazon US", "Etsy", "Google Shopping", "TikTok Shop", "eBay", "Walmart",
]

const ANALYSIS_STYLE_OPTIONS: Array<{ value: "margin-focused" | "growth-focused" | "gmv-focused"; label: string; desc: string }> = [
    { value: "margin-focused", label: "Margin-Focused", desc: "Optimize for profitability" },
    { value: "growth-focused", label: "Growth-Focused", desc: "Prioritize revenue growth" },
    { value: "gmv-focused", label: "GMV-Focused", desc: "Maximize gross merchandise value" },
]

export default function PreferenceSetup() {
    const { preferences, setPreferences } = useUserStore()
    const [saving, setSaving] = useState(false)

    const toggleKpi = (kpi: string) => {
        const current = preferences.preferred_kpis
        const next = current.includes(kpi)
            ? current.filter((k) => k !== kpi)
            : [...current, kpi]
        setPreferences({ preferred_kpis: next })
        savePrefs({ preferred_kpis: next })
    }

    const toggleMarketplace = (mp: string) => {
        const current = preferences.marketplaces
        const next = current.includes(mp)
            ? current.filter((m) => m !== mp)
            : [...current, mp]
        setPreferences({ marketplaces: next })
        savePrefs({ marketplaces: next })
    }

    const setStyle = (style: typeof preferences.analysis_style) => {
        setPreferences({ analysis_style: style })
        savePrefs({ analysis_style: style })
    }

    const savePrefs = async (partial: Partial<typeof preferences>) => {
        setSaving(true)
        try {
            await updatePreferences(partial)
        } catch {
            // ignore if backend unavailable
        } finally {
            setSaving(false)
        }
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[#e5e2db] pb-4">
                <h2 className="text-3xl font-serif font-bold text-[#181611]">Research Preferences</h2>
                <div className="flex items-center gap-2">
                    {saving && (
                        <span className="text-xs text-[#8a7e60] animate-pulse">Saving…</span>
                    )}
                    <span className="text-sm text-[#8a7e60]">Step 2 of 2</span>
                </div>
            </div>

            <div className="flex flex-col lg:flex-row gap-8">
                {/* KPIs */}
                <div className="flex-1 bg-white p-6 rounded-xl border border-[#e5e2db]">
                    <div className="flex items-center gap-2 mb-3">
                        <span className="material-symbols-outlined text-[#b7860b]" style={{ fontSize: 22 }}>monitoring</span>
                        <h4 className="font-bold text-lg text-[#181611]">Focus KPIs</h4>
                    </div>
                    <p className="text-sm text-[#8a7e60] mb-5">Select the metrics that matter most to your current goals.</p>
                    <div className="flex flex-wrap gap-3">
                        {KPI_OPTIONS.map((kpi) => {
                            const selected = preferences.preferred_kpis.includes(kpi)
                            return (
                                <button
                                    key={kpi}
                                    onClick={() => toggleKpi(kpi)}
                                    className={`px-4 py-2 rounded-full border text-sm font-medium transition-all shadow-sm ${selected
                                        ? "bg-[#b7860b] text-white border-[#b7860b]"
                                        : "bg-white text-[#181611] border-[#e5e2db] hover:border-[#b7860b]/50 hover:bg-[#b7860b]/5"
                                        }`}
                                >
                                    {kpi}
                                </button>
                            )
                        })}
                    </div>
                </div>

                {/* Marketplaces */}
                <div className="flex-1 bg-white p-6 rounded-xl border border-[#e5e2db]">
                    <div className="flex items-center gap-2 mb-3">
                        <span className="material-symbols-outlined text-[#b7860b]" style={{ fontSize: 22 }}>public</span>
                        <h4 className="font-bold text-lg text-[#181611]">Target Marketplaces</h4>
                    </div>
                    <p className="text-sm text-[#8a7e60] mb-5">Where should the AI look for trends and competitor data?</p>
                    <div className="flex flex-wrap gap-3">
                        {MARKETPLACE_OPTIONS.map((mp) => {
                            const selected = preferences.marketplaces.includes(mp)
                            return (
                                <button
                                    key={mp}
                                    onClick={() => toggleMarketplace(mp)}
                                    className={`px-4 py-2 rounded-full border text-sm font-medium transition-all shadow-sm ${selected
                                        ? "bg-[#b7860b] text-white border-[#b7860b]"
                                        : "bg-white text-[#181611] border-[#e5e2db] hover:border-[#b7860b]/50 hover:bg-[#b7860b]/5"
                                        }`}
                                >
                                    {mp}
                                </button>
                            )
                        })}
                    </div>
                </div>
            </div>

            {/* Analysis Style */}
            <div className="bg-white p-6 rounded-xl border border-[#e5e2db]">
                <div className="flex items-center gap-2 mb-3">
                    <span className="material-symbols-outlined text-[#b7860b]" style={{ fontSize: 22 }}>tune</span>
                    <h4 className="font-bold text-lg text-[#181611]">Analysis Style</h4>
                </div>
                <p className="text-sm text-[#8a7e60] mb-5">How should the AI frame its recommendations?</p>
                <div className="flex flex-col sm:flex-row gap-3">
                    {ANALYSIS_STYLE_OPTIONS.map((opt) => {
                        const selected = preferences.analysis_style === opt.value
                        return (
                            <button
                                key={opt.value}
                                onClick={() => setStyle(opt.value)}
                                className={`flex-1 p-4 rounded-xl border text-left transition-all ${selected
                                    ? "bg-[#b7860b]/10 border-[#b7860b] text-[#181611]"
                                    : "bg-[#FAFAF7] border-[#e5e2db] text-[#181611] hover:border-[#b7860b]/50"
                                    }`}
                            >
                                <div className="flex items-center gap-2 mb-1">
                                    {selected && (
                                        <span className="w-2 h-2 rounded-full bg-[#b7860b]" />
                                    )}
                                    <span className="text-sm font-semibold">{opt.label}</span>
                                </div>
                                <span className="text-xs text-[#8a7e60]">{opt.desc}</span>
                            </button>
                        )
                    })}
                </div>
            </div>
        </div>
    )
}
