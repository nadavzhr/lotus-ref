import { useWorkspaceStore } from "@/stores/workspace-store";
import { useTabsStore } from "@/stores/tabs-store";
import { useDocumentStore } from "@/stores/document-store";

/**
 * Status bar — thin bar at the very bottom of the window.
 *
 * Left:  document info (type, line count, selection)
 * Right: WARD, CELL, save indicator
 */
export function StatusBar() {
  const ward = useWorkspaceStore((s) => s.ward);
  const cell = useWorkspaceStore((s) => s.cell);

  const activeTabId = useTabsStore((s) => s.activeTabId);
  const activeDoc = useDocumentStore((s) =>
    activeTabId ? s.documents[activeTabId] : undefined,
  );

  return (
    <footer className="flex h-6 shrink-0 items-center justify-between border-t bg-muted/50 px-3 text-2xs text-muted-foreground">
      {/* Left — document info */}
      <div className="flex items-center gap-3">
        {activeDoc ? (
          <>
            <span>{activeDoc.docType.toUpperCase()}</span>
            <span>{activeDoc.totalLines} lines</span>
            {activeDoc.selectedPosition !== null && (
              <span>Ln {activeDoc.selectedPosition + 1}</span>
            )}
          </>
        ) : (
          <span>Ready</span>
        )}
      </div>

      {/* Right — workspace context */}
      <div className="flex items-center gap-3">
        {ward && <span>WARD: {ward}</span>}
        {cell && <span>CELL: {cell}</span>}
      </div>
    </footer>
  );
}
