# 示例：通过公式生成 10 个等级的配置
from sqlmodel import Session

from app.db.db import engine
from app.models import BuildingLevelsConfig


def generate_building_config(b_type, base_gold, base_duration):
    levels = []
    for lv in range(1, 11):  # 1级到10级
        # 指数增长公式：下一级费用 = 基础费用 * (1.5 ^ (lv-1))
        gold_cost = int(base_gold * (1.8 ** (lv - 1)))
        duration = int (base_duration * (1.8 ** (lv - 1)))
        levels.append({
            "building_meta_id": b_type,
            "level": lv,
            "cost": 0 if lv == 1 else gold_cost,
            "duration": 0 if lv == 1 else duration
        })
    return levels

all_configs = []
for b in ["farm_", "mine_plant_", "water_", "power_plant_", "house_assembly_plant_"]:
    all_configs.extend(generate_building_config(b, 500, 60 * 30))

def save_configs_to_db(configs):
    with Session(engine) as session:
        try:
            # 1. 先清空旧的配置（可选，防止重复）

            # 2. 批量转换成模型对象
            objects = [BuildingLevelsConfig(**item) for item in configs]

            # 3. 批量插入，效率极高
            session.bulk_save_objects(objects)
            session.commit()
            print(f"成功导入 {len(configs)} 条配置记录！")
        except Exception as e:
            session.rollback()
            print(f"导入失败: {e}")
if __name__ == "__main__":
    save_configs_to_db(all_configs)