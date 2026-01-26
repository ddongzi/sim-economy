from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, BackgroundTasks

from app.core.config import GAME_DATA_VERSION
from app.crud import crud_building, crud_recipe, crud_player, crud_resources, crud_building_task,crud_industry
from app.dependencies import get_current_user
from app.models import BuildingMetaPublic, ResourcePublic, Recipe, RecipePublic, Industry, BuildingMetaDetail
from app.routers.api import buildings, admin, recipe,player,task,inventory,exchange,public,contract
from app.db.session import SessionDep


api_router = APIRouter(
    dependencies=[Depends(get_current_user)]
)
api_router.include_router(buildings.router, prefix="/buildings", tags=["building"])
api_router.include_router(admin.router, prefix="/admin", tags=["api"])
api_router.include_router(recipe.router, prefix="/recipe", tags=["recipe"])
api_router.include_router(task.router, prefix="/task", tags=["task"],
                          )
api_router.include_router(player.router, prefix="/player", tags=["player"])
api_router.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
api_router.include_router(exchange.router, prefix="/exchange", tags=["exchange"])
api_router.include_router(public.router, prefix="/public", tags=["public"])

api_router.include_router(contract.router, prefix="/contract", tags=["contract"])


#  localstorage game data

@api_router.get("/version", tags=["api"])
def version():
    return {"version": GAME_DATA_VERSION}
@api_router.get("/gamedata", tags=["gamedata"])
async def gamedata(session: SessionDep):
    buildings = crud_building.get_all_building_metas(session)
    resources = crud_resources.get_resources_all(session)
    recipes = crud_recipe.get_recipes_all(session)
    industries = crud_industry.get_industries(session)
    return {
        "version": GAME_DATA_VERSION,
        "buildings": [ BuildingMetaDetail.model_validate(building) for building in buildings],
        "resources": [ ResourcePublic.model_validate(resource) for resource in resources],
        "recipes": [RecipePublic.model_validate(recipe) for recipe in recipes],
        "industries": industries
    }

