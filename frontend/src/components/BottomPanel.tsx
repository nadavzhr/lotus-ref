import { cn } from "@/lib/utils"
import { useAppStore } from "@/store/app-store"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ProblemsView } from "@/components/ProblemsView"
import { TerminalView } from "@/components/TerminalView"
import { ChevronDown, ChevronUp } from "lucide-react"
import { Button } from "@/components/ui/button"

export function BottomPanel() {
  const open = useAppStore((s) => s.bottomPanelOpen)
  const tab = useAppStore((s) => s.bottomPanelTab)
  const setTab = useAppStore((s) => s.setBottomPanelTab)
  const toggle = useAppStore((s) => s.toggleBottomPanel)

  return (
    <div
      className={cn(
        "shrink-0 border-t flex flex-col transition-all duration-200",
        open ? "h-[240px]" : "h-0"
      )}
    >
      {open && (
        <>
          <div className="flex items-center justify-between px-2 py-1 bg-muted/30">
            <Tabs
              value={tab}
              onValueChange={setTab}
              className="h-auto"
            >
              <TabsList className="h-7">
                <TabsTrigger value="problems" className="text-xs h-6 px-2">
                  Problems
                </TabsTrigger>
                <TabsTrigger value="terminal" className="text-xs h-6 px-2">
                  Terminal
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <Button
              variant="ghost"
              size="icon-sm"
              onClick={toggle}
              className="h-6 w-6"
            >
              {open ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronUp className="h-3 w-3" />
              )}
            </Button>
          </div>

          <ScrollArea className="flex-1">
            {tab === "problems" && <ProblemsView />}
            {tab === "terminal" && <TerminalView />}
          </ScrollArea>
        </>
      )}
    </div>
  )
}
