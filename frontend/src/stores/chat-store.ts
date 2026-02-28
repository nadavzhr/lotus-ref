/**
 * Chat Store — manages the state of the AI chatbot panel.
 *
 * Handles WebSocket connection lifecycle, message history, streaming state,
 * and coordinates with the ChatConnection API client.
 */

import { create } from "zustand";
import { ChatConnection, getChatStatus, type ChatEvent } from "@/api/chat";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

export type MessageRole = "user" | "assistant" | "system";

export interface ToolCallInfo {
  name: string;
  args: Record<string, unknown>;
  result?: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: number;
  /** Tool calls made during this assistant turn */
  toolCalls?: ToolCallInfo[];
}

/* ------------------------------------------------------------------ */
/* Store                                                               */
/* ------------------------------------------------------------------ */

interface ChatStoreState {
  /** Is the chat panel open? */
  isOpen: boolean;
  /** Is the chat service available on the backend? */
  available: boolean | null;
  /** Checked availability? */
  checkedStatus: boolean;
  /** WebSocket connected? */
  connected: boolean;
  /** Current session ID */
  sessionId: string | null;
  /** Chat message history */
  messages: ChatMessage[];
  /** Currently streaming assistant content (accumulated delta) */
  streamingContent: string;
  /** Is the assistant currently generating? */
  isGenerating: boolean;
  /** Active tool calls during generation */
  activeToolCalls: ToolCallInfo[];

  /** Toggle the chat panel open/closed */
  togglePanel: () => void;
  /** Open the panel */
  openPanel: () => void;
  /** Close the panel */
  closePanel: () => void;
  /** Check backend availability */
  checkStatus: () => Promise<void>;
  /** Connect WebSocket */
  connect: () => void;
  /** Disconnect WebSocket */
  disconnect: () => void;
  /** Send a user message */
  sendMessage: (content: string) => void;
  /** Start a new session (clear history) */
  newSession: () => void;
}

let connection: ChatConnection | null = null;
let msgIdCounter = 0;

// Track if a 'message' event was received for the current turn
let assistantMessageReceived = false;

function nextId(): string {
  return `msg-${++msgIdCounter}-${Date.now()}`;
}

export const useChatStore = create<ChatStoreState>((set, get) => ({
  isOpen: false,
  available: null,
  checkedStatus: false,
  connected: false,
  sessionId: null,
  messages: [],
  streamingContent: "",
  isGenerating: false,
  activeToolCalls: [],

  togglePanel: () => {
    const state = get();
    if (!state.isOpen) {
      get().openPanel();
    } else {
      set({ isOpen: false });
    }
  },

  openPanel: () => {
    const state = get();
    set({ isOpen: true });
    // Check status and connect if needed
    if (!state.checkedStatus) {
      get().checkStatus();
    }
    if (!state.connected && state.available !== false) {
      get().connect();
    }
  },

  closePanel: () => {
    set({ isOpen: false });
  },

  checkStatus: async () => {
    try {
      const status = await getChatStatus();
      set({ available: status.available, checkedStatus: true });
    } catch {
      set({ available: false, checkedStatus: true });
    }
  },

  connect: () => {
    if (connection) return;

    connection = new ChatConnection(async (event: ChatEvent) => {
      switch (event.type) {
                        case "session_created":
                          assistantMessageReceived = false;
                          set({ sessionId: event.session_id ?? null, connected: true });
                          break;
                case "doc_changed": {
                  const docId = event.tool_args?.doc_id;
                  if (docId) {
                    // Use dynamic import to avoid circular dependency
                    const mod = await import("./document-store");
                    mod.useDocumentStore.getState().refreshLines(docId);
                  }
                  break;
                }
        case "session_created":
          set({ sessionId: event.session_id ?? null, connected: true });
          break;

        case "delta":
          set((s) => ({
            streamingContent: s.streamingContent + (event.content ?? ""),
            isGenerating: true,
          }));
          break;

        case "message": {
          // Final message — replace streaming content with the full message
          assistantMessageReceived = true;
          const content = event.content ?? get().streamingContent;
          const currentToolCalls =
            get().activeToolCalls.length > 0
              ? [...get().activeToolCalls]
              : undefined;

          set((s) => ({
            messages: [
              ...s.messages,
              {
                id: nextId(),
                role: "assistant" as const,
                content,
                timestamp: Date.now(),
                toolCalls: currentToolCalls,
              },
            ],
            streamingContent: "",
            activeToolCalls: [],
          }));
          break;
        }

        case "tool_call":
          set((s) => ({
            activeToolCalls: [
              ...s.activeToolCalls,
              {
                name: event.tool_name ?? "unknown",
                args: event.tool_args ?? {},
              },
            ],
          }));
          break;

        case "tool_result":
          set((s) => ({
            activeToolCalls: s.activeToolCalls.map((tc) =>
              tc.name === event.tool_name && !tc.result
                ? { ...tc, result: event.tool_result }
                : tc,
            ),
          }));
          break;

        case "idle":
          // Only add a message if a 'message' event was NOT received for this turn
          if (!assistantMessageReceived && get().streamingContent) {
            const toolCalls =
              get().activeToolCalls.length > 0
                ? [...get().activeToolCalls]
                : undefined;
            set((s) => ({
              messages: [
                ...s.messages,
                {
                  id: nextId(),
                  role: "assistant" as const,
                  content: s.streamingContent,
                  timestamp: Date.now(),
                  toolCalls,
                },
              ],
              streamingContent: "",
              isGenerating: false,
              activeToolCalls: [],
            }));
          } else {
            set({ isGenerating: false, activeToolCalls: [] });
          }
          assistantMessageReceived = false;
          break;

        case "error":
          set((s) => ({
            messages: [
              ...s.messages,
              {
                id: nextId(),
                role: "system" as const,
                content: event.content ?? "An error occurred",
                timestamp: Date.now(),
              },
            ],
            isGenerating: false,
            streamingContent: "",
            activeToolCalls: [],
          }));
          break;
      }
    });

    connection.connect();
    set({ connected: true });
  },

  disconnect: () => {
    if (connection) {
      connection.disconnect();
      connection = null;
    }
    set({ connected: false, sessionId: null });
  },

  sendMessage: (content: string) => {
    if (!connection || !content.trim()) return;

    // Add user message to history
    set((s) => ({
      messages: [
        ...s.messages,
        {
          id: nextId(),
          role: "user" as const,
          content,
          timestamp: Date.now(),
        },
      ],
      isGenerating: true,
      streamingContent: "",
      activeToolCalls: [],
    }));

    connection.sendMessage(content);
  },

  newSession: () => {
    if (connection) {
      connection.requestNewSession();
    }
    set({
      messages: [],
      streamingContent: "",
      isGenerating: false,
      activeToolCalls: [],
    });
  },
}));
