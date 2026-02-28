import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Search, AlertTriangle, CheckCircle2, MessageSquare, XCircle, Plus, Trash2 } from "lucide-react"

// Mock data representing configuration lines
const mockLines = [
  { id: 1, text: "* Top-level clock nets", status: "comment" as const },
  { id: 2, text: "clk_core 0.45", status: "valid" as const },
  { id: 3, text: "clk_mem 0.38", status: "valid" as const },
  { id: 4, text: "clk_io 0.22 em", status: "valid" as const },
  { id: 5, text: "# Power rail overrides", status: "comment" as const },
  { id: 6, text: "data_bus[0:31] 0.15", status: "valid" as const },
  { id: 7, text: "addr_bus[0:15] 0.12", status: "warning" as const },
  { id: 8, text: "ctrl_sig 0.67 em sh", status: "valid" as const },
  { id: 9, text: "reset_n 0.01", status: "valid" as const },
  { id: 10, text: "invalid_net_xyz 0.50", status: "error" as const },
  { id: 11, text: "# Scan chain signals", status: "comment" as const },
  { id: 12, text: "scan_in 0.05", status: "valid" as const },
  { id: 13, text: "scan_out 0.05", status: "valid" as const },
  { id: 14, text: "scan_en 0.02", status: "valid" as const },
  { id: 15, text: "pll_out 0.90 em", status: "conflict" as const },
  { id: 16, text: "mem_wr_en 0.18", status: "valid" as const },
  { id: 17, text: "mem_rd_en 0.25", status: "valid" as const },
  { id: 18, text: "fifo_.*_ptr 0.30", status: "valid" as const },
  { id: 19, text: "dma_req[0:3] 0.08", status: "valid" as const },
  { id: 20, text: "irq_[0-9]+ 0.03", status: "warning" as const },
  { id: 21, text: "conflicting_net 0.50", status: "conflict" as const },
  { id: 22, text: "another_conflict 0.50", status: "conflict" as const },
]

const statusConfig = {
  valid: { color: "bg-emerald-500/15 text-emerald-700 border-emerald-500/20", icon: CheckCircle2, dot: "bg-emerald-500" },
  warning: { color: "bg-amber-500/15 text-amber-700 border-amber-500/20", icon: AlertTriangle, dot: "bg-amber-500" },
  error: { color: "bg-red-500/15 text-red-700 border-red-500/20", icon: XCircle, dot: "bg-red-500" },
  comment: { color: "bg-muted text-muted-foreground border-muted", icon: MessageSquare, dot: "bg-muted-foreground/50" },
  conflict: { color: "bg-purple-500/15 text-purple-700 border-purple-500/20", icon: AlertTriangle, dot: "bg-purple-500" },
}

interface LineListPanelProps {
  selectedLine: number | null
  onSelectLine: (line: number) => void
}

export function LineListPanel({ selectedLine, onSelectLine }: LineListPanelProps) {
  return (
    <div className="flex flex-col h-full">
      {/* Search / Filter bar */}
      <div className="p-2 border-b shrink-0">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Filter lines…"
            className="pl-8 h-8 text-xs"
          />
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b bg-muted/30 shrink-0">
        <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Lines</span>
        <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">{mockLines.length}</Badge>
        <div className="ml-auto flex gap-1.5">
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="text-[10px] text-muted-foreground">12</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            <span className="text-[10px] text-muted-foreground">2</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-red-500" />
            <span className="text-[10px] text-muted-foreground">1</span>
          </div>
        </div>
      </div>

      {/* Lines list */}
      <ScrollArea className="flex-1 min-h-0 overflow-hidden">
        <div className="p-1">
          {mockLines.map((line) => {
            const config = statusConfig[line.status]
            return (
              <button
                key={line.id}
                onClick={() => onSelectLine(line.id)}
                className={cn(
                  "w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left transition-colors",
                  "hover:bg-accent/60",
                  selectedLine === line.id && "bg-accent ring-1 ring-ring/20"
                )}
              >
                {/* Line number */}
                <span className="text-[10px] text-muted-foreground font-mono w-5 text-right shrink-0">
                  {line.id}
                </span>

                {/* Status dot */}
                <div className={cn("h-2 w-2 rounded-full shrink-0", config.dot)} />

                {/* Line text */}
                <span className={cn(
                  "text-xs font-mono truncate flex-1 min-w-0",
                  line.status === "comment" && "italic text-muted-foreground"
                )}>
                  {line.text}
                </span>

                {/* Conflict badge */}
                {line.status === "conflict" && (
                  <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5 border-purple-500/30 text-purple-600 shrink-0">
                    conflict
                  </Badge>
                )}
              </button>
            )
          })}
        </div>
      </ScrollArea>

      {/* Action bar: Insert / Delete */}
      <div className="flex items-center justify-between px-3 py-1.5 border-t bg-muted/20 shrink-0">
        <Button variant="outline" size="sm" className="h-7 text-xs gap-1">
          <Plus className="h-3.5 w-3.5" /> Insert
        </Button>
        <Button variant="destructive" size="sm" className="h-7 text-xs gap-1" disabled={!selectedLine}>
          <Trash2 className="h-3.5 w-3.5" /> Delete
        </Button>
      </div>
    </div>
  )
}
