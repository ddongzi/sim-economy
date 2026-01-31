from typing import List

from fastapi import APIRouter, HTTPException
from sqlmodel import select
from app.db.session import SessionDep
from app.crud import crud_resources, crud_recipe
from app.models import Recipe, ResourceCreate, RecipeCreate, UpdateResourceRecipeRequest, Resource, RecipeRequirement
from app.routers.api import recipe

router = APIRouter()
output_resource_id: int
duration: int
building_meta_id: str
@router.post("/")
async def create_resource(resource:ResourceCreate, session:SessionDep):
    """ 创建资源 ， """
    resource = crud_resources.create_resource(session, resource)
    session.commit()
    return

@router.post("/recipe/")
async def create_recipe(recipe:RecipeCreate, session:SessionDep):
    """ 创建一个配方 """
    return crud_recipe.create_recipe(session, recipe)

@router.post("/update")
async def update_resource_and_recipe(model:UpdateResourceRecipeRequest,session:SessionDep):
    """ 更新资源 和 recipe """
    resource = session.exec(
        select(Resource).where(Resource.id == model.resource_id)
    ).one_or_none()
    resource.base_price = model.base_price
    resource.base_weight = model.base_weight
    session.add(resource)
    session.flush()

    recipe = None
    if not model.recipe_id:
        # 如果还没有创建recipe， 就创建
        recipe = Recipe(
            output_resource_id = resource.id,
            building_meta_id = model.building_meta_id,
            per_hour = model.per_hour
        )
        session.add(recipe)
        session.flush()
    else:
        recipe = session.exec(
            select(Recipe).where(Recipe.id == model.recipe_id)
        ).one_or_none()
        if recipe.output_resource_id != resource.id:
            raise HTTPException(status_code=400, detail="参数错误")

    recipe.per_hour = model.per_hour
    session.add(recipe)
    session.flush()

    ingredients = session.exec(
        select(RecipeRequirement).where(RecipeRequirement.recipe_id == recipe.id)
    ).all()
    for ingredient in ingredients:
        session.delete(ingredient)
    for item in model.inputs:
        new_ingredient = RecipeRequirement(
            recipe_id = recipe.id,
            resource_id = item.resource_id,
            quantity = item.quantity,
        )
        session.add(new_ingredient)
    session.commit()

    return {"msg": "ok"}



