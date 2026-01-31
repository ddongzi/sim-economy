from typing import List, Optional
from sqlmodel import select, func
from app.db.session import SessionDep
from app.models import Resource,ResourceCreate,ResourcePublic


# --- 增 ---
def create_resource(session: SessionDep, resource_in: ResourceCreate) -> Resource:
    # 将 Schema 转换为 Model
    db_obj = Resource.model_validate(resource_in)
    session.add(db_obj)
    return db_obj


# --- 查（单个） ---
def get_resource(session: SessionDep, resource_id: int) -> Optional[Resource]:
    return session.get(Resource, resource_id)


# --- 查（分页列表） ---
def get_resources_page(session: SessionDep, page: int = 1, page_size: int = 10):
    skip = (page - 1) * page_size
    statement = select(Resource).offset(skip).limit(page_size)
    items = session.exec(statement).all()

    # 获取总数用于前端分页器
    total = session.exec(select(func.count()).select_from(Resource)).one()
    return {"items": items, "total": total}

def get_resources_all(session: SessionDep) -> List[Resource]:
    statement = select(Resource)
    items = session.exec(statement).all()
    return list(items)

# --- 改 ---
def update_resource(session: SessionDep, db_obj: Resource, obj_in: ResourceCreate) -> Resource:
    # 转换为字典，并排除未传的字段 (exclude_unset=True)
    update_data = obj_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)

    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


# --- 删 ---
def delete_resource(session: SessionDep, resource_id: int) -> bool:
    db_obj = session.get(Resource, resource_id)
    if not db_obj:
        return False
    session.delete(db_obj)
    session.commit()
    return True
