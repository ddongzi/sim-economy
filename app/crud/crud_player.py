from typing import List, Optional
from sqlmodel import select, func
from app.db.session import SessionDep
from app.models import Player,PlayerCreate
from app.core.config import INITIAL_CASH


# --- 增加 (Create) ---
def create_player(session: SessionDep, player_in: PlayerCreate) -> Player:
    # 这里的 **player_in.model_dump() 可以自动映射字段，更简洁
    # 自动校验转换
    db_obj = Player.model_validate(player_in)
    # 如果 Player 模型有 password 字段且需要加密，应在此处处理
    session.add(db_obj)
    session.flush()
    return db_obj


# --- 查询 (Read) ---
def get_player_by_id(session: SessionDep, player_id: int) -> Optional[Player]:
    return session.get(Player, player_id)


def get_player_by_email(session: SessionDep, email: str) -> Optional[Player]:
    statement = select(Player).where(Player.email == email)
    return session.exec(statement).first()

def get_player_by_name(session: SessionDep, name: str) -> Optional[Player]:
    statement = select(Player).where(Player.name == name)
    return session.exec(statement).first()

# --- 分页查询 (Read Multi) ---
def get_players_paginated(
        session: SessionDep,
        page: int = 1,
        page_size: int = 10
) -> dict:
    skip = (page - 1) * page_size

    # 获取数据
    statement = select(Player).offset(skip).limit(page_size)
    items = session.exec(statement).all()

    # 获取总数
    count_statement = select(func.count()).select_from(Player)
    total = session.exec(count_statement).one()

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size
    }


# --- 更新 (Update) ---
def update_player(
        session: SessionDep,
        db_player: Player,
        player_in: PlayerCreate
) -> Player:
    # 将输入数据转为字典，排除未设置的字段
    update_data = player_in.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_player, key, value)

    session.add(db_player)
    session.commit()
    session.refresh(db_player)
    return db_player


# --- 删除 (Delete) ---
def delete_player(session: SessionDep, player_id: int) -> bool:
    db_player = session.get(Player, player_id)
    if not db_player:
        return False
    session.delete(db_player)
    session.commit()
    return True

def deduct_cash(session: SessionDep, player_id: int, cash)->bool:
    player = session.exec(
        select(Player).where(Player.id == player_id)
    ).one_or_none()
    if not player or player.cash < cash:
        return False
    player.cash -= cash
    session.add(player)
    return True
def add_cash(session: SessionDep, player_id: int, cash)->bool:
    player = session.exec(
        select(Player).where(Player.id == player_id)
    ).one_or_none()
    if not player or player.cash < cash:
        return False
    player.cash += cash
    session.add(player)
    return True

def total_cash(session: SessionDep)->int:
    result = (session.exec(
        select(func.sum(Player.cash)).where(Player.id !=0)
    )
              .one())
    return result or 0