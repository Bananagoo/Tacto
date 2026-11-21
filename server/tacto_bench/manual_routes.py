"""HTTP controls for the hand-set mat, and the page that uses them."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from tacto.contract import Dot
from tacto.lab import Lab

from .manual_mat import PRESETS, ManualMat, Tool

PAGE = Path(__file__).with_name("manual_page.html")


class ToolUse(BaseModel):
    tool: Tool
    a: Dot
    b: Dot


class Finger(BaseModel):
    present: bool = True
    x: float = Field(0.0, ge=-0.2, le=1.2)
    y: float = Field(0.0, ge=-0.2, le=1.2)


class Preset(BaseModel):
    name: str


class MatVisible(BaseModel):
    visible: bool


def manual_router(mat: ManualMat, lab: Lab) -> APIRouter:
    router = APIRouter(prefix="/manual")

    @router.get("", response_class=HTMLResponse)
    def page() -> str:
        return PAGE.read_text()

    @router.get("/presets")
    def presets() -> list[str]:
        return list(PRESETS)

    @router.post("/tool")
    def use_tool(body: ToolUse) -> dict:
        try:
            mat.use_tool(body.tool, body.a, body.b)
        except ValueError as err:
            raise HTTPException(status_code=422, detail=str(err)) from err
        return {"ok": True}

    @router.post("/preset")
    def preset(body: Preset) -> dict:
        if body.name not in PRESETS:
            raise HTTPException(status_code=404, detail=f"no preset called {body.name!r}")
        mat.load_preset(body.name)
        return {"ok": True}

    @router.post("/finger")
    def finger(body: Finger) -> dict:
        mat.set_finger((body.x, body.y) if body.present else None)
        return {"ok": True}

    @router.post("/mat_visible")
    def mat_visible(body: MatVisible) -> dict:
        mat.set_mat_visible(body.visible)
        return {"ok": True}

    @router.post("/restart_lesson")
    def restart_lesson() -> dict:
        lab.restart_lesson()
        return {"ok": True}

    return router
