import { useState, useCallback, type RefObject } from "react"

export function useSplitter(
  initial: number,
  direction: "horizontal" | "vertical",
  containerRef: RefObject<HTMLDivElement | null>,
  min = 15,
  max = 85,
) {
  const [pct, setPct] = useState(initial)

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      let isDragging = true

      const onMouseMove = (ev: MouseEvent) => {
        if (!isDragging || !containerRef.current) return
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
        isDragging = false
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
    [direction, min, max, containerRef],
  )

  return { pct, onMouseDown }
}
