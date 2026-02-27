import { useEffect } from "react"
import { useAppStore } from "@/store/app-store"

/**
 * Initialises the theme from localStorage / system preference on mount
 * and listens for system theme changes when in "system" mode.
 */
export function useThemeInit() {
  const setTheme = useAppStore((s) => s.setTheme)

  useEffect(() => {
    const stored = localStorage.getItem("theme") as
      | "light"
      | "dark"
      | "system"
      | null

    // Apply the stored theme or default to system
    setTheme(stored ?? "system")

    // Listen for OS preference changes
    const mq = window.matchMedia("(prefers-color-scheme: dark)")
    const handler = () => {
      const current = useAppStore.getState().theme
      if (current === "system") {
        document.documentElement.classList.toggle("dark", mq.matches)
      }
    }
    mq.addEventListener("change", handler)
    return () => mq.removeEventListener("change", handler)
  }, [setTheme])
}
