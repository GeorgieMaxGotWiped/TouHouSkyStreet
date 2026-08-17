# Skyblock 物品系统
# 物品定义、掉落、背包、装备、商店价格与效果数据
#
# 效果数值约定：
#   - 大多数 +xx% 为加算（直接累加百分比）；唯一特例：增加爆率类用乘算。
#   - C 技能 = 按 C 释放，无上限次数，但无特殊说明时每一面中只能使用一次；
#     同时只能装备 1 件带 C 技能的物品。

import random
from src.engine import settings as cfg

# 装备槽顺序：界面与存档都使用这个顺序
EQUIPMENT_SLOTS = ["helmet", "chestplate", "leggings", "boots", "weapon", "accessory"]

SLOT_LABELS = {
    "helmet": "头盔",
    "chestplate": "胸甲",
    "leggings": "护腿",
    "boots": "靴子",
    "weapon": "武器",
    "accessory": "护符",
}

SLOT_TO_ITEM_TYPE = {
    "helmet": "armor",
    "chestplate": "armor",
    "leggings": "armor",
    "boots": "armor",
    "weapon": "weapon",
    "accessory": "accessory",
}

ITEM_TYPE_LABELS = {
    "weapon": "武器",
    "armor": "护甲",
    "accessory": "护符",
    "consumable": "消耗品",
    "material": "材料",
    "reforge_stone": "重铸石",
}

# 商店分类顺序（休整界面按此顺序展示）
SHOP_CATEGORY_ORDER = ["weapon", "armor", "accessory", "reforge_stone", "material"]


def parse_price(text):
    """把 10k / 1.5M / 1B 形式的字符串价格解析为整数金币。"""
    if text is None or text == "" or text == "/":
        return 0
    s = str(text).strip().upper().replace(" ", "")
    mult = 1
    if s.endswith("K"):
        mult = 1000
        s = s[:-1]
    elif s.endswith("M"):
        mult = 1000000
        s = s[:-1]
    elif s.endswith("B"):
        mult = 1000000000
        s = s[:-1]
    try:
        return int(round(float(s) * mult))
    except (TypeError, ValueError):
        return 0


# 效果条目 -> 中文说明（自动生成 lore 用）
_EFFECT_LORE = {
    "damage_pct": "伤害+{}%",
    "minion_damage_pct": "对小怪伤害+{}%",
    "bomb_damage_pct": "BOMB伤害+{}%",
    "coin_drop_pct": "Coin掉落+{}%",
    "drop_rate_mult": "所有掉落概率+{}%（乘算）",
    "epic_drop_rate_mult": "EPIC及以上物品获取概率+{}%（乘算）",
    "speed_pct": "移动速度{:+}%",
    "high_speed_pct": "高速状态移动速度+{}%",
    "graze_speed_pct": "有敌弹在擦弹范围内时移速+{}%",
    "hit_cancel_chance": "{}%概率被弹时将其抵消",
    "hitbox_scale": "判定点缩小{}%",
    "tracking_damage_pct": "追踪弹伤害+{}%",
    "non_tracking_damage_pct": "非追踪弹伤害+{}%",
    "tracking_high_speed_damage_pct": "高速状态追踪弹伤害+{}%",
    "fixed_bullet_speed_pct": "低速状态固定弹射速+{}%",
    "graze_slow_pct": "低速状态擦弹范围内敌弹速度-{}%",
    "fixed_bullet_add": "固定弹道{}条",
    "tracking_bullet_add": "追踪弹道+{}条",
    "start_bombs": "关卡开始时+1BOMB",
    "start_lives": "关卡开始时+1残机",
    "end_no_hit_lives": "关卡结束时未失去残机则+1残机",
    "end_no_hit_bombs": "关卡结束时未失去残机则+1BOMB",
    "end_lost_over1_bombs": "关卡结束时若失去残机>1则+1BOMB",
    "kill50_bombs": "每消灭50只怪物获得1BOMB",
    "kill50_lives": "每消灭50只怪物获得1残机",
    "kill_small_coins": "击杀1个小怪获得100K Coin",
    "kill_boss_coins": "击杀1个BOSS获得10M Coin",
    "kill_small_damage_pct": "每击杀1个小怪本关伤害+0.3%",
    "kill_boss_damage_pct": "每击杀1个BOSS本关伤害+3%",
    "midboss_damage_pct": "对道中BOSS伤害+{}%",
    "wither_damage_pct": "对凋零伤害+{}%",
    "terminator": "高速状态散射夹角9°/条，低速状态1°/条",
    "reforge_ancient_stage_pct": "伤害+X%（X=当前面数）",
    "arack_pct": "失去1残机后的10秒内伤害+35%",
    "spider_artifact": "失去1残机后的10秒内再次失去残机时，改为失去1B并放出决死Bomb",
    "deathbomb_refund": "使用决死Bomb消耗2B时回复1B",
}


def build_lore(effects):
    """根据效果数据自动生成中文说明行。"""
    lines = []
    if not effects:
        return lines
    for key, value in effects.items():
        if value is False or value is None or value == 0:
            continue
        fmt = _EFFECT_LORE.get(key)
        if fmt is None:
            continue
        if isinstance(value, bool):
            lines.append(fmt)
        elif key in ("fixed_bullet_add",):
            lines.append(fmt.format(value))
        elif key in ("hitbox_scale",):
            lines.append(fmt.format(int(round((1 - value) * 100))))
        elif key in ("drop_rate_mult", "epic_drop_rate_mult"):
            pct = int(round((value - 1) * 100))
            lines.append(fmt.format(pct))
        else:
            lines.append(fmt.format(value))
    return lines


class SkyblockItem:
    """Skyblock物品"""

    def __init__(self, id, name, rarity, item_type, stats=None, lore=None,
                 slot=None, buy_price=0, sell_price=None, effects=None):
        self.id = id
        self.name = name
        self.rarity = rarity  # COMMON / UNCOMMON / RARE / EPIC / LEGENDARY / MYTHIC / DIVINE / SPECIAL
        self.item_type = item_type  # weapon / armor / accessory / consumable / material / reforge_stone
        self.stats = stats or {}
        self.effects = dict(effects or {})
        self.lore = lore if lore is not None else build_lore(self.effects)
        self.slot = slot
        self.buy_price = parse_price(buy_price)
        if sell_price is None:
            self.sell_price = max(1, self.buy_price // 5) if self.buy_price > 0 else 0
        else:
            self.sell_price = parse_price(sell_price)

    @property
    def is_equippable(self):
        return self.slot in EQUIPMENT_SLOTS

    @property
    def can_reforge(self):
        """武器 / 护甲可以使用重铸石打前缀"""
        return self.item_type in ("weapon", "armor")

    @property
    def rarity_color(self):
        return cfg.RARITY_COLORS.get(self.rarity, cfg.COLOR_WHITE)

    @property
    def rarity_display(self):
        return self.rarity.capitalize()

    def stat_text(self):
        if not self.stats:
            return ""
        return "  ".join(f"{k}: {v}" for k, v in self.stats.items())

    def __repr__(self):
        return f"[{self.rarity}] {self.name}"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rarity": self.rarity,
            "type": self.item_type,
            "slot": self.slot,
            "stats": self.stats,
            "buy_price": self.buy_price,
            "sell_price": self.sell_price,
        }


# --- 物品定义 ------------------------------------------------------------

SKYBLOCK_ITEMS = {
    # ============ 武器 ============
    "aspect_of_the_jerry": SkyblockItem(
        "aspect_of_the_jerry", "Aspect of the Jerry", "COMMON", "weapon",
        effects={"damage_pct": 1},
        slot="weapon", buy_price="10k", sell_price="1k",
    ),
    "undead_sword": SkyblockItem(
        "undead_sword", "Undead Sword", "COMMON", "weapon",
        effects={"minion_damage_pct": 10},
        slot="weapon", buy_price="50k", sell_price="10k",
    ),
    "sword_of_bad_health": SkyblockItem(
        "sword_of_bad_health", "Sword of Bad Health", "UNCOMMON", "weapon",
        effects={},
        lore=["C技能：消耗1残机，10秒内友方造成的伤害+200%"],
        slot="weapon", buy_price="200k", sell_price="40k",
    ),
    "bonzos_staff": SkyblockItem(
        "bonzos_staff", "Bonzo's Staff", "RARE", "weapon",
        effects={},
        lore=["C技能：放出3个随机方向有后坐力的气球，碰到弹幕后爆炸"],
        slot="weapon", buy_price="5M", sell_price="2M",
    ),
    "golem_sword": SkyblockItem(
        "golem_sword", "Golem Sword", "RARE", "weapon",
        effects={},
        lore=["C技能：钢铁之击（每面可以使用4次）", "炸掉擦弹范围内所有弹幕"],
        slot="weapon", buy_price="2M", sell_price="500k",
    ),
    "aspect_of_the_end": SkyblockItem(
        "aspect_of_the_end", "Aspect of the End", "RARE", "weapon",
        effects={},
        lore=["C技能：向当前移动方向瞬移一段距离"],
        slot="weapon", buy_price="1M", sell_price="500k",
    ),
    "arack": SkyblockItem(
        "arack", "Arack", "EPIC", "weapon",
        effects={"arack_pct": 35},
        lore=["失去1残机后的10秒内造成+35%伤害"],
        slot="weapon", buy_price="300k", sell_price="100k",
    ),
    "end_stone_sword": SkyblockItem(
        "end_stone_sword", "End Stone Sword", "EPIC", "weapon",
        effects={},
        lore=["C技能：2秒内无法移动且无法受伤（每面可以使用3次）"],
        slot="weapon", buy_price="2M", sell_price="500k",
    ),
    "wither_cloak_sword": SkyblockItem(
        "wither_cloak_sword", "Wither Cloak Sword", "EPIC", "weapon",
        effects={},
        lore=["C技能：在周围召唤6个护盾，持续10秒",
              "6个护盾围绕自机旋转，位置约在擦弹处，碰到敌弹将其抵消并失去该护盾"],
        slot="weapon", buy_price="5M", sell_price="2M",
    ),
    "spirit_bow": SkyblockItem(
        "spirit_bow", "Spirit Bow", "EPIC", "weapon",
        effects={},
        lore=["C技能：接下来的10秒内所有自机子弹都变为追踪弹"],
        slot="weapon", buy_price="3M", sell_price="1.5M",
    ),
    "aspect_of_the_dragons": SkyblockItem(
        "aspect_of_the_dragons", "Aspect of the Dragons", "LEGENDARY", "weapon",
        effects={},
        lore=["C技能：放出龙怒炸掉上方一定距离的所有弹幕，并对BOSS造成大量伤害", "伤害4800"],
        slot="weapon", buy_price="15M", sell_price="10M",
    ),
    "flower_of_truth": SkyblockItem(
        "flower_of_truth", "Flower of Truth", "LEGENDARY", "weapon",
        effects={},
        lore=["C技能：放出1个玫瑰，追踪并消灭距离最近的3个弹幕，并对BOSS造成一定伤害（每面两次）",
              "3次后飞向BOSS并对其造成1200伤害"],
        slot="weapon", buy_price="6M", sell_price="3M",
    ),
    "giants_sword": SkyblockItem(
        "giants_sword", "Giant's Sword", "LEGENDARY", "weapon",
        effects={},
        lore=["C技能：召唤大剑清除场上所有弹幕，并对BOSS造成当前阶段50%的伤害"],
        slot="weapon", buy_price="100M", sell_price="75M",
    ),
    "hyperion": SkyblockItem(
        "hyperion", "Hyperion", "LEGENDARY", "weapon",
        effects={"bomb_damage_pct": 25, "deathbomb_refund": 1},
        slot="weapon", buy_price="1B", sell_price="750M",
    ),
    "terminator": SkyblockItem(
        "terminator", "Terminator", "LEGENDARY", "weapon",
        effects={"non_tracking_damage_pct": 35, "terminator": True},
        lore=["非追踪弹+35%伤害", "高速状态散射夹角9°/条，低速状态1°/条"],
        slot="weapon", buy_price="1B", sell_price="400M",
    ),
    "dark_claymore": SkyblockItem(
        "dark_claymore", "Dark Claymore", "LEGENDARY", "weapon",
        effects={"damage_pct": 25},
        slot="weapon", buy_price="1B", sell_price="100M",
    ),

    # ============ 护甲 ============
    "lapis_armor_helmet": SkyblockItem(
        "lapis_armor_helmet", "Lapis Armor Helmet", "UNCOMMON", "armor",
        effects={"coin_drop_pct": 3},
        lore=["+3% Coin掉落", "4件全套：所有EPIC及以上物品+20%获取概率"],
        slot="helmet", buy_price="80k", sell_price="30k",
    ),
    "lapis_armor_chestplate": SkyblockItem(
        "lapis_armor_chestplate", "Lapis Armor Chestplate", "UNCOMMON", "armor",
        effects={"kill_small_coins": 100000},
        lore=["击杀1个小怪时获得100K Coin", "4件全套：所有EPIC及以上物品+20%获取概率"],
        slot="chestplate", buy_price="150k", sell_price="30k",
    ),
    "lapis_armor_leggings": SkyblockItem(
        "lapis_armor_leggings", "Lapis Armor Leggings", "UNCOMMON", "armor",
        effects={"kill_boss_coins": 10000000},
        lore=["击杀1个BOSS时获得10M Coin", "4件全套：所有EPIC及以上物品+20%获取概率"],
        slot="leggings", buy_price="120k", sell_price="30k",
    ),
    "lapis_armor_boots": SkyblockItem(
        "lapis_armor_boots", "Lapis Armor Boots", "UNCOMMON", "armor",
        effects={"coin_drop_pct": 2},
        lore=["+2% Coin掉落", "4件全套：所有EPIC及以上物品+20%获取概率"],
        slot="boots", buy_price="100k", sell_price="30k",
    ),
    "heavy_armor_helmet": SkyblockItem(
        "heavy_armor_helmet", "Heavy Armor Helmet", "RARE", "armor",
        effects={"hit_cancel_chance": 6, "speed_pct": -6},
        lore=["6%概率被弹时将其抵消；移动速度-6%", "4件全套：高速状态移动速度+20%"],
        slot="helmet", buy_price="1M", sell_price="500k",
    ),
    "heavy_armor_chestplate": SkyblockItem(
        "heavy_armor_chestplate", "Heavy Armor Chestplate", "RARE", "armor",
        effects={"hit_cancel_chance": 15, "speed_pct": -15},
        lore=["15%概率被弹时将其抵消；移动速度-15%", "4件全套：高速状态移动速度+20%"],
        slot="chestplate", buy_price="2M", sell_price="1M",
    ),
    "heavy_armor_leggings": SkyblockItem(
        "heavy_armor_leggings", "Heavy Armor Leggings", "RARE", "armor",
        effects={"hit_cancel_chance": 12, "speed_pct": -12},
        lore=["12%概率被弹时将其抵消；移动速度-12%", "4件全套：高速状态移动速度+20%"],
        slot="leggings", buy_price="1.5M", sell_price="750k",
    ),
    "heavy_armor_boots": SkyblockItem(
        "heavy_armor_boots", "Heavy Armor Boots", "RARE", "armor",
        effects={"hit_cancel_chance": 10, "speed_pct": -10},
        lore=["10%概率被弹时将其抵消；移动速度-10%", "4件全套：高速状态移动速度+20%"],
        slot="boots", buy_price="1M", sell_price="500k",
    ),
    "wither_goggles": SkyblockItem(
        "wither_goggles", "Wither Goggles", "EPIC", "armor",
        effects={"bomb_damage_pct": 50},
        slot="helmet", buy_price="10M", sell_price="5M",
    ),
    "shadow_assassin_boots": SkyblockItem(
        "shadow_assassin_boots", "Shadow Assassin Boots", "EPIC", "armor",
        effects={"kill_small_damage_pct": 0.3, "kill_boss_damage_pct": 3},
        lore=["每关中击杀1个小怪本关伤害+0.3%，击杀1个BOSS本关伤害+3%"],
        slot="boots", buy_price="5M", sell_price="3M",
    ),
    "tarantula_helmet": SkyblockItem(
        "tarantula_helmet", "Tarantula Helmet", "EPIC", "armor",
        effects={"end_lost_over1_bombs": 1},
        lore=["C技能：关卡结束时若失去残机>1，获得1BOMB"],
        slot="helmet", buy_price="5M", sell_price="3M",
    ),
    "tarantula_boots": SkyblockItem(
        "tarantula_boots", "Tarantula Boots", "EPIC", "armor",
        lore=["C技能：清除当前移动方向上最近的1个弹幕并快速移动至其位置"],
        slot="boots", buy_price="5M", sell_price="3M",
    ),
    "necromancer_lord_leggings": SkyblockItem(
        "necromancer_lord_leggings", "Necromancer Lord Leggings", "LEGENDARY", "armor",
        effects={"end_no_hit_lives": 1, "end_no_hit_bombs": 1},
        lore=["关卡结束时若未失去残机，+1残机，+1BOMB"],
        slot="leggings", buy_price="40M", sell_price="10M",
    ),
    "precursor_eye": SkyblockItem(
        "precursor_eye", "Precursor Eye", "LEGENDARY", "armor",
        effects={},
        lore=["C技能：向上射出1道持续3秒的红色激光（帧伤20）"],
        slot="helmet", buy_price="40M", sell_price="20M",
    ),
    "superior_dragon_chestplate": SkyblockItem(
        "superior_dragon_chestplate", "Superior Dragon Chestplate", "LEGENDARY", "armor",
        effects={"damage_pct": 10, "drop_rate_mult": 1.1},
        slot="chestplate", buy_price="25M", sell_price="15M",
    ),
    "storms_leggings": SkyblockItem(
        "storms_leggings", "Storm's Leggings", "LEGENDARY", "armor",
        effects={"bomb_damage_pct": 35, "start_bombs": 1},
        slot="chestplate", buy_price="50M", sell_price="30M",
    ),
    "goldors_helmet": SkyblockItem(
        "goldors_helmet", "Goldor's Helmet", "LEGENDARY", "armor",
        effects={"start_lives": 1},
        slot="chestplate", buy_price="35M", sell_price="25M",
    ),
    "necrons_chestplate": SkyblockItem(
        "necrons_chestplate", "Necron's Chestplate", "LEGENDARY", "armor",
        effects={"non_tracking_damage_pct": 40},
        slot="chestplate", buy_price="65M", sell_price="50M",
    ),
    "maxors_boots": SkyblockItem(
        "maxors_boots", "Maxor's Boots", "LEGENDARY", "armor",
        effects={"speed_pct": 25, "hitbox_scale": 0.5},
        slot="chestplate", buy_price="30M", sell_price="20M",
    ),

    # ============ 护符 ============
    "balloon_snake": SkyblockItem(
        "balloon_snake", "Balloon Snake", "RARE", "accessory",
        effects={"tracking_high_speed_damage_pct": 20},
        lore=["高速状态下追踪弹伤害+20%"],
        slot="accessory", buy_price="3M", sell_price="2M",
    ),
    "maddox_batphone": SkyblockItem(
        "maddox_batphone", "Maddox Batphone", "RARE", "accessory",
        effects={"kill50_bombs": 1},
        lore=["每消灭50只怪物获得1BOMB"],
        slot="accessory", buy_price="1M", sell_price="200k",
    ),
    "overflux_power_orb": SkyblockItem(
        "overflux_power_orb", "Overflux Power Orb", "RARE", "accessory",
        effects={},
        lore=["C技能：Boss战中召唤Orb，若接下来10秒内持续处在Orb范围内获得1残机",
              "Orb判定大小约等于擦弹范围"],
        slot="accessory", buy_price="10M", sell_price="6M",
    ),
    "summoning_ring": SkyblockItem(
        "summoning_ring", "Summoning Ring", "RARE", "accessory",
        effects={},
        lore=["C技能：随机召唤2只归属于你的小怪",
              "反向移动、反向射击（自机狙锁Boss），弹幕可抵消敌弹或对敌人造成150伤害，不对玩家造成伤害"],
        slot="accessory", buy_price="20M", sell_price="10M",
    ),
    "tarantula_pet": SkyblockItem(
        "tarantula_pet", "Tarantula Pet", "RARE", "accessory",
        effects={"graze_speed_pct": 20},
        lore=["有敌弹在擦弹范围内时移速+20%"],
        slot="accessory", buy_price="1M", sell_price="200k",
    ),
    "enderman_pet_epic": SkyblockItem(
        "enderman_pet_epic", "Enderman Pet", "EPIC", "accessory",
        effects={},
        lore=["C技能：向当前移动方向瞬移一段距离"],
        slot="accessory", buy_price="10M", sell_price="2M",
    ),
    "spider_artifact": SkyblockItem(
        "spider_artifact", "Spider Artifact", "EPIC", "accessory",
        effects={"spider_artifact": True},
        lore=["失去1残机后的10秒内若再次失去残机，改为失去1B并放出决死Bomb"],
        slot="accessory", buy_price="1M", sell_price="500k",
    ),
    "catacombs_expert_ring": SkyblockItem(
        "catacombs_expert_ring", "Catacombs Expert Ring", "EPIC", "accessory",
        effects={"midboss_damage_pct": 50},
        slot="accessory", buy_price="30M", sell_price="20M",
    ),
    "scarfs_studies": SkyblockItem(
        "scarfs_studies", "Scarf's Studies", "LEGENDARY", "accessory",
        effects={"graze_slow_pct": 25},
        lore=["低速状态下擦弹范围内子弹速度-25%"],
        slot="accessory", buy_price="12M", sell_price="8M",
    ),
    "baby_yeti_pet": SkyblockItem(
        "baby_yeti_pet", "Baby Yeti Pet", "LEGENDARY", "accessory",
        effects={"kill50_lives": 1},
        lore=["消灭50只怪物后获得1残机"],
        slot="accessory", buy_price="40M", sell_price="10M",
    ),
    "ender_dragon_pet": SkyblockItem(
        "ender_dragon_pet", "Ender Dragon Pet", "LEGENDARY", "accessory",
        effects={"damage_pct": 20},
        slot="accessory", buy_price="1B", sell_price="20M",
    ),
    "wither_relic": SkyblockItem(
        "wither_relic", "Wither Relic", "LEGENDARY", "accessory",
        effects={"wither_damage_pct": 25},
        slot="accessory", buy_price="1B", sell_price="400M",
    ),

    # ============ 重铸石 ============
    "necromancers_brooch": SkyblockItem(
        "necromancers_brooch", "Necromancer's Brooch", "RARE", "reforge_stone",
        lore=["Reforge Stone", "Necrotic：低速状态下固定弹射速+3%"],
        buy_price="1M", sell_price="500k",
    ),
    "red_scarf": SkyblockItem(
        "red_scarf", "Red Scarf", "RARE", "reforge_stone",
        lore=["Reforge Stone", "Loving：BOMB伤害+8%；减少1条固定弹，增加1条追踪弹"],
        buy_price="5M", sell_price="2M",
    ),
    "dragons_claw": SkyblockItem(
        "dragons_claw", "Dragon Claw", "EPIC", "reforge_stone",
        lore=["Reforge Stone", "Fabled：非追踪弹造成+15%伤害"],
        buy_price=3000, sell_price=600,
    ),
    "wither_blood": SkyblockItem(
        "wither_blood", "Wither Blood", "EPIC", "reforge_stone",
        lore=["Reforge Stone", "Withered：追踪弹造成+20%伤害"],
        buy_price=3000, sell_price=600,
    ),
    "precursor_gear": SkyblockItem(
        "precursor_gear", "Precursor Gear", "EPIC", "reforge_stone",
        lore=["Reforge Stone", "Ancient：造成+X%伤害，X为当前面数"],
        buy_price=3000, sell_price=600,
    ),

    # ============ 材料 ============
    "divans_alloy": SkyblockItem(
        "divans_alloy", "Divan's Alloy", "LEGENDARY", "material",
        lore=["A legendary alloy. Purely collectible."],
        buy_price="1.2B", sell_price="1B",
    ),
    "necrons_handle": SkyblockItem(
        "necrons_handle", "Necron's Handle", "LEGENDARY", "material",
        lore=["The handle of the Wither King's most trusted weapon."],
        buy_price="1B", sell_price="600M",
    ),
    "judgement_core": SkyblockItem(
        "judgement_core", "Judgement Core", "LEGENDARY", "material",
        lore=["A core of judgment. Purely collectible."],
        buy_price="500M", sell_price="400M",
    ),
    "skyblock_coin": SkyblockItem(
        "skyblock_coin", "SkyBlock Coin", "SPECIAL", "material",
        lore=["拾取直接 +1M 金币，不进背包"],
        buy_price=0, sell_price=0,
    ),

    # ---- 旧版遗留物品（保留定义以兼容旧存档；不再掉落 / 不出售）----
    "divine_fragment": SkyblockItem(
        "divine_fragment", "Divine Fragment", "DIVINE", "material",
        lore=["A fragment of divine power.", "Radiates with celestial energy."],
        buy_price=4000,
    ),
    "power_orb": SkyblockItem(
        "power_orb", "Radiant Power Orb", "RARE", "accessory",
        stats={"health_regen": 10},
        lore=["Place to deploy a power orb", "that heals nearby players."],
        slot="accessory", buy_price=1200,
    ),
    "bonzos_mask": SkyblockItem(
        "bonzos_mask", "Bonzo's Mask", "RARE", "armor",
        stats={"health": 125, "defense": 100, "intelligence": 150},
        lore=["Returns you from the dead."],
        slot="helmet", buy_price=7000,
    ),
    "guardian_pet_rare": SkyblockItem(
        "guardian_pet_rare", "Guardian Pet [R]", "RARE", "accessory",
        stats={"defense": 20, "health": 25},
        slot="accessory", buy_price=1500,
    ),
    "enderman_pet_common": SkyblockItem(
        "enderman_pet_common", "Enderman Pet [C]", "COMMON", "accessory",
        stats={"crit_damage": 10},
        slot="accessory", buy_price=500,
    ),
}


# --- C 技能元数据 ---------------------------------------------------------
# 每个 C 技能物品：每面可使用次数（无特殊说明时默认 1 次）
C_SKILLS = {
    "sword_of_bad_health": {"name": "嗜血爆发", "per_stage": 1,
                            "desc": "消耗1残机，10秒内友方伤害+200%"},
    "bonzos_staff": {"name": "气球轰炸", "per_stage": 1,
                     "desc": "放出3个随机方向有后坐力的气球，碰弹幕爆炸"},
    "golem_sword": {"name": "钢铁之击", "per_stage": 4,
                    "desc": "炸掉擦弹范围内所有弹幕"},
    "aspect_of_the_end": {"name": "瞬移", "per_stage": 1,
                          "desc": "向当前移动方向瞬移一段距离"},
    "end_stone_sword": {"name": "不动金身", "per_stage": 3,
                        "desc": "2秒内无法移动且无法受伤"},
    "wither_cloak_sword": {"name": "凋零护盾", "per_stage": 1,
                           "desc": "召唤6个护盾围绕自机，持续10秒，抵消敌弹"},
    "spirit_bow": {"name": "追踪领域", "per_stage": 1,
                   "desc": "10秒内所有自机子弹变为追踪弹"},
    "aspect_of_the_dragons": {"name": "龙怒", "per_stage": 1,
                              "desc": "炸掉上方弹幕并对BOSS造成4800伤害"},
    "flower_of_truth": {"name": "玫瑰追踪", "per_stage": 2,
                        "desc": "玫瑰追踪消灭最近3个弹幕后飞向BOSS造成1200伤害"},
    "giants_sword": {"name": "巨人之剑", "per_stage": 1,
                     "desc": "清除全场弹幕并对BOSS造成当前阶段50%伤害"},
    "precursor_eye": {"name": "先驱激光", "per_stage": 1,
                      "desc": "向上射出1道持续3秒的红色激光（帧伤20）"},
    "overflux_power_orb": {"name": "能量核心", "per_stage": 1,
                           "desc": "Boss战中召唤Orb，持续处于范围内10秒获得1残机"},
    "summoning_ring": {"name": "唤灵", "per_stage": 1,
                       "desc": "随机召唤2只归属于你的小怪"},
    "enderman_pet": {"name": "瞬移", "per_stage": 1,
                     "desc": "向当前移动方向瞬移一段距离"},
    "tarantula_boots": {"name": "蛛影突袭", "per_stage": 1,
                        "desc": "清除当前移动方向上最近的1个弹幕并快速移动至其位置"},
}

# enderman_pet 使用 enderman_pet_epic 的 C 技能
C_SKILLS["enderman_pet_epic"] = C_SKILLS["enderman_pet"]


# --- 重铸石 / 前缀 --------------------------------------------------------

# 重铸石物品 id -> 前缀 id
REFORGE_STONES = {
    "dragons_claw": "fabled",
    "necromancers_brooch": "necrotic",
    "red_scarf": "loving",
    "wither_blood": "withered",
    "precursor_gear": "ancient",
}

# 前缀定义：name 英文显示名 / label 中文名 / effects 效果 / lore 说明
REFORGES = {
    "fabled": {
        "name": "Fabled",
        "label": "传奇",
        "effects": {"non_tracking_damage_pct": 15},
        "lore": ["非追踪弹造成+15%伤害"],
    },
    "necrotic": {
        "name": "Necrotic",
        "label": "死灵",
        "effects": {"fixed_bullet_speed_pct": 3},
        "lore": ["低速状态下固定弹射速+3%"],
    },
    "loving": {
        "name": "Loving",
        "label": "挚爱",
        "effects": {"bomb_damage_pct": 8, "fixed_bullet_add": -1,
                    "tracking_bullet_add": 1},
        "lore": ["BOMB伤害+8%；减少1条固定弹，增加1条追踪弹"],
    },
    "withered": {
        "name": "Withered",
        "label": "凋零",
        "effects": {"tracking_damage_pct": 20},
        "lore": ["追踪弹造成+20%伤害"],
    },
    "ancient": {
        "name": "Ancient",
        "label": "远古",
        "effects": {"reforge_ancient_stage_pct": True},
        "lore": ["造成+X%伤害，X为当前面数"],
    },
}

# 按稀有度的重铸费用（金币）
REFORGE_COSTS = {
    "COMMON": 250,
    "UNCOMMON": 500,
    "RARE": 1000,
    "EPIC": 2500,
    "LEGENDARY": 5000,
    "MYTHIC": 7500,
    "DIVINE": 10000,
    "SPECIAL": 10000,
}


# --- 每面关底 Boss 的三选一奖励池（每池 4 件，随机抽 3 件展示）---
BOSS_REWARD_POOLS = {
    1: ["arack", "spider_artifact", "tarantula_pet", "aspect_of_the_jerry"],
    2: ["aspect_of_the_dragons", "ender_dragon_pet", "superior_dragon_chestplate", "dragons_claw"],
    3: ["bonzos_staff", "balloon_snake", "necromancers_brooch", "wither_cloak_sword"],
    4: ["giants_sword", "summoning_ring", "necromancer_lord_leggings", "precursor_eye"],
    5: ["storms_leggings", "goldors_helmet", "necrons_chestplate", "maxors_boots"],
    6: ["hyperion", "terminator", "dark_claymore", "necrons_handle"],
}

class ItemDropManager:
    """物品掉落管理器"""

    # EPIC 及以上稀有度（Lapis 全套加成作用于此）
    HIGH_RARITIES = ("EPIC", "LEGENDARY", "MYTHIC", "DIVINE")

    def __init__(self):
        self.drop_table = {}

    def register_drop(self, enemy_type, item_id, drop_chance, conditions=None):
        """注册掉落"""
        if enemy_type not in self.drop_table:
            self.drop_table[enemy_type] = []
        self.drop_table[enemy_type].append({
            "item_id": item_id,
            "chance": drop_chance,
            "conditions": conditions or {},
        })

    def roll_drops(self, enemy_type, chance_mult=1.0, epic_chance_mult=1.0):
        """根据敌人类型掷骰掉落。

        chance_mult：所有掉落概率乘算倍率（Superior Dragon Chestplate +10% 用）；
        epic_chance_mult：仅 EPIC 及以上物品的乘算倍率（Lapis 全套 +20% 用）。
        """
        drops = []
        if enemy_type in self.drop_table:
            for entry in self.drop_table[enemy_type]:
                item = SKYBLOCK_ITEMS.get(entry["item_id"])
                if item is None:
                    continue
                mult = chance_mult
                if item.rarity in self.HIGH_RARITIES:
                    mult *= epic_chance_mult
                if random.random() < entry["chance"] * mult:
                    drops.append(item)
        return drops


class ItemInventory:
    """跨关卡背包与装备槽"""

    def __init__(self, inventory=None, equipment=None, coins=0, reforges=None):
        self.items = {}
        if inventory:
            for entry in inventory:
                item_id = entry.get("id") if isinstance(entry, dict) else entry
                count = entry.get("count", 1) if isinstance(entry, dict) else 1
                if item_id in SKYBLOCK_ITEMS:
                    self.items[item_id] = self.items.get(item_id, 0) + max(0, int(count))

        self.equipment = {slot: None for slot in EQUIPMENT_SLOTS}
        if equipment:
            for slot in EQUIPMENT_SLOTS:
                item_id = equipment.get(slot)
                if item_id in SKYBLOCK_ITEMS and SKYBLOCK_ITEMS[item_id].slot == slot:
                    self.equipment[slot] = item_id

        self.coins = max(0, int(coins or 0))
        self.applied_reforges = {}
        if reforges:
            for item_id, prefix_id in reforges.items():
                if item_id in SKYBLOCK_ITEMS and prefix_id in REFORGES:
                    self.applied_reforges[item_id] = prefix_id

    @classmethod
    def from_global_data(cls, data):
        return cls(
            inventory=data.get("inventory", []),
            equipment=data.get("equipment", {}),
            coins=data.get("coins", 0),
            reforges=data.get("reforges", {}),
        )

    def to_data(self):
        inventory = []
        for item_id, count in self.items.items():
            if count > 0:
                inventory.append({"id": item_id, "count": count})
        return {
            "inventory": inventory,
            "equipment": dict(self.equipment),
            "coins": self.coins,
            "reforges": dict(self.applied_reforges),
        }

    def save_to_global_data(self, global_data):
        data = self.to_data()
        global_data["inventory"] = data["inventory"]
        global_data["equipment"] = data["equipment"]
        global_data["coins"] = data["coins"]
        global_data["reforges"] = data["reforges"]

    def merge_from(self, other):
        """把另一份背包的物品、金币与重铸前缀并入本背包（撤离入库用）。"""
        for item_id, count in other.items.items():
            self.add_item(item_id, count)
        self.add_coins(other.coins)
        for item_id, prefix_id in other.applied_reforges.items():
            if self.has_item(item_id):
                self.applied_reforges[item_id] = prefix_id
        self._clear_missing_equipment()

    def add_item(self, item_id, count=1):
        if item_id not in SKYBLOCK_ITEMS or count <= 0:
            return
        self.items[item_id] = self.items.get(item_id, 0) + int(count)

    def remove_item(self, item_id, count=1):
        if self.items.get(item_id, 0) < count:
            return False
        self.items[item_id] -= count
        if self.items[item_id] <= 0:
            self.items.pop(item_id, None)
            self.applied_reforges.pop(item_id, None)
            self._clear_missing_equipment()
        return True

    def count_item(self, item_id):
        return self.items.get(item_id, 0)

    def has_item(self, item_id):
        return self.count_item(item_id) > 0

    def _clear_missing_equipment(self):
        for slot, item_id in list(self.equipment.items()):
            if item_id and not self.has_item(item_id):
                self.equipment[slot] = None

    def add_coins(self, amount):
        self.coins = max(0, self.coins + int(amount or 0))

    def spend_coins(self, amount):
        amount = int(amount or 0)
        if amount < 0 or self.coins < amount:
            return False
        self.coins -= amount
        return True

    def can_equip(self, item_id):
        item = SKYBLOCK_ITEMS.get(item_id)
        return item is not None and item.is_equippable and self.has_item(item_id)

    def equip(self, item_id):
        """装备物品；返回 (成功, 错误信息)。同一时间只能装备 1 件带 C 技能的物品。"""
        item = SKYBLOCK_ITEMS.get(item_id)
        if not item or not item.is_equippable:
            return False, "该物品无法装备"
        if not self.has_item(item_id):
            return False, "背包中没有该物品"
        if item_id in C_SKILLS:
            for slot, equipped_id in self.equipment.items():
                if equipped_id and equipped_id in C_SKILLS and equipped_id != item_id:
                    return False, "同时只能装备1件带C技能的物品"
        self.equipment[item.slot] = item_id
        return True, None

    def unequip_slot(self, slot):
        if slot not in self.equipment or not self.equipment[slot]:
            return False
        self.equipment[slot] = None
        return True

    def unequip_item(self, item_id):
        for slot, equipped_id in self.equipment.items():
            if equipped_id == item_id:
                self.equipment[slot] = None
                return True
        return False

    def toggle_equip(self, item_id):
        if self.is_equipped(item_id):
            return self.unequip_item(item_id)
        ok, _ = self.equip(item_id)
        return ok

    def is_equipped(self, item_id):
        return item_id in self.equipment.values()

    def get_equipped_slot(self, item_id):
        for slot, equipped_id in self.equipment.items():
            if equipped_id == item_id:
                return slot
        return None

    def get_equipped_item(self, slot):
        item_id = self.equipment.get(slot)
        return SKYBLOCK_ITEMS.get(item_id) if item_id else None

    def get_equipped_ids(self):
        return [item_id for item_id in self.equipment.values() if item_id]

    def get_equipped_stats(self):
        stats = {}
        for item_id in self.equipment.values():
            if not item_id:
                continue
            item = SKYBLOCK_ITEMS.get(item_id)
            if not item:
                continue
            for key, value in item.stats.items():
                stats[key] = stats.get(key, 0) + value
            prefix_id = self.applied_reforges.get(item_id)
            if prefix_id and prefix_id in REFORGES:
                for key, value in REFORGES[prefix_id].get("stats", {}).items():
                    stats[key] = stats.get(key, 0) + value
        return stats

    # --- 重铸（锻造） ---

    def get_item_prefix(self, item_id):
        """返回物品已打上的前缀 id；未重铸返回 None"""
        return self.applied_reforges.get(item_id)

    def get_display_name(self, item_id):
        """带前缀的显示名，例如 Fabled Aspect of the Dragons"""
        item = SKYBLOCK_ITEMS.get(item_id)
        if not item:
            return ""
        prefix_id = self.get_item_prefix(item_id)
        if prefix_id and prefix_id in REFORGES:
            return f"{REFORGES[prefix_id]['name']} {item.name}"
        return item.name

    def get_reforge_cost(self, item_id):
        """按稀有度返回重铸费用"""
        item = SKYBLOCK_ITEMS.get(item_id)
        if not item:
            return 0
        return REFORGE_COSTS.get(item.rarity, 1000)

    def can_reforge(self, item_id):
        """物品是否可锻造且已在背包中"""
        item = SKYBLOCK_ITEMS.get(item_id)
        return item is not None and item.can_reforge and self.has_item(item_id)

    def apply_reforge(self, item_id, stone_id):
        """用重铸石给物品打前缀：消耗重铸石 + 金币；已有前缀则直接替换。
        返回 (成功, 错误信息)。"""
        stone = SKYBLOCK_ITEMS.get(stone_id)
        item = SKYBLOCK_ITEMS.get(item_id)
        if not stone or stone.item_type != "reforge_stone":
            return False, "这不是重铸石"
        if not item or not item.can_reforge:
            return False, "该物品无法重铸"
        if not self.has_item(item_id):
            return False, "背包中没有该物品"
        if not self.has_item(stone_id):
            return False, "背包中没有该重铸石"
        cost = self.get_reforge_cost(item_id)
        if not self.spend_coins(cost):
            return False, f"金币不足（需要 {cost} 金币）"
        self.remove_item(stone_id, 1)
        prefix_id = REFORGE_STONES.get(stone_id)
        self.applied_reforges[item_id] = prefix_id
        return True, None

    def remove_reforge(self, item_id):
        """移除物品前缀，返回是否真的移除了"""
        return self.applied_reforges.pop(item_id, None) is not None

    def get_forge_entries(self):
        """锻造页数据：返回 (可用重铸石列表, 可锻造物品列表)"""
        stones = []
        for item_id, count in self.items.items():
            item = SKYBLOCK_ITEMS.get(item_id)
            if item and item.item_type == "reforge_stone" and count > 0:
                stones.append({
                    "id": item_id,
                    "item": item,
                    "count": count,
                    "prefix": REFORGE_STONES.get(item_id),
                })
        stones.sort(key=lambda e: e["item"].name)

        items = []
        for item_id, count in self.items.items():
            item = SKYBLOCK_ITEMS.get(item_id)
            if item and item.can_reforge and count > 0:
                items.append({
                    "id": item_id,
                    "item": item,
                    "count": count,
                    "prefix": self.get_item_prefix(item_id),
                    "cost": self.get_reforge_cost(item_id),
                    "equipped": self.get_equipped_slot(item_id),
                    "display_name": self.get_display_name(item_id),
                })
        items.sort(key=lambda e: e["item"].name)
        return stones, items

    def get_inventory_entries(self):
        entries = []
        for item_id, count in self.items.items():
            item = SKYBLOCK_ITEMS.get(item_id)
            if item and count > 0:
                entries.append({
                    "id": item_id,
                    "item": item,
                    "count": count,
                    "equipped": self.get_equipped_slot(item_id),
                    "display_name": self.get_display_name(item_id),
                })
        entries.sort(key=lambda e: e["item"].name)
        return entries

    def get_equippable_entries_for_slot(self, slot):
        entries = []
        for item_id, count in self.items.items():
            item = SKYBLOCK_ITEMS.get(item_id)
            if item and item.slot == slot and count > 0:
                entries.append({
                    "id": item_id,
                    "item": item,
                    "count": count,
                    "equipped": self.equipment.get(slot) == item_id,
                    "display_name": self.get_display_name(item_id),
                })
        entries.sort(key=lambda e: e["item"].name)
        return entries

    def get_sellable_entries(self):
        entries = []
        for item_id, count in self.items.items():
            item = SKYBLOCK_ITEMS.get(item_id)
            if item and item.sell_price > 0 and count > 0:
                entries.append({
                    "id": item_id,
                    "item": item,
                    "count": count,
                    "equipped": self.get_equipped_slot(item_id),
                    "sell_price": item.sell_price,
                })
        entries.sort(key=lambda e: e["item"].name)
        return entries

    def get_shop_stock(self):
        """商店可购买物品（有购买价格的物品，含材料与重铸石）"""
        stock = []
        for item in SKYBLOCK_ITEMS.values():
            if item.buy_price > 0:
                stock.append({"item": item, "buy_price": item.buy_price})
        stock.sort(key=lambda e: (e["item"].name))
        return stock

    def get_shop_stock_grouped(self):
        """按物品类型分组的商店库存：返回 {item_type: [entries]}"""
        groups = {}
        for entry in self.get_shop_stock():
            groups.setdefault(entry["item"].item_type, []).append(entry)
        return groups

    def get_c_skill_equipped_id(self):
        """返回当前装备中带 C 技能的物品 id；无则 None"""
        for item_id in self.get_equipped_ids():
            if item_id in C_SKILLS:
                return item_id
        return None


# --- 掉落表 ----------------------------------------------------------------

def roll_rarity_drop():
    """随机稀有度"""
    roll = random.random()
    cumulative = 0
    for rarity, chance in cfg.DROP_RATES.items():
        cumulative += chance
        if roll <= cumulative:
            return rarity
    return "COMMON"


def init_default_drop_table(manager: ItemDropManager):
    """初始化通用掉落表（妖精系 / 卫兵系 / Boss 通用 / 道中Boss通用）"""
    # 妖精系敌人（通用）
    manager.register_drop("FairyEnemy", "aspect_of_the_jerry", 0.05)
    manager.register_drop("FairyEnemy", "undead_sword", 0.02)
    manager.register_drop("FairyEnemy", "skyblock_coin", 0.20)

    # 卫兵系敌人（通用）
    manager.register_drop("GuardEnemy", "heavy_armor_chestplate", 0.05)
    manager.register_drop("GuardEnemy", "heavy_armor_leggings", 0.08)
    manager.register_drop("GuardEnemy", "heavy_armor_boots", 0.05)
    manager.register_drop("GuardEnemy", "baby_yeti_pet", 0.04)

    # Boss 通用表
    manager.register_drop("Boss", "divans_alloy", 0.01)

    # 道中BOSS（通用）
    manager.register_drop("MidBoss", "catacombs_expert_ring", 0.05)


def init_stage_drop_table(manager: ItemDropManager, stage_num: int):
    """按关卡注册道中Boss与小怪的专属掉落表。

    掉落 key 由 PlayingState 按敌人身份推导：
      stage{N}_minion / stage{N}_midboss / stage{N}_final_boss / stage{N}_any
    其中 stage{N}_any 表示该面任意敌人（小怪+道中+关底）都会掷。
    """
    # ---- 跨面通用：任意怪物 ----
    if stage_num in (3, 4, 5):
        manager.register_drop(f"stage{stage_num}_any", "wither_cloak_sword", 0.01)
        manager.register_drop(f"stage{stage_num}_any", "spirit_bow", 0.01)
    elif stage_num == 6:
        manager.register_drop(f"stage{stage_num}_any", "wither_cloak_sword", 0.02)
        manager.register_drop(f"stage{stage_num}_any", "spirit_bow", 0.01)

    if stage_num == 1:
        # 1面：蜘蛛巢穴
        manager.register_drop("stage1_minion", "skyblock_coin", 0.20)
        manager.register_drop("stage1_minion", "aspect_of_the_jerry", 0.05)
        manager.register_drop("stage1_minion", "undead_sword", 0.03)
        manager.register_drop("stage1_minion", "sword_of_bad_health", 0.04)
        manager.register_drop("stage1_minion", "lapis_armor_helmet", 0.04)
        manager.register_drop("stage1_minion", "lapis_armor_chestplate", 0.03)
        manager.register_drop("stage1_minion", "lapis_armor_leggings", 0.03)
        manager.register_drop("stage1_minion", "lapis_armor_boots", 0.03)
        manager.register_drop("stage1_minion", "heavy_armor_leggings", 0.04)
        manager.register_drop("stage1_minion", "tarantula_pet", 0.05)
        manager.register_drop("stage1_minion", "spider_artifact", 0.02)
        manager.register_drop("stage1_minion", "maddox_batphone", 0.02)
        manager.register_drop("stage1_midboss", "arack", 0.06)
        manager.register_drop("stage1_midboss", "spider_artifact", 0.25)
        manager.register_drop("stage1_midboss", "tarantula_boots", 0.04)
        manager.register_drop("stage1_midboss", "tarantula_helmet", 0.04)
        manager.register_drop("stage1_final_boss", "arack", 0.30)
        manager.register_drop("stage1_final_boss", "spider_artifact", 0.40)
        manager.register_drop("stage1_final_boss", "tarantula_boots", 0.18)
        manager.register_drop("stage1_final_boss", "tarantula_helmet", 0.18)
    elif stage_num == 2:
        # 2面：末地
        manager.register_drop("stage2_any", "aspect_of_the_end", 0.02)
        manager.register_drop("stage2_any", "judgement_core", 0.002)
        manager.register_drop("stage2_minion", "skyblock_coin", 0.22)
        manager.register_drop("stage2_minion", "sword_of_bad_health", 0.04)
        manager.register_drop("stage2_minion", "end_stone_sword", 0.03)
        manager.register_drop("stage2_minion", "enderman_pet_epic", 0.02)
        manager.register_drop("stage2_minion", "maddox_batphone", 0.02)
        manager.register_drop("stage2_midboss", "golem_sword", 1.0)
        manager.register_drop("stage2_midboss", "end_stone_sword", 0.50)
        manager.register_drop("stage2_midboss", "enderman_pet_epic", 0.20)
        manager.register_drop("stage2_midboss", "superior_dragon_chestplate", 0.02)
        manager.register_drop("stage2_midboss", "dragons_claw", 0.04)
        manager.register_drop("stage2_final_boss", "aspect_of_the_dragons", 0.30)
        manager.register_drop("stage2_final_boss", "ender_dragon_pet", 0.08)
        manager.register_drop("stage2_final_boss", "wither_relic", 0.08)
        manager.register_drop("stage2_final_boss", "superior_dragon_chestplate", 0.15)
        manager.register_drop("stage2_final_boss", "dragons_claw", 0.20)
    elif stage_num == 3:
        # 3面：地下墓穴 F1
        manager.register_drop("stage3_minion", "skyblock_coin", 0.30)
        manager.register_drop("stage3_minion", "maddox_batphone", 0.02)
        manager.register_drop("stage3_minion", "overflux_power_orb", 0.01)
        manager.register_drop("stage3_minion", "balloon_snake", 0.01)
        manager.register_drop("stage3_minion", "necromancers_brooch", 0.02)
        manager.register_drop("stage3_minion", "heavy_armor_helmet", 0.03)
        manager.register_drop("stage3_midboss", "necromancers_brooch", 0.08)
        manager.register_drop("stage3_final_boss", "bonzos_staff", 0.12)
        manager.register_drop("stage3_final_boss", "balloon_snake", 0.16)
        manager.register_drop("stage3_final_boss", "necromancers_brooch", 0.18)
    elif stage_num == 4:
        # 4面：墓穴深处
        manager.register_drop("stage4_minion", "skyblock_coin", 0.40)
        manager.register_drop("stage4_minion", "maddox_batphone", 0.02)
        manager.register_drop("stage4_minion", "overflux_power_orb", 0.01)
        manager.register_drop("stage4_minion", "summoning_ring", 0.01)
        manager.register_drop("stage4_minion", "necromancers_brooch", 0.02)
        manager.register_drop("stage4_midboss", "necromancers_brooch", 0.10)
        manager.register_drop("stage4_midboss", "summoning_ring", 0.05)
        manager.register_drop("stage4_midboss", "red_scarf", 0.80)
        manager.register_drop("stage4_midboss", "scarfs_studies", 1.0)
        manager.register_drop("stage4_terracotta", "flower_of_truth", 0.03)
        manager.register_drop("stage4_final_boss", "flower_of_truth", 0.60)
        manager.register_drop("stage4_final_boss", "giants_sword", 0.08)
        manager.register_drop("stage4_final_boss", "summoning_ring", 0.12)
        manager.register_drop("stage4_final_boss", "necromancer_lord_leggings", 0.10)
        manager.register_drop("stage4_final_boss", "precursor_eye", 0.08)
        manager.register_drop("stage4_final_boss", "shadow_assassin_boots", 0.10)
    elif stage_num == 5:
        # 5面：BOSS RUSH（Professor / Thorn / Livid / 四凋零领主）
        manager.register_drop("stage5_boss", "precursor_gear", 0.15)
        manager.register_drop("stage5_midboss_thorn", "spirit_bow", 0.10)
        manager.register_drop("stage5_midboss_livid", "shadow_assassin_boots", 1.0)
        manager.register_drop("stage5_final_boss", "maxors_boots", 0.50)
        manager.register_drop("stage5_final_boss", "storms_leggings", 0.50)
        manager.register_drop("stage5_final_boss", "goldors_helmet", 0.50)
        manager.register_drop("stage5_final_boss", "necrons_chestplate", 0.50)
        manager.register_drop("stage5_final_boss", "hyperion", 0.05)
        manager.register_drop("stage5_final_boss", "necrons_handle", 0.05)
        manager.register_drop("stage5_final_boss", "wither_blood", 0.15)
    elif stage_num == 6:
        # 6面：最终进军（Kaeman）
        manager.register_drop("stage6_minion", "skyblock_coin", 0.40)
        manager.register_drop("stage6_minion", "overflux_power_orb", 0.02)
        manager.register_drop("stage6_minion", "wither_blood", 0.05)
        manager.register_drop("stage6_minion", "precursor_gear", 0.02)
        manager.register_drop("stage6_final_boss", "dark_claymore", 0.50)
        manager.register_drop("stage6_final_boss", "wither_blood", 0.30)
        manager.register_drop("stage6_final_boss", "necrons_handle", 0.10)
