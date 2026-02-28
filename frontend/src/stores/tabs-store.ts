import { create } from "zustand";

export interface Tab {
  id: string;
  label: string;
  docType: "af" | "mutex";
  filePath: string;
}

interface TabsState {
  tabs: Tab[];
  activeTabId: string | null;
  openTab: (tab: Tab) => void;
  closeTab: (id: string) => void;
  setActive: (id: string) => void;
}

export const useTabsStore = create<TabsState>((set, get) => ({
  tabs: [],
  activeTabId: null,

  openTab: (tab) => {
    const existing = get().tabs.find((t) => t.id === tab.id);
    if (existing) {
      set({ activeTabId: tab.id });
    } else {
      set((s) => ({
        tabs: [...s.tabs, tab],
        activeTabId: tab.id,
      }));
    }
  },

  closeTab: (id) => {
    set((s) => {
      const tabs = s.tabs.filter((t) => t.id !== id);
      let activeTabId = s.activeTabId;
      if (activeTabId === id) {
        // Activate the nearest remaining tab
        const closedIndex = s.tabs.findIndex((t) => t.id === id);
        activeTabId =
          tabs[Math.min(closedIndex, tabs.length - 1)]?.id ?? null;
      }
      return { tabs, activeTabId };
    });
  },

  setActive: (id) => set({ activeTabId: id }),
}));
