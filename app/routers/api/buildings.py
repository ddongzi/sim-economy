from typing import List
from app.service.playerService import playerService
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import SQLModel, select, or_

from app.core.config import GOVERNMENT_PLAYER_ID
from app.core.error import GameError
from app.db.session import SessionDep
from app.dependencies import get_current_user
from app.models import PlayerBuilding, PlayerBuildingPublic, PlayerPublic, PlayerBuildingCreate, BuildingMetaPublic, \
    TransactionActionType, BuildingLevelsConfig

from app.crud import crud_building,crud_player
from app.service.accounting import AccountingService
import logging
logger = logging.getLogger("fastapi")

router = APIRouter()

@router.get("/", response_model=List[PlayerBuildingPublic])
async def get_buildings(session: SessionDep,
                        player_in: PlayerPublic = Depends(get_current_user)
                        ):
    """ 获取player的所有建筑"""
    result = []
    buildings = crud_building.get_player_buildings(session, player_id=player_in.id)
    for building in buildings:
        out = PlayerBuildingPublic.model_validate(building)
        out.building_meta = BuildingMetaPublic.model_validate(building.building_meta)
        task  = crud_building.get_building_tasks_by_player_building(session, building.id)
        out.task = task
        result.append(out)
    return result

@router.get("/{player_building_id}", response_model=PlayerBuildingPublic, tags=["playerBuilding"])
async def get_building(session: SessionDep,
                       player_building_id: int,
                        player_in: PlayerPublic = Depends(get_current_user),
                       ):
    return crud_building.get_player_building_by_id(session, player_building_id)


@router.post("/construct")
async def create_building(session: SessionDep, pb: PlayerBuildingCreate,
                          player_in: PlayerPublic = Depends(get_current_user)
                          ):
    """ 建造 """
    try:
        building_meta = crud_building.get_building_meta_by_id(session, pb.building_meta_id)
        AccountingService.change_cash(session, player_in.id, -building_meta.building_cost,
                                      TransactionActionType.BUILD_COST, 0)
        AccountingService.change_cash(session, GOVERNMENT_PLAYER_ID, building_meta.building_cost,
                                      TransactionActionType.BUILD_REVENUE, 0)
        crud_building.create_player_building(session, pb, player_in.id)
        session.commit()
        player = crud_player.get_player_by_id(session, player_in.id)
        await playerService.send_update_cash(player_in.name, player.cash)
    except Exception as e:
        session.rollback()
        logger.exception("Construct building err!")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # 无论成功失败
        pass



@router.post("/upgrade/{player_building_id}")
async def upgrade_building(session: SessionDep,
                          player_building_id: int,
                          player_in: PlayerPublic = Depends(get_current_user)
                          ):
    try:
        player_building = crud_building.get_player_building_by_id(session, player_building_id)
        player_building.level += 1
        session.add(player_building)
        session.flush()
        level_config = session.exec(
            select(BuildingLevelsConfig).where(BuildingLevelsConfig.level == player_building.level,
                                               BuildingLevelsConfig.building_meta_id == player_building.building_meta_id,
                                               )
        ).one_or_none()
        AccountingService.change_cash(session, player_in.id, -level_config.cost,
                                      TransactionActionType.BUILDING_UPGRADE_COST, player_building.id)
        AccountingService.change_cash(session, GOVERNMENT_PLAYER_ID, level_config.cost,
                                      TransactionActionType.SYSTEM_BUILDING_UPGRADE_REVENUE, player_building.id)
        session.commit()
        player = crud_player.get_player_by_id(session, player_in.id)
        await playerService.send_update_cash(player_in.name, player.cash)
    except GameError as e:
        session.rollback()
        logger.exception("Upgrade building err!")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        session.rollback()
        logger.exception("Upgrade building err!")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/remove/{player_building_id}")
async def remove_building(session: SessionDep,
                          player_building_id: int,
                          player_in: PlayerPublic = Depends(get_current_user)
                          ):
    crud_building.delete_player_building(session, player_building_id)
    session.commit()
