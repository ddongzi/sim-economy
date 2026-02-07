from fastapi import APIRouter
from app.routers.admin import api
from . import dashboard,players,resources,buildings,accounting

admin_router = APIRouter()
admin_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
admin_router.include_router(players.router, prefix="/players", tags=["dashboard"])
admin_router.include_router(resources.router, prefix="/resources", tags=["dashboard"])
admin_router.include_router(buildings.router, prefix="/buildings", tags=["dashboard"])
admin_router.include_router(accounting.router, prefix="/accounting", tags=["dashboard"])
admin_router.include_router(api.router, prefix="/api", tags=["api"])
