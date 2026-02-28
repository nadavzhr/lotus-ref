import { useEffect, useRef } from "react";
import { useLogStore } from "@/stores/log-store";
import { Button } from "@/components/ui/button";
import { Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

const LEVEL_CLASSES: Record<string, string> = {
  info: "text-foreground",
  warn: "text-[hsl(var(--status-warning))]",
  error: "text-[hsl(var(--status-error))]",
};

const LEVEL_PREFIX: Record<string, string> = {
  info: "INFO",
  warn: "WARN",
  error: "ERR ",
};

function fmt(d: Date): string {
  return d.toTimeString().slice(0, 8);
}

export function LogsPanel() {
  const entries = useLogStore((s) => s.entries);
  const clear = useLogStore((s) => s.clear);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new entries arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length]);

  return (
    <div className="flex h-full flex-col font-mono">
      {/* Toolbar */}
      <div className="flex shrink-0 items-center justify-end border-b px-2 py-0.5">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={clear}
          title="Clear logs"
          className="h-5 w-5"
        >
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>

      {/* Log lines */}
      <div className="flex-1 overflow-y-auto px-3 py-1">
        {entries.length === 0 ? (
          <p className="mt-2 text-xs text-muted-foreground">No log entries yet.</p>
        ) : (
          entries.map((e) => (
            <div key={e.id} className="flex gap-2 text-[11px] leading-5">
              <span className="shrink-0 text-muted-foreground">{fmt(e.timestamp)}</span>
              <span
                className={cn(
                  "shrink-0 font-semibold",
                  LEVEL_CLASSES[e.level] ?? "text-foreground",
                )}
              >
                {LEVEL_PREFIX[e.level] ?? e.level.toUpperCase()}
              </span>
              <span className={LEVEL_CLASSES[e.level] ?? "text-foreground"}>
                {e.message}
              </span>
            </div>
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
