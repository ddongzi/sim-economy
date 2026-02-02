import os
from fastapi.templating import Jinja2Templates
from sqlmodel import Session,select

from app.db.db import engine
from app.models import GameConfig
import logging
logger = logging.getLogger(__name__)
# 加载 .env 文件中的变量

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates_path = os.path.join(BASE_DIR, "app/templates")
templates = Jinja2Templates(directory=templates_path)

# 从环境变量中读取，如果读不到则使用默认值
GAME_DATA_VERSION = os.getenv("GAME_DATA_VERSION", "19970101")
# 注意：环境变量读取出来都是字符串，如果是数字需要转换
INITIAL_CASH = int(os.getenv("INITIAL_CASH", 5000))

GOVERNMENT_PLAYER_ID = 0

APP_CONFIG = {}

def load_config():
    local_settings = {}
    with Session(engine) as session:
        results = session.exec(select(GameConfig)).all()
        local_settings = {item.key: item.value for item in results}
    APP_CONFIG.update(local_settings)
    logger.info(f"APP_CONFIG: {APP_CONFIG}")
