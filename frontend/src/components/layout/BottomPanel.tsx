import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  AlertTriangle,
  XCircle,
  Info,
  ChevronDown,
  ChevronUp,
  ScrollText,
} from "lucide-react"
import { useState, useRef, useCallback } from "react"
import type { DocumentLine, StatusCounts } from "@/types/api"

interface BottomPanelProps {
  height: number
  onHeightChange: (h: number) => void
  lines: DocumentLine[]
  statusCounts: StatusCounts
  onProblemClick: (position: number) => void
}

interface Problem {
  position: number
  type: "error" | "warning" | "conflict"
  message: string
  rawText: string
}

function extractProblems(lines: DocumentLine[]): Problem[] {
  const problems: Problem[] = []
  for (const line of lines) {
    if (line.status === "error") {
      for (const err of line.errors) {
        problems.push({
          position: line.position,
          type: "error",
          message: err,
          rawText: line.raw_text,
        })
      }
      if (line.errors.length === 0) {
        problems.push({
          position: line.position,
          type: "error",
          message: `Parse error on line ${line.position + 1}`,
          rawText: line.raw_text,
        })
      }
    }
    if (line.status === "warning") {
      for (const warn of line.warnings) {
        problems.push({
          position: line.position,
          type: "warning",
          message: warn,
          rawText: line.raw_text,
        })
      }
    }
    if (line.status === "conflict" && line.conflict_info) {
      problems.push({
        position: line.position,
        type: "conflict",
        message: `Conflict with line(s) ${line.conflict_info.conflicting_positions.map((p) => p + 1).join(", ")} on nets: ${line.conflict_info.shared_nets.join(", ")}`,
        rawText: line.raw_text,
      })
    }
  }
  return problems
}

export function BottomPanel({ height, onHeightChange, lines, statusCounts, onProblemClick }: BottomPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const dragging = useRef(false)
  const didDrag = useRef(false)

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (isCollapsed) return
      e.preventDefault()
      dragging.current = true
      didDrag.current = false
      const startY = e.clientY
      const startH = height

      const onMouseMove = (ev: MouseEvent) => {
        if (!dragging.current) return
        const delta = startY - ev.clientY
        if (Math.abs(delta) > 3) didDrag.current = true
        const maxH = Math.max(120, window.innerHeight - 300)
        onHeightChange(Math.min(maxH, Math.max(80, startH + delta)))
      }

      const onMouseUp = () => {
        dragging.current = false
        document.removeEventListener("mousemove", onMouseMove)
        document.removeEventListener("mouseup", onMouseUp)
        document.body.style.cursor = ""
        document.body.style.userSelect = ""
      }

      document.body.style.cursor = "row-resize"
      document.body.style.userSelect = "none"
      document.addEventListener("mousemove", onMouseMove)
      document.addEventListener("mouseup", onMouseUp)
    },
    [isCollapsed, height, onHeightChange],
  )

  const handleClick = useCallback(() => {
    if (didDrag.current) return
    setIsCollapsed((c) => !c)
  }, [])

  const problems = extractProblems(lines)
  const errorCount = statusCounts.error ?? 0
  const warningCount = statusCounts.warning ?? 0
  const conflictCount = statusCounts.conflict ?? 0

  return (
    <div
      className="flex flex-col border-t bg-background shrink-0"
      style={isCollapsed ? undefined : { height: `${height}px` }}
    >
      {/* Collapse/expand toggle bar */}
      <button
        onMouseDown={onMouseDown}
        onClick={handleClick}
        className={`flex items-center justify-between px-3 py-1 bg-muted/30 hover:bg-muted/50 transition-colors shrink-0 ${
          !isCollapsed ? "cursor-row-resize" : "cursor-pointer"
        }`}
      >
        <div className="flex items-center gap-3">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
            Problems & Output
          </span>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <XCircle className="h-3 w-3 text-red-500" />
              <span className="text-[10px] text-muted-foreground">{errorCount}</span>
            </div>
            <div className="flex items-center gap-1">
              <AlertTriangle className="h-3 w-3 text-amber-500" />
              <span className="text-[10px] text-muted-foreground">{warningCount}</span>
            </div>
            <div className="flex items-center gap-1">
              <Info className="h-3 w-3 text-purple-500" />
              <span className="text-[10px] text-muted-foreground">{conflictCount}</span>
            </div>
          </div>
        </div>
        {isCollapsed ? (
          <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
        )}
      </button>

      {/* Panel content (collapsible) */}
      {!isCollapsed && (
        <Tabs defaultValue="problems" className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <TabsList className="w-full justify-start rounded-none border-b bg-transparent px-3 h-8">
            <TabsTrigger value="problems" className="text-[10px] h-6 data-[state=active]:bg-background">
              Problems
              <Badge variant="destructive" className="ml-1.5 text-[9px] px-1 py-0 h-3.5">
                {problems.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="log" className="text-[10px] h-6 data-[state=active]:bg-background">
              <ScrollText className="h-3 w-3 mr-1" />
              Log
            </TabsTrigger>
          </TabsList>

          <TabsContent value="problems" className="m-0 flex-1 min-h-0">
            <ScrollArea className="flex-1">
              <div className="p-1">
                {problems.length === 0 ? (
                  <div className="px-3 py-4 text-xs text-muted-foreground text-center">
                    No problems found
                  </div>
                ) : (
                  problems.map((problem, i) => (
                    <Button
                      key={`${problem.position}-${i}`}
                      variant="ghost"
                      className="w-full justify-start h-auto py-1.5 px-2.5 rounded-md hover:bg-accent/60"
                      onClick={() => onProblemClick(problem.position)}
                    >
                      <div className="flex items-start gap-2 w-full">
                        {problem.type === "error" ? (
                          <XCircle className="h-3.5 w-3.5 text-red-500 mt-0.5 shrink-0" />
                        ) : problem.type === "conflict" ? (
                          <Info className="h-3.5 w-3.5 text-purple-500 mt-0.5 shrink-0" />
                        ) : (
                          <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                        )}
                        <div className="flex-1 text-left">
                          <p className="text-xs leading-tight">{problem.message}</p>
                          <p className="text-[10px] text-muted-foreground mt-0.5">
                            Line {problem.position + 1}
                          </p>
                        </div>
                      </div>
                    </Button>
                  ))
                )}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="log" className="m-0 flex-1">
            <ScrollArea className="h-full">
              <div className="p-2 text-xs text-muted-foreground font-mono text-center py-4">
                Connect to backend for live logs
              </div>
            </ScrollArea>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
