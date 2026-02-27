import { useState, useRef, useCallback } from "react"
import { cn } from "@/lib/utils"
import { useTheme } from "@/hooks/useTheme"
import { useSplitter } from "@/hooks/useSplitter"
import { LineList } from "@/components/shared/LineList"
import { EditForm } from "@/components/shared/EditForm"
import { ChatWidget } from "@/components/shared/ChatWidget"
import { ProblemsPanel, ProblemsSummaryBar } from "@/components/shared/ProblemsPanel"
import type { DocumentTab } from "@/types"
import {
  Flower2,
  Sun,
  Moon,
  MessageSquare,
  FileText,
  Folder,
  Terminal,
  PanelLeftClose,
  PanelLeftOpen,
} from "lucide-react"

type RightPane = "edit" | "chat"

export function LayoutC() {
  const { theme, toggleTheme } = useTheme()
  const [selectedLine, setSelectedLine] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<DocumentTab>("af")
  const [rightPane, setRightPane] = useState<RightPane>("edit")
  const [explorerCollapsed, setExplorerCollapsed] = useState(false)

  // Left-center horizontal split (explorer | editor)
  const hContainerRef = useRef<HTMLDivElement>(null)
  const hSplit = useSplitter(25, "horizontal", hContainerRef, 15, 45)
  // Center-right horizontal split (editor | right pane)
  const rContainerRef = useRef<HTMLDivElement>(null)
  const rSplit = useSplitter(65, "horizontal", rContainerRef, 40, 85)
  // Vertical split (main | bottom)
  const [bottomHeight, setBottomHeight] = useState(160)
  const [bottomCollapsed, setBottomCollapsed] = useState(false)

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
        const maxH = Math.max(100, window.innerHeight - 250)
        setBottomHeight(Math.min(maxH, Math.max(60, startH + delta)))
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

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background text-foreground text-[13px]">
      {/* Title Bar */}
      <div className="h-8 border-b bg-muted/40 flex items-center px-2 shrink-0 gap-2">
        <Flower2 className="h-4 w-4 text-primary" />
        <span className="text-[11px] font-semibold">Lotus v2 — Workspace</span>
        <div className="ml-auto flex items-center gap-2">
          <span className="text-[10px] text-muted-foreground font-mono">my_block</span>
          <button
            onClick={toggleTheme}
            className="p-0.5 rounded hover:bg-accent transition-colors text-muted-foreground"
          >
            {theme === "dark" ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
          </button>
        </div>
      </div>

      {/* Main Area */}
      <div className="flex-1 min-h-0 flex flex-col">
        {/* Upper workspace */}
        <div className="flex-1 min-h-0 flex flex-row" ref={hContainerRef}>
          {/* Left: Explorer / Line List */}
          {!explorerCollapsed && (
            <>
              <div className="h-full overflow-hidden flex flex-col" style={{ width: `${hSplit.pct}%` }}>
                <div className="flex items-center justify-between px-2 py-1 border-b bg-muted/20 shrink-0">
                  <div className="flex items-center gap-1.5">
                    <Folder className="h-3 w-3 text-muted-foreground" />
                    <span className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
                      Explorer
                    </span>
                  </div>
                  <button
                    onClick={() => setExplorerCollapsed(true)}
                    className="p-0.5 rounded hover:bg-accent transition-colors text-muted-foreground"
                  >
                    <PanelLeftClose className="h-3 w-3" />
                  </button>
                </div>
                {/* Document Type Tabs (compact) */}
                <div className="flex border-b shrink-0">
                  <button
                    onClick={() => setActiveTab("af")}
                    className={cn(
                      "flex-1 text-[10px] py-1 text-center border-b-2 transition-colors",
                      activeTab === "af"
                        ? "border-primary text-foreground bg-background"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    )}
                  >
                    AF
                  </button>
                  <button
                    onClick={() => setActiveTab("mutex")}
                    className={cn(
                      "flex-1 text-[10px] py-1 text-center border-b-2 transition-colors",
                      activeTab === "mutex"
                        ? "border-primary text-foreground bg-background"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    )}
                  >
                    Mutex
                  </button>
                </div>
                <div className="flex-1 min-h-0">
                  <LineList selectedLine={selectedLine} onSelectLine={setSelectedLine} compact />
                </div>
              </div>
              <div className="relative w-0 shrink-0 z-10">
                <div
                  className="absolute inset-y-0 -left-[3px] w-[6px] cursor-col-resize hover:bg-primary/40 active:bg-primary/60 transition-colors"
                  onMouseDown={hSplit.onMouseDown}
                />
              </div>
            </>
          )}

          {/* Center + Right split */}
          <div className="flex-1 min-w-0 flex flex-row h-full" ref={rContainerRef}>
            {/* Center: Editor */}
            <div className="h-full overflow-hidden flex flex-col" style={{ width: `${rSplit.pct}%` }}>
              <div className="flex items-center px-2 py-1 border-b bg-muted/20 shrink-0 gap-2">
                {explorerCollapsed && (
                  <button
                    onClick={() => setExplorerCollapsed(false)}
                    className="p-0.5 rounded hover:bg-accent transition-colors text-muted-foreground mr-1"
                  >
                    <PanelLeftOpen className="h-3 w-3" />
                  </button>
                )}
                <FileText className="h-3 w-3 text-muted-foreground" />
                <span className="text-[10px] font-mono text-muted-foreground">
                  {activeTab === "af" ? "my_block.af.dcfg" : "my_block.mutex.dcfg"}
                </span>
              </div>
              <div className="flex-1 min-h-0">
                <EditForm selectedLine={selectedLine} activeTab={activeTab} />
              </div>
            </div>

            <div className="relative w-0 shrink-0 z-10">
              <div
                className="absolute inset-y-0 -left-[3px] w-[6px] cursor-col-resize hover:bg-primary/40 active:bg-primary/60 transition-colors"
                onMouseDown={rSplit.onMouseDown}
              />
            </div>

            {/* Right: Edit Details / Chat */}
            <div className="h-full overflow-hidden flex flex-col flex-1">
              <div className="flex items-center border-b bg-muted/20 shrink-0">
                <button
                  onClick={() => setRightPane("edit")}
                  className={cn(
                    "text-[10px] px-3 py-1.5 border-b-2 transition-colors",
                    rightPane === "edit"
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  Details
                </button>
                <button
                  onClick={() => setRightPane("chat")}
                  className={cn(
                    "text-[10px] px-3 py-1.5 border-b-2 transition-colors flex items-center gap-1",
                    rightPane === "chat"
                      ? "border-primary text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  )}
                >
                  <MessageSquare className="h-3 w-3" />
                  AI Chat
                </button>
              </div>
              <div className="flex-1 min-h-0">
                {rightPane === "edit" ? (
                  <div className="h-full p-3">
                    <div className="space-y-3">
                      <div>
                        <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                          Selection
                        </h4>
                        <p className="text-xs font-mono text-foreground">
                          {selectedLine ? `Line ${selectedLine}` : "No selection"}
                        </p>
                      </div>
                      <div className="h-px bg-border" />
                      <div>
                        <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                          Document
                        </h4>
                        <p className="text-xs text-foreground">{activeTab === "af" ? "Activity Factor" : "Mutex"}</p>
                        <p className="text-[10px] font-mono text-muted-foreground mt-0.5">
                          {activeTab === "af" ? "my_block.af.dcfg" : "my_block.mutex.dcfg"}
                        </p>
                      </div>
                      <div className="h-px bg-border" />
                      <div>
                        <h4 className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground mb-1.5">
                          Stats
                        </h4>
                        <div className="grid grid-cols-2 gap-y-1 text-[10px]">
                          <span className="text-muted-foreground">Total lines:</span>
                          <span className="font-mono">22</span>
                          <span className="text-muted-foreground">Valid:</span>
                          <span className="font-mono text-emerald-600">12</span>
                          <span className="text-muted-foreground">Warnings:</span>
                          <span className="font-mono text-amber-600">2</span>
                          <span className="text-muted-foreground">Errors:</span>
                          <span className="font-mono text-red-600">1</span>
                          <span className="text-muted-foreground">Conflicts:</span>
                          <span className="font-mono text-purple-600">3</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ) : (
                  <ChatWidget showHeader={false} />
                )}
              </div>
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
              "flex items-center justify-between px-2 py-0.5 bg-muted/30 hover:bg-muted/50 transition-colors shrink-0",
              !bottomCollapsed ? "cursor-row-resize" : "cursor-pointer"
            )}
          >
            <div className="flex items-center gap-2">
              <Terminal className="h-3 w-3 text-muted-foreground" />
              <span className="text-[10px] font-medium text-muted-foreground">
                Output
              </span>
              <ProblemsSummaryBar />
            </div>
          </button>
          {!bottomCollapsed && <ProblemsPanel compact />}
        </div>
      </div>

      {/* Compact Status Bar */}
      <div className="flex items-center justify-between px-2 py-0 bg-primary text-primary-foreground text-[9px] shrink-0 h-5">
        <div className="flex items-center gap-2">
          <span>Lotus v2.0.0-dev</span>
          <span>·</span>
          <span>{activeTab === "af" ? "my_block.af.dcfg" : "my_block.mutex.dcfg"}</span>
        </div>
        <div className="flex items-center gap-2">
          <span>22 lines</span>
          <span>·</span>
          <span>523,841 nets</span>
        </div>
      </div>
    </div>
  )
}
