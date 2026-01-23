from typing import Dict

from dotenv.cli import set_value
from fastapi import WebSocket
from abc import abstractmethod, ABC
import logging
logger = logging.getLogger(__name__)
class WSServiceBase(ABC):
    @classmethod
    @abstractmethod
    async def handle(cls, user_name, sub_type, data):
        """ 处理收到的msg """
        pass

class WSConnectionManager:
    def __init__(self):
        # 核心：键是 user_name，值是对应的 WebSocket 对象
        self.active_connections: Dict[str, WebSocket] = {}
        self.service_map = {}

    async def connect(self, websocket: WebSocket, user_name: str):
        await websocket.accept()
        # 玩家上线，登记入册
        if user_name not in self.active_connections:
            logger.info(f"玩家 {user_name} 已连接")
            self.active_connections[user_name] = websocket
            await self.broadcast_online_list()

    async def disconnect(self, user_name: str):
        # 玩家掉线，从名册移除
        if user_name in self.active_connections:
            del self.active_connections[user_name]
            logger.info(f"玩家 {user_name} 已断开")
            await self.broadcast_online_list()

    async def broadcast_online_list(self):
        """将当前所有在线用户的 ID 列表发给所有人"""
        online_ids = list(self.active_connections.keys())
        message = {
            "type": "user_list_update",
            "sub_type": "",
            "data": online_ids
        }
        await self.broadcast(message)

    async def send_personal_message(self, receiver_name: str, message: dict):
        # 定向推送：根据 ID 找到那个具体的 Socket
        if receiver_name in self.active_connections:
            websocket = self.active_connections[receiver_name]
            await websocket.send_json(message)
            logger.info(f"send to -> {receiver_name} {websocket}, {message}")
        else:
             # 这一行日志能帮你发现 ID 类型错误或玩家不在线
            logger.warning(f"❌ 发送失败: 玩家 {receiver_name} 不在线或 ID 类型({type(receiver_name)})错误, {self.active_connections.keys()}")
    async def broadcast(self, message: dict):
        # 广播：给所有人发
        for connection in self.active_connections.values():
            await connection.send_json(message)

    def register(self, msg_type, instance):
        """ 注册 type类型实例， """
        self.service_map[msg_type] = instance

    async def ws_dispatcher(self, user_name:str, msg):
        msg_type = msg.get("type")
        sub_type = msg.get("sub_type")
        data = msg.get("data", {})
        service = self.service_map.get(msg_type)
        logger.info(f"WS dispatcher: {msg} {service}")
        if service:
            # 执行对应业务逻辑
            await service.handle(user_name, sub_type, data)
        else:
            # 统一处理未知类型
            await manager.send_personal_message(user_name, {
                "type": "system",
                "sub_type": "error",
                "data": {"msg": f"Unsupported type: {msg_type}"}
            })

# 初始化一个全局唯一的管理器
manager = WSConnectionManager()
