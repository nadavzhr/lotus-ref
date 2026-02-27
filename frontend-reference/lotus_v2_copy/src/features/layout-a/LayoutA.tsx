import { useState, useRef, useCallback } from "react"
import { cn } from "@/lib/utils"
import { useTheme } from "@/hooks/useTheme"
import { useSplitter } from "@/hooks/useSplitter"
import { LineList } from "@/components/shared/LineList"
import { EditForm } from "@/components/shared/EditForm"
import { ChatWidget } from "@/components/shared/ChatWidget"
import { ProblemsPanel, ProblemsSummaryBar } from "@/components/shared/ProblemsPanel"
import { StatusBar } from "@/components/shared/StatusBar"
import type { DocumentTab } from "@/types"
import {
  Flower2,
  FileText,
  MessageSquare,
  AlertTriangle,
  Sun,
  Moon,
  ChevronDown,
  ChevronUp,
  Settings,
} from "lucide-react"

type SidebarPage = "files" | "chat" | "problems" | "settings"

export function LayoutA() {
  const { theme, toggleTheme } = useTheme()
  const [selectedLine, setSelectedLine] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<DocumentTab>("af")
  const [activePage, setActivePage] = useState<SidebarPage>("files")
  const [bottomCollapsed, setBottomCollapsed] = useState(false)
  const [bottomHeight, setBottomHeight] = useState(180)
  const hSplit = useSplitter(40, "horizontal", 20, 70)

  const dragging = useRef(false)
  const didDrag = useRef(false)

  const onBottomDragStart = useCallback(
    (e: React.MouseEvent) => {
      if (bottomCollapsed) return
      e.preventDefault()
      dragging.current = true
      didDrag.current = false
      const startY = e.clientY
      const startH = bottomHeight

      const onMouseMove = (ev: MouseEvent) => {
        if (!dragging.current) return
        const delta = startY - ev.clientY
        if (Math.abs(delta) > 3) didDrag.current = true
        const maxH = Math.max(120, window.innerHeight - 300)
        setBottomHeight(Math.min(maxH, Math.max(80, startH + delta)))
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
    [bottomCollapsed, bottomHeight],
  )

  const handleBottomClick = useCallback(() => {
    if (didDrag.current) return
    setBottomCollapsed((c) => !c)
  }, [])

  const sidebarItems: { id: SidebarPage; icon: React.ReactNode; label: string }[] = [
    { id: "files", icon: <FileText className="h-5 w-5" />, label: "Files" },
    { id: "chat", icon: <MessageSquare className="h-5 w-5" />, label: "Chat" },
    { id: "problems", icon: <AlertTriangle className="h-5 w-5" />, label: "Problems" },
    { id: "settings", icon: <Settings className="h-5 w-5" />, label: "Settings" },
  ]

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background text-foreground">
      <div className="flex-1 min-h-0 flex flex-row">
        {/* Activity Bar (narrow icon sidebar) */}
        <div className="w-12 bg-muted/30 border-r flex flex-col items-center py-3 gap-1 shrink-0">
          <div className="mb-4">
            <Flower2 className="h-6 w-6 text-primary" />
          </div>
          {sidebarItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setActivePage(item.id)}
              title={item.label}
              className={cn(
                "w-10 h-10 rounded-lg flex items-center justify-center transition-colors",
                activePage === item.id
                  ? "bg-accent text-foreground"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              {item.icon}
            </button>
          ))}
          <div className="mt-auto flex flex-col gap-1">
            <button
              onClick={toggleTheme}
              title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
              className="w-10 h-10 rounded-lg flex items-center justify-center text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-colors"
            >
              {theme === "dark" ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
            </button>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 min-w-0 flex flex-col">
          {/* Document Tabs */}
          <div className="flex items-center border-b bg-muted/20 px-2 h-9 shrink-0">
            <button
              onClick={() => setActiveTab("af")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-t-md border-b-2 transition-colors",
                activeTab === "af"
                  ? "border-primary bg-background text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              <FileText className="h-3.5 w-3.5" />
              Activity Factor
            </button>
            <button
              onClick={() => setActiveTab("mutex")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-t-md border-b-2 transition-colors",
                activeTab === "mutex"
                  ? "border-primary bg-background text-foreground"
                  : "border-transparent text-muted-foreground hover:text-foreground"
              )}
            >
              <FileText className="h-3.5 w-3.5" />
              Mutex
            </button>
            <div className="ml-auto flex items-center gap-2 pr-2">
              <span className="text-[10px] text-muted-foreground font-mono">ward: /path/to/ward</span>
              <span className="text-[10px] text-muted-foreground">|</span>
              <span className="text-[10px] text-muted-foreground font-mono">cell: my_block</span>
            </div>
          </div>

          {/* Upper content area */}
          <div className="flex-1 min-h-0 flex flex-col">
            <div className="flex-1 min-h-0 flex flex-row">
              {/* Side panel content based on activePage */}
              {activePage === "chat" ? (
                <div className="w-72 border-r shrink-0 h-full">
                  <ChatWidget showHeader={false} />
                </div>
              ) : activePage === "problems" ? (
                <div className="w-72 border-r shrink-0 h-full">
                  <ProblemsPanel compact />
                </div>
              ) : activePage === "settings" ? (
                <div className="w-72 border-r shrink-0 h-full p-4">
                  <h3 className="text-sm font-semibold mb-3">Settings</h3>
                  <p className="text-xs text-muted-foreground">Application settings will appear here.</p>
                </div>
              ) : null}

              {/* Line List + Edit Panel */}
              <div className="flex-1 min-w-0 flex flex-row h-full" ref={hSplit.containerRef}>
                {activePage === "files" && (
                  <>
                    <div className="h-full overflow-hidden border-r" style={{ width: `${hSplit.pct}%` }}>
                      <LineList selectedLine={selectedLine} onSelectLine={setSelectedLine} />
                    </div>
                    <div className="relative w-0 shrink-0 z-10">
                      <div
                        className="absolute inset-y-0 -left-[3px] w-[6px] cursor-col-resize hover:bg-primary/40 active:bg-primary/60 transition-colors"
                        onMouseDown={hSplit.onMouseDown}
                      />
                    </div>
                  </>
                )}
                <div className="h-full overflow-hidden flex-1">
                  <EditForm selectedLine={selectedLine} activeTab={activeTab} />
                </div>
              </div>
            </div>

            {/* Bottom Panel */}
            <div
              className="flex flex-col border-t bg-background shrink-0"
              style={bottomCollapsed ? undefined : { height: `${bottomHeight}px` }}
            >
              <button
                onMouseDown={onBottomDragStart}
                onClick={handleBottomClick}
                className={cn(
                  "flex items-center justify-between px-3 py-1 bg-muted/30 hover:bg-muted/50 transition-colors shrink-0",
                  !bottomCollapsed ? "cursor-row-resize" : "cursor-pointer"
                )}
              >
                <div className="flex items-center gap-3">
                  <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                    Problems & Output
                  </span>
                  <ProblemsSummaryBar />
                </div>
                {bottomCollapsed ? (
                  <ChevronUp className="h-3.5 w-3.5 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
                )}
              </button>
              {!bottomCollapsed && <ProblemsPanel />}
            </div>
          </div>
        </div>
      </div>

      <StatusBar />
    </div>
  )
}
