export type LineStatusValue = "ok" | "warning" | "error" | "comment" | "conflict"

export interface ConflictInfo {
  conflicting_positions: number[]
  shared_nets: string[]
}

export interface DocumentLine {
  position: number
  raw_text: string
  status: LineStatusValue
  errors: string[]
  warnings: string[]
  has_data: boolean
  data?: Record<string, unknown>
  conflict_info: ConflictInfo | null
}

export interface StatusCounts {
  ok?: number
  warning?: number
  error?: number
  comment?: number
  conflict?: number
}

export interface DocumentSummary {
  doc_id: string
  doc_type: "af" | "mutex"
  file_path: string
  total_lines: number
  status_counts: StatusCounts
  can_undo: boolean
  can_redo: boolean
}

export interface MutexEntry {
  net_name: string
  template_name: string
  regex_mode: boolean
  match_count: number
}

export interface MutexSession {
  template: string | null
  regex_mode: boolean
  num_active: number
  fev: string
  mutexed_entries: MutexEntry[]
  active_entries: MutexEntry[]
}

export interface QueryNetsResponse {
  nets: string[]
  templates: string[]
}

export interface HydrateSessionResponse {
  position: number
  doc_type: "af" | "mutex"
  data: Record<string, unknown>
}

export interface MutationResponse {
  action: string
  position: number
  position2?: number
  line?: DocumentLine
  can_undo: boolean
  can_redo: boolean
}

export interface SaveResponse {
  status: string
  file_path: string
}
