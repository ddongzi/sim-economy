from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import defer

from app.core.error import GameRespCode
from app.db.session import SessionDep
from app.dependencies import get_current_user
from datetime import datetime, timedelta
from app.crud import crud_building_task, crud_inventory, crud_player, crud_recipe
from app.logic.task import calculate_task_cost
from app.models import PlayerPublic, BuildingTaskCreate, BuildingTaskBase
from app.service.inventory import InventoryService

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
    calculate_task_cost(session, building_task)

    recipe = crud_recipe.get_recipe_by_output_resource_id(session, building_task.resource_id)
    if not recipe:
        raise HTTPException(status_code=400, detail="异常：找不到配方信息")
    hours = building_task.quantity / recipe.per_hour

    # 创建任务
    crud_building_task.create_building_task(session, building_task, player_id=player_in.id, duration=hours)
    # 扣除成本
    crud_player.deduct_cash(session, player_in.id, cash=building_task.cash_cost)
    # 扣除库存？？
    for input in recipe.inputs:
        InventoryService.change_resource(session, player_in.id, input.resource_id,
                                        -input.quantity * building_task.quantity)
    session.commit()
    return {"msg": "建筑任务创建成功"}


@router.get("/{player_building_id}")
async def get_task(session: SessionDep, player_building_id: int,
                   player_in: PlayerPublic = Depends(get_current_user), ):
    """返回任务, 如果已完成则返回None。"""
    task = crud_building_task.get_building_task_by_player_building_id(session, player_building_id)
    if not task:
        raise HTTPException(status_code=400, detail= GameRespCode.BUILDING_IDLE.detail)
    if task.end_time < datetime.now():
        # 加入仓库，删除任务
        InventoryService.change_resource(session, player_in.id, task.resource_id, task.quantity)
        crud_building_task.remove_building_task(session, task.id)
        raise HTTPException(status_code=400, detail= GameRespCode.TASK_STALE.detail)
    return task


@router.get("/claim/{player_building_id}")
async def claim_task(session: SessionDep, player_building_id: int,
                     player_in: PlayerPublic = Depends(get_current_user),
                     ):
    """ 对任务领取 """
    task = crud_building_task.get_building_task_by_player_building_id(session, player_building_id)
    if not task:
        return {"msg": "建筑没有任务"}
    if task.end_time > datetime.now():
        return {"msg": "任务在进行中"}
    else:
        # 任务已经完成，但还没有领取
        InventoryService.change_resource(session, player_in.id, task.resource_id, task.quantity)
        crud_building_task.remove_building_task(session, task.id)
        return {"msg": "领取成功，库存已经更新"}


@router.post("/cost/{resource_id}", response_model=BuildingTaskBase)
async def get_task_cost(session: SessionDep, task: BuildingTaskBase):
    """ 计算单位生产成本和时间 """
    calculate_task_cost(session, task)
    return task
