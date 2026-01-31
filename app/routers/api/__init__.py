from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, BackgroundTasks,HTTPException
from sqlmodel import select
from app.core.config import GAME_DATA_VERSION, GOVERNMENT_PLAYER_ID
from app.core.error import GameError
from app.crud import crud_building, crud_recipe, crud_player, crud_resources, crud_building_task,crud_industry
from app.dependencies import get_current_user
from app.models import BuildingMetaPublic, ResourcePublic, Recipe, RecipePublic, Industry, BuildingMetaDetail, \
    PlayerPublic, GovernmentOrder, TransactionActionType, GovernmentOrderDelivery
from app.routers.api import buildings, admin, recipe,player,task,inventory,exchange,public,contract
from app.db.session import SessionDep
from app.service.accounting import AccountingService
from app.service.inventory import InventoryService
from app.service.playerService import playerService
import logging
logger = logging.getLogger(__name__)
api_router = APIRouter(
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

@api_router.post("/government/delivery")
async def govern_purchase(session: SessionDep,
                        data: GovernmentOrderDelivery,
                          current_user: PlayerPublic = Depends(get_current_user)):
    """ 政府采购 """
    try:
        order = session.exec(
            select(GovernmentOrder).where(GovernmentOrder.id == data.order_id).with_for_update()
        ).first()
        if order.current_quantity + data.quantity > order.target_quantity:
            raise HTTPException(status_code=400, detail="采购计划已满")
        order.current_quantity += data.quantity
        session.add(order)
        AccountingService.change_cash(session, current_user.id, order.fixed_price * data.quantity,
                                      TransactionActionType.GOVERNMENT_PURCHASE_REVENUE, order.id)
        AccountingService.change_cash(session, GOVERNMENT_PLAYER_ID, -order.fixed_price * data.quantity,
                                      TransactionActionType.GOVERNMENT_PURCHASE_COST, order.id)
        InventoryService.change_resource(session, current_user.id, order.resource_id, -data.quantity)
        InventoryService.change_resource(session, GOVERNMENT_PLAYER_ID, order.resource_id, data.quantity)
        session.commit()
        player = crud_player.get_player_by_id(session, current_user.id)
        await playerService.send_update_cash(current_user.name, player.cash)
    except GameError as e:
        session.rollback()
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        session.rollback()
        logger.exception(f" govern purchase failed! {e}")
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "message": "ok"
    }