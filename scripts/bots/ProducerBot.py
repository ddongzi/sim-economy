import math
import sys

from scripts.bots.bot import BaseBot
from datetime import datetime
import asyncio
import logging
import random

logger = logging.getLogger("ProducerBot")

# ---------------------------------------------------------
# 1. 生产型 Bot
# -
# ---------------------------------------------------------
class ProducerBot(BaseBot):

    def __init__(self, resource_id, building_meta_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sleep_time = 60 * 3  # 周期检查，
        self.resource_id = resource_id  # 每个bot生产一种资源
        self.building_meta_id = building_meta_id
        self.inventory = {}  # 实时库存缓存
        self.recipe = {}  # 配方表
        self.buildings = []  #
        self.reserve_cash = 300 # 钱包阈值
        self.safety_hours = 1

    def __str__(self):
        return f"{self.player['name']}"

    def get_float_price(self, price: float, base_price: float, behavior, fluctuation_percent=0.02):
        # 1. 设定一个浮动范围（比如 ±2%）
        change = price * random.uniform(-fluctuation_percent, fluctuation_percent)

        if price < base_price * 0.8 and change < 0:
            if behavior == 'sell':
                # 如果当前价格过低， 卖方不应该继续低价卖了，必须上涨
                change = abs(change)  # 强行转为上涨
            if behavior == 'buy':
                # 当前价格很低， 准备大量购买，提高self.safety_hour
                pass
        # 2. 精度补偿：如果算出的波动比 0.001 还小，强制给它一个 0.001 的随机波动
        # 解决你提到的“0.02/0.03 不起作用”的问题
        if abs(change) < 0.001:
            # 随机决定是加、减、还是不动 (50% 概率动，50% 不动)
            change = random.choice([-0.001, 0, 0.001])

        final_price = price + change
        if final_price > base_price * 1.5:
            final_price = base_price * 1.5
        if final_price < base_price * 0.6:
            final_price = base_price * 0.6
        return round(final_price, 3)

    async def init_mine(self):
        """ login 之后 初始化"""
        matches = [
            r for r in self.gameData['recipes']
            if r.get('output_resource_id') == self.resource_id
        ]
        # 2. 取出第一个匹配项（或者存储全部）
        if matches:
            self.recipe = matches[0]
        else:
            self.recipe = None
            raise Exception("配方找不到错误")

        self.safety_hours = math.ceil(1 / self.recipe['per_hour'])
        if self.safety_hours < 1:
            self.safety_hours = 1

        logger.info(f"{self.username} init .")

    async def sync_inventory(self):
        """同步服务器背包数据并转换为字典"""
        resp = await self.client.get("/api/inventory")
        if resp.status_code == 200:
            raw_data = resp.json()  # 拿到原始列表

            # 核心转换逻辑：将列表转为 {id: qty} 字典
            self.inventory = {item['resource_id']: item['quantity'] for item in raw_data}

            logger.info(f"{self.username} sync inventory done: {self.inventory}")
        else:
            logger.error(f"{self.username} sync inventory failed: {resp.status_code} {resp.text}")

    async def buy_market_order(self, resource_id, qty):
        if qty <= 0:
            return
        resp = await self.client.get(f"/api/exchange/simple/{resource_id}")
        simple_price = resp.json()
        price = self.get_float_price(simple_price['market_price'], simple_price['base_price'], behavior='buy')
        resp = await self.client.post("/api/exchange/order", json={
            "order_type": "buy",
            "resource_id": resource_id,
            "price_per_unit": price,
            "quantity": qty,
            "created_at": datetime.now().isoformat()
        })
        if resp.status_code == 200:
            logger.info(f"{self.username} create buy market succeed. {resource_id}:{qty}@{price}")
        else:
            logger.error(f"{self.username} create buy market failed. {resp.status_code} {resp.text}")
    async def sell_market_order(self, resource_id, qty):
        if qty <= 0:
            return
        resp = await self.client.get(f"/api/exchange/simple/{resource_id}")
        simple_price = resp.json()
        price = self.get_float_price(simple_price['market_price'],simple_price['base_price'], behavior='sell')
        resp = await self.client.post("/api/exchange/order", json={
            "order_type": "sell",
            "resource_id": resource_id,
            "price_per_unit": price,
            "quantity": qty,
            "created_at": datetime.now().isoformat()
        })
        if resp.status_code == 200:
            logger.info(f"{self.username} create sell market succeed. {resource_id}:{qty}@{price}")
        else:
            logger.error(f"{self.username} create sell market failed. {resp.status_code} {resp.text}")


    async def try_purchase(self):
        """ 目标为4个小时生产 """
        # 0. 先更新一次钱包余额（假设存在 self.balance）
        await self.sync_player()
        await self.sync_inventory()

        # 1. 计算每秒消耗量
        # 消耗率 = (配方量 / 周期) * 建筑数
        for input_res in self.recipe['inputs']:
            input_resource_id = input_res['resource_id']
            consumption_per_hour = input_res['quantity'] * self.recipe['per_hour'] * 12

            # 2. 计算目标安全库存量
            target_amount = int(consumption_per_hour * self.safety_hours)

            # 3. 检查当前库存
            current_amount = self.inventory.get(input_resource_id, 0)

            if current_amount < target_amount:  # 够2各周期
                needed_qty = target_amount - current_amount
                resp = await self.client.get(f"/api/exchange/simple/{input_resource_id}")
                simple_price = resp.json()
                market_price = simple_price['market_price']
                available_cash = max(0, self.player['cash'] - self.reserve_cash)

                # 2. 核心：资金校验
                # 钱包能买的最大数量 = 总余额 / 单价 (预留一部分钱手续费或生产费)
                max_affordable = int((available_cash * 0.7// market_price))
                # 3. 取 需求量 和 财力 之间的最小值
                buy_qty = int(min(needed_qty, max_affordable))

                await self.buy_market_order(input_resource_id, buy_qty)
        logger.info(f"{self.username} try purchase done.")

    async def try_claim(self):
        # 先领取完成的任务
        for building_id in self.buildings:
            resp = await self.client.get(f"/api/task/{building_id}")
            if resp.status_code == 200:
                # 有任务在忙
                task = resp.json()
                if datetime.fromisoformat(task['end_time']) < datetime.now():
                    # 任务需要领取.
                    resp = await self.client.get(f"/api/task/claim/{building_id}")

    async def try_produce(self):
        """ 2. 能产则产：检查原材料是否足够 """

        await self.sync_inventory()
        # 检查所有原材料是否都满足配方
        total_quantity = sys.maxsize
        if not self.recipe['inputs']:
            total_quantity = int( self.recipe['per_hour']) * 12  # 电没有input， 默认1小时数量
        for input_res in self.recipe['inputs']:
            res_id = input_res['resource_id']
            qty = input_res['quantity']
            total_quantity = min(self.inventory.get(res_id, 0) // qty, total_quantity)

        every_quantity = math.floor(total_quantity / 12)

        if total_quantity <= 0:
            return
        if every_quantity <= 0:
            every_quantity = 1
        # 找到你那 12 个建筑中空闲的进行生产
        for building_id in self.buildings:
            resp = await self.client.get(f"/api/task/{building_id}")
            if resp.status_code == 200:
                # 有任务
                continue
            if resp.status_code == 400:

                await self.client.post("/api/task/create", json={
                    "resource_id": self.resource_id,
                    "quantity": every_quantity,
                    "player_building_id": building_id,
                    "start_time": datetime.now().isoformat()
                })
        logger.info(f"{self.username} try produce done.")

    async def try_sell(self):
        """ 3. 回笼资金：成品超过目标则卖出 """
        await self.sync_inventory()
        finished_goods = self.inventory.get(self.resource_id, 0)
        sell_qty = math.floor(finished_goods / 2)
        await self.sell_market_order(self.resource_id, sell_qty)
        logger.info(f"{self.username} try sell done.")


    async def try_buildings(self):
        """ 尝试建造12个playerbuilding """
        if self.is_initialized:
            return
        resp = await self.client.get("/api/buildings")
        if resp.status_code == 200:
            current_buildings = resp.json()
            existing_slots = {b['slot_number'] for b in current_buildings}

            # 3. 只建造缺失的 slot
            for i in range(12):
                if i not in existing_slots:
                    await self.client.post("/api/buildings/construct", json={
                        "building_meta_id": self.building_meta_id,
                        "slot_number": i,
                    })

            self.is_initialized = True  # 标记为已完成初始化

        resp = await self.client.get("/api/buildings")
        if resp.status_code == 200:
            self.buildings = [b['id'] for b in resp.json()]
        logger.info(f"{self.username} try get buildings done. {self.buildings}")


    async def run(self):
        # 1. 初始错峰，避免瞬间挤爆服务器
        await asyncio.sleep(random.uniform(1, 60))
        # 2. 前置初始化阶段（带重试机制）
        init_success = False
        retry_count = 0

        while not init_success:
            try:
                await self.login()
                await self.init_mine()  # 同步个人信息/钱包
                await self.try_buildings()  # 检查并建造
                init_success = True
                logger.info(f"{self.username} Bot 初始化成功，开始进入生产循环")
            except Exception as e:
                retry_count += 1
                # 计算等待时间：2, 4, 8, 16... 最大 60 秒
                wait_time = min(2 ** retry_count, 60)
                logger.error(f"{self.username} 初始化失败 (第{retry_count}次): {e}。{wait_time}秒后重试...")
                await asyncio.sleep(wait_time)
        retry_count = 0
        # 3. 核心业务循环
        while True:
            try:
                await self.sync_inventory()  # 每次循环前先看一眼包里有啥
                await self.try_claim()
                await self.try_purchase()
                await self.try_produce()
                await self.try_sell()
            except Exception as e:
                retry_count += 1
                # 计算等待时间：2, 4, 8, 16... 最大 60 秒
                wait_time = min(2 ** retry_count, 60)
                logger.error(f"{self.username} 业务失败 (第{retry_count}次): {e}。{wait_time}秒后重试...")
                await asyncio.sleep(wait_time)
            finally:
                # 无论是否报错，都进入下一次轮询前的休眠
                await asyncio.sleep(self.sleep_time + random.uniform(0, 60))


