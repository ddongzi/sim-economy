import asyncio

from sqlalchemy.sql import roles

from bots.bot import ArbitrageurBot
from bots.ProducerBot import ProducerBot
import logging
import random
logger = logging.getLogger(__name__)
async def main():
    # 定义你要运行的机器人阵列
    bot_army = [

    ]
    resources = ["Water", "Power", "Soil","House"]
    resource_ids = [1, 2, 9, 6]
    weights = [30, 40, 20, 10]

    bot_army.extend([ ProducerBot( resource_id = 1, building_meta_id="water_",  username=f"P_Water_{i}_V1_")for i in  range(3)])
    bot_army.extend([ ProducerBot( resource_id = 2, building_meta_id="power_plant_", username=f"P_Power_{i}_V1_")for i in  range(4)])
    bot_army.extend([ ProducerBot( resource_id = 9, building_meta_id="mine_plant_", username=f"P_Soil_{i}_V1_")for i in  range(2)])
    bot_army.extend([ ProducerBot( resource_id = 6, building_meta_id= "house_assembly_plant_", username=f"P_House_{i}_V1_")for i in  range(1)])

    # 并发启动所有机器人
    logger.info(f"🚀 经济系统自动化启动：{len(bot_army)} 个代理人正在进入市场...")
    await asyncio.gather(*[bot.run() for bot in bot_army])

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',  # 只显示 14:20:05
        force=True  # 强制覆盖掉其他可能存在的默认配置
    )
    asyncio.run(main())