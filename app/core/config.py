# app/core/config.py
"""
全局对象
"""
from fastapi.templating import Jinja2Templates
import os

# 获取项目根目录的绝对路径，确保在不同目录下运行都不会找不到 templates 文件夹
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates_path = os.path.join(BASE_DIR, "app/templates")

# 实例化一次
templates = Jinja2Templates(directory=templates_path)

DATABASE_URL = "postgresql+psycopg://postgres:123456@localhost:5432/simecon"

GAME_DATA_VERSION = "20240112_02"

# 不可修改！！！
GOVERNMENT_PLAYER_ID = 0

INITIAL_CASH = 9999