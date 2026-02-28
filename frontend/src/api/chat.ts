/**
 * Chat API — WebSocket client for real-time communication with the AI assistant.
 * 
 * Uses the same pattern as the rest of the API layer: components never 
 * interact with WebSocket directly; they go through the chat store which
 * internally uses this module.
 */

import { logInfo } from "./client";
import * as http from "./client";

/* ---------- Types ---------- */

export interface ChatEvent {
  type:
    | "delta"
    | "message"
    | "tool_call"
    | "tool_result"
    | "error"
    | "idle"
    | "session_created"
    | "status";
  content?: string;
  tool_name?: string;
  tool_args?: Record<string, unknown>;
  tool_result?: string;
  session_id?: string;
  available?: boolean;
}

export interface ChatStatusResponse {
  available: boolean;
  reason?: string;
}

/* ---------- REST helpers ---------- */

export function getChatStatus(): Promise<ChatStatusResponse> {
  return http.get("/chat/status");
}

/* ---------- WebSocket connection ---------- */

export type ChatEventHandler = (event: ChatEvent) => void;

export class ChatConnection {
  private ws: WebSocket | null = null;
  private onEvent: ChatEventHandler;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private _connected = false;

  constructor(onEvent: ChatEventHandler) {
    this.onEvent = onEvent;
  }

  get connected(): boolean {
    return this._connected;
  }

  connect(): void {
    if (this.ws) return;

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    const url = `${protocol}//${host}/api/chat/ws`;

    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this._connected = true;
      logInfo("Chat WebSocket connected");
    };

    this.ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data) as ChatEvent;
        this.onEvent(data);
      } catch {
        console.error("Failed to parse chat event:", evt.data);
      }
    };

    this.ws.onclose = () => {
      this._connected = false;
      this.ws = null;
      logInfo("Chat WebSocket disconnected");
    };

    this.ws.onerror = (err) => {
      console.error("Chat WebSocket error:", err);
    };
  }

  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
      this._connected = false;
    }
  }

  send(message: { type: string; content?: string; session_id?: string }): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    } else {
      console.error("Chat WS not connected");
    }
  }

  sendMessage(content: string): void {
    this.send({ type: "message", content });
  }

  requestNewSession(): void {
    this.send({ type: "create_session" });
  }
}
