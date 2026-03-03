import type { ResearchMode } from "../../lib/types"

interface ModeToggleProps {
    mode: ResearchMode
    onChange: (m: ResearchMode) => void
}

export default function ModeToggle({ mode, onChange }: ModeToggleProps) {
    return (
        <div className="flex flex-col items-center gap-2">
            <div className="flex items-center p-1 bg-[#f5f0e8] rounded-xl border border-[#e5e2db]">
                <button
                    onClick={() => onChange("quick")}
                    className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold transition-all ${mode === "quick"
                            ? "bg-[#b7860b] text-white shadow-sm"
                            : "text-[#8a7e60] hover:text-[#181611]"
                        }`}
                >
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>bolt</span>
                    Quick Scan
                </button>
                <button
                    onClick={() => onChange("deep")}
                    className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold transition-all ${mode === "deep"
                            ? "bg-[#b7860b] text-white shadow-sm"
                            : "text-[#8a7e60] hover:text-[#181611]"
                        }`}
                >
                    <span className="material-symbols-outlined" style={{ fontSize: 18 }}>database</span>
                    Deep Dive
                </button>
            </div>
            <p className="text-xs text-[#8a7e60]">
                {mode === "quick"
                    ? "Fast analysis — results in ~30 seconds"
                    : "Comprehensive deep dive — 2-3 minutes, higher accuracy"}
            </p>
        </div>
    )
}
