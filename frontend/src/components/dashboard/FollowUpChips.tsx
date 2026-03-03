interface FollowUpChipsProps {
    suggestions: string[]
    onSelect: (text: string) => void
}

export default function FollowUpChips({ suggestions, onSelect }: FollowUpChipsProps) {
    if (!suggestions.length) return null

    return (
        <div className="animate-fade-in">
            <p className="text-xs text-[#8a7e60] mb-3 font-medium uppercase tracking-wide">
                Continue your analysis
            </p>
            <div className="flex flex-wrap gap-2">
                {suggestions.map((suggestion) => (
                    <button
                        key={suggestion}
                        onClick={() => onSelect(suggestion)}
                        className="flex items-center gap-2 px-4 py-2 rounded-full bg-[#F0E6C8] text-[#b7860b] border border-[#e5e2db] text-sm font-medium transition-all hover:bg-[#e5d4a8] hover:border-[#b7860b]/50"
                    >
                        {suggestion}
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>arrow_forward</span>
                    </button>
                ))}
            </div>
        </div>
    )
}
