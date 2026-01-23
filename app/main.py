from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.staticfiles import StaticFiles
from app.routers import router
from app.service.chat_service import ChatService
from app.service.exchange import ExchangeService, exchange_service
from app.service.ws import manager
from contextlib import asynccontextmanager
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%H:%M:%S',  # 只显示 14:20:05
    force=True  # 强制覆盖掉其他可能存在的默认配置
)
logger = logging.getLogger(__name__)


# 1. 定义 Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- 这里是启动逻辑 ---
    from app.service.chat_service import ChatService
    from app.service.ws import manager

    # 初始化并注册
    chat_service = ChatService()
    manager.register("chat", chat_service)
    manager.register("exchange", exchange_service)

    # 强制打印到控制台
    logger.info("chatService init")

    yield  # 程序运行中...

    # --- 这里是关闭逻辑 ---
    logging.info("Shutting down...")

app = FastAPI(lifespan=lifespan)



app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse("app/static/favicon.ico")
