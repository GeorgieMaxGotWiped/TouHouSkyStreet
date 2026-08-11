# Skyblock 技能系统

from src.engine import settings as cfg

class Skill:
    """技能"""
    def __init__(self, name, icon=""):
        self.name = name
        self.icon = icon
        self.xp = 0
        self.level = 0

    @property
    def xp_to_next(self):
        if self.level >= len(cfg.SKILL_XP_TABLE) - 1:
            return float("inf")
        return cfg.SKILL_XP_TABLE[self.level]

    @property
    def total_xp_for_next(self):
        """升到下一级所需的总经验"""
        if self.level >= len(cfg.SKILL_XP_TABLE):
            return float("inf")
        return cfg.SKILL_XP_TABLE[self.level - 1] if self.level > 0 else 0

    @property
    def progress_to_next(self):
        """当前级别进度 0-1"""
        current_level_base = cfg.SKILL_XP_TABLE[self.level - 1] if self.level > 0 else 0
        xp_in_level = self.xp - current_level_base
        xp_needed = self.xp_to_next - current_level_base
        if xp_needed <= 0:
            return 1.0
        return min(1.0, xp_in_level / xp_needed)

    def add_xp(self, amount):
        old_level = self.level
        self.xp += amount
        # 重新计算等级
        while self.level < len(cfg.SKILL_XP_TABLE) and self.xp >= cfg.SKILL_XP_TABLE[self.level]:
            self.level += 1
        return self.level > old_level

    def get_bonus(self):
        """获取技能加成"""
        return {
            "COMBAT": {"damage_mult": 1.0 + self.level * 0.02},
            "MINING": {"defense": self.level * 2},
            "FARMING": {"health": self.level * 3},
            "FORAGING": {"strength": self.level * 2},
            "FISHING": {"health": self.level * 2},
            "ENCHANTING": {"intelligence": self.level * 2},
            "ALCHEMY": {"intelligence": self.level * 1},
        }.get(self.name, {})


class SkillManager:
    """技能管理器"""
    SKILL_NAMES = ["COMBAT", "MINING", "FARMING", "FORAGING", "FISHING", "ENCHANTING", "ALCHEMY"]

    def __init__(self):
        self.skills = {name: Skill(name) for name in self.SKILL_NAMES}

    def add_xp(self, skill_name, amount):
        if skill_name in self.skills:
            leveled = self.skills[skill_name].add_xp(amount)
            return leveled
        return False

    def get_level(self, skill_name):
        if skill_name in self.skills:
            return self.skills[skill_name].level
        return 0

    def get_all_bonuses(self):
        bonuses = {}
        for skill in self.skills.values():
            bonus = skill.get_bonus()
            for k, v in bonus.items():
                bonuses[k] = bonuses.get(k, 0) + v
        return bonuses

    def to_dict(self):
        return {name: {"xp": s.xp, "level": s.level} for name, s in self.skills.items()}

    def from_dict(self, data):
        for name, sdata in data.items():
            if name in self.skills:
                self.skills[name].xp = sdata.get("xp", 0)
                self.skills[name].level = sdata.get("level", 0)
