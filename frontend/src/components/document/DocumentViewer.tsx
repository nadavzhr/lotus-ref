import { useCallback, useEffect, useRef, useState } from "react";
import { useDocumentStore } from "@/stores/document-store";
import { useEditStore } from "@/stores/edit-store";
import { LineRow } from "./LineRow";
import { StatusBadge } from "./StatusBadge";
import { DocumentSearchBar } from "./DocumentSearchBar";
import { Loader2 } from "lucide-react";
import type { DocumentLine } from "@/api/documents";

interface DocumentViewerProps {
  docId: string;
}

/**
 * DocumentViewer — renders all lines of a loaded document.
 *
 * Handles:
 * - Line rendering with selection highlight
 * - Keyboard navigation & shortcuts
 * - Delegates mutations to the document store
 */
export function DocumentViewer({ docId }: DocumentViewerProps) {
  const doc = useDocumentStore((s) => s.documents[docId]);
  const selectLine = useDocumentStore((s) => s.selectLine);
  const deleteLine = useDocumentStore((s) => s.deleteLine);
  const insertLine = useDocumentStore((s) => s.insertLine);
  const toggleComment = useDocumentStore((s) => s.toggleComment);
  const swapLines = useDocumentStore((s) => s.swapLines);
  const undo = useDocumentStore((s) => s.undo);
  const redo = useDocumentStore((s) => s.redo);
  const openEdit = useEditStore((s) => s.openEdit);

  const containerRef = useRef<HTMLDivElement>(null);

  /** Position currently in inline-comment-edit mode */
  const [editingCommentPos, setEditingCommentPos] = useState<number | null>(null);

  /** Filtered lines from search bar — null means show all */
  const [filteredLines, setFilteredLines] = useState<DocumentLine[] | null>(null);

  const displayedLines = filteredLines ?? doc?.lines ?? [];

  /* ------ Callbacks for LineRow ------ */

  const handleSelect = useCallback(
    (pos: number) => selectLine(docId, pos),
    [docId, selectLine],
  );

  const handleEdit = useCallback(
    (pos: number) => {
      if (!doc) return;
      const line = doc.lines.find((l) => l.position === pos);
      if (!line) return;

      selectLine(docId, pos);

      // Comment lines → inline editor
      if (line.status === "comment") {
        setEditingCommentPos(pos);
        return;
      }

      // Data lines (including empty) → open edit dialog
      const row = document.querySelector(`[data-position="${pos}"]`);
      const rect = row?.getBoundingClientRect();
      const originY = rect ? rect.top + rect.height / 2 : undefined;
      openEdit(docId, pos, doc.docType, originY);
    },
    [docId, doc, selectLine, openEdit],
  );

  const handleDelete = useCallback(
    (pos: number) => deleteLine(docId, pos),
    [docId, deleteLine],
  );

  const handleInsertBelow = useCallback(
    (pos: number) => insertLine(docId, pos + 1),
    [docId, insertLine],
  );

  const handleToggleComment = useCallback(
    (pos: number) => toggleComment(docId, pos),
    [docId, toggleComment],
  );

  const handleSwapUp = useCallback(
    (pos: number) => {
      if (pos > 0) swapLines(docId, pos, pos - 1);
    },
    [docId, swapLines],
  );

  const handleSwapDown = useCallback(
    (pos: number) => {
      if (doc && pos < doc.lines.length - 1) swapLines(docId, pos, pos + 1);
    },
    [docId, doc, swapLines],
  );

  /* ------ Keyboard shortcuts (document-level) ------ */

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (!doc) return;
      const sel = doc.selectedPosition;

      // Undo: Ctrl+Z
      if ((e.ctrlKey || e.metaKey) && e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        undo(docId);
        return;
      }

      // Redo: Ctrl+Y or Ctrl+Shift+Z
      if (
        (e.ctrlKey || e.metaKey) &&
        (e.key === "y" || (e.key === "z" && e.shiftKey))
      ) {
        e.preventDefault();
        redo(docId);
        return;
      }

      // The rest require a selected line
      if (sel === null) return;

      // Alt+Up: swap up
      if (e.altKey && e.key === "ArrowUp") {
        e.preventDefault();
        if (sel > 0) swapLines(docId, sel, sel - 1);
        return;
      }

      // Alt+Down: swap down
      if (e.altKey && e.key === "ArrowDown") {
        e.preventDefault();
        if (sel < doc.lines.length - 1) swapLines(docId, sel, sel + 1);
        return;
      }

      // Ctrl+/: toggle comment
      if ((e.ctrlKey || e.metaKey) && e.key === "/") {
        e.preventDefault();
        toggleComment(docId, sel);
        return;
      }

      // Delete: delete line
      if (e.key === "Delete" && !e.ctrlKey && !e.altKey && !e.metaKey) {
        e.preventDefault();
        deleteLine(docId, sel);
        return;
      }

      // Arrow navigation (no modifier)
      if (e.key === "ArrowUp" && !e.altKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        if (sel > 0) selectLine(docId, sel - 1);
        return;
      }
      if (e.key === "ArrowDown" && !e.altKey && !e.ctrlKey && !e.metaKey) {
        e.preventDefault();
        if (sel < doc.lines.length - 1) selectLine(docId, sel + 1);
        return;
      }

      // Escape: deselect
      if (e.key === "Escape") {
        selectLine(docId, null);
        return;
      }
    };

    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [docId, doc, selectLine, deleteLine, toggleComment, swapLines, undo, redo]);

  /* ------ Scroll selected line into view ------ */

  useEffect(() => {
    if (!doc || doc.selectedPosition === null) return;
    const el = containerRef.current?.querySelector(
      `[data-position="${doc.selectedPosition}"]`,
    );
    el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [doc?.selectedPosition, doc]);

  /* ------ Loading / empty states ------ */

  if (!doc) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
        Document not loaded.
      </div>
    );
  }

  if (doc.loading) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading...
      </div>
    );
  }

  /* ------ Render ------ */

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Status summary bar */}
      <div className="flex shrink-0 items-center gap-3 border-b bg-muted/30 px-4 py-1.5">
        <span className="text-xs text-muted-foreground">
          {doc.totalLines} lines
        </span>
        <span className="text-xs text-muted-foreground/30">|</span>
        {/* Always show ok, warning, error in fixed order */}
        {(["ok", "warning", "error"] as const).map((status) => (
          <div key={status} className="flex items-center gap-1">
            <StatusBadge status={status} />
            <span className="text-2xs text-muted-foreground">
              {doc.statusCounts[status] ?? 0}
            </span>
          </div>
        ))}
        {/* Show comment only when present */}
        {(doc.statusCounts.comment ?? 0) > 0 && (
          <div className="flex items-center gap-1">
            <StatusBadge status="comment" />
            <span className="text-2xs text-muted-foreground">
              {doc.statusCounts.comment}
            </span>
          </div>
        )}
        {/* Conflict separated */}
        {(doc.statusCounts.conflict ?? 0) > 0 && (
          <>
            <span className="text-xs text-muted-foreground/30">|</span>
            <div className="flex items-center gap-1">
              <StatusBadge status="conflict" />
              <span className="text-2xs text-muted-foreground">
                {doc.statusCounts.conflict}
              </span>
            </div>
          </>
        )}
        {filteredLines && (
          <>
            <span className="text-xs text-muted-foreground/30">|</span>
            <span className="text-xs font-medium text-primary">
              {filteredLines.length} match{filteredLines.length !== 1 ? "es" : ""}
            </span>
          </>
        )}
      </div>

      {/* Search bar */}
      <DocumentSearchBar docId={docId} onResults={setFilteredLines} />

      {/* Column header */}
      <div className="flex shrink-0 items-center border-b bg-muted/20 text-2xs uppercase tracking-wider text-muted-foreground">
        <div className="w-10 shrink-0 pr-2 text-right">#</div>
        <div className="w-10 shrink-0 text-center">Status</div>
        <div className="flex-1 pl-2">Raw Text</div>
        <div className="w-16 shrink-0" />
      </div>

      {/* Scrollable line list */}
      <div
        ref={containerRef}
        role="grid"
        className="flex-1 overflow-y-auto"
      >
        {displayedLines.map((line) => (
          <LineRow
            key={line.position}
            line={line}
            isSelected={doc.selectedPosition === line.position}
            totalLines={doc.totalLines}
            docId={docId}
            editingComment={editingCommentPos === line.position}
            onCloseCommentEdit={() => setEditingCommentPos(null)}
            onSelect={handleSelect}
            onEdit={handleEdit}
            onDelete={handleDelete}
            onInsertBelow={handleInsertBelow}
            onToggleComment={handleToggleComment}
            onSwapUp={handleSwapUp}
            onSwapDown={handleSwapDown}
          />
        ))}

        {displayedLines.length === 0 && (
          <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
            {filteredLines ? "No matching lines" : "Empty document"}
          </div>
        )}
      </div>
    </div>
  );
}
