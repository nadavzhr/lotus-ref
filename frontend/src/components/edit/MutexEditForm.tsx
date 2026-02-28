/**
 * MutexEditForm — dialog form for editing Mutex configuration lines.
 *
 * Layout:
 *  - NetlistSearchPanel for NQS search with add-to-mutexed/active actions
 *  - Session info bar (template, regex, num_active, fev — derived from session)
 *  - Two side-by-side scrollable lists: Mutexed Nets / Active Nets
 *  - FEV mode control at the bottom
 *
 * Uses the mutex-specific API endpoints (add/remove mutexed/active, set-fev, set-num-active).
 * Stores full entry objects (with template_name, regex_mode, match_count) so
 * remove / promote operations pass the correct metadata to the backend.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useEditStore, type MutexSessionData, type MutexEntryData } from "@/stores/edit-store";
import { useDocumentStore } from "@/stores/document-store";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { NetlistSearchPanel } from "./NetlistSearchPanel";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Loader2,
  Save,
  X,
  Plus,
  Trash2,
  ArrowRight,
  AlertTriangle,
  AlertCircle,
} from "lucide-react";
import * as api from "@/api/documents";

/* ---- Helpers ---- */

const FEV_OPTIONS = [
  { value: "_none_", label: "(none)" },
  { value: "low", label: "Low" },
  { value: "high", label: "High" },
  { value: "ignore", label: "Ignore" },
];

/**
 * Parse a result item from NQS search into (template, net).
 * NQS returns nets in "template:net" format. We split on the FIRST colon
 * because net names can contain colons in bus notation (e.g. net[0:2]).
 */
function parseNetItem(item: string): { template: string | null; net: string } {
  const idx = item.indexOf(":");
  if (idx >= 0) {
    return { template: item.slice(0, idx), net: item.slice(idx + 1) };
  }
  return { template: null, net: item };
}

/* ---- Component ---- */

export function MutexEditForm() {
  const {
    docId,
    position,
    sessionData,
    loading,
    errors,
    warnings,
    setSessionData,
    setLoading,
    setValidation,
  } = useEditStore();

  const data = sessionData as MutexSessionData | null;

  /* ---- Search state for NetlistSearchPanel ---- */
  const [searchTemplate, setSearchTemplate] = useState("");
  const [searchNet, setSearchNet] = useState("");
  const [searchTemplateRegex, setSearchTemplateRegex] = useState(false);
  const [searchNetRegex, setSearchNetRegex] = useState(false);

  /* ---- Derived sets for fast lookup ---- */
  const mutexedEntries = data?.mutexed_entries ?? [];
  const activeEntries = data?.active_entries ?? [];
  const hasActiveNets = activeEntries.length > 0;

  // Sets of net names for quick membership checks (plain names, no template prefix)
  const mutexedNetNames = useMemo(
    () => new Set(mutexedEntries.map((e) => e.net_name)),
    [mutexedEntries],
  );
  const activeNetNames = useMemo(
    () => new Set(activeEntries.map((e) => e.net_name)),
    [activeEntries],
  );

  /* ---- Hydrate on mount ---- */
  useEffect(() => {
    if (docId === null || position === null) return;
    let cancelled = false;

    (async () => {
      setLoading(true);
      try {
        // Step 1: Start the edit session (hydrates the controller with line data)
        await api.hydrateSession(docId, position, null);
        if (cancelled) return;

        // Step 2: Fetch the rich session state (with full entry objects)
        const session = (await api.getMutexSession(docId, position)) as MutexSessionData;
        if (!cancelled) {
          setSessionData(session);
          // Pre-fill the search template from the session's derived template
          if (session.template) {
            setSearchTemplate(session.template);
          }
        }
      } catch {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [docId, position, setSessionData, setLoading]);

  /* ---- Apply API mutation result (all mutation endpoints return the full session) ---- */
  const applyResult = useCallback(
    (raw: unknown) => {
      // Mutation endpoints return the rich session format directly
      setSessionData(raw as MutexSessionData);
    },
    [setSessionData],
  );

  /* ---- Mutation helpers ---- */

  /**
   * Add a net to the mutexed set from an NQS search result.
   * NQS results are in "template:net" format — parseNetItem splits them.
   */
  const addMutexedFromSearch = useCallback(
    async (item: string) => {
      if (docId === null || position === null) return;
      const { template, net } = parseNetItem(item);
      try {
        const result = await api.mutexAddMutexed(
          docId, position, template, net, false,
        );
        applyResult(result);
      } catch (err) {
        setValidation(
          [err instanceof Error ? err.message : "Failed to add net"],
          [],
        );
      }
    },
    [docId, position, applyResult, setValidation],
  );

  /**
   * Add a net pattern from the search INPUT field (not a search result).
   * Uses searchTemplate and searchNetRegex from the form state.
   */
  const addMutexedFromInput = useCallback(
    async () => {
      if (docId === null || position === null) return;
      if (!searchNet.trim()) {
        setValidation(["Enter a net pattern first"], []);
        return;
      }
      const template = searchTemplate.trim() || null;
      try {
        const result = await api.mutexAddMutexed(
          docId, position, template, searchNet.trim(), searchNetRegex,
        );
        applyResult(result);
      } catch (err) {
        setValidation(
          [err instanceof Error ? err.message : "Failed to add net"],
          [],
        );
      }
    },
    [docId, position, searchTemplate, searchNet, searchNetRegex, applyResult, setValidation],
  );

  /**
   * Remove a mutexed entry. Uses the entry's own template_name and regex_mode.
   */
  const removeMutexed = useCallback(
    async (entry: MutexEntryData) => {
      if (docId === null || position === null) return;
      try {
        const result = await api.mutexRemoveMutexed(
          docId, position,
          entry.template_name,
          entry.net_name,
          entry.regex_mode,
        );
        applyResult(result);
      } catch (err) {
        setValidation(
          [err instanceof Error ? err.message : "Failed to remove net"],
          [],
        );
      }
    },
    [docId, position, applyResult, setValidation],
  );

  /**
   * Add a net to the active set from an NQS search result.
   */
  const addActiveFromSearch = useCallback(
    async (item: string) => {
      if (docId === null || position === null) return;
      const { template, net } = parseNetItem(item);
      try {
        const result = await api.mutexAddActive(
          docId, position, template, net,
        );
        applyResult(result);
      } catch (err) {
        setValidation(
          [err instanceof Error ? err.message : "Failed to add active net"],
          [],
        );
      }
    },
    [docId, position, applyResult, setValidation],
  );

  /**
   * Promote a mutexed entry to active. Uses the entry's own template_name.
   */
  const promoteToActive = useCallback(
    async (entry: MutexEntryData) => {
      if (docId === null || position === null) return;
      try {
        const result = await api.mutexAddActive(
          docId, position,
          entry.template_name,
          entry.net_name,
        );
        applyResult(result);
      } catch (err) {
        setValidation(
          [err instanceof Error ? err.message : "Failed to promote to active"],
          [],
        );
      }
    },
    [docId, position, applyResult, setValidation],
  );

  /**
   * Remove an active entry. Uses the entry's own template_name.
   */
  const removeActive = useCallback(
    async (entry: MutexEntryData) => {
      if (docId === null || position === null) return;
      try {
        const result = await api.mutexRemoveActive(
          docId, position,
          entry.template_name,
          entry.net_name,
        );
        applyResult(result);
      } catch (err) {
        setValidation(
          [err instanceof Error ? err.message : "Failed to remove active net"],
          [],
        );
      }
    },
    [docId, position, applyResult, setValidation],
  );

  const handleSetFev = useCallback(
    async (fev: string) => {
      if (docId === null || position === null) return;
      const actualFev = fev === "_none_" ? "" : fev;
      try {
        const result = await api.mutexSetFev(docId, position, actualFev);
        applyResult(result);
      } catch (err) {
        setValidation(
          [err instanceof Error ? err.message : "Failed to set FEV"],
          [],
        );
      }
    },
    [docId, position, applyResult, setValidation],
  );

  const handleSetNumActive = useCallback(
    async (value: number) => {
      if (docId === null || position === null) return;
      try {
        const result = await api.mutexSetNumActive(docId, position, value);
        applyResult(result);
      } catch (err) {
        setValidation(
          [err instanceof Error ? err.message : "Failed to set num_active"],
          [],
        );
      }
    },
    [docId, position, applyResult, setValidation],
  );

  /* ---- Render ---- */

  if (loading) {
    return (
      <div className="flex h-40 items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading session...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Netlist Search Panel — template & net inputs built-in */}
      <NetlistSearchPanel
        template={searchTemplate}
        netPattern={searchNet}
        templateRegex={searchTemplateRegex}
        netRegex={searchNetRegex}
        onTemplateChange={setSearchTemplate}
        onNetPatternChange={setSearchNet}
        onTemplateRegexChange={setSearchTemplateRegex}
        onNetRegexChange={setSearchNetRegex}
        renderResultAction={(item, kind) => {
          if (kind !== "net") return null;
          // NQS results are "template:net" — extract net for membership check
          const { net: parsedNet } = parseNetItem(item);
          const isInMutexed = mutexedNetNames.has(parsedNet);
          const isInActive = activeNetNames.has(parsedNet);
          return (
            <div className="flex shrink-0 items-center gap-0.5">
              {!isInMutexed && !isInActive && (
                <>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="h-5 w-5"
                    title="Add to mutexed"
                    onClick={() => addMutexedFromSearch(item)}
                  >
                    <Plus className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    className="h-5 w-5 text-primary"
                    title="Add to active"
                    onClick={() => addActiveFromSearch(item)}
                  >
                    <ArrowRight className="h-3 w-3" />
                  </Button>
                </>
              )}
              {isInMutexed && !isInActive && (
                <Button
                  variant="ghost"
                  size="icon-sm"
                  className="h-5 w-5 text-primary"
                  title="Promote to active"
                  onClick={() => addActiveFromSearch(item)}
                >
                  <ArrowRight className="h-3 w-3" />
                </Button>
              )}
              {(isInMutexed || isInActive) && (
                <span className="px-1 text-2xs text-muted-foreground">
                  {isInActive ? "active" : "mutexed"}
                </span>
              )}
            </div>
          );
        }}
        extraActions={
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="h-5 px-1.5 text-2xs"
            onClick={addMutexedFromInput}
            title="Add current pattern to mutexed"
          >
            <Plus className="mr-0.5 h-3 w-3" />
            Add
          </Button>
        }
      />

      {/* Session Info Bar */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border bg-muted/30 px-3 py-1.5 text-2xs text-muted-foreground">
        <span>
          Template:{" "}
          <span className="font-medium text-foreground">
            {data?.template || "(none)"}
          </span>
        </span>
        <span>
          Regex:{" "}
          <span className="font-medium text-foreground">
            {data?.regex_mode === null || data?.regex_mode === undefined
              ? "(unset)"
              : String(data.regex_mode)}
          </span>
        </span>
        <span className="flex items-center gap-1">
          Num active:{" "}
          {hasActiveNets ? (
            <>
              <span className="font-medium text-foreground">{data?.num_active ?? 0}</span>
              <span className="text-muted-foreground/60">(derived)</span>
            </>
          ) : (
            <Input
              type="number"
              min={0}
              className="ml-1 inline-flex h-5 w-14 px-1 text-2xs"
              value={data?.num_active ?? 1}
              onChange={(e) =>
                handleSetNumActive(parseInt(e.target.value, 10) || 0)
              }
            />
          )}
        </span>
        <span>
          FEV:{" "}
          <span className="font-medium text-foreground">
            {data?.fev || "(none)"}
          </span>
        </span>
      </div>

      {/* Two-column: Mutexed Nets / Active Nets */}
      <div className="grid grid-cols-2 gap-3">
        {/* Mutexed Nets */}
        <div className="space-y-1">
          <Label className="text-2xs">
            Mutexed Nets ({mutexedEntries.length})
          </Label>
          <ScrollArea className="h-40 rounded border bg-background">
            {mutexedEntries.length === 0 ? (
              <div className="flex h-full items-center justify-center p-4">
                <span className="text-2xs text-muted-foreground/50">
                  No mutexed nets
                </span>
              </div>
            ) : (
              <div className="space-y-px p-0.5">
                {mutexedEntries.map((entry) => {
                  const isActive = activeNetNames.has(entry.net_name);
                  // Promote button: only for non-regex, single-match, not already active
                  const canPromote = !entry.regex_mode && entry.match_count === 1 && !isActive;
                  return (
                    <div
                      key={`${entry.template_name ?? ""}:${entry.net_name}:${entry.regex_mode}`}
                      className={`group/entry flex items-center justify-between rounded px-2 py-0.5 hover:bg-accent ${isActive ? "bg-primary/5" : ""}`}
                    >
                      <div className="flex min-w-0 items-center gap-1.5">
                        <span className="truncate font-mono text-2xs">{entry.net_name}</span>
                        {entry.regex_mode && (
                          <span className="shrink-0 rounded bg-orange-500/15 px-1 py-px text-[9px] font-medium text-orange-500">
                            regex
                          </span>
                        )}
                        <span className={`shrink-0 text-[9px] ${entry.match_count > 0 ? "text-muted-foreground/60" : "text-destructive"}`}>
                          {entry.match_count > 0
                            ? `${entry.match_count} match${entry.match_count !== 1 ? "es" : ""}`
                            : "no matches"}
                        </span>
                      </div>
                      <div className="flex shrink-0 gap-0.5 opacity-0 group-hover/entry:opacity-100">
                        {canPromote && (
                          <Button
                            variant="ghost"
                            size="icon-sm"
                            className="h-5 w-5"
                            title="Promote to active"
                            onClick={() => promoteToActive(entry)}
                          >
                            <ArrowRight className="h-3 w-3" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          className="h-5 w-5 text-destructive hover:text-destructive"
                          title="Remove"
                          onClick={() => removeMutexed(entry)}
                        >
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Active Nets */}
        <div className="space-y-1">
          <Label className="text-2xs">
            Active Nets ({activeEntries.length})
          </Label>
          <ScrollArea className="h-40 rounded border bg-background">
            {activeEntries.length === 0 ? (
              <div className="flex h-full items-center justify-center p-4">
                <span className="text-2xs text-muted-foreground/50">
                  No active nets
                </span>
              </div>
            ) : (
              <div className="space-y-px p-0.5">
                {activeEntries.map((entry) => (
                  <div
                    key={`${entry.template_name ?? ""}:${entry.net_name}`}
                    className="group/entry flex items-center justify-between rounded px-2 py-0.5 hover:bg-accent"
                  >
                    <div className="flex min-w-0 items-center gap-1.5">
                      <span className="truncate font-mono text-2xs">{entry.net_name}</span>
                      <span className="shrink-0 text-[9px] text-muted-foreground/60">
                        {entry.match_count} match{entry.match_count !== 1 ? "es" : ""}
                      </span>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      className="h-5 w-5 text-destructive opacity-0 hover:text-destructive group-hover/entry:opacity-100"
                      title="Remove from active"
                      onClick={() => removeActive(entry)}
                    >
                      <Trash2 className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </ScrollArea>
        </div>
      </div>

      {/* FEV Mode — at the bottom */}
      <div className="flex items-center gap-3">
        <Label htmlFor="mutex-fev" className="text-2xs text-muted-foreground whitespace-nowrap">
          FEV Mode
        </Label>
        <Select
          value={data?.fev === "" ? "_none_" : (data?.fev ?? "_none_")}
          onValueChange={handleSetFev}
        >
          <SelectTrigger id="mutex-fev" className="h-7 w-32 text-xs">
            <SelectValue placeholder="Select FEV" />
          </SelectTrigger>
          <SelectContent>
            {FEV_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Validation messages */}
      {errors.length > 0 && (
        <div className="space-y-1 rounded-md border border-destructive/50 bg-destructive/10 p-2">
          {errors.map((e, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs text-destructive">
              <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
              {e}
            </div>
          ))}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="space-y-1 rounded-md border border-status-warning/50 bg-status-warning/10 p-2">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-1.5 text-xs text-status-warning">
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
              {w}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Footer buttons for the Mutex form */
export function MutexEditFormFooter() {
  const { docId, position, committing, closeEdit, setCommitting, setValidation } =
    useEditStore();
  const refreshLines = useDocumentStore((s) => s.refreshLines);

  const handleCommit = useCallback(async () => {
    if (docId === null || position === null) return;
    setCommitting(true);
    setValidation([], []);

    try {
      const result = (await api.commitEdit(docId, position)) as {
        errors?: string[];
        warnings?: string[];
      };

      if (result.errors && result.errors.length > 0) {
        setValidation(result.errors, result.warnings ?? []);
        setCommitting(false);
        return;
      }

      await refreshLines(docId);
      closeEdit();
    } catch (err) {
      setValidation(
        [err instanceof Error ? err.message : "Commit failed"],
        [],
      );
      setCommitting(false);
    }
  }, [docId, position, setCommitting, setValidation, refreshLines, closeEdit]);

  return (
    <>
      <Button variant="outline" size="sm" onClick={closeEdit} disabled={committing}>
        <X className="mr-1 h-3 w-3" />
        Cancel
      </Button>
      <Button size="sm" onClick={handleCommit} disabled={committing}>
        {committing ? (
          <Loader2 className="mr-1 h-3 w-3 animate-spin" />
        ) : (
          <Save className="mr-1 h-3 w-3" />
        )}
        Save
      </Button>
    </>
  );
}

