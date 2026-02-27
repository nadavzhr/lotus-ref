import { useState, useRef, useCallback, useEffect } from "react"
import { TooltipProvider } from "@/components/ui/tooltip"
import { ThemeProvider } from "@/hooks/useTheme"
import { DocumentProvider, useDocumentStore } from "@/hooks/useDocumentStore"
import { TopMenuBar } from "@/components/layout/TopMenuBar"
import { LineListPanel } from "@/components/layout/LineListPanel"
import { EditPanel } from "@/components/layout/EditPanel"
import { ChatPanel } from "@/components/layout/ChatPanel"
import { BottomPanel } from "@/components/layout/BottomPanel"
import { DocumentTabs } from "@/components/layout/DocumentTabs"
import { OpenFileDialog } from "@/components/layout/OpenFileDialog"

/* ── Drag-to-resize hook ──────────────────────────────────────────────── */
function useSplitter(
  initial: number,
  direction: "horizontal" | "vertical",
  min = 15,
  max = 85,
) {
  const [pct, setPct] = useState(initial)
  const dragging = useRef(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      dragging.current = true

      const onMouseMove = (ev: MouseEvent) => {
        if (!dragging.current || !containerRef.current) return
        const rect = containerRef.current.getBoundingClientRect()
        let ratio: number
        if (direction === "horizontal") {
          ratio = ((ev.clientX - rect.left) / rect.width) * 100
        } else {
          ratio = ((ev.clientY - rect.top) / rect.height) * 100
        }
        setPct(Math.min(max, Math.max(min, ratio)))
      }

      const onMouseUp = () => {
        dragging.current = false
        document.removeEventListener("mousemove", onMouseMove)
        document.removeEventListener("mouseup", onMouseUp)
        document.body.style.cursor = ""
        document.body.style.userSelect = ""
      }

      document.body.style.cursor =
        direction === "horizontal" ? "col-resize" : "row-resize"
      document.body.style.userSelect = "none"
      document.addEventListener("mousemove", onMouseMove)
      document.addEventListener("mouseup", onMouseUp)
    },
    [direction, min, max],
  )

  return { pct, containerRef, onMouseDown }
}

function AppContent() {
  const [selectedLine, setSelectedLine] = useState<number | null>(null)
  const [showChat, setShowChat] = useState(false)
  const [chatWidth, setChatWidth] = useState(320)
  const [openFileOpen, setOpenFileOpen] = useState(false)

  const store = useDocumentStore()

  // Horizontal splitter: line list / edit panel
  const hSplit = useSplitter(45, "horizontal", 20, 80)
  // Bottom panel height in pixels (when expanded)
  const [bottomHeight, setBottomHeight] = useState(200)

  // Refresh lines when active document changes
  useEffect(() => {
    if (store.activeDocId) {
      store.refreshLines()
    }
    setSelectedLine(null)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [store.activeDocId])

  /* ── Chat-panel drag-to-resize ──────────────────────────────────────── */
  const chatDragging = useRef(false)

  const onChatSplitterMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      chatDragging.current = true
      const startX = e.clientX
      const startW = chatWidth

      const onMouseMove = (ev: MouseEvent) => {
        if (!chatDragging.current) return
        const delta = startX - ev.clientX
        setChatWidth(Math.min(600, Math.max(240, startW + delta)))
      }

      const onMouseUp = () => {
        chatDragging.current = false
        document.removeEventListener("mousemove", onMouseMove)
        document.removeEventListener("mouseup", onMouseUp)
        document.body.style.cursor = ""
        document.body.style.userSelect = ""
      }

      document.body.style.cursor = "col-resize"
      document.body.style.userSelect = "none"
      document.addEventListener("mousemove", onMouseMove)
      document.addEventListener("mouseup", onMouseUp)
    },
    [chatWidth],
  )

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background text-foreground">
      {/* Top Menu Bar */}
      <TopMenuBar
        showChat={showChat}
        onToggleChat={() => setShowChat((v) => !v)}
        onOpenFile={() => setOpenFileOpen(true)}
      />

      {/* Document Tabs */}
      <DocumentTabs />

      {/* Upper area: Line List + Edit + (optional) Chat */}
      <div className="flex-1 min-h-0 relative overflow-hidden">
        <div className="absolute inset-0 flex flex-row">
          {/* Line List + Edit (resizable pair) */}
          <div
            className="flex-1 min-w-0 flex flex-row h-full"
            ref={hSplit.containerRef}
          >
            {/* Line List Panel */}
            <div
              className="h-full overflow-hidden border-r"
              style={{ width: `${hSplit.pct}%` }}
            >
              <LineListPanel
                selectedLine={selectedLine}
                onSelectLine={setSelectedLine}
              />
            </div>

            {/* Invisible resize handle (hover to reveal) */}
            <div className="relative w-0 shrink-0 z-10">
              <div
                className="absolute inset-y-0 -left-[3px] w-[6px] cursor-col-resize hover:bg-primary/40 active:bg-primary/60 transition-colors"
                onMouseDown={hSplit.onMouseDown}
              />
            </div>

            {/* Edit Panel */}
            <div className="h-full overflow-hidden flex-1">
              <EditPanel selectedLine={selectedLine} />
            </div>
          </div>

          {/* Chat Panel (togglable, resizable) */}
          {showChat && (
            <>
              <div className="relative w-0 shrink-0 z-10">
                <div
                  className="absolute inset-y-0 -left-[3px] w-[6px] cursor-col-resize hover:bg-primary/40 active:bg-primary/60 transition-colors"
                  onMouseDown={onChatSplitterMouseDown}
                />
              </div>
              <div
                className="h-full shrink-0 overflow-hidden border-l"
                style={{ width: `${chatWidth}px` }}
              >
                <ChatPanel onClose={() => setShowChat(false)} />
              </div>
            </>
          )}
        </div>
      </div>

      {/* Bottom Panel – Problems & Log (resizable via its header) */}
      <BottomPanel height={bottomHeight} onHeightChange={setBottomHeight} />

      {/* Status Bar */}
      <div className="flex items-center justify-between px-3 py-0.5 bg-primary text-primary-foreground text-[10px] shrink-0">
        <div className="flex items-center gap-3">
          <span>Lotus v2.0.0-dev</span>
          <span>|</span>
          <span>
            {store.activeDocId
              ? `${store.activeDocType?.toUpperCase()}: ${store.activeDocId}`
              : "No document loaded"}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span>{store.totalLines} lines</span>
          <span>|</span>
          <span>Problems: {store.problems.length}</span>
        </div>
      </div>

      {/* Open File Dialog */}
      <OpenFileDialog
        open={openFileOpen}
        onClose={() => setOpenFileOpen(false)}
      />
    </div>
  )
}

function App() {
  return (
    <ThemeProvider>
      <TooltipProvider>
        <DocumentProvider>
          <AppContent />
        </DocumentProvider>
      </TooltipProvider>
    </ThemeProvider>
  )
}

export default App
