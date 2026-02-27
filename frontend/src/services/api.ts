import type {
  LinesResponse,
  DocumentSummary,
  LoadRequest,
  LoadResponse,
  EditSession,
  SearchResult,
  QueryNetsRequest,
  QueryNetsResponse,
} from "@/types"

const BASE = "/api"

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

/* ── Documents ─────────────────────────────────────────────────────── */

export function listDocuments(): Promise<DocumentSummary[]> {
  return request<DocumentSummary[]>("/documents")
}

export function loadDocument(req: LoadRequest): Promise<LoadResponse> {
  return request<LoadResponse>("/documents/load", {
    method: "POST",
    body: JSON.stringify(req),
  })
}

export function closeDocument(docId: string): Promise<{ status: string; doc_id: string }> {
  return request(`/documents/${docId}`, { method: "DELETE" })
}

export function saveDocument(docId: string, filePath?: string): Promise<unknown> {
  return request(`/documents/${docId}/save`, {
    method: "POST",
    body: JSON.stringify({ file_path: filePath ?? null }),
  })
}

/* ── Lines ─────────────────────────────────────────────────────────── */

export function getLines(
  docId: string,
  offset = 0,
  limit?: number,
): Promise<LinesResponse> {
  const params = new URLSearchParams({ offset: String(offset) })
  if (limit !== undefined) params.set("limit", String(limit))
  return request<LinesResponse>(`/documents/${docId}/lines?${params}`)
}

export function getLine(docId: string, position: number): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}`)
}

export function deleteLine(docId: string, position: number): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}`, { method: "DELETE" })
}

export function insertLine(docId: string, position: number): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}/insert`, {
    method: "POST",
  })
}

export function toggleComment(docId: string, position: number): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}/toggle-comment`, {
    method: "POST",
  })
}

export function swapLines(docId: string, posA: number, posB: number): Promise<unknown> {
  return request(`/documents/${docId}/swap`, {
    method: "POST",
    body: JSON.stringify({ pos_a: posA, pos_b: posB }),
  })
}

/* ── Search ────────────────────────────────────────────────────────── */

export function searchLines(
  docId: string,
  q: string,
  regex = false,
  status?: string,
): Promise<SearchResult> {
  const params = new URLSearchParams({ q })
  if (regex) params.set("regex", "true")
  if (status) params.set("status", status)
  return request<SearchResult>(`/documents/${docId}/search?${params}`)
}

/* ── Edit Sessions ─────────────────────────────────────────────────── */

export function hydrateSession(
  docId: string,
  position: number,
  fields?: Record<string, unknown> | null,
): Promise<EditSession> {
  return request<EditSession>(`/documents/${docId}/lines/${position}/session`, {
    method: "PUT",
    body: JSON.stringify({ fields: fields ?? null }),
  })
}

export function commitEdit(docId: string, position: number): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}/commit`, {
    method: "POST",
  })
}

/* ── Undo / Redo ───────────────────────────────────────────────────── */

export function undo(docId: string): Promise<unknown> {
  return request(`/documents/${docId}/undo`, { method: "POST" })
}

export function redo(docId: string): Promise<unknown> {
  return request(`/documents/${docId}/redo`, { method: "POST" })
}

/* ── NQS Query ─────────────────────────────────────────────────────── */

export function queryNets(req: QueryNetsRequest): Promise<QueryNetsResponse> {
  return request<QueryNetsResponse>("/query-nets", {
    method: "POST",
    body: JSON.stringify(req),
  })
}

/* ── Mutex Session Operations ──────────────────────────────────────── */

export function mutexAddMutexed(
  docId: string,
  position: number,
  template: string | undefined,
  netPattern: string,
  isRegex = false,
): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}/mutex/add-mutexed`, {
    method: "POST",
    body: JSON.stringify({ template, net_pattern: netPattern, is_regex: isRegex }),
  })
}

export function mutexAddActive(
  docId: string,
  position: number,
  template: string | undefined,
  netName: string,
): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}/mutex/add-active`, {
    method: "POST",
    body: JSON.stringify({ template, net_name: netName }),
  })
}

export function mutexRemoveMutexed(
  docId: string,
  position: number,
  template: string | undefined,
  netPattern: string,
  isRegex = false,
): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}/mutex/remove-mutexed`, {
    method: "POST",
    body: JSON.stringify({ template, net_pattern: netPattern, is_regex: isRegex }),
  })
}

export function mutexRemoveActive(
  docId: string,
  position: number,
  template: string | undefined,
  netName: string,
): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}/mutex/remove-active`, {
    method: "POST",
    body: JSON.stringify({ template, net_name: netName }),
  })
}

export function mutexSetFev(docId: string, position: number, fev: string): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}/mutex/set-fev`, {
    method: "POST",
    body: JSON.stringify({ fev }),
  })
}

export function mutexSetNumActive(
  docId: string,
  position: number,
  value: number,
): Promise<unknown> {
  return request(`/documents/${docId}/lines/${position}/mutex/set-num-active`, {
    method: "POST",
    body: JSON.stringify({ value }),
  })
}
