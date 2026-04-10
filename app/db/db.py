import os
from sqlmodel import SQLModel, Session, create_engine, select
from sqlalchemy import event
from app.models import *
import logging
import pandas as pd

logger = logging.getLogger(__name__)

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/simecon"
engine = create_engine(
    DATABASE_URL,
)

print(f"Database switched to: {DATABASE_URL}")

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def seed_government():
      with Session(engine) as session:
        gov = session.get(Player, 1)
        if not gov:
            logger.info('add gov.')
            session.add(Player(
                id= 1,
                name= 'government',
                email = '1@q.com',
                password = '111111',
                is_bot= False,
                cash = 10**8
            ))
            inventory_items = [
                     {"resource_id": 1, "quantity": 100000},
                {"resource_id": 2, "quantity": 100000},
                {"resource_id": 3, "quantity": 100000},
            ]
            for item in inventory_items:
                session.add(Inventory(
                    player_id = 1,
                    resource_id = item['resource_id'],
                    quantity = item['quantity'],
                ))
            session.commit()

def init_db():
    logger.debug(f"SQLModel find tables: {list(SQLModel.metadata.tables.keys())}")
    create_db_and_tables()
    init_db_from_excel()
    seed_government()

SHEET_TO_MODEL = {
    'resource_base': Resource,
    'industry_base': Industry,
    'recipe_requirement_base': RecipeRequirement,
    'recipe_base': Recipe,
    'building_base': BuildingMeta,
    'bd_level_base': BuildingLevelsConfig,
    'game_config_base': GameConfig
}
# excel读取静态数据
def init_db_from_excel(filepath:str = 'design.xlsx'):
    logger.debug(f'current dir: {os.getcwd()}')
    
    try:
        xl = pd.ExcelFile(filepath)
    except FileNotFoundError as err:
        logger.error(err)
        return

    with Session(engine) as session:
        session.execute(text("SET session_replication_role = 'replica';"))
        for sheet_name, model_cls in SHEET_TO_MODEL.items():
            if sheet_name not in xl.sheet_names:
                continue
            logger.info(f'load from {sheet_name}')

            if session.exec(select(model_cls)).first():
                continue
            df = pd.read_excel(xl, sheet_name=sheet_name)
            df = df.where(pd.notnull(df), None)
            for _, row in df.iterrows():
                obj = model_cls.model_validate(row.to_dict())
                session.add(obj)
        session.commit()
        session.execute(text("SET session_replication_role = 'origin';"))
# from sqlalchemy import MetaData

# # 定义标准的命名规则
# naming_convention = {
#     "ix": "ix_%(column_0_label)s",
#     "uq": "uq_%(table_name)s_%(column_0_name)s",
#     "ck": "ck_%(table_name)s_%(constraint_name)s",
#     "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
#     "pk": "pk_%(table_name)s"
# }

# # 传给 SQLModel 的 metadata
# SQLModel.metadata = MetaData(naming_convention=naming_convention)
