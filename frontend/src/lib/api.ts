import type { DocumentLine, DocumentSummary, EditSession } from "@/types/api"

const API = "/api"

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(
      (body as Record<string, string>).detail ?? res.statusText
    )
  }
  return res.json() as Promise<T>
}

export async function loadDocument(
  docId: string,
  filePath: string,
  docType: string
): Promise<DocumentSummary> {
  const res = await fetch(`${API}/documents/load`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doc_id: docId, file_path: filePath, doc_type: docType }),
  })
  return handleResponse<DocumentSummary>(res)
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  const res = await fetch(`${API}/documents`)
  return handleResponse<DocumentSummary[]>(res)
}

export async function getLines(
  docId: string,
  offset = 0,
  limit?: number
): Promise<DocumentLine[]> {
  const params = new URLSearchParams({ offset: String(offset) })
  if (limit !== undefined) params.set("limit", String(limit))
  const res = await fetch(`${API}/documents/${docId}/lines?${params}`)
  return handleResponse<DocumentLine[]>(res)
}

export async function getLine(
  docId: string,
  position: number
): Promise<DocumentLine> {
  const res = await fetch(`${API}/documents/${docId}/lines/${position}`)
  return handleResponse<DocumentLine>(res)
}

export async function searchLines(
  docId: string,
  q: string,
  regex = false,
  status?: string
): Promise<DocumentLine[]> {
  const params = new URLSearchParams()
  if (q) params.set("q", q)
  if (regex) params.set("regex", "true")
  if (status) params.set("status", status)
  const res = await fetch(`${API}/documents/${docId}/search?${params}`)
  return handleResponse<DocumentLine[]>(res)
}

export async function hydrateSession(
  docId: string,
  position: number,
  fields?: Record<string, unknown> | null
): Promise<EditSession> {
  const res = await fetch(
    `${API}/documents/${docId}/lines/${position}/session`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fields: fields ?? null }),
    }
  )
  return handleResponse<EditSession>(res)
}

export async function commitEdit(
  docId: string,
  position: number
): Promise<DocumentLine> {
  const res = await fetch(
    `${API}/documents/${docId}/lines/${position}/commit`,
    { method: "POST" }
  )
  return handleResponse<DocumentLine>(res)
}

export async function undo(
  docId: string
): Promise<{ can_undo: boolean; can_redo: boolean }> {
  const res = await fetch(`${API}/documents/${docId}/undo`, { method: "POST" })
  return handleResponse<{ can_undo: boolean; can_redo: boolean }>(res)
}

export async function redo(
  docId: string
): Promise<{ can_undo: boolean; can_redo: boolean }> {
  const res = await fetch(`${API}/documents/${docId}/redo`, { method: "POST" })
  return handleResponse<{ can_undo: boolean; can_redo: boolean }>(res)
}

export async function deleteLine(
  docId: string,
  position: number
): Promise<DocumentSummary> {
  const res = await fetch(`${API}/documents/${docId}/lines/${position}`, {
    method: "DELETE",
  })
  return handleResponse<DocumentSummary>(res)
}

export async function toggleComment(
  docId: string,
  position: number
): Promise<DocumentLine> {
  const res = await fetch(
    `${API}/documents/${docId}/lines/${position}/toggle-comment`,
    { method: "POST" }
  )
  return handleResponse<DocumentLine>(res)
}

export async function saveDocument(
  docId: string,
  filePath?: string
): Promise<{ file_path: string }> {
  const res = await fetch(`${API}/documents/${docId}/save`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ file_path: filePath ?? null }),
  })
  return handleResponse<{ file_path: string }>(res)
}
