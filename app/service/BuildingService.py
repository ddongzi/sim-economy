from app.core.config import APP_CONFIG
from app.crud import crud_building
from app.db.db import engine
from app.db.session import SessionDep
from sqlmodel import Session,select

def get_player_current_building_value(session:SessionDep,
        player_id:int):
    """ 获取玩家建筑物估值 """
    result = 0
    player_buildings = crud_building.get_player_buildings(session, player_id)
    for pb in player_buildings:
        result += pb.building_meta.building_cost* float(APP_CONFIG['build_deconstruct_rate'])
    return result