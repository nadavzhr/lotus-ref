import { useCallback, useRef } from "react";
import type { DocumentLine } from "@/api/documents";
import { cn } from "@/lib/utils";
import { StatusBadge, ConflictBadge } from "./StatusBadge";
import { LineOverflowMenu } from "./LineOverflowMenu";
import { InlineCommentEditor } from "@/components/edit/InlineCommentEditor";
import { Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";

/* ------------------------------------------------------------------ */
/* Status → left-border color mapping                                  */
/* ------------------------------------------------------------------ */

const borderColors: Record<string, string> = {
  ok: "border-l-status-ok",
  warning: "border-l-status-warning",
  error: "border-l-status-error",
  comment: "border-l-muted-foreground",
  empty: "border-l-muted",
};

/* ------------------------------------------------------------------ */
/* Props                                                               */
/* ------------------------------------------------------------------ */

interface LineRowProps {
  line: DocumentLine;
  isSelected: boolean;
  totalLines: number;
  docId: string;
  editingComment: boolean;
  onCloseCommentEdit: () => void;
  onSelect: (position: number) => void;
  onEdit: (position: number) => void;
  onDelete: (position: number) => void;
  onInsertBelow: (position: number) => void;
  onToggleComment: (position: number) => void;
  onSwapUp: (position: number) => void;
  onSwapDown: (position: number) => void;
}

/* ------------------------------------------------------------------ */
/* Component                                                           */
/* ------------------------------------------------------------------ */

export function LineRow({
  line,
  isSelected,
  totalLines,
  docId,
  editingComment,
  onCloseCommentEdit,
  onSelect,
  onEdit,
  onDelete,
  onInsertBelow,
  onToggleComment,
  onSwapUp,
  onSwapDown,
}: LineRowProps) {
  const rowRef = useRef<HTMLDivElement>(null);

  const handleClick = useCallback(() => {
    onSelect(line.position);
  }, [line.position, onSelect]);

  const handleDoubleClick = useCallback(() => {
    onEdit(line.position);
  }, [line.position, onEdit]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      // Row-level shortcuts are handled by the parent via global handler.
      // Enter or Space to enter edit mode.
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onEdit(line.position);
      }
    },
    [line.position, onEdit],
  );

  const isComment = line.status === "comment";
  const isEmpty = line.status === "empty" || line.raw_text.trim() === "";

  return (
    <div
      ref={rowRef}
      role="row"
      tabIndex={0}
      data-position={line.position}
      className={cn(
        "group flex items-stretch border-l-[3px] transition-colors",
        borderColors[line.status] ?? "border-l-transparent",
        isSelected
          ? "bg-accent/60"
          : "hover:bg-accent/30",
        line.is_conflict && "ring-1 ring-inset ring-purple-500/30",
      )}
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onKeyDown={handleKeyDown}
    >
      {/* Line number */}
      <div className="flex w-10 shrink-0 items-center justify-end pr-2 text-2xs tabular-nums text-muted-foreground/50 select-none">
        {line.position + 1}
      </div>

      {/* Status dots */}
      <div className="flex w-10 shrink-0 items-center justify-center gap-1">
        <StatusBadge status={line.status} />
        {line.is_conflict && <ConflictBadge />}
      </div>

      {/* Raw text / inline comment editor */}
      {editingComment ? (
        <div className="flex-1 py-0.5 pl-2 pr-2">
          <InlineCommentEditor
            docId={docId}
            position={line.position}
            initialText={line.raw_text}
            onClose={onCloseCommentEdit}
          />
        </div>
      ) : (
        <div
          className={cn(
            "flex-1 truncate py-1 pl-2 pr-2 font-mono text-xs leading-relaxed",
            isComment && "text-muted-foreground italic",
            isEmpty && "text-muted-foreground/50",
          )}
          title={line.raw_text}
        >
          {line.raw_text || "\u00A0"}
        </div>
      )}

      {/* Hover actions — only one primary button visible on hover + overflow */}
      <div className="flex w-16 shrink-0 items-center justify-end gap-0.5 pr-2 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
        <Button
          variant="ghost"
          size="icon-sm"
          className="h-6 w-6"
          onClick={(e) => {
            e.stopPropagation();
            onEdit(line.position);
          }}
          title="Edit (Enter)"
        >
          <Pencil className="h-3 w-3" />
        </Button>

        <LineOverflowMenu
          position={line.position}
          totalLines={totalLines}
          onDelete={onDelete}
          onInsertBelow={onInsertBelow}
          onToggleComment={onToggleComment}
          onSwapUp={onSwapUp}
          onSwapDown={onSwapDown}
        />
      </div>
    </div>
  );
}
