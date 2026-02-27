"""
FastAPI application entry point.

Run:  cd bg-refactor && python -m uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import sys
import os
import logging

# Ensure bg-refactor/src is on sys.path so absolute imports work
_project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(_project_root, "src"))
sys.path.insert(0, _project_root)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.document_service import DocumentService
from app.routes import router, init_service

app = FastAPI(title="DCFG Editor Prototype")

from nqs.netlist_query_service import NetlistQueryService
from nqs.netlist_parser.NetlistBuilder import NetlistBuilder
_spice_file = os.path.join(_project_root, "data", "spice", "mycell.sp")
nqs = NetlistQueryService(cell="mycell", spice_file=_spice_file, netlist=NetlistBuilder(logger=logging.getLogger(__name__)))

init_service(DocumentService(nqs=nqs))

# API routes
app.include_router(router)

# Serve static frontend
_static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_static_dir):
    app.mount("/static", StaticFiles(directory=_static_dir), name="static")


@app.get("/")
def index():
    """Serve the frontend."""
    return FileResponse(os.path.join(_static_dir, "index.html"))
