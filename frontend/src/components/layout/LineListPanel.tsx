import { useState, useCallback } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Search, AlertTriangle, CheckCircle2, MessageSquare, XCircle, Plus, Trash2 } from "lucide-react"
import type { DocumentLine, StatusCounts } from "@/types/api"

const statusConfig = {
  ok: { icon: CheckCircle2, dot: "bg-emerald-500" },
  warning: { icon: AlertTriangle, dot: "bg-amber-500" },
  error: { icon: XCircle, dot: "bg-red-500" },
  comment: { icon: MessageSquare, dot: "bg-muted-foreground/50" },
  conflict: { icon: AlertTriangle, dot: "bg-purple-500" },
} as const

interface LineListPanelProps {
  lines: DocumentLine[]
  selectedLine: number | null
  onSelectLine: (position: number) => void
  statusCounts: StatusCounts
  onInsert: (position: number) => void
  onDelete: (position: number) => void
  onFilterChange: (query: string) => void
}

export function LineListPanel({
  lines,
  selectedLine,
  onSelectLine,
  statusCounts,
  onInsert,
  onDelete,
  onFilterChange,
}: LineListPanelProps) {
  const [filterText, setFilterText] = useState("")

  const handleFilterChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const val = e.target.value
      setFilterText(val)
      onFilterChange(val)
    },
    [onFilterChange],
  )

  return (
    <div className="flex flex-col h-full">
      {/* Search / Filter bar */}
      <div className="p-2 border-b shrink-0">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Filter lines…"
            className="pl-8 h-8 text-xs"
            value={filterText}
            onChange={handleFilterChange}
          />
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b bg-muted/30 shrink-0">
        <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">Lines</span>
        <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">{lines.length}</Badge>
        <div className="ml-auto flex gap-1.5">
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="text-[10px] text-muted-foreground">{statusCounts.ok ?? 0}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            <span className="text-[10px] text-muted-foreground">{statusCounts.warning ?? 0}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-red-500" />
            <span className="text-[10px] text-muted-foreground">{statusCounts.error ?? 0}</span>
          </div>
        </div>
      </div>

      {/* Lines list */}
      <ScrollArea className="flex-1 min-h-0 overflow-hidden">
        <div className="p-1">
          {lines.map((line) => {
            const config = statusConfig[line.status] ?? statusConfig.ok
            return (
              <button
                key={line.position}
                onClick={() => onSelectLine(line.position)}
                className={cn(
                  "w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left transition-colors",
                  "hover:bg-accent/60",
                  selectedLine === line.position && "bg-accent ring-1 ring-ring/20"
                )}
              >
                {/* Line number */}
                <span className="text-[10px] text-muted-foreground font-mono w-5 text-right shrink-0">
                  {line.position + 1}
                </span>

                {/* Status dot */}
                <div className={cn("h-2 w-2 rounded-full shrink-0", config.dot)} />

                {/* Line text */}
                <span className={cn(
                  "text-xs font-mono truncate flex-1 min-w-0",
                  line.status === "comment" && "italic text-muted-foreground"
                )}>
                  {line.raw_text || "(empty)"}
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
        <Button
          variant="outline"
          size="sm"
          className="h-7 text-xs gap-1"
          onClick={() => onInsert(selectedLine !== null ? selectedLine + 1 : lines.length)}
        >
          <Plus className="h-3.5 w-3.5" /> Insert
        </Button>
        <Button
          variant="destructive"
          size="sm"
          className="h-7 text-xs gap-1"
          disabled={selectedLine === null}
          onClick={() => { if (selectedLine !== null) onDelete(selectedLine) }}
        >
          <Trash2 className="h-3.5 w-3.5" /> Delete
        </Button>
      </div>
    </div>
  )
}
