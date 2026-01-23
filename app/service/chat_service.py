from app.service.ws import WSServiceBase,manager
import json
import logging
logger = logging.getLogger(__name__)
class ChatService(WSServiceBase):
    def __init__(self):
        self.type = "chat"
    async def handle(self, user_name:str, sub_type, data):
        """ user_name ws 到来数据 处理 """
        data = json.loads(data)
        logger.info(f"user_name:{user_name}, sub_type:{sub_type}, data:{data}")
        if sub_type == "global":
            await self.send_global(user_name, data["message"])
        elif sub_type == "private":
            await self.send_private(sender=data["from"], receiver=data["to"], message=data["message"])
        pass

    async def send_global(self, sender: str, message: str):
        """【全局】发给所有人"""
        sub_type = "global"
        payload = {"from": sender, "message": message}
        message = {
            "type": self.type,
            "sub_type": sub_type,
            "data": payload
        }
        await manager.broadcast(message)

    async def send_private(self, sender: str, receiver: str, message: str):
        """【私聊】只发给目标和自己"""
        sub_type = "private"
        payload = {"from": sender, "to": receiver, "message": message}
        message = {
            "type": self.type,
            "sub_type": sub_type, "data": payload
        }
        await manager.send_personal_message(receiver, message)
        await manager.send_personal_message(sender,message)
