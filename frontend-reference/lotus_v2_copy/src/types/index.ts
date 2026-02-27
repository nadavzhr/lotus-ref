export type LineStatus = "valid" | "warning" | "error" | "comment" | "conflict"

export interface ConfigLine {
  id: number
  text: string
  status: LineStatus
}

export type ProblemType = "error" | "warning" | "conflict"

export interface Problem {
  id: number
  type: ProblemType
  message: string
  line: number
  file: string
}

export interface LogEntry {
  time: string
  level: "INFO" | "WARN" | "ERROR"
  message: string
}

export interface ChatMessage {
  id: number
  role: "user" | "assistant"
  content: string
  timestamp: Date
}

export type DocumentTab = "af" | "mutex"

export type LayoutVersion = "A" | "B" | "C"
