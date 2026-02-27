"""
FastAPI application entry point.

Run:  cd lotus-ref && python -m uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import logging
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from services.document_service import DocumentService
from app.routes import router, init_service
from nqs.netlist_query_service import NetlistQueryService
from nqs.netlist_parser.NetlistBuilder import NetlistBuilder

_project_root = Path(__file__).resolve().parent.parent

app = FastAPI(title="DCFG Editor Prototype")

cell = "mycell"
_spice_file = _project_root / "data" / "spice" / f"{cell}.sp"
nqs = NetlistQueryService(cell=cell, spice_file=_spice_file, netlist=NetlistBuilder(logger=logging.getLogger(__name__)))

# cell = "ip78d6hcf2sr4096x135m4i2k4w8r2lya"
# _spice_file2 = _project_root / "tmp" / cell / "spice" / f"{cell}.sp"
# nqs = NetlistQueryService(cell=cell, spice_file=_spice_file2, netlist=NetlistBuilder(logger=logging.getLogger(__name__)))

init_service(DocumentService(nqs=nqs))

# API routes
app.include_router(router)

# Serve static frontend
_static_dir = Path(__file__).resolve().parent / "static"
if _static_dir.is_dir():
    # Serve /assets/ for JS/CSS bundles produced by Vite
    _assets_dir = _static_dir / "assets"
    if _assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=str(_assets_dir)), name="assets")
    # Serve remaining static files (e.g. vite.svg) at root-level
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/vite.svg")
def vite_svg():
    """Serve the Vite favicon."""
    return FileResponse(str(_static_dir / "vite.svg"))


@app.get("/")
def index():
    """Serve the frontend."""
    return FileResponse(str(_static_dir / "index.html"))
