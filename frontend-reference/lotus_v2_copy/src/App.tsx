import { useState } from "react"
import { TooltipProvider } from "@/components/ui/tooltip"
import { ThemeProvider } from "@/hooks/useTheme"
import { LayoutA } from "@/features/layout-a/LayoutA"
import { LayoutB } from "@/features/layout-b/LayoutB"
import { LayoutC } from "@/features/layout-c/LayoutC"
import type { LayoutVersion } from "@/types"
import { cn } from "@/lib/utils"

function VersionSwitcher({
  version,
  onChange,
}: {
  version: LayoutVersion
  onChange: (v: LayoutVersion) => void
}) {
  const versions: { id: LayoutVersion; label: string; description: string }[] = [
    { id: "A", label: "Version A", description: "Sidebar Dashboard" },
    { id: "B", label: "Version B", description: "Top Nav Centered" },
    { id: "C", label: "Version C", description: "Split-Pane Workspace" },
  ]

  return (
    <div className="fixed top-2 right-2 z-50 flex gap-1 rounded-lg border bg-background/95 backdrop-blur p-1 shadow-lg">
      {versions.map((v) => (
        <button
          key={v.id}
          onClick={() => onChange(v.id)}
          title={v.description}
          className={cn(
            "px-2.5 py-1 rounded-md text-[10px] font-medium transition-colors",
            version === v.id
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground hover:bg-accent hover:text-foreground"
          )}
        >
          {v.label}
        </button>
      ))}
    </div>
  )
}

function App() {
  const [version, setVersion] = useState<LayoutVersion>("A")

  return (
    <ThemeProvider>
      <TooltipProvider>
        <VersionSwitcher version={version} onChange={setVersion} />
        {version === "A" && <LayoutA />}
        {version === "B" && <LayoutB />}
        {version === "C" && <LayoutC />}
      </TooltipProvider>
    </ThemeProvider>
  )
}

export default App
