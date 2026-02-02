import logging

from fastapi import APIRouter, Depends, HTTPException
from app.db.session import SessionDep
from app.dependencies import get_current_user

from app.crud import crud_inventory, crud_market, crud_resources, crud_player
from app.models import MarketOrder, MarketOrderCreate, PlayerPublic, MarketOrderPublic, TransactionActionType
from app.core.error import GameError
from app.service import AccountingService, ExchangeService, PlayerService, InventoryService
import asyncio
from app.service.ws import manager

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/order")
async def create_market_order(session: SessionDep, order_in: MarketOrderCreate,
                              player_in: PlayerPublic = Depends(get_current_user)):
    """ 提交委托订单 """
    try:
        resource = crud_resources.get_resource(session, order_in.resource_id)
        # 涨跌停设置
        min_price = resource.base_price * 0.5
        max_price = resource.base_price * 2.0

        if order_in.price_per_unit > max_price:
            raise HTTPException(status_code=400, detail=f"价格超出涨停价: {max_price}")

        if order_in.price_per_unit < min_price:
            raise HTTPException(status_code=400, detail=f"价格低于跌停价: {min_price}")

        order = MarketOrder(
            **order_in.model_dump()
        )

        order.player_id = player_in.id
        order.total_quantity = order_in.quantity
        order.filled_quantity = 0
        order.status = 0
        crud_market.create_market_order(session, order)

        # 如果是卖单，检查扣除库存
        if order_in.order_type == "sell":
            InventoryService.change_resource(session, player_in.id, order_in.resource_id, -order_in.quantity)
        # 如果是买单，检查扣除资金
        if order_in.order_type == "buy":
            total_cost = order_in.quantity * order_in.price_per_unit
            AccountingService.change_cash(session, player_in.id, -total_cost,
                                          TransactionActionType.MARKET_BUY, order.id)
        # 撮合订单
        ExchangeService.match_order(session, order)
        session.commit()

        player = crud_player.get_player_by_id(session, player_in.id)
        await PlayerService.playerWs.send_update_cash(player.name, player.cash)

        # 撮合完成后，调用广播
        # 这个 broadcast 不在 websocket 循环里，而是在业务逻辑里
        new_orders = crud_market.get_active_orders_by_resource(session, order.resource_id)
        ret_orders = {
            'asks': [],
            'bids': []
        }
        for o in new_orders['asks']:
            op = o.model_dump()
            op['quantity'] = o.total_quantity - o.filled_quantity
            op = MarketOrderPublic.model_validate(op)
            ret_orders['asks'].append(op.model_dump(mode="json"))
        for o in new_orders['bids']:
            op = o.model_dump()
            op['quantity'] = o.total_quantity - o.filled_quantity
            op = MarketOrderPublic.model_validate(op)
            op.quantity = o.total_quantity - o.filled_quantity
            ret_orders['bids'].append(op.model_dump(mode="json"))
        logger.info("Match ok. will ws broadcast")
        await ExchangeService.exchangeWs.broadcast_to_resource(order.resource_id, {
            "type": "exchange",
            "sub_type":"update",
            "data": {
                "resource_id": order.resource_id,
                "orders": ret_orders
            }
        })

    except GameError as e:
        logger.error(f"create market order failed. {e}")
        raise HTTPException(status_code=400, detail=e.message)
    except Exception as e:
        logger.exception(f"create market order failed. {e}")
        raise HTTPException(status_code=500, detail="内部错误")
    return {"msg": "订单创建成功"}


@router.get("/orders")
async def get_orders(session: SessionDep, resource_id: int,
                     player_in: PlayerPublic = Depends(get_current_user)):
    return crud_market.get_active_orders_by_resource(session, resource_id)


@router.get("/price_suggestion/{resource_id}")
async def get_suggested_price(session: SessionDep, resource_id: int,
                              strategy_name: str | None = None,
                              player_in: PlayerPublic = Depends(get_current_user)):
    price = ExchangeService.calculate_price_per_unit(session, resource_id, strategy_name)
    return {"suggest_price": price}


@router.get("/simple/{resource_id}")
async def get_market_price(session: SessionDep, resource_id: int,
                           player_in: PlayerPublic = Depends(get_current_user)):
    """ 获取资源最近市价(已成交均价)， 最低卖单/最高买单 """
    lowest_sell_order = crud_market.get_resource_market_lowest_sell_order(session, resource_id)
    if lowest_sell_order:
        lowest_sell_order = MarketOrderPublic(**lowest_sell_order.model_dump(),
                                              quantity=lowest_sell_order.total_quantity - lowest_sell_order.filled_quantity)
    highest_buy_order = crud_market.get_resource_market_highest_buy_order(session, resource_id)
    if highest_buy_order:
        highest_buy_order = MarketOrderPublic(**highest_buy_order.model_dump(),
                                              quantity=highest_buy_order.total_quantity - highest_buy_order.filled_quantity)
    market_price = crud_market.get_resource_market_price(session, resource_id)
    resource = crud_resources.get_resource(session, resource_id)
    if market_price == 0:
        market_price = resource.base_price
    return {
        "base_price": resource.base_price,
        "market_price": round(market_price, 3),
        "lowest_sell_order": lowest_sell_order,
        "highest_buy_order": highest_buy_order
    }
