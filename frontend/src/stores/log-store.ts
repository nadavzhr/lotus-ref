import { create } from "zustand";

export type LogLevel = "info" | "warn" | "error";

export interface LogEntry {
  id: string;
  level: LogLevel;
  message: string;
  timestamp: Date;
}

interface LogState {
  entries: LogEntry[];
  push: (level: LogLevel, message: string) => void;
  clear: () => void;
}

let _seq = 0;

export const useLogStore = create<LogState>((set) => ({
  entries: [],
  push: (level, message) =>
    set((s) => ({
      entries: [
        ...s.entries,
        { id: `log-${++_seq}`, level, message, timestamp: new Date() },
      ],
    })),
  clear: () => set({ entries: [] }),
}));
