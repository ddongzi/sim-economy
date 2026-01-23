from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlmodel import Session, select, func
from app.db.session import SessionDep
from app.models import Player, BuildingTask,Resource
from app.core.config import templates
router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, session: SessionDep):

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
    })