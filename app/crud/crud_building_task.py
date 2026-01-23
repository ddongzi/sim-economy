from datetime import timedelta

from app.db.session import SessionDep
from app.models import BuildingTask,BuildingTaskCreate
from sqlmodel import Session, select

def get_building_task(session: Session, task_id: int) -> BuildingTask | None:
    return session.get(BuildingTask, task_id)

def get_building_task_by_player_building_id(session: Session, player_building_id: int) -> BuildingTask | None:
    return session.exec(
        select(BuildingTask).where(BuildingTask.player_building_id == player_building_id)
    ).one_or_none()

def get_multi_by_player(session: Session, player_id: int, skip: int = 0, limit: int = 100) -> list[BuildingTask]:
    statement = select(BuildingTask).where(BuildingTask.player_id == player_id).offset(skip).limit(limit)
    return session.exec(statement).all()

def create_building_task(session: Session, building_task_in: BuildingTaskCreate, player_id: int
                         ,duration:float) -> BuildingTask:
    # 将 Schema 转换为 数据库模型实例
    db_obj = BuildingTask(
        **building_task_in.model_dump(),
        player_id=player_id
    )
    db_obj.end_time = db_obj.start_time + timedelta(hours=duration)

    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

def remove_building_task(session: Session, task_id: int) -> BuildingTask:
    db_obj = session.get(BuildingTask, task_id)
    if db_obj:
        session.delete(db_obj)
        session.commit()
    return db_obj

def update_building_task(session: Session, building_task_in: BuildingTaskCreate) -> BuildingTask:
    session.add(building_task_in)
    session.commit()
    session.refresh(building_task_in)
    return building_task_in
