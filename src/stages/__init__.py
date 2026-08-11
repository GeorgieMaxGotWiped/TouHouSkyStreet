# 关卡注册表

def get_stage_class(stage_num):
    """按关卡号返回关卡类；未注册返回 None"""
    from src.stages.stage1 import Stage1_SkyblockHub
    from src.stages.stage2 import Stage2_DragonsNest
    from src.stages.stage3 import Stage3_CatacombsF1
    return {1: Stage1_SkyblockHub, 2: Stage2_DragonsNest, 3: Stage3_CatacombsF1}.get(stage_num)


def get_next_stage_class(stage_num):
    """返回当前关卡通关后的下一关类；没有下一关返回 None"""
    return get_stage_class(stage_num + 1)
