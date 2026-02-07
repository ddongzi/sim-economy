from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from sqlmodel import Session,select

from app.core.config import GOVERNMENT_PLAYER_ID
from app.db.session import SessionDep  # 假设你的 session 依赖项位置
from app.crud import crud_player,crud_market,crud_inventory
from app.dependencies import create_access_token, get_current_user
from datetime import datetime

from app.models import SpotContract, GovernmentOrder, GovernmentActionLog
from app.service.ExchangeService import calculate_cpi, calculate_gini, get_cpi_trend, calculate_m1, calculate_total_assets, \
    calculate_m0, get_all_resource_market_snapshot, get_market_history, \
    calculate_sector_24h_trade_stats, get_24h_trade_stats
import logging
logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/economy", tags=["economy"])
def economic(session: SessionDep):
    """
    经济指标
    """
    # 1. 货币维度
    m0_cash = crud_player.total_cash(session)  # 你已有的：所有玩家口袋里的钱
    locked_cash = crud_market.total_locked_buy_cash(session)  # 正在买单中锁定的钱

    # 2. 市场活跃维度
    daily_volume = get_24h_trade_stats(session)  # 过去24小时成交总额

    # 3. 生产力维度 (社会总财富估计)
    # 所有 Inventory 数量 * 该资源基础价格/市场均价
    total_inventory_value = crud_inventory.get_all_assets_value(session)

    #
    cpi = calculate_cpi(session)
    velocity_val = round(daily_volume['turnover'] / (m0_cash + locked_cash + total_inventory_value), 2)

    # 政府公开
    cash = crud_player.get_player_by_id(session, GOVERNMENT_PLAYER_ID).cash
    inventoy = crud_inventory.get_player_inventory(session, GOVERNMENT_PLAYER_ID)
    current_policy = session.exec(
        select(GovernmentActionLog).where(GovernmentActionLog.is_active == True)
    ).first()

    # 2. 查【审计日志】：给下方那个滚动列表
    history_logs = session.exec(
        select(GovernmentActionLog).order_by(GovernmentActionLog.created_at.desc()).limit(10)
    ).all()

    government_orders = session.exec(
        select(GovernmentOrder).where(GovernmentOrder.status == 0)
    ).all()

    government = {
        "cash":cash,
        "inventory":inventoy,
        "current_policy":current_policy,
        "history": history_logs,
        "orders": government_orders
    }

    return {
        "m0": calculate_m0(session),
        "m1": calculate_m1(session),
        "market_24h": get_24h_trade_stats(session),
        "total_assets_value": calculate_total_assets(session),
        "cpi": cpi,  # 物价指数
        "cpi_trend": get_cpi_trend(session, cpi),
        "gini": calculate_gini(session),
        "velocity_val": velocity_val, # 24h流转速率
        "timestamp": datetime.utcnow(),
        "history": get_market_history(session),
        "sectors": calculate_sector_24h_trade_stats(session),
        "resources": get_all_resource_market_snapshot(session),
        "government": government
    }

