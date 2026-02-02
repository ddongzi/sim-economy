from fastapi import APIRouter
from fastapi.params import Depends

from app.core.config import GAME_DATA_VERSION
from app.models import PlayerPublic
from app.routers.api import api_router
from app.routers import landscape,exchange,constract,inventory,economic,journal,chat,ws,personal
from app.routers.admin import admin_router
from fastapi import FastAPI, Request
from app.core.config import templates
from app.dependencies import get_current_user
router = APIRouter()

@router.get("/")
async def root(request: Request,):
    return templates.TemplateResponse("index.html", {"request": request})

router.include_router(admin_router, prefix="/admin")
router.include_router(api_router, prefix="/api")

router.include_router(landscape.router, prefix="/landscape")
router.include_router(exchange.router, prefix="/exchange")
router.include_router(constract.router, prefix="/contract")
router.include_router(inventory.router, prefix="/inventory")
router.include_router(economic.router, prefix="/economic")
router.include_router(chat.router, prefix="/chat")
router.include_router(personal.router, prefix="/personal")

router.include_router(journal.router, prefix="/journal")
router.include_router(ws.router, prefix="/ws")

