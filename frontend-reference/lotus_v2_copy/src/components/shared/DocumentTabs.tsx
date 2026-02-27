import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { FileText } from "lucide-react"
import type { DocumentTab } from "@/types"

interface DocumentTabsProps {
  activeTab: DocumentTab
  onTabChange: (tab: DocumentTab) => void
  showFilePath?: boolean
}

export function DocumentTabBar({ activeTab, onTabChange, showFilePath = true }: DocumentTabsProps) {
  return (
    <div className="border-b bg-muted/20 shrink-0">
      <Tabs value={activeTab} onValueChange={(v) => onTabChange(v as DocumentTab)}>
        <TabsList className="h-9 rounded-none bg-transparent px-2 gap-1">
          <TabsTrigger
            value="af"
            className="text-xs gap-1.5 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-b-none data-[state=active]:border-b-2 data-[state=active]:border-primary px-3"
          >
            <FileText className="h-3.5 w-3.5" />
            Activity Factor
            <Badge variant="outline" className="text-[9px] px-1 py-0 h-3.5 ml-0.5 border-amber-500/30 text-amber-600">
              modified
            </Badge>
          </TabsTrigger>
          <TabsTrigger
            value="mutex"
            className="text-xs gap-1.5 data-[state=active]:bg-background data-[state=active]:shadow-sm rounded-b-none data-[state=active]:border-b-2 data-[state=active]:border-primary px-3"
          >
            <FileText className="h-3.5 w-3.5" />
            Mutex
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {showFilePath && (
        <div className="px-4 py-1 bg-muted/10 border-t">
          <span className="text-[10px] text-muted-foreground font-mono">
            {activeTab === "af"
              ? "/path/to/ward/drive/cfg/my_block.af.dcfg"
              : "/path/to/ward/drive/cfg/my_block.mutex.dcfg"}
          </span>
        </div>
      )}
    </div>
  )
}
