/** Line health status from the backend. */
export type LineStatus = "ok" | "warning" | "error" | "comment" | "conflict"

/** Conflict metadata attached to a line. */
export interface ConflictInfo {
  conflicting_positions: number[]
  shared_nets: string[]
}

/** A single document line returned by the API. */
export interface DocumentLine {
  position: number
  raw_text: string
  status: LineStatus
  errors: string[]
  warnings: string[]
  has_data: boolean
  data: Record<string, unknown> | null
  conflict_info: ConflictInfo | null
}

/** Summary returned after loading a document. */
export interface DocumentSummary {
  doc_id: string
  doc_type: "af" | "mutex"
  file_path: string
  total_lines: number
  status_counts: Record<string, number>
  can_undo: boolean
  can_redo: boolean
}

/** Edit session hydration response. */
export interface EditSession {
  position: number
  doc_type: string
  data: Record<string, unknown>
}

/** Problem entry for the problems panel. */
export interface Problem {
  position: number
  severity: "error" | "warning" | "conflict"
  message: string
}
