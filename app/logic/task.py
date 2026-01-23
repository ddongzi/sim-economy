from app.models import BuildingTask, BuildingTaskCreate, BuildingTaskBase
from app.crud import crud_building,crud_resources,crud_recipe
from app.db.session import SessionDep
from decimal import Decimal,ROUND_UP
import math

def calculate_task_cost(session: SessionDep, task:BuildingTaskBase) :
    """计算任务成本。 设置task属性  数量-决定时间，  时间 对于 成本"""
    total_cost = 0

    # 建筑成本: 只和建筑本身meta有关
    recipe = crud_recipe.get_recipe_by_output_resource_id(session, task.resource_id)
    seconds =  math.floor(task.quantity / recipe.per_hour * 3600)
    hours = math.ceil(task.quantity / recipe.per_hour)
    task.duration = seconds

    building_meta = crud_building.get_building_meta_by_resource_id(session, task.resource_id)
    if not building_meta :
        print("get_building_meta_by_resource_id failed")
        task.cash_cost = -1
    total_cost += building_meta.maintenance_cost * hours

    # 原料成本. 还要考虑仓库. 原料按照基础价格或者市价
    for input in recipe.inputs:
        input_resource = crud_resources.get_resource(session, input.resource_id)
        total_cost += task.quantity * input.quantity * input_resource.base_price

    task.cash_cost = round(total_cost, 3)
    return task