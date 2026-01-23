from typing import List, Optional
from sqlalchemy import exc
from sqlmodel import select, func, delete, col
from app.db.session import SessionDep
from app.models import Recipe, RecipeRequirement, RecipeCreate


# --- 增 ---
def create_recipe(session: SessionDep, recipe_in: RecipeCreate) -> Recipe:
    """ 创建配方 及requirement关联 """
    # 1. 转换基础数据
    data = recipe_in.model_dump(exclude={"inputs"})
    db_obj = Recipe(**data)
    # 2. 处理关联关系
    if recipe_in.inputs:
        for req_in in recipe_in.inputs:
            # 创建真正的数据库模型对象
            db_requirement = RecipeRequirement(
                resource_id=req_in.resource_id,
                quantity=req_in.quantity
                # 注意：这里不需要手动设置 recipe_id，SQLAlchemy 会自动帮你关联
            )
            # 只要添加到 append 到主对象的 relationship 属性即可
            db_obj.inputs.append(db_requirement)

    # 3. 统一入库
    session.add(db_obj)
    session.commit()

    # 4. 刷新数据以确保 db_obj 包含数据库生成的 ID 和关联数据
    session.refresh(db_obj)
    return db_obj


# --- 查 (列表) ---
def get_recipes(session: SessionDep, page: int = 1, page_size: int = 10):
    skip = (page - 1) * page_size
    statement = select(Recipe).offset(skip).limit(page_size)
    items = session.exec(statement).all()

    total = session.exec(select(func.count()).select_from(Recipe)).one()
    return {"items": items, "total": total}

def get_recipes_all(session: SessionDep):
    statement = select(Recipe)
    items = session.exec(statement).all()
    return items

# --- 查 (单个) ---
def get_recipe(session: SessionDep, recipe_id: int) -> Optional[Recipe]:
    return session.get(Recipe, recipe_id)

def get_recipe_by_input_resource_id(session: SessionDep, resource_id: int) -> List[Recipe]:
    return list(session.exec(
        select(Recipe).where(Recipe.input_resource_id == resource_id)
    ).all())
def get_recipe_by_output_resource_id(session: SessionDep, resource_id: int) -> Recipe:
    return session.exec(
        select(Recipe).where(Recipe.output_resource_id == resource_id)
    ).one_or_none()

# --- 改 ---
def update_recipe(session: SessionDep, db_obj: Recipe, obj_in: Recipe) -> Recipe:
    update_data = obj_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_obj, key, value)

    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


# --- 删 ---
def delete_recipe(session: SessionDep, recipe_id: int) -> bool:
    db_obj = session.get(Recipe, recipe_id)
    if not db_obj:
        return False
    session.delete(db_obj)
    session.commit()
    return True
def delete_recipes_by_output_resource_id(session: SessionDep, resource_id: int) -> bool:
    try:
        recipes = session.exec(select(Recipe).where(Recipe.output_resource_id == resource_id)).all()
        if not recipes:
            print("no delete recipes found")
            return False
        for recipe in recipes:
            session.delete(recipe)
        session.commit()
        return True
    except Exception as e:
        print(e)
        return False