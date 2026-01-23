from fastapi import APIRouter
from app.routers.api.admin import players,resources,buildings,accounting

router = APIRouter()
router.include_router(players.router, prefix="/players", tags=["admin"])
router.include_router(resources.router, prefix="/resources", tags=["admin"])
router.include_router(buildings.router, prefix="/buildings", tags=["admin"])
router.include_router(accounting.router, prefix="/accounting", tags=["admin"])
