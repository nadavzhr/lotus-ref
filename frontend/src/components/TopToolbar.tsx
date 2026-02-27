import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import { useAppStore } from "@/store/app-store"
import { Save, Undo2, Redo2, FileText } from "lucide-react"

export function TopToolbar() {
  const doc = useAppStore((s) => s.document)

  return (
    <div className="flex h-10 shrink-0 items-center gap-2 border-b bg-background px-3 text-sm">
      <FileText className="h-4 w-4 text-muted-foreground" />

      {doc ? (
        <>
          <span className="font-medium truncate max-w-[200px]">
            {doc.file_path.split("/").pop()}
          </span>

          <Separator orientation="vertical" className="h-4" />

          <Badge variant="outline" className="text-[11px] font-normal">
            {doc.doc_type.toUpperCase()}
          </Badge>

          <Badge variant="secondary" className="text-[11px] font-normal">
            {doc.total_lines} lines
          </Badge>

          <Separator orientation="vertical" className="h-4" />

          <span className="text-muted-foreground text-xs truncate max-w-[280px]">
            {doc.doc_id}
          </span>

          <div className="ml-auto flex items-center gap-1">
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon-sm" disabled={!doc.can_undo}>
                  <Undo2 className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Undo</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon-sm" disabled={!doc.can_redo}>
                  <Redo2 className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Redo</TooltipContent>
            </Tooltip>

            <Separator orientation="vertical" className="h-4 mx-1" />

            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon-sm">
                  <Save className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Save</TooltipContent>
            </Tooltip>
          </div>
        </>
      ) : (
        <span className="text-muted-foreground">No document loaded</span>
      )}
    </div>
  )
}
