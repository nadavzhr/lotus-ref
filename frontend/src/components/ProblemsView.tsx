import { useAppStore } from "@/store/app-store"
import { cn } from "@/lib/utils"
import {
  AlertCircle,
  AlertTriangle,
  GitCompareArrows,
} from "lucide-react"

const severityIcon = {
  error: <AlertCircle className="h-3.5 w-3.5 text-red-500 shrink-0" />,
  warning: <AlertTriangle className="h-3.5 w-3.5 text-amber-500 shrink-0" />,
  conflict: <GitCompareArrows className="h-3.5 w-3.5 text-purple-500 shrink-0" />,
}

const severityOrder = { error: 0, conflict: 1, warning: 2 }

export function ProblemsView() {
  const problems = useAppStore((s) => s.problems)
  const setScrollToLine = useAppStore((s) => s.setScrollToLine)
  const selectLine = useAppStore((s) => s.selectLine)

  const sorted = [...problems].sort(
    (a, b) => severityOrder[a.severity] - severityOrder[b.severity]
  )

  if (sorted.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-foreground py-8">
        No problems detected
      </div>
    )
  }

  return (
    <div className="divide-y divide-border/50">
      {sorted.map((p, i) => (
        <button
          key={`${p.position}-${p.severity}-${i}`}
          className={cn(
            "flex items-start gap-2 w-full text-left px-3 py-1.5 text-xs hover:bg-muted/50 transition-colors cursor-pointer"
          )}
          onClick={() => {
            selectLine(p.position)
            setScrollToLine(p.position)
          }}
        >
          {severityIcon[p.severity]}
          <span className="text-muted-foreground tabular-nums shrink-0 w-10">
            Ln {p.position + 1}
          </span>
          <span className="flex-1 truncate">{p.message}</span>
        </button>
      ))}
    </div>
  )
}
