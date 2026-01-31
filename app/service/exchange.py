import random
from abc import ABC
from typing import Dict
import json
from app.db.db import engine
from app.db.session import SessionDep
from app.crud import crud_market, crud_inventory, crud_player, crud_resources
from app.dependencies import get_current_user
from app.models import MarketOrder, TransactionActionType, MarketOrderPublic, Player, Inventory, Resource, \
    ExchangeTradeHistory, ResourceSnapshot
from typing import Dict
from abc import ABC, abstractmethod
from sqlmodel import Session, select,func
from app.service.accounting import AccountingService
from app.service.inventory import InventoryService
from app.service.ws import WSServiceBase
from app.service.ws import manager
import logging
from datetime import datetime,timedelta
from app.models import  MarketSnapshot
import numpy as np

logger = logging.getLogger(__name__)


class PriceStrategy(ABC):
    """ 委托单价格 各种定价策略"""

    @abstractmethod
    def calculate_price(self, session: SessionDep, resource_id: int, context: Dict) -> float:
        pass


class MarketAvgFollowerStrategy(PriceStrategy):
    """ 跟随当前市场价格 来定价"""

    def calculate_price(self, session: SessionDep, resource_id: int, context: Dict) -> float:
        price = crud_market.get_resource_market_price(session, resource_id)
        return round(price * (1 + context["fluctuation_margin"]), 2)


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
    random_factor = random.uniform(-0.05, 0.05)
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


def match_order(session: SessionDep, new_order: MarketOrder):
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
        # 如果匹配了，但是发生自我冲突，跳过即可
        if match.player_id == new_order.player_id:
            continue
        my_remaining = new_order.total_quantity - new_order.filled_quantity
        match_remaining = match.total_quantity - match.filled_quantity
        trade_qty = min(my_remaining, match_remaining)

        if trade_qty <= 0: continue

        execute_settlement(session, new_order, match, trade_qty)
        # 4. 更新订单状态
        crud_market.update_order_filled_quantity(session, new_order.id, trade_qty)
        crud_market.update_order_filled_quantity(session, match.id, trade_qty)


def calculate_cpi(session: SessionDep):
    """
    cpi指数
    :param session:
    :return:
    """
    resources = crud_resources.get_resources_all(session)
    weighted_sum = 0.0
    total_weight = 0.0

    for resource in resources:
        # 获取当前市场价（如果没有成交，回退到基准价）
        recent_price = crud_market.get_resource_market_price(session, resource.id)
        current_price = recent_price if recent_price > 0 else resource.base_price

        # 获取权重，确保最小值为 0.001 防止除以 0
        weight = getattr(resource, 'base_weight', 1.0)

        # 计算价格变动率：P_current / P_base
        price_ratio = current_price / resource.base_price

        # 累加加权变动
        weighted_sum += price_ratio * weight
        total_weight += weight

    if total_weight == 0:
        return 1.0  # 默认基准值

    # 最终 CPI = 加权变动总和 / 总权重
    return round(weighted_sum / total_weight, 3) * 100

def get_player_assets_list(session: Session):
    # 1. 子查询：计算每个玩家的库存总价值
    # 注意：这里建议用 Inventory.resource_id 关联 Resource
    inventory_value_stmt = (
        select(
            Inventory.player_id,
            func.sum(Inventory.quantity * Resource.base_price).label("inv_val")
        )
        .where(Inventory.player_id != 0)
        .join(Resource, Inventory.resource_id == Resource.id)
        .group_by(Inventory.player_id)
        .subquery()
    )

    # 2. 主查询：玩家现金 + 库存价值 (使用 coalesce 处理没有库存的玩家)
    statement = (
        select(
            (Player.cash + func.coalesce(inventory_value_stmt.c.inv_val, 0)).label("total_wealth")
        )
        .where(Player.id != 0)
        .outerjoin(inventory_value_stmt, Player.id == inventory_value_stmt.c.player_id)
    )

    # 3. 执行并转换为 Python List
    results = session.exec(statement).all()
    return [float(wealth) for wealth in results]

def calculate_m0(session:SessionDep):
    m0_cash = crud_player.total_cash(session)  # 你已有的：所有玩家口袋里的钱
    return round(m0_cash, 3)

def calculate_m1(session:SessionDep):
    """ 计算m1 """
    m0_cash = crud_player.total_cash(session)  # 你已有的：所有玩家口袋里的钱
    locked_cash = crud_market.total_locked_buy_cash(session)  # 正在买单中锁定的钱
    return round(m0_cash + locked_cash,3)
def calculate_total_assets(session:SessionDep):
    """ 社会总资产： m1 + 仓库价格 """
    total_inventory_value = crud_inventory.get_all_assets_value(session)
    return round(calculate_m1(session) + total_inventory_value, 3)

def calculate_gini(session: SessionDep):
    """ 计算财富gini指数
    资产列表必须包含每个玩家的总资产（资金+库存估值）。
    基尼系数范围 0 (完美平等) 到 1 (完美不平等)。
    """
    assets_list = get_player_assets_list(session)

    # 确保输入是 numpy 数组以便计算
    assets = np.array(assets_list)

    # 排除资产为 0 或负数的异常情况，如果需要可以自行处理
    assets = assets[assets >= 0]
    if len(assets) == 0:
        return 0.0

    # 1. 对资产进行排序（这是最关键的一步）
    sorted_assets = np.sort(assets)
    n = len(sorted_assets)

    # 2. 计算洛伦茨曲线下的面积（梯形法则的简化版）
    # 使用累积和来高效计算面积
    cumulative_assets = np.cumsum(sorted_assets)

    # 3. 应用基尼系数公式
    # 公式: (n + 1 - 2 * sum(i * yi) / sum(yi)) / n
    # 这里的 indices 是 [1, 2, ..., n]
    indices = np.arange(1, n + 1)

    # G = (np.sum(indices * sorted_assets) / np.sum(sorted_assets) - (n + 1) / 2) * (2 / n) # 另一种写法

    # 标准的累积和公式实现（更常见）
    gini = (2 * np.sum(indices * sorted_assets) - (n + 1) * np.sum(sorted_assets)) / (n * np.sum(sorted_assets))

    return round(gini, 3)
def get_cpi_trend(session: Session, current_cpi: float):
    # 查找 24 小时前最接近的一条记录
    one_day_ago = datetime.now() - timedelta(days=1)
    past_snapshot = session.exec(
        select(MarketSnapshot)
        .where(MarketSnapshot.timestamp <= one_day_ago)
        .order_by(MarketSnapshot.timestamp.desc())
    ).first()

    if not past_snapshot or past_snapshot.cpi == 0:
        return 0

    change_rate = (current_cpi - past_snapshot.cpi) / past_snapshot.cpi
    return change_rate
def get_24h_trade_stats(session: Session):
    """
    宏观数据核心：计算过去 24 小时全服交易额，交易订单数, 交易量
    """
    time_threshold = datetime.utcnow() - timedelta(hours=24)
    statement = select(
        func.sum(ExchangeTradeHistory.total_amount).label("total_turnover"),
        func.count(ExchangeTradeHistory.id).label("trade_count"),
        func.sum(ExchangeTradeHistory.quantity).label("total_quantity")
    ).where(ExchangeTradeHistory.created_at >= time_threshold)

    result = session.exec(statement).first()
    return {
        "turnover": round(result[0] or 0.0, 3),
        "volume": result[2] or 0,
        "count": result[1] or 0
    }
def calculate_sector_24h_trade_stats(session: SessionDep):
    # 1. 定义时间窗口（过去24小时）
    one_day_ago = datetime.now() - timedelta(days=1)

    # 2. 构造聚合查询
    # 我们需要：Resource.category (产业链名称), sum(成交额)
    statement = (
        select(
            Resource.industry_id,
            func.sum(ExchangeTradeHistory.price_per_unit * ExchangeTradeHistory.quantity).label("turnover"),
            func.sum(ExchangeTradeHistory.quantity).label("volume")
        )
        .join(ExchangeTradeHistory, Resource.id == ExchangeTradeHistory.resource_id)
        .where(ExchangeTradeHistory.created_at >= one_day_ago)
        .group_by(Resource.industry_id)
    )

    # 3. 执行查询
    results = session.exec(statement).all()
    # 4. 格式化为前端需要的 JSON 列表
    # result 每一行是一个 Row 对象，包含 name 和 volume
    sector_data = [
        {
            "industry_id": row.industry_id,
            "turnover": round(row.turnover, 3) if row.turnover else 0.0,
            "volume": row.volume
        }
        for row in results
    ]
    # 如果没有任何交易，返回空列表防止前端图表报错
    return sector_data

def create_market_snapshot():
    """ 创建市场宏观快照 """
    # 1. 调用你之前写的计算逻辑获取各项指标
    # 这里的函数名需对应你实际定义的逻辑
    with Session(engine) as session:
        current_cpi = calculate_cpi(session)
        m1 = calculate_m1(session)
        total_assets = calculate_total_assets(session)
        gini = calculate_gini(session)  # 记得传入 assets_list
        daily_stat = get_24h_trade_stats(session)
        # 2. 创建快照模型对象
        snapshot = MarketSnapshot(
            timestamp=datetime.now(),
            cpi=current_cpi,
            m1_total=m1,
            total_assets=total_assets,
            gini_index=gini,
            volume=daily_stat['volume'],
            turnover = daily_stat['turnover'],
            order_count=daily_stat['count']
        )

        # 3. 写入数据库
        session.add(snapshot)
        session.commit()
        logger.info(f"[{datetime.now()}] 市场快照已保存")


def calculate_liquidity_score(session: SessionDep, res_id: int):
    """
    计算资源的市场流动性
    """
    # 1. 获取过去24H成交笔数 (反映热度)
    one_day_ago = datetime.now() - timedelta(days=1)
    trade_count = session.exec(
        select(func.count(ExchangeTradeHistory.id))
        .where(ExchangeTradeHistory.resource_id == res_id)
        .where(ExchangeTradeHistory.created_at >= one_day_ago)
    ).first() or 0

    # 2. 获取买卖价差 (反映市场共识)
    min_ask = session.exec(select(func.min(MarketOrder.price_per_unit))
                           .where(MarketOrder.resource_id == res_id, MarketOrder.order_type== "sell")).first()
    max_bid = session.exec(select(func.max(MarketOrder.price_per_unit))
                           .where(MarketOrder.resource_id == res_id, MarketOrder.order_type== "buy")).first()

    spread_ratio = 1.0
    if min_ask and max_bid and min_ask > 0:
        spread_ratio = (min_ask - max_bid) / min_ask  # 价差越小越好

    # 3. 综合评分逻辑 (算法可根据游戏手感调整)
    # 基础分：成交笔数越多分越高 (封顶 60 分)
    score = min(60, trade_count * 2)

    # 修正分：价差越小加分越多 (最高加 40 分)
    if spread_ratio < 0.01:
        score += 40  # 价差在1%以内
    elif spread_ratio < 0.05:
        score += 20  # 价差在5%以内

    return min(100, score)


def get_resource_row(session: SessionDep, res_id: int):
    """ 辅助资源快照 """
    # 1. 获取当前最新成交价
    current_price = session.exec(
        select(ExchangeTradeHistory.price_per_unit)
        .where(ExchangeTradeHistory.resource_id == res_id)
        .order_by(ExchangeTradeHistory.id.desc())
    ).first() or 0.0

    # 2. 获取24小时前的价格 (计算 change)
    one_day_ago = datetime.now() - timedelta(days=1)
    old_price = session.exec(
        select(ResourceSnapshot.price)
        .where(ResourceSnapshot.resource_id == res_id, ResourceSnapshot.timestamp <= one_day_ago)
        .order_by(ResourceSnapshot.timestamp.desc())
    ).first() or current_price

    change = round(((current_price - old_price) / old_price * 100), 2) if old_price > 0 else 0

    # 3. 统计挂单深度 (Ask/Bid)
    ask_v = (session.exec(
        select(func.sum(MarketOrder.total_quantity - MarketOrder.filled_quantity))
        .where(MarketOrder.resource_id == res_id, MarketOrder.order_type == "sell"))
             .first() or 0)
    bid_v = (session.exec(
        select(func.sum(MarketOrder.total_quantity - MarketOrder.filled_quantity))
            .where(MarketOrder.resource_id == res_id, MarketOrder.order_type == "buy"))
             .first() or 0
             )

    # 4. 返回填充 JSON
    return {
        "resource_id": res_id,
        "current_price": current_price,
        "change": change,
        "stock": session.exec(
            select(func.sum(Inventory.quantity)).where(Inventory.resource_id == res_id)).first() or 0,
        "ask_depth": ask_v,
        "bid_depth": bid_v,
        "liquidity": calculate_liquidity_score(session, res_id)  # 自定义评分函数
    }


def get_all_resource_market_snapshot(session: SessionDep):
    """ 所有资源的市场状态 """
    resources  = crud_resources.get_resources_all(session)
    result = []
    for res in resources:
        result.append(get_resource_row(session, res.id))
    return result


def economy_heartbeat_task():
    """
    市场宏观快照和资源微观快照， 定时保存

    :return:
    """
    with Session(engine) as session:
        # --- A. 存宏观快照 ---
        create_market_snapshot()

        # --- B. 存每个资源的微观快照 ---
        all_resources = session.exec(select(Resource)).all()
        for res in all_resources:
            row = get_resource_row(session, res.id)
            snapshot = ResourceSnapshot(
                resource_id=res.id,
                price=row['current_price'],
            )
            session.add(snapshot)
        session.commit()

        logger.info("全服宏观与资源微观快照同步保存完成")

def get_market_history(session: Session):
    """
    获取市场历史快照

    :param session:
    :return:
    """
    snapshots = session.exec(
        select(MarketSnapshot)
        .order_by(MarketSnapshot.timestamp.desc())
        .limit(1000)
    ).all()

    # 翻转回正序（因为 limit 用了 desc）
    snapshots.reverse()

    return {
        "dates": [s.timestamp.isoformat() for s in snapshots],
        "cpi_values": [round(s.cpi, 2) for s in snapshots],
        "volume_values": [round(s.volume, 0) for s in snapshots]
    }


class ExchangeService(WSServiceBase):

    def __init__(self):
        """ username , resource id"""
        self.user_watching_resource: Dict[str, int] = {}

    async def handle(self, user_name, sub_type, data):
        data = json.loads(data)
        logger.info(f"handle : {data}")
        """ 处理到来消息 """
        if sub_type == "switch_resource":
            await self.switch_resource(user_name, data)

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
                "sub_type": "snapshot",
                "data": {
                    "resource_id": res_id,
                    "orders": ret_orders
                }
            })

    async def broadcast_to_resource(self, resource_id: int, msg):
        watchers = [username for username, res_id in self.user_watching_resource.items() if
                    res_id == resource_id]
        logger.info(f"broadcast to {watchers}, {self.user_watching_resource}")
        for name in watchers:
            await manager.send_personal_message(name, msg)


exchange_service = ExchangeService()
