from typing import List

from fastapi import APIRouter, Depends, HTTPException
from app.crud.crud_recipe import get_recipes
from app.db.session import SessionDep
from app.dependencies import get_current_user
from datetime import datetime, timedelta
from app.crud import crud_building_task, crud_inventory
from app.models import PlayerPublic, InventoryPublic

router = APIRouter()


@router.get("/", response_model=List[InventoryPublic])
async def get_inventory(session: SessionDep,
                        player_in: PlayerPublic = Depends(get_current_user)):
    """获取用户库存"""
    return crud_inventory.get_player_inventory(session, player_in.id)


@router.get("/{resource_id}", response_model=InventoryPublic)
async def get_inventory(session: SessionDep,
                        resource_id: int,
                        player_in: PlayerPublic = Depends(get_current_user)):
    """获取用户库存"""
    inventory = crud_inventory.get_player_inventory_resource(session, player_in.id, resource_id)
    if not inventory:
        return InventoryPublic(
            resource_id=resource_id,
            quantity=0
        )
    return inventory
