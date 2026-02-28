import { AlertCircle, AlertTriangle } from "lucide-react";
import { useDocumentStore } from "@/stores/document-store";
import { useTabsStore } from "@/stores/tabs-store";
import { cn } from "@/lib/utils";

interface Problem {
  severity: "error" | "warning";
  message: string;
  docId: string;
  filePath: string;
  /** 0-based line position */
  position: number;
}

function basename(filePath: string): string {
  return filePath.split(/[\\/]/).pop() ?? filePath;
}

export function ProblemsPanel() {
  const documents = useDocumentStore((s) => s.documents);
  const selectLine = useDocumentStore((s) => s.selectLine);
  const setActive = useTabsStore((s) => s.setActive);

  const problems: Problem[] = [];

  for (const [docId, doc] of Object.entries(documents)) {
    for (const line of doc.lines) {
      for (const msg of line.errors) {
        problems.push({
          severity: "error",
          message: msg,
          docId,
          filePath: doc.filePath,
          position: line.position,
        });
      }
      for (const msg of line.warnings) {
        problems.push({
          severity: "warning",
          message: msg,
          docId,
          filePath: doc.filePath,
          position: line.position,
        });
      }
    }
  }

  const errorCount = problems.filter((p) => p.severity === "error").length;
  const warnCount = problems.filter((p) => p.severity === "warning").length;

  const handleClick = (p: Problem) => {
    setActive(p.docId);
    selectLine(p.docId, p.position);
  };

  if (problems.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
        No problems detected.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      {/* Summary row */}
      <div className="flex items-center gap-3 border-b px-3 py-1 text-[11px] text-muted-foreground">
        {errorCount > 0 && (
          <span className="flex items-center gap-1 text-[hsl(var(--status-error))]">
            <AlertCircle className="h-3 w-3" />
            {errorCount} error{errorCount !== 1 ? "s" : ""}
          </span>
        )}
        {warnCount > 0 && (
          <span className="flex items-center gap-1 text-[hsl(var(--status-warning))]">
            <AlertTriangle className="h-3 w-3" />
            {warnCount} warning{warnCount !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {/* Problem list */}
      <div className="flex-1 overflow-y-auto">
        {problems.map((p, i) => (
          <button
            key={i}
            onClick={() => handleClick(p)}
            className={cn(
              "flex w-full items-start gap-2 px-3 py-1.5 text-left text-xs",
              "transition-colors hover:bg-accent/50 focus-visible:outline-none focus-visible:bg-accent/50",
            )}
          >
            {p.severity === "error" ? (
              <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[hsl(var(--status-error))]" />
            ) : (
              <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-[hsl(var(--status-warning))]" />
            )}
            <span className="flex-1 text-foreground">{p.message}</span>
            <span className="shrink-0 tabular-nums text-muted-foreground">
              {basename(p.filePath)}:{p.position + 1}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
