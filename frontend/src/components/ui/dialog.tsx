/**
 * Dialog — modal with macOS-style zoom-from-origin animation.
 *
 * Custom keyframes (in globals.css) bake the centering translate into
 * the animation so we can freely set `transform-origin` to the clicked
 * row's direction.  The dialog scales from 0.85 → 1.0 out of the
 * source point for a satisfying "Quick Look" feel.
 */

import * as React from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const Dialog = DialogPrimitive.Root;
const DialogTrigger = DialogPrimitive.Trigger;
const DialogClose = DialogPrimitive.Close;
const DialogPortal = DialogPrimitive.Portal;

const DialogOverlay = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Overlay>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Overlay
    ref={ref}
    className={cn(
      "fixed inset-0 z-50 bg-black/50",
      "data-[state=open]:[animation:overlay-enter_250ms_ease-out_forwards]",
      "data-[state=closed]:[animation:overlay-exit_180ms_ease-in_forwards]",
      className,
    )}
    {...props}
  />
));
DialogOverlay.displayName = DialogPrimitive.Overlay.displayName;

const DialogContent = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Content> & {
    /** Width variant */
    size?: "default" | "lg" | "xl";
    /** Viewport-Y of the element the dialog should zoom from */
    originY?: number | null;
  }
>(({ className, children, size = "default", originY, style, ...props }, ref) => {
  // Compute transform-origin so the scale emanates from the source row.
  // The dialog is centered at viewport-center via left:50% top:50% +
  // translate(-50%,-50%) in the keyframes, so the offset relative to
  // the dialog's own center is (clickY - viewportCenterY).
  const computedOrigin = React.useMemo(() => {
    if (originY == null) return "center center";
    const offsetY = originY - window.innerHeight / 2;
    // Clamp to ±300px so the origin doesn't go too extreme
    const clamped = Math.max(-300, Math.min(300, offsetY));
    return `50% calc(50% + ${clamped}px)`;
  }, [originY]);

  return (
    <DialogPortal>
      <DialogOverlay />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(
          "fixed left-[50%] top-[50%] z-50 grid w-full gap-4 border bg-background shadow-lg",
          "rounded-lg p-0",
          "data-[state=open]:[animation:dialog-enter_280ms_cubic-bezier(0.32,0.72,0,1)_forwards]",
          "data-[state=closed]:[animation:dialog-exit_200ms_cubic-bezier(0.4,0,1,1)_forwards]",
          size === "default" && "max-w-lg",
          size === "lg" && "max-w-2xl",
          size === "xl" && "max-w-4xl",
          className,
        )}
        style={{ ...style, transformOrigin: computedOrigin }}
        {...props}
      >
        {children}
        <DialogPrimitive.Close className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none">
          <X className="h-4 w-4" />
          <span className="sr-only">Close</span>
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </DialogPortal>
  );
});
DialogContent.displayName = DialogPrimitive.Content.displayName;

function DialogHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex flex-col space-y-1.5 border-b px-6 py-4",
        className,
      )}
      {...props}
    />
  );
}

function DialogFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-center justify-end gap-2 border-t px-6 py-3",
        className,
      )}
      {...props}
    />
  );
}

const DialogTitle = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Title>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Title
    ref={ref}
    className={cn(
      "text-lg font-semibold leading-none tracking-tight",
      className,
    )}
    {...props}
  />
));
DialogTitle.displayName = DialogPrimitive.Title.displayName;

const DialogDescription = React.forwardRef<
  React.ElementRef<typeof DialogPrimitive.Description>,
  React.ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(({ className, ...props }, ref) => (
  <DialogPrimitive.Description
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
));
DialogDescription.displayName = DialogPrimitive.Description.displayName;

export {
  Dialog,
  DialogTrigger,
  DialogClose,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
};
