import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Save, X, Search, ToggleLeft, Regex, Plus, Trash2 } from "lucide-react"

interface EditPanelProps {
  selectedLine: number | null
  activeTab: string
}

/* ── Template + Net + Netlist Search (shared module) ──────────────────── */
function TemplateNetSearch() {
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
        <Search className="h-3.5 w-3.5" /> Netlist Search
      </h4>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Template</label>
            <Button variant="ghost" size="sm" className="h-5 px-1.5 text-[10px] text-muted-foreground gap-1">
              <Regex className="h-3 w-3" /> Regex
            </Button>
          </div>
          <Input placeholder="e.g. u_core/u_alu" className="h-8 text-xs font-mono" defaultValue="" />
        </div>
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Net</label>
            <Button variant="ghost" size="sm" className="h-5 px-1.5 text-[10px] text-muted-foreground gap-1">
              <Regex className="h-3 w-3" /> Regex
            </Button>
          </div>
          <Input placeholder="e.g. clk_core" className="h-8 text-xs font-mono" defaultValue="clk_core" />
        </div>
      </div>
      <Button size="sm" className="w-full h-7 text-xs">
        <Search className="h-3 w-3 mr-1.5" /> Search Netlist
      </Button>

        <Tabs defaultValue="nets" className="mt-2">
          <TabsList className="h-7 w-full">
            <TabsTrigger value="nets" className="text-[10px] h-5">
              Nets <Badge variant="secondary" className="ml-1 text-[9px] px-1 py-0 h-3.5">24</Badge>
            </TabsTrigger>
            <TabsTrigger value="templates" className="text-[10px] h-5">
              Templates <Badge variant="secondary" className="ml-1 text-[9px] px-1 py-0 h-3.5">3</Badge>
            </TabsTrigger>
          </TabsList>
          <TabsContent value="nets" className="mt-1.5">
            <div className="border rounded-md bg-muted/20">
              <ScrollArea className="h-[120px]">
                <div className="p-1 space-y-0.5">
                  {["u_core:clk_core", "u_core:clk_div2", "u_core:clk_gated", "u_mem:clk_mem", "u_mem:clk_mem_div2", "u_io:clk_io"].map((net) => (
                    <div key={net} className="px-2 py-1 text-xs font-mono rounded hover:bg-accent cursor-pointer transition-colors">
                      {net}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </TabsContent>
          <TabsContent value="templates" className="mt-1.5">
            <div className="border rounded-md bg-muted/20">
              <ScrollArea className="h-[120px]">
                <div className="p-1 space-y-0.5">
                  {["u_core", "u_core/u_alu", "u_core/u_regfile", "u_mem", "u_io"].map((tmpl) => (
                    <div key={tmpl} className="px-2 py-1 text-xs font-mono rounded hover:bg-accent cursor-pointer transition-colors">
                      {tmpl}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>
          </TabsContent>
        </Tabs>
    </div>
  )
}

/* ── AF Edit Form ─────────────────────────────────────────────────────── */
function AFEditForm() {
  return (
    <div className="p-4 space-y-4">
      {/* Template + Net + Netlist Search (shared module) */}
      <TemplateNetSearch />

      <Separator />

      {/* Flags + Activity Factor in a single row at the bottom */}
      <div className="flex items-end gap-4">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground">Activity Factor</label>
          <Input type="number" min={0} max={1} step={0.01} placeholder="0.0 – 1.0" className="h-8 text-xs font-mono w-28" defaultValue="0.45" />
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="h-8 text-xs gap-1.5">
            <ToggleLeft className="h-3.5 w-3.5" /> EM
          </Button>
          <Button variant="outline" size="sm" className="h-8 text-xs gap-1.5">
            <ToggleLeft className="h-3.5 w-3.5" /> SH
          </Button>
        </div>
      </div>
    </div>
  )
}

/* ── Mutex Edit Form ──────────────────────────────────────────────────── */
function MutexEditForm() {
  return (
    <div className="p-4 space-y-4">
      {/* Template + Net + Netlist Search (shared module) */}
      <TemplateNetSearch />

      <Separator />

      {/* Mutexed Nets + Active Nets side by side */}
      <div className="grid grid-cols-2 gap-3">
        {/* Mutexed nets list */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Mutexed Nets</label>
            <span className="text-[10px] text-muted-foreground">3 nets</span>
          </div>
          <div className="border rounded-md bg-muted/20">
            <ScrollArea className="h-[100px]">
              <div className="p-1 space-y-0.5">
                {["clk_phase_a", "clk_phase_b", "clk_phase_c"].map((net) => (
                  <div key={net} className="flex items-center justify-between px-2 py-1 text-xs font-mono rounded hover:bg-accent transition-colors group">
                    <span>{net}</span>
                    <button className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
          <Button variant="outline" size="sm" className="h-6 text-[10px] gap-1 w-full">
            <Plus className="h-3 w-3" /> Add Net
          </Button>
        </div>

        {/* Active nets list */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Active Nets (on=)</label>
            <span className="text-[10px] text-muted-foreground">1 net</span>
          </div>
          <div className="border rounded-md bg-muted/20">
            <ScrollArea className="h-[100px]">
              <div className="p-1 space-y-0.5">
                {["clk_phase_a"].map((net) => (
                  <div key={net} className="flex items-center justify-between px-2 py-1 text-xs font-mono rounded hover:bg-accent transition-colors group">
                    <span>{net}</span>
                    <button className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </div>
          <Button variant="outline" size="sm" className="h-6 text-[10px] gap-1 w-full">
            <Plus className="h-3 w-3" /> Add Active Net
          </Button>
        </div>
      </div>
    </div>
  )
}

/* ── Right Panel ──────────────────────────────────────────────────────── */
export function EditPanel({ selectedLine, activeTab }: EditPanelProps) {
  if (!selectedLine) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <p className="text-sm">Select a line from the left panel to edit</p>
          <p className="text-xs mt-1 text-muted-foreground/70">or press Insert to create a new line</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header: line info + Cancel / Save */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/20 shrink-0">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[10px] font-mono">Line {selectedLine}</Badge>
          <Badge className="text-[10px] bg-emerald-500/15 text-emerald-700 border-emerald-500/20 hover:bg-emerald-500/20" variant="outline">
            Valid
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <Button size="sm" variant="ghost" className="h-7 px-2 text-xs">
            <X className="h-3.5 w-3.5 mr-1" /> Cancel
          </Button>
          <Button size="sm" className="h-7 px-2.5 text-xs">
            <Save className="h-3.5 w-3.5 mr-1" /> Save
          </Button>
        </div>
      </div>

      {/* Edit / Comment tabs */}
      <Tabs defaultValue="edit" className="flex-1 flex flex-col min-h-0">
        <TabsList className="w-full justify-start rounded-none border-b bg-transparent px-4 h-9 shrink-0">
          <TabsTrigger value="edit" className="text-xs data-[state=active]:bg-background rounded-b-none data-[state=active]:border-b-2 data-[state=active]:border-primary">
            Structured Edit
          </TabsTrigger>
          <TabsTrigger value="comment" className="text-xs data-[state=active]:bg-background rounded-b-none data-[state=active]:border-b-2 data-[state=active]:border-primary">
            Comment
          </TabsTrigger>
        </TabsList>

        <TabsContent value="edit" className="flex-1 m-0 overflow-hidden min-h-0">
          <ScrollArea className="h-full">
            {activeTab === "af" ? <AFEditForm /> : <MutexEditForm />}
          </ScrollArea>
        </TabsContent>

        <TabsContent value="comment" className="flex-1 m-0 p-4 min-h-0">
          <div className="space-y-1.5 h-full flex flex-col">
            <label className="text-xs font-medium text-foreground">Raw comment text</label>
            <textarea
              className="flex-1 w-full rounded-md border bg-transparent px-3 py-2 text-xs font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
              placeholder="# Enter raw comment text…"
              defaultValue="# Top-level clock nets"
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
