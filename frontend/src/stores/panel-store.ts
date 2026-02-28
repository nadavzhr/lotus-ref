import { create } from "zustand";

export type BottomTab = "problems" | "conflicts" | "logs" | "terminal";

interface PanelState {
  bottomOpen: boolean;
  bottomHeight: number; // pixels
  activeTab: BottomTab;
  toggleBottom: () => void;
  setBottomHeight: (h: number) => void;
  setActiveTab: (tab: BottomTab) => void;
  /** Opens the panel (if closed) and switches to the given tab. */
  openTab: (tab: BottomTab) => void;
}

const MIN_HEIGHT = 80;
const MAX_HEIGHT = 700;

export const usePanelStore = create<PanelState>((set) => ({
  bottomOpen: false,
  bottomHeight: 220,
  activeTab: "problems",
  toggleBottom: () => set((s) => ({ bottomOpen: !s.bottomOpen })),
  setBottomHeight: (h) =>
    set({ bottomHeight: Math.max(MIN_HEIGHT, Math.min(h, MAX_HEIGHT)) }),
  setActiveTab: (tab) => set({ activeTab: tab }),
  openTab: (tab) => set({ activeTab: tab, bottomOpen: true }),
}));
