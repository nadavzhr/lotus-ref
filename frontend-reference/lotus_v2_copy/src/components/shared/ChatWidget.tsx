import { useRef, useEffect } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Bot, Send, User, X, Sparkles } from "lucide-react"
import { useChat } from "@/hooks/useChat"

interface ChatWidgetProps {
  onClose?: () => void
  showHeader?: boolean
}

export function ChatWidget({ onClose, showHeader = true }: ChatWidgetProps) {
  const { messages, input, setInput, isTyping, handleSend } = useChat()
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, isTyping])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex flex-col h-full bg-background">
      {showHeader && (
        <div className="flex items-center justify-between px-3 py-2 border-b shrink-0">
          <div className="flex items-center gap-2">
            <div className="flex items-center justify-center w-6 h-6 rounded-md bg-primary/10">
              <Sparkles className="h-3.5 w-3.5 text-primary" />
            </div>
            <div>
              <h3 className="text-xs font-semibold">AI Assistant</h3>
              <p className="text-[9px] text-muted-foreground">Powered by Copilot</p>
            </div>
          </div>
          {onClose && (
            <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={onClose}>
              <X className="h-3.5 w-3.5" />
            </Button>
          )}
        </div>
      )}

      <ScrollArea className="flex-1 min-h-0">
        <div ref={scrollRef} className="p-3 space-y-3">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <div
                className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center ${
                  msg.role === "assistant"
                    ? "bg-primary/10 text-primary"
                    : "bg-accent text-accent-foreground"
                }`}
              >
                {msg.role === "assistant" ? (
                  <Bot className="h-3.5 w-3.5" />
                ) : (
                  <User className="h-3.5 w-3.5" />
                )}
              </div>
              <div
                className={`max-w-[85%] rounded-lg px-3 py-2 text-xs leading-relaxed ${
                  msg.role === "assistant"
                    ? "bg-muted text-foreground"
                    : "bg-primary text-primary-foreground"
                }`}
              >
                {msg.content}
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex gap-2">
              <div className="shrink-0 w-6 h-6 rounded-full flex items-center justify-center bg-primary/10 text-primary">
                <Bot className="h-3.5 w-3.5" />
              </div>
              <div className="bg-muted rounded-lg px-3 py-2">
                <div className="flex gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:0ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:150ms]" />
                  <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/40 animate-bounce [animation-delay:300ms]" />
                </div>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      <div className="border-t p-2 shrink-0">
        <div className="flex gap-1.5">
          <Input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about configs, nets..."
            className="h-8 text-xs flex-1"
            disabled={isTyping}
          />
          <Button
            size="sm"
            className="h-8 w-8 p-0 shrink-0"
            onClick={handleSend}
            disabled={!input.trim() || isTyping}
          >
            <Send className="h-3.5 w-3.5" />
          </Button>
        </div>
        <p className="text-[9px] text-muted-foreground mt-1.5 text-center">
          AI may produce inaccurate results. Verify critical values.
        </p>
      </div>
    </div>
  )
}
