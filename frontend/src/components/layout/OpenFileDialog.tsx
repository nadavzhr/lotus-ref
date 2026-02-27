import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { useDocumentStore } from "@/hooks/useDocumentStore"

interface OpenFileDialogProps {
  open: boolean
  onClose: () => void
}

export function OpenFileDialog({ open, onClose }: OpenFileDialogProps) {
  const [filePath, setFilePath] = useState("")
  const [docType, setDocType] = useState<"af" | "mutex">("af")
  const [docId, setDocId] = useState("")
  const { loadDocument, refreshLines } = useDocumentStore()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  if (!open) return null

  const handleLoad = async () => {
    if (!filePath.trim() || !docId.trim()) return
    setLoading(true)
    setError(null)
    try {
      await loadDocument(docId.trim(), filePath.trim(), docType)
      await refreshLines()
      onClose()
      setFilePath("")
      setDocId("")
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background border rounded-lg shadow-lg p-6 w-[420px] space-y-4">
        <h2 className="text-sm font-semibold">Open Document</h2>

        <div className="space-y-1.5">
          <label className="text-xs font-medium">Document ID</label>
          <Input
            placeholder="e.g. my_block_af"
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
            className="h-8 text-xs"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium">File Path</label>
          <Input
            placeholder="e.g. data/cfg/my_block.af.dcfg"
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
            className="h-8 text-xs font-mono"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium">Document Type</label>
          <div className="flex gap-2">
            <Button
              variant={docType === "af" ? "default" : "outline"}
              size="sm"
              className="h-8 text-xs flex-1"
              onClick={() => setDocType("af")}
            >
              Activity Factor
            </Button>
            <Button
              variant={docType === "mutex" ? "default" : "outline"}
              size="sm"
              className="h-8 text-xs flex-1"
              onClick={() => setDocType("mutex")}
            >
              Mutex
            </Button>
          </div>
        </div>

        {error && <p className="text-xs text-destructive">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button variant="ghost" size="sm" className="h-8 text-xs" onClick={onClose}>
            Cancel
          </Button>
          <Button
            size="sm"
            className="h-8 text-xs"
            onClick={handleLoad}
            disabled={loading || !filePath.trim() || !docId.trim()}
          >
            {loading ? "Loading…" : "Open"}
          </Button>
        </div>
      </div>
    </div>
  )
}
