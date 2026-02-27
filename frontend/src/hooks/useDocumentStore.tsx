import { createContext, useCallback, useContext, useState, type ReactNode } from "react"
import type { DocumentLine, DocumentSummary, LogEntry, Problem } from "@/types"
import * as api from "@/services/api"

interface DocumentStore {
  /* Documents */
  documents: DocumentSummary[]
  activeDocId: string | null
  activeDocType: "af" | "mutex" | null

  /* Lines for the active document */
  lines: DocumentLine[]
  totalLines: number
  loading: boolean
  error: string | null

  /* Problems & logs */
  problems: Problem[]
  logs: LogEntry[]

  /* Actions */
  loadDocument: (docId: string, filePath: string, docType: "af" | "mutex") => Promise<void>
  refreshDocuments: () => Promise<void>
  refreshLines: () => Promise<void>
  setActiveDoc: (docId: string) => void
  deleteLine: (position: number) => Promise<void>
  insertLine: (position: number) => Promise<void>
  toggleComment: (position: number) => Promise<void>
  swapLines: (posA: number, posB: number) => Promise<void>
  saveDocument: () => Promise<void>
  undoAction: () => Promise<void>
  redoAction: () => Promise<void>
  closeDocument: (docId: string) => Promise<void>
  addLog: (level: LogEntry["level"], message: string) => void
}

const DocumentContext = createContext<DocumentStore | null>(null)

function timestamp(): string {
  return new Date().toLocaleTimeString("en-GB", { hour12: false })
}

function deriveProblems(lines: DocumentLine[], filePath: string): Problem[] {
  const problems: Problem[] = []
  for (const line of lines) {
    for (const err of line.errors) {
      problems.push({ type: "error", message: err, line: line.position + 1, file: filePath })
    }
    for (const warn of line.warnings) {
      problems.push({ type: "warning", message: warn, line: line.position + 1, file: filePath })
    }
    for (const c of line.conflicts) {
      problems.push({ type: "conflict", message: c, line: line.position + 1, file: filePath })
    }
  }
  return problems
}

function deriveStatus(line: DocumentLine): DocumentLine["status"] {
  if (line.is_comment) return "comment"
  if (line.errors.length > 0) return "error"
  if (line.conflicts.length > 0) return "conflict"
  if (line.warnings.length > 0) return "warning"
  return "valid"
}

export function DocumentProvider({ children }: { children: ReactNode }) {
  const [documents, setDocuments] = useState<DocumentSummary[]>([])
  const [activeDocId, setActiveDocId] = useState<string | null>(null)
  const [activeDocType, setActiveDocType] = useState<"af" | "mutex" | null>(null)
  const [lines, setLines] = useState<DocumentLine[]>([])
  const [totalLines, setTotalLines] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [problems, setProblems] = useState<Problem[]>([])
  const [logs, setLogs] = useState<LogEntry[]>([
    { time: timestamp(), level: "INFO", message: "Lotus frontend initialized" },
  ])

  const addLog = useCallback((level: LogEntry["level"], message: string) => {
    setLogs((prev) => [...prev, { time: timestamp(), level, message }])
  }, [])

  const refreshDocuments = useCallback(async () => {
    try {
      const docs = await api.listDocuments()
      setDocuments(docs)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      addLog("ERROR", `Failed to list documents: ${msg}`)
    }
  }, [addLog])

  const refreshLines = useCallback(async () => {
    if (!activeDocId) return
    setLoading(true)
    try {
      const res = await api.getLines(activeDocId)
      const enriched = res.lines.map((l) => ({ ...l, status: deriveStatus(l) }))
      setLines(enriched)
      setTotalLines(res.total)

      const doc = documents.find((d) => d.doc_id === activeDocId)
      const filePath = doc?.file_path ?? activeDocId
      setProblems(deriveProblems(enriched, filePath))
      setError(null)
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
      addLog("ERROR", `Failed to fetch lines: ${msg}`)
    } finally {
      setLoading(false)
    }
  }, [activeDocId, documents, addLog])

  const loadDocumentAction = useCallback(
    async (docId: string, filePath: string, docType: "af" | "mutex") => {
      setLoading(true)
      try {
        const res = await api.loadDocument({ doc_id: docId, file_path: filePath, doc_type: docType })
        addLog("INFO", `Loaded ${docType} document: ${filePath} (${res.line_count} lines)`)
        setActiveDocId(docId)
        setActiveDocType(docType)
        await refreshDocuments()
      } catch (e) {
        const msg = e instanceof Error ? e.message : String(e)
        setError(msg)
        addLog("ERROR", `Failed to load document: ${msg}`)
      } finally {
        setLoading(false)
      }
    },
    [addLog, refreshDocuments],
  )

  const setActiveDoc = useCallback(
    (docId: string) => {
      setActiveDocId(docId)
      const doc = documents.find((d) => d.doc_id === docId)
      if (doc) {
        setActiveDocType(doc.doc_type as "af" | "mutex")
      }
    },
    [documents],
  )

  const deleteLineAction = useCallback(
    async (position: number) => {
      if (!activeDocId) return
      try {
        await api.deleteLine(activeDocId, position)
        addLog("INFO", `Deleted line ${position + 1}`)
        await refreshLines()
      } catch (e) {
        addLog("ERROR", `Delete failed: ${e instanceof Error ? e.message : String(e)}`)
      }
    },
    [activeDocId, addLog, refreshLines],
  )

  const insertLineAction = useCallback(
    async (position: number) => {
      if (!activeDocId) return
      try {
        await api.insertLine(activeDocId, position)
        addLog("INFO", `Inserted line at position ${position + 1}`)
        await refreshLines()
      } catch (e) {
        addLog("ERROR", `Insert failed: ${e instanceof Error ? e.message : String(e)}`)
      }
    },
    [activeDocId, addLog, refreshLines],
  )

  const toggleCommentAction = useCallback(
    async (position: number) => {
      if (!activeDocId) return
      try {
        await api.toggleComment(activeDocId, position)
        addLog("INFO", `Toggled comment on line ${position + 1}`)
        await refreshLines()
      } catch (e) {
        addLog("ERROR", `Toggle comment failed: ${e instanceof Error ? e.message : String(e)}`)
      }
    },
    [activeDocId, addLog, refreshLines],
  )

  const swapLinesAction = useCallback(
    async (posA: number, posB: number) => {
      if (!activeDocId) return
      try {
        await api.swapLines(activeDocId, posA, posB)
        addLog("INFO", `Swapped lines ${posA + 1} and ${posB + 1}`)
        await refreshLines()
      } catch (e) {
        addLog("ERROR", `Swap failed: ${e instanceof Error ? e.message : String(e)}`)
      }
    },
    [activeDocId, addLog, refreshLines],
  )

  const saveDocumentAction = useCallback(async () => {
    if (!activeDocId) return
    try {
      await api.saveDocument(activeDocId)
      addLog("INFO", `Saved document: ${activeDocId}`)
      await refreshDocuments()
    } catch (e) {
      addLog("ERROR", `Save failed: ${e instanceof Error ? e.message : String(e)}`)
    }
  }, [activeDocId, addLog, refreshDocuments])

  const undoActionFn = useCallback(async () => {
    if (!activeDocId) return
    try {
      await api.undo(activeDocId)
      addLog("INFO", "Undo")
      await refreshLines()
    } catch (e) {
      addLog("WARN", `Undo: ${e instanceof Error ? e.message : String(e)}`)
    }
  }, [activeDocId, addLog, refreshLines])

  const redoActionFn = useCallback(async () => {
    if (!activeDocId) return
    try {
      await api.redo(activeDocId)
      addLog("INFO", "Redo")
      await refreshLines()
    } catch (e) {
      addLog("WARN", `Redo: ${e instanceof Error ? e.message : String(e)}`)
    }
  }, [activeDocId, addLog, refreshLines])

  const closeDocumentAction = useCallback(
    async (docId: string) => {
      try {
        await api.closeDocument(docId)
        addLog("INFO", `Closed document: ${docId}`)
        if (activeDocId === docId) {
          setActiveDocId(null)
          setActiveDocType(null)
          setLines([])
          setTotalLines(0)
          setProblems([])
        }
        await refreshDocuments()
      } catch (e) {
        addLog("ERROR", `Close failed: ${e instanceof Error ? e.message : String(e)}`)
      }
    },
    [activeDocId, addLog, refreshDocuments],
  )

  return (
    <DocumentContext.Provider
      value={{
        documents,
        activeDocId,
        activeDocType,
        lines,
        totalLines,
        loading,
        error,
        problems,
        logs,
        loadDocument: loadDocumentAction,
        refreshDocuments,
        refreshLines,
        setActiveDoc,
        deleteLine: deleteLineAction,
        insertLine: insertLineAction,
        toggleComment: toggleCommentAction,
        swapLines: swapLinesAction,
        saveDocument: saveDocumentAction,
        undoAction: undoActionFn,
        redoAction: redoActionFn,
        closeDocument: closeDocumentAction,
        addLog,
      }}
    >
      {children}
    </DocumentContext.Provider>
  )
}

export function useDocumentStore() {
  const ctx = useContext(DocumentContext)
  if (!ctx) throw new Error("useDocumentStore must be used within DocumentProvider")
  return ctx
}
