import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Search, Plus, Trash2 } from "lucide-react"
import type { ConfigLine, LineStatus } from "@/types"
import { mockLines, getLineStats } from "@/services/mockData"

const statusDot: Record<LineStatus, string> = {
  valid: "bg-emerald-500",
  warning: "bg-amber-500",
  error: "bg-red-500",
  comment: "bg-muted-foreground/50",
  conflict: "bg-purple-500",
}

interface LineListProps {
  selectedLine: number | null
  onSelectLine: (line: number) => void
  compact?: boolean
}

function LineItem({
  line,
  isSelected,
  onSelect,
}: {
  line: ConfigLine
  isSelected: boolean
  onSelect: () => void
}) {
  return (
    <button
      onClick={onSelect}
      className={cn(
        "w-full flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left transition-colors",
        "hover:bg-accent/60",
        isSelected && "bg-accent ring-1 ring-ring/20"
      )}
    >
      <span className="text-[10px] text-muted-foreground font-mono w-5 text-right shrink-0">
        {line.id}
      </span>
      <div className={cn("h-2 w-2 rounded-full shrink-0", statusDot[line.status])} />
      <span
        className={cn(
          "text-xs font-mono truncate flex-1 min-w-0",
          line.status === "comment" && "italic text-muted-foreground"
        )}
      >
        {line.text}
      </span>
      {line.status === "conflict" && (
        <Badge
          variant="outline"
          className="text-[9px] px-1 py-0 h-3.5 border-purple-500/30 text-purple-600 shrink-0"
        >
          conflict
        </Badge>
      )}
    </button>
  )
}

export function LineList({ selectedLine, onSelectLine, compact }: LineListProps) {
  const stats = getLineStats(mockLines)

  return (
    <div className="flex flex-col h-full">
      <div className={cn("border-b shrink-0", compact ? "p-1.5" : "p-2")}>
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input placeholder="Filter lines…" className="pl-8 h-8 text-xs" />
        </div>
      </div>

      <div className="flex items-center gap-2 px-3 py-1.5 border-b bg-muted/30 shrink-0">
        <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
          Lines
        </span>
        <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
          {stats.total}
        </Badge>
        <div className="ml-auto flex gap-1.5">
          <StatusDot color="bg-emerald-500" count={stats.valid} />
          <StatusDot color="bg-amber-500" count={stats.warnings} />
          <StatusDot color="bg-red-500" count={stats.errors} />
        </div>
      </div>

      <ScrollArea className="flex-1 min-h-0 overflow-hidden">
        <div className="p-1">
          {mockLines.map((line) => (
            <LineItem
              key={line.id}
              line={line}
              isSelected={selectedLine === line.id}
              onSelect={() => onSelectLine(line.id)}
            />
          ))}
        </div>
      </ScrollArea>

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

function StatusDot({ color, count }: { color: string; count: number }) {
  return (
    <div className="flex items-center gap-1">
      <div className={cn("h-1.5 w-1.5 rounded-full", color)} />
      <span className="text-[10px] text-muted-foreground">{count}</span>
    </div>
  )
}

