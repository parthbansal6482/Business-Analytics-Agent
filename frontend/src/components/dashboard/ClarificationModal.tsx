import { useState } from "react"
import { useSessionStore } from "../../store/useSessionStore"

interface ClarificationModalProps {
    onSubmit: (answer: string) => void
}

export default function ClarificationModal({ onSubmit }: ClarificationModalProps) {
    const { clarificationQuestion } = useSessionStore()
    const [answer, setAnswer] = useState("")

    const handleSubmit = () => {
        if (answer.trim()) onSubmit(answer.trim())
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/20 backdrop-blur-sm animate-fade-in">
            <div className="bg-white rounded-xl shadow-2xl w-full max-w-md border border-[#e5e2db] overflow-hidden">
                {/* Header */}
                <div className="bg-[#b7860b]/5 px-6 py-5 border-b border-[#b7860b]/10">
                    <h3 className="text-xl font-serif font-bold text-[#181611]">One quick question</h3>
                    <p className="text-sm text-[#8a7e60] mt-1">To refine your research results.</p>
                </div>

                {/* Body */}
                <div className="p-6 space-y-5">
                    <p className="text-[#181611] text-sm font-medium">{clarificationQuestion}</p>
                    <textarea
                        value={answer}
                        onChange={(e) => setAnswer(e.target.value)}
                        placeholder="Type your answer here…"
                        rows={3}
                        autoFocus
                        className="w-full px-4 py-3 rounded-lg border border-[#e5e2db] bg-[#FAFAF7] text-sm text-[#181611] placeholder-[#8a7e60] resize-none outline-none focus:border-[#b7860b] focus:ring-2 focus:ring-[#b7860b]/20 transition-all"
                        onKeyDown={(e) => {
                            if ((e.metaKey || e.ctrlKey) && e.key === "Enter") handleSubmit()
                        }}
                    />
                </div>

                {/* Footer */}
                <div className="px-6 py-4 bg-[#FAFAF7] border-t border-[#e5e2db] flex justify-end gap-3">
                    <button
                        onClick={() => onSubmit("")}
                        className="px-4 py-2 rounded-lg text-sm font-medium text-[#8a7e60] hover:text-[#181611] transition-colors"
                    >
                        Analyze Everything
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={!answer.trim()}
                        className="px-5 py-2 rounded-lg text-sm font-bold bg-[#b7860b] text-white hover:bg-[#9a7009] shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        Continue Research
                    </button>
                </div>
            </div>
        </div>
    )
}
