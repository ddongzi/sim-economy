from fastapi import  APIRouter,HTTPException,Query
from app.crud import crud_player
from app.db.session import SessionDep
from app.models import Player, PlayerPublic, PlayerCreate, TransactionLog, TransactionActionType
from sqlmodel import select,func

router = APIRouter()

@router.get("/")
async def get_accounting_logs_all(
    session: SessionDep,
    page: int = 1,
    size: int = 10,
    action: int = None
):
    # 1. 基础查询逻辑（用于复用）
    base_query = select(TransactionLog)
    if action:
        base_query = base_query.where(TransactionLog.action_type == action)

    # 2. 计算过滤后的总数
    # 使用 select_from 确保 count 的是过滤后的集合
    total_statement = select(func.count()).select_from(base_query.subquery())
    total = session.exec(total_statement).one()

    # 3. 执行分页查询
    offset = (page - 1) * size
    # 增加明确的排序，防止翻页数据重复
    items_statement = base_query.order_by(TransactionLog.created_at.desc()).offset(offset).limit(size)
    items = session.exec(items_statement).all()

    return {
        "total": total,
        "page": page,
        "size": size,
        "items": items
    }


@router.get("/stats")
async def get_accounting_stats(session:SessionDep):
    # 1. 按 action_type 分组汇总流水
    stats_query = select(
        TransactionLog.action_type,
        func.sum(TransactionLog.change_amount).label("total")
    ).group_by(TransactionLog.action_type)

    results = session.exec(stats_query).all()
    # 转化为字典格式方便前端使用: {1: -500.0, 2: 1200.0, ...}
    stat_map = {row.action_type: row.total for row in results}
    # 2. 获取玩家表的实时余额总和 (用于对比验证)
    actual_player_cash = session.exec(select(func.sum(Player.cash))).one() or 0
    # 3. 计算对账偏差
    # 流水计算出的总余额 (所有正负流水的代数和)
    computed_balance = sum(stat_map.values())
    delta = computed_balance - actual_player_cash

    return {
        "inflow": {
            "build": abs(stat_map.get(str(TransactionActionType.BUILD_REVENUE), 0))
        },
        "outflow": {
            "produce": abs(stat_map.get(str(TransactionActionType.PRODUCE_COST), 0)),
            "build": abs(stat_map.get(str(TransactionActionType.BUILD_COST), 0)),
        },
        "audit": {
            "player_cash_actual": actual_player_cash,
            "computed_balance": computed_balance,
            "delta": delta
        }
    }