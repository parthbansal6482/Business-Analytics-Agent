interface ExampleChipsProps {
    onSelect: (text: string) => void
}

const EXAMPLE_QUERIES = [
    "Why is this product underperforming?",
    "Top complaints for my best-selling SKU",
    "What features do competitors have that I don't?",
    "Summarize review sentiment",
    "Which products should I discount?",
    "What's driving my return rate?",
]

export default function ExampleChips({ onSelect }: ExampleChipsProps) {
    return (
        <div>
            <p className="text-xs text-[#8a7e60] mb-3 font-medium uppercase tracking-wide">Try asking</p>
            <div className="flex flex-wrap gap-2 sm:flex-nowrap sm:overflow-x-auto sm:pb-1">
                {EXAMPLE_QUERIES.map((query) => (
                    <button
                        key={query}
                        onClick={() => onSelect(query)}
                        className="flex-shrink-0 px-4 py-2 rounded-full bg-[#F0E6C8] text-[#b7860b] border border-[#e5e2db] text-sm font-medium transition-all hover:bg-[#e5d4a8] hover:border-[#b7860b]/50 whitespace-nowrap"
                    >
                        {query}
                    </button>
                ))}
            </div>
        </div>
    )
}
