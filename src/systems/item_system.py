# Skyblock 物品系统
# 物品定义、掉落、背包、装备与商店价格

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


class SkyblockItem:
    """Skyblock物品"""

    def __init__(self, id, name, rarity, item_type, stats=None, lore=None,
                 slot=None, buy_price=0, sell_price=None):
        self.id = id
        self.name = name
        self.rarity = rarity  # COMMON / UNCOMMON / RARE / EPIC / LEGENDARY / MYTHIC / DIVINE / SPECIAL
        self.item_type = item_type  # weapon / armor / accessory / consumable / material
        self.stats = stats or {}
        self.lore = lore or []
        self.slot = slot
        self.buy_price = int(buy_price or 0)
        if sell_price is None:
            self.sell_price = max(1, self.buy_price // 5) if self.buy_price > 0 else 0
        else:
            self.sell_price = int(sell_price or 0)

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


# --- 物品定义 ---

SKYBLOCK_ITEMS = {
    "aspect_of_the_jerry": SkyblockItem(
        "aspect_of_the_jerry", "Aspect of the Jerry", "COMMON", "weapon",
        stats={"damage": 1, "strength": 1},
        lore=["The legendary Aspect of the Jerry.", "Deals massive damage... or not."],
        slot="weapon", buy_price=50,
    ),
    "undead_sword": SkyblockItem(
        "undead_sword", "Undead Sword", "COMMON", "weapon",
        stats={"damage": 30, "strength": 10},
        lore=["Deals +100% damage to", "undead enemies."],
        slot="weapon", buy_price=300,
    ),
    "lapis_armor_helmet": SkyblockItem(
        "lapis_armor_helmet", "Lapis Armor Helmet", "UNCOMMON", "armor",
        stats={"health": 15, "defense": 25},
        slot="helmet", buy_price=400,
    ),
    "lapis_armor_chestplate": SkyblockItem(
        "lapis_armor_chestplate", "Lapis Armor Chestplate", "UNCOMMON", "armor",
        stats={"health": 20, "defense": 35},
        slot="chestplate", buy_price=500,
    ),
    "lapis_armor_leggings": SkyblockItem(
        "lapis_armor_leggings", "Lapis Armor Leggings", "UNCOMMON", "armor",
        stats={"health": 15, "defense": 30},
        slot="leggings", buy_price=450,
    ),
    "lapis_armor_boots": SkyblockItem(
        "lapis_armor_boots", "Lapis Armor Boots", "UNCOMMON", "armor",
        stats={"health": 10, "defense": 20},
        slot="boots", buy_price=350,
    ),
    "enderman_pet_common": SkyblockItem(
        "enderman_pet_common", "Enderman Pet [C]", "COMMON", "accessory",
        stats={"crit_damage": 10},
        slot="accessory", buy_price=500,
    ),
    "enderman_pet_epic": SkyblockItem(
        "enderman_pet_epic", "Enderman Pet [E]", "EPIC", "accessory",
        stats={"crit_damage": 30, "crit_chance": 5},
        slot="accessory", buy_price=5000,
    ),
    "guardian_pet_rare": SkyblockItem(
        "guardian_pet_rare", "Guardian Pet [R]", "RARE", "accessory",
        stats={"defense": 20, "health": 25},
        slot="accessory", buy_price=1500,
    ),
    "maddox_batphone": SkyblockItem(
        "maddox_batphone", "Maddox Batphone", "RARE", "accessory",
        lore=["Call Maddox to start", "a new slayer quest."],
        slot="accessory", buy_price=300,
    ),
    "necrons_handle": SkyblockItem(
        "necrons_handle", "Necron's Handle", "LEGENDARY", "material",
        lore=["The handle of the Wither King's", "most trusted weapon."],
        buy_price=12000,
    ),
    "hyperion": SkyblockItem(
        "hyperion", "Hyperion", "LEGENDARY", "weapon",
        stats={"damage": 260, "strength": 150, "intelligence": 350},
        lore=["The most powerful Wither Blade.", "Right-click: Wither Impact"],
        slot="weapon", buy_price=25000,
    ),
    "divine_fragment": SkyblockItem(
        "divine_fragment", "Divine Fragment", "DIVINE", "material",
        lore=["A fragment of divine power.", "Radiates with celestial energy."],
        buy_price=4000,
    ),
    "skyblock_coin": SkyblockItem(
        "skyblock_coin", "SkyBlock Coin", "SPECIAL", "material",
        lore=["The official currency of Hypixel SkyBlock.", "Can be used to trade with NPCs."],
        buy_price=0,
        sell_price=0,
    ),
    "power_orb": SkyblockItem(
        "power_orb", "Radiant Power Orb", "RARE", "accessory",
        stats={"health_regen": 10},
        lore=["Place to deploy a power orb", "that heals nearby players."],
        slot="accessory", buy_price=1200,
    ),
    # --- 1面 Arachne 奖励池 ---
    "arack": SkyblockItem(
        "arack", "Arack", "EPIC", "weapon",
        stats={"damage": 90, "strength": 60},
        lore=["A legendary spider fang.", "While poisoned, gain +100 Strength."],
        slot="weapon", buy_price=12000,
    ),
    "spider_artifact": SkyblockItem(
        "spider_artifact", "Spider Artifact", "EPIC", "accessory",
        lore=["Take 15% less damage from spiders."],
        slot="accessory", buy_price=6000,
    ),
    "tarantula_helmet": SkyblockItem(
        "tarantula_helmet", "Tarantula Helmet", "EPIC", "armor",
        stats={"health": 100, "defense": 80, "intelligence": 100},
        lore=["Spider slayer helmet."],
        slot="helmet", buy_price=8000,
    ),
    "tarantula_boots": SkyblockItem(
        "tarantula_boots", "Tarantula Boots", "EPIC", "armor",
        stats={"health": 70, "defense": 100, "speed": 5, "intelligence": 50},
        lore=["Leap high into the air!"],
        slot="boots", buy_price=7000,
    ),
    # --- 2面 Ender Dragon 奖励池 ---
    "aspect_of_the_dragons": SkyblockItem(
        "aspect_of_the_dragons", "Aspect of the Dragons", "LEGENDARY", "weapon",
        stats={"damage": 225, "strength": 100},
        lore=["Right-click to summon the power of the dragons."],
        slot="weapon", buy_price=25000,
    ),
    "ender_dragon_pet": SkyblockItem(
        "ender_dragon_pet", "Ender Dragon Pet", "LEGENDARY", "accessory",
        stats={"strength": 50, "crit_chance": 10, "crit_damage": 50},
        lore=["The majestic Ender Dragon, now your ally."],
        slot="accessory", buy_price=20000,
    ),
    "superior_dragon_chestplate": SkyblockItem(
        "superior_dragon_chestplate", "Superior Dragon Chestplate", "LEGENDARY", "armor",
        stats={"health": 150, "defense": 190, "strength": 10,
               "crit_chance": 2, "crit_damage": 10, "intelligence": 25},
        lore=["All stats +5%."],
        slot="chestplate", buy_price=22000,
    ),
    "dragons_claw": SkyblockItem(
        "dragons_claw", "Dragon's Claw", "EPIC", "reforge_stone",
        lore=["Reforge Stone", "Applies the Fabled reforge to a weapon."],
        buy_price=3000, sell_price=600,
    ),
    # --- 3面 Bonzo 奖励池 ---
    "bonzos_staff": SkyblockItem(
        "bonzos_staff", "Bonzo's Staff", "RARE", "weapon",
        stats={"damage": 160, "intelligence": 250},
        lore=["Right-click to launch a balloon that deals AOE damage."],
        slot="weapon", buy_price=8000,
    ),
    "balloon_snake": SkyblockItem(
        "balloon_snake", "Balloon Snake", "RARE", "accessory",
        stats={"health": 10, "intelligence": 10},
        lore=["Grants Jump Boost II."],
        slot="accessory", buy_price=4000,
    ),
    "bonzos_mask": SkyblockItem(
        "bonzos_mask", "Bonzo's Mask", "RARE", "armor",
        stats={"health": 125, "defense": 100, "intelligence": 150},
        lore=["Returns you from the dead."],
        slot="helmet", buy_price=7000,
    ),
    "necromancers_brooch": SkyblockItem(
        "necromancers_brooch", "Necromancer's Brooch", "RARE", "reforge_stone",
        lore=["Reforge Stone", "Applies the Necrotic reforge to armor."],
        buy_price=2000, sell_price=400,
    ),
    # --- 4面 Sadan 奖励池 ---
    "giants_sword": SkyblockItem(
        "giants_sword", "Giant's Sword", "LEGENDARY", "weapon",
        stats={"damage": 500},
        lore=["The sword of a giant. Deals massive damage."],
        slot="weapon", buy_price=30000,
    ),
    "summoning_ring": SkyblockItem(
        "summoning_ring", "Summoning Ring", "RARE", "accessory",
        lore=["Absorbs souls and summons them to fight for you."],
        slot="accessory", buy_price=6000,
    ),
    "necromancer_lord_leggings": SkyblockItem(
        "necromancer_lord_leggings", "Necromancer Lord Leggings", "LEGENDARY", "armor",
        stats={"health": 180, "defense": 160, "intelligence": 60},
        lore=["Worn by the Necromancer Lord."],
        slot="leggings", buy_price=18000,
    ),
    "precursor_eye": SkyblockItem(
        "precursor_eye", "Precursor Eye", "LEGENDARY", "armor",
        stats={"health": 222, "defense": 222, "intelligence": 222},
        lore=["The all-seeing eye of the Precursor."],
        slot="helmet", buy_price=20000,
    ),
    "grappling_hook": SkyblockItem(
        "grappling_hook", "Grappling Hook", "UNCOMMON", "weapon",
        lore=["Right-click to launch yourself", "towards the targeted location."],
        slot="weapon", buy_price=800,
    ),
}


# --- 重铸石 / 前缀 ---

# 重铸石物品 id -> 前缀 id
REFORGE_STONES = {
    "dragons_claw": "fabled",
    "necromancers_brooch": "necrotic",
}

# 前缀定义：name 英文显示名 / label 中文名 / stats 属性加成 / lore 说明
REFORGES = {
    "fabled": {
        "name": "Fabled",
        "label": "传奇",
        "stats": {"strength": 30, "crit_damage": 15},
        "lore": ["Critical hits deal extra damage."],
    },
    "necrotic": {
        "name": "Necrotic",
        "label": "死灵",
        "stats": {"intelligence": 60},
        "lore": ["Enhances your magical power."],
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


# --- 每面关底 Boss 的 4 选 1 奖励池 ---

BOSS_REWARD_POOLS = {
    1: ["arack", "spider_artifact", "tarantula_helmet", "tarantula_boots"],
    2: ["aspect_of_the_dragons", "ender_dragon_pet", "superior_dragon_chestplate", "dragons_claw"],
    3: ["bonzos_staff", "balloon_snake", "bonzos_mask", "necromancers_brooch"],
    4: ["giants_sword", "summoning_ring", "necromancer_lord_leggings", "precursor_eye"],
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
        item = SKYBLOCK_ITEMS.get(item_id)
        if not item or not item.is_equippable:
            return False
        if not self.has_item(item_id):
            return False
        self.equipment[item.slot] = item_id
        return True

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
        return self.equip(item_id)

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
                for key, value in REFORGES[prefix_id]["stats"].items():
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
            if item and item.is_equippable and item.sell_price > 0 and count > 0:
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
        stock = []
        for item in SKYBLOCK_ITEMS.values():
            if item.is_equippable and item.buy_price > 0:
                stock.append({"item": item, "buy_price": item.buy_price})
        stock.sort(key=lambda e: e["item"].name)
        return stock


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


def init_stage_drop_table(manager: ItemDropManager, stage_num: int):
    """按关卡注册道中Boss与小怪的专属掉落表。

    掉落 key 由 PlayingState 按敌人身份推导：
    stage{N}_minion / stage{N}_midboss / stage{N}_final_boss。
    """
    if stage_num == 1:
        # 1面：蜘蛛巢穴
        manager.register_drop("stage1_minion", "skyblock_coin", 0.20)
        manager.register_drop("stage1_minion", "aspect_of_the_jerry", 0.05)
        manager.register_drop("stage1_minion", "undead_sword", 0.03)
        manager.register_drop("stage1_minion", "spider_artifact", 0.02)
        manager.register_drop("stage1_minion", "lapis_armor_helmet", 0.04)
        manager.register_drop("stage1_minion", "lapis_armor_boots", 0.03)
        manager.register_drop("stage1_midboss", "spider_artifact", 0.25)
        manager.register_drop("stage1_midboss", "arack", 0.06)
        manager.register_drop("stage1_midboss", "tarantula_helmet", 0.04)
        manager.register_drop("stage1_midboss", "tarantula_boots", 0.04)
        manager.register_drop("stage1_final_boss", "arack", 0.30)
        manager.register_drop("stage1_final_boss", "spider_artifact", 0.40)
        manager.register_drop("stage1_final_boss", "tarantula_helmet", 0.18)
        manager.register_drop("stage1_final_boss", "tarantula_boots", 0.18)
    elif stage_num == 2:
        # 2面：末地
        manager.register_drop("stage2_minion", "skyblock_coin", 0.22)
        manager.register_drop("stage2_minion", "enderman_pet_common", 0.05)
        manager.register_drop("stage2_minion", "guardian_pet_rare", 0.02)
        manager.register_drop("stage2_minion", "enderman_pet_epic", 0.01)
        manager.register_drop("stage2_midboss", "enderman_pet_epic", 0.10)
        manager.register_drop("stage2_midboss", "dragons_claw", 0.04)
        manager.register_drop("stage2_midboss", "superior_dragon_chestplate", 0.02)
        manager.register_drop("stage2_final_boss", "aspect_of_the_dragons", 0.10)
        manager.register_drop("stage2_final_boss", "ender_dragon_pet", 0.08)
        manager.register_drop("stage2_final_boss", "superior_dragon_chestplate", 0.10)
        manager.register_drop("stage2_final_boss", "dragons_claw", 0.15)
    elif stage_num == 3:
        # 3面：地下墓穴 F1
        manager.register_drop("stage3_minion", "skyblock_coin", 0.20)
        manager.register_drop("stage3_minion", "power_orb", 0.04)
        manager.register_drop("stage3_minion", "grappling_hook", 0.04)
        manager.register_drop("stage3_minion", "maddox_batphone", 0.02)
        manager.register_drop("stage3_minion", "balloon_snake", 0.01)
        manager.register_drop("stage3_midboss", "necromancers_brooch", 0.08)
        manager.register_drop("stage3_midboss", "bonzos_mask", 0.03)
        manager.register_drop("stage3_midboss", "balloon_snake", 0.05)
        manager.register_drop("stage3_final_boss", "bonzos_staff", 0.12)
        manager.register_drop("stage3_final_boss", "balloon_snake", 0.16)
        manager.register_drop("stage3_final_boss", "bonzos_mask", 0.10)
        manager.register_drop("stage3_final_boss", "necromancers_brooch", 0.18)
    elif stage_num == 4:
        # 4面：墓穴深处
        manager.register_drop("stage4_minion", "skyblock_coin", 0.20)
        manager.register_drop("stage4_minion", "maddox_batphone", 0.02)
        manager.register_drop("stage4_minion", "power_orb", 0.04)
        manager.register_drop("stage4_minion", "summoning_ring", 0.01)
        manager.register_drop("stage4_minion", "guardian_pet_rare", 0.02)
        manager.register_drop("stage4_midboss", "necromancers_brooch", 0.10)
        manager.register_drop("stage4_midboss", "summoning_ring", 0.05)
        manager.register_drop("stage4_midboss", "bonzos_mask", 0.04)
        manager.register_drop("stage4_final_boss", "giants_sword", 0.08)
        manager.register_drop("stage4_final_boss", "summoning_ring", 0.12)
        manager.register_drop("stage4_final_boss", "necromancer_lord_leggings", 0.10)
        manager.register_drop("stage4_final_boss", "precursor_eye", 0.08)
        manager.register_drop("stage4_final_boss", "necromancers_brooch", 0.15)
    elif stage_num == 5:
        # 5面：BOSS RUSH（后续可细化）
        manager.register_drop("stage5_minion", "skyblock_coin", 0.20)
        manager.register_drop("stage5_minion", "maddox_batphone", 0.02)
        manager.register_drop("stage5_minion", "power_orb", 0.03)
