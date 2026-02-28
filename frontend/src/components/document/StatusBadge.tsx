import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

/* Maps status → Tailwind bg color for the dot */
const dotColor: Record<string, string> = {
  ok: "bg-status-ok",
  warning: "bg-status-warning",
  error: "bg-status-error",
  comment: "bg-muted-foreground/60",
  empty: "bg-muted-foreground/25",
  conflict: "bg-purple-400",
};

interface StatusBadgeProps {
  status: string;
  className?: string;
}

/**
 * StatusBadge — small colored circle indicating line status.
 * Tooltip shows the status text on hover.
 */
export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-block h-2.5 w-2.5 shrink-0 rounded-full",
            dotColor[status] ?? "bg-muted-foreground/30",
            className,
          )}
        />
      </TooltipTrigger>
      <TooltipContent side="top" className="text-2xs">
        {status}
      </TooltipContent>
    </Tooltip>
  );
}

/**
 * ConflictBadge — small purple circle for conflict status.
 */
export function ConflictBadge({ className }: { className?: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span
          className={cn(
            "inline-block h-2.5 w-2.5 shrink-0 rounded-full bg-purple-400",
            className,
          )}
        />
      </TooltipTrigger>
      <TooltipContent side="top" className="text-2xs">
        conflict
      </TooltipContent>
    </Tooltip>
  );
}
