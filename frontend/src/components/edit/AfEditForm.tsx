/**
 * AfEditForm — dialog form for editing AF configuration lines.
 *
 * Fields:
 *  - AF value (number input)
 *  - Checkboxes: EM, SH, SCH
 *  - NetlistSearchPanel (template, net, regex toggles, NQS results)
 *
 * Uses the hydrate → update → commit pattern:
 *  1. On open: hydrate_session to get current data
 *  2. On field change: hydrate_session with updated fields (preview)
 *  3. On Save: commit_edit to write back to document
 */

import { useCallback, useEffect, useState } from "react";
import { useEditStore, type AfSessionData } from "@/stores/edit-store";
import { useDocumentStore } from "@/stores/document-store";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { NetlistSearchPanel } from "./NetlistSearchPanel";
import { Loader2, Save, X, AlertTriangle, AlertCircle } from "lucide-react";
import * as api from "@/api/documents";

export function AfEditForm() {
  const {
    docId,
    position,
    sessionData,
    loading,
    errors,
    warnings,
    setSessionData,
    setLoading,
  } = useEditStore();

  const data = sessionData as AfSessionData | null;

  /* ---- Local form state (mirrors sessionData, but allows fast typing) ---- */
  const [form, setForm] = useState<AfSessionData>({
    template: null,
    net: "",
    af_value: 0,
    is_template_regex: false,
    is_net_regex: false,
    is_em_enabled: false,
    is_sh_enabled: false,
    is_sch_enabled: false,
  });

  // Sync local form when session data arrives
  useEffect(() => {
    if (data) {
      setForm(data);
    }
  }, [data]);

  /* ---- Hydrate on mount ---- */
  useEffect(() => {
    if (docId === null || position === null) return;
    let cancelled = false;

    (async () => {
      setLoading(true);
      try {
        const result = (await api.hydrateSession(docId, position, null)) as {
          data: AfSessionData;
        };
        if (!cancelled) setSessionData(result.data);
      } catch {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [docId, position, setSessionData, setLoading]);

  /* ---- Field change handler ---- */
  const updateField = useCallback(
    (field: keyof AfSessionData, value: unknown) => {
      setForm((prev) => ({ ...prev, [field]: value }));
    },
    [],
  );

  /* ---- Apply fields to backend (debounced preview) ---- */
  useEffect(() => {
    if (docId === null || position === null || loading) return;

    const timer = setTimeout(async () => {
      try {
        const result = (await api.hydrateSession(docId, position, {
          template: form.template,
          net: form.net,
          af_value: form.af_value,
          is_template_regex: form.is_template_regex,
          is_net_regex: form.is_net_regex,
          is_em_enabled: form.is_em_enabled,
          is_sh_enabled: form.is_sh_enabled,
          is_sch_enabled: form.is_sch_enabled,
        })) as { data: AfSessionData };
        // Don't overwrite user's typing, just update store silently
        useEditStore.setState({ sessionData: result.data });
      } catch {
        // ignore transient errors
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [docId, position, form, loading]);

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
    <div className="space-y-5">
      {/* Netlist Search Panel — template, net, regex toggles, NQS results */}
      <NetlistSearchPanel
        template={form.template ?? ""}
        netPattern={form.net}
        templateRegex={form.is_template_regex}
        netRegex={form.is_net_regex}
        onTemplateChange={(v) => updateField("template", v || null)}
        onNetPatternChange={(v) => updateField("net", v)}
        onTemplateRegexChange={(v) => updateField("is_template_regex", v)}
        onNetRegexChange={(v) => updateField("is_net_regex", v)}
        onNetSelect={(net) => updateField("net", net)}
      />

      {/* AF Value + Options in one row */}
      <div className="flex items-end gap-4">
        <div className="w-32 space-y-1.5">
          <Label htmlFor="af-value">AF Value</Label>
          <Input
            id="af-value"
            type="number"
            step="any"
            value={form.af_value}
            onChange={(e) =>
              updateField("af_value", parseFloat(e.target.value) || 0)
            }
          />
        </div>

        <div className="flex flex-wrap items-center gap-4 pb-1">
          <div className="flex items-center gap-2">
            <Checkbox
              id="af-em"
              checked={form.is_em_enabled}
              onCheckedChange={(v) =>
                updateField("is_em_enabled", Boolean(v))
              }
            />
            <Label htmlFor="af-em" className="text-xs font-normal">
              EM
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="af-sh"
              checked={form.is_sh_enabled}
              onCheckedChange={(v) =>
                updateField("is_sh_enabled", Boolean(v))
              }
            />
            <Label htmlFor="af-sh" className="text-xs font-normal">
              SH
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox
              id="af-sch"
              checked={form.is_sch_enabled}
              onCheckedChange={(v) =>
                updateField("is_sch_enabled", Boolean(v))
              }
            />
            <Label htmlFor="af-sch" className="text-xs font-normal">
              SCH
            </Label>
          </div>
        </div>
      </div>

      {/* Validation messages */}
      {errors.length > 0 && (
        <div className="space-y-1 rounded-md border border-destructive/50 bg-destructive/10 p-3">
          {errors.map((e, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-destructive">
              <AlertCircle className="mt-0.5 h-3 w-3 shrink-0" />
              {e}
            </div>
          ))}
        </div>
      )}

      {warnings.length > 0 && (
        <div className="space-y-1 rounded-md border border-status-warning/50 bg-status-warning/10 p-3">
          {warnings.map((w, i) => (
            <div key={i} className="flex items-start gap-2 text-xs text-status-warning">
              <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0" />
              {w}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/** Footer buttons for the AF form */
export function AfEditFormFooter() {
  const { docId, position, committing, closeEdit, setCommitting, setValidation } =
    useEditStore();
  const refreshLines = useDocumentStore((s) => s.refreshLines);

  // Read form from the store's sessionData
  const sessionData = useEditStore((s) => s.sessionData) as AfSessionData | null;

  const handleCommit = useCallback(async () => {
    if (docId === null || position === null || !sessionData) return;
    setCommitting(true);
    setValidation([], []);

    try {
      await api.hydrateSession(docId, position, {
        template: sessionData.template,
        net: sessionData.net,
        af_value: sessionData.af_value,
        is_template_regex: sessionData.is_template_regex,
        is_net_regex: sessionData.is_net_regex,
        is_em_enabled: sessionData.is_em_enabled,
        is_sh_enabled: sessionData.is_sh_enabled,
        is_sch_enabled: sessionData.is_sch_enabled,
      });

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
  }, [docId, position, sessionData, setCommitting, setValidation, refreshLines, closeEdit]);

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
