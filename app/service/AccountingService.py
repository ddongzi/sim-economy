from app.core.error import GameError
from app.db.session import SessionDep
from app.models import Player, TransactionLog, LedgerLogFull, TransactionActionType
from sqlmodel import select,func

def change_cash(
        session:SessionDep,
        player_id:int,
        amount:float,
        action_type:int,
        ref_id:int
):
    # 锁定行
    statement = select(Player).where(Player.id == player_id).with_for_update()
    player = session.exec(statement).one_or_none()

    if not player:
        raise ValueError("player 异常")
    amount = round(amount, 3)

    before = player.cash
    after = player.cash + amount
    if after < 0:
        raise GameError(f"player 资金不足 after:{after} change:{amount}")
    player.cash += amount

    log = TransactionLog(
        player_id=player_id,
        action_type=action_type,
        change_amount=amount,
        before_balance=before,
        after_balance=after,
        ref_id=ref_id,
    )
    session.add(log)
    session.add(player)

    # Warn: 不执行commit， 外部事务提交

def get_all_ledger(session:SessionDep, player_id:int,
                   page: int = 1,
                   page_size: int = 10,
                   ledger_type:int = None,
                   ):
    """
    # 获取所有的流水， 并且展开
    :param ledger_type:
    :param session:
    :param player_id:
    :param page:
    :param page_size:
    :return:
    """
    skip = (page - 1) * page_size

    logs = session.exec(
        select(TransactionLog).where(TransactionLog.player_id == player_id).offset(skip).limit(page_size)
        .order_by(TransactionLog.created_at.desc())
    ).all()

    result = []

    # 获取总数
    count_statement = (select(func.count()).select_from(TransactionLog)
                       .where(TransactionLog.player_id == player_id)
                       )
    total = session.exec(count_statement).one()

    for log in logs:
        ledger = LedgerLogFull(
            time = log.created_at,
            type = log.action_type,
            type_display = TransactionActionType(log.action_type).name,
            description="流水描述",
            change=round(log.change_amount, 3),
            balance_after=round(log.after_balance, 3),
        )
        result.append(ledger)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": result
    }

