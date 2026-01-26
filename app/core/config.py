import os
from dotenv import load_dotenv
from fastapi.templating import Jinja2Templates

# 加载 .env 文件中的变量
load_dotenv()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates_path = os.path.join(BASE_DIR, "app/templates")
templates = Jinja2Templates(directory=templates_path)

# 从环境变量中读取，如果读不到则使用默认值
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
GAME_DATA_VERSION = os.getenv("GAME_DATA_VERSION", "20260126_01")
# 注意：环境变量读取出来都是字符串，如果是数字需要转换
INITIAL_CASH = int(os.getenv("INITIAL_CASH", 5000))

GOVERNMENT_PLAYER_ID = 0
