"""
API routes for the document editor prototype.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from core import DocumentType
from app.document_service import DocumentService


router = APIRouter(prefix="/api")

# Singleton service — created in main.py and attached here
_service: Optional[DocumentService] = None


def init_service(svc: DocumentService) -> None:
    global _service
    _service = svc


def svc() -> DocumentService:
    if _service is None:
        raise RuntimeError("DocumentService not initialized")
    return _service


# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------

class LoadRequest(BaseModel):
    doc_id: str
    file_path: str
    doc_type: str  # "af" or "mutex"


class EditRequest(BaseModel):
    fields: dict


class SaveRequest(BaseModel):
    file_path: Optional[str] = None


class QueryNetsRequest(BaseModel):
    template: Optional[str] = None
    net_pattern: str = ""
    template_regex: bool = False
    net_regex: bool = False


class MutexEntryRequest(BaseModel):
    template: Optional[str] = None
    net_pattern: str
    is_regex: bool = False


class MutexActiveRequest(BaseModel):
    template: Optional[str] = None
    net_name: str


class MutexFevRequest(BaseModel):
    fev: str = ""


class MutexNumActiveRequest(BaseModel):
    value: int


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/documents/load")
def load_document(req: LoadRequest):
    """Load a dcfg file into memory."""
    try:
        dt = DocumentType(req.doc_type)
    except ValueError:
        raise HTTPException(400, f"Unknown doc_type: {req.doc_type}")
    try:
        return svc().load(req.doc_id, req.file_path, dt)
    except FileNotFoundError:
        raise HTTPException(404, f"File not found: {req.file_path}")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/documents")
def list_documents():
    """List all loaded documents."""
    return svc().list_documents()


@router.get("/documents/{doc_id}/lines")
def get_lines(doc_id: str):
    """Get all lines in a document."""
    try:
        return svc().get_lines(doc_id)
    except KeyError:
        raise HTTPException(404, f"Document not found: {doc_id}")


@router.get("/documents/{doc_id}/lines/{position}")
def get_line(doc_id: str, position: int):
    """Get a single line by 0-based position."""
    try:
        return svc().get_line(doc_id, position)
    except (KeyError, IndexError):
        raise HTTPException(404, "Document or line not found")


@router.post("/documents/{doc_id}/lines/{position}/edit")
def start_edit(doc_id: str, position: int):
    """Start editing a line — returns editable fields."""
    try:
        return svc().start_edit(doc_id, position)
    except (KeyError, IndexError):
        raise HTTPException(404, "Document or line not found")


@router.put("/documents/{doc_id}/lines/{position}/session")
def update_session(doc_id: str, position: int, req: EditRequest):
    """Update the active edit session with new field values (any doc type)."""
    try:
        return svc().update_session(doc_id, position, req.fields)
    except (KeyError, IndexError):
        raise HTTPException(404, "Document or line not found")
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post("/documents/{doc_id}/lines/{position}/commit")
def commit_edit(doc_id: str, position: int):
    """Commit the current edit session to the document (any doc type)."""
    try:
        return svc().commit_edit(doc_id, position)
    except (KeyError, IndexError):
        raise HTTPException(404, "Document or line not found")
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post("/documents/{doc_id}/save")
def save_doc(doc_id: str, req: SaveRequest):
    """Save a document back to disk."""
    try:
        return svc().save(doc_id, req.file_path)
    except KeyError:
        raise HTTPException(404, f"Document not found: {doc_id}")
    except Exception as e:
        raise HTTPException(500, str(e))


# ------------------------------------------------------------------
# NQS Query Preview
# ------------------------------------------------------------------

@router.post("/query-nets")
def query_nets(req: QueryNetsRequest):
    """Query NQS for matching nets and templates."""
    try:
        return svc().query_nets(
            req.template, req.net_pattern,
            req.template_regex, req.net_regex,
        )
    except Exception as e:
        raise HTTPException(422, str(e))


# ------------------------------------------------------------------
# Mutex session operations
# ------------------------------------------------------------------

@router.get("/documents/{doc_id}/lines/{position}/mutex/session")
def get_mutex_session(doc_id: str, position: int):
    """Get current mutex edit session state."""
    try:
        return svc().get_mutex_session(doc_id, position)
    except (KeyError, IndexError):
        raise HTTPException(404, "Document or line not found")
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post("/documents/{doc_id}/lines/{position}/mutex/add-mutexed")
def mutex_add_mutexed(doc_id: str, position: int, req: MutexEntryRequest):
    """Add a net pattern to the mutexed set via the controller."""
    try:
        return svc().mutex_add_mutexed(
            doc_id, position, req.template, req.net_pattern, req.is_regex,
        )
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post("/documents/{doc_id}/lines/{position}/mutex/add-active")
def mutex_add_active(doc_id: str, position: int, req: MutexActiveRequest):
    """Add a net directly to the active (and mutexed) set."""
    try:
        return svc().mutex_add_active(
            doc_id, position, req.template, req.net_name,
        )
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post("/documents/{doc_id}/lines/{position}/mutex/remove-mutexed")
def mutex_remove_mutexed(doc_id: str, position: int, req: MutexEntryRequest):
    """Remove a net pattern from the mutexed set."""
    try:
        return svc().mutex_remove_mutexed(
            doc_id, position, req.template, req.net_pattern, req.is_regex,
        )
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post("/documents/{doc_id}/lines/{position}/mutex/remove-active")
def mutex_remove_active(doc_id: str, position: int, req: MutexActiveRequest):
    """Remove a net from the active set."""
    try:
        return svc().mutex_remove_active(
            doc_id, position, req.template, req.net_name,
        )
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post("/documents/{doc_id}/lines/{position}/mutex/set-fev")
def mutex_set_fev(doc_id: str, position: int, req: MutexFevRequest):
    """Set FEV mode on the mutex session."""
    try:
        return svc().mutex_set_fev(doc_id, position, req.fev)
    except Exception as e:
        raise HTTPException(422, str(e))


@router.post("/documents/{doc_id}/lines/{position}/mutex/set-num-active")
def mutex_set_num_active(doc_id: str, position: int, req: MutexNumActiveRequest):
    """Set num_active on the mutex session (only when active list is empty)."""
    try:
        return svc().mutex_set_num_active(doc_id, position, req.value)
    except Exception as e:
        raise HTTPException(422, str(e))


# commit_mutex_edit removed — use the unified POST /lines/{position}/commit instead
