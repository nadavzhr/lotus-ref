import { useState, useMemo } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { cn } from "@/lib/utils"
import {
  Search,
  AlertTriangle,
  CheckCircle2,
  MessageSquare,
  XCircle,
  Plus,
  Trash2,
  MoreHorizontal,
  ArrowUp,
  ArrowDown,
  MessageSquareOff,
} from "lucide-react"
import { useDocumentStore } from "@/hooks/useDocumentStore"
import type { LineStatus } from "@/types"

const statusConfig: Record<
  LineStatus,
  { dot: string; icon: typeof CheckCircle2 }
> = {
  valid: { dot: "bg-emerald-500", icon: CheckCircle2 },
  warning: { dot: "bg-amber-500", icon: AlertTriangle },
  error: { dot: "bg-red-500", icon: XCircle },
  comment: { dot: "bg-muted-foreground/50", icon: MessageSquare },
  conflict: { dot: "bg-purple-500", icon: AlertTriangle },
}

interface LineListPanelProps {
  selectedLine: number | null
  onSelectLine: (line: number | null) => void
}

export function LineListPanel({ selectedLine, onSelectLine }: LineListPanelProps) {
  const [filter, setFilter] = useState("")
  const { lines, totalLines, loading, deleteLine, insertLine, toggleComment, swapLines } =
    useDocumentStore()

  const filteredLines = useMemo(() => {
    if (!filter) return lines
    const lower = filter.toLowerCase()
    return lines.filter((l) => l.raw_text.toLowerCase().includes(lower))
  }, [lines, filter])

  const statusCounts = useMemo(() => {
    const counts = { valid: 0, warning: 0, error: 0, comment: 0, conflict: 0 }
    for (const l of lines) {
      counts[l.status]++
    }
    return counts
  }, [lines])

  return (
    <div className="flex flex-col h-full">
      {/* Search / Filter bar */}
      <div className="p-2 border-b shrink-0">
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
          <Input
            placeholder="Filter lines…"
            className="pl-8 h-8 text-xs"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
      </div>

      {/* Stats bar */}
      <div className="flex items-center gap-2 px-3 py-1.5 border-b bg-muted/30 shrink-0">
        <span className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
          Lines
        </span>
        <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-4">
          {totalLines}
        </Badge>
        <div className="ml-auto flex gap-1.5">
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
            <span className="text-[10px] text-muted-foreground">{statusCounts.valid}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-amber-500" />
            <span className="text-[10px] text-muted-foreground">{statusCounts.warning}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-red-500" />
            <span className="text-[10px] text-muted-foreground">{statusCounts.error}</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="h-1.5 w-1.5 rounded-full bg-purple-500" />
            <span className="text-[10px] text-muted-foreground">{statusCounts.conflict}</span>
          </div>
        </div>
      </div>

      {/* Lines list */}
      <ScrollArea className="flex-1 min-h-0 overflow-hidden">
        <div className="p-1">
          {loading && lines.length === 0 && (
            <div className="text-center py-8 text-xs text-muted-foreground">Loading lines…</div>
          )}
          {!loading && lines.length === 0 && (
            <div className="text-center py-8 text-xs text-muted-foreground">
              No lines. Load a document first.
            </div>
          )}
          {filteredLines.map((line) => {
            const config = statusConfig[line.status]
            return (
              <div key={line.position} className="flex items-center group">
                <button
                  onClick={() => onSelectLine(line.position)}
                  className={cn(
                    "flex-1 flex items-center gap-2 px-2.5 py-1.5 rounded-md text-left transition-colors",
                    "hover:bg-accent/60",
                    selectedLine === line.position && "bg-accent ring-1 ring-ring/20",
                  )}
                >
                  {/* Line number */}
                  <span className="text-[10px] text-muted-foreground font-mono w-5 text-right shrink-0">
                    {line.position + 1}
                  </span>

                  {/* Status dot */}
                  <div className={cn("h-2 w-2 rounded-full shrink-0", config.dot)} />

                  {/* Line text */}
                  <span
                    className={cn(
                      "text-xs font-mono truncate flex-1 min-w-0",
                      line.status === "comment" && "italic text-muted-foreground",
                    )}
                  >
                    {line.raw_text || "(empty)"}
                  </span>

                  {/* Conflict badge */}
                  {line.status === "conflict" && (
                    <Badge
                      variant="outline"
                      className="text-[9px] px-1 py-0 h-3.5 border-purple-500/30 text-purple-600 shrink-0"
                    >
                      conflict
                    </Badge>
                  )}
                </button>

                {/* Context menu button */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-accent transition-all shrink-0 mr-1">
                      <MoreHorizontal className="h-3.5 w-3.5 text-muted-foreground" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-44">
                    <DropdownMenuItem onClick={() => insertLine(line.position)}>
                      <Plus className="h-3.5 w-3.5 mr-2" /> Insert Above
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => insertLine(line.position + 1)}>
                      <Plus className="h-3.5 w-3.5 mr-2" /> Insert Below
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={() => toggleComment(line.position)}>
                      {line.is_comment ? (
                        <>
                          <MessageSquareOff className="h-3.5 w-3.5 mr-2" /> Uncomment
                        </>
                      ) : (
                        <>
                          <MessageSquare className="h-3.5 w-3.5 mr-2" /> Comment
                        </>
                      )}
                    </DropdownMenuItem>
                    {line.position > 0 && (
                      <DropdownMenuItem
                        onClick={() => swapLines(line.position, line.position - 1)}
                      >
                        <ArrowUp className="h-3.5 w-3.5 mr-2" /> Move Up
                      </DropdownMenuItem>
                    )}
                    {line.position < lines.length - 1 && (
                      <DropdownMenuItem
                        onClick={() => swapLines(line.position, line.position + 1)}
                      >
                        <ArrowDown className="h-3.5 w-3.5 mr-2" /> Move Down
                      </DropdownMenuItem>
                    )}
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      variant="destructive"
                      onClick={() => {
                        deleteLine(line.position)
                        if (selectedLine === line.position) onSelectLine(null)
                      }}
                    >
                      <Trash2 className="h-3.5 w-3.5 mr-2" /> Delete Line
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
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
          onClick={() => insertLine(selectedLine ?? lines.length)}
        >
          <Plus className="h-3.5 w-3.5" /> Insert
        </Button>
        <Button
          variant="destructive"
          size="sm"
          className="h-7 text-xs gap-1"
          disabled={selectedLine === null}
          onClick={() => {
            if (selectedLine !== null) {
              deleteLine(selectedLine)
              onSelectLine(null)
            }
          }}
        >
          <Trash2 className="h-3.5 w-3.5" /> Delete
        </Button>
      </div>
    </div>
  )
}
