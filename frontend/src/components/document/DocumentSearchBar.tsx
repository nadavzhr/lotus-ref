/**
 * DocumentSearchBar — search/filter bar above the document viewer.
 *
 * Features:
 *  - Text search with regex toggle (.*) overlay icon on input
 *  - Status dropdown filter (ok, warning, error, comment, empty)
 *  - Calls the backend searchLines API + updates displayed lines
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { StatusBadge } from "./StatusBadge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Filter, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";
import * as api from "@/api/documents";
import type { DocumentLine } from "@/api/documents";

const STATUS_OPTIONS = [
  { value: "ok", label: "OK" },
  { value: "warning", label: "Warning" },
  { value: "error", label: "Error" },
  { value: "comment", label: "Comment" },
];

interface DocumentSearchBarProps {
  docId: string;
  /** Called with filtered lines — parent replaces displayed lines. null = show all. */
  onResults: (lines: DocumentLine[] | null) => void;
}

export function DocumentSearchBar({ docId, onResults }: DocumentSearchBarProps) {
  const [query, setQuery] = useState("");
  const [isRegex, setIsRegex] = useState(false);
  const [statusFilter, setStatusFilter] = useState<string | null>(null);
  const [searching, setSearching] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const hasFilter = query.length > 0 || statusFilter !== null;

  /* ---- Run search with debounce ---- */
  const doSearch = useCallback(async () => {
    if (!query && !statusFilter) {
      onResults(null);
      return;
    }
    setSearching(true);
    try {
      const results = await api.searchLines(
        docId,
        query,
        isRegex,
        statusFilter ?? undefined,
      );
      onResults(results);
    } catch {
      onResults(null);
    } finally {
      setSearching(false);
    }
  }, [docId, query, isRegex, statusFilter, onResults]);

  useEffect(() => {
    const timer = setTimeout(doSearch, 300);
    return () => clearTimeout(timer);
  }, [doSearch]);

  const handleClear = useCallback(() => {
    setQuery("");
    setStatusFilter(null);
    setIsRegex(false);
    onResults(null);
    inputRef.current?.focus();
  }, [onResults]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.stopPropagation(); // Don't trigger document-level shortcuts
      if (e.key === "Escape") {
        if (hasFilter) handleClear();
      }
    },
    [hasFilter, handleClear],
  );

  return (
    <div className="flex shrink-0 items-center gap-2 border-b bg-muted/20 px-3 py-1.5">
      {/* Search input with regex overlay toggle */}
      <div className="relative flex-1">
        <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground/50" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search lines..."
          className="h-7 w-full rounded-md border bg-background pl-7 pr-16 text-xs outline-none placeholder:text-muted-foreground/40 focus:ring-1 focus:ring-ring"
        />
        {/* Regex toggle — overlaid inside the input, right side */}
        <button
          type="button"
          title="Toggle regex mode"
          onClick={() => setIsRegex((v) => !v)}
          className={cn(
            "absolute right-1 top-1/2 -translate-y-1/2 rounded px-1.5 py-0.5 font-mono text-2xs font-bold transition-colors",
            isRegex
              ? "bg-primary text-primary-foreground"
              : "text-muted-foreground/50 hover:bg-accent hover:text-foreground",
          )}
        >
          .*
        </button>
      </div>

      {/* Status filter dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant={statusFilter ? "secondary" : "ghost"}
            size="sm"
            className="h-7 gap-1.5 text-xs"
          >
            <Filter className="h-3 w-3" />
            {statusFilter ? (
              <div className="flex items-center gap-1.5">
                <StatusBadge status={statusFilter} />
                <span className="text-xs capitalize">{statusFilter}</span>
              </div>
            ) : (
              <span className="text-muted-foreground">Status</span>
            )}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={() => setStatusFilter(null)}>
            <span className="text-xs text-muted-foreground">All statuses</span>
          </DropdownMenuItem>
          {STATUS_OPTIONS.map(({ value, label }) => (
            <DropdownMenuItem key={value} onClick={() => setStatusFilter(value)}>
              <div className="flex items-center gap-2">
                <StatusBadge status={value} />
                <span className="text-xs">{label}</span>
              </div>
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Clear button */}
      {hasFilter && (
        <Button
          variant="ghost"
          size="icon-sm"
          className="h-6 w-6"
          onClick={handleClear}
          title="Clear search"
        >
          <X className="h-3 w-3" />
        </Button>
      )}

      {/* Searching indicator */}
      {searching && (
        <span className="text-2xs text-muted-foreground animate-pulse">
          ...
        </span>
      )}
    </div>
  );
}
