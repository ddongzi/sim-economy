import asyncio
import httpx

from scripts.bots.bot import BaseBot
from scripts.bots.ProducerBot import ProducerBot
import logging

logger = logging.getLogger(__name__)

BOT_VERSION = "v0.0.3"

async def main():
    async with httpx.AsyncClient(base_url="http://localhost:8000") as temp_client:
        await BaseBot.load_shared_data(temp_client)
    # 定义你要运行的机器人阵列
    bot_army = [
    ]
    total_bots = 80
    bot_config = [
        {"res_id": 1, "meta": "water_", "name": "水", "w": 20},  # 基
        {"res_id": 2, "meta": "power_plant_", "name": "电", "w": 40},  # 工业核心
        {"res_id": 9, "meta": "mine_plant_", "name": "土", "w": 10},  # 基建与农业必备

        {"res_id": 3, "meta": "farm_", "name": "小麦", "w": 15},
        {"res_id": 14, "meta": "farm_", "name": "苹果", "w": 10},  #
        {"res_id": 4, "meta": "flour_mill_", "name": "面粉", "w": 10},  #

        {"res_id": 13, "meta": "bakery_", "name": "馒头", "w": 8},
        {"res_id": 5, "meta": "bakery_", "name": "面包", "w": 7},

        {"res_id": 6, "meta": "house_assembly_plant_", "name": "普通房", "w": 5},
        {"res_id": 10, "meta": "house_assembly_plant_", "name": "别墅", "w": 2},

        {"res_id": 16, "meta": "steel_mill_", "name": "钢铁", "w": 5},
        {"res_id": 15, "meta": "mine_plant_", "name": "铁矿石", "w": 15},
    ]
    total_weight = sum(config['w'] for config in bot_config)
    for config in bot_config:
        count = int(total_bots * (config['w'] / total_weight))
        bot_army.extend([
            ProducerBot(
                resource_id=config['res_id'],
                building_meta_id=config['meta'],
                username=f"P_{config['name']}_{i}_V2"
            ) for i in range(count)
        ])

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
    logging.getLogger("httpx").setLevel(logging.WARNING)

    asyncio.run(main())