from app.models import Inventory,Resource  # 确保路径正确
from app.db.session import SessionDep
from sqlmodel import  select,func

def get_player_inventory(session: SessionDep, player_id: int) -> list[Inventory]:
    """获取玩家所有库存"""
    statement = select(Inventory).where(Inventory.player_id == player_id)
    return session.exec(statement).all()
def get_player_inventory_resource(session: SessionDep, player_id: int, resource_id:int) -> Inventory:
    """获取玩家某个资源库存"""
    statement = select(Inventory).where(
        Inventory.player_id == player_id,
        Inventory.resource_id == resource_id
    )
    return session.exec(statement).one_or_none()


def add_resource(session: SessionDep, player_id: int, resource_id: int, amount: int) -> Inventory:
    """
    增加资源入库 (惰性结算时调用)
    """
    # 1. 查找现有库存记录
    statement = select(Inventory).where(
        Inventory.player_id == player_id,
        Inventory.resource_id == resource_id
    )
    db_inventory = session.exec(statement).first()

    if db_inventory:
        # 2. 存在则累加数量 (数学中的 a = a + b)
        db_inventory.quantity += amount
    else:
        # 3. 不存在则新建一条记录
        db_inventory = Inventory(
            player_id=player_id,
            resource_id=resource_id,
            quantity=amount
        )
        session.add(db_inventory)

    return db_inventory


def consume_resource(session: SessionDep, player_id: int, resource_id: int, amount: int) -> bool:
    """
    消耗资源 (开始生产时调用)
    返回布尔值，表示是否消耗成功
    """
    statement = select(Inventory).where(
        Inventory.player_id == player_id,
        Inventory.resource_id == resource_id
    )
    db_inventory = session.exec(statement).first()

    if not db_inventory or db_inventory.quantity < amount:
        print("# 库存不足，判定失败 ")
        return False

    db_inventory.quantity -= amount
    return True

def get_all_assets_value(session: SessionDep):
    """ 仓库内资源总价值，以base_price计算"""
    statement = select(func.sum(Inventory.quantity * Resource.base_price)
                       ).join(Resource, Inventory.resource_id == Resource.id).where(Inventory.player_id != 0)
    result = session.exec(statement).one()
    return int(result or 0)