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
import { Separator } from "@/components/ui/separator"
import { useAppStore } from "@/store/app-store"
import {
  AlertCircle,
  AlertTriangle,
  GitCompareArrows,
  Sun,
  Moon,
  Monitor,
  Wifi,
  WifiOff,
  ChevronUp,
} from "lucide-react"

export function StatusBar() {
  const doc = useAppStore((s) => s.document)
  const problems = useAppStore((s) => s.problems)
  const theme = useAppStore((s) => s.theme)
  const setTheme = useAppStore((s) => s.setTheme)
  const connected = useAppStore((s) => s.connected)
  const setBottomPanelOpen = useAppStore((s) => s.setBottomPanelOpen)
  const setBottomPanelTab = useAppStore((s) => s.setBottomPanelTab)
  const bottomPanelOpen = useAppStore((s) => s.bottomPanelOpen)
  const toggleBottomPanel = useAppStore((s) => s.toggleBottomPanel)

  const errorCount = problems.filter((p) => p.severity === "error").length
  const warningCount = problems.filter((p) => p.severity === "warning").length
  const conflictCount = problems.filter((p) => p.severity === "conflict").length

  const openProblems = () => {
    setBottomPanelOpen(true)
    setBottomPanelTab("problems")
  }

  const themeIcon =
    theme === "dark" ? (
      <Moon className="h-3 w-3" />
    ) : theme === "light" ? (
      <Sun className="h-3 w-3" />
    ) : (
      <Monitor className="h-3 w-3" />
    )

  return (
    <div className="flex h-6 shrink-0 items-center justify-between border-t bg-muted/30 px-2 text-[11px]">
      {/* Left side */}
      <div className="flex items-center gap-2">
        {doc && (
          <>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className="flex items-center gap-1 hover:bg-accent rounded px-1 py-0.5 transition-colors"
                  onClick={openProblems}
                >
                  <AlertCircle className="h-3 w-3 text-red-500" />
                  <span>{errorCount}</span>
                </button>
              </TooltipTrigger>
              <TooltipContent>Errors</TooltipContent>
            </Tooltip>

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className="flex items-center gap-1 hover:bg-accent rounded px-1 py-0.5 transition-colors"
                  onClick={openProblems}
                >
                  <AlertTriangle className="h-3 w-3 text-amber-500" />
                  <span>{warningCount}</span>
                </button>
              </TooltipTrigger>
              <TooltipContent>Warnings</TooltipContent>
            </Tooltip>

            {conflictCount > 0 && (
              <Tooltip>
                <TooltipTrigger asChild>
                  <button
                    className="flex items-center gap-1 hover:bg-accent rounded px-1 py-0.5 transition-colors"
                    onClick={openProblems}
                  >
                    <GitCompareArrows className="h-3 w-3 text-purple-500" />
                    <span>{conflictCount}</span>
                  </button>
                </TooltipTrigger>
                <TooltipContent>Conflicts</TooltipContent>
              </Tooltip>
            )}

            <Separator orientation="vertical" className="h-3" />

            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  className="flex items-center gap-1 hover:bg-accent rounded px-1 py-0.5 transition-colors"
                  onClick={toggleBottomPanel}
                >
                  <ChevronUp
                    className={`h-3 w-3 transition-transform ${bottomPanelOpen ? "rotate-180" : ""}`}
                  />
                  <span>Panel</span>
                </button>
              </TooltipTrigger>
              <TooltipContent>Toggle bottom panel</TooltipContent>
            </Tooltip>
          </>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button className="flex items-center gap-1 hover:bg-accent rounded px-1 py-0.5 transition-colors">
              {themeIcon}
              <span className="capitalize">{theme}</span>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={() => setTheme("light")}>
              <Sun className="h-3.5 w-3.5 mr-2" />
              Light
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme("dark")}>
              <Moon className="h-3.5 w-3.5 mr-2" />
              Dark
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => setTheme("system")}>
              <Monitor className="h-3.5 w-3.5 mr-2" />
              System
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Separator orientation="vertical" className="h-3" />

        <Tooltip>
          <TooltipTrigger asChild>
            <span className="flex items-center gap-1">
              {connected ? (
                <Wifi className="h-3 w-3 text-emerald-500" />
              ) : (
                <WifiOff className="h-3 w-3 text-red-500" />
              )}
              <span>{connected ? "Connected" : "Disconnected"}</span>
            </span>
          </TooltipTrigger>
          <TooltipContent>
            {connected ? "Connected to backend" : "Backend unreachable"}
          </TooltipContent>
        </Tooltip>

        {doc && (
          <>
            <Separator orientation="vertical" className="h-3" />
            <span className="text-muted-foreground">
              {doc.doc_type.toUpperCase()}
            </span>
          </>
        )}
      </div>
    </div>
  )
}
