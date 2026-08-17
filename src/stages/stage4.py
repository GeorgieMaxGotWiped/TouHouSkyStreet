# 四面：地下墓穴深处 ~ The Catacombs
# 道中Boss：Scarf（学徒死灵术士）
# 关底Boss：Sadan（死灵王）
# 道中Boss Scarf 使用唯一符卡队符「Necrotic Squad」；关底 Sadan 使用三张通常符与一张 Last Spell。

import math
import os
import random

import pygame

from src.engine import settings as cfg
from src.engine.collision import circle_collision
from src.engine.pseudo3d import Pseudo3DFloor
from src.entities.boss import Boss, SpellCard
from src.entities.bullet import Bullet, create_bullet_angle, create_bullet_aimed
from src.entities.enemy import (
    Enemy,
    EnemyWave,
    FairyEnemy,
    FairyVolleyEnemy,
    GuardEnemy,
    GraveCasterEnemy,
    SpiritEnemy,
)
from src.stages.stage1 import Stage, BOSS_BG_RAMP_TIME, FINAL_BOSS_BG_SPEED_MULT


# 四面 Boss 血量：三张通常符与一张 Last Spell，弹幕暂不填充。
SCARF_MAX_HP = 7200
SADAN_MAX_HP = 36000


# ---------------------------------------------------------------------------
# 小怪工厂与专属移动逻辑
# ---------------------------------------------------------------------------

def _undead(x, y, move_pattern="descend"):
    """四面食尸鬼：使用四面 undead 贴图，数值略高于三面同类。"""
    enemy = FairyEnemy(x, y, move_pattern,
                       sprite_paths=cfg.STAGE4_FAIRY_SPRITES,
                       sprite_height=cfg.STAGE4_FAIRY_SPRITE_HEIGHT)
    enemy.defense = 1.6
    enemy.move_speed = 1.35
    return enemy


def _soul(x, y, move_pattern="strafe"):
    """四面游魂：横向小幅漂移 + 下坠，散射弹。"""
    enemy = SpiritEnemy(x, y, move_pattern,
                        sprite_paths=cfg.STAGE4_SPIRIT_SPRITES,
                        sprite_height=cfg.STAGE4_SPIRIT_SPRITE_HEIGHT)
    enemy.defense = 1.6
    enemy.move_speed = 0.9
    enemy.move_amplitude = 2.8
    return enemy


def _skeleton(x, y):
    """四面骷髅守卫：原地环形弹幕。"""
    enemy = GuardEnemy(x, y,
                       sprite_paths=cfg.STAGE4_GUARD_SPRITES,
                       sprite_height=cfg.STAGE4_GUARD_SPRITE_HEIGHT)
    enemy.defense = 2.2
    return enemy


def _caster(x, y, deploy_y=168):
    """四面墓穴唤魂者：快速下坠到部署位后连发环弹。"""
    return GraveCasterEnemy(x, y, deploy_y=deploy_y,
                            sprite_paths=cfg.STAGE4_CASTER_SPRITES,
                            sprite_height=cfg.STAGE4_CASTER_SPRITE_HEIGHT)


def _undead_chain(x, count=10, spacing=40, start_y=-16, volley_stagger=9, lead_in=110):
    """食尸鬼队列：一列依次降下，入画后按极短间隔依次瞄准射击。"""
    chain = [
        FairyVolleyEnemy(x, start_y - i * spacing, volley_index=i,
                         volley_stagger=volley_stagger, lead_in=lead_in,
                         sprite_paths=cfg.STAGE4_FAIRY_SPRITES,
                         sprite_height=cfg.STAGE4_FAIRY_SPRITE_HEIGHT)
        for i in range(count)
    ]
    for enemy in chain:
        enemy.defense = 1.6
    return chain


class CryptWraithEnemy(SpiritEnemy):
    """墓穴幽魂：从画面左右两侧横向切入，边飘边发射自机狙。

    相比前三面常见的“顶部降落→射击→离场”，它从侧方贯穿战场，
    用来在四面制造交叉火力与不对称节奏。
    """

    def __init__(self, x, y, direction=1):
        super().__init__(x, y, "sin",
                         sprite_paths=cfg.STAGE4_SPIRIT_SPRITES,
                         sprite_height=cfg.STAGE4_SPIRIT_SPRITE_HEIGHT)
        self.direction = 1 if direction >= 0 else -1
        self.vx = self.direction * 1.9
        self.vy = 0.45
        self.move_speed = 0.0
        self.move_amplitude = 5.0
        self.shoot_interval = 44
        self.shoot_pattern = "aimed"
        self.defense = 1.7
        self.entry_done = True

    def _move(self):
        self.x += self.vx
        self.y += self.vy + math.sin(self.age * 0.045) * self.move_amplitude


class BoneSniperEnemy(GuardEnemy):
    """骷髅狙击手：原地驻守，以“单发贯穿箭 → 三发扇形箭”循环射击。"""
    def __init__(self, x, y):
        super().__init__(x, y,
                         sprite_paths=cfg.STAGE4_GUARD_SPRITES,
                         sprite_height=cfg.STAGE4_GUARD_SPRITE_HEIGHT)
        self.shoot_interval = 72
        self.shoot_pattern = "none"
        self.shoot_cycle = 1
        self.defense = 2.0

    def shoot(self, bullet_manager, player_x, player_y):
        self.shoot_cycle = (self.shoot_cycle + 1) % 2
        base = math.atan2(player_y - self.y, player_x - self.x)
        if self.shoot_cycle == 0:
            b = create_bullet_angle(self.x, self.y, base, 3.0,
                                    Bullet.TYPE_ARROW, radius=2.4,
                                    color=(190, 165, 205))
            bullet_manager.add_enemy_bullet(b)
        else:
            for offset in (-0.26, 0.0, 0.26):
                b = create_bullet_angle(self.x, self.y, base + offset, 2.4,
                                        Bullet.TYPE_KNIFE, radius=2.4,
                                        color=(150, 120, 180))
                bullet_manager.add_enemy_bullet(b)


# ---------------------------------------------------------------------------
# Boss 专属非符弹幕（暂无符卡）
# ---------------------------------------------------------------------------

class SkeletorEnemy(SpiritEnemy):
    """Skeletor 小怪：以正常 soul 形态入场，soul 被击破时向四周放出两圈弹幕并变为 skeletor。
    skeletor 形态使用 stage4/skeletor.png，发射初速较低、会持续加速的自机瞄准麟弹。
    """

    SOUL_HP = 80
    SKELETOR_HP = 260

    def __init__(self, x, y, move_pattern="strafe"):
        super().__init__(x, y, move_pattern,
                         sprite_paths=cfg.STAGE4_SPIRIT_SPRITES,
                         sprite_height=cfg.STAGE4_SPIRIT_SPRITE_HEIGHT)
        self.phase = "soul"
        self.burst_pending = False
        self.hp = self.max_hp = self.SOUL_HP
        self.defense = 1.6
        self.move_speed = 0.9
        self.move_amplitude = 2.8
        self.shoot_interval = 120
        self.shoot_pattern = "spread"

    def update(self, dt, player_x=0, player_y=0):
        if self.phase == "soul" and self.hp <= 0:
            self._become_skeletor()
        super().update(dt, player_x, player_y)

    def take_damage(self, damage):
        if self.phase == "soul":
            self.hp -= damage / self.defense
            if self.hp <= 0:
                self._become_skeletor()
            return False
        return super().take_damage(damage)

    def _become_skeletor(self):
        self.phase = "skeletor"
        self.burst_pending = True
        self.hp = self.max_hp = self.SKELETOR_HP
        self.defense = 2.0
        self.sprite_paths = cfg.STAGE4_SKELETOR_SPRITES
        self.sprite_height = cfg.STAGE4_SKELETOR_SPRITE_HEIGHT
        self.move_pattern = "strafe"
        self.move_speed = 0.45
        self.move_amplitude = 1.5
        self.shoot_interval = 56
        self.shoot_pattern = "none"
        self.shoot_timer = 12

    def emit_death_burst(self, bullet_manager):
        """soul 击破瞬间的两圈环状弹幕。"""
        if not self.burst_pending:
            return
        self.burst_pending = False
        rings = (
            (10, 1.6, 0.0, 2.6, (190, 145, 225)),
            (16, 2.4, math.pi / 16, 2.4, (225, 205, 255)),
        )
        for count, speed, offset, radius, color in rings:
            for i in range(count):
                angle = offset + i * math.tau / count
                b = create_bullet_angle(self.x, self.y, angle, speed,
                                        Bullet.TYPE_CIRCLE, radius=radius,
                                        color=color)
                bullet_manager.add_enemy_bullet(b)

    def can_shoot(self):
        if self.burst_pending:
            return False
        return super().can_shoot()

    def shoot(self, bullet_manager, player_x, player_y):
        if self.phase == "soul":
            super().shoot(bullet_manager, player_x, player_y)
            return

        # 麟弹：初始速度低，沿自机方向逐渐加速。
        b = create_bullet_aimed(self.x, self.y, player_x, player_y, 1.15,
                                Bullet.TYPE_RICE, radius=2.4,
                                color=(175, 140, 225), lifetime=700)
        b.sprite_slot = "g01_00"
        b.accel = 0.028
        bullet_manager.add_enemy_bullet(b)


def _add(bullet_manager, b):
    bullet_manager.add_enemy_bullet(b)


def _non_spell_scarf(boss, bullet_manager, timer, player_x, player_y):
    """Scarf 非符：亡者队列、骷髅弹幕与灵魂沙风暴的意象。

    三发刀弹自机狙是基础压迫；周期性紫色圆环像亡灵环绕；
    左右两侧箭弹从下方扇出，模拟 Scarf 的 Undead 夹击。
    """
    if timer % 150 == 0:
        boss.move_to(random.uniform(cfg.BATTLE_AREA_WIDTH * 0.28,
                                    cfg.BATTLE_AREA_WIDTH * 0.72),
                     random.uniform(82, 128))

    if timer % 30 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for offset in (-0.20, 0.0, 0.20):
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, base + offset, 2.6,
                Bullet.TYPE_KNIFE, radius=2.5, color=(245, 105, 105)))

    if timer % 55 == 0:
        for i in range(10):
            angle = timer * 0.023 + i * math.tau / 10
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, angle, 1.7,
                Bullet.TYPE_CIRCLE, radius=2.6, color=(150, 82, 220)))

    if timer % 120 == 0:
        for side in (-1, 1):
            for i in range(3):
                angle = math.pi / 2 + side * (0.26 + i * 0.19)
                b = create_bullet_angle(boss.x + side * 44, boss.y - 10,
                                        angle, 2.1,
                                        Bullet.TYPE_ARROW, radius=2.4,
                                        color=(180, 150, 225))
                b.turn_rate = side * 0.008
                _add(bullet_manager, b)

    if timer % 190 == 0:
        for i in range(4):
            angle = timer * 0.02 + i * math.tau / 4
            b = create_bullet_angle(boss.x, boss.y, angle, 1.9,
                                    Bullet.TYPE_BIG, radius=4.4,
                                    color=(225, 80, 80))
            b.brake = 0.012
            b.brake_floor = 0.65
            _add(bullet_manager, b)


def _non_spell_sadan(boss, bullet_manager, timer, player_x, player_y):
    """Sadan 非符：巨人、巨石与赤陶军的混合弹幕意象。

    顶部刀弹扇是持续压迫；周期性赤陶米弹从头顶列阵落下；
    大玉巨石缓慢下坠并减速；四把旋转刀弹模拟巨人挥剑。
    """
    if timer % 180 == 0:
        target_x = max(cfg.BATTLE_AREA_WIDTH * 0.25,
                       min(cfg.BATTLE_AREA_WIDTH * 0.75,
                           boss.x + random.uniform(-60, 60)))
        boss.move_to(target_x, random.uniform(88, 126))

    if timer % 26 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for offset in (-0.30, -0.15, 0.0, 0.15, 0.30):
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, base + offset, 2.8,
                Bullet.TYPE_KNIFE, radius=2.5, color=(205, 125, 90)))

    if timer % 62 == 0:
        for col in (-170, -60, 60, 170):
            x = max(30, min(cfg.BATTLE_AREA_WIDTH - 30, boss.x + col))
            _add(bullet_manager, create_bullet_angle(
                x, -12, math.pi / 2, random.uniform(2.0, 2.7),
                Bullet.TYPE_RICE, radius=2.2, color=(185, 130, 95)))

    if timer % 88 == 0:
        for i in range(14):
            angle = timer * 0.017 + i * math.tau / 14
            color = (150, 78, 220) if i % 2 == 0 else (225, 130, 60)
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, angle, 1.8,
                Bullet.TYPE_CIRCLE, radius=2.7, color=color))

    if timer % 128 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for i in range(3):
            angle = base + (i - 1) * 0.34
            b = create_bullet_angle(boss.x, boss.y, angle, 2.2,
                                    Bullet.TYPE_BIG, radius=4.6,
                                    color=(210, 95, 70))
            b.brake = 0.010
            b.brake_floor = 0.85
            _add(bullet_manager, b)

    if timer % 200 == 0:
        for i in range(4):
            angle = timer * 0.022 + i * math.tau / 4
            b = create_bullet_angle(boss.x, boss.y, angle, 2.9,
                                    Bullet.TYPE_ARROW, radius=2.3,
                                    color=(220, 160, 90))
            b.turn_rate = 0.010
            _add(bullet_manager, b)


_SADAN_TERRACOTTA = {
    "rows": 6,
    "cols": 8,
    "margin_x": 30,
    "start_y": 150,
    "row_gap": 46,
    "sprite_height": 38,
    "soldier_hp": 48,
    "soldier_boss_damage": 200,
    "hit_radius": 15,
    "down_time": 190,
    "revive_time": 38,
    "charge_time": 42,
    "charge_bottom": cfg.BATTLE_AREA_HEIGHT - 110,
    "wave_interval": 280,
    "rank_wave_offset": 42,
    "column_stagger": 3,
    "fan_fire_points": (2, 14, 28),
    "fan_count": 5,
    "fan_spread": 0.42,
    "fan_speed": 2.15,
    "fan_lifetime": 320,
    "kunai_interval": 18,
    "kunai_count": 8,
    "kunai_speed": 1.35,
    "kunai_lifetime": 430,
    "melee_bullet": (226, 136, 76),
    "kunai_bullet": (205, 128, 84),
    "clay_light": (232, 158, 92),
}


def _sadan_terracotta_make_army(P):
    w = cfg.BATTLE_AREA_WIDTH
    margin = P["margin_x"]
    gap = (w - margin * 2) / max(1, P["cols"] - 1)
    army = []
    for row in range(P["rows"]):
        y = P["start_y"] + row * P["row_gap"]
        for col in range(P["cols"]):
            x = margin + col * gap
            army.append({
                "row": row,
                "col": col,
                "home_x": x,
                "home_y": y,
                "x": x,
                "y": y,
                "sprite": cfg.STAGE4_TERRACOTTA_SPRITE,
                "sprite_height": P["sprite_height"],
                "hp": P["soldier_hp"],
                "max_hp": P["soldier_hp"],
                "phase": "active",
                "timer": 0,
                "attack_active": False,
                "attack_charge": 0.0,
                "melee": row >= P["rows"] - 3,
            })
    return army


def _sadan_terracotta_particles(bullet_manager, x, y, P, count=6, speed=1.2, lifetime=26):
    for i in range(count):
        ang = i * math.tau / count + random.uniform(-0.35, 0.35)
        b = create_bullet_angle(x, y, ang, random.uniform(0.55, speed),
                                Bullet.TYPE_CIRCLE, radius=1.8,
                                color=random.choice((P["clay_light"], P["melee_bullet"])))
        b.harmless = True
        b.manager = bullet_manager
        b.lifetime = random.randint(max(8, lifetime - 8), lifetime)
        bullet_manager.add_enemy_bullet(b)


def _sadan_terracotta_down(s, bullet_manager, P):
    if s["phase"] == "down":
        return
    s["phase"] = "down"
    s["timer"] = 0
    s["hp"] = 0
    s["attack_active"] = False
    s["attack_charge"] = 0.0
    _sadan_terracotta_particles(bullet_manager, s["x"], s["y"], P,
                                count=9, speed=1.5, lifetime=30)


def _sadan_terracotta_revive(s, bullet_manager, P):
    s["phase"] = "active"
    s["timer"] = 0
    s["hp"] = s["max_hp"]
    s["x"] = s["home_x"]
    s["y"] = s["home_y"]
    s["attack_active"] = False
    s["attack_charge"] = 0.0
    _sadan_terracotta_particles(bullet_manager, s["x"], s["y"], P,
                                count=6, speed=1.1, lifetime=24)


def _sadan_terracotta_wave_for(s, timer, P):
    order = P["rows"] - 1 - s["row"]
    return (timer - order * P["rank_wave_offset"]) % P["wave_interval"]


def _sadan_terracotta_fan(bullet_manager, s, P):
    count = P["fan_count"]
    step = P["fan_spread"] / max(1, count - 1)
    for i in range(count):
        angle = math.pi / 2 + (i - (count - 1) / 2) * step
        b = create_bullet_angle(s["x"], s["y"], angle, P["fan_speed"],
                                Bullet.TYPE_RICE, radius=2.4,
                                color=P["melee_bullet"],
                                lifetime=P["fan_lifetime"])
        bullet_manager.add_enemy_bullet(b)


def _sadan_terracotta_kunai_ring(bullet_manager, s, P):
    count = P["kunai_count"]
    base = (s["col"] % 2) * (math.pi / count)
    for i in range(count):
        angle = base + i * math.tau / count
        b = create_bullet_angle(s["x"], s["y"], angle, P["kunai_speed"],
                                Bullet.TYPE_KNIFE, radius=2.2,
                                color=P["kunai_bullet"],
                                lifetime=P["kunai_lifetime"])
        bullet_manager.add_enemy_bullet(b)


def _sadan_terracotta_update_active(s, bullet_manager, timer, P):
    wave = _sadan_terracotta_wave_for(s, timer, P)
    in_wave = wave < P["charge_time"]
    s["attack_active"] = in_wave

    if not in_wave:
        s["attack_charge"] = 0.0
        s["x"] = s["home_x"]
        s["y"] = s["home_y"]
        return

    if s["melee"]:
        prog = min(1.0, wave / P["charge_time"])
        s["attack_charge"] = prog
        s["x"] = s["home_x"]
        target_y = max(s["home_y"], P["charge_bottom"])
        s["y"] = s["home_y"] + (target_y - s["home_y"]) * s["attack_charge"]
        local = wave - s["col"] * P["column_stagger"]
        if local >= 0 and local in P["fan_fire_points"]:
            _sadan_terracotta_fan(bullet_manager, s, P)
        return

    s["attack_charge"] = 0.0
    s["x"] = s["home_x"]
    s["y"] = s["home_y"]
    local = wave - s["col"] * P["column_stagger"]
    if local < 0:
        return
    if local % P["kunai_interval"] == 0 and local < P["charge_time"]:
        _sadan_terracotta_kunai_ring(bullet_manager, s, P)


def _sadan_terracotta_check_hits(army, bullet_manager, P, boss):
    for s in army:
        if s["phase"] != "active":
            continue
        for pb in bullet_manager.player_bullets[:]:
            if not pb.alive or pb.cancel_timer > 0:
                continue
            if circle_collision(s["x"], s["y"], P["hit_radius"],
                                pb.x, pb.y, pb.collision_radius):
                pb.alive = False
                s["hp"] -= pb.damage
                if s["hp"] <= 0:
                    _sadan_terracotta_down(s, bullet_manager, P)
                    boss.take_damage(P["soldier_boss_damage"])
                    drop_cb = getattr(boss, "terracotta_drop_callback", None)
                    if drop_cb is not None:
                        drop_cb(s)
                    if boss.phase != "spell" or not boss.alive:
                        return
                    break


def spell_sadan_terracotta_army(boss, bullet_manager, timer, dt,
                                player_x=0, player_y=0):
    """兵符「Terracotta Army」：Sadan 的第一符卡。

    兵马俑以 6 排 × 8 列的军阵列队，每排从左到右铺满战场；前 3 排
    近战单位周期性向下冲锋到底并释放短程扇形弹，后 3 排弓手释放
    环形苦无弹。被玩家击破的单位会倒下并留下石质头骨标记，稍后
    回到原阵位复活，且每次击破都会削减 Sadan 的血量。
    """
    P = _SADAN_TERRACOTTA

    if timer == 1:
        boss.sadan_army = _sadan_terracotta_make_army(P)
        return

    boss.target_x = cfg.BATTLE_AREA_WIDTH / 2 + math.sin(timer * 0.006) * 16
    boss.target_y = 118 + math.sin(timer * 0.011) * 5

    for s in boss.sadan_army:
        if s["phase"] == "active":
            _sadan_terracotta_update_active(s, bullet_manager, timer, P)
        elif s["phase"] == "down":
            s["timer"] += 1
            if s["timer"] >= P["down_time"]:
                s["phase"] = "reviving"
                s["timer"] = 0
        elif s["phase"] == "reviving":
            s["timer"] += 1
            if s["timer"] >= P["revive_time"]:
                _sadan_terracotta_revive(s, bullet_manager, P)

    _sadan_terracotta_check_hits(boss.sadan_army, bullet_manager, P, boss)



# ---------------------------------------------------------------------------
# Spell Card: Giant Sign "Precursors' Return"
# One continuous loop: Bigfoot -> The Diamond Giant -> L.A.S.R. -> Jolly Pink Giant.
# All timing/pattern parameters are centralized below.
# ---------------------------------------------------------------------------

PRECURSORS_RETURN_SPELL = {
    "order": ("bigfoot", "diamond", "laser", "jolly"),
    "opening_time": 12,
    "rest_base": 20,
    "rest_step": 2,
    "rest_min": 10,
    "telegraph_base": 16,
    "telegraph_step": 1,
    "telegraph_min": 10,
    "entry_base": 14,
    "entry_step": 1,
    "entry_min": 8,
    "exit_time": 24,
    "max_ramp": 4,
    "giant_scale": 1.5,
    "giant_hp": 1500,
    "giant_boss_damage": 1500,
    "sword_sprite": cfg.STAGE4_DIAMOND_SWORD_SPRITE,
    "sword_height": 660,
    "sword_fall_speed": 6.333333333333333,
    "sword_land_y": 500,
    "giants": {
        "bigfoot": {
            "label": "Bigfoot",
            "sprite": cfg.STAGE4_BIGFOOT_SPRITE,
            "height": 285,
            "color": (126, 88, 66),
            "slot_x": int(cfg.BATTLE_AREA_WIDTH * 0.26),
            "ground_y": 200,
            "hit_radius": 78,
            "origin_y": -210,
            "ease": 2.0,
            "stomp_cycle": 240,
            "stomp_slots": (120, 288, 456),
            "slam_time": 88,
            "slam_ring_interval": 16,
            "slam_ring_count": 13,
            "slam_ring_layers": 4,
            "slam_ring_grow": 3.2,
            "slam_debris_count": 28,
            "slam_debris_speed": 2.2,
            "arc_layers": 5,
            "arc_rays": 9,
            "arc_half": 0.85,
            "arc_grow": 2.8,
            "debris_count": 28,
            "debris_speed": 2.0,
        },
        "diamond": {
            "label": "The Diamond Giant",
            "sprite": cfg.STAGE4_DIAMOND_GIANT_SPRITE,
            "height": 300,
            "color": (84, 190, 255),
            "slot_x": int(cfg.BATTLE_AREA_WIDTH * 0.74),
            "ground_y": 220,
            "hit_radius": 80,
            "origin_y": -220,
            "ease": 1.6,
            "exit_time": 200,
            "toss_first": 18,
            "toss_interval": 330,
            "boulder_count": 12,
            "boulder_speed": 3.6,
            "boulder_radius": 9.0,
            "boulder_color": (120, 205, 255),
            "boulder_split_time": 70,
            "boulder_spread": 1.45,
            "toss_target": (int(cfg.BATTLE_AREA_WIDTH * 0.20), 250),
            "split_count": 16,
            "split_spread": 0.62,
            "split_speed": 2.55,
            "spark_interval": 42,
            "spark_count": 20,
            "spark_speed": 1.95,
        },
        "laser": {
            "label": "L.A.S.R.",
            "sprite": cfg.STAGE4_LASR_SPRITE,
            "height": 285,
            "color": (255, 70, 70),
            "slot_left": int(cfg.BATTLE_AREA_WIDTH * 0.22),
            "slot_right": int(cfg.BATTLE_AREA_WIDTH * 0.78),
            "ground_y": 180,
            "hit_radius": 72,
            "origin_y": -210,
            "ease": 1.0,
            "hidden_time": 30,
            "warn_time": 24,
            "active_time": 95,
            "recover_time": 30,
            "laser_radius": 4,
            "laser_color": (255, 70, 70),
            "secondary_interval": 12,
            "secondary_speed": 1.55,
            "secondary_columns": (48, 120, 192, 264, 336, 408, 480, 552),
            "guard_ring_interval": 40,
            "guard_ring_count": 18,
            "guard_ring_speed": 1.5,
        },
        "jolly": {
            "label": "Jolly Pink Giant",
            "sprite": cfg.STAGE4_JOLLY_PINK_GIANT_SPRITE,
            "height": 300,
            "color": (255, 120, 175),
            "slot_x": int(cfg.BATTLE_AREA_WIDTH * 0.50),
            "ground_y": 215,
            "hit_radius": 80,
            "origin_y": -220,
            "ease": 0.8,
            "pulse_first": 8,
            "pulse_interval": 56,
            "ring_layers": 5,
            "ring_count": 24,
            "ring_spacing": 20,
            "ring_grow": 2.7,
            "petal_interval": 56,
            "petal_count": 24,
            "petal_speed": 1.9,
        },
    },
}


def _pr_ramp(state):
    """Ramps spell pressure by cycle, but never by unbounded bullet speed."""
    return min(state.get("cycle", 0), PRECURSORS_RETURN_SPELL["max_ramp"])


def _pr_duration(base, step, minimum, ramp):
    """Shortens transition windows as the loop repeats."""
    return max(minimum, base - step * ramp)


class GiantHitbox:
    """Enemy-style proxy for the active giant.

    The stage's player-bullet collision and homing code expects an object with
    x/y/alive, a score and collides_with_bullet/take_damage. The persistent
    giant record in boss.sadan_giant_state remains the source of truth.
    """

    def __init__(self, record):
        self.record = record
        self.score = 1200
        self.resistance = 1.0

    @property
    def x(self):
        return self.record.get("x", 0.0)

    @property
    def y(self):
        return self.record.get("y", 0.0)

    @property
    def alive(self):
        return bool(self.record.get("alive"))

    @property
    def hp(self):
        return self.record.get("hp", 0)

    @hp.setter
    def hp(self, value):
        self.record["hp"] = max(0.0, value)
        if self.record.get("alive") and self.record["hp"] <= 0:
            self.record["alive"] = False
            self.record["kill_pending"] = True
            _pr_on_giant_killed(self.record)

    def collides_with_bullet(self, bx, by, br):
        if not self.alive:
            return False
        if self.record.get("phase") not in ("entering", "attack", "stomping"):
            return False
        return circle_collision(bx, by, br, self.x, self.y,
                                self.record.get("hit_radius", 90))

    def take_damage(self, damage):
        if not self.alive:
            return False
        if self.record.get("phase") not in ("entering", "attack", "stomping"):
            return False
        self.hp = self.record["hp"] - damage
        return self.record.get("kill_pending", False)


def _pr_init_state(boss):
    """Creates persistent giant records and the single spell-long state machine."""
    P = PRECURSORS_RETURN_SPELL
    state = {
        "cycle": 0,
        "phase": "opening",
        "t": 0,
        "giant_index": 0,
        "giants": [],
        "giant": None,
        "telegraph": None,
        "laser": None,
        "laser_beam": None,
        "waves": [],
        "boulder_refs": [],
        "sword": None,
        "player_history": [],
    }
    boss.sadan_giant_state = state

    for index, kind in enumerate(P["order"]):
        spec = _pr_giant_spec(kind, index)
        record = {
            "kind": kind,
            "label": spec["label"],
            "sprite": spec["sprite"],
            "height": spec["height"],
            "color": spec["color"],
            "home_x": spec["slot_x"],
            "home_y": spec["ground_y"],
            "origin_y": spec["origin_y"],
            "hit_radius": spec["hit_radius"],
            "ease": spec["ease"],
            "x": spec["slot_x"],
            "y": spec["ground_y"],
            "alpha": 0,
            "hp": P["giant_hp"],
            "max_hp": P["giant_hp"],
            "alive": True,
            "kill_pending": False,
            "kill_applied": False,
            "phase": "waiting",
            "local_t": 0,
            "stomp_active": False,
            "stomp_t": 0,
            "next_stomp_at": 1,
            "stomp_x": spec["slot_x"],
            "stomp_start_y": spec["origin_y"],
            "stomp_end_y": cfg.BATTLE_AREA_HEIGHT + spec["height"] * 0.5,
            "boss": boss,
            "state": state,
        }
        record["proxy"] = GiantHitbox(record)
        state["giants"].append(record)


def _pr_push_player_history(state, player_x, player_y):
    """Keeps the last 30 frames of player positions for the delayed L.A.S.R. aim."""
    history = state.setdefault("player_history", [])
    history.append((player_x, player_y))
    if len(history) > 30:
        history.pop(0)


def _pr_giant_spec(kind, cycle):
    """Returns fixed spawn/attack data for a giant.

    L.A.S.R. keeps two fixed side slots and alternates them by cycle; its beam aim
    is updated dynamically from the delayed player position.
    """
    data = dict(PRECURSORS_RETURN_SPELL["giants"][kind])
    scale = PRECURSORS_RETURN_SPELL["giant_scale"]
    data["height"] = int(round(data["height"] * scale))
    data["hit_radius"] = data["hit_radius"] * scale
    if kind == "laser":
        data["slot_x"] = data["slot_left"] if cycle % 2 == 0 else data["slot_right"]
    return data


def _pr_add_wave(state, x, y, color, start_radius=18, end_radius=180,
                 life=36, width=2):
    """Adds a non-collision shockwave animation ring."""
    state.setdefault("waves", []).append({
        "x": x,
        "y": y,
        "color": color,
        "start_radius": start_radius,
        "end_radius": end_radius,
        "life": life,
        "max_life": life,
        "width": width,
    })


def _pr_update_visuals(state):
    """Advances visual-only effects and clears expired bullet references."""
    for wave in state["waves"]:
        wave["life"] -= 1
    state["waves"] = [wave for wave in state["waves"] if wave["life"] > 0]

    state["boulder_refs"] = [ref for ref in state.get("boulder_refs", [])
                             if ref["b"].alive]
    if state["laser_beam"] is not None and not state["laser_beam"].alive:
        state["laser_beam"] = None


def _pr_begin_telegraph(boss, state, ramp):
    """Shows a readable warning at the next fixed giant slot."""
    order = PRECURSORS_RETURN_SPELL["order"]
    kind = order[state["giant_index"]]
    spec = _pr_giant_spec(kind, state["cycle"])

    state["giant"] = None
    state["telegraph"] = {
        "kind": kind,
        "label": spec["label"],
        "x": spec["slot_x"],
        "y": spec["ground_y"],
        "radius": 32,
        "phase": 0.0,
        "color": spec["color"],
    }
    state["laser"] = None
    state["laser_beam"] = None
    state["boulder_refs"] = []
    state["sword"] = None
    state["phase"] = "telegraph"
    state["t"] = 0


def _pr_begin_entry(boss, state, ramp):
    """Spawns the giant above the battlefield and starts its entry animation."""
    kind = state["telegraph"]["kind"]
    spec = _pr_giant_spec(kind, state["cycle"])
    giant = state["giants"][state["giant_index"]]
    giant["kind"] = kind
    giant["label"] = spec["label"]
    giant["sprite"] = spec["sprite"]
    giant["height"] = spec["height"]
    giant["color"] = spec["color"]
    giant["home_x"] = spec["slot_x"]
    giant["home_y"] = spec["ground_y"]
    giant["origin_y"] = spec["origin_y"]
    giant["base_y"] = spec["ground_y"]
    giant["exit_start_y"] = spec["ground_y"]
    giant["ease"] = spec["ease"]
    giant["hit_radius"] = spec["hit_radius"]
    giant["x"] = spec["slot_x"]
    giant["y"] = spec["origin_y"]
    giant["alpha"] = 255
    giant["phase"] = "entering"
    giant["kill_pending"] = False
    giant["kill_applied"] = False
    giant["exit_started"] = False
    giant["stomp_active"] = False
    giant["stomp_t"] = 0
    giant["next_stomp_at"] = 1
    giant["stomp_x"] = spec["slot_x"]
    giant["stomp_start_y"] = spec["origin_y"]
    giant["stomp_end_y"] = cfg.BATTLE_AREA_HEIGHT + spec["height"] * 0.5
    state["giant"] = giant
    state["telegraph"] = None
    state["phase"] = "entering"
    state["t"] = 0


def _pr_update_entry(state, t, ramp):
    """Moves the giant from off-screen to its fixed landing slot."""
    duration = _pr_duration(PRECURSORS_RETURN_SPELL["entry_base"],
                            PRECURSORS_RETURN_SPELL["entry_step"],
                            PRECURSORS_RETURN_SPELL["entry_min"], ramp)
    giant = state["giant"]
    if giant is None:
        return
    p = min(1.0, t / max(1, duration))
    giant["y"] = giant["origin_y"] + (giant["base_y"] - giant["origin_y"]) * (p ** giant["ease"])
    giant["x"] = giant["home_x"]


def _pr_add_ring(bullet_manager, x, y, count, speed, bullet_type, radius,
                 color, lifetime=320, angle_offset=0.0):
    """Adds a deterministic fixed-direction ring of bullets."""
    for i in range(count):
        angle = angle_offset + i * math.tau / count
        b = create_bullet_angle(x, y, angle, speed, bullet_type,
                                radius=radius, color=color, lifetime=lifetime)
        b.manager = bullet_manager
        bullet_manager.add_enemy_bullet(b)


def _pr_bigfoot_landing_arcs(bullet_manager, state, x, y, d, ramp):
    """Heavy landing shock arcs plus a full debris ring."""
    _pr_add_wave(state, x, y, d["color"], 24, 300, 34, 2)

    layers = d["arc_layers"] + ramp // 2
    for layer in range(layers):
        radius = 22 + layer * 16
        grow = max(1.5, d["arc_grow"] - layer * 0.18)
        rays = d["arc_rays"]
        half_rays = rays // 2
        for side in (-1.0, 1.0):
            center = 0.0 if side > 0 else math.pi
            for k in range(-half_rays, half_rays + 1):
                angle = center + k * (2.0 * d["arc_half"] / max(1, rays - 1))
                b = create_bullet_angle(x, y, angle, 0.0, Bullet.TYPE_CIRCLE,
                                        radius=3.0, color=(168, 124, 92),
                                        lifetime=300)
                b.manager = bullet_manager
                b.orbit_center = (x, y)
                b.orbit_radius = radius
                b.orbit_angle = angle
                b.orbit_grow = grow
                b.orbit_speed = 0.0
                bullet_manager.add_enemy_bullet(b)

    count = d["debris_count"] + ramp * 2
    offset = 0.0 if (ramp % 2 == 0) else math.tau / (count * 2)
    _pr_add_ring(bullet_manager, x, y, count, d["debris_speed"],
                 Bullet.TYPE_ARROW, 2.2, (190, 142, 100), 300, offset)


def _pr_bigfoot_slam_rings(bullet_manager, state, giant, d, ramp):
    """Dense expanding rings emitted continuously while Bigfoot slams downward."""
    x, y = giant["x"], giant["y"]
    _pr_add_wave(state, x, y, d["color"], 16, 220, 26, 2)

    layers = d["slam_ring_layers"] + ramp // 2
    count = d["slam_ring_count"] + ramp * 2
    for layer in range(layers):
        radius = 14 + layer * 15
        angle_offset = 0.0 if layer % 2 == 0 else math.tau / (count * 2)
        for i in range(count):
            angle = angle_offset + i * math.tau / count
            b = create_bullet_angle(x, y, angle, 0.0, Bullet.TYPE_CIRCLE,
                                    radius=2.7 if layer % 2 == 0 else 2.2,
                                    color=(168, 124, 92) if layer % 2 == 0 else (210, 164, 116),
                                    lifetime=240)
            b.manager = bullet_manager
            b.orbit_center = (x, y)
            b.orbit_radius = radius
            b.orbit_angle = angle
            b.orbit_grow = max(1.6, d["slam_ring_grow"] - layer * 0.14)
            b.orbit_speed = 0.0
            bullet_manager.add_enemy_bullet(b)

    _pr_add_ring(bullet_manager, x, y, d["slam_debris_count"] + ramp * 2,
                 d["slam_debris_speed"], Bullet.TYPE_ARROW, 2.1,
                 (190, 142, 100), 300, ramp * 0.07)


def _pr_bigfoot_attack(bullet_manager, state, giant, t, ramp, d=None):
    """Bigfoot repeatedly teleports to a fixed upper slot, slams down through
    the screen while releasing expanding rings, then returns home and waits.

    The cycle is 240 frames (4 seconds), so the wait after returning is readable.
    """
    if d is None:
        d = PRECURSORS_RETURN_SPELL["giants"]["bigfoot"]

    if giant.get("stomp_active"):
        giant["stomp_t"] += 1
        duration = max(1, d["slam_time"])
        p = min(1.0, giant["stomp_t"] / duration)
        giant["x"] = giant["stomp_x"]
        giant["y"] = giant["stomp_start_y"] + (
            giant["stomp_end_y"] - giant["stomp_start_y"]) * (p ** 0.85)
        giant["alpha"] = 255
        if giant["stomp_t"] % max(1, d["slam_ring_interval"]) == 0:
            _pr_bigfoot_slam_rings(bullet_manager, state, giant, d, ramp)
        if giant["stomp_t"] >= duration:
            giant["stomp_active"] = False
            giant["x"] = giant["home_x"]
            giant["y"] = giant["home_y"]
            giant["alpha"] = 255
            giant["next_stomp_at"] = t + d["stomp_cycle"]
            _pr_bigfoot_landing_arcs(bullet_manager, state,
                                     giant["x"], giant["y"], d, ramp)
        return

    if t >= giant.get("next_stomp_at", 1):
        giant["stomp_active"] = True
        giant["stomp_t"] = 0
        giant["stomp_x"] = random.choice(d["stomp_slots"])
        giant["stomp_start_y"] = giant["origin_y"]
        giant["stomp_end_y"] = cfg.BATTLE_AREA_HEIGHT + giant["height"] * 0.5
        giant["alpha"] = 0


def _pr_diamond_toss(bullet_manager, state, ramp, d=None):
    """Diamond Giant throws 12 large square boulders along fixed fan paths.

    Every boulder is an oversized TYPE_BIG bullet with a square frame drawn by
    the boss visual layer. They split into fixed diamond shards after a fixed
    flight time.
    """
    giant = state["giant"]
    if d is None:
        d = PRECURSORS_RETURN_SPELL["giants"]["diamond"]
    x, y = giant["x"], giant["y"]
    tx, ty = d["toss_target"]
    base_angle = math.atan2(ty - y, tx - x)
    count = max(1, d["boulder_count"])
    spread = d["boulder_spread"]
    for i in range(count):
        angle = base_angle + (i - (count - 1) / 2) * (spread / max(1, count - 1))
        split_at = d["boulder_split_time"] + (i % 3) * 5
        b = create_bullet_angle(x, y, angle, d["boulder_speed"], Bullet.TYPE_BIG,
                                radius=d["boulder_radius"],
                                color=d["boulder_color"],
                                lifetime=split_at + 120)
        b.manager = bullet_manager
        state.setdefault("boulder_refs", []).append({
            "b": b,
            "split_at": split_at,
            "angle": angle,
        })
        bullet_manager.add_enemy_bullet(b)


def _pr_diamond_spark(bullet_manager, state, ramp, d=None):
    """Fixed diamond-shard ring while the boulder is in flight."""
    giant = state["giant"]
    if d is None:
        d = PRECURSORS_RETURN_SPELL["giants"]["diamond"]
    count = d["spark_count"] + ramp // 2
    _pr_add_ring(bullet_manager, giant["x"], giant["y"], count,
                 d["spark_speed"], Bullet.TYPE_ARROW, 2.2,
                 (150, 215, 255), 300, ramp * 0.11)


def _pr_laser_target(state):
    """Returns the player position from 0.5 seconds ago."""
    history = state.get("player_history", [])
    if history:
        return history[0]
    giant = state.get("giant")
    if giant is None:
        return (cfg.BATTLE_AREA_WIDTH / 2.0, cfg.BATTLE_AREA_HEIGHT / 2.0)
    return (giant["x"], giant["y"] + 120.0)


def _pr_update_laser_aim(state, laser, x, y):
    """Aims the beam at the delayed player position and returns (angle, length)."""
    target_x, target_y = _pr_laser_target(state)
    dx = target_x - x
    dy = target_y - y
    distance = math.hypot(dx, dy)
    if distance < 1.0:
        angle = 0.0
        length = 240.0
    else:
        angle = math.atan2(dy, dx)
        length = distance + 60.0
    laser["x"] = x
    laser["y"] = y
    laser["angle"] = angle
    laser["length"] = length
    return angle, length


def _pr_laser_attack(bullet_manager, state, t, ramp, d=None):
    """L.A.S.R. repeating delayed-player beam.

    Each cycle hides the laser for 30 frames (0.5 seconds), shows a moving
    warning line, fires an active beam that follows the player position from
    0.5 seconds earlier, then recovers. Fixed rain and guard rings keep the
    rest of the field busy without stealing focus from the beam.
    """
    if d is None:
        d = PRECURSORS_RETURN_SPELL["giants"]["laser"]
    giant = state["giant"]
    x, y = giant["x"], giant["y"]

    hidden = d["hidden_time"]
    warn_end = hidden + d["warn_time"]
    active_end = warn_end + d["active_time"]
    cycle = active_end + d["recover_time"]
    local = t % max(1, cycle)

    if local < hidden:
        # Laser vanishes for 0.5s before every new tracking pass.
        if state.get("laser_beam") is not None:
            state["laser_beam"].start_cancel()
            state["laser_beam"] = None
        state["laser"] = None
        return

    if local < warn_end:
        if local == hidden:
            state["laser"] = {
                "x": x,
                "y": y,
                "angle": 0.0,
                "length": 240.0,
                "color": d["laser_color"],
                "phase": "warn",
            }
        if state["laser"] is not None:
            _pr_update_laser_aim(state, state["laser"], x, y)

    elif local < active_end:
        if local == warn_end:
            state["laser"]["phase"] = "active"
            angle, length = _pr_update_laser_aim(state, state["laser"], x, y)
            beam = create_bullet_angle(x, y, angle, 0.0, Bullet.TYPE_BEAM,
                                       radius=d["laser_radius"],
                                       color=d["laser_color"],
                                       lifetime=d["active_time"] + 20)
            beam.manager = bullet_manager
            beam.angle = angle
            beam.beam_length = length
            state["laser_beam"] = beam
            bullet_manager.add_enemy_bullet(beam)

        if state["laser"] is not None:
            _pr_update_laser_aim(state, state["laser"], x, y)
            if state["laser_beam"] is not None:
                state["laser_beam"].angle = state["laser"]["angle"]
                state["laser_beam"].beam_length = state["laser"]["length"]

        interval = max(8, d["secondary_interval"] - ramp * 2)
        if (local - warn_end) % interval == 0:
            for col in d["secondary_columns"]:
                for drift in (-0.16, 0.0, 0.16):
                    b = create_bullet_angle(col, -18, math.pi / 2 + drift,
                                            d["secondary_speed"], Bullet.TYPE_CIRCLE,
                                            radius=2.0, color=(205, 95, 95),
                                            lifetime=470)
                    b.manager = bullet_manager
                    bullet_manager.add_enemy_bullet(b)

    else:
        if local == active_end:
            if state.get("laser_beam") is not None:
                state["laser_beam"].start_cancel()
                state["laser_beam"] = None
            if state["laser"] is not None:
                state["laser"]["phase"] = "recover"

    guard_interval = max(22, d["guard_ring_interval"] - ramp * 2)
    if hidden <= local < active_end and (local - hidden) % guard_interval == 0:
        _pr_add_ring(bullet_manager, x, y, d["guard_ring_count"] + ramp,
                     d["guard_ring_speed"], Bullet.TYPE_KNIFE, 2.2,
                     (255, 110, 110), 300, ramp * 0.05)


def _pr_update_boulder(bullet_manager, state, ramp, d=None):
    """Splits every tracked Diamond boulder after its fixed flight time."""
    if d is None:
        d = PRECURSORS_RETURN_SPELL["giants"]["diamond"]
    for ref in list(state.get("boulder_refs", [])):
        boulder = ref["b"]
        split_at = ref.get("split_at", d["boulder_split_time"])
        if not boulder.alive:
            state["boulder_refs"].remove(ref)
            continue
        if boulder.age < split_at:
            continue

        x, y = boulder.x, boulder.y
        angle = math.atan2(boulder.vy, boulder.vx)
        count = d["split_count"] + ramp * 2
        for i in range(count):
            child_angle = angle + (i - (count - 1) / 2) * d["split_spread"]
            child = create_bullet_angle(x, y, child_angle, d["split_speed"],
                                        Bullet.TYPE_ARROW, radius=2.3,
                                        color=(180, 225, 255), lifetime=340)
            child.manager = bullet_manager
            bullet_manager.add_enemy_bullet(child)

        _pr_add_wave(state, x, y, (150, 215, 255), 12, 90, 20, 2)
        boulder.alive = False
        state["boulder_refs"].remove(ref)


def _pr_spawn_diamond_sword(state, x=None):
    """Spawns the huge diamond sword visual that falls when Diamond Giant leaves."""
    P = PRECURSORS_RETURN_SPELL
    state["sword"] = {
        "x": x if x is not None else cfg.BATTLE_AREA_WIDTH / 2,
        "y": -P["sword_height"],
        "height": P["sword_height"],
        "sprite": P["sword_sprite"],
        "speed": P["sword_fall_speed"],
        "land_y": P["sword_land_y"],
        "alpha": 255,
    }


def _pr_update_sword(state, bullet_manager, ramp):
    """Moves the falling sword and fires a diamond burst when it lands."""
    sword = state.get("sword")
    if not sword:
        return
    sword["y"] += sword["speed"]
    if sword["y"] < sword["land_y"]:
        return

    _pr_add_wave(state, sword["x"], sword["land_y"], (140, 215, 255), 20, 260, 34, 3)
    _pr_add_ring(bullet_manager, sword["x"], sword["land_y"], 28 + ramp * 2,
                 2.0, Bullet.TYPE_ARROW, 2.4, (150, 215, 255), 320)
    state["sword"] = None


def _pr_jolly_pulse(bullet_manager, state, ramp, d=None):
    """Jolly Pink Giant's large expanding concentric rings."""
    giant = state["giant"]
    if d is None:
        d = PRECURSORS_RETURN_SPELL["giants"]["jolly"]
    x, y = giant["x"], giant["y"]

    _pr_add_wave(state, x, y, d["color"], 20, 330, 30, 2)

    layers = d["ring_layers"] + ramp // 2
    count = d["ring_count"] + ramp * 2
    for layer in range(layers):
        radius = 20 + layer * d["ring_spacing"]
        angle_offset = 0.0 if layer % 2 == 0 else math.tau / (count * 2)
        color = (255, 130, 185) if layer % 2 == 0 else (255, 185, 215)
        for i in range(count):
            angle = angle_offset + i * math.tau / count
            b = create_bullet_angle(x, y, angle, 0.0, Bullet.TYPE_CIRCLE,
                                    radius=2.6 if layer % 2 == 0 else 2.2,
                                    color=color, lifetime=300)
            b.manager = bullet_manager
            b.orbit_center = (x, y)
            b.orbit_radius = radius
            b.orbit_angle = angle
            b.orbit_grow = d["ring_grow"]
            b.orbit_speed = 0.0
            bullet_manager.add_enemy_bullet(b)


def _pr_jolly_petals(bullet_manager, state, ramp, d=None):
    """A second fixed pink pattern so the giant is not only rings."""
    giant = state["giant"]
    if d is None:
        d = PRECURSORS_RETURN_SPELL["giants"]["jolly"]
    count = d["petal_count"] + ramp // 2
    _pr_add_ring(bullet_manager, giant["x"], giant["y"], count,
                 d["petal_speed"], Bullet.TYPE_ARROW, 2.4,
                 (255, 150, 195), 340, ramp * 0.09)


def _pr_entry_burst(bullet_manager, state, ramp):
    """Common fixed-range impact burst for every giant landing."""
    giant = state["giant"]
    kind = giant["kind"]
    x, y = giant["x"], giant["y"]
    if kind == "bigfoot":
        d = PRECURSORS_RETURN_SPELL["giants"]["bigfoot"]
        _pr_bigfoot_landing_arcs(bullet_manager, state, x, y, d, ramp)
    elif kind == "diamond":
        _pr_add_ring(bullet_manager, x, y, 34 + ramp * 2, 1.65, Bullet.TYPE_ARROW,
                     2.3, (150, 215, 255), 280)
    elif kind == "laser":
        _pr_add_ring(bullet_manager, x, y, 28 + ramp * 2, 1.55, Bullet.TYPE_KNIFE,
                     2.2, (255, 90, 90), 260)
    else:
        _pr_add_ring(bullet_manager, x, y, 38 + ramp * 2, 1.55, Bullet.TYPE_CIRCLE,
                     2.4, (255, 140, 185), 280)


def _pr_land_giant(bullet_manager, state, ramp):
    """Finishes entry, fires the fixed impact burst and starts the attack phase."""
    giant = state["giant"]
    giant["y"] = giant["base_y"]
    giant["x"] = giant["home_x"]
    giant["exit_start_y"] = giant["base_y"]
    giant["phase"] = "attack"
    giant["local_t"] = 0
    giant["stomp_active"] = False
    giant["stomp_t"] = 0
    _pr_add_wave(state, giant["x"], giant["y"], giant["color"], 18, 190, 30, 2)
    _pr_entry_burst(bullet_manager, state, ramp)


def _pr_begin_exit(state):
    """Starts the giant's off-screen exit after its HP has been depleted."""
    giant = state["giant"]
    if giant is not None:
        giant["phase"] = "exiting"
        giant["exit_start_y"] = giant["y"]
        giant["alpha"] = 255
        if giant["kind"] == "diamond":
            _pr_spawn_diamond_sword(state)
        else:
            state["boulder_refs"] = []
    state["laser"] = None
    state["laser_beam"] = None
    state["phase"] = "exiting"
    state["t"] = 0


def _pr_update_exit(state, t):
    """Moves the giant downward and fades it out."""
    giant = state["giant"]
    if giant is None:
        return
    duration = PRECURSORS_RETURN_SPELL["giants"].get(giant["kind"], {}).get(
        "exit_time", PRECURSORS_RETURN_SPELL["exit_time"])
    p = min(1.0, t / max(1, duration))
    giant["y"] = giant["exit_start_y"] + p * 360.0
    giant["alpha"] = int(255 * (1.0 - p))


def _pr_attack_kind(bullet_manager, state, kind, t, ramp, d=None):
    """Dispatches the current giant's attack."""
    if d is None:
        d = PRECURSORS_RETURN_SPELL["giants"][kind]
    giant = state["giant"]
    if kind == "bigfoot":
        _pr_bigfoot_attack(bullet_manager, state, giant, t, ramp, d)
    elif kind == "diamond":
        if t == d["toss_first"] or (t > d["toss_first"] and
                                    (t - d["toss_first"]) % d["toss_interval"] == 0):
            _pr_diamond_toss(bullet_manager, state, ramp, d)
        if t > 0 and t % d["spark_interval"] == 0:
            _pr_diamond_spark(bullet_manager, state, ramp, d)
    elif kind == "laser":
        _pr_laser_attack(bullet_manager, state, t, ramp, d)
    elif kind == "jolly":
        if t == d["pulse_first"] or (t > d["pulse_first"] and
                                     (t - d["pulse_first"]) % d["pulse_interval"] == 0):
            _pr_jolly_pulse(bullet_manager, state, ramp, d)
        if t > 0 and t % d["petal_interval"] == 0:
            _pr_jolly_petals(bullet_manager, state, ramp, d)


def _pr_select_next_alive(state):
    """Advances the order index to the next living giant."""
    P = PRECURSORS_RETURN_SPELL
    order = P["order"]
    for _ in range(len(order)):
        state["giant_index"] = (state["giant_index"] + 1) % len(order)
        record = state["giants"][state["giant_index"]]
        if record.get("alive"):
            return record
    return None


def _pr_on_giant_killed(record):
    """Applies giant-kill damage to Sadan once and ends the spell on the last kill."""
    if record.get("kill_applied"):
        return
    record["kill_applied"] = True
    record["alive"] = False
    record["kill_pending"] = True

    boss = record.get("boss")
    state = record.get("state")
    if not boss or not state:
        return

    P = PRECURSORS_RETURN_SPELL
    boss.hp = max(0, boss.hp - P["giant_boss_damage"])
    alive_giants = [g for g in state.get("giants", []) if g.get("alive")]
    if alive_giants:
        return

    if boss.current_spell is not None and boss.current_spell.end_hp_threshold is not None:
        floor = boss.max_hp * boss.current_spell.end_hp_threshold
        boss.hp = max(boss.hp, floor)
    boss._end_spell()


def _pr_advance_phase(boss, bullet_manager, state, ramp, dt):
    """Advances the single spell loop by one frame."""
    P = PRECURSORS_RETURN_SPELL
    state["t"] += 1
    t = state["t"]
    phase = state["phase"]

    if phase == "opening":
        if t >= P["opening_time"]:
            _pr_begin_telegraph(boss, state, ramp)
        return

    if phase == "rest":
        rest = _pr_duration(P["rest_base"], P["rest_step"], P["rest_min"], ramp)
        if t >= rest:
            if _pr_select_next_alive(state) is None:
                boss._end_spell()
                return
            if state["giant_index"] == 0:
                state["cycle"] += 1
                ramp = _pr_ramp(state)
            _pr_begin_telegraph(boss, state, ramp)
        return

    if phase == "telegraph":
        duration = _pr_duration(P["telegraph_base"], P["telegraph_step"],
                                P["telegraph_min"], ramp)
        if t >= duration:
            _pr_begin_entry(boss, state, ramp)
        elif state["telegraph"] is not None:
            state["telegraph"]["phase"] = t * 0.35
        return

    if phase == "entering":
        _pr_update_entry(state, t, ramp)
        duration = _pr_duration(P["entry_base"], P["entry_step"],
                                P["entry_min"], ramp)
        if t >= duration:
            _pr_land_giant(bullet_manager, state, ramp)
            state["phase"] = "attack"
            state["t"] = 0
        return

    if phase == "attack":
        giant = state["giant"]
        kind = giant["kind"]
        _pr_attack_kind(bullet_manager, state, kind, t, ramp)
        if giant.get("kill_pending") and not giant.get("exit_started"):
            giant["exit_started"] = True
            _pr_begin_exit(state)
        return

    if phase == "exiting":
        _pr_update_exit(state, t)
        duration = P["giants"].get(state["giant"]["kind"], {}).get(
            "exit_time", P["exit_time"])
        if t >= duration:
            state["giant"] = None
            state["phase"] = "rest"
            state["t"] = 0


def spell_sadan_precursors_return(boss, bullet_manager, timer, dt,
                                  player_x=0, player_y=0):
    """Giant Sign "Precursors' Return": Sadan's second spell card.

    Four ancient giants appear one by one in the same loop:
    Bigfoot stomps, The Diamond Giant throws boulders, L.A.S.R. cuts with a
    delayed-player beam, and Jolly Pink Giant releases expanding pink rings.
    """
    if timer == 1:
        _pr_init_state(boss)

    state = getattr(boss, "sadan_giant_state", None)
    if not state:
        return

    # Sadan stays near his throne; the giants are the actual threat. He is not
    # targetable while this spell is active (handled by Stage4.get_active_enemies).
    boss.target_x = cfg.BATTLE_AREA_WIDTH / 2 + math.sin(timer * 0.004) * 12
    boss.target_y = 112 + math.sin(timer * 0.008) * 4

    _pr_push_player_history(state, player_x, player_y)
    _pr_update_visuals(state)
    ramp = _pr_ramp(state)
    _pr_update_boulder(bullet_manager, state, ramp)
    _pr_update_sword(state, bullet_manager, ramp)
    _pr_advance_phase(boss, bullet_manager, state, ramp, dt)







THE_GIANT_ONE_SPELL = {
    "cycle": 240,
    "skill_pool": ("bigfoot", "diamond", "laser", "jolly"),
    "sprite": cfg.STAGE4_THE_GIANT_ONE_SPRITE,
    "sprite_height": 320,
    "hover_y": 126,
    "origin_y": -340,
    "giant_height": 320,
}


def _tgo_half_data(kind):
    """Returns the Precursors' Return skill data with half bullet count/frequency.

    Bigfoot also keeps its stomp window but falls at half speed, which is
    represented by doubling slam_time.
    """
    d = dict(PRECURSORS_RETURN_SPELL["giants"][kind])

    if kind == "bigfoot":
        d["slam_time"] = max(1, int(round(d["slam_time"] * 2)))
        d["slam_ring_interval"] = max(1, int(round(d["slam_ring_interval"] * 2)))
        d["slam_ring_count"] = max(1, d["slam_ring_count"] // 2)
        d["slam_ring_layers"] = max(1, d["slam_ring_layers"] // 2)
        d["slam_debris_count"] = max(1, d["slam_debris_count"] // 2)
        d["arc_layers"] = max(1, d["arc_layers"] // 2)
        d["arc_rays"] = max(1, d["arc_rays"] // 2)
        d["debris_count"] = max(1, d["debris_count"] // 2)
    elif kind == "diamond":
        d["boulder_count"] = max(1, d["boulder_count"] // 2)
        d["toss_interval"] = max(1, int(round(d["toss_interval"] * 2)))
        d["spark_interval"] = max(1, int(round(d["spark_interval"] * 2)))
        d["spark_count"] = max(1, d["spark_count"] // 2)
        d["split_count"] = max(1, d["split_count"] // 2)
    elif kind == "laser":
        d["active_time"] = max(1, int(round(d["active_time"] * 0.5)))
        d["warn_time"] = max(1, int(round(d["warn_time"] * 2)))
        d["secondary_interval"] = max(1, int(round(d["secondary_interval"] * 2)))
        d["secondary_columns"] = tuple(d["secondary_columns"][::2])
        d["guard_ring_interval"] = max(1, int(round(d["guard_ring_interval"] * 2)))
        d["guard_ring_count"] = max(1, d["guard_ring_count"] // 2)
    elif kind == "jolly":
        d["pulse_interval"] = max(1, int(round(d["pulse_interval"] * 2)))
        d["ring_layers"] = max(1, d["ring_layers"] // 2)
        d["ring_count"] = max(1, d["ring_count"] // 2)
        d["petal_interval"] = max(1, int(round(d["petal_interval"] * 2)))
        d["petal_count"] = max(1, d["petal_count"] // 2)

    return d


def _tgo_select_skills(state):
    """Chooses two distinct Precursors' Return skills for the next 4 seconds."""
    state["skills"] = random.sample(THE_GIANT_ONE_SPELL["skill_pool"], 2)
    state["stomp_active"] = False
    state["stomp_t"] = 0
    state["next_stomp_at"] = 1


def _tgo_init_state(boss):
    """Creates the visual/attack state used by The Giant One spell card."""
    P = THE_GIANT_ONE_SPELL
    center_x = cfg.BATTLE_AREA_WIDTH / 2
    state = {
        "skills": [],
        "waves": [],
        "boulder_refs": [],
        "laser": None,
        "laser_beam": None,
        "sword": None,
        "hide_giant": True,
        "player_history": [],
        "stomp_active": False,
        "stomp_t": 0,
        "next_stomp_at": 1,
        "stomp_x": center_x,
        "stomp_start_y": P["origin_y"],
        "stomp_end_y": cfg.BATTLE_AREA_HEIGHT + P["giant_height"] * 0.5,
        "giant": {
            "x": center_x,
            "y": P["hover_y"],
            "home_x": center_x,
            "home_y": P["hover_y"],
            "base_y": P["hover_y"],
            "origin_y": P["origin_y"],
            "height": P["giant_height"],
            "color": (210, 165, 100),
            "sprite": P["sprite"],
            "label": "The Giant One",
            "alpha": 0,
            "kind": "giant_one",
            "phase": "attack",
        },
    }
    boss.sadan_giant_state = state


def _tgo_bigfoot_attack(bullet_manager, state, boss, t, d):
    """The Giant One's halved Bigfoot stomp.

    The stomp itself lasts twice as long because its fall speed is halved.
    """
    giant = state["giant"]

    if not state.get("stomp_active"):
        if t >= state.get("next_stomp_at", 1):
            state["stomp_active"] = True
            state["stomp_t"] = 0
            state["stomp_x"] = random.choice(d["stomp_slots"])
            state["stomp_start_y"] = THE_GIANT_ONE_SPELL["origin_y"]
            state["stomp_end_y"] = (
                cfg.BATTLE_AREA_HEIGHT + THE_GIANT_ONE_SPELL["giant_height"] * 0.5)
        return

    state["stomp_t"] += 1
    duration = max(1, d["slam_time"])
    p = min(1.0, state["stomp_t"] / duration)
    boss.x = state["stomp_x"]
    boss.y = state["stomp_start_y"] + (
        state["stomp_end_y"] - state["stomp_start_y"]) * (p ** 0.85)
    boss.target_x = boss.x
    boss.target_y = boss.y
    giant["x"] = boss.x
    giant["y"] = boss.y

    if state["stomp_t"] % max(1, d["slam_ring_interval"]) == 0:
        _pr_bigfoot_slam_rings(bullet_manager, state, giant, d, 0)

    if state["stomp_t"] >= duration:
        state["stomp_active"] = False
        boss.x = giant["home_x"]
        boss.y = giant["home_y"]
        boss.target_x = boss.x
        boss.target_y = boss.y
        giant["x"] = boss.x
        giant["y"] = boss.y
        state["next_stomp_at"] = t + d["stomp_cycle"]
        _pr_bigfoot_landing_arcs(bullet_manager, state,
                                 boss.x, boss.y, d, 0)


def _tgo_attack_kind(bullet_manager, state, boss, kind, t):
    """Dispatches one selected half-power skill for The Giant One."""
    d = _tgo_half_data(kind)

    if kind == "bigfoot":
        _tgo_bigfoot_attack(bullet_manager, state, boss, t, d)
    elif kind == "diamond":
        if t == d["toss_first"] or (t > d["toss_first"] and
                                    (t - d["toss_first"]) % d["toss_interval"] == 0):
            _pr_diamond_toss(bullet_manager, state, 0, d)
        if t > 0 and t % d["spark_interval"] == 0:
            _pr_diamond_spark(bullet_manager, state, 0, d)
    elif kind == "laser":
        _pr_laser_attack(bullet_manager, state, t, 0, d)
    elif kind == "jolly":
        if t == d["pulse_first"] or (t > d["pulse_first"] and
                                     (t - d["pulse_first"]) % d["pulse_interval"] == 0):
            _pr_jolly_pulse(bullet_manager, state, 0, d)
        if t > 0 and t % d["petal_interval"] == 0:
            _pr_jolly_petals(bullet_manager, state, 0, d)


def spell_sadan_the_giant_one(boss, bullet_manager, timer, dt,
                              player_x=0, player_y=0):
    """王符「The Giant One」：Sadan's third spell card.

    Sadan transforms into The Giant One. Every 4 seconds it randomly releases
    two of the four Precursors' Return boss skills, with bullet count and
    frequency halved. Bigfoot's stomp falls at half speed.
    """
    P = THE_GIANT_ONE_SPELL

    if timer == 1:
        boss._spell_sprite_restore = (boss.sprite_path, boss.sprite_height)
        boss.sprite_path = P["sprite"]
        boss.sprite_height = P["sprite_height"]
        _tgo_init_state(boss)

    state = getattr(boss, "sadan_giant_state", None)
    if not state:
        return

    local_t = ((timer - 1) % P["cycle"]) + 1
    if local_t == 1:
        _tgo_select_skills(state)

    boss.target_x = cfg.BATTLE_AREA_WIDTH / 2 + math.sin(timer * 0.005) * 16
    boss.target_y = P["hover_y"] + math.sin(timer * 0.011) * 5

    giant = state["giant"]
    giant["x"] = boss.x
    giant["y"] = boss.y

    _pr_push_player_history(state, player_x, player_y)
    _pr_update_visuals(state)
    _pr_update_boulder(bullet_manager, state, 0, _tgo_half_data("diamond"))

    for kind in state["skills"]:
        _tgo_attack_kind(bullet_manager, state, boss, kind, local_t)


_BBW_DURATION = 25 * 60
_BBW_DARK_FRONT_START = float(cfg.BATTLE_AREA_HEIGHT)
_BBW_DARK_FRONT_END = cfg.BATTLE_AREA_HEIGHT * (2.0 / 3.0)
_BBW_DARK_SPEED = 2.0 * (_BBW_DARK_FRONT_START - _BBW_DARK_FRONT_END) / float(_BBW_DURATION)
_BBW_CHANNEL_SPEED = 2.0 * _BBW_DARK_SPEED
_BBW_CHANNEL_TOP_START_Y = _BBW_DARK_FRONT_START
_BBW_CHANNEL_HALF_TURNS = 6
_BBW_CHANNEL_HEIGHT = _BBW_CHANNEL_SPEED * _BBW_DURATION + 60.0
_BBW_CHANNEL_AMPLITUDE = _BBW_CHANNEL_HEIGHT / (2.0 * _BBW_CHANNEL_HALF_TURNS)
_BBW_CHANNEL_BASE_START_Y = _BBW_CHANNEL_TOP_START_Y + _BBW_CHANNEL_HEIGHT
_BBW_CHANNEL_CORRIDOR_HALF_WIDTH = 52.0
_BBW_CHANNEL_NODE_COLOR = (190, 160, 255)
_BBW_SPIRAL_COLORS = ((150, 205, 255), (180, 150, 255), (110, 230, 220))
_BBW_OUTSIDE_WALL_COLOR = (105, 70, 160)
_BBW_OUTSIDE_WALL_RADIUS = 5.0
_BBW_OUTSIDE_ROW_GAP = 14.0
_BBW_OUTSIDE_COL_GAP = 14.0


def _bbw_channel_vertices(base_y):
    """弹簧通道中心线的顶点：整体竖直堆叠，左右交替向上推进。"""
    center_x = cfg.BATTLE_AREA_WIDTH * 0.5
    vertices = []
    for i in range(_BBW_CHANNEL_HALF_TURNS + 1):
        t = i / float(_BBW_CHANNEL_HALF_TURNS)
        y = base_y - _BBW_CHANNEL_HEIGHT * t
        x = center_x + (_BBW_CHANNEL_AMPLITUDE if i % 2 else -_BBW_CHANNEL_AMPLITUDE)
        vertices.append((x, y))
    return vertices


def _bbw_center_x_at_y(base_y, y):
    """返回通道中心线在指定 y 处的 x 坐标。

    中心线是左右交替的折线，这里用于在每一行生成“桥外弹幕”时，
    精确避开左右两串弹幕围出的通道。
    """
    center_x = cfg.BATTLE_AREA_WIDTH * 0.5
    top_y = base_y - _BBW_CHANNEL_HEIGHT
    y = max(top_y, min(base_y, y))
    local = (base_y - y) / float(_BBW_CHANNEL_HEIGHT)
    seg = min(_BBW_CHANNEL_HALF_TURNS - 1,
              int(local * _BBW_CHANNEL_HALF_TURNS))
    t = local * _BBW_CHANNEL_HALF_TURNS - seg
    x0 = center_x + (_BBW_CHANNEL_AMPLITUDE if seg % 2 else -_BBW_CHANNEL_AMPLITUDE)
    x1 = center_x + (_BBW_CHANNEL_AMPLITUDE if (seg + 1) % 2 else -_BBW_CHANNEL_AMPLITUDE)
    return x0 + (x1 - x0) * t


def _bbw_spawn_outside_walls(bullet_manager, base_y, rise, lifetime):
    """填充桥体两侧、桥顶以下的区域，防止玩家从桥外绕行。

    每一行先根据中心线位置算出当前通道边界，再只向左右边界外放置子弹，
    因此桥内仍然保持为可通行通道。
    """
    top_y = base_y - _BBW_CHANNEL_HEIGHT
    width = cfg.BATTLE_AREA_WIDTH
    margin = 14.0
    rows = int(math.ceil(_BBW_CHANNEL_HEIGHT / _BBW_OUTSIDE_ROW_GAP)) + 1

    for row in range(rows):
        y = top_y + row * _BBW_OUTSIDE_ROW_GAP
        if y < top_y - 1.0 or y > base_y + 1.0:
            continue

        center_x = _bbw_center_x_at_y(base_y, y)
        left_bound = center_x - _BBW_CHANNEL_CORRIDOR_HALF_WIDTH
        right_bound = center_x + _BBW_CHANNEL_CORRIDOR_HALF_WIDTH

        x = margin
        while x < left_bound - 6.0:
            wall = Bullet(x, y, 0.0, -rise, Bullet.TYPE_CIRCLE,
                          radius=_BBW_OUTSIDE_WALL_RADIUS,
                          color=_BBW_OUTSIDE_WALL_COLOR,
                          lifetime=lifetime)
            wall.manager = bullet_manager
            wall.ignore_offscreen = True
            _add(bullet_manager, wall)
            x += _BBW_OUTSIDE_COL_GAP

        x = right_bound + 6.0
        while x < width - margin:
            wall = Bullet(x, y, 0.0, -rise, Bullet.TYPE_CIRCLE,
                          radius=_BBW_OUTSIDE_WALL_RADIUS,
                          color=_BBW_OUTSIDE_WALL_COLOR,
                          lifetime=lifetime)
            wall.manager = bullet_manager
            wall.ignore_offscreen = True
            _add(bullet_manager, wall)
            x += _BBW_OUTSIDE_COL_GAP


def _bbw_spawn_channel(boss, bullet_manager, timer):
    """一次性生成下方竖向弹簧通道及桥外弹幕。

    通道由左右两串节点弹围成，桥外区域同时补满压迫弹幕；
    整体以黑暗吞噬速度的 2 倍上升，所有通道/桥外子弹均为可判定弹幕。
    """
    state = boss.bridge_worlds_state
    if state is None:
        return
    rise = _BBW_CHANNEL_SPEED
    base_y = _BBW_CHANNEL_BASE_START_Y - rise * max(0, timer - 1)
    center_vertices = _bbw_channel_vertices(base_y)
    lifetime = _BBW_DURATION + 60

    strands = []
    for offset in (-_BBW_CHANNEL_CORRIDOR_HALF_WIDTH,
                   _BBW_CHANNEL_CORRIDOR_HALF_WIDTH):
        strands.append([(x + offset, y) for x, y in center_vertices])

    for vertices in strands:
        for i in range(len(vertices) - 1):
            x1, y1 = vertices[i]
            x2, y2 = vertices[i + 1]
            seg_len = math.hypot(x2 - x1, y2 - y1)

            steps = max(1, int(round(seg_len / 9.0)))
            for j in range(steps + 1):
                t = j / steps
                x = x1 + (x2 - x1) * t
                y = y1 + (y2 - y1) * t
                node = Bullet(x, y, 0.0, -rise, Bullet.TYPE_CIRCLE,
                              radius=2.8, color=_BBW_CHANNEL_NODE_COLOR,
                              lifetime=lifetime)
                node.manager = bullet_manager
                node.ignore_offscreen = True
                _add(bullet_manager, node)

    _bbw_spawn_outside_walls(bullet_manager, base_y, rise, lifetime)

    state["channel_spawned"] = True


def _bbw_boss_settled(boss):
    """Sadan 是否已经移动到本符的悬停位置。"""
    return math.hypot(boss.target_x - boss.x, boss.target_y - boss.y) <= 6.0


def _bbw_spiral(boss, bullet_manager, timer):
    """顶部高密度低旋转螺旋弹幕。

    低速角速度让弹幕保持螺旋感，同时不会快速转成难以阅读的圆环。
    """
    if timer < 45:
        return

    if timer % 12 == 0:
        base = timer * 0.0105
        for arm in range(4):
            angle = base + arm * math.tau / 4
            color = _BBW_SPIRAL_COLORS[(timer // 4 + arm) % len(_BBW_SPIRAL_COLORS)]
            b = create_bullet_angle(boss.x, boss.y, angle, 1.65,
                                    Bullet.TYPE_CIRCLE, radius=2.5,
                                    color=color, lifetime=720)
            b.turn_rate = 0.0038
            _add(bullet_manager, b)

    if timer % 18 == 0:
        base = -timer * 0.0075
        for arm in range(3):
            angle = base + arm * math.tau / 3 + math.pi / 3
            b = create_bullet_angle(boss.x, boss.y, angle, 1.45,
                                    Bullet.TYPE_CIRCLE, radius=2.3,
                                    color=(235, 235, 255), lifetime=680)
            b.turn_rate = -0.0034
            _add(bullet_manager, b)


def spell_sadan_bridge_between_worlds(boss, bullet_manager, timer, dt,
                                      player_x=0, player_y=0):
    """终符神代「Bridge Between Worlds」：25 秒时符。

    Sadan 在战场上方维持高密度螺旋弹幕，竖向弹簧通道从下方以黑暗 2 倍速升起；
    黑暗从底部向上吞噬自机所在区域（仅遮挡视觉，不造成伤害）。
    作为 Last Spell，Miss 仍会直接结束战斗且不扣残机。
    """
    if timer >= _BBW_DURATION:
        boss.force_end_last_spell()
        return

    if timer == 1 or boss.bridge_worlds_state is None:
        boss.bridge_worlds_state = {
            "darkness_front": _BBW_DARK_FRONT_START,
            "channel_spawned": False,
        }
    state = boss.bridge_worlds_state

    state["darkness_front"] = (_BBW_DARK_FRONT_START
                               - _BBW_DARK_SPEED * min(timer, _BBW_DURATION))

    boss.target_x = cfg.BATTLE_AREA_WIDTH / 2 + math.sin(timer * 0.006) * 18
    boss.target_y = 96 + math.sin(timer * 0.012) * 7

    if timer >= 45 and _bbw_boss_settled(boss):
        _bbw_spiral(boss, bullet_manager, timer)

    if not state.get("channel_spawned"):
        _bbw_spawn_channel(boss, bullet_manager, timer)


# ---------------------------------------------------------------------------
# 队符「Necrotic Squad」——Scarf 的小队协同符卡
# ---------------------------------------------------------------------------

# 四名亡灵成员在战场上的固定站位（位置与配色集中管理，仅视觉成员，攻击由符卡调度）
SCARF_SQUAD_MEMBERS = {
    "warrior": {
        "label": "Warrior", "x": 136, "y": 86,
        "sprite": os.path.join(cfg.BACKGROUNDS_DIR, "stage4", "Undead_Warrior.png"),
        "height": 96,
        "color": (240, 240, 235),
        "float_phase": 0.0,
    },
    "archer": {
        "label": "Archer", "x": 440, "y": 86,
        "sprite": os.path.join(cfg.BACKGROUNDS_DIR, "stage4", "Undead_Archer.png"),
        "height": 66,
        "color": (70, 185, 95),
        "float_phase": 1.25,
    },
    "mage": {
        "label": "Mage", "x": 132, "y": 216,
        "sprite": os.path.join(cfg.BACKGROUNDS_DIR, "stage4", "Undead_Mage.gif"),
        "height": 88,
        "color": (95, 225, 235),
        "float_phase": 2.30,
    },
    "priest": {
        "label": "Priest", "x": 444, "y": 216,
        "sprite": os.path.join(cfg.BACKGROUNDS_DIR, "stage4", "Undead_Priest.png"),
        "height": 82,
        "color": (180, 95, 240),
        "float_phase": 3.55,
    },
}

# 小队职业池：每轮从四个职业中随机洗牌，保证四名职业各出场一次。
SCARF_SQUAD_ORDER = ("warrior", "archer", "mage", "priest")

# 每个职业负责主攻击的持续帧数（60FPS：总循环约 20 秒，切换间隔为上一版的 1/2）。
SCARF_SQUAD_PHASE_DURATIONS = {
    "warrior": 240,
    "archer": 320,
    "mage": 360,
    "priest": 280,
}

SCARF_SQUAD_CYCLE_DURATION = sum(SCARF_SQUAD_PHASE_DURATIONS.values())

# 队符全部参数集中管理：数量、间隔、弹速、弹量、持续时间、循环时间、强化法阵效果。
SCARF_SQUAD_SPELL = {
    "squad_count": 4,
    "float_amp": 13.0,      # 四名成员空中飘浮的垂直振幅
    "float_speed": 0.021,   # 四名成员空中飘浮的正弦频率
    "phase_durations": SCARF_SQUAD_PHASE_DURATIONS,
    "cycle_duration": SCARF_SQUAD_CYCLE_DURATION,
    "buff_center": (cfg.BATTLE_AREA_WIDTH / 2.0, 248.0),
    "buff_brighten": 0.30,
    "split_count": 3,
    "split_spread": 0.55,
    "split_speed_mult": 1.0,
    "priest_circle_positions": (
        (cfg.BATTLE_AREA_WIDTH * 0.24, 210),
        (cfg.BATTLE_AREA_WIDTH * 0.50, 160),
        (cfg.BATTLE_AREA_WIDTH * 0.76, 210),
        (cfg.BATTLE_AREA_WIDTH * 0.32, 330),
        (cfg.BATTLE_AREA_WIDTH * 0.68, 330),
    ),
    "priest_circle_radius": 28,
    "warrior": {
        "fan_interval": 24,      # 扇形压迫弹发射间隔
        "fan_count": 15,
        "fan_half_angle": 0.60,
        "fan_speed": 2.25,
        "ring_interval": 75,     # 白色骨刺圆环发射间隔
        "ring_count": 18,
        "ring_speed": 2.40,
        "radius": 2.2,
        "color": (240, 240, 235),
        "bullet_type": Bullet.TYPE_KNIFE,
    },
    "archer": {
        "arrow_interval": 6,     # 直线箭雨发射间隔
        "arrow_offsets": (-0.48, -0.32, -0.16, 0.0, 0.16, 0.32, 0.48),
        "arrow_speed": 4.60,
        "radius": 2.1,
        "color": (70, 185, 95),
        "bullet_type": Bullet.TYPE_ARROW,
    },
    "mage": {
        "aim_offsets": (-0.8, 0.0, 0.8),  # 瞄准玩家后，左右各复制一组攻击的偏转角
        "orb_interval": 6,       # 灵魂波浪弹发射间隔（慢速高密度）
        "orb_offsets": (-0.34, -0.17, 0.17, 0.34),
        "orb_speed": 1.55,
        "orb_wobble_amp": 20,
        "orb_wobble_freq": 0.085,
        "radius": 2.4,
        "color": (95, 225, 235),
        "bullet_type": Bullet.TYPE_CIRCLE,
    },
    "priest": {
        "ring_interval": 45,     # 牧师自身低频环形弹（攻击强度不高）
        "ring_count": 8,
        "ring_speed": 1.30,
        "radius": 2.3,
        "color": (180, 95, 240),
        "bullet_type": Bullet.TYPE_CIRCLE,
    },
}


def _scarf_brighten(color, amount):
    """强化弹幕配色：把颜色向白色拉近，让经过法阵的子弹更亮。"""
    return tuple(min(255, int(ch + (255 - ch) * amount)) for ch in color)


def _scarf_home_angle(x, y):
    """从成员站位指向强化法阵中心（固定角度，不追踪玩家）。"""
    cx, cy = SCARF_SQUAD_SPELL["buff_center"]
    return math.atan2(cy - y, cx - x)


def _scarf_member_pos(boss, name):
    """返回小队成员当前飘浮位置，弹幕生成点与视觉位置保持一致。"""
    for member in boss.scarf_squad:
        if member.get("name") == name:
            return member["x"], member["y"]
    data = SCARF_SQUAD_MEMBERS[name]
    return data["x"], data["y"]


def _scarf_update_squad_float(boss, timer):
    """让四名小队成员按各自相位在空中上下飘浮，互不错拍。"""
    if not boss.scarf_squad:
        return
    amp = SCARF_SQUAD_SPELL["float_amp"]
    speed = SCARF_SQUAD_SPELL["float_speed"]
    for member in boss.scarf_squad:
        phase = member.get("float_phase", 0.0)
        member["y"] = member["base_y"] + math.sin(timer * speed + phase) * amp


def _scarf_apply_buff(b, boss):
    """牧师强化法阵：判断子弹弹道是否会穿过任一小法阵。

    触碰后子弹会在到达法阵位置时分裂成散射弹，不改变原弹速度；
    只在生成时判定一次，保持弹幕规律可读。
    """
    circles = boss.scarf_buff_circles
    if not circles or getattr(b, "harmless", False):
        return

    dx = math.cos(b.angle)
    dy = math.sin(b.angle)
    speed_before = math.hypot(b.vx, b.vy)
    if speed_before <= 0.001:
        return

    for circle in circles:
        fx = circle["x"] - b.x
        fy = circle["y"] - b.y

        # 射线到圆心的投影：必须朝圆心方向前进，才有机会“触碰”法阵。
        proj = fx * dx + fy * dy
        if proj <= 0:
            continue

        closest_sq = fx * fx + fy * fy - proj * proj
        r = circle["radius"]
        if closest_sq > r * r:
            continue

        b.scarf_empowered = True
        b.color = _scarf_brighten(b.color, SCARF_SQUAD_SPELL["buff_brighten"])

        # 预估子弹到达法阵边界的帧数，让分裂发生在法阵附近。
        entry_distance = max(0.0, proj - math.sqrt(max(0.0, r * r - closest_sq)))
        split_delay = max(1, int(entry_distance / speed_before))
        b.split_spec = {
            "timer": split_delay,
            "count": SCARF_SQUAD_SPELL["split_count"],
            "spread": SCARF_SQUAD_SPELL["split_spread"],
            "speed": speed_before * SCARF_SQUAD_SPELL["split_speed_mult"],
            "type": b.bullet_type,
            "radius": b.radius,
            "color": b.color,
            "aimed": False,
            "base_angle": b.angle,
        }
        break


def _scarf_add(bullet_manager, boss, b, empower=True):
    """统一接入现有 BulletManager，并在必要时应用牧师强化。"""
    b.manager = bullet_manager
    if empower:
        _scarf_apply_buff(b, boss)
    bullet_manager.add_enemy_bullet(b)


def _scarf_burst(bullet_manager, x, y, color, count=8, speed=1.2,
                 radius=2.0, lifetime=26):
    """职业切换/法阵生成时的视觉粒子：固定角度无判定小光点，复用 Bullet 系统。"""
    for i in range(count):
        a = i * math.tau / count + math.pi / count
        p = create_bullet_angle(x, y, a, speed, Bullet.TYPE_CIRCLE,
                                radius=radius, color=color, lifetime=lifetime)
        p.manager = bullet_manager
        p.harmless = True
        bullet_manager.add_enemy_bullet(p)


def _scarf_begin_cycle(boss, cycle_no):
    """每个循环开始时洗牌一次，确保 Warrior/Archer/Mage/Priest 各出场一次。"""
    if getattr(boss, "scarf_pending_order", None) is not None:
        # Priest 为上一轮最后一位时，下一轮顺序已被预先洗好，直接沿用。
        order = boss.scarf_pending_order
        boss.scarf_pending_order = None
    else:
        order = list(SCARF_SQUAD_ORDER)
        random.shuffle(order)
    starts = {}
    accum = 0
    for name in order:
        starts[name] = accum
        accum += SCARF_SQUAD_PHASE_DURATIONS[name]
    boss.scarf_cycle_order = order
    boss.scarf_cycle_starts = starts
    boss.scarf_cycle_no = cycle_no


def _scarf_phase_name(boss, local):
    """小队调度逻辑：按本循环的随机顺序和相对帧数决定当前主攻击者。"""
    durations = SCARF_SQUAD_PHASE_DURATIONS
    for name in boss.scarf_cycle_order:
        if local < boss.scarf_cycle_starts[name] + durations[name]:
            return name
    return boss.scarf_cycle_order[-1]


def _scarf_switch_job(boss, name, bullet_manager):
    """职业切换逻辑：点亮当前成员并熄灭其他成员。"""
    if not boss.scarf_squad:
        return
    target = None
    for member in boss.scarf_squad:
        member["active"] = (member["name"] == name)
        if member["name"] == name:
            target = member
    boss.scarf_active_squad = name
    if target is not None:
        _scarf_burst(bullet_manager, target["x"], target["y"], target["color"], count=8)


def _scarf_init_squad(boss, bullet_manager):
    """开符时建立固定小队，首轮随机顺序由第一帧调度生成。"""
    boss.scarf_squad = []
    for name in SCARF_SQUAD_ORDER:
        data = SCARF_SQUAD_MEMBERS[name]
        boss.scarf_squad.append({
            "name": name,
            "label": data["label"],
            "x": data["x"],
            "base_y": data["y"],
            "y": data["y"],
            "float_phase": data["float_phase"],
            "sprite": data["sprite"],
            "height": data["height"],
            "color": data["color"],
            "active": False,
        })
    boss.scarf_active_squad = None
    boss.scarf_cycle_no = -1
    boss.scarf_cycle_order = list(SCARF_SQUAD_ORDER)
    boss.scarf_cycle_starts = {name: 0 for name in SCARF_SQUAD_ORDER}
    boss.scarf_pending_order = None
    boss.scarf_buff_circles = []


def _scarf_update_buff_circles(boss):
    """多个强化法阵生命周期：持续到下一轮 Priest 接手前。"""
    circles = boss.scarf_buff_circles
    for circle in circles:
        circle["life"] -= 1
    boss.scarf_buff_circles = [c for c in circles if c["life"] > 0]


def _scarf_warrior_attack(boss, bullet_manager, phase):
    """Warrior：宽扇形压迫弹 + 周期性骨刺圆环。"""
    P = SCARF_SQUAD_SPELL["warrior"]
    x, y = _scarf_member_pos(boss, "warrior")
    base = _scarf_home_angle(x, y)

    # 扇形压迫弹：较宽的固定扇，周期性与骨刺弹错开。
    if phase > 0 and phase % P["fan_interval"] == 0:
        count = P["fan_count"]
        half = P["fan_half_angle"]
        for i in range(count):
            a = base - half + i * (2 * half / (count - 1))
            b = create_bullet_angle(x, y, a, P["fan_speed"],
                                    P["bullet_type"], radius=P["radius"],
                                    color=P["color"])
            _scarf_add(bullet_manager, boss, b)

    # 白色骨刺圆环：短促高密度扩散，强化 Warrior 的压迫感。
    if phase > 0 and phase % P["ring_interval"] == 0:
        rot = phase * 0.006
        for i in range(P["ring_count"]):
            a = rot + i * math.tau / P["ring_count"]
            b = create_bullet_angle(x, y, a, P["ring_speed"],
                                    P["bullet_type"], radius=P["radius"],
                                    color=P["color"])
            _scarf_add(bullet_manager, boss, b)


def _scarf_archer_attack(boss, bullet_manager, phase, player_x, player_y):
    """Archer：深绿色高速直线箭雨全部朝向玩家，左右两侧加宽后持续压制。"""
    P = SCARF_SQUAD_SPELL["archer"]
    x, y = _scarf_member_pos(boss, "archer")
    base = math.atan2(player_y - y, player_x - x)

    # 直线箭雨：从 Archer 位置快速瞄准玩家，左右对称展开七条箭道。
    if phase > 0 and phase % P["arrow_interval"] == 0:
        for offset in P["arrow_offsets"]:
            b = create_bullet_angle(x, y, base + offset,
                                    P["arrow_speed"], P["bullet_type"],
                                    radius=P["radius"], color=P["color"])
            _scarf_add(bullet_manager, boss, b)


def _scarf_mage_attack(boss, bullet_manager, phase, player_x, player_y):
    """Mage：青色灵魂火改为朝向玩家发射，并在左右各复制一组相同攻击。"""
    P = SCARF_SQUAD_SPELL["mage"]
    x, y = _scarf_member_pos(boss, "mage")
    base = math.atan2(player_y - y, player_x - x)
    aim_offsets = P["aim_offsets"]

    # 多线灵魂波浪弹：相位交替，慢速交错前进。
    if phase > 0 and phase % P["orb_interval"] == 0:
        for aim_offset in aim_offsets:
            for idx, offset in enumerate(P["orb_offsets"]):
                a = base + aim_offset + offset
                b = create_bullet_angle(x, y, a, P["orb_speed"],
                                        P["bullet_type"], radius=P["radius"],
                                        color=P["color"])
                b.wobble_amp = P["orb_wobble_amp"]
                b.wobble_freq = P["orb_wobble_freq"]
                b.wobble_phase = idx * (math.pi / max(1, len(P["orb_offsets"]) - 1))
                _scarf_add(bullet_manager, boss, b)

def _scarf_priest_attack(boss, bullet_manager, phase):
    """Priest：攻击强度不高；在场地中生成多个紫色小法阵，供下一位成员攻击穿过时分裂。"""
    P = SCARF_SQUAD_SPELL["priest"]
    data = SCARF_SQUAD_MEMBERS["priest"]

    # 职业回合开头生成/刷新多个小法阵（上一轮法阵会在此时被替换）。
    if phase == 0:
        boss.scarf_buff_circles = []
        order = boss.scarf_cycle_order
        priest_pos = order.index("priest")
        priest_start = boss.scarf_cycle_starts["priest"]
        durations = SCARF_SQUAD_PHASE_DURATIONS

        if priest_pos < len(order) - 1:
            next_name = order[priest_pos + 1]
            next_start = boss.scarf_cycle_starts[next_name]
            next_end = next_start + durations[next_name]
        else:
            # Priest 是本轮最后一位时，法阵需跨循环保留到下一轮首位成员攻击结束。
            if getattr(boss, "scarf_pending_order", None) is None:
                pending = list(SCARF_SQUAD_ORDER)
                random.shuffle(pending)
                boss.scarf_pending_order = pending
            next_name = boss.scarf_pending_order[0]
            next_end = SCARF_SQUAD_CYCLE_DURATION + durations[next_name]

        life = next_end - priest_start + 1
        for cx, cy in SCARF_SQUAD_SPELL["priest_circle_positions"]:
            boss.scarf_buff_circles.append({
                "x": cx,
                "y": cy,
                "radius": SCARF_SQUAD_SPELL["priest_circle_radius"],
                "life": life,
                "max_life": life,
            })
            _scarf_burst(bullet_manager, cx, cy, data["color"],
                         count=8, speed=1.4, radius=2.0, lifetime=24)
        return

    # 牧师自身的低频环形弹：仅维持存在感，不铺满全场。
    if phase % P["ring_interval"] == 0:
        x, y = _scarf_member_pos(boss, "priest")
        for i in range(P["ring_count"]):
            a = i * math.tau / P["ring_count"]
            b = create_bullet_angle(x, y, a, P["ring_speed"],
                                    P["bullet_type"], radius=P["radius"],
                                    color=P["color"])
            _scarf_add(bullet_manager, boss, b, empower=False)


def spell_scarf_necrotic_squad(boss, bullet_manager, timer, dt,
                               player_x=0, player_y=0):
    """队符「Necrotic Squad」：四名亡灵固定在场，每轮随机洗牌后轮流主攻。

    每轮四名成员各出场一次；仅一名成员在当前回合主攻。
    Priest 生成多个小强化法阵，下一位成员攻击穿过法阵时会分裂；原弹不加速。
    Archer 使用朝向玩家的高速箭；其余成员保持固定角度/对称/阵列谱。
    """
    P = SCARF_SQUAD_SPELL

    # 开符第一帧：建立固定小队；随机顺序将在下一帧生成本轮调度。
    if timer == 1:
        _scarf_init_squad(boss, bullet_manager)
        return

    # Scarf 本体居中悬浮，不主动走位。
    boss.target_y = 120 + math.sin(timer * 0.008) * 4

    # 先更新小队成员的空中飘浮位置，再让本帧弹幕从当前位置生成。
    _scarf_update_squad_float(boss, timer)

    # 单循环调度：先确认当前轮次，进入新轮次时随机洗牌一次。
    cycle_no = (timer - 1) // P["cycle_duration"]
    if getattr(boss, "scarf_cycle_no", -1) != cycle_no:
        _scarf_begin_cycle(boss, cycle_no)

    # timer 映射到 0..cycle_duration-1 的相对帧。
    local = (timer - 1) % P["cycle_duration"]
    name = _scarf_phase_name(boss, local)

    # 职业切换：进入新职业帧时点亮对应成员。
    if name != boss.scarf_active_squad:
        _scarf_switch_job(boss, name, bullet_manager)

    phase = local - boss.scarf_cycle_starts[name]

    if name == "warrior":
        _scarf_warrior_attack(boss, bullet_manager, phase)
    elif name == "archer":
        _scarf_archer_attack(boss, bullet_manager, phase, player_x, player_y)
    elif name == "mage":
        _scarf_mage_attack(boss, bullet_manager, phase, player_x, player_y)
    else:
        _scarf_priest_attack(boss, bullet_manager, phase)

    # 强化法阵生命周期推进（下一轮 Priest 会重新生成）。
    _scarf_update_buff_circles(boss)


# ---------------------------------------------------------------------------
# 四面关卡
# ---------------------------------------------------------------------------

class Stage4_Catacombs(Stage):
    """Stage 4: The Catacombs - 地下墓穴深处"""

    def __init__(self):
        super().__init__(4, "地下墓穴深处 ~ The Catacombs",
                         bg_color=(7, 7, 12))
        self.background = Pseudo3DFloor(
            cfg.STAGE4_FLOOR, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT,
            bg_color=self.bg_color,
            wall_texture_path=cfg.STAGE4_WALL,
            horizon_ratio=0.36, tunnel_width=1.8,
            far_opening=34, floor_stretch=3.2, wall_stretch=1.0,
            wall_align_to_floor=True)
        self.title_path = cfg.STAGE4_TITLE
        self.music_path = cfg.STAGE4_MUSIC_START
        self.music_loop_path = cfg.STAGE4_MUSIC_LOOP
        self.boss_music_start_path = cfg.STAGE4_BOSS_MUSIC_START
        self.boss_music_loop_path = cfg.STAGE4_BOSS_MUSIC_LOOP
        self.music_name = cfg.STAGE4_MUSIC_NAME
        self.boss_music_name = cfg.STAGE4_BOSS_MUSIC_NAME
        self.mid_boss_music_path = None
        self.background_darkness = 145

        self.defeat_dialogue_lines = [
            ("Sadan", "看来，我的忠告并没有什么作用。"),
            ("魔法使 Mage", "所以，地下城深处究竟隐藏着什么？"),
            ("Sadan", "一个漫长的故事。"),
            ("魔法使 Mage", "听起来，你并不准备解释。"),
            ("Sadan", "有些答案，只有亲眼见到才能理解。"),
            ("魔法使 Mage", "看来，我只能继续前进了。"),
            ("Sadan", "那么，去吧。"),
            ("Sadan", "不过，从这里开始，等待你的将不再是守卫者。"),
            ("魔法使 Mage", "什么意思？"),
            ("Sadan", "你很快就会知道。"),
        ]
        self.defeat_dialogue_portraits = {
            "魔法使 Mage": cfg.SELF_SPRITE,
            "Sadan": cfg.SADAN_BOSS_SPRITE,
        }
        self.defeat_dialogue_portrait_sides = {
            "魔法使 Mage": "left",
        }

    def setup_waves(self):
        """四面小怪：刻意打乱前三面“每 5 秒一波”的节奏。

        这里使用侧向横穿的幽魂、原地交替射击的骷髅狙击手、
        长队列食尸鬼与墓穴唤魂者混编，让波次间距和威胁方向都不再固定。
        """
        w = cfg.BATTLE_AREA_WIDTH

        self.enemy_manager.add_timed_wave(0, EnemyWave([
            _undead(90, -20, "descend"),
            _undead(w - 90, -20, "descend"),
        ], name="Crypt Gate"))

        self.enemy_manager.add_timed_wave(2 * 60, EnemyWave([
            CryptWraithEnemy(-32, 118, direction=1),
            CryptWraithEnemy(w + 32, 178, direction=-1),
        ], name="Ghost Cross"))

        self.enemy_manager.add_timed_wave(6 * 60, EnemyWave(
            _undead_chain(w * 0.30), name="Rotting Procession"))

        self.enemy_manager.add_timed_wave(10 * 60, EnemyWave([
            _skeleton(w / 2, 96),
            BoneSniperEnemy(96, 132),
            BoneSniperEnemy(w - 96, 152),
        ], name="Bone Watch"))

        self.enemy_manager.add_timed_wave(14 * 60, EnemyWave([
            CryptWraithEnemy(-28, 128, direction=1),
            _caster(w * 0.72, -30, deploy_y=170),
        ], name="Tomb Ambush"))

        self.enemy_manager.add_timed_wave(18 * 60, EnemyWave([
            _undead(86, -20, "descend"),
            _soul(w / 2, -30, "strafe"),
            _undead(w - 86, -20, "descend"),
        ], name="Corpse Pincer"))

        self.enemy_manager.add_timed_wave(22 * 60, EnemyWave(
            _undead_chain(w * 0.68, count=8, spacing=38),
            name="Scarf's Line"))

        self.enemy_manager.add_timed_wave(26 * 60, EnemyWave([
            _skeleton(w * 0.35, 90),
            _skeleton(w * 0.65, 110),
            _undead(w / 2, -30, "descend"),
        ], name="Twin Reliquaries"))

        self.enemy_manager.add_timed_wave(30 * 60, EnemyWave([
            _caster(100, -30, deploy_y=164),
            _caster(w - 100, -30, deploy_y=172),
        ], name="Necromancer Duet"))

        self.enemy_manager.add_timed_wave(34 * 60, EnemyWave([
            _soul(110, -30, "strafe"),
            BoneSniperEnemy(140, 126),
            BoneSniperEnemy(w - 140, 144),
            _soul(w - 110, -30, "strafe"),
        ], name="Haunted Firing Line"))

        self.enemy_manager.add_timed_wave(38 * 60, EnemyWave([
            CryptWraithEnemy(-30, 140, direction=1),
            CryptWraithEnemy(w + 30, 200, direction=-1),
            _caster(w / 2, -34, deploy_y=166),
        ], name="Catacomb Ambush"))

        self.enemy_manager.add_timed_wave(42 * 60, EnemyWave([
            _undead(80, -24, "descend"),
            _soul(w / 2, -36, "strafe"),
            _skeleton(w * 0.38, 92),
            _caster(w - 100, -30, deploy_y=168),
            _undead(w - 80, -24, "descend"),
        ], name="Scarf's Vanguard"))

    def update(self, dt, bullet_manager, player_x, player_y):
        super().update(dt, bullet_manager, player_x, player_y)
        for enemy in self.enemy_manager.active_enemies:
            if isinstance(enemy, SkeletorEnemy) and enemy.burst_pending:
                enemy.emit_death_burst(bullet_manager)

    def setup_mid_boss(self):
        """47s 出场的道中Boss：Scarf。

        非符阶段用专属弹幕表现“亡灵随从 + 骷髅弹幕”的学徒死灵术士；
        血量过半后展开唯一符卡「队符「Necrotic Squad」」，由四名亡灵小队轮番主攻。
        """
        self.mid_boss = Boss(
            "Scarf", hp=SCARF_MAX_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-40,
            size=24, color=(150, 70, 220),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_min_duration=180,
            non_spell_func=_non_spell_scarf,
            hp_bar_inset=16,
            sprite_path=cfg.SCARF_BOSS_SPRITE,
            sprite_scale=2.4)
        self.mid_boss.bonus_drops = ["overflux_power_orb", "revive_stone"]
        self.mid_boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 108)
        self.mid_boss.add_spell_card(SpellCard(
            "队符「Necrotic Squad」", spell_scarf_necrotic_squad,
            hp_threshold=0.5, bg_style="scarf"))

    def _add_post_midboss_waves(self):
        """Scarf 击破后，用侧向穿插与短队列继续推进到关底对话。"""
        w = cfg.BATTLE_AREA_WIDTH
        base = self.mid_boss_defeated_at
        plans = [
            (60, [
                CryptWraithEnemy(-30, 130, direction=1),
                CryptWraithEnemy(w + 30, 185, direction=-1),
            ], "Scattered Souls"),
            (150, [
                _undead(80, -24, "descend"),
                _undead(w / 2, -42, "descend"),
                _undead(w - 80, -24, "descend"),
            ], "Grave Scavengers"),
            (210, [
                SkeletorEnemy(w * 0.30, -30),
                SkeletorEnemy(w * 0.70, -46),
            ], "Skeletor Awakening"),
            (260, [
                _soul(110, -30, "strafe"),
                _soul(w - 110, -30, "strafe"),
                _caster(w * 0.75, -30, deploy_y=170),
            ], "Crypt Echoes"),
            (360, _undead_chain(w * 0.70, count=7, spacing=36),
             "Final Procession"),
            (470, [
                _undead(90, -24, "descend"),
                _soul(w / 2, -34, "strafe"),
                _caster(w * 0.30, -30, deploy_y=160),
                _caster(w * 0.70, -30, deploy_y=168),
                _undead(w - 90, -24, "descend"),
            ], "Necromancer Rearguard"),
        ]
        for offset, enemies, name in plans:
            wave = EnemyWave(enemies, name=name)
            self.post_waves.append(wave)
            self.enemy_manager.add_timed_wave(base + offset, wave)

    def _on_boss_combat_start(self):
        """Sadan 开战：视角逐渐抬升，营造大殿中的压迫感。"""
        if self.background is not None:
            self.background.ramp_view_height(118.0, 2.6)

    def get_active_enemies(self):
        """During Precursors' Return only the current giant is targetable.

        Sadan himself is removed from the target list so player shots and bombs
        cannot damage him directly; killing each giant applies its 1/4 spell HP
        damage through the giant hitbox proxy.
        """
        boss = getattr(self, "boss", None)
        if (boss is not None and boss.alive and boss.combat_enabled
                and boss.phase == "spell"
                and boss.current_spell is not None
                and boss.current_spell.name == "巨符「Precursors' Return」"):
            state = getattr(boss, "sadan_giant_state", None)
            if state:
                giant = state.get("giant")
                if (giant is not None and giant.get("alive")
                        and giant.get("phase") in ("entering", "attack")):
                    return [giant["proxy"]]
            return []
        return super().get_active_enemies()

    def skip_to_precursors_return(self):
        """G key during Sadan's pre-battle dialogue: jump straight to the
        second spell card, Giant Sign "Precursors' Return".
        """
        if self.phase != "dialogue" or self.dialogue_is_defeat:
            return False

        boss = self.boss
        if boss is None or len(boss.spell_cards) < 2:
            return False

        # Reuse the normal dialogue-end transition (boss phase, music hook and
        # background camera ramp), then override the non-spell wait below.
        self.on_dialogue_end()

        boss.arm_combat(0)
        boss.entering = False
        boss.entry_timer = 0
        target_idx = 1
        card = boss.spell_cards[target_idx]
        boss.current_spell_idx = target_idx
        boss.hp = boss.max_hp * card.hp_threshold
        boss._start_spell(card)
        return True

    def skip_to_bridge_between_worlds(self):
        """H key during Sadan's pre-battle dialogue: jump straight to the
        final spell, Divine Age "Bridge Between Worlds".
        """
        if self.phase != "dialogue" or self.dialogue_is_defeat:
            return False

        boss = self.boss
        if boss is None or boss.last_spell is None:
            return False

        # Reuse the normal dialogue-end transition (boss phase, music hook and
        # background camera ramp), then immediately open the Last Spell.
        self.on_dialogue_end()

        boss.arm_combat(0)
        boss.entering = False
        boss.entry_timer = 0
        boss.current_spell_idx = len(boss.spell_cards)
        boss._start_spell(boss.last_spell)
        return True

    def setup_boss(self):
        """关底Boss：Sadan。

        三张通常符与一张 Last Spell 已初始化，弹幕后续填充。
        """
        self.boss = Boss(
            "Sadan", hp=SADAN_MAX_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
            size=26, color=(190, 90, 50),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_level=2, non_spell_min_duration=240,
            non_spell_func=_non_spell_sadan,
            hp_bar_inset=16,
            sprite_path=cfg.SADAN_BOSS_SPRITE,
            sprite_scale=1.82)
        self.boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 106)
        self.boss.add_spell_card(SpellCard(
            "兵符「Terracotta Army」", spell_sadan_terracotta_army,
            hp_threshold=31500 / SADAN_MAX_HP,
            end_hp_threshold=26250 / SADAN_MAX_HP,
            bg_style="sadan"))
        self.boss.add_spell_card(SpellCard(
            "巨符「Precursors' Return」", spell_sadan_precursors_return,
            hp_threshold=18000 / SADAN_MAX_HP,
            end_hp_threshold=12000 / SADAN_MAX_HP,
            bg_style="stone"))
        self.boss.add_spell_card(SpellCard(
            "王符「The Giant One」", spell_sadan_the_giant_one,
            hp_threshold=9000 / SADAN_MAX_HP,
            end_hp_threshold=4500 / SADAN_MAX_HP,
            bg_style="stone"))
        self.boss.set_last_spell(SpellCard(
            "终符神代「Bridge Between Worlds」", spell_sadan_bridge_between_worlds,
            hp_threshold=0, bg_style="sadan", time_spell=True))

    def draw_foreground(self, screen, offset_x=0, offset_y=0):
        """终符前景遮罩：从战斗区底部向上吞噬的渐变黑暗。

        该层绘制在子弹与自机之上，因此自机进入黑暗后会看不见自身；
        它只是视觉遮挡，没有碰撞判定，伤害仍只来自场上弹幕。
        """
        boss = getattr(self, "boss", None)
        if boss is None or not boss.alive:
            return
        state = getattr(boss, "bridge_worlds_state", None)
        if not state:
            return
        front = state.get("darkness_front")
        if front is None:
            return

        height = cfg.BATTLE_AREA_HEIGHT
        width = cfg.BATTLE_AREA_WIDTH
        top = int(round(max(0.0, min(float(height), float(front)))))
        if top >= height:
            return

        overlay = pygame.Surface((width, height), pygame.SRCALPHA)
        span = max(1.0, float(height - top))
        for y in range(top, height):
            t = (y - top) / span
            alpha = int(255 * min(1.0, 0.18 + t * 1.35))
            pygame.draw.line(overlay, (0, 0, 3, alpha), (0, y), (width, y))
        screen.blit(overlay, (offset_x, offset_y))

    def _start_dialogue(self):
        """关底对话：自机 Mage 与 Sadan 战前对峙（自机立绘在左侧）。"""
        self.dialogue_lines = [
            ("Sadan", "能来到这里，说明你已经击败了前面的那些家伙。"),
            ("魔法使 Mage", "看来，你知道我为什么会来到这里。"),
            ("Sadan", "最近的地下城，确实有些不同。"),
            ("魔法使 Mage", "终于有人愿意承认这一点了。"),
            ("Sadan", "但我劝你不要继续前进。"),
            ("魔法使 Mage", "为什么？"),
            ("Sadan", "因为有些事情，并不值得被重新唤醒。"),
            ("魔法使 Mage", "那我更应该亲眼确认。"),
            ("Sadan", "既然如此，就先证明你有继续前进的资格吧。"),
        ]
        self.dialogue_portraits = {
            "魔法使 Mage": cfg.SELF_SPRITE,
            "Sadan": cfg.SADAN_BOSS_SPRITE,
        }
        self.dialogue_portrait_sides = {
            "魔法使 Mage": "left",
        }
        self.setup_boss()
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)
        if self.boss:
            self.boss.hold_combat()
        self.dialogue_is_defeat = False
        self.dialogue_active = True
        self.phase = "dialogue"
