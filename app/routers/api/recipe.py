from fastapi import APIRouter
from app.crud.crud_recipe import get_recipes
from app.models import BuildingTaskCreate
from app.logic.task import calculate_task_cost
from app.db.session import SessionDep
router = APIRouter()

@router.get("/")
async def get_recipes():

    pass

