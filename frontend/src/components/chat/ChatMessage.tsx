/**
 * ChatMessage — renders a single message in the chat panel.
 *
 * Supports user, assistant, and system messages.
 * Shows tool call details when present (collapsed by default).
 */

import { useState } from "react";
import type { ChatMessage as ChatMessageType, ToolCallInfo } from "@/stores/chat-store";
import { cn } from "@/lib/utils";
import {
  ChevronDown,
  ChevronRight,
  User,
  Bot,
  AlertCircle,
  Wrench,
} from "lucide-react";

interface Props {
  message: ChatMessageType;
}

export function ChatMessage({ message }: Props) {
  return (
    <div
      className={cn(
        "flex gap-2 px-3 py-2",
        message.role === "user" && "flex-row-reverse",
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex h-6 w-6 shrink-0 items-center justify-center rounded-full",
          message.role === "user"
            ? "bg-primary text-primary-foreground"
            : message.role === "system"
              ? "bg-destructive/20 text-destructive"
              : "bg-muted text-muted-foreground",
        )}
      >
        {message.role === "user" ? (
          <User className="h-3.5 w-3.5" />
        ) : message.role === "system" ? (
          <AlertCircle className="h-3.5 w-3.5" />
        ) : (
          <Bot className="h-3.5 w-3.5" />
        )}
      </div>

      {/* Content */}
      <div
        className={cn(
          "flex min-w-0 max-w-[85%] flex-col gap-1",
          message.role === "user" && "items-end",
        )}
      >
        <div
          className={cn(
            "rounded-lg px-3 py-2 text-sm leading-relaxed",
            message.role === "user"
              ? "bg-primary text-primary-foreground"
              : message.role === "system"
                ? "bg-destructive/10 text-destructive"
                : "bg-muted text-foreground",
          )}
        >
          <MessageContent content={message.content} />
        </div>

        {/* Tool calls */}
        {message.toolCalls && message.toolCalls.length > 0 && (
          <ToolCallsSection toolCalls={message.toolCalls} />
        )}
      </div>
    </div>
  );
}

/** Renders message content with basic markdown-like formatting. */
function MessageContent({ content }: { content: string }) {
  // Simple rendering — split by code blocks and paragraphs
  const parts = content.split(/(```[\s\S]*?```)/g);

  return (
    <div className="whitespace-pre-wrap break-words">
      {parts.map((part, i) => {
        if (part.startsWith("```") && part.endsWith("```")) {
          const inner = part.slice(3, -3).replace(/^\w*\n/, ""); // strip language tag
          return (
            <pre
              key={i}
              className="my-1 overflow-x-auto rounded bg-background/50 px-2 py-1 font-mono text-xs"
            >
              {inner}
            </pre>
          );
        }
        // Render inline code
        const segments = part.split(/(`[^`]+`)/g);
        return (
          <span key={i}>
            {segments.map((seg, j) => {
              if (seg.startsWith("`") && seg.endsWith("`")) {
                return (
                  <code
                    key={j}
                    className="rounded bg-background/50 px-1 py-0.5 font-mono text-xs"
                  >
                    {seg.slice(1, -1)}
                  </code>
                );
              }
              // Bold
              const boldParts = seg.split(/(\*\*[^*]+\*\*)/g);
              return (
                <span key={j}>
                  {boldParts.map((bp, k) => {
                    if (bp.startsWith("**") && bp.endsWith("**")) {
                      return <strong key={k}>{bp.slice(2, -2)}</strong>;
                    }
                    return <span key={k}>{bp}</span>;
                  })}
                </span>
              );
            })}
          </span>
        );
      })}
    </div>
  );
}

/** Collapsible section showing tool calls made by the assistant. */
function ToolCallsSection({ toolCalls }: { toolCalls: ToolCallInfo[] }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="w-full">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        <Wrench className="h-3 w-3" />
        <span>
          {toolCalls.length} tool call{toolCalls.length !== 1 ? "s" : ""}
        </span>
      </button>

      {expanded && (
        <div className="mt-1 space-y-1">
          {toolCalls.map((tc, i) => (
            <div
              key={i}
              className="rounded border bg-muted/30 px-2 py-1 text-xs"
            >
              <div className="font-medium text-muted-foreground">
                {tc.name}
                {tc.args && Object.keys(tc.args).length > 0 && (
                  <span className="ml-1 font-normal opacity-70">
                    ({Object.entries(tc.args)
                      .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
                      .join(", ")})
                  </span>
                )}
              </div>
              {tc.result && (
                <pre className="mt-1 max-h-24 overflow-auto whitespace-pre-wrap break-all font-mono opacity-70">
                  {tc.result.length > 500
                    ? tc.result.slice(0, 500) + "…"
                    : tc.result}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
