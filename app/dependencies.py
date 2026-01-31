"""
共享依赖函数

"""

from fastapi import Request, HTTPException, Depends, status
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.testing.pickleable import User

from app.core.error import RedirectToLoginException
from app.models import PlayerCreate,PlayerPublic
from app.db.session import SessionDep
import logging
logger = logging.getLogger(__name__)
# 这里的配置应与你生成 Token 时一致
SECRET_KEY = "你的加密密钥"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # Token 有效期（如：24小时）


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    生成 JWT Token
    :param data: 包含用户身份信息的字典，例如 {"sub": "username"}
    :param expires_delta: 可选的过期时间差
    """
    to_encode = data.copy()

    # 设置过期时间
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # 将过期时间写入负载 (Payload)
    to_encode.update({"exp": expire})

    # 使用密钥和算法进行加密签名
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt

# 验证函数：尝试从 Cookie 获取 token 并解析
async def get_current_user(request: Request) -> PlayerPublic:
    token = request.cookies.get("access_token")

    if not token:
        # 不抛出 401，而是抛出自定义异常
        raise RedirectToLoginException()
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("name")
        userid: str = payload.get("id")
        if username is None:
            raise RedirectToLoginException()
        return PlayerPublic(name=username, id=int(userid))
    except JWTError:
        raise RedirectToLoginException()

async def refresh_building( session:SessionDep,
                            current_player: PlayerPublic = Depends(get_current_user)):
    """ 更新建筑或任务状态 """
    pass
