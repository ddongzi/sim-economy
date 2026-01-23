from datetime import datetime
from typing import Optional, List, Sequence
from sqlmodel import Session, select, func, and_
from datetime import datetime
from typing import Optional, List, Sequence
from sqlmodel import Session, select, func, and_
from app.models import BuildingMeta, PlayerBuilding, BuildingTask, PlayerBuildingCreate, Recipe, BuildingMetaCreate
from app.db.session import SessionDep

def get_all_building_metas(session: SessionDep) -> List[BuildingMeta]:
    return session.exec(select(BuildingMeta)).all()


def get_building_meta_by_id(session: SessionDep, meta_id: str) -> Optional[BuildingMeta]:
    return session.get(BuildingMeta, meta_id)


def get_building_meta_by_name(session: SessionDep, name: str) -> Optional[BuildingMeta]:
    statement = select(BuildingMeta).where(BuildingMeta.name == name)
    return session.exec(statement).one_or_none()


def get_building_meta_by_player_building_id(session: SessionDep, player_building_id: int) -> Optional[BuildingMeta]:
    """ 获取playerbuilding对应的 buildingmeta"""
    statement = (select(BuildingMeta).
                 where(PlayerBuilding.id == player_building_id).
                 join(PlayerBuilding, BuildingMeta.id == PlayerBuilding.building_meta_id))
    return  session.exec(statement).one()

def create_building_meta(session: SessionDep, metaCreate: BuildingMetaCreate) -> BuildingMeta:
    meta = BuildingMeta(**metaCreate.model_dump())
    session.add(meta)
    session.commit()
    session.refresh(meta)
    return meta


def update_building_meta(session: SessionDep, meta: BuildingMeta) -> BuildingMeta:
    session.add(meta)
    session.commit()
    session.refresh(meta)
    return meta


def delete_building_meta(session: SessionDep, meta_id: str) -> None:
    meta = session.get(BuildingMeta, meta_id)
    if meta:
        session.delete(meta)
        session.commit()


def get_all_player_buildings(session: SessionDep) -> List[PlayerBuilding]:
    return session.exec(select(PlayerBuilding)
                        ).all()

def get_player_buildings(session: SessionDep, player_id:int) -> List[PlayerBuilding]:
    return session.exec(select(PlayerBuilding).where(PlayerBuilding.player_id == player_id)
                        ).all()

def get_player_building_by_id(session: SessionDep, id: int) -> PlayerBuilding | None:
    return session.get(PlayerBuilding, id)


def create_player_building(session: SessionDep, building: PlayerBuildingCreate, player_id: int) -> PlayerBuilding:
    building = PlayerBuilding(**building.model_dump())
    building.player_id = player_id
    session.add(building)
    return building


def update_player_building(session: SessionDep, building: PlayerBuilding) -> PlayerBuilding:
    session.add(building)
    session.commit()
    session.refresh(building)
    return building


def delete_player_building(session: SessionDep, building_id: int) -> None:
    building = session.get(PlayerBuilding, building_id)
    if building:
        session.delete(building)
        session.commit()


def get_all_building_tasks(session: SessionDep) -> List[BuildingTask]:
    return session.exec(select(BuildingTask)).all()


def get_building_task_by_id(session: SessionDep, task_id: int) -> Optional[BuildingTask]:
    return session.get(BuildingTask, task_id)


def create_building_task(session: SessionDep, task: BuildingTask) -> BuildingTask:
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def update_building_task(session: SessionDep, task: BuildingTask) -> BuildingTask:
    session.add(task)
    session.commit()
    session.refresh(task)
    return task


def delete_building_task(session: SessionDep, task_id: int) -> None:
    task = session.get(BuildingTask, task_id)
    if task:
        session.delete(task)
        session.commit()


def get_player_buildings_by_meta(session: SessionDep, meta_id: str) -> List[PlayerBuilding]:
    return session.exec(select(PlayerBuilding).where(PlayerBuilding.meta_id == meta_id)).all()


def get_building_tasks_by_player_building(session: SessionDep, player_building_id: int) -> BuildingTask:
    return session.exec(select(BuildingTask).where(BuildingTask.player_building_id == player_building_id)).one_or_none()


def get_building_tasks_by_player(session: SessionDep, player_id: int) -> List[BuildingTask]:
    return session.exec(select(BuildingTask).where(BuildingTask.player_id == player_id)).all()


def get_building_tasks_by_type(session: SessionDep, task_type: str) -> List[BuildingTask]:
    return session.exec(select(BuildingTask).where(BuildingTask.task_type == task_type)).all()


def get_building_tasks_by_status(session: SessionDep, status: str) -> List[BuildingTask]:
    return session.exec(select(BuildingTask).where(BuildingTask.status == status)).all()


def get_building_tasks_by_resource(session: SessionDep, resource_id: int) -> List[BuildingTask]:
    return session.exec(select(BuildingTask).where(BuildingTask.resource_id == resource_id)).all()


def get_building_tasks_between_dates(session: SessionDep, start_date: datetime, end_date: datetime) -> List[
    BuildingTask]:
    return session.exec(select(BuildingTask).where(
        and_(BuildingTask.start_time >= start_date, BuildingTask.end_time <= end_date))).all()


def get_building_tasks_count_by_player(session: SessionDep, player_id: int) -> int:
    return session.exec(select(func.count()).where(BuildingTask.player_id == player_id)).one()


def get_building_tasks_count_by_type(session: SessionDep, task_type: str) -> int:
    return session.exec(select(func.count()).where(BuildingTask.task_type == task_type)).one()


def get_building_tasks_count_by_status(session: SessionDep, status: str) -> int:
    return session.exec(select(func.count()).where(BuildingTask.status == status)).one()


def get_building_tasks_count_by_resource(session: SessionDep, resource_id: int) -> int:
    return session.exec(select(func.count()).where(BuildingTask.resource_id == resource_id)).one()


def get_building_tasks_count_between_dates(session: SessionDep, start_date: datetime, end_date: datetime) -> int:
    return session.exec(select(func.count()).where(
        and_(BuildingTask.start_time >= start_date, BuildingTask.end_time <= end_date))).one()


def get_building_meta_by_resource_id(session: SessionDep, resource_id: int) -> Optional[BuildingMeta]:
    """ 通过resource id 找到 building meta """
    statement = select(BuildingMeta).join(Recipe).where(Recipe.output_resource_id == resource_id)
    return session.exec(statement).one_or_none()
