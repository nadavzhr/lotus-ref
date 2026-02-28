/**
 * EditDialog — modal popup hosting the AF or Mutex edit form.
 *
 * Uses a macOS-style zoom-from-origin animation: the dialog scales
 * outward from the clicked row and shrinks back on close.
 */

import { useRef } from "react";
import { useEditStore } from "@/stores/edit-store";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { AfEditForm, AfEditFormFooter } from "./AfEditForm";
import { MutexEditForm, MutexEditFormFooter } from "./MutexEditForm";

export function EditDialog() {
  const isOpen = useEditStore((s) => s.isOpen);
  const docType = useEditStore((s) => s.docType);
  const position = useEditStore((s) => s.position);
  const originY = useEditStore((s) => s.originY);
  const closeEdit = useEditStore((s) => s.closeEdit);

  // Remember the last values so the close animation still renders the
  // correct title, description, form, and footer while fading out.
  // (closeEdit() immediately resets the store to null.)
  const lastDocTypeRef = useRef<"af" | "mutex" | null>(null);
  const lastPositionRef = useRef<number | null>(null);
  const lastOriginRef = useRef<number | null>(null);

  if (docType != null) lastDocTypeRef.current = docType;
  if (position != null) lastPositionRef.current = position;
  if (originY != null) lastOriginRef.current = originY;

  const effectiveDocType = docType ?? lastDocTypeRef.current;
  const effectivePosition = position ?? lastPositionRef.current;
  const effectiveOrigin = isOpen ? originY : lastOriginRef.current;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && closeEdit()}>
      <DialogContent
        size={effectiveDocType === "mutex" ? "xl" : "lg"}
        originY={effectiveOrigin}
      >
        <DialogHeader>
          <DialogTitle>
            {effectiveDocType === "af" ? "Edit AF Line" : "Edit Mutex Line"}
          </DialogTitle>
          <DialogDescription>
            Line {effectivePosition !== null ? effectivePosition + 1 : "?"} ·{" "}
            {effectiveDocType?.toUpperCase() ?? "Unknown"} configuration
          </DialogDescription>
        </DialogHeader>

        {/* Form body */}
        <div className="max-h-[70vh] overflow-y-auto px-6 py-2">
          {effectiveDocType === "af" && <AfEditForm />}
          {effectiveDocType === "mutex" && <MutexEditForm />}
        </div>

        {/* Footer with Save / Cancel */}
        <DialogFooter>
          {effectiveDocType === "af" && <AfEditFormFooter />}
          {effectiveDocType === "mutex" && <MutexEditFormFooter />}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
