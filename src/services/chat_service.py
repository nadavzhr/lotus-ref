"""
Chat Service — wraps the GitHub Copilot SDK to provide an AI assistant
that can query the netlist and mutate documents via custom tools.

Lifecycle:
    chat_svc = ChatService(document_service)
    await chat_svc.start()                   # spawns copilot CLI
    session_id = await chat_svc.create_session()
    async for event in chat_svc.send(session_id, "hello"):
        ...  # stream events to the frontend
    await chat_svc.stop()
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Graceful import — the Copilot CLI may not be installed
# ---------------------------------------------------------------------------
try:
    from copilot import CopilotClient, define_tool
    from pydantic import BaseModel as _PydanticBaseModel, Field as _Field

    COPILOT_SDK_AVAILABLE = True
except ImportError:
    COPILOT_SDK_AVAILABLE = False
    logger.warning(
        "github-copilot-sdk not installed or copilot CLI not found. "
        "Chat features will be unavailable."
    )


from services.document_service import DocumentService

# ---------------------------------------------------------------------------
# Event types streamed to the frontend via WebSocket
# ---------------------------------------------------------------------------

@dataclass
class ChatEvent:
    """A single event in the chat stream sent to the frontend."""
    type: str  # "delta", "message", "tool_call", "tool_result", "error", "idle"
    content: str = ""
    tool_name: str = ""
    tool_args: dict = field(default_factory=dict)
    tool_result: str = ""

    def to_dict(self) -> dict:
        d: dict[str, Any] = {"type": self.type}
        if self.content:
            d["content"] = self.content
        if self.tool_name:
            d["tool_name"] = self.tool_name
        if self.tool_args:
            d["tool_args"] = self.tool_args
        if self.tool_result:
            d["tool_result"] = self.tool_result
        return d


# ---------------------------------------------------------------------------
# Tool parameter models (Pydantic, used by @define_tool)
# ---------------------------------------------------------------------------

if COPILOT_SDK_AVAILABLE:

    class ListDocumentsParams(_PydanticBaseModel):
        """No parameters needed."""
        pass

    class GetDocumentLinesParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")
        offset: int = _Field(default=0, description="0-based start position")
        limit: int = _Field(default=50, description="Max lines to return")

    class GetLineParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")
        position: int = _Field(description="0-based line position")

    class SearchLinesParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")
        query: str = _Field(default="", description="Search text or regex pattern")
        use_regex: bool = _Field(default=False, description="Treat query as regex")
        status_filter: Optional[str] = _Field(default=None, description="Filter by status: ok, error, warning, comment, empty")

    class DeleteLineParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")
        position: int = _Field(description="0-based line position to delete")

    class InsertLineParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")
        position: int = _Field(description="0-based position to insert at")

    class ToggleCommentParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")
        position: int = _Field(description="0-based line position")

    class EditCommentTextParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")
        position: int = _Field(description="0-based line position")
        text: str = _Field(description="New comment text (should include '# ' prefix)")

    class SwapLinesParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")
        pos_a: int = _Field(description="First line position (0-based)")
        pos_b: int = _Field(description="Second line position (0-based)")

    class EditAfLineParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")
        position: int = _Field(description="0-based line position")
        template: Optional[str] = _Field(default=None, description="Template name (None for top cell)")
        net: str = _Field(description="Net name or pattern")
        af_value: float = _Field(description="Activity factor value (0.0 to 1.0)")
        is_template_regex: bool = _Field(default=False, description="Treat template as regex")
        is_net_regex: bool = _Field(default=False, description="Treat net as regex")
        is_em_enabled: bool = _Field(default=False, description="Enable EM check")
        is_sh_enabled: bool = _Field(default=False, description="Enable SH check")
        is_sch_enabled: bool = _Field(default=False, description="Enable SCH check")

    class UndoRedoParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")

    class SaveDocumentParams(_PydanticBaseModel):
        doc_id: str = _Field(description="Document ID")

    class QueryNetsParams(_PydanticBaseModel):
        template: Optional[str] = _Field(default=None, description="Template name to search in (None for all)")
        net_pattern: str = _Field(default="", description="Net name or pattern to search for")
        template_regex: bool = _Field(default=False, description="Treat template as regex")
        net_regex: bool = _Field(default=False, description="Treat net_pattern as regex")

    class CheckNetExistsParams(_PydanticBaseModel):
        net_name: str = _Field(description="Net name to check")
        template_name: Optional[str] = _Field(default=None, description="Template to check within")

    class GetTemplatesParams(_PydanticBaseModel):
        pattern: str = _Field(description="Template name or pattern")
        is_regex: bool = _Field(default=False, description="Treat pattern as regex")

    class GetTopCellParams(_PydanticBaseModel):
        """No parameters needed."""
        pass

    class GetNetsInTemplateParams(_PydanticBaseModel):
        template: Optional[str] = _Field(default=None, description="Template name (None for top cell)")


# ---------------------------------------------------------------------------
# ChatService
# ---------------------------------------------------------------------------

class ChatService:
    """Manages Copilot SDK sessions with custom document/NQS tools."""

    def __init__(self, doc_service: DocumentService):
        self._doc_service = doc_service
        self._nqs = doc_service._nqs
        self._client: Any = None
        self._sessions: dict[str, Any] = {}
        self._event_queues: dict[str, asyncio.Queue] = {}
        self._started = False

    @property
    def available(self) -> bool:
        return COPILOT_SDK_AVAILABLE

    async def start(self) -> None:
        """Start the Copilot CLI client."""
        if not COPILOT_SDK_AVAILABLE:
            raise RuntimeError("Copilot SDK is not available")
        if self._started:
            return

        self._client = CopilotClient({
            "log_level": "warning",
        })
        await self._client.start()
        self._started = True
        logger.info("Copilot client started")

    async def stop(self) -> None:
        """Stop the Copilot CLI client and all sessions."""
        if self._client and self._started:
            for sid in list(self._sessions):
                try:
                    await self._sessions[sid].destroy()
                except Exception:
                    pass
            self._sessions.clear()
            self._event_queues.clear()
            await self._client.stop()
            self._started = False
            logger.info("Copilot client stopped")

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def create_session(self, session_id: str | None = None) -> str:
        """Create a new Copilot session with all tools registered.

        Returns the session_id.
        """
        if not self._started:
            await self.start()

        tools = self._build_tools()
        system_message = self._build_system_message()

        # Copilot SDK requires an on_permission_request handler
        def approve_all_permission_handler(request, context):
            return {"kind": "approved"}
        session = await self._client.create_session({
            "model": "gpt-4.1",
            "streaming": True,
            "tools": tools,
            "system_message": {"content": system_message},
            "infinite_sessions": {"enabled": False},
            "on_permission_request": approve_all_permission_handler,
        })

        sid = session_id or session.session_id
        queue: asyncio.Queue[ChatEvent] = asyncio.Queue()
        self._sessions[sid] = session
        self._event_queues[sid] = queue

        def on_event(event):
            evt_type = event.type.value if hasattr(event.type, "value") else str(event.type)
            logger.debug("Chat event: %s", evt_type)

            if evt_type == "assistant.message_delta":
                delta = getattr(event.data, "delta_content", "") or ""
                queue.put_nowait(ChatEvent(type="delta", content=delta))

            elif evt_type == "assistant.message":
                content = getattr(event.data, "content", "") or ""
                queue.put_nowait(ChatEvent(type="message", content=content))

            elif evt_type == "tool.execution_start":
                name = getattr(event.data, "tool_name", "") or ""
                args = getattr(event.data, "arguments", None)
                if args is None:
                    args = {}
                elif not isinstance(args, dict):
                    try:
                        args = json.loads(str(args)) if isinstance(args, str) else {}
                    except Exception:
                        args = {}
                queue.put_nowait(ChatEvent(
                    type="tool_call", tool_name=name, tool_args=args,
                ))

            elif evt_type == "tool.execution_complete":
                name = getattr(event.data, "tool_name", "") or ""
                result_obj = getattr(event.data, "result", None)
                # Result is a dataclass with .content, not a plain string
                if result_obj is not None and hasattr(result_obj, "content"):
                    result_text = result_obj.content or ""
                else:
                    result_text = str(result_obj) if result_obj else ""
                queue.put_nowait(ChatEvent(
                    type="tool_result", tool_name=name, tool_result=result_text,
                ))

            elif evt_type == "session.idle":
                queue.put_nowait(ChatEvent(type="idle"))

            elif evt_type == "session.error":
                msg = getattr(event.data, "message", "") or "Unknown session error"
                queue.put_nowait(ChatEvent(type="error", content=msg))

        session.on(on_event)

        logger.info("Created chat session %s", sid)
        return sid

    async def send_message(
        self, session_id: str, prompt: str,
    ) -> AsyncIterator[ChatEvent]:
        """Send a user message and yield streaming events."""
        session = self._sessions.get(session_id)
        queue = self._event_queues.get(session_id)
        if session is None or queue is None:
            yield ChatEvent(type="error", content="Session not found")
            return

        # Inject current context as a preamble
        context = self._build_context_preamble()
        full_prompt = f"{context}\n\nUser message: {prompt}" if context else prompt

        # Launch send in a background task so we can yield events concurrently.
        # session.send() fires the prompt and resolves when the CLI acknowledges
        # receipt; the actual response streams via the on_event callback → queue.
        send_task = asyncio.ensure_future(session.send({"prompt": full_prompt}))

        # Yield events until idle (or send failure)
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=180.0)
                yield event
                if event.type in ("idle", "error"):
                    break
            except asyncio.TimeoutError:
                yield ChatEvent(type="error", content="Response timed out after 3 minutes")
                break

        # Make sure the send task is cleaned up
        if not send_task.done():
            send_task.cancel()
        else:
            # Surface any exception from send itself
            exc = send_task.exception() if not send_task.cancelled() else None
            if exc:
                logger.error("send_task exception: %s", exc)

    async def destroy_session(self, session_id: str) -> None:
        """Clean up a session."""
        session = self._sessions.pop(session_id, None)
        self._event_queues.pop(session_id, None)
        if session is not None:
            try:
                await session.destroy()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # System message & context
    # ------------------------------------------------------------------

    def _build_system_message(self) -> str:
        return """\
You are an AI assistant embedded in Lotus-Ref, a DCFG (Design Configuration) document editor \
used in VLSI/chip design workflows. You help engineers manage activity factor (AF) and mutex \
documents that reference nets from a parsed SPICE netlist.

## Application Context
- This editor works with two document types: **AF** (Activity Factor) and **Mutex**.
- Each document contains lines that can be: data lines (with parsed fields), comment lines (prefixed with #), or empty lines.
- Line indices are 0-based but it's common to refer to them as 1-based in conversation for user-friendliness (e.g. "line 10" means index 9).
- Lines have validation statuses: ok, warning, error, comment, empty.
- Lines can conflict when their resolved net instances overlap with other lines.
- A SPICE netlist is loaded providing net and template (subcircuit instance) information.

## AF Lines
AF lines define activity factors for nets. Fields: template (optional subcircuit), net name/pattern, \
af_value (0.0-1.0), regex flags, and EM/SH/SCH check enables.

## Mutex Lines
Mutex lines define groups of mutually-exclusive nets. Fields: mutexed net entries, active net entries, \
num_active count, and FEV mode.

## Your Capabilities
You can:
1. **Query the netlist** — search for nets, check if nets exist, list templates, find matching patterns
2. **Read documents** — list loaded documents, view lines, search/filter lines
3. **Mutate documents** — insert/delete/swap lines, toggle comments, edit AF lines, undo/redo, save
4. **Explain** — help users understand validation errors, conflicts, and netlist structure

## Guidelines
- When performing mutations, confirm the action briefly after completion.
- When showing line data, format it clearly with positions and key fields.
- For netlist queries, summarize results concisely. If there are many matches, show a sample and the total count.
- Use 0-based positions when referencing lines.
- If a tool call fails, explain the error and suggest alternatives.
- Be concise and technical — users are chip design engineers.
"""

    def _build_context_preamble(self) -> str:
        """Build a dynamic context string with current session state."""
        parts: list[str] = []

        # Loaded documents
        docs = self._doc_service.list_documents()
        if docs:
            doc_lines = []
            for d in docs:
                doc_lines.append(
                    f"  - {d['doc_id']} ({d['doc_type']}): {d['total_lines']} lines, "
                    f"file={d['file_path']}, status={d['status_counts']}"
                )
            parts.append("Currently loaded documents:\n" + "\n".join(doc_lines))
        else:
            parts.append("No documents are currently loaded.")

        # Top cell
        try:
            top_cell = self._nqs.get_top_cell()
            parts.append(f"Netlist top cell: {top_cell}")
        except Exception:
            parts.append("No netlist is loaded.")

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    def _build_tools(self) -> list:
        """Build the list of @define_tool functions for the Copilot session."""
        svc = self._doc_service
        nqs = self._nqs

        # ---- Document read tools ----

        @define_tool(description="List all loaded documents with their types, line counts, and status summaries")
        def list_documents(params: ListDocumentsParams) -> str:
            docs = svc.list_documents()
            if not docs:
                return "No documents are currently loaded."
            return json.dumps(docs, indent=2)

        @define_tool(description="Get lines from a document. Returns position, raw_text, status, errors, warnings for each line.")
        def get_document_lines(params: GetDocumentLinesParams) -> str:
            try:
                lines = svc.get_lines(params.doc_id, offset=params.offset, limit=params.limit)
                return json.dumps(lines, indent=2)
            except KeyError:
                return f"Error: Document '{params.doc_id}' not found"

        @define_tool(description="Get a single line by position with full details (data, status, conflicts)")
        def get_line(params: GetLineParams) -> str:
            try:
                line = svc.get_line(params.doc_id, params.position)
                return json.dumps(line, indent=2)
            except (KeyError, IndexError):
                return f"Error: Line {params.position} not found in document '{params.doc_id}'"

        @define_tool(description="Search/filter lines by text content or status. Supports plain text and regex search.")
        def search_lines(params: SearchLinesParams) -> str:
            try:
                results = svc.search_lines(
                    params.doc_id, params.query,
                    use_regex=params.use_regex,
                    status_filter=params.status_filter,
                )
                return json.dumps(results, indent=2)
            except KeyError:
                return f"Error: Document '{params.doc_id}' not found"
            except ValueError as e:
                return f"Error: {e}"


        # Helper to emit doc_changed event after mutation
        def emit_doc_changed(doc_id):
            # Find all queues and put a doc_changed event (for this session only)
            queue = self._event_queues.get(list(self._sessions.keys())[-1])
            if queue:
                queue.put_nowait(ChatEvent(type="doc_changed", content="", tool_name="", tool_args={"doc_id": doc_id}))

        @define_tool(description="Delete a line at the given 0-based position. Returns updated document summary.")
        def delete_line(params: DeleteLineParams) -> str:
            try:
                result = svc.delete_line(params.doc_id, params.position)
                emit_doc_changed(params.doc_id)
                return json.dumps(result, indent=2)
            except (KeyError, IndexError):
                return f"Error: Line {params.position} not found in document '{params.doc_id}'"
            except Exception as e:
                return f"Error: {e}"

        @define_tool(description="Insert a blank line at the given 0-based position")
        def insert_line(params: InsertLineParams) -> str:
            try:
                result = svc.insert_blank_line(params.doc_id, params.position)
                emit_doc_changed(params.doc_id)
                return json.dumps(result, indent=2)
            except (KeyError, IndexError):
                return f"Error: Position {params.position} not found in document '{params.doc_id}'"
            except Exception as e:
                return f"Error: {e}"

        @define_tool(description="Toggle comment state of a line (comment ↔ uncomment). Commenting prepends '# ', uncommenting re-parses.")
        def toggle_comment(params: ToggleCommentParams) -> str:
            try:
                result = svc.toggle_comment(params.doc_id, params.position)
                emit_doc_changed(params.doc_id)
                return json.dumps(result, indent=2)
            except (KeyError, IndexError):
                return f"Error: Line {params.position} not found in document '{params.doc_id}'"
            except Exception as e:
                return f"Error: {e}"

        @define_tool(description="Edit the raw text of a comment line (must already be a comment)")
        def edit_comment_text(params: EditCommentTextParams) -> str:
            try:
                result = svc.edit_comment_text(params.doc_id, params.position, params.text)
                emit_doc_changed(params.doc_id)
                return json.dumps(result, indent=2)
            except (KeyError, IndexError):
                return f"Error: Line {params.position} not found"
            except ValueError as e:
                return f"Error: {e}"

        @define_tool(description="Swap two lines by their 0-based positions")
        def swap_lines(params: SwapLinesParams) -> str:
            try:
                result = svc.swap_lines(params.doc_id, params.pos_a, params.pos_b)
                emit_doc_changed(params.doc_id)
                return json.dumps(result, indent=2)
            except (KeyError, IndexError, ValueError) as e:
                return f"Error: {e}"

        @define_tool(description="Edit an AF line: hydrates session with given fields, validates, and commits. One-shot edit.")
        def edit_af_line(params: EditAfLineParams) -> str:
            try:
                fields = {
                    "template": params.template,
                    "net": params.net,
                    "af_value": params.af_value,
                    "is_template_regex": params.is_template_regex,
                    "is_net_regex": params.is_net_regex,
                    "is_em_enabled": params.is_em_enabled,
                    "is_sh_enabled": params.is_sh_enabled,
                    "is_sch_enabled": params.is_sch_enabled,
                }
                svc.hydrate_session(params.doc_id, params.position, fields)
                result = svc.commit_edit(params.doc_id, params.position)
                emit_doc_changed(params.doc_id)
                return json.dumps(result, indent=2)
            except (KeyError, IndexError):
                return f"Error: Line {params.position} not found in document '{params.doc_id}'"
            except Exception as e:
                return f"Error: {e}"

        @define_tool(description="Undo the last mutation in a document")
        def undo(params: UndoRedoParams) -> str:
            try:
                result = svc.undo(params.doc_id)
                emit_doc_changed(params.doc_id)
                return json.dumps(result, indent=2)
            except (KeyError, ValueError) as e:
                return f"Error: {e}"

        @define_tool(description="Redo the last undone mutation in a document")
        def redo(params: UndoRedoParams) -> str:
            try:
                result = svc.redo(params.doc_id)
                emit_doc_changed(params.doc_id)
                return json.dumps(result, indent=2)
            except (KeyError, ValueError) as e:
                return f"Error: {e}"

        @define_tool(description="Save a document to disk (overwrites the original file)")
        def save_document(params: SaveDocumentParams) -> str:
            try:
                result = svc.save(params.doc_id)
                emit_doc_changed(params.doc_id)
                return json.dumps(result, indent=2)
            except KeyError:
                return f"Error: Document '{params.doc_id}' not found"
            except Exception as e:
                return f"Error: {e}"

        # ---- NQS (Netlist Query Service) tools ----

        @define_tool(description="Search the netlist for nets matching a pattern. Returns lists of matching nets and templates. Supports regex and plain substring matching.")
        def query_nets(params: QueryNetsParams) -> str:
            try:
                result = svc.query_nets(
                    params.template, params.net_pattern,
                    params.template_regex, params.net_regex,
                )
                nets = result.get("nets", [])
                templates = result.get("templates", [])
                summary = f"Found {len(nets)} nets and {len(templates)} templates."
                if len(nets) > 100:
                    return json.dumps({
                        "summary": summary,
                        "nets_sample": nets[:50],
                        "nets_total": len(nets),
                        "templates": templates,
                    }, indent=2)
                return json.dumps(result, indent=2)
            except Exception as e:
                return f"Error: {e}"

        @define_tool(description="Check if a specific net exists in the netlist, optionally within a template")
        def check_net_exists(params: CheckNetExistsParams) -> str:
            try:
                exists = nqs.net_exists(params.net_name, params.template_name)
                return json.dumps({"net": params.net_name, "template": params.template_name, "exists": exists})
            except Exception as e:
                return f"Error: {e}"

        @define_tool(description="Find templates (subcircuit instances) matching a pattern")
        def get_templates(params: GetTemplatesParams) -> str:
            try:
                templates = nqs.get_matching_templates(params.pattern, params.is_regex)
                return json.dumps({"pattern": params.pattern, "templates": sorted(templates)}, indent=2)
            except Exception as e:
                return f"Error: {e}"

        @define_tool(description="Get the top-level cell name from the loaded netlist")
        def get_top_cell(params: GetTopCellParams) -> str:
            try:
                return json.dumps({"top_cell": nqs.get_top_cell()})
            except Exception as e:
                return f"Error: {e}"

        @define_tool(description="Get all net names within a specific template (or all nets in top cell if template is None)")
        def get_nets_in_template(params: GetNetsInTemplateParams) -> str:
            try:
                nets = nqs.get_all_nets_in_template(params.template)
                net_list = sorted(nets)
                if len(net_list) > 200:
                    return json.dumps({
                        "template": params.template,
                        "total": len(net_list),
                        "sample": net_list[:100],
                    }, indent=2)
                return json.dumps({"template": params.template, "nets": net_list}, indent=2)
            except Exception as e:
                return f"Error: {e}"

        return [
            list_documents,
            get_document_lines,
            get_line,
            search_lines,
            delete_line,
            insert_line,
            toggle_comment,
            edit_comment_text,
            swap_lines,
            edit_af_line,
            undo,
            redo,
            save_document,
            query_nets,
            check_net_exists,
            get_templates,
            get_top_cell,
            get_nets_in_template,
        ]
