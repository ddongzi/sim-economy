from fastapi import APIRouter,WebSocketDisconnect
from fastapi import WebSocket
from typing import Dict
from app.service import ChatService
from abc import ABC, abstractmethod
from app.service.ws import manager
import logging
router = APIRouter()
logger = logging.getLogger(__name__)
@router.websocket("/{user_name}")
async def websocket_endpoint(websocket: WebSocket, user_name: str):
    logger.info(f"WS {user_name} connect")
    await manager.connect(websocket, user_name)
    try:
        while True:
            # 1. 统一接收数据
            msg = await websocket.receive_json()
            # 2. 收到消息，扔给分发器处理，不阻塞主循环
            logger.info(f"WS {msg} ")
            await manager.ws_dispatcher(user_name, msg)
    except WebSocketDisconnect:
        await manager.disconnect(user_name)
    except Exception as e:
        logger.error(f"WS 运行异常: {str(e)}")
        await manager.disconnect(user_name)
