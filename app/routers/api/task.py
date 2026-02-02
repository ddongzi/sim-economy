from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import defer

from app.core.error import GameRespCode, GameError
from app.db.session import SessionDep
from app.dependencies import get_current_user
from datetime import datetime, timedelta
from app.crud import crud_building_task, crud_inventory, crud_player, crud_recipe
from app.logic.task import calculate_task_cost
from app.models import PlayerPublic, BuildingTaskCreate, BuildingTaskBase, TransactionActionType, BuildingTask
from app.service import AccountingService
from app.service import InventoryService
from app.service import PlayerService
import logging
logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create", tags=["task"])
async def product(session: SessionDep, building_task: BuildingTaskCreate,
                  player_in: PlayerPublic = Depends(get_current_user),
                  ):
    """开始生产"""
    task = crud_building_task.get_building_task_by_player_building_id(session, building_task.player_building_id)
    if task:
        if task.end_time <= datetime.now():
            # 任务过期了，但还没领取
            raise HTTPException(status_code=400, detail=GameRespCode.TASK_NOT_CLAIM.detail)
        else:
            raise HTTPException(status_code=400, detail=GameRespCode.BUILDING_BUSY.detail)
    # 计算时间成本
    calculate_task_cost(session, building_task)

    recipe = crud_recipe.get_recipe_by_output_resource_id(session, building_task.resource_id)
    if not recipe:
        raise HTTPException(status_code=400, detail="异常：找不到配方信息")
    hours = building_task.quantity / recipe.per_hour

    try:
        # 创建任务
        task = crud_building_task.create_building_task(session, building_task, player_id=player_in.id, duration=hours)
        session.flush()
        # 扣除成本
        AccountingService.change_cash(session, player_in.id, -building_task.cash_cost,
                                      TransactionActionType.PRODUCE_COST, task.id)
        # 扣除库存
        for input in recipe.inputs:
            InventoryService.change_resource(session, player_in.id, input.resource_id,
                                             -input.quantity * building_task.quantity)
        session.commit()
        player = crud_player.get_player_by_id(session, player_in.id)
        await PlayerService.playerWs.send_update_cash(player_in.name, player.cash)
    except GameError as e:
        session.rollback()
        logger.error(e)
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        session.rollback()
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))

    return {"msg": "建筑任务创建成功"}


@router.get("/{player_building_id}")
async def get_task(session: SessionDep, player_building_id: int,
                   player_in: PlayerPublic = Depends(get_current_user), ):
    """返回任务"""
    task = crud_building_task.get_building_task_by_player_building_id(session, player_building_id)
    if not task:
        raise HTTPException(status_code=400, detail=GameRespCode.BUILDING_IDLE.detail)
    return task

@router.get("/claim/{player_building_id}")
async def claim_task(session: SessionDep, player_building_id: int,
                     player_in: PlayerPublic = Depends(get_current_user),
                     ):
    """ 对任务领取 """
    task = crud_building_task.get_building_task_by_player_building_id(session, player_building_id)
    if not task:
        raise HTTPException(status_code=400, detail=GameRespCode.BUILDING_IDLE.detail)
    if task.end_time > datetime.now():
        raise HTTPException(status_code=400, detail=GameRespCode.BUILDING_BUSY.detail)
    else:
        # 任务已经完成，但还没有领取
        try:
            InventoryService.change_resource(session, player_in.id, task.resource_id, task.quantity)
            crud_building_task.remove_building_task(session, task.id)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(e)
            raise HTTPException(status_code=400, detail=str(e))
        return {"msg": "领取成功，库存已经更新"}


@router.post("/cost/{resource_id}", response_model=BuildingTaskBase)
async def get_task_cost(session: SessionDep, task: BuildingTaskBase):
    """ 计算单位生产成本和时间 """
    calculate_task_cost(session, task)
    return task
