from app.crud import crud_player
from app.service.ws import WSServiceBase,manager
import json
import logging
logger = logging.getLogger(__name__)
class PlayerService(WSServiceBase):
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

playerService = PlayerService()
manager.register("player", playerService)
