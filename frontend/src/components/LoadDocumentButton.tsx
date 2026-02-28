import { useState, useCallback } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useDocumentStore } from "@/stores/document-store";
import { useTabsStore } from "@/stores/tabs-store";
import { FolderOpen } from "lucide-react";

/**
 * LoadDocumentDialog — a simple inline form in the toolbar area to
 * load a document by file path and type.
 *
 * In the Electron future this will invoke a native file picker.
 * For now it's a compact input form.
 */
export function LoadDocumentButton() {
  const [open, setOpen] = useState(false);
  const [filePath, setFilePath] = useState("");
  const [docType, setDocType] = useState<"af" | "mutex">("af");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const loadDocument = useDocumentStore((s) => s.loadDocument);
  const openTab = useTabsStore((s) => s.openTab);

  const handleLoadPath = useCallback(
    async (path: string, type: "af" | "mutex") => {
      const trimmed = path.trim();
      if (!trimmed) {
        setError("Enter a file path");
        return;
      }

      // Derive doc_id from filename (same logic as original)
      const fileName = trimmed.split(/[/\\]/).pop() ?? trimmed;
      const docId = fileName.replace(/\./g, "_");

      setLoading(true);
      setError(null);

      try {
        await loadDocument(docId, trimmed, type);

        // Open a tab
        openTab({
          id: docId,
          label: fileName,
          docType: type,
          filePath: trimmed,
        });

        // Reset form and close
        setFilePath("");
        setOpen(false);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setLoading(false);
      }
    },
    [loadDocument, openTab],
  );

  const handleLoad = useCallback(() => {
    handleLoadPath(filePath, docType);
  }, [filePath, docType, handleLoadPath]);

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="gap-1.5 text-xs">
          <FolderOpen className="h-3.5 w-3.5" />
          Open
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-96 p-3">
        <div className="space-y-3">
          <div className="text-xs font-medium text-foreground">
            Load Document
          </div>

          {/* File path input */}
          <input
            type="text"
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") handleLoad();
            }}
            placeholder="/path/to/file.dcfg"
            className="w-full rounded-md border bg-background px-3 py-1.5 font-mono text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
            autoFocus
          />

          {/* Doc type selector */}
          <div className="flex items-center gap-2">
            <span className="text-2xs text-muted-foreground">Type:</span>
            {(["af", "mutex"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setDocType(t)}
                className={`rounded px-2 py-0.5 text-xs font-medium transition-colors ${
                  docType === t
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted text-muted-foreground hover:bg-accent"
                }`}
              >
                {t.toUpperCase()}
              </button>
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="rounded bg-destructive/10 px-2 py-1 text-xs text-destructive">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setOpen(false)}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleLoad}
              disabled={loading}
              className="text-xs"
            >
              {loading ? "Loading..." : "Load"}
            </Button>
          </div>
        </div>

        {/* Quick-load helpers — sample files from workspace */}
        <div className="mt-3 border-t pt-2">
          <div className="text-2xs text-muted-foreground mb-1">Quick load:</div>
          {[
            { path: "C:/Projects/lotus-ref/data/cfg/mycell.af.dcfg", type: "af" as const },
            { path: "C:/Projects/lotus-ref/data/cfg/mycell.mutex.dcfg", type: "mutex" as const },
          ].map(({ path, type }) => (
            <DropdownMenuItem
              key={path}
              className="text-xs font-mono"
              onSelect={(e) => {
                e.preventDefault();
                handleLoadPath(path, type);
              }}
            >
              {path.split("/").pop()} ({type.toUpperCase()})
            </DropdownMenuItem>
          ))}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
