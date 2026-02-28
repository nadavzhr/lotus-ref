import { create } from "zustand";

interface PanelState {
  bottomOpen: boolean;
  bottomHeight: number; // pixels
  toggleBottom: () => void;
  setBottomHeight: (h: number) => void;
}

export const usePanelStore = create<PanelState>((set) => ({
  bottomOpen: false,
  bottomHeight: 200,
  toggleBottom: () => set((s) => ({ bottomOpen: !s.bottomOpen })),
  setBottomHeight: (h) => set({ bottomHeight: h }),
}));
