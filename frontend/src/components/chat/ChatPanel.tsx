/**
 * ChatPanel — floating expandable AI chat panel.
 *
 * Positioned at bottom-right of the viewport, above the edit dialog.
 * Expands upward when opened via the toggle button (in StatusBar or
 * a dedicated FAB). Always accessible regardless of modal dialogs.
 *
 * Features:
 * - Streaming message display
 * - Tool call visibility
 * - New session button
 * - Auto-scroll to bottom
 * - Responsive sizing
 */

import { useEffect, useRef } from "react";
import { useChatStore } from "@/stores/chat-store";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { Button } from "@/components/ui/button";
import {
  Bot,
  X,
  RotateCcw,
  Loader2,
  MessageSquare,
  WifiOff,
  Wrench,
} from "lucide-react";
import { cn } from "@/lib/utils";

export function ChatPanel() {
  const {
    isOpen,
    available,
    connected,
    messages,
    streamingContent,
    isGenerating,
    activeToolCalls,
    closePanel,
    sendMessage,
    newSession,
    connect,
  } = useChatStore();

  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new content
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, streamingContent, activeToolCalls]);

  // Try to connect if panel is open but not connected
  useEffect(() => {
    if (isOpen && !connected) {
      connect();
    }
  }, [isOpen, connected, connect]);

  if (!isOpen) return null;

  return (
    <div
      className={cn(
        "fixed bottom-10 right-4 z-[100]",
        "flex flex-col",
        "w-[400px] max-w-[calc(100vw-2rem)]",
        "h-[500px] max-h-[calc(100vh-6rem)]",
        "rounded-lg border bg-background shadow-xl",
        "animate-in slide-in-from-bottom-4 fade-in duration-200",
      )}
    >
      {/* Header */}
      <ChatHeader
        onClose={closePanel}
        onNewSession={newSession}
        isGenerating={isGenerating}
      />

      {/* Messages area */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {available === false ? (
          <UnavailableState />
        ) : messages.length === 0 && !streamingContent ? (
          <EmptyState />
        ) : (
          <div className="flex flex-col pb-2">
            {messages.map((msg) => (
              <ChatMessage key={msg.id} message={msg} />
            ))}

            {/* Active tool calls (during generation) */}
            {activeToolCalls.length > 0 && (
              <div className="px-3 py-1">
                {activeToolCalls.map((tc, i) => (
                  <div
                    key={i}
                    className="flex items-center gap-1.5 text-xs text-muted-foreground"
                  >
                    <Wrench className="h-3 w-3 animate-spin" />
                    <span className="font-mono">{tc.name}</span>
                    {tc.result ? (
                      <span className="text-[var(--status-ok)]">✓</span>
                    ) : (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Streaming content (not yet finalized) */}
            {streamingContent && (
              <div className="flex gap-2 px-3 py-2">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <Bot className="h-3.5 w-3.5" />
                </div>
                <div className="rounded-lg bg-muted px-3 py-2 text-sm leading-relaxed">
                  <span className="whitespace-pre-wrap break-words">
                    {streamingContent}
                  </span>
                  <span className="ml-0.5 inline-block h-4 w-1 animate-pulse bg-foreground/50" />
                </div>
              </div>
            )}

            {/* Generating indicator (no streaming yet) */}
            {isGenerating && !streamingContent && activeToolCalls.length === 0 && (
              <div className="flex gap-2 px-3 py-2">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <Bot className="h-3.5 w-3.5" />
                </div>
                <div className="flex items-center gap-1.5 rounded-lg bg-muted px-3 py-2 text-sm text-muted-foreground">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  Thinking…
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        disabled={isGenerating || available === false}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Sub-components                                                      */
/* ------------------------------------------------------------------ */

function ChatHeader({
  onClose,
  onNewSession,
  isGenerating,
}: {
  onClose: () => void;
  onNewSession: () => void;
  isGenerating: boolean;
}) {
  return (
    <div className="flex items-center justify-between border-b px-3 py-2">
      <div className="flex items-center gap-2">
        <Bot className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium">AI Assistant</span>
        {isGenerating && (
          <Loader2 className="h-3.5 w-3.5 animate-spin text-muted-foreground" />
        )}
      </div>
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={onNewSession}
          title="New session"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={onClose}
          title="Close chat"
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
        <MessageSquare className="h-6 w-6 text-primary" />
      </div>
      <div>
        <p className="text-sm font-medium">Lotus-Ref AI Assistant</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Ask about your document, search the netlist, or request edits.
          The assistant can read and modify your loaded documents.
        </p>
      </div>
      <div className="mt-2 space-y-1 text-xs text-muted-foreground">
        <p className="font-medium text-foreground/70">Try asking:</p>
        <p>"Show me all lines with errors"</p>
        <p>"Does net VDD exist in the netlist?"</p>
        <p>"Comment out line 5"</p>
      </div>
    </div>
  );
}

function UnavailableState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10">
        <WifiOff className="h-6 w-6 text-destructive" />
      </div>
      <div>
        <p className="text-sm font-medium">Chat Unavailable</p>
        <p className="mt-1 text-xs text-muted-foreground">
          The AI assistant requires the GitHub Copilot CLI to be installed.
          Install it and restart the application.
        </p>
      </div>
    </div>
  );
}
