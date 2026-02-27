import { useState, useEffect, useCallback } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { useAppStore } from "@/store/app-store"
import type { DocumentLine } from "@/types/api"
import { Loader2, Save, X } from "lucide-react"

interface EditDialogProps {
  lines: DocumentLine[]
}

export function EditDialog({ lines }: EditDialogProps) {
  const editingLine = useAppStore((s) => s.editingLine)
  const setEditingLine = useAppStore((s) => s.setEditingLine)
  const doc = useAppStore((s) => s.document)

  const [sessionData, setSessionData] = useState<Record<string, unknown> | null>(null)
  const [modified, setModified] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const line = editingLine !== null ? lines.find((l) => l.position === editingLine) : null

  // Hydrate session when dialog opens
  useEffect(() => {
    if (editingLine === null || !doc) {
      setSessionData(null)
      setModified(false)
      setError(null)
      return
    }

    setLoading(true)
    setError(null)

    fetch(`/api/documents/${doc.doc_id}/lines/${editingLine}/session`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fields: null }),
    })
      .then(async (res) => {
        if (!res.ok) {
          const body = await res.json().catch(() => ({}))
          throw new Error((body as Record<string, string>).detail ?? "Failed to load session")
        }
        return res.json()
      })
      .then((data: { data: Record<string, unknown> }) => {
        setSessionData(data.data)
        setModified(false)
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false))
  }, [editingLine, doc])

  const handleFieldChange = useCallback(
    (key: string, value: string) => {
      setSessionData((prev) => (prev ? { ...prev, [key]: value } : prev))
      setModified(true)
    },
    []
  )

  const handleCommit = useCallback(async () => {
    if (!doc || editingLine === null) return
    setLoading(true)
    setError(null)

    try {
      // First, update session with current fields
      if (sessionData) {
        const hydRes = await fetch(
          `/api/documents/${doc.doc_id}/lines/${editingLine}/session`,
          {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ fields: sessionData }),
          }
        )
        if (!hydRes.ok) {
          const body = await hydRes.json().catch(() => ({}))
          throw new Error((body as Record<string, string>).detail ?? "Update failed")
        }
      }

      // Then commit
      const res = await fetch(
        `/api/documents/${doc.doc_id}/lines/${editingLine}/commit`,
        { method: "POST" }
      )
      if (!res.ok) {
        const body = await res.json().catch(() => ({}))
        throw new Error((body as Record<string, string>).detail ?? "Commit failed")
      }

      setEditingLine(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error")
    } finally {
      setLoading(false)
    }
  }, [doc, editingLine, sessionData, setEditingLine])

  const handleCancel = useCallback(() => {
    if (modified) {
      if (!window.confirm("You have unsaved changes. Discard?")) return
    }
    setEditingLine(null)
  }, [modified, setEditingLine])

  const open = editingLine !== null

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleCancel()}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Edit Line {editingLine !== null ? editingLine + 1 : ""}
            {modified && (
              <Badge variant="secondary" className="text-[10px]">
                Modified
              </Badge>
            )}
          </DialogTitle>
          <DialogDescription>
            {line
              ? `Editing ${doc?.doc_type?.toUpperCase() ?? ""} line — ${line.raw_text.slice(0, 60)}${line.raw_text.length > 60 ? "…" : ""}`
              : "Loading…"}
          </DialogDescription>
        </DialogHeader>

        <Separator />

        {error && (
          <div className="rounded-md bg-destructive/10 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading && !sessionData ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            <span className="ml-2 text-sm text-muted-foreground">
              Loading session…
            </span>
          </div>
        ) : sessionData ? (
          <ScrollArea className="max-h-[400px]">
            <div className="space-y-3 pr-4">
              {Object.entries(sessionData).map(([key, value]) => (
                <div key={key} className="space-y-1">
                  <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                    {key.replace(/_/g, " ")}
                  </label>
                  {typeof value === "string" || typeof value === "number" ? (
                    <input
                      className="flex h-8 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring font-mono"
                      value={String(value)}
                      onChange={(e) => handleFieldChange(key, e.target.value)}
                    />
                  ) : (
                    <pre className="rounded-md bg-muted p-2 text-xs font-mono overflow-auto">
                      {JSON.stringify(value, null, 2)}
                    </pre>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        ) : (
          <div className="py-4 text-center text-sm text-muted-foreground">
            No session data available. The line may not have editable data.
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={handleCancel} disabled={loading}>
            <X className="h-3.5 w-3.5 mr-1" />
            Cancel
          </Button>
          <Button onClick={handleCommit} disabled={loading || !sessionData}>
            {loading ? (
              <Loader2 className="h-3.5 w-3.5 mr-1 animate-spin" />
            ) : (
              <Save className="h-3.5 w-3.5 mr-1" />
            )}
            Commit
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
