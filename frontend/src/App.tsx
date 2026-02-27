import { useEffect } from "react"
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query"
import { TooltipProvider } from "@/components/ui/tooltip"
import { MainLayout } from "@/layout/MainLayout"
import { useThemeInit } from "@/hooks/use-theme-init"
import { useAppStore } from "@/store/app-store"
import { MOCK_LINES, MOCK_SUMMARY } from "@/lib/mock-data"
import * as api from "@/lib/api"
import type { DocumentLine } from "@/types/api"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
    },
  },
})

function AppInner() {
  useThemeInit()

  const doc = useAppStore((s) => s.document)
  const setDocument = useAppStore((s) => s.setDocument)
  const setConnected = useAppStore((s) => s.setConnected)
  const updateProblemsFromLines = useAppStore((s) => s.updateProblemsFromLines)

  // Try to load document list from backend on mount
  const { data: documents } = useQuery({
    queryKey: ["documents"],
    queryFn: api.listDocuments,
    retry: false,
  })

  // If backend has documents, load the first one
  useEffect(() => {
    if (documents && documents.length > 0 && !doc) {
      setDocument(documents[0])
      setConnected(true)
    } else if (documents && documents.length === 0 && !doc) {
      // Backend is up but no documents - use mock
      setDocument(MOCK_SUMMARY)
      setConnected(true)
    }
  }, [documents, doc, setDocument, setConnected])

  // Fallback: if backend is not available, use mock data
  useEffect(() => {
    const timer = setTimeout(() => {
      if (!doc) {
        setDocument(MOCK_SUMMARY)
        setConnected(false)
      }
    }, 2000)
    return () => clearTimeout(timer)
  }, [doc, setDocument, setConnected])

  // Fetch lines from backend if we have a real document
  const { data: linesData } = useQuery({
    queryKey: ["lines", doc?.doc_id],
    queryFn: () =>
      doc ? api.getLines(doc.doc_id) : Promise.resolve([] as DocumentLine[]),
    enabled: !!doc,
    retry: false,
  })

  // Use backend lines or fall back to mock
  const lines = linesData && linesData.length > 0 ? linesData : MOCK_LINES

  // Update problems whenever lines change
  useEffect(() => {
    updateProblemsFromLines(lines)
  }, [lines, updateProblemsFromLines])

  return (
    <TooltipProvider delayDuration={300}>
      <MainLayout lines={lines} />
    </TooltipProvider>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
    </QueryClientProvider>
  )
}
