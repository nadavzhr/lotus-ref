import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { MoreHorizontal } from "lucide-react";

interface LineOverflowMenuProps {
  position: number;
  totalLines: number;
  onDelete: (pos: number) => void;
  onInsertBelow: (pos: number) => void;
  onToggleComment: (pos: number) => void;
  onSwapUp: (pos: number) => void;
  onSwapDown: (pos: number) => void;
}

export function LineOverflowMenu({
  position,
  totalLines,
  onDelete,
  onInsertBelow,
  onToggleComment,
  onSwapUp,
  onSwapDown,
}: LineOverflowMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          className="h-6 w-6"
          onClick={(e) => e.stopPropagation()}
        >
          <MoreHorizontal className="h-3.5 w-3.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        <DropdownMenuItem
          onClick={(e) => {
            e.stopPropagation();
            onInsertBelow(position);
          }}
        >
          Insert line below
        </DropdownMenuItem>

        <DropdownMenuItem
          onClick={(e) => {
            e.stopPropagation();
            onToggleComment(position);
          }}
        >
          Toggle comment
          <DropdownMenuShortcut>Ctrl+/</DropdownMenuShortcut>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          disabled={position <= 0}
          onClick={(e) => {
            e.stopPropagation();
            onSwapUp(position);
          }}
        >
          Move up
          <DropdownMenuShortcut>Alt+↑</DropdownMenuShortcut>
        </DropdownMenuItem>

        <DropdownMenuItem
          disabled={position >= totalLines - 1}
          onClick={(e) => {
            e.stopPropagation();
            onSwapDown(position);
          }}
        >
          Move down
          <DropdownMenuShortcut>Alt+↓</DropdownMenuShortcut>
        </DropdownMenuItem>

        <DropdownMenuSeparator />

        <DropdownMenuItem
          className="text-destructive focus:text-destructive"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(position);
          }}
        >
          Delete line
          <DropdownMenuShortcut>Del</DropdownMenuShortcut>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
