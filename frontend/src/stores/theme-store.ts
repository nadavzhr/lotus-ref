import { create } from "zustand";

export type Theme = "light" | "dark" | "system";

interface ThemeState {
  theme: Theme;
  resolvedTheme: "light" | "dark";
  setTheme: (theme: Theme) => void;
}

function resolveTheme(theme: Theme): "light" | "dark" {
  if (theme === "system") {
    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  }
  return theme;
}

function getInitialTheme(): Theme {
  const stored = localStorage.getItem("lotus-theme") as Theme | null;
  if (stored === "light" || stored === "dark" || stored === "system") {
    return stored;
  }
  return "system";
}

const initial = getInitialTheme();

export const useThemeStore = create<ThemeState>((set) => ({
  theme: initial,
  resolvedTheme: resolveTheme(initial),
  setTheme: (theme: Theme) => {
    localStorage.setItem("lotus-theme", theme);
    const resolved = resolveTheme(theme);
    // Apply class to <html>
    const root = document.documentElement;
    root.classList.remove("light", "dark");
    root.classList.add(resolved);
    set({ theme, resolvedTheme: resolved });
  },
}));
