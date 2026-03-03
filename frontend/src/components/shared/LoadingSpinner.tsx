interface LoadingSpinnerProps {
    size?: number
    className?: string
}

export default function LoadingSpinner({ size = 20, className = "" }: LoadingSpinnerProps) {
    return (
        <div
            className={`animate-spin rounded-full border-2 border-[#b7860b]/20 border-t-[#b7860b] ${className}`}
            style={{ width: size, height: size, flexShrink: 0 }}
            role="status"
            aria-label="Loading"
        />
    )
}
