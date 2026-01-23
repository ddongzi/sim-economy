from datetime import datetime,timezone
from enum import IntEnum, StrEnum

from sqlmodel import SQLModel, Field, Relationship,text
from time import time
from typing import Optional, List

# 行业， 建筑物/资源分类
class Industry(SQLModel, table=True):
    id: str = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True)
    icon: str = Field(default="bi-industry")

class PlayerBase(SQLModel):
    name:str
class Player(PlayerBase, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(default="")
    email: str = Field(default="example@gmail.com")
    password: str = Field(default="")

    is_bot: bool = Field(default=False, nullable=True)
    description: str = Field(default="", nullable=True)

    icon: str = Field(default="bi-building", nullable=True)
    level: int = Field(default=1, nullable=True)
    experience: int = Field(default=0, nullable=True)
    cash: float = Field(default=0, nullable=True)
    rating: str = Field(default="B", nullable=True)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
class PlayerPublic(PlayerBase):
    id:int
    name: str
    cash: float | None = 0.0
class PlayerCreate(PlayerBase):
    name: str
    email: str
    password: str
class PlayerLogin(PlayerBase):
    pass

class ResourceBase(SQLModel):
    name: str
    base_price: float
class Resource(ResourceBase, table=True):
    id: int = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    base_price: float = Field(default=0)
    icon: str = Field(default="bi-box")
    industry_id: str = Field(default=0, foreign_key="industry.id", nullable=True)

class ResourceCreate(ResourceBase):
    name: str
    base_price: int
    industry_id:str
class ResourcePublic(ResourceBase):
    id:int
    icon:str


class Plot(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    owner_id: int = Field(default=None, foreign_key="player.id")


# 配方 记录产出，耗时
class RecipeBase(SQLModel):
    output_resource_id: int
    per_hour: float
    building_meta_id: str
class Recipe(RecipeBase, table=True):
    id: int = Field(default=None, primary_key=True)
    output_resource_id: int = Field(default=None, foreign_key="resource.id", unique=True)
    per_hour: float = Field(description="每小时产出", default=0, nullable=True)
    building_meta_id: str = Field(default=None, foreign_key="building_meta.id")

    building: BuildingMeta = Relationship()
    output: Resource = Relationship()
    inputs: List[RecipeRequirement] = Relationship(back_populates="recipe")

class RecipeCreate(RecipeBase):
    inputs: List[RecipeRequirementCreate]

class RecipePublic(RecipeBase):
    id: int
    output: ResourcePublic
    inputs: List[RecipeRequirementPublic]

class RecipeRequirementBase(SQLModel):
    resource_id: int
    quantity: int
class RecipeRequirement(RecipeRequirementBase, table=True):
    """ 产出一个recipe resource所需 """
    __tablename__ = "recipe_requirement"
    id: int = Field(default=None, primary_key=True)
    recipe_id: int = Field(default=None, foreign_key="recipe.id")
    resource_id: int = Field(default=None, foreign_key="resource.id")
    quantity: int = Field(default=1)

    recipe: Recipe = Relationship(back_populates="inputs")
class RecipeRequirementPublic(RecipeRequirementBase):
    recipe_id: int
    id: int
class RecipeRequirementCreate(RecipeRequirementBase):
    pass

class InventoryBase(SQLModel):
    resource_id: int
    quantity:int
class Inventory(InventoryBase, table=True):
    """仓库item"""
    id: int = Field(default=None, primary_key=True)
    player_id: int = Field(default=None, foreign_key="player.id")
    resource_id: int = Field(default=None, foreign_key="resource.id")
    quantity: int = Field(default=0)
class InventoryPublic(InventoryBase):
    pass

# --- 1. 建筑原型 (元属性) ---
class BuildingMetaBase(SQLModel):
    id: str
    name: str
    building_cost: float
    industry_id: str
    maintenance_cost: float

class BuildingMeta(BuildingMetaBase, table=True):
    __tablename__ = "building_meta"
    id: str = Field(primary_key=True)  # 如: "steel_mill"
    name: str = Field(index=True)
    building_cost: float = Field(default=0,description="建造成本", nullable=True)

    maintenance_cost: float = Field(default=0, description="生产时候 每分钟维护成本", nullable=True)
    description: str = Field(default="")
    icon: str = Field(default="bi-box")

class BuildingMetaPublic(BuildingMetaBase):
    icon:str
class BuildingMetaCreate(BuildingMetaBase):
    pass

# --- 2. 玩家建筑实例 (状态属性) ---
class PlayerBuildingBase(SQLModel):
    building_meta_id: str
    slot_number: int | None = None

class PlayerBuilding(PlayerBuildingBase, table=True):
    __tablename__ = "player_building"
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    building_meta_id: str = Field(foreign_key="building_meta.id")
    slot_number: int = Field(default=0)

    level: int = Field(default=1)
    # status 建议设为枚举：idle (空闲), upgrading (升级中), producing (生产中)
    status: str = Field(default="idle")
    # 关系：关联回原型
    building_meta: BuildingMeta = Relationship()
class PlayerBuildingCreate(PlayerBuildingBase):
    pass
class PlayerBuildingPublic(PlayerBuildingBase):
    id: int
    building_meta: BuildingMetaPublic
    task: BuildingTask | None = None
    level: int
#
class BuildingTaskBase(SQLModel):
    resource_id:int
    quantity:int
    duration: int | None = None
    cash_cost: float | None = None # 可选

class BuildingTask(BuildingTaskBase, table=True):
    __tablename__ = "building_task"
    id: int | None = Field(default=None, primary_key=True)

    player_id: int = Field(foreign_key="player.id")
    # 关键修改：关联到玩家的具体建筑实例，而不是原型 ID
    player_building_id: int = Field(foreign_key="player_building.id", index=True)
    task_type: str = Field(default="production")  # "upgrade" (升级) 或 "production" (生产)

    # 任务产生的消耗/产出
    resource_id: Optional[int] = Field(default=None, foreign_key="resource.id")
    quantity: int = Field(default=0)
    cash_cost: float = Field(default=0)
    # 时间管理
    start_time: datetime = Field(default_factory=datetime.utcnow)
    duration: int = Field(nullable=True)  # seconds
    end_time: datetime = Field()

class BuildingTaskCreate(BuildingTaskBase):
    player_building_id: int
    start_time: datetime

# MarketOrder 订单
class MarketOrderBase(SQLModel):
    order_type: str
    resource_id: int
    price_per_unit: float

class MarketOrder(MarketOrderBase, table=True):
    __tablename__ = "market_order"
    id: int = Field(default=None, primary_key=True)
    # 发起者：买或者卖家
    player_id: int = Field(default=None, foreign_key="player.id")

    order_type: str = Field() # buy sell
    resource_id: int = Field(default=None, foreign_key="resource.id")
    quality: int = Field(default=0)

    total_quantity:int = Field(default=0)
    filled_quantity:int = Field(default=0) # 已经买/卖的数量

    price_per_unit: float = Field(default=0.1)

    # 0 进行中， 1完成 2撤单了
    status:int = Field(default=0, index=True)

    created_at: datetime = Field()
class MarketOrderPublic(MarketOrderBase):
    id:int
    quantity: int
    player_id: int
class MarketOrderCreate(MarketOrderBase):
    quantity:int = Field(ge=1)
    created_at: str

class ExchangeTradeHistory(SQLModel, table=True):
    """ 成交记录：交易额 """
    __tablename__ = "exchange_trade_history"
    id: int = Field(default=None, primary_key=True)

    # 关联字段
    resource_id: int = Field(foreign_key="resource.id")
    seller_id: int = Field(foreign_key="player.id")
    buyer_id: int = Field(foreign_key="player.id")

    # 核心数据：这一笔成交了多少？单价是多少？
    quantity: int = Field()
    price_per_unit: float = Field()

    # 冗余一个成交总额 (数学上：quantity * price_per_unit)
    # 记录它能极大地优化后续全服 GDP 的统计效率
    total_amount: float = Field()

    created_at: datetime = Field(default_factory=datetime.utcnow)


class Asset(SQLModel, table=True):
    """ 资产：房子/奢侈品 """
    id: int = Field(default=None, primary_key=True)
    name: str
    price:float

class PlayerAsset(SQLModel, table=True):
    __tablename__ = "player_asset"
    id: int = Field(default=None, primary_key=True)
    player_id: int = Field(default=None, foreign_key="player.id")
    asset_id: int = Field(default=None, foreign_key="asset.id")

class TransactionActionType(IntEnum):
    PRODUCE_COST = 1    # 生产消耗
    MARKET_SELL = 2     # 交易所出售所得
    MARKET_BUY = 3     # 交易所收入所得

    MARKET_REFUND = 5 # 交易所成交差价 退回
    MATCH_CONFLICT_REFUND = 7 # 撮合订单中 异常退回

    BUILD_COST = 6 # 建筑建造成本消耗
    BUILD_REVENUE = 8 # 系统收取建筑建造费用

    QUEST_REWARD = 10    # 任务奖励
    ADMIN_ADJUST = 11    # 后台调整

    NEW_PLAYER_INITIAL_REVENUE = 12 # 新用户初始资金
    SYSTEM_NEW_PLAYER_COST = 13 #新用户初始资金支出

    CONTRACT_COST = 14 # 合同支出
    CONTRACT_REVENUE = 15 # 合同收入

    BUILDING_UPGRADE_COST = 16 # 建筑升级指出
    SYSTEM_BUILDING_UPGRADE_REVENUE = 17 # 系统收取升级费用


class TransactionLog(SQLModel, table=True):
    """ 全服记账表 """
    __tablename__ = "transaction_log"
    id: int = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id")
    action_type: int = Field(default=-1,description="0交易 1任务 3消耗 4 退款")
    before_balance: float= Field(default=0, description="变动余额")
    change_amount: float = Field(default=0, description="变动金额")
    after_balance: float = Field(default=0, description="变动后余额")
    created_at: datetime = Field(default_factory=datetime.now)
    ref_id: int = Field(default=None, description="关联的交易id，任务id 等")
class ContractStatus(StrEnum):
    PENDING = "pending"     # 待签署（发起方已创建）
    SIGNED = "signed"       # 已签署（对方已同意，资金/货权交割中或已完成）
    CANCELLED = "cancelled" # 发送方已取消,
    REJECTED = "rejected"  # 接收方拒绝
    FAILED = "failed"       # 交易失败（如签署时发现余额/库存不足）

class SpotContract(SQLModel, table=True):
    """ 现货合同 """
    __tablename__ = "spot_contract"
    id: int = Field(default=None, primary_key=True)
    contract_no: str = Field(unique=True, index=True, description="合同编号", nullable=True)

    sender_id: int = Field(default=None, foreign_key="player.id")
    receiver_id: int = Field(default=None, foreign_key="player.id")

    resource_id: int = Field(default=None, foreign_key="resource.id")
    quantity: int
    price_per_unit: float
    total_amount: float = Field(description="冗余字段")

    status: ContractStatus = Field(default=ContractStatus.PENDING)

    created_at: datetime = Field(default_factory=datetime.now)
    signed_at: datetime = Field(default=None, nullable=True)
    expires_at: datetime = Field(default=None)

    note: str = Field(default=None, description="留言")

    is_recurring: bool = Field(default=False, description="是否为长期协议：自动化现货", nullable=True)
    frequency: str = Field(default="daily", nullable=True)
    last_executed_at: datetime = Field(default=None, nullable=True)
class SpotContractBase(SQLModel):
    pass

class SpotContractCreate(SpotContractBase):
    receiver_id: int
    resource_id: int
    quantity: int
    price_per_unit: float
    total_amount: float
    status: ContractStatus = Field(default=ContractStatus.PENDING)
    expires_at:datetime
    note: str = Field(default="")

class BuildingLevelsConfig(SQLModel, table=True):
    __tablename__ = "building_levels_config"
    id: int = Field(default=None, primary_key=True)
    building_meta_id: str = Field(default=None, foreign_key="building_meta.id",index=True)
    level: int = Field(description="升级到这个级别")
    cost: float = Field(default=0)
    duration: int = Field(default=0, description="升级耗时 秒")





