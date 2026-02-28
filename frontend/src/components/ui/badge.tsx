import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-md border px-1.5 py-0.5 text-2xs font-semibold uppercase transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground",
        outline: "text-foreground",
        /* ---- Status variants ---- */
        ok: "border-status-ok/30 bg-status-ok/15 text-status-ok",
        warning:
          "border-status-warning/30 bg-status-warning/15 text-status-warning",
        error: "border-status-error/30 bg-status-error/15 text-status-error",
        comment:
          "border-muted-foreground/30 bg-muted-foreground/10 text-muted-foreground",
        empty: "border-muted/50 bg-muted/30 text-muted-foreground/60",
        conflict:
          "border-purple-500/30 bg-purple-500/15 text-purple-400",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
