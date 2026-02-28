/**
 * ChatToggle — floating button to open/close the chat panel.
 *
 * Positioned at the bottom-right corner, above the status bar.
 * Shows a pulsing dot when there are unread messages.
 */

import { useChatStore } from "@/stores/chat-store";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { MessageSquare } from "lucide-react";
import { cn } from "@/lib/utils";

export function ChatToggle() {
  const { isOpen, togglePanel, isGenerating } = useChatStore();

  if (isOpen) return null; // hide toggle when panel is open

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="default"
          size="icon"
          onClick={togglePanel}
          className={cn(
            "fixed bottom-10 right-4 z-[99]",
            "h-10 w-10 rounded-full shadow-lg",
            "transition-transform hover:scale-105",
          )}
        >
          <MessageSquare className="h-5 w-5" />
          {isGenerating && (
            <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-[var(--status-warning)] animate-pulse" />
          )}
        </Button>
      </TooltipTrigger>
      <TooltipContent side="left">
        <p>AI Assistant</p>
      </TooltipContent>
    </Tooltip>
  );
}
