import type { ConfigLine, Problem, LogEntry, ChatMessage } from "@/types"

export const mockLines: ConfigLine[] = [
  { id: 1, text: "* Top-level clock nets", status: "comment" },
  { id: 2, text: "clk_core 0.45", status: "valid" },
  { id: 3, text: "clk_mem 0.38", status: "valid" },
  { id: 4, text: "clk_io 0.22 em", status: "valid" },
  { id: 5, text: "# Power rail overrides", status: "comment" },
  { id: 6, text: "data_bus[0:31] 0.15", status: "valid" },
  { id: 7, text: "addr_bus[0:15] 0.12", status: "warning" },
  { id: 8, text: "ctrl_sig 0.67 em sh", status: "valid" },
  { id: 9, text: "reset_n 0.01", status: "valid" },
  { id: 10, text: "invalid_net_xyz 0.50", status: "error" },
  { id: 11, text: "# Scan chain signals", status: "comment" },
  { id: 12, text: "scan_in 0.05", status: "valid" },
  { id: 13, text: "scan_out 0.05", status: "valid" },
  { id: 14, text: "scan_en 0.02", status: "valid" },
  { id: 15, text: "pll_out 0.90 em", status: "conflict" },
  { id: 16, text: "mem_wr_en 0.18", status: "valid" },
  { id: 17, text: "mem_rd_en 0.25", status: "valid" },
  { id: 18, text: "fifo_.*_ptr 0.30", status: "valid" },
  { id: 19, text: "dma_req[0:3] 0.08", status: "valid" },
  { id: 20, text: "irq_[0-9]+ 0.03", status: "warning" },
  { id: 21, text: "conflicting_net 0.50", status: "conflict" },
  { id: 22, text: "another_conflict 0.50", status: "conflict" },
]

export const mockProblems: Problem[] = [
  { id: 1, type: "error", message: "Net 'invalid_net_xyz' not found in netlist", line: 10, file: "my_block.af.dcfg" },
  { id: 2, type: "warning", message: "Regex 'irq_[0-9]+' matches 0 nets — possible typo", line: 20, file: "my_block.af.dcfg" },
  { id: 3, type: "warning", message: "Bus 'addr_bus[0:15]' — 3 nets not found in template", line: 7, file: "my_block.af.dcfg" },
  { id: 4, type: "conflict", message: "Conflict: Line 15 ('pll_out') overlaps with Line 8 ('ctrl_sig') on nets: pll_out_clk", line: 15, file: "my_block.af.dcfg" },
]

export const mockLogs: LogEntry[] = [
  { time: "15:03:22", level: "INFO", message: "Application started" },
  { time: "15:03:23", level: "INFO", message: "Ward resolved: /path/to/ward" },
  { time: "15:03:23", level: "INFO", message: "Cell: my_block" },
  { time: "15:03:24", level: "INFO", message: "Loading SPICE netlist: /path/to/ward/netlists/spice/my_block.sp" },
  { time: "15:03:28", level: "INFO", message: "Netlist loaded: 142 templates, 523,841 nets" },
  { time: "15:03:28", level: "INFO", message: "Loading AF config: my_block.af.dcfg" },
  { time: "15:03:28", level: "INFO", message: "Parsed 20 lines (12 valid, 3 comments, 2 warnings, 1 error)" },
  { time: "15:03:29", level: "WARN", message: "Conflict detected between lines 8 and 15" },
  { time: "15:03:29", level: "INFO", message: "Loading Mutex config: my_block.mutex.dcfg" },
  { time: "15:03:29", level: "INFO", message: "Parsed 8 mutex groups" },
]

export const initialChatMessages: ChatMessage[] = [
  {
    id: 1,
    role: "assistant",
    content: "Hi! I'm your Lotus AI assistant. I can help you with activity factors, mutex configurations, netlist queries, and more. How can I help?",
    timestamp: new Date(),
  },
]

export const mockNets = [
  "u_core:clk_core",
  "u_core:clk_div2",
  "u_core:clk_gated",
  "u_mem:clk_mem",
  "u_mem:clk_mem_div2",
  "u_io:clk_io",
]

export const mockTemplates = [
  "u_core",
  "u_core/u_alu",
  "u_core/u_regfile",
  "u_mem",
  "u_io",
]

export const mockMutexNets = ["clk_phase_a", "clk_phase_b", "clk_phase_c"]
export const mockActiveNets = ["clk_phase_a"]

export function getStubResponse(input: string): string {
  const lower = input.toLowerCase()
  if (lower.includes("activity") || lower.includes("af")) {
    return "Activity factors represent the switching probability of nets. Values range from 0.0 (static) to 1.0 (toggling every cycle). Typical clock nets use 0.5, while data buses vary based on workload."
  }
  if (lower.includes("mutex")) {
    return "Mutex groups define mutually exclusive nets — signals that can never switch simultaneously. This helps prevent overestimation of power consumption in the analysis."
  }
  if (lower.includes("netlist") || lower.includes("net")) {
    return "You can search nets using the Netlist Search panel in the edit area. Use template and net filters, with optional regex support, to find specific signals."
  }
  if (lower.includes("help") || lower.includes("what can")) {
    return "I can help with:\n• Explaining activity factor concepts\n• Mutex configuration guidance\n• Netlist search tips\n• Troubleshooting config errors\n• General Lotus workflow questions"
  }
  return "I understand your question. Once the Copilot SDK is connected, I'll be able to provide contextual answers based on your actual configuration and netlist data."
}

export function getLineStats(lines: ConfigLine[]) {
  const valid = lines.filter((l) => l.status === "valid").length
  const warnings = lines.filter((l) => l.status === "warning").length
  const errors = lines.filter((l) => l.status === "error").length
  const conflicts = lines.filter((l) => l.status === "conflict").length
  return { valid, warnings, errors, conflicts, total: lines.length }
}

export function getProblemStats(problems: Problem[]) {
  const errors = problems.filter((p) => p.type === "error").length
  const warnings = problems.filter((p) => p.type === "warning").length
  const conflicts = problems.filter((p) => p.type === "conflict").length
  return { errors, warnings, conflicts }
}
