import random
from abc import ABC
from typing import Dict
import json
from app.db.db import engine
from app.db.session import SessionDep
from app.crud import crud_market,crud_inventory,crud_player,crud_resources
from app.models import MarketOrder, TransactionActionType, MarketOrderPublic
from typing import Dict
from abc import ABC, abstractmethod
from sqlmodel import  Session
from app.service.accounting import AccountingService
from app.service.inventory import InventoryService
from app.service.ws import WSServiceBase
from app.service.ws import manager
import logging
logger = logging.getLogger(__name__)

class PriceStrategy(ABC):
    """ 委托单价格 各种定价策略"""
    @abstractmethod
    def calculate_price(self, session: SessionDep, resource_id: int, context: Dict)->float:
        pass
class MarketAvgFollowerStrategy(PriceStrategy):
    """ 跟随当前市场价格 来定价"""
    def calculate_price(self, session: SessionDep, resource_id: int, context: Dict)->float:
        price = crud_market.get_resource_market_price(session, resource_id)
        return round(price * (1 + context["fluctuation_margin"]),2)

def calculate_price_per_unit(
        session: SessionDep,
        resource_id: int,
        strategy_name: str = "market_avg_follower",
        context: Dict = None
) -> float:
    """
    根据指定的定价策略，返回价格
    """
    # 市场价格策略：上下浮5%之间比例
    random_factor =random.uniform(-0.05, 0.05)
    context = {"fluctuation_margin": random_factor}
    return MarketAvgFollowerStrategy().calculate_price(session, resource_id, context or {})


def execute_settlement(session: SessionDep, order_a: MarketOrder, order_b: MarketOrder, qty: int):
    """ 处理订单结算：货物金钱转移 """
    sell_order = order_a if order_a.order_type == "sell" else order_b
    buy_order = order_b if order_b.order_type == "buy" else order_a

    strike_price = order_b.price_per_unit
    total_cash = qty * strike_price
    # 给买家增加货物
    InventoryService.change_resource(session, buy_order.player_id, buy_order.resource_id, qty)
    # 给卖家增加金钱
    AccountingService.change_cash(session, sell_order.player_id, total_cash,
                                  TransactionActionType.MARKET_SELL,
                                  sell_order.id)

    # 买家挂单价大于成交价，退回差价
    if buy_order.price_per_unit > strike_price:
        refund = qty * (buy_order.price_per_unit - strike_price)
        AccountingService.change_cash(session, buy_order.player_id, refund,
                                      TransactionActionType.MARKET_REFUND,
                                      buy_order.id)

    crud_market.create_trade_record(session, sell_order.player_id,
                                    buy_order.player_id,
                                    order_b.resource_id,
                                    quantity=qty,
                                    price=strike_price
                                    )





def refund_marker_order(session, order: MarketOrder):
    """ 某种原因：比如撮合冲突。 需要回退资源和金钱 """
    if order.order_type == "buy":
        remaining_qty = order.total_quantity - order.filled_quantity
        refund_cash = remaining_qty * order.price_per_unit
        AccountingService.change_cash(session, order.player_id, refund_cash,
                                      TransactionActionType.MATCH_CONFLICT_REFUND, order.id)
    if order.order_type == "sell":
        remaining_qty = order.total_quantity - order.filled_quantity
        InventoryService.change_resource(session, order.player_id, order.resource_id, remaining_qty)
    print("refund market order !")

def match_order(session:SessionDep,new_order: MarketOrder):
    """ 在每次创建订单后执行 """
    potential_matches = []
    if new_order.order_type == "buy":
        potential_matches = crud_market.get_sell_orders_where_le_price(session, new_order.resource_id,
                                                                       new_order.price_per_unit,
                                                                       )
    if new_order.order_type == "sell":
        potential_matches = crud_market.get_buy_orders_where_ge_price(session, new_order.resource_id,
                                                                      new_order.price_per_unit,
                                                                      )
    for match in potential_matches:
        if new_order.status != 0: break;
        my_remaining = new_order.total_quantity - new_order.filled_quantity
        match_remaining = match.total_quantity - match.filled_quantity
        trade_qty = min(my_remaining, match_remaining)

        if trade_qty <= 0: continue

        # 如果匹配了，但是发生自冲突，应该取消该订单，即标记订单状态为取消
        if match.player_id == new_order.player_id:
            new_order.status = 2
            refund_marker_order(session, new_order)
            break

        execute_settlement(session, new_order, match, trade_qty)
        # 4. 更新订单状态
        crud_market.update_order_filled_quantity(session,new_order.id, trade_qty)
        crud_market.update_order_filled_quantity(session,match.id, trade_qty)

def calculate_cpi(session:SessionDep):
    """计算cpi物价指数"""
    resources = crud_resources.get_resources_all(session)
    current_market_total = 0.0
    base_market_total = 0.0
    for resource in resources:
        recent_price = crud_market.get_resource_market_price(session, resource.id)
        current_price = resource.base_price
        if recent_price != 0:
            current_price = recent_price
        weight = getattr(resource, 'weight', 1.0)
        current_market_total += current_price * weight
        base_market_total += resource.base_price * weight
    # 4. 计算指数 (基准值为 100)
    if base_market_total == 0:
        return 100.0

    cpi = (current_market_total / base_market_total) * 100
    return round(cpi, 2)

class ExchangeService(WSServiceBase):

    def __init__(self):
        """ username , resource id"""
        self.user_watching_resource: Dict[str, int] = {}

    async def handle(self, user_name, sub_type, data):
        data = json.loads(data)
        logger.info(f"handle : {data}")
        """ 处理到来消息 """
        if sub_type == "switch_resource":
            await self.switch_resource(user_name,data)

    def set_watching_resource(self, user_name: str, resource_id: int):
        """设置当前监督的资源（直接覆盖旧值）"""
        self.user_watching_resource[user_name] = resource_id
        logging.info(f"玩家 {user_name} 切换监督资源至: {resource_id}")

    async def switch_resource(self, user_name: str, data):
        res_id = data["resource_id"]
        # 1. 记录该连接正在看这个 res_id
        self.set_watching_resource(user_name, resource_id=res_id)

        # 2. 切换瞬间，只给【当前这一个连接】发一份初始数据（Snapshot）
        with Session(engine) as session:
            orders = crud_market.get_active_orders_by_resource(session, res_id)
            ret_orders = {
                'asks': [],
                'bids': []
            }
            for o in orders['asks']:
                op = o.model_dump()
                op['quantity'] = o.total_quantity - o.filled_quantity
                op = MarketOrderPublic.model_validate(op)
                ret_orders['asks'].append(op.model_dump(mode="json"))
            for o in orders['bids']:
                op = o.model_dump()
                op['quantity'] = o.total_quantity - o.filled_quantity
                op = MarketOrderPublic.model_validate(op)
                op.quantity = o.total_quantity - o.filled_quantity
                ret_orders['bids'].append(op.model_dump(mode="json"))

            await manager.send_personal_message(user_name, {
                "type": "exchange",
                "subtype": "snapshot",
                "data": {
                    "resource_id": res_id,
                    "orders": ret_orders
                }
            })

    async def broadcast_to_resource(self, resource_id:int, msg):
        watchers = [username for username, res_id in self.user_watching_resource.items() if
                    res_id == resource_id]
        logger.info(f"broadcast to {watchers}, {self.user_watching_resource}")
        for name in watchers:
            await manager.send_personal_message(name, msg)
exchange_service = ExchangeService()
