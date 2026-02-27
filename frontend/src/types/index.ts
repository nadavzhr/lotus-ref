/* ── Line statuses ─────────────────────────────────────────────────────── */
export type LineStatus = "ok" | "warning" | "error" | "comment" | "conflict"

/* ── Conflict info ────────────────────────────────────────────────────── */
export interface ConflictInfo {
  conflicting_positions: number[]
  shared_nets: string[]
}

/* ── Document line as returned by GET /api/documents/{id}/lines ─────── */
export interface DocumentLine {
  position: number
  raw_text: string
  status: LineStatus
  errors: string[]
  warnings: string[]
  has_data: boolean
  conflict_info: ConflictInfo | null
  data?: Record<string, unknown>
}

/* ── Document summary from GET /api/documents ──────────────────────── */
export interface DocumentSummary {
  doc_id: string
  doc_type: string
  file_path: string
  total_lines: number
  status_counts: Record<string, number>
  can_undo: boolean
  can_redo: boolean
}

/* ── Load request/response ─────────────────────────────────────────── */
export interface LoadRequest {
  doc_id: string
  file_path: string
  doc_type: "af" | "mutex"
}

export interface LoadResponse {
  doc_id: string
  doc_type: string
  file_path: string
  total_lines: number
  status_counts: Record<string, number>
  can_undo: boolean
  can_redo: boolean
}

/* ── Edit session (hydrate response) ──────────────────────────────── */
export interface EditSession {
  position: number
  doc_type: string
  data: Record<string, unknown>
}

/* ── Search result ────────────────────────────────────────────────── */
export interface SearchResult {
  doc_id: string
  matches: DocumentLine[]
}

/* ── NQS Query ────────────────────────────────────────────────────── */
export interface QueryNetsRequest {
  template?: string
  net_pattern: string
  template_regex?: boolean
  net_regex?: boolean
}

export interface QueryNetsResponse {
  nets: string[]
  templates: string[]
}

/* ── Problem (derived from line errors/warnings/conflicts) ─────────── */
export interface Problem {
  type: "error" | "warning" | "conflict"
  message: string
  line: number
  file: string
}

/* ── Log entry ────────────────────────────────────────────────────── */
export interface LogEntry {
  time: string
  level: "INFO" | "WARN" | "ERROR"
  message: string
}
