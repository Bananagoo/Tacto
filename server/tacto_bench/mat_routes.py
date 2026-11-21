"""Routes for the virtual mat (web page at /devtools/#mat). Not part of the product.

GET  /dev/mat            the layout and what is on the mat now
POST /dev/mat/draw       draw or erase one of the mat's lines
POST /dev/mat/slot       put a tile in a slot, or empty it
POST /dev/mat/finger     put the fingertip somewhere, or lift it
POST /dev/mat/reset      back to the kit as it ships
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tacto.mat.models import SlotContent
from tacto.observation import Fingertip

from .virtual_mat import VirtualMat


class Draw(BaseModel):
    id: str
    drawn: bool


class PutTile(BaseModel):
    id: str
    content: SlotContent


class Finger(BaseModel):
    fingertip: Fingertip | None


def mat_router(mat: VirtualMat) -> APIRouter:
    router = APIRouter(prefix="/dev/mat", tags=["devtools"])

    @router.get("")
    def show() -> dict:
        observation = mat.observe()
        return {
            "layout": mat.layout.model_dump(),
            "drawn": sorted(observation.reading.drawn),
            "slots": observation.reading.slots,
            "fingertip": observation.fingertip,
        }

    @router.post("/draw")
    def draw(body: Draw) -> dict:
        try:
            mat.set_drawn(body.id, body.drawn)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        return show()

    @router.post("/slot")
    def put_tile(body: PutTile) -> dict:
        try:
            mat.set_slot(body.id, body.content)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error.args[0])) from error
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        return show()

    @router.post("/finger")
    def finger(body: Finger) -> dict:
        mat.set_fingertip(body.fingertip)
        return show()

    @router.post("/reset")
    def reset() -> dict:
        mat.reset()
        return show()

    return router
