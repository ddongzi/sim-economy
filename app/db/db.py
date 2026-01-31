from sqlmodel import SQLModel, Session

from sqlalchemy import create_engine
from app.core.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_size=100,         # 常驻连接 100
    max_overflow=200,      # 允许爆发到 300
    pool_timeout=30,       # 拿不到连接时排队等 30 秒
)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def init_db():
    create_db_and_tables()