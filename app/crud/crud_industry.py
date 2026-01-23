from app.models import Industry
from app.db.session import SessionDep
from typing import List, Optional
from sqlmodel import select
# 1. 创建 (Create)
def create_industry(session: SessionDep, industry_in: Industry) -> Industry:
    db_industry = Industry.model_validate(industry_in)
    session.add(db_industry)
    session.commit()
    session.refresh(db_industry)
    return db_industry


# 2. 读取全部 (Read All)
def get_industries(session: SessionDep) -> List[Industry]:
    return session.exec( select(Industry)).all()


# 3. 根据 ID 读取 (Read by ID)
def get_industry_by_id(session: SessionDep, industry_id: str) -> Optional[Industry]:
    return session.get(Industry, industry_id)


# 4. 更新 (Update)
def update_industry(session: SessionDep, industry_id: str, industry_in: Industry) -> Optional[Industry]:
    db_industry = session.get(Industry, industry_id)
    if not db_industry:
        return None

    # 提取非空数据并更新到数据库模型
    update_data = industry_in.model_dump(exclude_unset=True)
    db_industry.sqlmodel_update(update_data)

    session.add(db_industry)
    session.commit()
    session.refresh(db_industry)
    return db_industry


# 5. 删除 (Delete)
def delete_industry(session: SessionDep, industry_id: str) -> bool:
    db_industry = session.get(Industry, industry_id)
    if not db_industry:
        return False

    session.delete(db_industry)
    session.commit()
    return True
