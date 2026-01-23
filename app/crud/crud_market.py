from typing import List

from datetime import timedelta
from sqlmodel import Session, select, col,func
from app.models import MarketOrder,ExchangeTradeHistory
from datetime import datetime
from app.db.session import SessionDep


def create_market_order(session: Session, order: MarketOrder) -> MarketOrder:
    """纯插入记录：在数据库中创建一个委托单"""

    session.add(order)
    session.flush()

    return order


def get_order_by_id(session: Session, order_id: int) -> MarketOrder | None:
    """基础查询：通过 ID 获取订单信息"""
    return session.get(MarketOrder, order_id)


def get_active_orders_by_resource(
        session: Session,
        resource_id: int,
        limit: int = 100
):
    """
    获取订单book, 卖单按价格升序 (由低到高)，买单按价格降序 (由高到低)
    """
    statement = select(MarketOrder).where(
        MarketOrder.resource_id == resource_id,
        MarketOrder.status == 0
    ).where(MarketOrder.order_type == "sell").order_by(MarketOrder.price_per_unit.asc())
    asks = session.exec(statement).all()

    statement = select(MarketOrder).where(
        MarketOrder.resource_id == resource_id,
        MarketOrder.status == 0
    ).where(MarketOrder.order_type == "buy").order_by(MarketOrder.price_per_unit.desc())
    bids = session.exec(statement).all()

    return {
        "asks":asks,
        "bids":bids
    }
def get_sell_orders_where_le_price(session: Session,
                                   resource_id: int,
                                   price: float,
                                   ) -> List[MarketOrder] | None:
    """ 获取所有低于某一价格的卖单，按价格升序排列"""
    statement = select(MarketOrder).where(
        MarketOrder.resource_id == resource_id,
        MarketOrder.order_type == "sell",
        MarketOrder.price_per_unit <= price,
        MarketOrder.status == 0,
    ).order_by(MarketOrder.price_per_unit.asc(), MarketOrder.created_at.asc())
    return session.exec(statement).all()

def get_buy_orders_where_ge_price(session: Session,
                                   resource_id: int,
                                   price: float,
                                   ) -> List[MarketOrder] | None:
    """ 获取所有高于某一价格的买单，按价格降序排列"""
    statement = select(MarketOrder).where(
        MarketOrder.resource_id == resource_id,
        MarketOrder.order_type == "buy",
        MarketOrder.price_per_unit >= price,
        MarketOrder.status == 0,
    ).order_by(MarketOrder.price_per_unit.desc(), MarketOrder.created_at.desc())
    return session.exec(statement).all()

def update_order_filled_quantity(
        session: Session,
        order_id: int,
        increment_amount: int
) -> MarketOrder | None:
    """
    进度更新：增加已成交数量。
    如果 filled_quantity >= total_quantity，则自动标记为完成 (status=1)。
    """
    db_order = session.get(MarketOrder, order_id)
    if not db_order:
        return None

    db_order.filled_quantity += increment_amount

    # 状态自动流转逻辑：观察者模式
    if db_order.filled_quantity >= db_order.total_quantity:
        db_order.status = 1  # 标记为已完成

    session.add(db_order)
    return db_order


def set_order_status(session: Session, order_id: int, new_status: int) -> bool:
    """状态修改：如撤单(2)等"""
    db_order = session.get(MarketOrder, order_id)
    if not db_order:
        return False
    db_order.status = new_status
    session.add(db_order)
    session.commit()
    return True


def get_player_orders(session: Session, player_id: int) -> list[MarketOrder]:
    """查询玩家自己的所有委托（包含历史）"""
    statement = select(MarketOrder).where(MarketOrder.player_id == player_id)
    return session.exec(statement.order_by(col(MarketOrder.created_at).desc())).all()

def total_locked_buy_cash(session:SessionDep) ->int:
    """ 交易所中买单锁定的金额 """
    statement = select(func.sum(MarketOrder.price_per_unit * (MarketOrder.total_quantity - MarketOrder.filled_quantity))).where(
        MarketOrder.order_type == "buy",
        MarketOrder.status == 0
    )
    result = session.exec(statement).one()
    return int(result or 0)

def count_active_orders(session: SessionDep):
    """ 挂单总数"""
    return session.exec(select(func.count(MarketOrder.id)).where(
        MarketOrder.status == 0
    )).one()

def create_trade_record(session: Session,
                        seller_id: int,
                        buyer_id: int,
                        resource_id: int,
                        quantity: int,
                        price: float) -> ExchangeTradeHistory:
    """
    创建成交记录（原子操作）
    数学逻辑：total_amount = quantity * price
    """
    total_amount = quantity * price
    db_trade = ExchangeTradeHistory(
        seller_id=seller_id,
        buyer_id=buyer_id,
        resource_id=resource_id,
        quantity=quantity,
        price_per_unit=price,
        total_amount=total_amount,
        created_at=datetime.utcnow()
    )
    session.add(db_trade)
    return db_trade


def get_recent_trades_by_resource(session: Session, resource_id: int, limit: int = 20):
    """
    获取某个资源的最近成交（用于前端“最新成交”列表展示）
    """
    statement = select(ExchangeTradeHistory).where(
        ExchangeTradeHistory.resource_id == resource_id
    ).order_by(ExchangeTradeHistory.created_at.desc()).limit(limit)
    return session.exec(statement).all()


def get_24h_volume_stats(session: Session):
    """
    宏观数据核心：计算过去 24 小时全服总成交额和总订单数
    """
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    statement = select(
        func.sum(ExchangeTradeHistory.total_amount).label("total_volume"),
        func.count(ExchangeTradeHistory.id).label("trade_count")
    ).where(ExchangeTradeHistory.created_at >= time_threshold)

    result = session.exec(statement).first()
    return {
        "volume": result[0] or 0.0,
        "count": result[1] or 0
    }
def get_resource_market_lowest_sell_order(session: Session, resource_id: int) -> MarketOrder:
    """ 最低卖价 """
    statement = select(MarketOrder).where(
        MarketOrder.resource_id ==resource_id,
        MarketOrder.order_type=="sell",
        MarketOrder.status == 0
    ).order_by(MarketOrder.price_per_unit.asc()).limit(1) # 价格从低到高
    return session.exec(statement).one_or_none()

def get_resource_market_highest_buy_order(session: Session, resource_id: int) -> MarketOrder:
    """ 最高买价 """
    statement = select(MarketOrder).where(
        MarketOrder.resource_id ==resource_id,
        MarketOrder.order_type=="buy",
        MarketOrder.status == 0
    ).order_by(MarketOrder.price_per_unit.desc()).limit(1) # 价格从低到高
    return session.exec(statement).one_or_none()

def get_resource_market_price(session: Session, resource_id: int) -> float:
    """
    计算资源当前“市场价”（取最近 5 笔成交的加权平均价）
    数学逻辑：Σ(price * qty) / Σ(qty)
    """
    statement = select(ExchangeTradeHistory).where(
        ExchangeTradeHistory.resource_id == resource_id
    ).order_by(ExchangeTradeHistory.created_at.desc()).limit(5)

    trades = session.exec(statement).all()
    if not trades:
        return 0.0

    total_q = sum(t.quantity for t in trades)
    total_v = sum(t.total_amount for t in trades)
    return total_v / total_q if total_q > 0 else 0.0

def get_24h_avg_price(session: Session, resource_id: int) -> float:
    """ 获取资源的 24h均价"""
    pass