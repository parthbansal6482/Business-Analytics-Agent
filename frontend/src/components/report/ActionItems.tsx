import type { ActionItem } from "../../lib/types"
import Badge from "../shared/Badge"

interface ActionItemsProps {
    actions: ActionItem[]
}

export default function ActionItems({ actions }: ActionItemsProps) {
    return (
        <div className="p-6 md:p-8">
            <div className="flex items-center gap-2 mb-5">
                <span className="material-symbols-outlined" style={{ fontSize: 20 }}>task_alt</span>
                <h3 className="text-sm font-semibold uppercase tracking-widest text-[#8a7e60]">Recommended Actions</h3>
            </div>

            <div className="space-y-3">
                {actions.map((action, i) => (
                    <div
                        key={i}
                        className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl border border-[#e5e2db] bg-white hover:shadow-sm transition-shadow border-l-4 border-l-[#b7860b]"
                    >
                        <div className="flex items-start gap-3">
                            <Badge variant={action.priority.toLowerCase() as "high" | "medium" | "low"} />
                            <p className="text-[#181611] text-sm font-medium leading-relaxed">{action.action}</p>
                        </div>
                        <div className="flex items-center gap-2 shrink-0 ml-auto">
                            <span className="text-[#8a7e60]">→</span>
                            <span className="text-sm text-[#8a7e60]">{action.expected_impact}</span>
                        </div>
                    </div>
                ))}
                {actions.length === 0 && (
                    <p className="text-sm text-[#8a7e60] italic">No recommended actions at this time.</p>
                )}
            </div>
        </div>
    )
}
