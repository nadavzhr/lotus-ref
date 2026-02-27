import { useState, useRef, useCallback, useEffect } from "react"
import { TooltipProvider } from "@/components/ui/tooltip"
import { ThemeProvider } from "@/hooks/useTheme"
import { TopMenuBar } from "@/components/layout/TopMenuBar"
import { LineListPanel } from "@/components/layout/LineListPanel"
import { EditPanel } from "@/components/layout/EditPanel"
import { ChatPanel } from "@/components/layout/ChatPanel"
import { BottomPanel } from "@/components/layout/BottomPanel"
import { DocumentTabs } from "@/components/layout/DocumentTabs"
import * as api from "@/services/api"
import type { DocumentSummary, DocumentLine, StatusCounts } from "@/types/api"

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

      document.body.style.cursor = direction === "horizontal" ? "col-resize" : "row-resize"
      document.body.style.userSelect = "none"
      document.addEventListener("mousemove", onMouseMove)
      document.addEventListener("mouseup", onMouseUp)
    },
    [direction, min, max],
  )

  return { pct, containerRef, onMouseDown }
}

/* ── Config paths ─────────────────────────────────────────────────────── */
const CELL_NAME = "mycell"
const AF_DOC_ID = "af"
const MUTEX_DOC_ID = "mutex"
const AF_FILE = "data/cfg/mycell.af.dcfg"
const MUTEX_FILE = "data/cfg/mycell.mutex.dcfg"

function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [lines, setLines] = useState<DocumentLine[]>([])
  const [allLines, setAllLines] = useState<DocumentLine[]>([])
  const [selectedLinePos, setSelectedLinePos] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState(AF_DOC_ID)
  const [showChat, setShowChat] = useState(false)
  const [chatWidth, setChatWidth] = useState(320)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Horizontal splitter: line list / edit panel
  const hSplit = useSplitter(45, "horizontal", 20, 80)
  // Bottom panel height in pixels (when expanded)
  const [bottomHeight, setBottomHeight] = useState(200)

  /* ── Chat-panel drag-to-resize ──────────────────────────────────────── */
  const chatDragging = useRef(false)

  const onChatSplitterMouseDown = useCallback((e: React.MouseEvent) => {
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
  }, [chatWidth])

  /* ── Load documents on mount ────────────────────────────────────────── */
  const loadDocuments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      // Load both document types
      const afSummary = await api.loadDocument(AF_DOC_ID, AF_FILE, "af")
      const mutexSummary = await api.loadDocument(MUTEX_DOC_ID, MUTEX_FILE, "mutex")
      setDocuments([afSummary, mutexSummary])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load documents")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadDocuments()
  }, [loadDocuments])

  /* ── Fetch lines when active tab changes ────────────────────────────── */
  const fetchLines = useCallback(async () => {
    try {
      const data = await api.getLines(activeTab)
      setLines(data)
      setAllLines(data)
    } catch {
      setLines([])
      setAllLines([])
    }
  }, [activeTab])

  useEffect(() => {
    if (!loading && documents.length > 0) {
      fetchLines()
    }
  }, [activeTab, loading, documents.length, fetchLines])

  /* ── Refresh document summary ───────────────────────────────────────── */
  const refreshSummaries = useCallback(async () => {
    try {
      const docs = await api.listDocuments()
      setDocuments(docs)
    } catch {
      // ignore
    }
  }, [])

  /* ── Refresh both lines and summaries ───────────────────────────────── */
  const refreshAll = useCallback(async () => {
    await fetchLines()
    await refreshSummaries()
  }, [fetchLines, refreshSummaries])

  /* ── Filter lines ───────────────────────────────────────────────────── */
  const handleFilterChange = useCallback(
    (query: string) => {
      if (!query.trim()) {
        setLines(allLines)
        return
      }
      const q = query.toLowerCase()
      setLines(allLines.filter((l) => l.raw_text.toLowerCase().includes(q)))
    },
    [allLines],
  )

  /* ── Line operations ────────────────────────────────────────────────── */
  const handleInsert = useCallback(
    async (position: number) => {
      try {
        await api.insertLine(activeTab, position)
        await refreshAll()
      } catch {
        // ignore
      }
    },
    [activeTab, refreshAll],
  )

  const handleDelete = useCallback(
    async (position: number) => {
      try {
        await api.deleteLine(activeTab, position)
        setSelectedLinePos(null)
        await refreshAll()
      } catch {
        // ignore
      }
    },
    [activeTab, refreshAll],
  )

  const handleSave = useCallback(async () => {
    try {
      await api.saveDocument(activeTab)
    } catch {
      // ignore
    }
  }, [activeTab])

  const handleUndo = useCallback(async () => {
    try {
      await api.undo(activeTab)
      await refreshAll()
    } catch {
      // ignore
    }
  }, [activeTab, refreshAll])

  const handleRedo = useCallback(async () => {
    try {
      await api.redo(activeTab)
      await refreshAll()
    } catch {
      // ignore
    }
  }, [activeTab, refreshAll])

  /* ── Derived state ──────────────────────────────────────────────────── */
  const activeDoc = documents.find((d) => d.doc_id === activeTab)
  const statusCounts: StatusCounts = activeDoc?.status_counts ?? {}
  const selectedLine = selectedLinePos !== null
    ? allLines.find((l) => l.position === selectedLinePos) ?? null
    : null

  if (loading) {
    return (
      <ThemeProvider>
        <div className="h-screen w-screen flex items-center justify-center bg-background text-foreground">
          <div className="text-center">
            <p className="text-sm font-medium">Loading documents…</p>
            <p className="text-xs text-muted-foreground mt-1">Connecting to backend</p>
          </div>
        </div>
      </ThemeProvider>
    )
  }

  if (error) {
    return (
      <ThemeProvider>
        <div className="h-screen w-screen flex items-center justify-center bg-background text-foreground">
          <div className="text-center max-w-md">
            <p className="text-sm font-medium text-destructive">Failed to load</p>
            <p className="text-xs text-muted-foreground mt-1">{error}</p>
            <button
              onClick={loadDocuments}
              className="mt-3 px-4 py-2 rounded-md bg-primary text-primary-foreground text-xs"
            >
              Retry
            </button>
          </div>
        </div>
      </ThemeProvider>
    )
  }

  return (
    <ThemeProvider>
    <TooltipProvider>
      <div className="h-screen w-screen flex flex-col overflow-hidden bg-background text-foreground">
        {/* Top Menu Bar */}
        <TopMenuBar
          showChat={showChat}
          onToggleChat={() => setShowChat((v) => !v)}
          onSave={handleSave}
          onUndo={handleUndo}
          onRedo={handleRedo}
          cellName={CELL_NAME}
        />

        {/* Document Tabs */}
        <DocumentTabs
          activeTab={activeTab}
          onTabChange={(tab) => {
            setActiveTab(tab)
            setSelectedLinePos(null)
          }}
          documents={documents}
        />

        {/* Upper area: Line List + Edit + (optional) Chat */}
        <div className="flex-1 min-h-0 relative overflow-hidden">
          <div className="absolute inset-0 flex flex-row">
          {/* Line List + Edit (resizable pair) */}
          <div className="flex-1 min-w-0 flex flex-row h-full" ref={hSplit.containerRef}>
            {/* Line List Panel */}
            <div className="h-full overflow-hidden border-r" style={{ width: `${hSplit.pct}%` }}>
              <LineListPanel
                lines={lines}
                selectedLine={selectedLinePos}
                onSelectLine={setSelectedLinePos}
                statusCounts={statusCounts}
                onInsert={handleInsert}
                onDelete={handleDelete}
                onFilterChange={handleFilterChange}
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
              <EditPanel
                selectedLine={selectedLine}
                activeDocId={activeTab}
                activeDocType={activeDoc?.doc_type ?? "af"}
                onCommit={refreshAll}
                onCancel={() => setSelectedLinePos(null)}
              />
            </div>
          </div>

          {/* Chat Panel (togglable, resizable) */}
          {showChat && (
            <>
              {/* Invisible resize handle (hover to reveal) */}
              <div className="relative w-0 shrink-0 z-10">
                <div
                  className="absolute inset-y-0 -left-[3px] w-[6px] cursor-col-resize hover:bg-primary/40 active:bg-primary/60 transition-colors"
                  onMouseDown={onChatSplitterMouseDown}
                />
              </div>
              <div className="h-full shrink-0 overflow-hidden border-l" style={{ width: `${chatWidth}px` }}>
                <ChatPanel onClose={() => setShowChat(false)} />
              </div>
            </>
          )}
          </div>
        </div>

        {/* Bottom Panel – Problems & Log (resizable via its header) */}
        <BottomPanel
          height={bottomHeight}
          onHeightChange={setBottomHeight}
          lines={allLines}
          statusCounts={statusCounts}
          onProblemClick={(pos) => setSelectedLinePos(pos)}
        />

        {/* Status Bar */}
        <div className="flex items-center justify-between px-3 py-0.5 bg-primary text-primary-foreground text-[10px] shrink-0">
          <div className="flex items-center gap-3">
            <span>Lotus v2.0.0-dev</span>
            <span>|</span>
            <span>
              {activeDoc?.doc_type === "af" ? "AF" : "Mutex"}: {activeDoc?.file_path ?? ""}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span>{activeDoc?.total_lines ?? 0} lines</span>
            <span>|</span>
            <span>Cell: {CELL_NAME}</span>
          </div>
        </div>
      </div>
    </TooltipProvider>
    </ThemeProvider>
  )
}

export default App
