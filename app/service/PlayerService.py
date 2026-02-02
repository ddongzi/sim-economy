from app.crud import crud_player
from app.models import PlayerEconomySnapshot, Player
from app.service import InventoryService
from app.service.ws import WSServiceBase,manager
from app.service import BuildingService
import json
import logging
from app.db.db import engine
from app.db.session import SessionDep
from sqlmodel import Session,select
logger = logging.getLogger(__name__)
from datetime import datetime
class PlayerWS(WSServiceBase):
    @classmethod
    async def handle(cls, user_name, sub_type, data):
        data = json.loads(data)
        pass
    async def send_update_cash(self,player_name:str, cash:float):
        await manager.send_personal_message(player_name, {
            "type": "player",
            "sub_type": "update_cash",
            "data": {
                "cash": cash
            }
        })


def get_history_curve(session:SessionDep, player_id:int):
    # 1. 从快照表取过去 6 天的数据
    historical_data = session.exec(select(PlayerEconomySnapshot)
                                   .where(PlayerEconomySnapshot.player_id == player_id)
                                   .limit(6)
                                   ).all()
    player = session.get(Player, player_id)

    # 2. 从实时数据表取“今天”的数据 (确保图表终点是实时的)
    current_cash = player.cash
    current_build = BuildingService.get_player_current_building_value(session, player_id)
    current_stock = InventoryService.get_player_current_inventory_value(session, player_id)

    # 3. 合并成你给出的 JSON 结构
    return {
        "labels": [d.snap_time for d in historical_data] + [datetime.now().isoformat()],
        "datasets": [
            {"name": "现金", "values": [d.cash for d in historical_data] + [current_cash]},
            {"name": "建筑估值", "values": [d.building_valuation for d in historical_data] + [current_build]},
            {"name": "仓库估值", "values": [d.warehouse_valuation for d in historical_data] + [current_stock]},
        ]
    }

def create_player_economy_snapshot(player_id:int):
    """
    用户经济快照，login时候记录； 访问个人economy时候也记录

    :param player_id:
    :return:
    """
    with Session(engine) as session:
        player = session.get(Player, player_id)
        # 2. 从实时数据表取“今天”的数据 (确保图表终点是实时的)
        current_cash = player.cash
        current_build = BuildingService.get_player_current_building_value(session, player_id)
        current_stock = InventoryService.get_player_current_inventory_value(session, player_id)
        shot = PlayerEconomySnapshot(
            player_id=player_id,
            cash=current_cash,
            building_valuation=current_build,
            warehouse_valuation=current_stock,
        )
        session.add(shot)
        session.commit()


playerWs = PlayerWS()
manager.register("player", playerWs)
