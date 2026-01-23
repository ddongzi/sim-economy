from typing import List

from fastapi import APIRouter
from app.db.session import SessionDep
from app.crud import crud_resources, crud_recipe
from app.models import Recipe,ResourceCreate, RecipeCreate
from app.routers.api import recipe

router = APIRouter()
output_resource_id: int
duration: int
building_meta_id: str
@router.post("/")
async def create_resource(resource:ResourceCreate, session:SessionDep):
    """ 创建资源 ， """
    resource = crud_resources.create_resource(session, resource)
    return

@router.post("/recipe/")
async def create_recipe(recipe:RecipeCreate, session:SessionDep):
    """ 创建一个配方 """
    return crud_recipe.create_recipe(session, recipe)