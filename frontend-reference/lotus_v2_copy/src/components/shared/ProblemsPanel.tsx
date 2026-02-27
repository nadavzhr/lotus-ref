import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { AlertTriangle, XCircle, Info, ScrollText } from "lucide-react"
import { mockProblems, mockLogs, getProblemStats } from "@/services/mockData"

interface ProblemsPanelProps {
  compact?: boolean
}

export function ProblemsPanel({ compact }: ProblemsPanelProps) {
  return (
    <Tabs defaultValue="problems" className="flex-1 flex flex-col min-h-0 overflow-hidden">
      <TabsList className="w-full justify-start rounded-none border-b bg-transparent px-3 h-8">
        <TabsTrigger value="problems" className="text-[10px] h-6 data-[state=active]:bg-background">
          Problems
          <Badge variant="destructive" className="ml-1.5 text-[9px] px-1 py-0 h-3.5">
            {mockProblems.length}
          </Badge>
        </TabsTrigger>
        <TabsTrigger value="log" className="text-[10px] h-6 data-[state=active]:bg-background">
          <ScrollText className="h-3 w-3 mr-1" />
          Log
        </TabsTrigger>
      </TabsList>

      <TabsContent value="problems" className="m-0 flex-1 min-h-0">
        <ScrollArea className="flex-1">
          <div className="p-1">
            {mockProblems.map((problem) => (
              <Button
                key={problem.id}
                variant="ghost"
                className="w-full justify-start h-auto py-1.5 px-2.5 rounded-md hover:bg-accent/60"
              >
                <div className="flex items-start gap-2 w-full">
                  {problem.type === "error" ? (
                    <XCircle className="h-3.5 w-3.5 text-red-500 mt-0.5 shrink-0" />
                  ) : problem.type === "conflict" ? (
                    <Info className="h-3.5 w-3.5 text-purple-500 mt-0.5 shrink-0" />
                  ) : (
                    <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
                  )}
                  <div className="flex-1 text-left">
                    <p className={compact ? "text-[10px] leading-tight" : "text-xs leading-tight"}>
                      {problem.message}
                    </p>
                    <p className="text-[10px] text-muted-foreground mt-0.5">
                      {problem.file} : line {problem.line}
                    </p>
                  </div>
                </div>
              </Button>
            ))}
          </div>
        </ScrollArea>
      </TabsContent>

      <TabsContent value="log" className="m-0 flex-1">
        <ScrollArea className="h-full">
          <div className="p-2 space-y-0.5">
            {mockLogs.map((log, i) => (
              <div key={i} className="flex items-start gap-2 text-[11px] font-mono leading-relaxed">
                <span className="text-muted-foreground shrink-0">{log.time}</span>
                <span
                  className={
                    log.level === "WARN"
                      ? "text-amber-600 shrink-0 w-10"
                      : log.level === "ERROR"
                        ? "text-red-600 shrink-0 w-10"
                        : "text-muted-foreground shrink-0 w-10"
                  }
                >
                  {log.level}
                </span>
                <span className="text-foreground/90">{log.message}</span>
              </div>
            ))}
          </div>
        </ScrollArea>
      </TabsContent>
    </Tabs>
  )
}

export function ProblemsSummaryBar() {
  const stats = getProblemStats(mockProblems)

  return (
    <div className="flex items-center gap-3">
      <div className="flex items-center gap-1">
        <XCircle className="h-3 w-3 text-red-500" />
        <span className="text-[10px] text-muted-foreground">{stats.errors}</span>
      </div>
      <div className="flex items-center gap-1">
        <AlertTriangle className="h-3 w-3 text-amber-500" />
        <span className="text-[10px] text-muted-foreground">{stats.warnings}</span>
      </div>
      <div className="flex items-center gap-1">
        <Info className="h-3 w-3 text-purple-500" />
        <span className="text-[10px] text-muted-foreground">{stats.conflicts}</span>
      </div>
    </div>
  )
}
