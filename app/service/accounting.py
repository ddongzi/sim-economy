from app.core.error import GameError
from app.db.session import SessionDep
from app.models import Player, TransactionLog
from sqlmodel import select

class AccountingService:
    """ 金额变动 """
    @staticmethod
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
