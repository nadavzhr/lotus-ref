import { useState, useEffect, useCallback } from "react"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Save, X, Search, ToggleLeft, Regex, Plus, Trash2 } from "lucide-react"
import { useDocumentStore } from "@/hooks/useDocumentStore"
import * as api from "@/services/api"
import type { EditSession, QueryNetsResponse } from "@/types"

interface EditPanelProps {
  selectedLine: number | null
}

/* ── Template + Net + Netlist Search (shared module) ──────────────────── */
function TemplateNetSearch({
  onNetSelect,
}: {
  onNetSelect?: (net: string) => void
}) {
  const [template, setTemplate] = useState("")
  const [netPattern, setNetPattern] = useState("")
  const [templateRegex, setTemplateRegex] = useState(false)
  const [netRegex, setNetRegex] = useState(false)
  const [results, setResults] = useState<QueryNetsResponse | null>(null)
  const [searching, setSearching] = useState(false)

  const handleSearch = useCallback(async () => {
    setSearching(true)
    try {
      const res = await api.queryNets({
        template: template || undefined,
        net_pattern: netPattern,
        template_regex: templateRegex,
        net_regex: netRegex,
      })
      setResults(res)
    } catch {
      setResults(null)
    } finally {
      setSearching(false)
    }
  }, [template, netPattern, templateRegex, netRegex])

  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-foreground flex items-center gap-1.5">
        <Search className="h-3.5 w-3.5" /> Netlist Search
      </h4>
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Template</label>
            <Button
              variant="ghost"
              size="sm"
              className={`h-5 px-1.5 text-[10px] gap-1 ${templateRegex ? "text-primary" : "text-muted-foreground"}`}
              onClick={() => setTemplateRegex((v) => !v)}
            >
              <Regex className="h-3 w-3" /> Regex
            </Button>
          </div>
          <Input
            placeholder="e.g. u_core/u_alu"
            className="h-8 text-xs font-mono"
            value={template}
            onChange={(e) => setTemplate(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Net</label>
            <Button
              variant="ghost"
              size="sm"
              className={`h-5 px-1.5 text-[10px] gap-1 ${netRegex ? "text-primary" : "text-muted-foreground"}`}
              onClick={() => setNetRegex((v) => !v)}
            >
              <Regex className="h-3 w-3" /> Regex
            </Button>
          </div>
          <Input
            placeholder="e.g. clk_core"
            className="h-8 text-xs font-mono"
            value={netPattern}
            onChange={(e) => setNetPattern(e.target.value)}
          />
        </div>
      </div>
      <Button size="sm" className="w-full h-7 text-xs" onClick={handleSearch} disabled={searching}>
        <Search className="h-3 w-3 mr-1.5" /> {searching ? "Searching…" : "Search Netlist"}
      </Button>

      {results && (
        <Tabs defaultValue="nets" className="mt-2">
          <TabsList className="h-7 w-full">
            <TabsTrigger value="nets" className="text-[10px] h-5">
              Nets{" "}
              <Badge variant="secondary" className="ml-1 text-[9px] px-1 py-0 h-3.5">
                {results.nets.length}
              </Badge>
            </TabsTrigger>
            <TabsTrigger value="templates" className="text-[10px] h-5">
              Templates{" "}
              <Badge variant="secondary" className="ml-1 text-[9px] px-1 py-0 h-3.5">
                {results.templates.length}
              </Badge>
            </TabsTrigger>
          </TabsList>
          <TabsContent value="nets" className="mt-1.5">
            <div className="border rounded-md bg-muted/20">
              <ScrollArea className="h-[120px]">
                <div className="p-1 space-y-0.5">
                  {results.nets.map((net) => (
                    <div
                      key={net}
                      className="px-2 py-1 text-xs font-mono rounded hover:bg-accent cursor-pointer transition-colors"
                      onClick={() => onNetSelect?.(net)}
                    >
                      {net}
                    </div>
                  ))}
                  {results.nets.length === 0 && (
                    <div className="px-2 py-3 text-xs text-muted-foreground text-center">
                      No matching nets
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>
          </TabsContent>
          <TabsContent value="templates" className="mt-1.5">
            <div className="border rounded-md bg-muted/20">
              <ScrollArea className="h-[120px]">
                <div className="p-1 space-y-0.5">
                  {results.templates.map((tmpl) => (
                    <div
                      key={tmpl}
                      className="px-2 py-1 text-xs font-mono rounded hover:bg-accent cursor-pointer transition-colors"
                    >
                      {tmpl}
                    </div>
                  ))}
                  {results.templates.length === 0 && (
                    <div className="px-2 py-3 text-xs text-muted-foreground text-center">
                      No matching templates
                    </div>
                  )}
                </div>
              </ScrollArea>
            </div>
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

/* ── AF Edit Form ─────────────────────────────────────────────────────── */
function AFEditForm({
  session,
  onFieldChange,
}: {
  session: EditSession
  onFieldChange: (fields: Record<string, unknown>) => void
}) {
  const data = session.data
  const af = (data.af_value as number) ?? 0
  const em = (data.is_em_enabled as boolean) ?? false
  const sh = (data.is_sh_enabled as boolean) ?? false

  return (
    <div className="p-4 space-y-4">
      <TemplateNetSearch />
      <Separator />

      {/* Flags + Activity Factor */}
      <div className="flex items-end gap-4">
        <div className="space-y-1.5">
          <label className="text-xs font-medium text-foreground">Activity Factor</label>
          <Input
            type="number"
            min={0}
            max={1}
            step={0.01}
            placeholder="0.0 – 1.0"
            className="h-8 text-xs font-mono w-28"
            value={af}
            onChange={(e) =>
              onFieldChange({ ...data, af_value: parseFloat(e.target.value) || 0 })
            }
          />
        </div>
        <div className="flex gap-2">
          <Button
            variant={em ? "default" : "outline"}
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={() => onFieldChange({ ...data, is_em_enabled: !em })}
          >
            <ToggleLeft className="h-3.5 w-3.5" /> EM
          </Button>
          <Button
            variant={sh ? "default" : "outline"}
            size="sm"
            className="h-8 text-xs gap-1.5"
            onClick={() => onFieldChange({ ...data, is_sh_enabled: !sh })}
          >
            <ToggleLeft className="h-3.5 w-3.5" /> SH
          </Button>
        </div>
      </div>
    </div>
  )
}

/* ── Mutex Edit Form ──────────────────────────────────────────────────── */
function MutexEditForm({
  session,
  docId,
  position,
  onRefresh,
}: {
  session: EditSession
  docId: string
  position: number
  onRefresh: () => void
}) {
  const data = session.data
  const mutexedNets = (data.mutexed_nets as string[]) ?? []
  const activeNets = (data.active_nets as string[]) ?? []
  const [newMutexedNet, setNewMutexedNet] = useState("")
  const [newActiveNet, setNewActiveNet] = useState("")

  const handleAddMutexed = useCallback(
    async (net: string) => {
      try {
        await api.mutexAddMutexed(docId, position, undefined, net)
        onRefresh()
      } catch {
        /* handled at store level */
      }
    },
    [docId, position, onRefresh],
  )

  const handleRemoveMutexed = useCallback(
    async (net: string) => {
      try {
        await api.mutexRemoveMutexed(docId, position, undefined, net)
        onRefresh()
      } catch {
        /* handled at store level */
      }
    },
    [docId, position, onRefresh],
  )

  const handleAddActive = useCallback(
    async (net: string) => {
      try {
        await api.mutexAddActive(docId, position, undefined, net)
        onRefresh()
      } catch {
        /* handled at store level */
      }
    },
    [docId, position, onRefresh],
  )

  const handleRemoveActive = useCallback(
    async (net: string) => {
      try {
        await api.mutexRemoveActive(docId, position, undefined, net)
        onRefresh()
      } catch {
        /* handled at store level */
      }
    },
    [docId, position, onRefresh],
  )

  return (
    <div className="p-4 space-y-4">
      <TemplateNetSearch onNetSelect={handleAddMutexed} />
      <Separator />

      {/* Mutexed Nets + Active Nets side by side */}
      <div className="grid grid-cols-2 gap-3">
        {/* Mutexed nets list */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Mutexed Nets</label>
            <span className="text-[10px] text-muted-foreground">{mutexedNets.length} nets</span>
          </div>
          <div className="border rounded-md bg-muted/20">
            <ScrollArea className="h-[100px]">
              <div className="p-1 space-y-0.5">
                {mutexedNets.map((net) => (
                  <div
                    key={net}
                    className="flex items-center justify-between px-2 py-1 text-xs font-mono rounded hover:bg-accent transition-colors group"
                  >
                    <span>{net}</span>
                    <button
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleRemoveMutexed(net)}
                    >
                      <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                ))}
                {mutexedNets.length === 0 && (
                  <div className="px-2 py-3 text-xs text-muted-foreground text-center">
                    No mutexed nets
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
          <div className="flex gap-1">
            <Input
              placeholder="net name"
              className="h-6 text-[10px] font-mono flex-1"
              value={newMutexedNet}
              onChange={(e) => setNewMutexedNet(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newMutexedNet.trim()) {
                  handleAddMutexed(newMutexedNet.trim())
                  setNewMutexedNet("")
                }
              }}
            />
            <Button
              variant="outline"
              size="sm"
              className="h-6 text-[10px] gap-1 px-2 shrink-0"
              disabled={!newMutexedNet.trim()}
              onClick={() => {
                if (newMutexedNet.trim()) {
                  handleAddMutexed(newMutexedNet.trim())
                  setNewMutexedNet("")
                }
              }}
            >
              <Plus className="h-3 w-3" />
            </Button>
          </div>
        </div>

        {/* Active nets list */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label className="text-xs font-medium text-foreground">Active Nets (on=)</label>
            <span className="text-[10px] text-muted-foreground">{activeNets.length} nets</span>
          </div>
          <div className="border rounded-md bg-muted/20">
            <ScrollArea className="h-[100px]">
              <div className="p-1 space-y-0.5">
                {activeNets.map((net) => (
                  <div
                    key={net}
                    className="flex items-center justify-between px-2 py-1 text-xs font-mono rounded hover:bg-accent transition-colors group"
                  >
                    <span>{net}</span>
                    <button
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                      onClick={() => handleRemoveActive(net)}
                    >
                      <Trash2 className="h-3 w-3 text-muted-foreground hover:text-destructive" />
                    </button>
                  </div>
                ))}
                {activeNets.length === 0 && (
                  <div className="px-2 py-3 text-xs text-muted-foreground text-center">
                    No active nets
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
          <div className="flex gap-1">
            <Input
              placeholder="net name"
              className="h-6 text-[10px] font-mono flex-1"
              value={newActiveNet}
              onChange={(e) => setNewActiveNet(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newActiveNet.trim()) {
                  handleAddActive(newActiveNet.trim())
                  setNewActiveNet("")
                }
              }}
            />
            <Button
              variant="outline"
              size="sm"
              className="h-6 text-[10px] gap-1 px-2 shrink-0"
              disabled={!newActiveNet.trim()}
              onClick={() => {
                if (newActiveNet.trim()) {
                  handleAddActive(newActiveNet.trim())
                  setNewActiveNet("")
                }
              }}
            >
              <Plus className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ── Right Panel ──────────────────────────────────────────────────────── */
export function EditPanel({ selectedLine }: EditPanelProps) {
  const { activeDocId, activeDocType, lines, refreshLines, addLog } = useDocumentStore()
  const [session, setSession] = useState<EditSession | null>(null)
  const [sessionLoading, setSessionLoading] = useState(false)
  const [dirty, setDirty] = useState(false)

  const activeLine = lines.find((l) => l.position === selectedLine) ?? null

  // Hydrate session when a line is selected
  useEffect(() => {
    if (activeDocId === null || selectedLine === null) {
      setSession(null)
      return
    }
    let cancelled = false
    setSessionLoading(true)
    api
      .hydrateSession(activeDocId, selectedLine)
      .then((s) => {
        if (!cancelled) {
          setSession(s)
          setDirty(false)
        }
      })
      .catch(() => {
        if (!cancelled) setSession(null)
      })
      .finally(() => {
        if (!cancelled) setSessionLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [activeDocId, selectedLine])

  const handleFieldChange = useCallback(
    async (fields: Record<string, unknown>) => {
      if (!activeDocId || selectedLine === null) return
      try {
        const updated = await api.hydrateSession(activeDocId, selectedLine, fields)
        setSession(updated)
        setDirty(true)
      } catch {
        addLog("ERROR", "Failed to update edit session")
      }
    },
    [activeDocId, selectedLine, addLog],
  )

  const handleCommit = useCallback(async () => {
    if (!activeDocId || selectedLine === null) return
    try {
      await api.commitEdit(activeDocId, selectedLine)
      addLog("INFO", `Committed changes to line ${selectedLine + 1}`)
      setDirty(false)
      await refreshLines()
      // Refresh session
      const s = await api.hydrateSession(activeDocId, selectedLine)
      setSession(s)
    } catch (e) {
      addLog("ERROR", `Commit failed: ${e instanceof Error ? e.message : String(e)}`)
    }
  }, [activeDocId, selectedLine, addLog, refreshLines])

  const handleCancel = useCallback(async () => {
    if (!activeDocId || selectedLine === null) return
    // Re-hydrate to discard changes
    try {
      const s = await api.hydrateSession(activeDocId, selectedLine)
      setSession(s)
      setDirty(false)
    } catch {
      addLog("ERROR", "Failed to cancel edit")
    }
  }, [activeDocId, selectedLine, addLog])

  const handleRefreshSession = useCallback(async () => {
    if (!activeDocId || selectedLine === null) return
    try {
      const s = await api.hydrateSession(activeDocId, selectedLine)
      setSession(s)
    } catch {
      /* ignore */
    }
  }, [activeDocId, selectedLine])

  if (selectedLine === null || !activeDocId) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <div className="text-center">
          <p className="text-sm">Select a line from the left panel to edit</p>
          <p className="text-xs mt-1 text-muted-foreground/70">
            or press Insert to create a new line
          </p>
        </div>
      </div>
    )
  }

  if (sessionLoading && !session) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <p className="text-xs">Loading edit session…</p>
      </div>
    )
  }

  if (!session) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <p className="text-xs">Unable to load edit session for this line.</p>
      </div>
    )
  }

  const statusColor: Record<string, string> = {
    ok: "bg-emerald-500/15 text-emerald-700 border-emerald-500/20 hover:bg-emerald-500/20",
    warning: "bg-amber-500/15 text-amber-700 border-amber-500/20 hover:bg-amber-500/20",
    error: "bg-red-500/15 text-red-700 border-red-500/20 hover:bg-red-500/20",
    comment: "bg-muted text-muted-foreground border-muted",
    conflict: "bg-purple-500/15 text-purple-700 border-purple-500/20 hover:bg-purple-500/20",
  }

  const lineStatus = activeLine?.status ?? "ok"

  return (
    <div className="flex flex-col h-full">
      {/* Header: line info + Cancel / Save */}
      <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/20 shrink-0">
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="text-[10px] font-mono">
            Line {selectedLine + 1}
          </Badge>
          <Badge
            className={`text-[10px] ${statusColor[lineStatus] ?? ""}`}
            variant="outline"
          >
            {lineStatus}
          </Badge>
          {dirty && (
            <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-600">
              unsaved
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-1">
          <Button size="sm" variant="ghost" className="h-7 px-2 text-xs" onClick={handleCancel}>
            <X className="h-3.5 w-3.5 mr-1" /> Cancel
          </Button>
          <Button size="sm" className="h-7 px-2.5 text-xs" onClick={handleCommit} disabled={!dirty}>
            <Save className="h-3.5 w-3.5 mr-1" /> Save
          </Button>
        </div>
      </div>

      {/* Edit / Comment tabs */}
      <Tabs defaultValue="edit" className="flex-1 flex flex-col min-h-0">
        <TabsList className="w-full justify-start rounded-none border-b bg-transparent px-4 h-9 shrink-0">
          <TabsTrigger
            value="edit"
            className="text-xs data-[state=active]:bg-background rounded-b-none data-[state=active]:border-b-2 data-[state=active]:border-primary"
          >
            Structured Edit
          </TabsTrigger>
          <TabsTrigger
            value="comment"
            className="text-xs data-[state=active]:bg-background rounded-b-none data-[state=active]:border-b-2 data-[state=active]:border-primary"
          >
            Comment
          </TabsTrigger>
        </TabsList>

        <TabsContent value="edit" className="flex-1 m-0 overflow-hidden min-h-0">
          <ScrollArea className="h-full">
            {activeDocType === "af" ? (
              <AFEditForm session={session} onFieldChange={handleFieldChange} />
            ) : (
              <MutexEditForm
                session={session}
                docId={activeDocId}
                position={selectedLine}
                onRefresh={handleRefreshSession}
              />
            )}
          </ScrollArea>
        </TabsContent>

        <TabsContent value="comment" className="flex-1 m-0 p-4 min-h-0">
          <div className="space-y-1.5 h-full flex flex-col">
            <label className="text-xs font-medium text-foreground">Raw text</label>
            <textarea
              className="flex-1 w-full rounded-md border bg-transparent px-3 py-2 text-xs font-mono ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring resize-none"
              placeholder="# Enter raw text…"
              value={activeLine?.raw_text ?? ""}
              readOnly
            />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
