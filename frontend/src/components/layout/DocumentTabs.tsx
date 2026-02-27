import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { FileText } from "lucide-react"
import type { DocumentSummary } from "@/types/api"

interface DocumentTabsProps {
  activeTab: string
  onTabChange: (tab: string) => void
  documents: DocumentSummary[]
}

export function DocumentTabs({ activeTab, onTabChange, documents }: DocumentTabsProps) {
  const activeDoc = documents.find((d) => d.doc_id === activeTab)

  return (
    <div className="border-b bg-muted/20 shrink-0">
      <Tabs value={activeTab} onValueChange={onTabChange}>
        <TabsList className="h-9 rounded-none bg-transparent px-2 gap-1">
          {documents.map((doc) => (
            <TabsTrigger
              key={doc.doc_id}
              value={doc.doc_id}
              className="text-xs gap-1.5 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-b-none data-[state=active]:border-b-2 data-[state=active]:border-primary px-3"
            >
              <FileText className="h-3.5 w-3.5" />
              {doc.doc_type === "af" ? "Activity Factor" : "Mutex"}
              {(doc.status_counts.warning ?? 0) > 0 || (doc.status_counts.error ?? 0) > 0 ? (
                <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5 ml-0.5 border-amber-500/30 text-amber-600">
                  modified
                </Badge>
              ) : null}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      {/* File path display */}
      {activeDoc && (
        <div className="px-4 py-1 bg-muted/10 border-t">
          <span className="text-[10px] text-muted-foreground font-mono">
            {activeDoc.file_path}
          </span>
        </div>
      )}
    </div>
  )
}
