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
import { useState, useRef, useCallback, useEffect, useMemo } from "react"
import { Terminal as XTerminal } from "@xterm/xterm"
import { FitAddon } from "@xterm/addon-fit"
import "@xterm/xterm/css/xterm.css"
import { useTheme } from "@/hooks/useTheme"
import { useDocumentStore } from "@/hooks/useDocumentStore"

interface BottomPanelProps {
  height: number
  onHeightChange: (h: number) => void
}

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
  const themeRef = useRef(theme)
  themeRef.current = theme

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
      theme: XTERM_THEMES[themeRef.current],
      cursorBlink: true,
      convertEol: true,
    })

    const fit = new FitAddon()
    term.loadAddon(fit)
    term.open(containerRef.current)
    fit.fit()

    term.writeln("\x1b[1;36mLotus v2 Terminal\x1b[0m")
    term.writeln("\x1b[90mThis terminal will connect to the backend shell.\x1b[0m")
    term.writeln("")

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

    const ro = new ResizeObserver(() => {
      try {
        fit.fit()
      } catch {
        /* ignore */
      }
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
  const { problems, logs } = useDocumentStore()

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

  const errorCount = useMemo(() => problems.filter((p) => p.type === "error").length, [problems])
  const warningCount = useMemo(
    () => problems.filter((p) => p.type === "warning").length,
    [problems],
  )
  const conflictCount = useMemo(
    () => problems.filter((p) => p.type === "conflict").length,
    [problems],
  )

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

      {/* Panel content */}
      {!isCollapsed && (
        <Tabs defaultValue="problems" className="flex-1 flex flex-col min-h-0 overflow-hidden">
          <TabsList className="w-full justify-start rounded-none border-b bg-transparent px-3 h-8">
            <TabsTrigger
              value="problems"
              className="text-[10px] h-6 data-[state=active]:bg-background"
            >
              Problems
              <Badge variant="destructive" className="ml-1.5 text-[9px] px-1 py-0 h-3.5">
                {problems.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="log" className="text-[10px] h-6 data-[state=active]:bg-background">
              <ScrollText className="h-3 w-3 mr-1" />
              Log
            </TabsTrigger>
            <TabsTrigger
              value="terminal"
              className="text-[10px] h-6 data-[state=active]:bg-background"
            >
              <Terminal className="h-3 w-3 mr-1" />
              Terminal
            </TabsTrigger>
          </TabsList>

          <TabsContent value="problems" className="m-0 flex-1 min-h-0">
            <ScrollArea className="flex-1">
              <div className="p-1">
                {problems.length === 0 && (
                  <div className="text-center py-4 text-xs text-muted-foreground">
                    No problems detected
                  </div>
                )}
                {problems.map((problem, i) => (
                  <Button
                    key={`${problem.line}-${problem.type}-${i}`}
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
                {logs.map((log, i) => (
                  <div
                    key={i}
                    className="flex items-start gap-2 text-[11px] font-mono leading-relaxed"
                  >
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
