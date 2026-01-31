from app.core.error import GameError
from app.db.session import SessionDep
from app.models import Player, TransactionLog,Inventory
from sqlmodel import select
import logging

from app.service.ws import manager

logger = logging.getLogger(__name__)
class InventoryService:
    """ 库存 """

    @staticmethod
    def change_resource(session:SessionDep, player_id:int,resource_id: int, quantity:int):
        """ 改变库存 """
        statement = select(Inventory).where(
            Inventory.player_id == player_id,
            Inventory.resource_id == resource_id
        )
        db_inventory = session.exec(statement).first()

        if not db_inventory:
            db_inventory = Inventory(
                player_id=player_id,
                resource_id=resource_id,
                quantity=quantity
            )
            session.add(db_inventory)

        db_inventory.quantity += quantity

        if db_inventory.quantity < 0:

            raise GameError(f"库存资源不足 {resource_id}, change:{quantity}, after:{db_inventory.quantity}" )

        session.add(db_inventory)
        session.flush()

    async def send_notify(self, message: str):
        """ 库存更新通知 """

        pass

inventory_service = InventoryService()
manager.register("inventory", inventory_service)