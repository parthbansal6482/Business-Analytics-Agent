import { useState, useRef, useEffect } from "react"
import axios from "axios"
import { API_URL } from "../../config"

interface Message {
    role: "user" | "assistant"
    content: string
    report?: Record<string, unknown>
    timestamp: Date
}

interface ChatPanelProps {
    sessionId: string
    userId: string
    initialReport: Record<string, unknown>
    onReportUpdate: (report: Record<string, unknown>) => void
}

export default function ChatPanel({ sessionId, userId, initialReport, onReportUpdate }: ChatPanelProps) {
    const [messages, setMessages] = useState<Message[]>([])
    const [input, setInput] = useState("")
    const [isLoading, setIsLoading] = useState(false)
    const bottomRef = useRef<HTMLDivElement>(null)

    // Auto-scroll on new messages
    useEffect(() => {
        bottomRef.current?.scrollIntoView({ behavior: "smooth" })
    }, [messages, isLoading])

    // First message on mount
    useEffect(() => {
        const summary = (initialReport as Record<string, unknown>)?.executive_summary as string || "Analysis complete."
        setMessages([{
            role: "assistant",
            content: `Analysis complete. ${summary} Ask me anything about it.`,
            report: initialReport,
            timestamp: new Date(),
        }])
    }, []) // intentionally only on mount

    const handleSend = async () => {
        if (!input.trim() || isLoading) return

        const userMessage: Message = {
            role: "user",
            content: input.trim(),
            timestamp: new Date(),
        }
        const newMessages = [...messages, userMessage]
        setMessages(newMessages)
        setInput("")
        setIsLoading(true)

        // Build conversation_history: use executive_summary for report messages
        const history = newMessages.map((m) => ({
            role: m.role,
            content: m.report
                ? String((m.report as Record<string, unknown>)?.executive_summary || m.content)
                : m.content,
        }))

        try {
            const res = await axios.post(`${API_URL}/api/research/chat`, {
                query: userMessage.content,
                session_id: sessionId,
                user_id: userId,
                conversation_history: history,
                report_context: initialReport,
            }, {
                headers: {
                    "Content-Type": "application/json",
                    "X-User-ID": userId,
                },
            })

            const data = res.data as {
                chat_answer: string
                report: Record<string, unknown> | null
                is_followup: boolean
            }

            const assistantMessage: Message = {
                role: "assistant",
                content: data.chat_answer,
                report: data.report || undefined,
                timestamp: new Date(),
            }
            setMessages((prev) => [...prev, assistantMessage])

            // If fresh report returned (not a follow-up), update the left panel
            if (data.report && !data.is_followup) {
                onReportUpdate(data.report)
            }
        } catch {
            setMessages((prev) => [...prev, {
                role: "assistant",
                content: "Sorry, something went wrong. Please try again.",
                timestamp: new Date(),
            }])
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault()
            handleSend()
        }
    }

    return (
        <div className="flex flex-col h-full bg-[#FAFAF7]">
            {/* Header */}
            <div className="px-4 py-3 border-b border-[#e5e2db] bg-white">
                <h3 className="font-serif font-semibold text-[#181611] text-base">Chat</h3>
                <p className="text-xs text-[#8a7e60]">Ask follow-up questions about your report</p>
            </div>

            {/* Messages area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {messages.map((msg, i) => (
                    <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                        <div className="flex flex-col max-w-[85%]">
                            <div
                                className={
                                    msg.role === "user"
                                        ? "bg-[#b7860b] text-white rounded-2xl rounded-br-sm px-4 py-2 text-sm"
                                        : "bg-white border border-[#e5e2db] shadow-sm rounded-2xl rounded-bl-sm px-4 py-2 text-sm text-[#181611]"
                                }
                            >
                                <p className="whitespace-pre-wrap">{msg.content}</p>
                                {/* View updated report button for follow-up reports */}
                                {msg.report && msg.role === "assistant" && i > 0 && (
                                    <button
                                        onClick={() => msg.report && onReportUpdate(msg.report)}
                                        className="mt-2 text-xs text-[#b7860b] hover:text-[#9a7009] font-medium flex items-center gap-1"
                                    >
                                        View updated report →
                                    </button>
                                )}
                            </div>
                            <span className="text-xs opacity-40 mt-1 px-1">
                                {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                            </span>
                        </div>
                    </div>
                ))}

                {/* Loading indicator */}
                {isLoading && (
                    <div className="flex justify-start">
                        <div className="bg-white border border-[#e5e2db] shadow-sm rounded-2xl rounded-bl-sm px-4 py-3">
                            <div className="flex space-x-1.5">
                                <div className="w-2 h-2 rounded-full bg-[#b7860b]/40 animate-bounce" style={{ animationDelay: "0ms" }} />
                                <div className="w-2 h-2 rounded-full bg-[#b7860b]/40 animate-bounce" style={{ animationDelay: "150ms" }} />
                                <div className="w-2 h-2 rounded-full bg-[#b7860b]/40 animate-bounce" style={{ animationDelay: "300ms" }} />
                            </div>
                        </div>
                    </div>
                )}

                <div ref={bottomRef} />
            </div>

            {/* Input area */}
            <div className="px-4 py-3 border-t border-[#e5e2db] bg-white">
                <div className="flex items-center gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        onKeyDown={handleKeyDown}
                        placeholder="Ask a follow-up..."
                        disabled={isLoading}
                        className="flex-1 border border-[#e5e2db] rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#b7860b]/30 bg-[#FAFAF7] text-[#181611] placeholder-[#8a7e60]"
                    />
                    <button
                        onClick={handleSend}
                        disabled={isLoading || !input.trim()}
                        className="bg-[#b7860b] hover:bg-[#9a7009] disabled:opacity-40 text-white rounded-xl p-2 transition-colors"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <line x1="22" y1="2" x2="11" y2="13" />
                            <polygon points="22 2 15 22 11 13 2 9 22 2" />
                        </svg>
                    </button>
                </div>
            </div>
        </div>
    )
}
