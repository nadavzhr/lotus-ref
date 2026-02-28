import { useEffect } from "react";
import { useThemeStore } from "@/stores/theme-store";

/**
 * ThemeProvider — applies the resolved theme class to <html> and
 * listens for system preference changes when theme === "system".
 * Renders children without wrapping DOM.
 */
export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const theme = useThemeStore((s) => s.theme);
  const setTheme = useThemeStore((s) => s.setTheme);

  useEffect(() => {
    // Apply immediately on mount
    setTheme(theme);

    if (theme !== "system") return;

    // Listen for OS preference changes
    const mql = window.matchMedia("(prefers-color-scheme: dark)");
    const handler = () => setTheme("system"); // re-resolve
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [theme, setTheme]);

  return <>{children}</>;
}
