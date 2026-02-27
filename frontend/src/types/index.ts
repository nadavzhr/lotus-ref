/* ── Line statuses ─────────────────────────────────────────────────────── */
export type LineStatus = "valid" | "warning" | "error" | "comment" | "conflict"

/* ── Document line as returned by GET /api/documents/{id}/lines ─────── */
export interface DocumentLine {
  position: number
  raw_text: string
  status: LineStatus
  is_comment: boolean
  fields: Record<string, unknown>
  errors: string[]
  warnings: string[]
  conflicts: string[]
}

/* ── Lines response (paginated) ───────────────────────────────────────── */
export interface LinesResponse {
  doc_id: string
  total: number
  offset: number
  limit: number | null
  lines: DocumentLine[]
}

/* ── Document summary from GET /api/documents ──────────────────────── */
export interface DocumentSummary {
  doc_id: string
  doc_type: string
  file_path: string
  line_count: number
  is_modified: boolean
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
  line_count: number
}

/* ── Edit session (hydrate response) ──────────────────────────────── */
export interface EditSession {
  position: number
  fields: Record<string, unknown>
  raw_text: string
  status: LineStatus
  errors: string[]
  warnings: string[]
  validation: Record<string, unknown>
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
  net_count: number
  template_count: number
}

/* ── Mutex session state ──────────────────────────────────────────── */
export interface MutexSession {
  mutexed_nets: string[]
  active_nets: string[]
  fev: string
  num_active: number
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
