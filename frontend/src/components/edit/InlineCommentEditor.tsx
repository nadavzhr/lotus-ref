/**
 * InlineCommentEditor — small inline text input that appears in-place
 * when editing a comment line.
 *
 * Replaces the raw_text display within the LineRow. Commits on Enter
 * or blur, cancels on Escape.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { useDocumentStore } from "@/stores/document-store";
import * as api from "@/api/documents";

interface InlineCommentEditorProps {
  docId: string;
  position: number;
  initialText: string;
  onClose: () => void;
}

export function InlineCommentEditor({
  docId,
  position,
  initialText,
  onClose,
}: InlineCommentEditorProps) {
  const [text, setText] = useState(initialText);
  const [saving, setSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const refreshLines = useDocumentStore((s) => s.refreshLines);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const handleSave = useCallback(async () => {
    if (text === initialText) {
      onClose();
      return;
    }
    setSaving(true);
    try {
      await api.editCommentText(docId, position, text);
      await refreshLines(docId);
      onClose();
    } catch {
      // Stay open on error so user can retry
      setSaving(false);
    }
  }, [docId, position, text, initialText, refreshLines, onClose]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      e.stopPropagation(); // Prevent document-level shortcuts
      if (e.key === "Enter") {
        e.preventDefault();
        handleSave();
      }
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    },
    [handleSave, onClose],
  );

  return (
    <input
      ref={inputRef}
      type="text"
      value={text}
      onChange={(e) => setText(e.target.value)}
      onKeyDown={handleKeyDown}
      onBlur={handleSave}
      disabled={saving}
      className="w-full rounded border border-ring bg-background px-2 py-0.5 font-mono text-xs leading-relaxed outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
      aria-label="Edit comment text"
    />
  );
}
