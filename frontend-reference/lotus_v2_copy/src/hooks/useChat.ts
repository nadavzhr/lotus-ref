import { useState, useCallback } from "react"
import type { ChatMessage } from "@/types"
import { initialChatMessages, getStubResponse } from "@/services/mockData"

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialChatMessages)
  const [input, setInput] = useState("")
  const [isTyping, setIsTyping] = useState(false)

  const handleSend = useCallback(() => {
    const text = input.trim()
    if (!text) return

    const userMsg: ChatMessage = {
      id: Date.now(),
      role: "user",
      content: text,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput("")
    setIsTyping(true)

    setTimeout(() => {
      const aiMsg: ChatMessage = {
        id: Date.now() + 1,
        role: "assistant",
        content: getStubResponse(text),
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, aiMsg])
      setIsTyping(false)
    }, 800 + Math.random() * 600)
  }, [input])

  return { messages, input, setInput, isTyping, handleSend }
}
