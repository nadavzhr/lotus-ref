import { useEffect, useRef, useCallback } from "react";
import { AlertCircle, ChevronDown, ChevronUp, GitMerge, ScrollText, Terminal } from "lucide-react";
import { usePanelStore, type BottomTab } from "@/stores/panel-store";
import { useDocumentStore } from "@/stores/document-store";
import { useLogStore } from "@/stores/log-store";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { ProblemsPanel } from "./bottom-panel/ProblemsPanel";
import { ConflictsPanel } from "./bottom-panel/ConflictsPanel";
import { LogsPanel } from "./bottom-panel/LogsPanel";
import { TerminalPanel } from "./bottom-panel/TerminalPanel";

/* ------------------------------------------------------------------ */
/* Tab definitions                                                     */
/* ------------------------------------------------------------------ */

interface TabDef {
  id: BottomTab;
  label: string;
  icon: React.ElementType;
}

const TABS: TabDef[] = [
  { id: "problems",  label: "Problems",  icon: AlertCircle },
  { id: "conflicts", label: "Conflicts", icon: GitMerge },
  { id: "logs",      label: "Logs",      icon: ScrollText },
  { id: "terminal",  label: "Terminal",  icon: Terminal },
];

/* ------------------------------------------------------------------ */
/* Tiny inline badge                                                   */
/* ------------------------------------------------------------------ */

function CountBadge({ n, className }: { n: number; className?: string }) {
  if (n === 0) return null;
  return (
    <span
      className={cn(
        "ml-1 min-w-[16px] rounded-full px-1 py-px text-center text-[10px] font-semibold leading-none",
        className,
      )}
    >
      {n > 999 ? "999+" : n}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Aggregate problem/log/conflict counts                               */
/* ------------------------------------------------------------------ */

function useProblemCounts() {
  const documents = useDocumentStore((s) => s.documents);
  let errors = 0;
  let warnings = 0;
  let conflicts = 0;
  for (const doc of Object.values(documents)) {
    for (const line of doc.lines) {
      errors   += line.errors.length;
      warnings += line.warnings.length;
      if (line.is_conflict) conflicts += 1;
    }
  }
  return { errors, warnings, conflicts };
}

/* ------------------------------------------------------------------ */
/* BottomPanel                                                         */
/* ------------------------------------------------------------------ */

/**
 * Collapsible, resizable VS Code-style bottom panel.
 *
 * • Drag the top handle to resize.
 * • Click any tab label to open/switch; click the active tab to collapse.
 * • Keyboard: Ctrl+` toggles open/closed.
 */
export function BottomPanel() {
  const open          = usePanelStore((s) => s.bottomOpen);
  const height        = usePanelStore((s) => s.bottomHeight);
  const activeTab     = usePanelStore((s) => s.activeTab);
  const toggle        = usePanelStore((s) => s.toggleBottom);
  const setActiveTab  = usePanelStore((s) => s.setActiveTab);
  const setHeight     = usePanelStore((s) => s.setBottomHeight);

  const { errors, warnings, conflicts } = useProblemCounts();
  const logCount = useLogStore((s) => s.entries.length);

  /* ── Resize drag ─────────────────────────────────────────────────── */
  const dragStartY = useRef<number | null>(null);
  const dragStartH = useRef<number>(height);

  const onResizeMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragStartY.current = e.clientY;
      dragStartH.current = height;

      const onMouseMove = (ev: MouseEvent) => {
        if (dragStartY.current === null) return;
        // dragging upward increases delta → taller panel
        const delta = dragStartY.current - ev.clientY;
        setHeight(dragStartH.current + delta);
      };

      const onMouseUp = () => {
        dragStartY.current = null;
        window.removeEventListener("mousemove", onMouseMove);
        window.removeEventListener("mouseup", onMouseUp);
      };

      window.addEventListener("mousemove", onMouseMove);
      window.addEventListener("mouseup", onMouseUp);
    },
    [height, setHeight],
  );

  /* ── Keyboard shortcut ───────────────────────────────────────────── */
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.ctrlKey && e.key === "`") {
        e.preventDefault();
        toggle();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [toggle]);

  /* ── Per-tab badge ───────────────────────────────────────────────── */
  function tabBadge(id: BottomTab) {
    if (id === "problems") {
      return (
        <>
          {errors > 0 && (
            <CountBadge
              n={errors}
              className="bg-[hsl(var(--status-error)/0.15)] text-[hsl(var(--status-error))]"
            />
          )}
          {warnings > 0 && (
            <CountBadge
              n={warnings}
              className="bg-[hsl(var(--status-warning)/0.15)] text-[hsl(var(--status-warning))]"
            />
          )}
        </>
      );
    }
    if (id === "conflicts" && conflicts > 0) {
      return (
        <CountBadge
          n={conflicts}
          className="bg-[hsl(280_80%_60%/0.15)] text-[hsl(280_80%_60%)] dark:text-[hsl(280_70%_75%)]"
        />
      );
    }
    if (id === "logs" && logCount > 0) {
      return <CountBadge n={logCount} className="bg-muted text-muted-foreground" />;
    }
    return null;
  }

  return (
    <div className="shrink-0 bg-background">
      {/* ── Drag handle (only shown when open) ───────────────────────── */}
      {open && (
        <div
          onMouseDown={onResizeMouseDown}
          className="h-1 w-full cursor-ns-resize border-t transition-colors hover:bg-primary/30"
          title="Drag to resize"
          aria-hidden
        />
      )}

      {/* ── Tab bar ──────────────────────────────────────────────────── */}
      <div className={cn("flex h-8 items-stretch border-t", !open && "border-t")}>
        <div className="flex items-stretch">
          {TABS.map(({ id, label, icon: Icon }) => {
            const isActive = open && activeTab === id;
            return (
              <button
                key={id}
                onClick={() => {
                  if (isActive) {
                    // clicking active tab collapses the panel
                    toggle();
                  } else {
                    setActiveTab(id);
                    if (!open) toggle();
                  }
                }}
                className={cn(
                  "flex items-center gap-1.5 border-b-2 px-3 text-xs transition-colors",
                  "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
                  isActive
                    ? "border-primary text-foreground"
                    : "border-transparent text-muted-foreground hover:text-foreground",
                )}
              >
                <Icon className="h-3.5 w-3.5 shrink-0" />
                {label}
                {tabBadge(id)}
              </button>
            );
          })}
        </div>

        {/* right-side chevron toggle */}
        <div className="ml-auto flex items-center pr-1">
          <Button
            variant="ghost"
            size="icon-sm"
            onClick={toggle}
            title={open ? "Collapse panel  (Ctrl+`)" : "Expand panel  (Ctrl+`)"}
            aria-label={open ? "Collapse panel" : "Expand panel"}
            className="h-6 w-6"
          >
            {open ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronUp className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>
      </div>

      {/* ── Panel body ───────────────────────────────────────────────── */}
      {open && (
        <div className="overflow-hidden border-t" style={{ height }}>
          {activeTab === "problems"  && <ProblemsPanel />}
          {activeTab === "conflicts" && <ConflictsPanel />}
          {activeTab === "logs"      && <LogsPanel />}
          {activeTab === "terminal"  && <TerminalPanel />}
        </div>
      )}
    </div>
  );
}
