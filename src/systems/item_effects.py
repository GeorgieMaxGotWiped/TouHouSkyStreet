# 物品被动效果聚合
# 根据当前装备（含重铸前缀）聚合出战斗用效果字典。
#
# 约定：大多数 +xx% 为加算；增加爆率用乘算（drop_rate_mult / epic_drop_rate_mult）。

from src.systems.item_system import (
    EQUIPMENT_SLOTS,
    SKYBLOCK_ITEMS,
    REFORGES,
    C_SKILLS,
)

# 套装定义：item_id 列表 -> 套装标识
ARMOR_SETS = {
    "lapis": ("lapis_armor_helmet", "lapis_armor_chestplate",
              "lapis_armor_leggings", "lapis_armor_boots"),
    "heavy": ("heavy_armor_helmet", "heavy_armor_chestplate",
              "heavy_armor_leggings", "heavy_armor_boots"),
}


def _empty_effects():
    return {
        "damage_pct": 0.0,                # 总伤害加算%
        "minion_damage_pct": 0.0,         # 对小怪伤害%
        "bomb_damage_pct": 0.0,           # BOMB伤害%
        "coin_drop_pct": 0.0,             # Coin掉落% （加算）
        "drop_rate_mult": 1.0,            # 所有掉落概率乘算
        "epic_drop_rate_mult": 1.0,       # EPIC及以上掉落概率乘算
        "speed_pct": 0.0,                 # 移速加算%
        "high_speed_pct": 0.0,            # 高速态移速%
        "graze_speed_pct": 0.0,           # 有敌弹在擦弹范围内时移速%
        "hit_cancel_chance": 0.0,         # 被弹抵消概率%
        "hitbox_scale": 1.0,              # 判定点缩放（1=原始）
        "tracking_damage_pct": 0.0,       # 追踪弹伤害%
        "non_tracking_damage_pct": 0.0,   # 非追踪弹伤害%
        "tracking_high_speed_damage_pct": 0.0,  # 高速态追踪弹伤害%
        "fixed_bullet_speed_pct": 0.0,    # 低速态固定弹射速%
        "graze_slow_pct": 0.0,            # 低速态擦弹范围内敌弹减速%
        "fixed_bullet_add": 0,            # 固定弹道调整（负=减少）
        "tracking_bullet_add": 0,         # 追踪弹道调整
        "start_bombs": 0,                 # 关卡开始+BOMB
        "start_lives": 0,                 # 关卡开始+残机
        "end_no_hit_lives": 0,            # 关卡结束未失残机+残机
        "end_no_hit_bombs": 0,            # 关卡结束未失残机+BOMB
        "end_lost_over1_bombs": 0,        # 关卡结束失去残机>1+BOMB
        "kill50_bombs": 0,                # 每50杀+BOMB
        "kill50_lives": 0,                # 每50杀+残机
        "kill_small_coins": 0,            # 击杀小怪金币
        "kill_boss_coins": 0,             # 击杀BOSS金币
        "kill_small_damage_pct": 0.0,     # 击杀小怪堆叠伤害%每只
        "kill_boss_damage_pct": 0.0,      # 击杀BOSS堆叠伤害%每只
        "midboss_damage_pct": 0.0,        # 对道中BOSS伤害%
        "wither_damage_pct": 0.0,         # 对凋零伤害%
        "terminator": False,              # 散射夹角覆盖
        "reforge_ancient_stage_pct": False,  # Ancient：+当前面数%
        "arack_pct": 0.0,                 # 失残机后10s伤害%
        "spider_artifact": False,         # 蜘蛛护符
        "deathbomb_refund": 0,            # 决死Bomb 2B回1B
        "graze_shield": False,            # 预留
    }


def _merge(target, effects):
    """把 effects 条目并入聚合结果。数值类加算；乘算类相乘；布尔类取或。"""
    if not effects:
        return
    for key, value in effects.items():
        if value is None:
            continue
        if key not in target:
            continue
        if key in ("drop_rate_mult", "epic_drop_rate_mult", "hitbox_scale"):
            target[key] *= float(value)
        elif isinstance(value, bool):
            target[key] = target[key] or value
        else:
            try:
                target[key] = target.get(key, 0) + float(value)
            except (TypeError, ValueError):
                pass


def aggregate_effects(inventory, stage_num=1):
    """根据当前装备与重铸前缀聚合效果。stage_num 用于 Ancient 前缀。"""
    eff = _empty_effects()
    equipped = inventory.get_equipped_ids()
    equipped_set = set(equipped)

    for item_id in equipped:
        item = SKYBLOCK_ITEMS.get(item_id)
        if item is None:
            continue
        _merge(eff, item.effects)
        prefix_id = inventory.get_item_prefix(item_id)
        if prefix_id and prefix_id in REFORGES:
            _merge(eff, REFORGES[prefix_id].get("effects", {}))

    # 套装加成
    for set_id, member_ids in ARMOR_SETS.items():
        if all(mid in equipped_set for mid in member_ids):
            if set_id == "lapis":
                eff["epic_drop_rate_mult"] *= 1.2
            elif set_id == "heavy":
                eff["high_speed_pct"] += 20.0

    # Ancient：造成+X%伤害，X为当前面数
    if eff["reforge_ancient_stage_pct"]:
        eff["damage_pct"] += float(stage_num)

    return eff


def has_c_skill(item_id):
    return item_id in C_SKILLS
