import type { DocumentLine, DocumentSummary } from "@/types/api"

/**
 * Example mock data so the UI can be demonstrated without a running backend.
 * When the real API is available the app uses React Query to fetch from /api.
 */

export const MOCK_SUMMARY: DocumentSummary = {
  doc_id: "mycell_af_dcfg",
  doc_type: "af",
  file_path: "data/cfg/mycell.af.dcfg",
  total_lines: 42,
  status_counts: { ok: 34, warning: 4, error: 2, comment: 1, conflict: 1 },
  can_undo: false,
  can_redo: false,
}

const statuses: Array<DocumentLine["status"]> = [
  "ok", "ok", "ok", "comment", "ok", "ok", "warning", "ok", "ok", "ok",
  "ok", "error", "ok", "ok", "ok", "ok", "warning", "ok", "ok", "ok",
  "conflict", "ok", "ok", "ok", "ok", "ok", "ok", "warning", "ok", "ok",
  "ok", "ok", "ok", "ok", "ok", "ok", "error", "ok", "ok", "ok",
  "warning", "ok",
]

const rawTexts = [
  'af_define net="VDD" template="power_supply"',
  'af_define net="VSS" template="ground"',
  'af_define net="CLK" template="clock_input"',
  "# This section configures the analog front-end signals",
  'af_define net="DATA_IN<0>" template="data_input"',
  'af_define net="DATA_IN<1>" template="data_input"',
  'af_define net="DATA_IN<2>" template="data_input"',
  'af_define net="DATA_OUT<0>" template="data_output"',
  'af_define net="DATA_OUT<1>" template="data_output"',
  'af_define net="DATA_OUT<2>" template="data_output"',
  'af_define net="BIAS_P" template="bias"',
  'af_define net="BIAS_N" template="bias_invalid"',
  'af_define net="REF_TOP" template="reference"',
  'af_define net="REF_BOT" template="reference"',
  'af_define net="EN" template="enable"',
  'af_define net="RST" template="reset"',
  'af_define net="VCTRL" template="ctrl" fev="non_canonical"',
  'af_define net="IOUT" template="current_output"',
  'af_define net="IOUT_B" template="current_output"',
  'af_define net="SENSE" template="sense"',
  'af_define net="MUX_A" template="mux_sel"',
  'af_define net="MUX_B" template="mux_sel"',
  'af_define net="CAL<0>" template="calibration"',
  'af_define net="CAL<1>" template="calibration"',
  'af_define net="CAL<2>" template="calibration"',
  'af_define net="CAL<3>" template="calibration"',
  'af_define net="PD" template="power_down"',
  'af_define net="TRIM<0>" template="trim" fev="approx"',
  'af_define net="TRIM<1>" template="trim"',
  'af_define net="TRIM<2>" template="trim"',
  'af_define net="TRIM<3>" template="trim"',
  'af_define net="COMP_OUT" template="comparator"',
  'af_define net="COMP_IN_P" template="comparator_input"',
  'af_define net="COMP_IN_N" template="comparator_input"',
  'af_define net="OSC" template="oscillator"',
  'af_define net="DIV_OUT" template="divider"',
  'af_define net="TEST_MODE" template="invalid_template"',
  'af_define net="SCAN_IN" template="scan"',
  'af_define net="SCAN_OUT" template="scan"',
  'af_define net="JTAG_TDI" template="jtag"',
  'af_define net="JTAG_TDO" template="jtag" fev="non_standard"',
  'af_define net="JTAG_TCK" template="jtag"',
]

export const MOCK_LINES: DocumentLine[] = rawTexts.map((raw_text, i) => {
  const status = statuses[i] ?? "ok"
  const errors: string[] = []
  const warnings: string[] = []

  if (status === "error") errors.push(`Parse error on line ${i + 1}: invalid template reference`)
  if (status === "warning")
    warnings.push(`Net name may be non-canonical on line ${i + 1}`)

  return {
    position: i,
    raw_text,
    status,
    errors,
    warnings,
    has_data: status !== "comment",
    data: null,
    conflict_info:
      status === "conflict"
        ? { conflicting_positions: [21], shared_nets: ["MUX_A"] }
        : null,
  }
})
