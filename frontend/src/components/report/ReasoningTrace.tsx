import { useState } from "react"

interface Props {
    trace: string[]
}

export default function ReasoningTrace({ trace }: Props) {
    const [expanded, setExpanded] = useState(false)

    if (!trace || trace.length === 0) return null

    return (
        <div className="border-t border-[#e5e2db] px-8 py-4">
            <button
                onClick={() => setExpanded(!expanded)}
                className="flex items-center gap-2 text-sm text-[#8a7e60] 
                   hover:text-[#181611] transition-colors focus:outline-none"
            >
                <span className="font-mono text-xs">{expanded ? "▼" : "▶"}</span>
                <span className="font-mono text-xs tracking-wide uppercase">
                    {expanded ? "Hide" : "View"} reasoning trace
                </span>
            </button>

            {expanded && (
                <div className="mt-4 space-y-3">
                    {trace.map((step, i) => (
                        <div key={i} className="bg-[#fafaf7] rounded-md p-4 border border-[#e5e2db]">
                            <pre className="text-xs font-mono text-[#8a7e60] 
                              whitespace-pre-wrap leading-relaxed overflow-x-auto">
                                {step}
                            </pre>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
