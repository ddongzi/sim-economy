import os
from dotenv import load_dotenv

from app.models import Player

load_dotenv()


from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI,Request,status
from fastapi.responses import FileResponse,JSONResponse
from starlette.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from app.core.config import load_config
from app.core.error import RedirectToLoginException
from app.routers import router
from app.service import ChatService,ExchangeService, PlayerService
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

load_config()

# 1. 定义 Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):

#   后台定时任务
    scheduler = BackgroundScheduler()
    # 开发环境
    # trigger = CronTrigger(hour=0, minute=0, second=0)
    # scheduler.add_job(economy_heartbeat_task, trigger=trigger)
    scheduler.add_job(ExchangeService.economy_heartbeat_task, "interval", seconds=60 * 60)

    scheduler.start()
    logger.info("scheduler start")

    yield  # 程序运行中...

    # --- 这里是关闭逻辑 ---
    logging.info("Shutting down...")

app = FastAPI(lifespan=lifespan)

# 全局异常
@app.exception_handler(RedirectToLoginException)
async def redirect_to_login_handler(request: Request, exc: RedirectToLoginException):
    # 判断是否是页面访问
    if "text/html" in request.headers.get("accept", ""):
        return RedirectResponse(url="/")

    # 如果是 API 请求 (Fetch/Axios)
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Session expired, please login again."}
    )

app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(router)

@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    return FileResponse("app/static/favicon.ico")
