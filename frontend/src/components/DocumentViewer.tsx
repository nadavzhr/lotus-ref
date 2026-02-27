import { useCallback, useEffect, useRef } from "react"
import { useVirtualizer } from "@tanstack/react-virtual"
import { useAppStore } from "@/store/app-store"
import { DocumentLineRow } from "@/components/DocumentLine"
import type { DocumentLine } from "@/types/api"

interface DocumentViewerProps {
  lines: DocumentLine[]
}

export function DocumentViewer({ lines }: DocumentViewerProps) {
  const parentRef = useRef<HTMLDivElement>(null)
  const scrollToLine = useAppStore((s) => s.scrollToLine)
  const setScrollToLine = useAppStore((s) => s.setScrollToLine)

  const virtualizer = useVirtualizer({
    count: lines.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 32,
    overscan: 20,
  })

  // Scroll to line when requested (e.g. from problems panel)
  useEffect(() => {
    if (scrollToLine !== null) {
      const idx = lines.findIndex((l) => l.position === scrollToLine)
      if (idx >= 0) {
        virtualizer.scrollToIndex(idx, { align: "center" })
      }
      setScrollToLine(null)
    }
  }, [scrollToLine, lines, virtualizer, setScrollToLine])

  const selectedLines = useAppStore((s) => s.selectedLines)
  const selectLine = useAppStore((s) => s.selectLine)
  const setEditingLine = useAppStore((s) => s.setEditingLine)

  const handleLineClick = useCallback(
    (pos: number, e: React.MouseEvent) => {
      selectLine(pos, e.metaKey || e.ctrlKey)
    },
    [selectLine]
  )

  const handleEdit = useCallback(
    (pos: number) => {
      setEditingLine(pos)
    },
    [setEditingLine]
  )

  return (
    <div
      ref={parentRef}
      className="flex-1 overflow-auto"
    >
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const line = lines[virtualItem.index]
          return (
            <div
              key={virtualItem.key}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: `${virtualItem.size}px`,
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              <DocumentLineRow
                line={line}
                isSelected={selectedLines.has(line.position)}
                onClick={handleLineClick}
                onEdit={handleEdit}
              />
            </div>
          )
        })}
      </div>
    </div>
  )
}
