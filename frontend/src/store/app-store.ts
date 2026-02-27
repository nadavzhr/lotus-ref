import { create } from "zustand"
import type { DocumentSummary, Problem, DocumentLine } from "@/types/api"

interface AppState {
  /** Currently loaded document summary */
  document: DocumentSummary | null
  setDocument: (doc: DocumentSummary | null) => void

  /** Selected line positions */
  selectedLines: Set<number>
  selectLine: (pos: number, multi?: boolean) => void
  clearSelection: () => void

  /** Bottom panel visibility */
  bottomPanelOpen: boolean
  toggleBottomPanel: () => void
  setBottomPanelOpen: (open: boolean) => void

  /** Active tab in bottom panel */
  bottomPanelTab: string
  setBottomPanelTab: (tab: string) => void

  /** Line to scroll to (set by problems panel click) */
  scrollToLine: number | null
  setScrollToLine: (pos: number | null) => void

  /** Edit dialog state */
  editingLine: number | null
  setEditingLine: (pos: number | null) => void

  /** Theme */
  theme: "light" | "dark" | "system"
  setTheme: (theme: "light" | "dark" | "system") => void

  /** Connection status */
  connected: boolean
  setConnected: (c: boolean) => void

  /** Problems derived from lines */
  problems: Problem[]
  updateProblemsFromLines: (lines: DocumentLine[]) => void
}

export const useAppStore = create<AppState>((set) => ({
  document: null,
  setDocument: (doc) => set({ document: doc }),

  selectedLines: new Set<number>(),
  selectLine: (pos, multi = false) =>
    set((state) => {
      if (multi) {
        const next = new Set(state.selectedLines)
        if (next.has(pos)) {
          next.delete(pos)
        } else {
          next.add(pos)
        }
        return { selectedLines: next }
      }
      return { selectedLines: new Set([pos]) }
    }),
  clearSelection: () => set({ selectedLines: new Set() }),

  bottomPanelOpen: false,
  toggleBottomPanel: () =>
    set((state) => ({ bottomPanelOpen: !state.bottomPanelOpen })),
  setBottomPanelOpen: (open) => set({ bottomPanelOpen: open }),

  bottomPanelTab: "problems",
  setBottomPanelTab: (tab) => set({ bottomPanelTab: tab }),

  scrollToLine: null,
  setScrollToLine: (pos) => set({ scrollToLine: pos }),

  editingLine: null,
  setEditingLine: (pos) => set({ editingLine: pos }),

  theme: "system",
  setTheme: (theme) => {
    set({ theme })
    const root = document.documentElement
    if (theme === "system") {
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)"
      ).matches
      root.classList.toggle("dark", prefersDark)
    } else {
      root.classList.toggle("dark", theme === "dark")
    }
    localStorage.setItem("theme", theme)
  },

  connected: true,
  setConnected: (c) => set({ connected: c }),

  problems: [],
  updateProblemsFromLines: (lines) => {
    const problems: Problem[] = []
    for (const line of lines) {
      for (const msg of line.errors) {
        problems.push({ position: line.position, severity: "error", message: msg })
      }
      for (const msg of line.warnings) {
        problems.push({ position: line.position, severity: "warning", message: msg })
      }
      if (line.status === "conflict") {
        const nets =
          line.conflict_info?.shared_nets?.join(", ") ?? "unknown nets"
        problems.push({
          position: line.position,
          severity: "conflict",
          message: `Conflict with lines ${line.conflict_info?.conflicting_positions?.join(", ") ?? "?"}: ${nets}`,
        })
      }
    }
    set({ problems })
  },
}))
