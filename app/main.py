"""
FastAPI application entry point.

Run:  cd bg-refactor && python -m uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import sys
import os

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

sys.path.append("/nfs/site/disks/cccad_totem/work/nadavzoh/testing-ground/lotus/")
sys.path.append("/nfs/site/disks/cccad_totem/work/nadavzoh/testing-ground/fly/")
from fly.fly_netlist.FlyNetlistBuilder import FlyNetlistBuilder
fly_netlist_builder = FlyNetlistBuilder()
from nqs.netlist_query_service import NetlistQueryService  # noqa — src/nqs/
nqs = NetlistQueryService(cell="dcchunkrotd", spice_file="/nfs/site/disks/cccad_totem/work/nadavzoh/WARDS/dcchunkrotd/netlists/spice/dcchunkrotd.sp", fly_netlist=fly_netlist_builder)

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
