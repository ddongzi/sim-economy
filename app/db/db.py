import os

from sqlmodel import SQLModel, Session

from sqlalchemy import create_engine
DATABASE_URL="postgresql+psycopg://postgres:123456@localhost:5432/simecon"


engine = create_engine(
    DATABASE_URL,
    pool_size=100,         # 常驻连接 100
    max_overflow=200,      # 允许爆发到 300
    pool_timeout=30,       # 拿不到连接时排队等 30 秒
    echo=False
)
print(DATABASE_URL)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def init_db():
    create_db_and_tables()