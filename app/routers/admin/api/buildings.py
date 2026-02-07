from fastapi import APIRouter, HTTPException, Query
from typing import List,Optional
from datetime import datetime
from app.db.session import SessionDep
from app.models import BuildingMeta, BuildingMetaPublic, BuildingMetaCreate

from app.crud.crud_building import get_building_meta_by_id, create_building_meta, get_all_building_metas, \
    get_building_meta_by_name

router = APIRouter()

# --- 3. 元数据维护：新增 ---
@router.post("/metas", response_model=BuildingMetaPublic)
async def admin_create_meta(payload: BuildingMetaCreate, session: SessionDep):

    if get_building_meta_by_name(session, payload.name):
        raise HTTPException(status_code=400, detail="建筑  已存在")

    return create_building_meta(session, payload)

@router.get("/metas", response_model=List[BuildingMetaPublic])
async def admin_get_buildings(
        session: SessionDep,
):
     return get_all_building_metas(session)