import { useWorkspaceStore } from "@/stores/workspace-store";
import { useTabsStore } from "@/stores/tabs-store";
import { useDocumentStore } from "@/stores/document-store";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LoadDocumentButton } from "@/components/LoadDocumentButton";
import { Button } from "@/components/ui/button";
import { Undo2, Redo2, Save } from "lucide-react";
import { useCallback } from "react";

/**
 * Top toolbar — persistent header.
 *
 * Left:  App name + Open button + breadcrumb
 * Right: WARD/CELL context, undo/redo, save, theme toggle
 */
export function TopToolbar() {
  const ward = useWorkspaceStore((s) => s.ward);
  const cell = useWorkspaceStore((s) => s.cell);

  const activeTabId = useTabsStore((s) => s.activeTabId);
  const activeDoc = useDocumentStore((s) =>
    activeTabId ? s.documents[activeTabId] : undefined,
  );
  const undoFn = useDocumentStore((s) => s.undo);
  const redoFn = useDocumentStore((s) => s.redo);
  const saveFn = useDocumentStore((s) => s.saveDocument);

  const canUndo = activeDoc?.canUndo ?? false;
  const canRedo = activeDoc?.canRedo ?? false;
  const hasActiveDoc = !!activeDoc;

  const handleUndo = useCallback(() => {
    if (activeTabId) undoFn(activeTabId);
  }, [activeTabId, undoFn]);

  const handleRedo = useCallback(() => {
    if (activeTabId) redoFn(activeTabId);
  }, [activeTabId, redoFn]);

  const handleSave = useCallback(() => {
    if (activeTabId) saveFn(activeTabId);
  }, [activeTabId, saveFn]);

  return (
    <header className="flex h-11 shrink-0 items-center justify-between border-b bg-background px-4">
      {/* Left section */}
      <div className="flex items-center gap-3">
        <span className="text-sm font-semibold tracking-tight text-foreground">
          Lotus
        </span>
        <span className="text-xs text-muted-foreground">/</span>
        <span className="text-xs text-muted-foreground">
          {cell || "no cell"}
        </span>

        <div className="mx-1 h-4 w-px bg-border" />

        {/* Open document */}
        <LoadDocumentButton />
      </div>

      {/* Right section */}
      <div className="flex items-center gap-2">
        {/* Undo / Redo */}
        <div className="flex items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon-sm"
            disabled={!canUndo}
            onClick={handleUndo}
            aria-label="Undo"
            title="Undo (Ctrl+Z)"
          >
            <Undo2 className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            disabled={!canRedo}
            onClick={handleRedo}
            aria-label="Redo"
            title="Redo (Ctrl+Y)"
          >
            <Redo2 className="h-4 w-4" />
          </Button>
        </div>

        {/* Save */}
        <Button
          variant="ghost"
          size="icon-sm"
          disabled={!hasActiveDoc}
          onClick={handleSave}
          aria-label="Save"
          title="Save (Ctrl+S)"
        >
          <Save className="h-4 w-4" />
        </Button>

        {/* Separator */}
        <div className="mx-1 h-4 w-px bg-border" />

        {/* Workspace context */}
        {ward && (
          <span className="hidden text-2xs text-muted-foreground sm:inline">
            WARD: {ward}
          </span>
        )}
        {cell && (
          <span className="text-2xs text-muted-foreground">CELL: {cell}</span>
        )}

        <div className="mx-1 h-4 w-px bg-border" />

        {/* Theme toggle */}
        <ThemeToggle />
      </div>
    </header>
  );
}
