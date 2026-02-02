import json
from json import JSONDecoder

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Query
from sqlmodel import Session, Field

from app.core.config import INITIAL_CASH, GOVERNMENT_PLAYER_ID
from app.db.session import SessionDep  # 假设你的 session 依赖项位置
from app.crud import crud_player
from app.dependencies import create_access_token, get_current_user
from app.models import PlayerCreate, PlayerPublic, PlayerLogin, TransactionActionType
from app.service import AccountingService,PlayerService
import base64

router = APIRouter()


# -----------------------------------------------------------------------------
# 1. 注册 (Register)
# -----------------------------------------------------------------------------
@router.post("/register", response_model=PlayerPublic)
async def register_player(player_in: PlayerCreate, session: SessionDep):
    # 检查玩家名是否已存在
    db_player = crud_player.get_player_by_name(session, name=player_in.name)
    if db_player:
        raise HTTPException(status_code=400, detail="该用户名已被注册")

    new_player = crud_player.create_player(session, player_in=player_in)
    AccountingService.change_cash(session, new_player.id, INITIAL_CASH,
                                  TransactionActionType.NEW_PLAYER_INITIAL_REVENUE,
                                  new_player.id)
    AccountingService.change_cash(session, GOVERNMENT_PLAYER_ID, -INITIAL_CASH,
                                  TransactionActionType.SYSTEM_NEW_PLAYER_COST,
                                  new_player.id)
    session.commit()
    return new_player


# -----------------------------------------------------------------------------
# 2. 登录 (Login)
# -----------------------------------------------------------------------------
@router.post("/login")
async def login(
        response: Response,
        player_in: PlayerLogin,
        session: SessionDep
):
    # 简单的登录逻辑：匹配用户名（实际项目中应加入密码验证）
    player = crud_player.get_player_by_name(session, name=player_in.name)

    if not player:
        raise HTTPException(status_code=404, detail="玩家不存在")
    if player.password != player_in.password:
        raise HTTPException(status_code=400, detail="登录信息错误")

    # 将 player_id 写入 Cookie
    # 生成 Token
    token = create_access_token(data={"name": player.name, "id": player.id})

    user_info = json.dumps({"name": player.name, "id": player.id})
    encoded_value = base64.urlsafe_b64encode(user_info.encode()).decode().rstrip("=")
    response.set_cookie(
        key="user_info",
        value=encoded_value,
        # 建议加上这些参数提高安全性
        samesite="lax",
        httponly=False  # 确保前端能读到
    )

    # 将 Token 写入 Cookie
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,  # 重要：前端 JS 无法读取，防止 XSS 攻击
        max_age=3600 * 24,  # 有效期 1 天
        samesite="lax",  # 防止 CSRF 攻击
        secure=False  # 如果是生产环境 https，请设为 True
    )

    PlayerService.create_player_economy_snapshot(player.id)

    return {"status": "ok"}


# -----------------------------------------------------------------------------
# 3. 登出 (Logout)
# -----------------------------------------------------------------------------
@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token")
    return {"message": "已登出"}


# -----------------------------------------------------------------------------
# 4. 获取当前玩家信息 (Me)
# -----------------------------------------------------------------------------
@router.get("/me", response_model=PlayerPublic)
async def read_current_player(
        session: SessionDep,
        player: PlayerPublic = Depends(get_current_user)
):
    player = crud_player.get_player_by_id(session, player_id=player.id)
    if not player:
        raise HTTPException(status_code=404, detail="玩家不存在")
    return player


@router.get("/economy/ledger")
async def ledgers(
        session: SessionDep,
        player: PlayerPublic = Depends(get_current_user),
        page:int = Query(default=1, ge=1),
        limit: int = Query(default= 10, le= 100),
        ledger_type: int= Query(default=None)
):
    # 返回流水记录，
    return AccountingService.get_all_ledger(session, player.id, page, limit, ledger_type)


@router.get("/economy/overview")
async def economy_overview(
        session: SessionDep,
        player: PlayerPublic = Depends(get_current_user)
):

    PlayerService.create_player_economy_snapshot(player.id)

    return {
        "status": "success",
        "data": {
            "history_curve": PlayerService.get_history_curve(session, player_id= player.id)
        }
    }
