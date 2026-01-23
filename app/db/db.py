from sqlmodel import SQLModel, Session

from sqlalchemy import create_engine
from app.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL , echo=False)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def init_db():
    create_db_and_tables()