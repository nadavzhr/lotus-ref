import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { FileText, X } from "lucide-react"
import { useDocumentStore } from "@/hooks/useDocumentStore"

export function DocumentTabs() {
  const { documents, activeDocId, setActiveDoc, closeDocument } = useDocumentStore()

  if (documents.length === 0) {
    return (
      <div className="border-b bg-muted/20 shrink-0 px-4 py-2">
        <span className="text-xs text-muted-foreground">No documents loaded. Use File → Open to load a document.</span>
      </div>
    )
  }

  return (
    <div className="border-b bg-muted/20 shrink-0">
      <Tabs value={activeDocId ?? undefined} onValueChange={setActiveDoc}>
        <TabsList className="h-9 rounded-none bg-transparent px-2 gap-1">
          {documents.map((doc) => (
            <TabsTrigger
              key={doc.doc_id}
              value={doc.doc_id}
              className="text-xs gap-1.5 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-b-none data-[state=active]:border-b-2 data-[state=active]:border-primary px-3 group"
            >
              <FileText className="h-3.5 w-3.5" />
              {doc.doc_type === "af" ? "Activity Factor" : "Mutex"}
              {doc.is_modified && (
                <Badge
                  variant="outline"
                  className="text-[9px] px-1 py-0 h-3.5 ml-0.5 border-amber-500/30 text-amber-600"
                >
                  modified
                </Badge>
              )}
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  closeDocument(doc.doc_id)
                }}
                className="ml-1 opacity-0 group-hover:opacity-100 hover:text-destructive transition-opacity"
              >
                <X className="h-3 w-3" />
              </button>
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* File path display */}
      {activeDocId && (
        <div className="px-4 py-1 bg-muted/10 border-t">
          <span className="text-[10px] text-muted-foreground font-mono">
            {documents.find((d) => d.doc_id === activeDocId)?.file_path ?? ""}
          </span>
        </div>
      )}
    </div>
  )
}
