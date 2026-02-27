import { memo } from "react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { DocumentLine } from "@/types/api"
import {
  Pencil,
  MoreHorizontal,
  MessageSquare,
  Trash2,
  AlertCircle,
  AlertTriangle,
  GitCompareArrows,
  Hash,
  CheckCircle2,
} from "lucide-react"

interface DocumentLineRowProps {
  line: DocumentLine
  isSelected: boolean
  onClick: (pos: number, e: React.MouseEvent) => void
  onEdit: (pos: number) => void
}

const statusIcon: Record<string, React.ReactNode> = {
  ok: <CheckCircle2 className="h-3 w-3 text-emerald-500" />,
  warning: <AlertTriangle className="h-3 w-3 text-amber-500" />,
  error: <AlertCircle className="h-3 w-3 text-red-500" />,
  comment: <Hash className="h-3 w-3 text-muted-foreground" />,
  conflict: <GitCompareArrows className="h-3 w-3 text-purple-500" />,
}

export const DocumentLineRow = memo(function DocumentLineRow({
  line,
  isSelected,
  onClick,
  onEdit,
}: DocumentLineRowProps) {
  return (
    <div
      className={cn(
        "group flex h-8 items-center border-b border-border/50 px-2 text-[13px] font-mono cursor-pointer select-none transition-colors",
        isSelected && "bg-accent",
        !isSelected && "hover:bg-muted/50",
        line.status === "error" && "bg-red-500/5",
        line.status === "conflict" && "bg-purple-500/5"
      )}
      onClick={(e) => onClick(line.position, e)}
    >
      {/* Line number */}
      <span className="w-12 shrink-0 text-right pr-3 text-muted-foreground text-xs tabular-nums">
        {line.position + 1}
      </span>

      {/* Status icon */}
      <span className="w-5 shrink-0 flex items-center justify-center">
        {statusIcon[line.status]}
      </span>

      {/* Text content */}
      <span
        className={cn(
          "flex-1 truncate pl-2",
          line.status === "comment" && "text-muted-foreground italic"
        )}
      >
        {line.raw_text}
      </span>

      {/* Line actions - visible on hover */}
      <div className="shrink-0 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={(e) => {
                e.stopPropagation()
                onEdit(line.position)
              }}
            >
              <Pencil className="h-3 w-3" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>Edit line</TooltipContent>
        </Tooltip>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={(e) => e.stopPropagation()}
            >
              <MoreHorizontal className="h-3 w-3" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => onEdit(line.position)}>
              <Pencil className="h-3.5 w-3.5 mr-2" />
              Edit
            </DropdownMenuItem>
            <DropdownMenuItem>
              <MessageSquare className="h-3.5 w-3.5 mr-2" />
              Toggle Comment
            </DropdownMenuItem>
            <DropdownMenuItem className="text-destructive">
              <Trash2 className="h-3.5 w-3.5 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  )
})
