# Skyblock 物品系统
# 物品定义、掉落、背包管理

import random
from src.engine import settings as cfg

class SkyblockItem:
    """Skyblock物品"""
    def __init__(self, id, name, rarity, item_type, stats=None, lore=None):
        self.id = id
        self.name = name
        self.rarity = rarity  # COMMON / UNCOMMON / RARE / EPIC / LEGENDARY / MYTHIC / DIVINE / SPECIAL
        self.item_type = item_type  # weapon / armor / accessory / consumable / material
        self.stats = stats or {}
        self.lore = lore or []

    @property
    def rarity_color(self):
        return cfg.RARITY_COLORS.get(self.rarity, cfg.COLOR_WHITE)

    @property
    def rarity_display(self):
        return self.rarity.capitalize()

    def __repr__(self):
        return f"[{self.rarity}] {self.name}"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "rarity": self.rarity,
            "type": self.item_type,
            "stats": self.stats,
        }


# --- 物品定义 ---

SKYBLOCK_ITEMS = {
    "aspect_of_the_jerry": SkyblockItem(
        "aspect_of_the_jerry", "Aspect of the Jerry", "COMMON", "weapon",
        stats={"damage": 1, "strength": 1},
        lore=["The legendary Aspect of the Jerry.", "Deals massive damage... or not."]
    ),
    "undead_sword": SkyblockItem(
        "undead_sword", "Undead Sword", "COMMON", "weapon",
        stats={"damage": 30, "strength": 10},
        lore=["Deals +100% damage to", "undead enemies."]
    ),
    "lapis_armor_helmet": SkyblockItem(
        "lapis_armor_helmet", "Lapis Armor Helmet", "UNCOMMON", "armor",
        stats={"health": 15, "defense": 25},
    ),
    "lapis_armor_chestplate": SkyblockItem(
        "lapis_armor_chestplate", "Lapis Armor Chestplate", "UNCOMMON", "armor",
        stats={"health": 20, "defense": 35},
    ),
    "lapis_armor_leggings": SkyblockItem(
        "lapis_armor_leggings", "Lapis Armor Leggings", "UNCOMMON", "armor",
        stats={"health": 15, "defense": 30},
    ),
    "lapis_armor_boots": SkyblockItem(
        "lapis_armor_boots", "Lapis Armor Boots", "UNCOMMON", "armor",
        stats={"health": 10, "defense": 20},
    ),
    "enderman_pet_common": SkyblockItem(
        "enderman_pet_common", "Enderman Pet [C]", "COMMON", "accessory",
        stats={"crit_damage": 10},
    ),
    "enderman_pet_epic": SkyblockItem(
        "enderman_pet_epic", "Enderman Pet [E]", "EPIC", "accessory",
        stats={"crit_damage": 30, "crit_chance": 5},
    ),
    "guardian_pet_rare": SkyblockItem(
        "guardian_pet_rare", "Guardian Pet [R]", "RARE", "accessory",
        stats={"defense": 20, "health": 25},
    ),
    "maddox_batphone": SkyblockItem(
        "maddox_batphone", "Maddox Batphone", "RARE", "accessory",
        lore=["Call Maddox to start", "a new slayer quest."]
    ),
    "necrons_handle": SkyblockItem(
        "necrons_handle", "Necron's Handle", "LEGENDARY", "material",
        lore=["The handle of the Wither King's", "most trusted weapon."]
    ),
    "hyperion": SkyblockItem(
        "hyperion", "Hyperion", "LEGENDARY", "weapon",
        stats={"damage": 260, "strength": 150, "intelligence": 350},
        lore=["The most powerful Wither Blade.", "Right-click: Wither Impact"]
    ),
    "divine_fragment": SkyblockItem(
        "divine_fragment", "Divine Fragment", "DIVINE", "material",
        lore=["A fragment of divine power.", "Radiates with celestial energy."]
    ),
    "skyblock_coin": SkyblockItem(
        "skyblock_coin", "SkyBlock Coin", "SPECIAL", "material",
        lore=["The official currency of Hypixel SkyBlock.", "Can be used to trade with NPCs."]
    ),
    "power_orb": SkyblockItem(
        "power_orb", "Radiant Power Orb", "RARE", "accessory",
        stats={"health_regen": 10},
        lore=["Place to deploy a power orb", "that heals nearby players."]
    ),
    "grappling_hook": SkyblockItem(
        "grappling_hook", "Grappling Hook", "UNCOMMON", "weapon",
        lore=["Right-click to launch yourself", "towards the targeted location."]
    ),
}


class ItemDropManager:
    """物品掉落管理器"""
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

    def roll_drops(self, enemy_type):
        """根据敌人类型掷骰掉落"""
        drops = []
        if enemy_type in self.drop_table:
            for entry in self.drop_table[enemy_type]:
                if random.random() < entry["chance"]:
                    item = SKYBLOCK_ITEMS.get(entry["item_id"])
                    if item:
                        drops.append(item)
        return drops


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
    """初始化默认掉落表"""
    # FairyEnemy 掉落
    manager.register_drop("FairyEnemy", "skyblock_coin", 0.20)
    manager.register_drop("FairyEnemy", "aspect_of_the_jerry", 0.05)
    manager.register_drop("FairyEnemy", "undead_sword", 0.02)

    # SpiritEnemy 掉落
    manager.register_drop("SpiritEnemy", "grappling_hook", 0.08)
    manager.register_drop("SpiritEnemy", "power_orb", 0.04)

    # GuardEnemy 掉落
    manager.register_drop("GuardEnemy", "lapis_armor_helmet", 0.08)
    manager.register_drop("GuardEnemy", "lapis_armor_chestplate", 0.05)
    manager.register_drop("GuardEnemy", "guardian_pet_rare", 0.03)

    # Boss 掉落
    manager.register_drop("Boss", "necrons_handle", 0.02)
    manager.register_drop("Boss", "hyperion", 0.005)
    manager.register_drop("Boss", "divine_fragment", 0.01)
    manager.register_drop("Boss", "enderman_pet_epic", 0.05)
