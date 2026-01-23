from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlmodel import Session
from app.db.session import SessionDep  # 假设你的 session 依赖项位置
from app.crud import crud_player,crud_market,crud_inventory
from app.dependencies import create_access_token, get_current_user
from datetime import datetime
from app.service.exchange import calculate_cpi
router = APIRouter()

@router.get("/economy", tags=["economy"])
def economic(session: SessionDep):
    """
    全服宏观经济快照
    数学逻辑：
    M0 = 流通现金
    M1 = M0 + 挂单锁定
    """
    # 1. 货币维度
    m0_cash = crud_player.total_cash(session)  # 你已有的：所有玩家口袋里的钱
    locked_cash = crud_market.total_locked_buy_cash(session)  # 正在买单中锁定的钱

    # 2. 市场活跃维度
    daily_volume = crud_market.get_24h_volume_stats(session)  # 过去24小时成交总额
    active_orders_count = crud_market.count_active_orders(session)  # 挂单总数

    # 3. 生产力维度 (社会总财富估计)
    # 计算逻辑：所有 Inventory 数量 * 该资源基础价格/市场均价
    total_inventory_value = crud_inventory.get_all_assets_value(session)

    return {
        "m0": m0_cash,
        "m1": m0_cash + locked_cash,
        "market_volume_24h": daily_volume,
        "active_orders": active_orders_count,
        "total_assets_value": total_inventory_value,
        "cpi": calculate_cpi(session),  # 物价指数
        "timestamp": datetime.utcnow(),
        "history": {
            "dates": ["01-10", "01-11", "01-12", "01-13"],
            "cpi_values": [100.2, 101.5, 103.1, 104.2],
            "volume_values": [8000, 11000, 9500, 12500]
        },
        "sectors": [
            {"name": "电力", "volume": 5000},
            {"name": "矿产", "volume": 3500}
        ],
        "resources": [
            {"name": "电力", "current_price": 0.52, "change": 2.4, "stock": 50000, "ask_depth": 120, "bid_depth": 85,
             "liquidity": 82}
        ]
    }