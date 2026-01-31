from time import sleep

import httpx
import asyncio
from datetime import datetime, timedelta
import random
from anyio import wait_writable

from app.routers.api.task import product

import logging

logger = logging.getLogger(__name__)


class BaseBot:
    gameData = None
    def __init__(self, username, password="111111", base_url="http://localhost:8000"):
        self.username = username
        self.password = password
        self.token = None
        self.client = httpx.AsyncClient(base_url=base_url, follow_redirects=True,timeout=15.0)
        # 核心：增加状态标记
        self.is_initialized = False
        self.player = None

    @classmethod
    async def load_shared_data(cls, client):
        """类方法：所有实例共用一个 gameData"""
        if cls.gameData is None:  # 确保只请求一次
            resp = await client.get("/api/gamedata")
            cls.gameData = resp.json()
            logger.info("游戏gamedata已加载到类属性中")
    async def sync_player(self):

        resp = await self.client.get("/api/player/me")
        if resp.status_code == 200:
            self.player = resp.json()
        logger.info(f"Player info {self.player}")

    async def login(self):

        resp = await self.client.post("/api/player/register", json={"name": self.username, "email": "1@q.com",
                                                                    "password": self.password})
        resp = await self.client.post("/api/player/login", json={"name": self.username, "password": self.password})
        # 验证是否登录成功
        if resp.status_code == 200:
            logger.info(f"机器人 {self.username} 登录成功")

        else:
            logger.info(f"登录失败: {self.username} {resp.text}")
        await self.sync_player()


# ---------------------------------------------------------
# 2. 做市商 Bot (高频)
# ---------------------------------------------------------
class MarketMakerBot(BaseBot):
    async def run(self):
        await self.login()
        while True:
            # 获取当前盘口
            market = await self.client.get("/api/public/economy")
            curr_p = market.json()["resources"][0]["current_price"]

            # 双向挂单：在均价上下 5% 挂单
            await self.client.post("/api/market/orders", headers=self.headers, json={
                "resource_id": 1, "order_type": "buy", "price": curr_p * 0.95, "quantity": 100
            })
            await self.client.post("/api/market/orders", headers=self.headers, json={
                "resource_id": 1, "order_type": "sell", "price": curr_p * 1.05, "quantity": 100
            })
            await asyncio.sleep(10)  # 每10秒更新一次挂单


class ArbitrageurBot(BaseBot):
    """ 套利者： 时间套利 """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.threshold = 0.05  # 价差百分比

    async def run(self):
        await self.login()
        while True:
            try:
                await self.liquidity_sniffing_loop()
                await asyncio.sleep(60)  # 1min 一般周期比较长，才会出现
            except Exception as e:
                logger.info("ArbitrageurBot E", e)

    async def liquidity_sniffing_loop(self):
        """ 发现巨大价差， """
        resp = await self.client.get("/api/exchange/simple/2", headers=self.client.headers)
        if resp.status_code == 200:
            logger.info("get best price ok")
        else:
            logger.info(f"get best price failed . {resp.text}")
            return
        data = resp.json()
        best_ask = data['lowest_sell_order']
        best_bid = data["highest_buy_order"]
        avg_price = data['market_price']
        current_threshold = (best_ask['price_per_unit'] - best_bid['price_per_unit']) / avg_price
        if current_threshold > self.threshold:
            # 发现价差太大
            # 1. 低价吸收
            await self.client.post("/api/exchange/order", headers=self.client.headers, json={
                "resource_id": 2,
                "quantity": best_ask['quantity'],
                "price_per_unit": round(best_bid['price_per_unit'] + 0.1, 2),
                "created_at": datetime.now().isoformat(),
                "order_type": "buy",
                "quality": 0
            })
            logger.info(f"尝试以 {round(best_bid['price_per_unit'] + 0.1, 2)} 价格挂买单...")
            # 2. 高价卖出
            await self.client.post("/api/exchange/order", headers=self.client.headers, json={
                "resource_id": 2,
                "quantity": best_ask['quantity'],
                "price_per_unit": round(best_ask['price_per_unit'] - 0.1, 2),
                "created_at": datetime.now().isoformat(),
                "order_type": "sell",
                "quality": 0
            })
            logger.info(f"尝试以 {round(best_ask['price_per_unit'] - 0.1, 2)} 价格挂卖单...")
        else:
            logger.info("价差不够大， 无需套利")
