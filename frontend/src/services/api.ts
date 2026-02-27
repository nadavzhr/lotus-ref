import type {
  DocumentSummary,
  DocumentLine,
  HydrateSessionResponse,
  MutationResponse,
  MutexSession,
  QueryNetsResponse,
  SaveResponse,
} from "@/types/api"

const BASE = "/api"

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  })
  if (!res.ok) {
    const body = await res.text()
    throw new Error(`API ${res.status}: ${body}`)
  }
  return res.json() as Promise<T>
}

// Document lifecycle
export function loadDocument(
  docId: string,
  filePath: string,
  docType: "af" | "mutex",
): Promise<DocumentSummary> {
  return request(`${BASE}/documents/load`, {
    method: "POST",
    body: JSON.stringify({ doc_id: docId, file_path: filePath, doc_type: docType }),
  })
}

export function listDocuments(): Promise<DocumentSummary[]> {
  return request(`${BASE}/documents`)
}

export function closeDocument(docId: string): Promise<{ status: string; doc_id: string }> {
  return request(`${BASE}/documents/${docId}`, { method: "DELETE" })
}

// Lines
export function getLines(
  docId: string,
  offset = 0,
  limit?: number,
): Promise<DocumentLine[]> {
  const params = new URLSearchParams({ offset: String(offset) })
  if (limit !== undefined) params.set("limit", String(limit))
  return request(`${BASE}/documents/${docId}/lines?${params}`)
}

export function getLine(docId: string, position: number): Promise<DocumentLine> {
  return request(`${BASE}/documents/${docId}/lines/${position}`)
}

export function searchLines(
  docId: string,
  query: string,
  regex = false,
  status?: string,
): Promise<DocumentLine[]> {
  const params = new URLSearchParams({ q: query })
  if (regex) params.set("regex", "true")
  if (status) params.set("status", status)
  return request(`${BASE}/documents/${docId}/search?${params}`)
}

// Line mutations
export function deleteLine(docId: string, position: number): Promise<DocumentSummary> {
  return request(`${BASE}/documents/${docId}/lines/${position}`, { method: "DELETE" })
}

export function insertLine(docId: string, position: number): Promise<{ position: number }> {
  return request(`${BASE}/documents/${docId}/lines/${position}/insert`, { method: "POST" })
}

export function toggleComment(docId: string, position: number): Promise<DocumentLine> {
  return request(`${BASE}/documents/${docId}/lines/${position}/toggle-comment`, { method: "POST" })
}

export function swapLines(
  docId: string,
  posA: number,
  posB: number,
): Promise<DocumentSummary> {
  return request(`${BASE}/documents/${docId}/swap`, {
    method: "POST",
    body: JSON.stringify({ pos_a: posA, pos_b: posB }),
  })
}

// Edit session
export function hydrateSession(
  docId: string,
  position: number,
  fields?: Record<string, unknown>,
): Promise<HydrateSessionResponse> {
  return request(`${BASE}/documents/${docId}/lines/${position}/session`, {
    method: "PUT",
    body: JSON.stringify({ fields: fields ?? null }),
  })
}

export function commitEdit(docId: string, position: number): Promise<DocumentLine> {
  return request(`${BASE}/documents/${docId}/lines/${position}/commit`, { method: "POST" })
}

// Undo / Redo
export function undo(docId: string): Promise<MutationResponse> {
  return request(`${BASE}/documents/${docId}/undo`, { method: "POST" })
}

export function redo(docId: string): Promise<MutationResponse> {
  return request(`${BASE}/documents/${docId}/redo`, { method: "POST" })
}

// Save
export function saveDocument(
  docId: string,
  filePath?: string,
): Promise<SaveResponse> {
  return request(`${BASE}/documents/${docId}/save`, {
    method: "POST",
    body: JSON.stringify({ file_path: filePath ?? null }),
  })
}

// NQS query
export function queryNets(
  template: string | null,
  netPattern: string,
  templateRegex = false,
  netRegex = false,
): Promise<QueryNetsResponse> {
  return request(`${BASE}/query-nets`, {
    method: "POST",
    body: JSON.stringify({
      template,
      net_pattern: netPattern,
      template_regex: templateRegex,
      net_regex: netRegex,
    }),
  })
}

// Mutex session
export function getMutexSession(
  docId: string,
  position: number,
): Promise<MutexSession> {
  return request(`${BASE}/documents/${docId}/lines/${position}/mutex/session`)
}

export function mutexAddMutexed(
  docId: string,
  position: number,
  template: string | null,
  netPattern: string,
  isRegex = false,
): Promise<MutexSession> {
  return request(`${BASE}/documents/${docId}/lines/${position}/mutex/add-mutexed`, {
    method: "POST",
    body: JSON.stringify({ template, net_pattern: netPattern, is_regex: isRegex }),
  })
}

export function mutexAddActive(
  docId: string,
  position: number,
  template: string | null,
  netName: string,
): Promise<MutexSession> {
  return request(`${BASE}/documents/${docId}/lines/${position}/mutex/add-active`, {
    method: "POST",
    body: JSON.stringify({ template, net_name: netName }),
  })
}

export function mutexRemoveMutexed(
  docId: string,
  position: number,
  template: string | null,
  netPattern: string,
  isRegex = false,
): Promise<MutexSession> {
  return request(`${BASE}/documents/${docId}/lines/${position}/mutex/remove-mutexed`, {
    method: "POST",
    body: JSON.stringify({ template, net_pattern: netPattern, is_regex: isRegex }),
  })
}

export function mutexRemoveActive(
  docId: string,
  position: number,
  template: string | null,
  netName: string,
): Promise<MutexSession> {
  return request(`${BASE}/documents/${docId}/lines/${position}/mutex/remove-active`, {
    method: "POST",
    body: JSON.stringify({ template, net_name: netName }),
  })
}

export function mutexSetFev(
  docId: string,
  position: number,
  fev: string,
): Promise<MutexSession> {
  return request(`${BASE}/documents/${docId}/lines/${position}/mutex/set-fev`, {
    method: "POST",
    body: JSON.stringify({ fev }),
  })
}

export function mutexSetNumActive(
  docId: string,
  position: number,
  value: number,
): Promise<MutexSession> {
  return request(`${BASE}/documents/${docId}/lines/${position}/mutex/set-num-active`, {
    method: "POST",
    body: JSON.stringify({ value }),
  })
}
