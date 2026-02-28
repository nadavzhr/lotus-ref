"""
Chat WebSocket routes for the AI assistant.

Provides a WebSocket endpoint that streams chat events (deltas, tool calls,
final messages) from the Copilot SDK to the frontend.

Protocol (JSON over WebSocket):

  Client → Server:
    { "type": "message", "content": "..." }
    { "type": "create_session" }
    { "type": "destroy_session", "session_id": "..." }

  Server → Client:
    { "type": "delta", "content": "..." }           — streaming text chunk
    { "type": "message", "content": "..." }          — final complete message
    { "type": "tool_call", "tool_name": "...", "tool_args": {...} }
    { "type": "tool_result", "tool_name": "...", "tool_result": "..." }
    { "type": "error", "content": "..." }
    { "type": "idle" }                               — turn complete
    { "type": "session_created", "session_id": "..." }
    { "type": "status", "available": bool }
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat")

# Set by main.py
_chat_service = None


def init_chat_service(svc) -> None:
    global _chat_service
    _chat_service = svc


def chat_svc():
    return _chat_service


# ------------------------------------------------------------------
# REST endpoints (for status checks)
# ------------------------------------------------------------------

@router.get("/status")
async def chat_status():
    """Check if the chat service is available."""
    if chat_svc() is None:
        return {"available": False, "reason": "Chat service not initialized"}
    return {"available": chat_svc().available}


# ------------------------------------------------------------------
# WebSocket endpoint
# ------------------------------------------------------------------

@router.websocket("/ws")
async def chat_websocket(ws: WebSocket):
    """WebSocket endpoint for real-time chat with the AI assistant."""
    await ws.accept()

    svc = chat_svc()
    if svc is None or not svc.available:
        await ws.send_json({
            "type": "error",
            "content": "Chat service is not available. Ensure the Copilot CLI is installed.",
        })
        await ws.close()
        return

    # Create a session for this WebSocket connection
    session_id: Optional[str] = None

    try:
        # Auto-create a session on connect
        try:
            session_id = await svc.create_session()
            await ws.send_json({
                "type": "session_created",
                "session_id": session_id,
            })
        except Exception as e:
            logger.error("Failed to create chat session: %s", e, exc_info=True)
            await ws.send_json({
                "type": "error",
                "content": f"Failed to create session: {e}",
            })
            await ws.close()
            return

        # Message loop
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "")

            if msg_type == "message":
                content = msg.get("content", "").strip()
                if not content:
                    await ws.send_json({"type": "error", "content": "Empty message"})
                    continue

                try:
                    async for event in svc.send_message(session_id, content):
                        await ws.send_json(event.to_dict())
                except Exception as e:
                    logger.error("Chat error: %s", e, exc_info=True)
                    await ws.send_json({
                        "type": "error",
                        "content": f"Chat error: {e}",
                    })

            elif msg_type == "create_session":
                # Destroy old session, create new one
                if session_id:
                    await svc.destroy_session(session_id)
                try:
                    session_id = await svc.create_session()
                    await ws.send_json({
                        "type": "session_created",
                        "session_id": session_id,
                    })
                except Exception as e:
                    await ws.send_json({
                        "type": "error",
                        "content": f"Failed to create session: {e}",
                    })

            elif msg_type == "destroy_session":
                if session_id:
                    await svc.destroy_session(session_id)
                    session_id = None
                await ws.send_json({"type": "idle"})

            else:
                await ws.send_json({
                    "type": "error",
                    "content": f"Unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        logger.info("Chat WebSocket disconnected (session=%s)", session_id)
    except Exception as e:
        logger.error("Chat WebSocket error: %s", e, exc_info=True)
    finally:
        if session_id and svc:
            try:
                await svc.destroy_session(session_id)
            except Exception:
                pass
