import math

from bots.bot import BaseBot
from datetime import datetime
import asyncio
import logging
import random
logger = logging.getLogger("ProducerBot")

class ProduceTask:
    def __init__(self, player_building_id, resource_id, quantity, duration):
        self.player_building_id = player_building_id
        self.resource_id = resource_id
        self.quantity = quantity
        self.duration = duration
    def __str__(self):
        return f"player_building_id:{self.player_building_id} resource_id:{self.resource_id} quantity:{self.quantity} duration:{self.duration}s"
# ---------------------------------------------------------
# 1. 生产型 Bot
# -
# ---------------------------------------------------------
class ProducerBot(BaseBot):
    def __init__(self, resource_id, building_meta_id,  *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sleep_time = 30 # 周期检查，
        self.resource_id = resource_id # 每个bot生产一种资源
        self.building_meta_id = building_meta_id
        self.produce_tasks = [] # ProduceTask

    async def try_purchase(self):
        """ 尝试补货 """

        pass

    async def try_produce(self):
        """ 尝试生产 """
        pass

    async def try_sell(self):
        """ 尝试售出 """
    async def try_buildings(self):
        """ 尝试建造12个playerbuilding """
        for i in range(12):
            await self.client.post(f"/api/buildings/construct", json={
                "building_meta_id": self.building_meta_id,
                "slot_number": i,
            })
        pass

    async def run(self):
        await asyncio.sleep(random.uniform(0, 30))  # 核心：错峰执行
        await self.login()
        await self.try_buildings()
        while True:
            await self.try_purchase()
            await self.try_produce()
            await self.try_sell()

            await asyncio.sleep(self.sleep_time + random.uniform(0, 10))  #

    async def get_all_produce_task(self) ->bool:
        """ 获取所有建筑状态，试着生产 """
        resp = await self.client.get("/api/buildings/")
        if resp.status_code != 200:
            logger.info(f"get player buildings failed! . {resp.text}")
            return False
        player_buildings = resp.json()
        for pb in player_buildings:
            """ 空闲建筑 """
            resp = await self.client.get(f"/api/task/{pb['id']}")
            if resp.status_code != 400:
                continue
            if resp.json()['detail']['id'] != "BUILDING_IDLE":
                continue
            # 空闲建筑可以生产. 选择 时间利润 最大的资源进行生产
            # 获取所有可以生产的资源
            for pb_recipe in pb_recipes:
                resp = await self.client.get(f"/api/exchange/simple/{pb_recipe['output_resource_id']}")
                if resp.status_code != 200:
                    logger.info(f"get simple price failed. {resp.text}")
                    continue
                market_price = resp.json()["market_price"]
                resp = await self.client.post(f"/api/task/cost/{pb_recipe['output_resource_id']}", json={
                    "resource_id": pb_recipe['output_resource_id'],
                    "quantity": 1000,
                })
                if resp.status_code != 200:
                    logger.info(f"get task cost . {resp.text}")
                data = resp.json()
                profit_sec = (data["quantity"] * market_price - data["cash_cost"]) / data['duration']
                if best_resource['profit_sec'] < profit_sec:
                    best_resource['resource_id'] = pb_recipe['output_resource_id']
                    best_resource['profit_sec'] = profit_sec
            # 填补库存。尝试以1小时数量生产
            recipe = next((r for r in recipes if r["output_resource_id"] == best_resource["resource_id"]), None)
            quantity = math.ceil(recipe["per_hour"])
            resp = await self.client.get("/api/inventory/")
            inventory = resp.json()
            for input in recipe['inputs']:
                inv = next((x for x in inventory if x["resource_id"] == input["resource_id"]), None)
                need_quantity = quantity* input["quantity"]
                if need_quantity > inv['quantity']:
                    resp = await self.client.get(f"/api/exchange/simple/{input["resource_id"]}")
                    if resp.status_code != 200:
                        logger.info(f"get simple price failed. {resp.text}")
                        quantity = 0
                    market_price = resp.json()["market_price"]
                    # 需要购买
                    resp = await self.client.post(f"/api/exchange/", json={
                        "order_type": "buy",
                        "resource_id": input["resource_id"],
                        "price_per_unit": market_price,
                        "quantity": quantity,
                        "created_at": datetime.now().isoformat()
                    })
                    logger.info(f"Buy for {best_resource['resource_id']} input meterials  :{input["resource_id"]} {need_quantity}@{market_price}")

            duration = int(quantity / recipe['per_hour'] * 3600)
            produce_task = ProduceTask(
                player_building_id= pb['id'],
                resource_id=best_resource['resource_id'],
                quantity = quantity,
                duration=duration
            )
            self.produce_tasks.append(produce_task)
            logger.info(f"Task append: {produce_task}" )

        return True


    async def produce(self, task):
        try:
            # 尝试领取完成任务。
            resp = await self.client.get(f"api/task/claim/{task.resource_id}")
            if resp.status_code != 200:
                logger.info(f"claim task fail . {resp.text}")
                return
            # 创建任务
            resp = await self.client.post("/api/task/create", headers=self.client.headers, json=
            {
                "player_building_id": task.player_building_id,
                "resource_id": task.resource_id,
                "quantity": task.quantity,
                "start_time": datetime.now().isoformat(),
            }
                                          )
            if resp.status_code != 200:
                logger.info(f"create task failed {task}: {resp.text}")
            # 卖出: 听从市场建议； 全部卖出.
            resp = await self.client.get(f"/api/exchange/price_suggestion/{task.resource_id}", headers=self.client.headers)
            data = resp.json()
            suggestion_price =data["suggest_price"]

            resp = await self.client.get(f"/api/inventory/{task.resource_id}")
            inv_quantity = resp.json()["quantity"]
            if inv_quantity == 0:
                logger.info(f"ProducerBot cant's sell , resource_id:{task.resource_id} inventory quantity:{inv_quantity} ")
                return
            resp = await self.client.post("/api/exchange/order", headers=self.client.headers, json=
            {
                "resource_id": task.resource_id,
                "quantity": inv_quantity,
                "price_per_unit": suggestion_price,
                "created_at": datetime.now().isoformat(),
                "order_type": "sell",
            })
            logger.info(f"ProducerBot sell quantity {inv_quantity} @{suggestion_price}")
            if resp.status_code != 200:
                logger.info(f"create order fail . {resp.text}")

        except Exception as e:
            logger.info(f"{e}")