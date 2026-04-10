import math
import sys

from scripts.bots.bot import BaseBot
from datetime import datetime
import asyncio
import logging
import random

logger = logging.getLogger(__name__)
# ---------------------------------------------------------
# 2. 做市商 Bot (高频)
# ---------------------------------------------------------
class MarketMakerBot(BaseBot):

    def __init__(self, resource_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.resource_id = resource_id  # 每个bot对一个资源

    async def run(self):
        await self.login()
        while True:
            try:
                # 1. 获取当前盘口价格
                resp = await self.client.get(f"/api/exchange/simple/{self.resource_id }")
                simple_price = resp.json()
                curr_p = float(simple_price["market_price"])

                # 2. 模拟用户行为逻辑
                # 在 curr_p - 0.05 到 curr_p + 0.05 之间产生随机价格
                # 使用 uniform 产生浮点随机数
                rand_price_buy = round(random.uniform(curr_p - 0.05, curr_p), 2)
                rand_price_sell = round(random.uniform(curr_p, curr_p + 0.05), 2)
                
                # 随机交易数量 (例如 10 到 150 之间)
                rand_qty = random.randint(10, 100)

                # 3. 随机决策：30%概率只买，30%概率只卖，40%概率双向挂单
                decision = random.random()
                if decision < 0.3:
                    # 模拟买入行为
                    price = rand_price_buy
                    qty = rand_qty

                    resp = await self.client.post("/api/exchange/order/create", json={
                       "resource_id": self.resource_id, "order_type": "buy", 
                        "price_per_unit": price, "quantity": qty,
                        "created_at": int(datetime.now().timestamp())
                    })
                    if resp.status_code == 200:
                        logger.info(f"{self.username} create buy market succeed. {self.resource_id}:{qty}@{price}")
                    else:
                        logger.error(f"{self.username} create buy market failed. {resp.status_code} {resp.text}")
               
                elif decision < 0.6:
                    # 模拟卖出行为
                    price = rand_price_sell
                    qty = rand_qty
                    resp = await self.client.post("/api/exchange/order/create", json={
                        "resource_id": self.resource_id, "order_type": "sell", 
                        "price_per_unit": rand_price_sell, "quantity": rand_qty,
                        "created_at": int(datetime.now().timestamp())
                    })
                    if resp.status_code == 200:
                        logger.info(f"{self.username} create sell market succeed. {self.resource_id}:{qty}@{price}")
                    else:
                        logger.error(f"{self.username} create sell market failed. {resp.status_code} {resp.text}")
                else:
                    # 双向提供流动性
                    price = rand_price_buy
                    qty = rand_qty
                    resp = await self.client.post("/api/exchange/order/create", json={
                       "resource_id": self.resource_id, "order_type": "buy", 
                        "price_per_unit": rand_price_buy, "quantity": rand_qty,
                        "created_at": int(datetime.now().timestamp())
                    })
                    if resp.status_code == 200:
                        logger.info(f"{self.username} create buy market succeed. {self.resource_id}:{qty}@{price}")
                    else:
                        logger.error(f"{self.username} create buy market failed. {resp.status_code} {resp.text}")
                    price = rand_price_sell
                    qty = rand_qty
                     # 模拟卖出行为
                    resp = await self.client.post("/api/exchange/order/create", json={
                        "resource_id": self.resource_id, "order_type": "sell", 
                        "price_per_unit": rand_price_sell, "quantity": rand_qty,
                        "created_at": int(datetime.now().timestamp())
                    })
                    if resp.status_code == 200:
                        logger.info(f"{self.username} create sell market succeed. {self.resource_id}:{qty}@{price}")
                    else:
                        logger.error(f"{self.username} create sell market failed. {resp.status_code} {resp.text}")

                # 4. 随机等待时间 (模仿人类操作间隔，不固定10秒)
                wait_time = random.uniform(5, 15)
                await asyncio.sleep(wait_time)

            except Exception as e:
                logger.error(f"交易异常: {e}")
                await asyncio.sleep(5)