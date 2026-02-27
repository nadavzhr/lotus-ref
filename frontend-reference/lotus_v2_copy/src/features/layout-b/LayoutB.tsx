import { useState } from "react"
import { cn } from "@/lib/utils"
import { useTheme } from "@/hooks/useTheme"
import { LineList } from "@/components/shared/LineList"
import { EditForm } from "@/components/shared/EditForm"
import { ChatWidget } from "@/components/shared/ChatWidget"
import { ProblemsPanel, ProblemsSummaryBar } from "@/components/shared/ProblemsPanel"
import { StatusBar } from "@/components/shared/StatusBar"
import type { DocumentTab } from "@/types"
import {
  Flower2,
  Sun,
  Moon,
  MessageSquare,
  FileText,
  AlertTriangle,
  ChevronRight,
  Home,
  X,
} from "lucide-react"
import { Button } from "@/components/ui/button"

type ContentView = "editor" | "problems" | "chat"

export function LayoutB() {
  const { theme, toggleTheme } = useTheme()
  const [selectedLine, setSelectedLine] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<DocumentTab>("af")
  const [contentView, setContentView] = useState<ContentView>("editor")
  const [showChat, setShowChat] = useState(false)

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background text-foreground">
      {/* Top Navigation Bar */}
      <nav className="h-12 border-b bg-background shrink-0 flex items-center px-4 gap-4">
        <div className="flex items-center gap-2">
          <Flower2 className="h-5 w-5 text-primary" />
          <span className="font-semibold text-sm tracking-tight">Lotus v2</span>
        </div>

        <div className="h-6 w-px bg-border" />

        <div className="flex items-center gap-1">
          <NavButton
            active={contentView === "editor"}
            onClick={() => setContentView("editor")}
            icon={<FileText className="h-4 w-4" />}
            label="Editor"
          />
          <NavButton
            active={contentView === "problems"}
            onClick={() => setContentView("problems")}
            icon={<AlertTriangle className="h-4 w-4" />}
            label="Problems"
          />
        </div>

        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-muted-foreground font-mono">ward: /path/to/ward</span>
          <span className="text-xs text-muted-foreground">|</span>
          <span className="text-xs text-muted-foreground font-mono">cell: my_block</span>

          <div className="h-6 w-px bg-border" />

          <button
            onClick={() => setShowChat((v) => !v)}
            className={cn(
              "p-1.5 rounded-md transition-colors",
              showChat
                ? "bg-primary/10 text-primary"
                : "text-muted-foreground hover:bg-accent hover:text-foreground"
            )}
            title={showChat ? "Hide AI Chat" : "Show AI Chat"}
          >
            <MessageSquare className="h-4 w-4" />
          </button>
          <button
            onClick={toggleTheme}
            className="p-1.5 rounded-md hover:bg-accent transition-colors text-muted-foreground hover:text-foreground"
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>
        </div>
      </nav>

      {/* Breadcrumb + Document Tabs */}
      <div className="border-b bg-muted/10 px-6 py-1.5 shrink-0 flex items-center gap-2">
        <Home className="h-3 w-3 text-muted-foreground" />
        <ChevronRight className="h-3 w-3 text-muted-foreground" />
        <span className="text-xs text-muted-foreground">my_block</span>
        <ChevronRight className="h-3 w-3 text-muted-foreground" />
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab("af")}
            className={cn(
              "text-xs px-2 py-0.5 rounded transition-colors",
              activeTab === "af"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent"
            )}
          >
            Activity Factor
          </button>
          <button
            onClick={() => setActiveTab("mutex")}
            className={cn(
              "text-xs px-2 py-0.5 rounded transition-colors",
              activeTab === "mutex"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent"
            )}
          >
            Mutex
          </button>
        </div>
        <span className="ml-auto text-[10px] text-muted-foreground font-mono">
          {activeTab === "af"
            ? "/path/to/ward/drive/cfg/my_block.af.dcfg"
            : "/path/to/ward/drive/cfg/my_block.mutex.dcfg"}
        </span>
      </div>

      {/* Main Content */}
      <div className="flex-1 min-h-0 flex flex-row">
        <div className="flex-1 min-w-0">
          {contentView === "editor" ? (
            <div className="h-full max-w-6xl mx-auto flex flex-col px-6 py-4 gap-4">
              {/* Cards Layout */}
              <div className="flex-1 min-h-0 grid grid-cols-2 gap-4">
                {/* Line List Card */}
                <div className="border rounded-lg bg-card shadow-sm overflow-hidden flex flex-col min-h-0">
                  <div className="px-4 py-2.5 border-b bg-muted/20">
                    <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Configuration Lines
                    </h2>
                  </div>
                  <div className="flex-1 min-h-0">
                    <LineList selectedLine={selectedLine} onSelectLine={setSelectedLine} />
                  </div>
                </div>

                {/* Edit Form Card */}
                <div className="border rounded-lg bg-card shadow-sm overflow-hidden flex flex-col min-h-0">
                  <div className="px-4 py-2.5 border-b bg-muted/20">
                    <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Editor
                    </h2>
                  </div>
                  <div className="flex-1 min-h-0">
                    <EditForm selectedLine={selectedLine} activeTab={activeTab} />
                  </div>
                </div>
              </div>

              {/* Bottom Problems Summary */}
              <div className="border rounded-lg bg-card shadow-sm overflow-hidden h-48 shrink-0">
                <div className="px-4 py-2 border-b bg-muted/20 flex items-center justify-between">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Problems & Logs
                  </h2>
                  <ProblemsSummaryBar />
                </div>
                <div className="flex-1 min-h-0 h-[calc(100%-36px)]">
                  <ProblemsPanel compact />
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full max-w-4xl mx-auto px-6 py-4">
              <div className="border rounded-lg bg-card shadow-sm overflow-hidden h-full flex flex-col">
                <div className="px-4 py-2.5 border-b bg-muted/20">
                  <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Problems & Logs
                  </h2>
                </div>
                <div className="flex-1 min-h-0">
                  <ProblemsPanel />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Chat Side Panel */}
        {showChat && (
          <div className="w-80 border-l bg-card shrink-0 flex flex-col h-full">
            <div className="flex items-center justify-between px-3 py-2 border-b">
              <span className="text-xs font-semibold">AI Assistant</span>
              <Button variant="ghost" size="sm" className="h-6 w-6 p-0" onClick={() => setShowChat(false)}>
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>
            <div className="flex-1 min-h-0">
              <ChatWidget showHeader={false} />
            </div>
          </div>
        )}
      </div>

      <StatusBar />
    </div>
  )
}

function NavButton({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
        active
          ? "bg-accent text-foreground"
          : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
      )}
    >
      {icon}
      {label}
    </button>
  )
}
