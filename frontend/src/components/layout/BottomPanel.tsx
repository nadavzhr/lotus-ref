import { usePanelStore } from "@/stores/panel-store";
import { Button } from "@/components/ui/button";
import { ChevronUp, ChevronDown } from "lucide-react";

/**
 * BottomPanel — collapsible panel for Problems / Logs / Terminal.
 * Phase 4 content; skeleton only for now.
 */
export function BottomPanel() {
  const open = usePanelStore((s) => s.bottomOpen);
  const height = usePanelStore((s) => s.bottomHeight);
  const toggle = usePanelStore((s) => s.toggleBottom);

  return (
    <div className="shrink-0 border-t bg-background">
      {/* Toggle bar — always visible */}
      <div className="flex h-7 items-center gap-2 px-3">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={toggle}
          aria-label={open ? "Collapse panel" : "Expand panel"}
          className="h-5 w-5"
        >
          {open ? (
            <ChevronDown className="h-3.5 w-3.5" />
          ) : (
            <ChevronUp className="h-3.5 w-3.5" />
          )}
        </Button>
        <span className="text-2xs text-muted-foreground">Problems</span>
        <span className="text-2xs text-muted-foreground">Logs</span>
      </div>

      {/* Panel body */}
      {open && (
        <div
          className="overflow-auto border-t px-3 py-2 text-xs text-muted-foreground"
          style={{ height }}
        >
          {/* Phase 4: render tab content here */}
          <p>No problems detected.</p>
        </div>
      )}
    </div>
  );
}
