import { create } from "zustand";
import type { DocumentLine, DocumentSummary } from "@/api/documents";
import * as api from "@/api/documents";

/* ------------------------------------------------------------------ */
/* Per-document state                                                  */
/* ------------------------------------------------------------------ */

export interface DocumentState {
  docId: string;
  docType: "af" | "mutex";
  filePath: string;
  totalLines: number;
  statusCounts: Record<string, number>;
  canUndo: boolean;
  canRedo: boolean;
  lines: DocumentLine[];
  selectedPosition: number | null;
  loading: boolean;
}

/* ------------------------------------------------------------------ */
/* Store                                                               */
/* ------------------------------------------------------------------ */

interface DocumentStoreState {
  /** Map of docId → document state */
  documents: Record<string, DocumentState>;

  /** Load a document from the backend and store its state */
  loadDocument: (
    docId: string,
    filePath: string,
    docType: "af" | "mutex",
  ) => Promise<void>;

  /** Refresh lines for a document (after mutations) */
  refreshLines: (docId: string) => Promise<void>;

  /** Close / unload a document */
  closeDocument: (docId: string) => Promise<void>;

  /** Select a line by position (or null to deselect) */
  selectLine: (docId: string, position: number | null) => void;

  /** Delete a line */
  deleteLine: (docId: string, position: number) => Promise<void>;

  /** Insert a blank line at position */
  insertLine: (docId: string, position: number) => Promise<void>;

  /** Toggle comment on a line */
  toggleComment: (docId: string, position: number) => Promise<void>;

  /** Swap two lines */
  swapLines: (docId: string, posA: number, posB: number) => Promise<void>;

  /** Undo last mutation */
  undo: (docId: string) => Promise<void>;

  /** Redo last undone mutation */
  redo: (docId: string) => Promise<void>;

  /** Save document to disk */
  saveDocument: (docId: string) => Promise<string>;
}

function summaryToState(
  summary: DocumentSummary,
  existing?: Partial<DocumentState>,
): DocumentState {
  return {
    docId: summary.doc_id,
    docType: summary.doc_type as "af" | "mutex",
    filePath: summary.file_path,
    totalLines: summary.total_lines,
    statusCounts: summary.status_counts,
    canUndo: summary.can_undo,
    canRedo: summary.can_redo,
    lines: existing?.lines ?? [],
    selectedPosition: existing?.selectedPosition ?? null,
    loading: false,
  };
}

/** Derive status counts from lines (client-side, always fresh). */
function computeStatusCounts(lines: DocumentLine[]): Record<string, number> {
  const counts: Record<string, number> = {};
  for (const line of lines) {
    counts[line.status] = (counts[line.status] ?? 0) + 1;
    if (line.is_conflict) {
      counts.conflict = (counts.conflict ?? 0) + 1;
    }
  }
  return counts;
}

function patchDoc(
  state: DocumentStoreState,
  docId: string,
  patch: Partial<DocumentState>,
): DocumentStoreState {
  const prev = state.documents[docId];
  if (!prev) return state;
  return {
    ...state,
    documents: {
      ...state.documents,
      [docId]: { ...prev, ...patch },
    },
  };
}

export const useDocumentStore = create<DocumentStoreState>((set, get) => ({
  documents: {},

  loadDocument: async (docId, filePath, docType) => {
    // Mark loading
    set((s) => ({
      documents: {
        ...s.documents,
        [docId]: {
          docId,
          docType,
          filePath,
          totalLines: 0,
          statusCounts: {},
          canUndo: false,
          canRedo: false,
          lines: [],
          selectedPosition: null,
          loading: true,
        },
      },
    }));

    const summary = await api.loadDocument(docId, filePath, docType);
    const lines = await api.getLines(docId);

    set((s) => ({
      documents: {
        ...s.documents,
        [docId]: {
          ...summaryToState(summary, { lines }),
          statusCounts: computeStatusCounts(lines),
        },
      },
    }));
  },

  refreshLines: async (docId) => {
    const lines = await api.getLines(docId);
    set((s) => patchDoc(s, docId, {
      lines,
      totalLines: lines.length,
      statusCounts: computeStatusCounts(lines),
    }));
  },

  closeDocument: async (docId) => {
    try {
      await api.closeDocument(docId);
    } catch {
      // ignore — backend may have already closed it
    }
    set((s) => {
      const { [docId]: _, ...rest } = s.documents;
      return { documents: rest };
    });
  },

  selectLine: (docId, position) => {
    set((s) => patchDoc(s, docId, { selectedPosition: position }));
  },

  deleteLine: async (docId, position) => {
    const doc = get().documents[docId];
    if (!doc) return;

    await api.deleteLine(docId, position);
    const lines = await api.getLines(docId);

    // Adjust selection
    let sel = doc.selectedPosition;
    if (sel === position) sel = null;
    else if (sel !== null && sel > position) sel--;

    set((s) =>
      patchDoc(s, docId, {
        lines,
        totalLines: lines.length,
        statusCounts: computeStatusCounts(lines),
        selectedPosition: sel,
        canUndo: true,
        canRedo: false,
      }),
    );
  },

  insertLine: async (docId, position) => {
    const doc = get().documents[docId];
    if (!doc) return;

    await api.insertLine(docId, position);
    const lines = await api.getLines(docId);

    let sel = doc.selectedPosition;
    if (sel !== null && sel >= position) sel++;

    set((s) =>
      patchDoc(s, docId, {
        lines,
        totalLines: lines.length,
        statusCounts: computeStatusCounts(lines),
        selectedPosition: sel,
        canUndo: true,
        canRedo: false,
      }),
    );
  },

  toggleComment: async (docId, position) => {
    await api.toggleComment(docId, position);
    const lines = await api.getLines(docId);
    set((s) =>
      patchDoc(s, docId, {
        lines,
        totalLines: lines.length,
        statusCounts: computeStatusCounts(lines),
        canUndo: true,
        canRedo: false,
      }),
    );
  },

  swapLines: async (docId, posA, posB) => {
    const doc = get().documents[docId];
    if (!doc) return;

    await api.swapLines(docId, posA, posB);
    const lines = await api.getLines(docId);

    // If selected line was one of the swapped, follow it
    let sel = doc.selectedPosition;
    if (sel === posA) sel = posB;
    else if (sel === posB) sel = posA;

    set((s) =>
      patchDoc(s, docId, {
        lines,
        totalLines: lines.length,
        statusCounts: computeStatusCounts(lines),
        selectedPosition: sel,
        canUndo: true,
        canRedo: false,
      }),
    );
  },

  undo: async (docId) => {
    const result = await api.undo(docId);
    const lines = await api.getLines(docId);
    set((s) =>
      patchDoc(s, docId, {
        lines,
        totalLines: lines.length,
        statusCounts: computeStatusCounts(lines),
        canUndo: result.can_undo,
        canRedo: result.can_redo,
      }),
    );
  },

  redo: async (docId) => {
    const result = await api.redo(docId);
    const lines = await api.getLines(docId);
    set((s) =>
      patchDoc(s, docId, {
        lines,
        totalLines: lines.length,
        statusCounts: computeStatusCounts(lines),
        canUndo: result.can_undo,
        canRedo: result.can_redo,
      }),
    );
  },

  saveDocument: async (docId) => {
    const result = await api.saveDocument(docId);
    return result.file_path;
  },
}));
