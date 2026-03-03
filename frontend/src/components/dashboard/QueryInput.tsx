import { useRef, useEffect } from "react"
import LoadingSpinner from "../shared/LoadingSpinner"

interface QueryInputProps {
    value: string
    onChange: (v: string) => void
    onSubmit: () => void
    disabled: boolean
}

export default function QueryInput({ value, onChange, onSubmit, disabled }: QueryInputProps) {
    const textareaRef = useRef<HTMLTextAreaElement>(null)

    // Auto-resize textarea
    useEffect(() => {
        const el = textareaRef.current
        if (!el) return
        el.style.height = "auto"
        el.style.height = `${Math.max(el.scrollHeight, 120)}px`
    }, [value])

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
            e.preventDefault()
            if (!disabled && value.trim()) onSubmit()
        }
    }

    return (
        <div className="relative">
            <div className={`bg-[#f5f0e8] border rounded-xl transition-all ${!disabled ? "border-[#e5e2db] focus-within:border-[#b7860b] focus-within:ring-2 focus-within:ring-[#b7860b]/20" : "border-[#e5e2db]"}`}>
                <textarea
                    ref={textareaRef}
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    onKeyDown={handleKeyDown}
                    disabled={disabled}
                    placeholder="Ask anything about your business… e.g. 'Why is my best-selling SKU underperforming?'"
                    rows={4}
                    className="w-full bg-transparent p-4 text-[#181611] placeholder-[#8a7e60] text-sm leading-relaxed resize-none outline-none disabled:opacity-50 disabled:cursor-not-allowed"
                    style={{ minHeight: 120, maxHeight: 400 }}
                />

                <div className="flex items-center justify-between px-4 pb-3">
                    <span className="text-xs text-[#8a7e60]">
                        <kbd className="px-1.5 py-0.5 rounded bg-white border border-[#e5e2db] text-[10px] font-mono">⌘</kbd>
                        <span className="mx-1">+</span>
                        <kbd className="px-1.5 py-0.5 rounded bg-white border border-[#e5e2db] text-[10px] font-mono">↵</kbd>
                        <span className="ml-1">to submit</span>
                    </span>

                    <button
                        onClick={onSubmit}
                        disabled={disabled || !value.trim()}
                        className="flex items-center gap-2 px-5 py-2 rounded-lg bg-[#b7860b] text-white text-sm font-bold hover:bg-[#9a7009] transition-colors shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {disabled ? (
                            <>
                                <LoadingSpinner size={16} />
                                Analyzing…
                            </>
                        ) : (
                            <>
                                <span className="material-symbols-outlined" style={{ fontSize: 18 }}>search</span>
                                Analyze
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}
