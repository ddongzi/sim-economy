from app.core.error import GameError
from app.db.session import SessionDep
from app.models import Player, TransactionLog,Inventory
from app.crud import crud_inventory
from sqlmodel import select
import logging

from app.service.ws import manager

logger = logging.getLogger(__name__)


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


def get_player_current_inventory_value(session:SessionDep, player_id:int):
    """
    仓库价格，按照基础价
    :param session:
    :param player_id:
    :return:
    """
    return crud_inventory.get_player_all_assets_value(session, player_id)
