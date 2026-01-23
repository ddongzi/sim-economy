class GameError(Exception):
    """ 游戏业务异常 """
    def __init__(self, message:str):
        self.message = message

from enum import Enum

class GameRespCode(Enum):
    """
    响应错误码
    1xxx auth
    2xxx 建筑
    3xxx 任务
    """
    BUILDING_IDLE = (3001, "BUILDING_IDLE", "建筑空闲中，没有任务")
    TASK_STALE = (3005, "TASK_STALE", "任务已经过时,已自动领取，查看仓库")
    BUILDING_BUSY = (3002, "BUILDING_BUSY","建筑已经在任务中")
    TASK_NOT_CLAIM = (3003, "TASK_NOT_CLAIM", "建筑任务完成，还未领取")
    @property
    def detail(self):
        return {
            "code": self.value[0],
            "id": self.value[1],
            "msg": self.value[2]
        }