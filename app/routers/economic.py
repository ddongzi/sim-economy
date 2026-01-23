# app/api/v1/endpoints/users.py
from fastapi import APIRouter, Request
from fastapi.params import Depends
from starlette.responses import HTMLResponse
from app.core.config import templates
from app.crud import crud_building,crud_player
from app.db.session import SessionDep
from app.dependencies import get_current_user
from app.models import PlayerPublic

router = APIRouter()

@router.get("/", tags=["economic"])
async def economic(request: Request,
                    response: HTMLResponse, session:SessionDep,
                    player_in: PlayerPublic = Depends(get_current_user), ):
    return templates.TemplateResponse(
        "economic.html",
        {
            "request": request,
        }
    )