import { useState, useRef, useCallback } from "react"

export function useSplitter(
  initial: number,
  direction: "horizontal" | "vertical",
  min = 15,
  max = 85,
) {
  const [pct, setPct] = useState(initial)
  const dragging = useRef(false)
  const containerRef = useRef<HTMLDivElement>(null)

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      dragging.current = true

      const onMouseMove = (ev: MouseEvent) => {
        if (!dragging.current || !containerRef.current) return
        const rect = containerRef.current.getBoundingClientRect()
        let ratio: number
        if (direction === "horizontal") {
          ratio = ((ev.clientX - rect.left) / rect.width) * 100
        } else {
          ratio = ((ev.clientY - rect.top) / rect.height) * 100
        }
        setPct(Math.min(max, Math.max(min, ratio)))
      }

      const onMouseUp = () => {
        dragging.current = false
        document.removeEventListener("mousemove", onMouseMove)
        document.removeEventListener("mouseup", onMouseUp)
        document.body.style.cursor = ""
        document.body.style.userSelect = ""
      }

      document.body.style.cursor = direction === "horizontal" ? "col-resize" : "row-resize"
      document.body.style.userSelect = "none"
      document.addEventListener("mousemove", onMouseMove)
      document.addEventListener("mouseup", onMouseUp)
    },
    [direction, min, max],
  )

  return { pct, containerRef, onMouseDown }
}
