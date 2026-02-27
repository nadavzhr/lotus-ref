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
  Terminal,
  ScrollText,
} from "lucide-react"
import { useState, useRef, useCallback, useEffect } from "react"
import { Terminal as XTerminal } from "@xterm/xterm"
import { FitAddon } from "@xterm/addon-fit"
import "@xterm/xterm/css/xterm.css"
import { useTheme } from "@/hooks/useTheme"

interface BottomPanelProps {
  height: number
  onHeightChange: (h: number) => void
}

const mockProblems = [
  { id: 1, type: "error" as const, message: "Net 'invalid_net_xyz' not found in netlist", line: 10, file: "my_block.af.dcfg" },
  { id: 2, type: "warning" as const, message: "Regex 'irq_[0-9]+' matches 0 nets — possible typo", line: 20, file: "my_block.af.dcfg" },
  { id: 3, type: "warning" as const, message: "Bus 'addr_bus[0:15]' — 3 nets not found in template", line: 7, file: "my_block.af.dcfg" },
  { id: 4, type: "conflict" as const, message: "Conflict: Line 15 ('pll_out') overlaps with Line 8 ('ctrl_sig') on nets: pll_out_clk", line: 15, file: "my_block.af.dcfg" },
]

const mockLogs = [
  { time: "15:03:22", level: "INFO", message: "Application started" },
  { time: "15:03:23", level: "INFO", message: "Ward resolved: /path/to/ward" },
  { time: "15:03:23", level: "INFO", message: "Cell: my_block" },
  { time: "15:03:24", level: "INFO", message: "Loading SPICE netlist: /path/to/ward/netlists/spice/my_block.sp" },
  { time: "15:03:28", level: "INFO", message: "Netlist loaded: 142 templates, 523,841 nets" },
  { time: "15:03:28", level: "INFO", message: "Loading AF config: my_block.af.dcfg" },
  { time: "15:03:28", level: "INFO", message: "Parsed 20 lines (12 valid, 3 comments, 2 warnings, 1 error)" },
  { time: "15:03:29", level: "WARN", message: "Conflict detected between lines 8 and 15" },
  { time: "15:03:29", level: "INFO", message: "Loading Mutex config: my_block.mutex.dcfg" },
  { time: "15:03:29", level: "INFO", message: "Parsed 8 mutex groups" },
]

/* ── XTerm Terminal Tab ────────────────────────────────────────────────── */
const XTERM_THEMES = {
  dark: {
    background: "#09090b",
    foreground: "#fafafa",
    cursor: "#fafafa",
    cursorAccent: "#09090b",
    selectionBackground: "#27272a",
    black: "#09090b",
    red: "#ef4444",
    green: "#22c55e",
    yellow: "#eab308",
    blue: "#3b82f6",
    magenta: "#a855f7",
    cyan: "#06b6d4",
    white: "#fafafa",
    brightBlack: "#52525b",
    brightRed: "#f87171",
    brightGreen: "#4ade80",
    brightYellow: "#facc15",
    brightBlue: "#60a5fa",
    brightMagenta: "#c084fc",
    brightCyan: "#22d3ee",
    brightWhite: "#ffffff",
  },
  light: {
    background: "#fafafa",
    foreground: "#18181b",
    cursor: "#18181b",
    cursorAccent: "#fafafa",
    selectionBackground: "#d4d4d8",
    black: "#18181b",
    red: "#dc2626",
    green: "#16a34a",
    yellow: "#ca8a04",
    blue: "#2563eb",
    magenta: "#9333ea",
    cyan: "#0891b2",
    white: "#fafafa",
    brightBlack: "#71717a",
    brightRed: "#ef4444",
    brightGreen: "#22c55e",
    brightYellow: "#eab308",
    brightBlue: "#3b82f6",
    brightMagenta: "#a855f7",
    brightCyan: "#06b6d4",
    brightWhite: "#ffffff",
  },
}

function XTermTab() {
  const { theme } = useTheme()
  const containerRef = useRef<HTMLDivElement>(null)
  const termRef = useRef<XTerminal | null>(null)
  const fitRef = useRef<FitAddon | null>(null)

  // Sync xterm theme when app theme changes
  useEffect(() => {
    if (termRef.current) {
      termRef.current.options.theme = XTERM_THEMES[theme]
    }
  }, [theme])

  useEffect(() => {
    if (!containerRef.current || termRef.current) return

    const term = new XTerminal({
      fontSize: 12,
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      theme: XTERM_THEMES[theme],
      cursorBlink: true,
      convertEol: true,
    })

    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(containerRef.current)
    fit.fit()

    // Write a welcome message
    term.writeln("\x1b[1;36mLotus v2 Terminal\x1b[0m")
    term.writeln("\x1b[90mThis terminal will connect to the backend shell.\x1b[0m")
    term.writeln("")

    // Simple local echo for now (will be replaced with websocket to backend)
    let currentLine = ""
    const prompt = () => term.write("\x1b[32m$ \x1b[0m")
    prompt()

    term.onData((data) => {
      if (data === "\r") {
        term.writeln("")
        if (currentLine.trim()) {
          term.writeln(`\x1b[90m[echo] ${currentLine}\x1b[0m`)
        }
        currentLine = ""
        prompt()
      } else if (data === "\x7f") {
        // Backspace
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1)
          term.write("\b \b")
        }
      } else if (data >= " ") {
        currentLine += data
        term.write(data)
      }
    })

    termRef.current = term
    fitRef.current = fit

    // Resize observer
    const ro = new ResizeObserver(() => {
      try { fit.fit() } catch { /* ignore */ }
    })
    ro.observe(containerRef.current)

    return () => {
      ro.disconnect()
      term.dispose()
      termRef.current = null
      fitRef.current = null
    }
  }, [])

  return <div ref={containerRef} className="h-full w-full" />
}

export function BottomPanel({ height, onHeightChange }: BottomPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false)
  const dragging = useRef(false)
  const didDrag = useRef(false)

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      // Only start drag if expanded
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
        // Cap max height so the upper area retains at least ~200px
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
    // Only toggle collapse if the user didn't drag
    if (didDrag.current) return
    setIsCollapsed((c) => !c)
  }, [])

  const errorCount = mockProblems.filter((p) => p.type === "error").length
  const warningCount = mockProblems.filter((p) => p.type === "warning").length
  const conflictCount = mockProblems.filter((p) => p.type === "conflict").length

  return (
    <div
      className="flex flex-col border-t bg-background shrink-0"
      style={isCollapsed ? undefined : { height: `${height}px` }}
    >
      {/* Collapse/expand toggle bar — also acts as drag handle when expanded */}
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
                {mockProblems.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="log" className="text-[10px] h-6 data-[state=active]:bg-background">
              <ScrollText className="h-3 w-3 mr-1" />
              Log
            </TabsTrigger>
            <TabsTrigger value="terminal" className="text-[10px] h-6 data-[state=active]:bg-background">
              <Terminal className="h-3 w-3 mr-1" />
              Terminal
            </TabsTrigger>
          </TabsList>

          <TabsContent value="problems" className="m-0 flex-1 min-h-0">
            <ScrollArea className="flex-1">
              <div className="p-1">
                {mockProblems.map((problem) => (
                  <Button
                    key={problem.id}
                    variant="ghost"
                    className="w-full justify-start h-auto py-1.5 px-2.5 rounded-md hover:bg-accent/60"
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
                          {problem.file} : line {problem.line}
                        </p>
                      </div>
                    </div>
                  </Button>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="log" className="m-0 flex-1">
            <ScrollArea className="h-full">
              <div className="p-2 space-y-0.5">
                {mockLogs.map((log, i) => (
                  <div key={i} className="flex items-start gap-2 text-[11px] font-mono leading-relaxed">
                    <span className="text-muted-foreground shrink-0">{log.time}</span>
                    <span
                      className={
                        log.level === "WARN"
                          ? "text-amber-600 shrink-0 w-10"
                          : log.level === "ERROR"
                          ? "text-red-600 shrink-0 w-10"
                          : "text-muted-foreground shrink-0 w-10"
                      }
                    >
                      {log.level}
                    </span>
                    <span className="text-foreground/90">{log.message}</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="terminal" className="m-0 flex-1 min-h-0">
            <XTermTab />
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
