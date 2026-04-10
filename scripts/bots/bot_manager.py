import asyncio
import httpx

from scripts.bots.bot import BaseBot
from scripts.bots.ProducerBot import ProducerBot
from scripts.bots.MarketMakerBot import MarketMakerBot
import logging

logger = logging.getLogger(__name__)

BOT_VERSION = "v0.0.3"
async def main():
    # 1. 建立临时客户端并加载共享数据
    async with httpx.AsyncClient(base_url="http://localhost:8000") as temp_client:
        # 直接通过类名调用
        await BaseBot.load_shared_data(temp_client)
    bot_settings = [
        {
            "cls": ProducerBot, 
            "count": 20, 
            "name": "电", 
            "params": {"resource_id": 2, "building_meta_id": "power_plant_"}
        },
        {
            "cls": MarketMakerBot, 
            "count": 4, 
            "name": "商", 
            "params": {"resource_id": 2}
        },
  
    ]

    bot_army = []

    # 2. 简单的嵌套循环生成实例
    for setting in bot_settings:
        BotClass = setting["cls"]
        for i in range(setting["count"]):
            # 自动生成唯一 username，例如 P_电_0, M_商_1
            username = f"{BotClass.__name__[0]}_{setting['name']}_{i}"
            
            # 实例化并解包特有参数
            instance = BotClass(
                username=username,
                **setting.get("params", {})
            )
            bot_army.append(instance)

    # 3. 统一启动
    if bot_army:
        logger.info(f"🚀 经济系统启动：共 {len(bot_army)} 个代理人正在进入市场...")
        await asyncio.gather(*(bot.run() for bot in bot_army))
    else:
        logger.error("❌ 未配置任何机器人")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%H:%M:%S',  # 只显示 14:20:05
        force=True  # 强制覆盖掉其他可能存在的默认配置
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

    asyncio.run(main())