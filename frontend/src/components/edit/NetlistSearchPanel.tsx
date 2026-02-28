/**
 * NetlistSearchPanel — compact unified NQS netlist search viewer.
 *
 * Template + net inputs side-by-side with regex toggle overlays (.*).
 * Tabbed results: "Nets" or "Templates" (only one active at a time).
 * Used inside both AF and Mutex edit dialogs.
 */

import { useCallback, useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Loader2, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import * as api from "@/api/documents";

interface NetlistSearchPanelProps {
  /** Current template value (pre-filled from form) */
  template: string;
  /** Current net pattern (pre-filled from form) */
  netPattern: string;
  /** Whether template field is regex */
  templateRegex: boolean;
  /** Whether net field is regex */
  netRegex: boolean;
  /** Template field change */
  onTemplateChange: (v: string) => void;
  /** Net pattern field change */
  onNetPatternChange: (v: string) => void;
  /** Template regex toggle */
  onTemplateRegexChange: (v: boolean) => void;
  /** Net regex toggle */
  onNetRegexChange: (v: boolean) => void;
  /** Called when a net is clicked in results */
  onNetSelect?: (net: string) => void;
  /** Extra action per result row (e.g., "Add to mutexed") */
  renderResultAction?: (item: string, kind: "net" | "template") => React.ReactNode;
  /** Extra action buttons rendered in the header bar (e.g., "Add" from input) */
  extraActions?: React.ReactNode;
}

type ResultTab = "nets" | "templates";

export function NetlistSearchPanel({
  template,
  netPattern,
  templateRegex,
  netRegex,
  onTemplateChange,
  onNetPatternChange,
  onTemplateRegexChange,
  onNetRegexChange,
  onNetSelect,
  renderResultAction,
  extraActions,
}: NetlistSearchPanelProps) {
  const [nets, setNets] = useState<string[]>([]);
  const [templates, setTemplates] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [activeTab, setActiveTab] = useState<ResultTab>("nets");

  const doSearch = useCallback(async () => {
    if (!netPattern && !template) return;
    setLoading(true);
    try {
      const result = await api.queryNets(
        template || null,
        netPattern,
        templateRegex,
        netRegex,
      );
      setNets(result.nets);
      setTemplates(result.templates);
      setSearched(true);
    } catch {
      setNets([]);
      setTemplates([]);
    } finally {
      setLoading(false);
    }
  }, [template, netPattern, templateRegex, netRegex]);

  // Auto-search with debounce
  useEffect(() => {
    if (!netPattern && !template) {
      setNets([]);
      setTemplates([]);
      setSearched(false);
      return;
    }
    const timer = setTimeout(doSearch, 400);
    return () => clearTimeout(timer);
  }, [doSearch, template, netPattern]);

  const resultItems = activeTab === "nets" ? nets : templates;

  return (
    <div className="flex flex-col rounded-lg border bg-muted/20 p-2">
      {/* Header row: label + search button */}
      <div className="mb-1.5 flex items-center justify-between">
        <span className="flex items-center gap-1 text-2xs font-medium text-muted-foreground">
          <Search className="h-3 w-3" />
          NQS Search
        </span>
        <div className="flex items-center gap-1">
          {extraActions}
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-5 px-1.5 text-2xs"
            onClick={doSearch}
            disabled={loading}
          >
            {loading && <Loader2 className="mr-1 h-3 w-3 animate-spin" />}
            Search
          </Button>
        </div>
      </div>

      {/* Template + Net inputs — single row */}
      <div className="flex gap-2">
        {/* Template */}
        <div className="relative flex-1">
          <input
            type="text"
            value={template}
            onChange={(e) => onTemplateChange(e.target.value)}
            placeholder="Template"
            className="h-7 w-full rounded-md border bg-background px-2 pr-8 text-xs outline-none placeholder:text-muted-foreground/40 focus:ring-1 focus:ring-ring"
          />
          <button
            type="button"
            title="Template regex"
            onClick={() => onTemplateRegexChange(!templateRegex)}
            className={cn(
              "absolute right-1 top-1/2 -translate-y-1/2 rounded px-1 py-0.5 font-mono text-2xs font-bold transition-colors",
              templateRegex
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground/40 hover:bg-accent hover:text-foreground",
            )}
          >
            .*
          </button>
        </div>
        {/* Net */}
        <div className="relative flex-1">
          <input
            type="text"
            value={netPattern}
            onChange={(e) => onNetPatternChange(e.target.value)}
            placeholder="Net pattern"
            className="h-7 w-full rounded-md border bg-background px-2 pr-8 text-xs outline-none placeholder:text-muted-foreground/40 focus:ring-1 focus:ring-ring"
          />
          <button
            type="button"
            title="Net regex"
            onClick={() => onNetRegexChange(!netRegex)}
            className={cn(
              "absolute right-1 top-1/2 -translate-y-1/2 rounded px-1 py-0.5 font-mono text-2xs font-bold transition-colors",
              netRegex
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground/40 hover:bg-accent hover:text-foreground",
            )}
          >
            .*
          </button>
        </div>
      </div>

      {/* Tabbed results */}
      {searched && (
        <div className="mt-2 flex flex-1 flex-col overflow-hidden">
          {/* Tab bar */}
          <div className="flex border-b">
            <button
              type="button"
              className={cn(
                "px-3 py-1 text-2xs font-medium transition-colors",
                activeTab === "nets"
                  ? "border-b-2 border-primary text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
              onClick={() => setActiveTab("nets")}
            >
              Nets ({nets.length})
            </button>
            <button
              type="button"
              className={cn(
                "px-3 py-1 text-2xs font-medium transition-colors",
                activeTab === "templates"
                  ? "border-b-2 border-primary text-foreground"
                  : "text-muted-foreground hover:text-foreground",
              )}
              onClick={() => setActiveTab("templates")}
            >
              Templates ({templates.length})
            </button>
          </div>

          {/* Result list */}
          <ScrollArea className="max-h-44 flex-1 rounded-b border-x border-b bg-background p-0.5">
            {resultItems.length === 0 ? (
              <p className="px-2 py-3 text-center text-2xs text-muted-foreground/50">
                No {activeTab} matched
              </p>
            ) : (
              <div className="space-y-px">
                {resultItems.map((item) => (
                  <div
                    key={item}
                    className="group/net flex items-center justify-between rounded px-2 py-0.5 hover:bg-accent"
                  >
                    <button
                      type="button"
                      className="flex-1 truncate text-left font-mono text-2xs"
                      onClick={() => {
                        if (activeTab === "nets") onNetSelect?.(item);
                      }}
                    >
                      {item}
                    </button>
                    {renderResultAction?.(item, activeTab === "nets" ? "net" : "template")}
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>
      )}

      {!searched && (
        <p className="mt-2 text-center text-2xs text-muted-foreground/50">
          Enter a template or net pattern to search
        </p>
      )}
    </div>
  );
}
