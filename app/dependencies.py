"""
共享依赖函数

"""

from fastapi import Request, HTTPException, Depends, status
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.testing.pickleable import User
from app.models import PlayerCreate,PlayerPublic

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
async def get_current_user(request: Request)->PlayerPublic:
    # 1. 从请求的 Cookie 中获取名为 'access_token' 的值
    token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未检测到登录凭证",
        )

    try:
        # 2. 解码 JWT
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("name")
        userid: str = payload.get("id")
        if username is None:
            raise HTTPException(status_code=401, detail="无效的凭证内容")
        return PlayerPublic(name=username, id=int(userid))  # 或者返回从数据库查到的 User 对象
    except JWTError:
        raise HTTPException(status_code=401, detail="凭证已过期或被篡改")