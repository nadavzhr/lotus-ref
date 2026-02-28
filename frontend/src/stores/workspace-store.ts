import { create } from "zustand";

interface WorkspaceState {
  ward: string;
  cell: string;
  setWard: (ward: string) => void;
  setCell: (cell: string) => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  ward: import.meta.env.VITE_WARD ?? "",
  cell: import.meta.env.VITE_CELL ?? "",
  setWard: (ward) => set({ ward }),
  setCell: (cell) => set({ cell }),
}));
