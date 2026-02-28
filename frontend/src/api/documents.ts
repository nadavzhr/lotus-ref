/**
 * Document API — maps 1:1 to the FastAPI routes in app/routes.py.
 * Components never call fetch() directly; they call these functions.
 */

import * as http from "./client";
import { logInfo } from "./client";

/* ---------- Types ---------- */

export interface DocumentSummary {
  doc_id: string;
  file_path: string;
  doc_type: string;
  total_lines: number;
  status_counts: Record<string, number>;
  can_undo: boolean;
  can_redo: boolean;
}

export interface DocumentLine {
  position: number;
  raw_text: string;
  status: string;
  errors: string[];
  warnings: string[];
  is_conflict: boolean;
  conflict_info?: {
    peers: Array<{
      position: number;
      shared_nets: string[];
    }>;
  };
  data?: Record<string, unknown>;
}

/* ---------- Endpoints ---------- */

export async function loadDocument(
  docId: string,
  filePath: string,
  docType: string,
): Promise<DocumentSummary> {
  const summary = await http.post<DocumentSummary>("/documents/load", {
    doc_id: docId,
    file_path: filePath,
    doc_type: docType,
  });
  logInfo(`Loaded ${docType.toUpperCase()} document: ${filePath} (${summary.total_lines} lines)`);
  return summary;
}

export function listDocuments(): Promise<DocumentSummary[]> {
  return http.get("/documents");
}

export function closeDocument(docId: string): Promise<{ status: string }> {
  return http.del(`/documents/${docId}`);
}

export function getLines(
  docId: string,
  offset = 0,
  limit?: number,
): Promise<DocumentLine[]> {
  const params = new URLSearchParams();
  params.set("offset", String(offset));
  if (limit !== undefined) params.set("limit", String(limit));
  return http.get(`/documents/${docId}/lines?${params}`);
}

export function getLine(
  docId: string,
  position: number,
): Promise<DocumentLine> {
  return http.get(`/documents/${docId}/lines/${position}`);
}

export function deleteLine(
  docId: string,
  position: number,
): Promise<DocumentLine[]> {
  return http.del(`/documents/${docId}/lines/${position}`);
}

export function insertLine(
  docId: string,
  position: number,
): Promise<DocumentLine[]> {
  return http.post(`/documents/${docId}/lines/${position}/insert`);
}

export function toggleComment(
  docId: string,
  position: number,
): Promise<DocumentLine[]> {
  return http.post(`/documents/${docId}/lines/${position}/toggle-comment`);
}

export function swapLines(
  docId: string,
  posA: number,
  posB: number,
): Promise<unknown> {
  return http.post(`/documents/${docId}/swap`, { pos_a: posA, pos_b: posB });
}

export function hydrateSession(
  docId: string,
  position: number,
  fields: Record<string, unknown> | null,
): Promise<unknown> {
  return http.put(`/documents/${docId}/lines/${position}/session`, { fields });
}

export function commitEdit(
  docId: string,
  position: number,
): Promise<unknown> {
  return http.post(`/documents/${docId}/lines/${position}/commit`);
}

export async function saveDocument(
  docId: string,
  filePath?: string,
): Promise<{ file_path: string }> {
  const result = await http.post<{ file_path: string }>(
    `/documents/${docId}/save`,
    { file_path: filePath ?? null },
  );
  logInfo(`Saved document to: ${result.file_path}`);
  return result;
}

export function undo(docId: string): Promise<{ can_undo: boolean; can_redo: boolean }> {
  return http.post(`/documents/${docId}/undo`);
}

export function redo(docId: string): Promise<{ can_undo: boolean; can_redo: boolean }> {
  return http.post(`/documents/${docId}/redo`);
}

export function searchLines(
  docId: string,
  q: string,
  regex: boolean,
  status?: string,
): Promise<DocumentLine[]> {
  const params = new URLSearchParams();
  if (q) params.set("q", q);
  if (regex) params.set("regex", "true");
  if (status) params.set("status", status);
  return http.get(`/documents/${docId}/search?${params}`);
}

export function editCommentText(
  docId: string,
  position: number,
  text: string,
): Promise<unknown> {
  return http.put(`/documents/${docId}/lines/${position}/comment-text`, { text });
}

/* ---------- NQS ---------- */

export function queryNets(
  template: string | null,
  netPattern: string,
  templateRegex?: boolean,
  netRegex?: boolean,
): Promise<{ nets: string[]; templates: string[] }> {
  return http.post("/query-nets", {
    template,
    net_pattern: netPattern,
    template_regex: templateRegex ?? false,
    net_regex: netRegex ?? false,
  });
}

/* ---------- Mutex session operations ---------- */

export function getMutexSession(
  docId: string,
  position: number,
): Promise<unknown> {
  return http.get(`/documents/${docId}/lines/${position}/mutex/session`);
}

export function mutexAddMutexed(
  docId: string,
  position: number,
  template: string | null,
  netPattern: string,
  isRegex: boolean,
): Promise<unknown> {
  return http.post(`/documents/${docId}/lines/${position}/mutex/add-mutexed`, {
    template,
    net_pattern: netPattern,
    is_regex: isRegex,
  });
}

export function mutexAddActive(
  docId: string,
  position: number,
  template: string | null,
  netName: string,
): Promise<unknown> {
  return http.post(`/documents/${docId}/lines/${position}/mutex/add-active`, {
    template,
    net_name: netName,
  });
}

export function mutexRemoveMutexed(
  docId: string,
  position: number,
  template: string | null,
  netPattern: string,
  isRegex: boolean,
): Promise<unknown> {
  return http.post(`/documents/${docId}/lines/${position}/mutex/remove-mutexed`, {
    template,
    net_pattern: netPattern,
    is_regex: isRegex,
  });
}

export function mutexRemoveActive(
  docId: string,
  position: number,
  template: string | null,
  netName: string,
): Promise<unknown> {
  return http.post(`/documents/${docId}/lines/${position}/mutex/remove-active`, {
    template,
    net_name: netName,
  });
}

export function mutexSetFev(
  docId: string,
  position: number,
  fev: string,
): Promise<unknown> {
  return http.post(`/documents/${docId}/lines/${position}/mutex/set-fev`, {
    fev,
  });
}

export function mutexSetNumActive(
  docId: string,
  position: number,
  value: number,
): Promise<unknown> {
  return http.post(`/documents/${docId}/lines/${position}/mutex/set-num-active`, {
    value,
  });
}
