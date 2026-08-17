# -*- coding: utf-8 -*-
# 五面：凋零之厅 ~ The Wither Lords（BOSS RUSH）
# 开场 The Watcher 对话并释放一张符卡；退下后召唤 The Professor / Thorn / Livid。
# 三名前置 Boss 各有一个非符和一张符卡。Livid 被击败后进入 Wither Lords 连战：
# Maxor（1 符）、Storm（1 符）、Goldor（2 符：机械符 / Phase3）、Necron（2 符，无 Last Spell）。
# 击败 Necron 后进入战后对话并结算五面。

import math
import os
import random

import pygame

from src.engine import settings as cfg
from src.engine.collision import point_segment_distance
from src.engine.pseudo3d import Pseudo3DFloor
from src.entities.boss import Boss, SpellCard
from src.entities.bullet import Bullet, create_bullet_angle, create_bullet_aimed
from src.entities.enemy import Enemy
from src.stages.stage1 import (
    Stage,
    BOSS_BG_RAMP_TIME,
    BOSS_COMBAT_DELAY,
    FINAL_BOSS_BG_SPEED_MULT,
)

# 复用三面 The Watcher 的展符弹幕，保持视觉语言一致。
from src.stages.stage3 import spell_watcher_undead_exhibition

# Goldor 第一张符卡「Terminal Pursuit」：方形环路终端破解 + 追击
from src.stages.goldor_terminal import (
    spell_goldor_terminal_pursuit,
    _gt_draw_foreground,
    _gt_clamp_player,
)

# Goldor 第二张符卡「Phase3 Infinite Rage」：旋转剑盾 + 剑隙骷髅
from src.stages.goldor_rage import (
    spell_goldor_infinite_rage,
    draw_goldor_rage,
)


# ---------------------------------------------------------------------------
# 五面 Boss 血量（BOSS RUSH，总量适中，逐个击破后立即接续）
# ---------------------------------------------------------------------------
WATCHER_HP = 5200
PROFESSOR_HP = 5600
THORN_HP = 6000
LIVID_HP = 6400
MAXOR_HP = 7600
STORM_HP = 8200
# Storm 符卡「Giga Lightning」：4 根方形避雷柱 / 阶段节奏 / 狂暴倍率
STORM_GIGA_PILLAR_POSITIONS = ((152, 250), (424, 250), (152, 430), (424, 430))
STORM_GIGA_PILLAR_SAFE_RADIUS = 34      # 柱子下方避雷安全区半径（px）
STORM_GIGA_NORMAL_DURATION = 480        # 普通雷击阶段时长（帧，约 8 秒）
STORM_GIGA_CHARGE_DURATION = 240        # Giga Lightning 蓄力倒计时（帧，约 4 秒）
STORM_GIGA_PILLAR_DESTROY_AT = 150      # 蓄力中 Storm 破坏玩家上次避雷柱的时刻
STORM_GIGA_PILLAR_FLASH = 26            # 柱子被破坏的电光闪光帧数
STORM_GIGA_STRIKE_DURATION = 36         # 全屏毁灭性雷击表现时长（帧）
STORM_GIGA_FRENZY_DAMAGE_MULT = 4.0    # 狂暴状态受伤倍率（相对普通符卡伤害）
GOLDOR_HP = 6000   # Goldor 总血量 = 原 2/3（Phase3 打空整条即击破，符卡伤害量与之前一致）
NECRON_HP = 10000


# Professor 实验符卡专用小 guardian 贴图。
_PROFESSOR_GUARDIAN_SPRITE = os.path.join(
    cfg.SPRITES_DIR, "enemies", "stage5", "professor", "Guardian.png")
_PROFESSOR_ELDER_GUARDIAN_SPRITE = os.path.join(
    cfg.SPRITES_DIR, "enemies", "stage5", "professor", "Elder_Guardian.png")
_PROFESSOR_GUARDIAN_HEIGHT = 42
_PROFESSOR_ELDER_GUARDIAN_HEIGHT = 84


def _add(bullet_manager, bullet):
    bullet_manager.add_enemy_bullet(bullet)


def _clamp_x(x, margin=52):
    return max(margin, min(cfg.BATTLE_AREA_WIDTH - margin, x))


def _clamp_y(y, low=78, high=250):
    return max(low, min(high, y))


def _clamp_guardian_y(y):
    return max(128, min(cfg.BATTLE_AREA_HEIGHT - 70, y))


def _prof_init_guardians(boss):
    """初始化实验符卡：一个漂浮巨型守卫者 + 三只可被击破的小 guardian。"""
    boss.professor_giant = Enemy(
        boss.x, boss.y - 78,
        hp=999999, score=0, size=17, color=(130, 235, 205),
        sprite_paths=[_PROFESSOR_ELDER_GUARDIAN_SPRITE],
        sprite_height=_PROFESSOR_ELDER_GUARDIAN_HEIGHT)
    boss.professor_giant.entry_done = True
    boss.professor_giant.age = 0

    boss.professor_guardians = []
    for i in range(3):
        guardian = Enemy(
            cfg.BATTLE_AREA_WIDTH / 2, 210,
            hp=520, score=1800, size=12, color=(80, 225, 185),
            sprite_paths=[_PROFESSOR_GUARDIAN_SPRITE],
            sprite_height=_PROFESSOR_GUARDIAN_HEIGHT)
        guardian.entry_done = True
        guardian.age = 0
        guardian.base_x = 150 + i * 210
        guardian.base_y = 205 + i * 14
        guardian.phase = i * 2.1
        guardian.fire_phase = i * 23
        boss.professor_guardians.append(guardian)

    boss.professor_lightning_wave = []
    boss.professor_lightning_warnings = []
    boss.professor_lightning_cycle = -1


def _prof_scale_burst(bullet_manager, x, y, count, base_angle, half_spread=0.92,
                      speed_min=1.5, speed_max=2.55):
    """从守卫者位置喷出一片青蓝色鳞弹。"""
    for i in range(count):
        if count <= 1:
            angle = base_angle
        else:
            angle = base_angle + (i - (count - 1) / 2.0) * (half_spread * 2.0 / (count - 1))
        speed = random.uniform(speed_min, speed_max)
        color = (90, 235, 220) if i % 2 == 0 else (70, 210, 245)
        bullet = create_bullet_angle(x, y, angle, speed,
                                     Bullet.TYPE_RICE, radius=2.5, color=color)
        bullet.sprite_slot = "g01_00"   # etama.png 第二行：麟弹
        _add(bullet_manager, bullet)


def _prof_lightning_warning(boss, x):
    """登记一条纵向落雷预警：由 Stage5.draw 以半透明虚线绘制，不进入弹幕判定。"""
    boss.professor_lightning_warnings.append({
        "x": x,
        "age": 0,
        "max_age": 74,
    })


def _prof_lightning_strike(bullet_manager, x):
    """实际落雷：短暂纵向判定光束，并在底部迸出两发侧向鳞弹。"""
    top = 12.0
    bottom = cfg.BATTLE_AREA_HEIGHT - 8.0
    length = bottom - top
    beam = create_bullet_angle(x, top, math.pi / 2, 0.0,
                               Bullet.TYPE_BEAM, radius=3.0,
                               color=(125, 235, 255))
    beam.manager = bullet_manager
    beam.angle = math.pi / 2
    beam.beam_length = length
    beam.sprite_slot = "s12"
    beam.lifetime = 15
    bullet_manager.add_enemy_bullet(beam)

    for offset in (-0.42, 0.42):
        _add(bullet_manager,
             create_bullet_angle(x, bottom, math.pi / 2 + offset, 2.0,
                                 Bullet.TYPE_RICE, radius=2.5,
                                 color=(90, 225, 245)))


# ---------------------------------------------------------------------------
# 前置 Boss 专属非符
# ---------------------------------------------------------------------------

def _non_spell_professor(boss, bullet_manager, timer, player_x, player_y):
    """Professor：缓步左右巡游，周期性投出追踪弹与环形护身弹。"""
    if timer % 90 == 0:
        boss.move_to(_clamp_x(cfg.BATTLE_AREA_WIDTH / 2 + math.sin(timer * 0.013) * 170),
                     _clamp_y(112 + math.sin(timer * 0.021) * 12))
    if timer % 26 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for offset in (-0.22, 0.0, 0.22):
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, base + offset, 2.7,
                                     Bullet.TYPE_CIRCLE, radius=3, color=(150, 230, 120)))
    if timer % 52 == 0:
        for i in range(12):
            angle = timer * 0.035 + i * math.tau / 12
            bullet = create_bullet_angle(boss.x, boss.y, angle, 1.7,
                                         Bullet.TYPE_RICE, radius=2.5,
                                         color=(120, 220, 160))
            bullet.sprite_slot = "g01_00"   # etama.png 第二行：麟弹
            _add(bullet_manager, bullet)


def _non_spell_thorn(boss, bullet_manager, timer, player_x, player_y):
    """Thorn：高频扇形刺弹与斜向针弹交替压制。"""
    if timer % 44 == 0:
        boss.move_to(_clamp_x(cfg.BATTLE_AREA_WIDTH / 2 - math.sin(timer * 0.017) * 150),
                     _clamp_y(106 + math.cos(timer * 0.023) * 14))
    base = math.atan2(player_y - boss.y, player_x - boss.x)
    if timer % 17 == 0:
        for i in range(5):
            offset = (i - 2) * 0.14
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, base + offset, 2.9,
                                     Bullet.TYPE_KNIFE, radius=2.5, color=(190, 110, 255)))
    if timer % 31 == 0:
        for sign in (-1, 1):
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, math.pi / 2 + sign * 0.65, 2.4,
                                     Bullet.TYPE_ARROW, radius=3, color=(160, 80, 240)))


def _non_spell_livid(boss, bullet_manager, timer, player_x, player_y):
    """Livid：短距瞬移后立即释放一圈刀弹，再补一组自机狙。"""
    if timer % 62 == 0:
        boss.x = _clamp_x(random.uniform(110, cfg.BATTLE_AREA_WIDTH - 110))
        boss.y = _clamp_y(random.uniform(95, 185))
        boss.move_to(boss.x, boss.y)
        for i in range(18):
            angle = i * math.tau / 18 + timer * 0.02
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, angle, 2.0,
                                     Bullet.TYPE_KNIFE, radius=2.5, color=(80, 210, 240)))
    if timer % 20 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for offset in (-0.10, 0.10):
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, base + offset, 3.0,
                                     Bullet.TYPE_CIRCLE, radius=3, color=(70, 200, 230)))


# ---------------------------------------------------------------------------
# 五面符卡弹幕（每名 Wither Lord 使用不同风格）
# ---------------------------------------------------------------------------

def spell_professor_guardian_array(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """守符「Professor's Guardian Array」：绿色护符阵列从两侧回旋推进。"""
    if timer % 120 == 0:
        boss.move_to(_clamp_x(random.uniform(150, cfg.BATTLE_AREA_WIDTH - 150)), 104)
    if timer % 24 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for offset in (-0.28, 0.0, 0.28):
            _add(bullet_manager,
                 create_bullet_aimed(boss.x, boss.y, player_x, player_y, 2.8,
                                     Bullet.TYPE_CIRCLE, radius=3, color=(150, 230, 120)))
    if timer % 58 == 0:
        for side in (-1, 1):
            sx = boss.x + side * 120
            sy = 30 + (timer % 180) * 0.35
            for i in range(7):
                angle = math.pi / 2 + side * (0.15 + i * 0.11)
                _add(bullet_manager,
                     create_bullet_angle(sx, sy, angle, 2.2,
                                         Bullet.TYPE_RICE, radius=2.5, color=(110, 220, 140)))
    if timer % 45 == 0:
        for i in range(10):
            angle = -timer * 0.025 + i * math.tau / 10
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, angle, 1.7,
                                     Bullet.TYPE_CIRCLE, radius=3, color=(180, 255, 180)))


def spell_professor_experiment(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """实验「Professor's Experiment」：

    巨大守卫者漂浮在 Professor 上方，持续喷出青色鳞弹；同时每隔一段时间
    在场地内随机 x 位置召唤 5 条纵向落雷。落雷前会先出现淡青色预警线。
    此外 Professor 还会放出三只可被击破的小 guardian 游走并发射自机狙。
    """
    if getattr(boss, "professor_giant", None) is None:
        _prof_init_guardians(boss)

    giant = boss.professor_giant
    guardians = boss.professor_guardians

    # 本体轻度左右巡游，压低高度，给上方 giant 与落雷留出空间。
    if timer % 100 == 0:
        boss.move_to(_clamp_x(random.uniform(180, cfg.BATTLE_AREA_WIDTH - 180)), 128)

    # 巨大守卫者：跟随本体水平位置，漂浮在头顶并缓慢上下起伏。
    giant.age += 1
    giant.x += (boss.x - giant.x) * min(1.0, dt * 7.0)
    giant.x = _clamp_x(giant.x, 70)
    giant.y = boss.y - 76 + math.sin(timer * 0.055) * 9
    giant.y = max(38, min(220, giant.y))

    # 巨大守卫者鳞弹：高频散射，青色为主。
    if timer >= 28 and timer % 17 == 0:
        count = 14 + (timer // 210) % 3
        _prof_scale_burst(bullet_manager, giant.x, giant.y, count, math.pi / 2,
                          half_spread=1.02, speed_min=1.45, speed_max=2.5)
    if timer >= 30 and timer % 43 == 0:
        for i in range(11):
            angle = -timer * 0.037 + i * math.tau / 11
            _add(bullet_manager,
                 create_bullet_angle(giant.x, giant.y, angle, 1.55,
                                     Bullet.TYPE_CIRCLE, radius=2.5,
                                     color=(70, 225, 235)))

    # 小 guardian：游走 + 周期自机狙，且保留血量可被击破。
    for guardian in guardians:
        if not guardian.alive:
            continue
        guardian.age += 1
        guardian.x = guardian.base_x + math.sin((timer + guardian.phase * 11) * 0.021) * 88
        guardian.y = _clamp_guardian_y(
            guardian.base_y + math.sin((timer + guardian.phase * 17) * 0.033) * 24)
        guardian.x = _clamp_x(guardian.x, 42)
        if timer >= 45 and (timer + guardian.fire_phase) % 71 == 0:
            base = math.atan2(player_y - guardian.y, player_x - guardian.x)
            for offset in (-0.12, 0.12):
                _add(bullet_manager,
                     create_bullet_angle(guardian.x, guardian.y, base + offset, 2.35,
                                         Bullet.TYPE_CIRCLE, radius=2.5,
                                         color=(115, 235, 200)))

    # 5 条纵向落雷：先预警，再短暂判定光束。
    for warning in boss.professor_lightning_warnings:
        warning["age"] += 1
    boss.professor_lightning_warnings = [
        w for w in boss.professor_lightning_warnings
        if w["age"] < w["max_age"]
    ]
    if timer < 34:
        cycle = -1
    else:
        cycle = (timer - 34) % 170
    if cycle == 0:
        # 5 条雷柱：在五条随机 x 车道上生成，避免挤在一起。
        lanes = [90, 215, 340, 465, 590]
        positions = []
        for lane in lanes:
            x = _clamp_x(lane + random.uniform(-38, 38), 38)
            positions.append(x)
        boss.professor_lightning_wave = positions
        boss.professor_lightning_cycle = cycle
        for x in positions:
            _prof_lightning_warning(boss, x)
    elif cycle == 74:
        for x in boss.professor_lightning_wave:
            _prof_lightning_strike(bullet_manager, x)
        boss.professor_lightning_wave = []
        boss.professor_lightning_cycle = cycle




# ---------------------------------------------------------------------------
# 灵符「Spirit Zoo」：Thorn 的 Spirit Animals 展示符卡
# ---------------------------------------------------------------------------
_THORN_SPIRIT_DIR = os.path.join(cfg.SPRITES_DIR, "enemies", "stage5", "thorn")
_SPIRIT_CHICKEN_SPRITE = os.path.join(_THORN_SPIRIT_DIR, "Chicken_(Temperate).png")
_SPIRIT_RABBIT_SPRITE = os.path.join(_THORN_SPIRIT_DIR, "Rabbit.gif")
_SPIRIT_SHEEP_SPRITE = os.path.join(_THORN_SPIRIT_DIR, "Sheep_(White).png")
_SPIRIT_WOLF_SPRITE = os.path.join(_THORN_SPIRIT_DIR, "Wolf.png")
_SPIRIT_BAT_SPRITE = os.path.join(_THORN_SPIRIT_DIR, "Bat.gif")
_SPIRIT_BEAR_SPRITE = os.path.join(_THORN_SPIRIT_DIR, "Spirit_Bear.png")
_SPIRIT_BOW_SPRITE = os.path.join(_THORN_SPIRIT_DIR, "Spirit_Bow.png")
_SPIRIT_ARROW_SPRITE = os.path.join(_THORN_SPIRIT_DIR, "arrow.png")

# 所有可调参数集中在这里。Spirit Zoo 不是轮流发射，而是让五种动物以各自的
# 固定行为同时存在于场上：Chicken 造雷、Rabbit 冲线、Sheep 接近爆炸、
# Wolf 巡逻切路、Bat 在上方压高度。Mine 会成为多条行为线的交汇点。
_SPIRIT_ZOO = {
    # 总节奏：前段理解行为，中段 2~3 种并存，后段多种并存并由 Bear 收尾。
    "duration": 1480,
    "ramp1": 420,
    "ramp2": 820,
    "max_total": 32,
    "bear_time": 1140,
    "bear_aim_frames": 78,
    "bear_end_delay": 46,

    "chicken": {
        "max": 4, "max_mid": 8, "max_late": 8,
        "first_spawn": 30, "interval": 300, "life": 660,
        "speed": 0.95,
        "x_amp": 84, "x_freq": 0.019,
        "first_mine": 64, "mine_every": 82,
        "lanes": (88, 176, 264, 352, 440, 528),
    },
    "mine": {
        "max": 8,
        "warn": 38,
        "armed_life": 470,
        "player_trigger_radius": 24.0,
        "player_fuse": 34,
        "animal_fuse": 7,
        "fragment_count": 7,
        "fragment_speed_min": 1.35,
        "fragment_speed_max": 2.10,
    },
    "rabbit": {
        "max": 2, "max_mid": 2, "max_late": 4,
        "first_spawn": 300, "interval": 520, "life": 1240,
        "lanes": (190, 275, 360, 450),
        "rest_frames": 46,
        "telegraph_frames": 38,
        "dash_frames": 16,
        "pause_frames": 42,
        "trigger_radius": 30,
    },
    "sheep": {
        "max": 0, "max_mid": 2, "max_late": 4,
        "first_spawn": 430, "interval": 500,
        "speed": 0.72,
        "turn_speed": 0.017,
        "retarget_interval": 48,
        "explode_distance": 96,
        "warn_frames": 62,
        "radial_count": 16,
        "radial_speed": 1.85,
        "explosion_radius": 92,
    },
    "wolf": {
        "max": 0, "max_mid": 4, "max_late": 8,
        "first_spawn": 540, "interval": 480, "life": 1150,
        "speed": 0.82,
        "fire_interval": 88,
        "fire_count": 3,
        "fire_speed": 1.75,
        "fire_spread": 0.28,
        "trigger_radius": 28,
    },
    "bat": {
        "max": 4, "max_mid": 4, "max_late": 8,
        "first_spawn": 55, "interval": 620, "life": 1320,
        "y_base": 52,
        "x_min": 110, "x_max": 466,
        "speed": 0.65,
        "bob_amp": 10,
        "bob_speed": 0.021,
        "fire_interval": 104,
        "row_count": 5,
        "row_spread": 17,
        "bullet_speed": 1.38,
        "visual_count": 7,
        "visual_spread": 21,
    },
}

_SPIRIT_KINDS = ("chicken", "bat", "rabbit", "sheep", "wolf")
_SPIRIT_SPRITE_PATHS = {
    "chicken": _SPIRIT_CHICKEN_SPRITE,
    "rabbit": _SPIRIT_RABBIT_SPRITE,
    "sheep": _SPIRIT_SHEEP_SPRITE,
    "wolf": _SPIRIT_WOLF_SPRITE,
    "bat": _SPIRIT_BAT_SPRITE,
    "bear": _SPIRIT_BEAR_SPRITE,
    "bow": _SPIRIT_BOW_SPRITE,
}


def _spirit_zoo_max_for(kind, timer):
    """返回某动物在当前符卡阶段的场上数量上限。"""
    spec = _SPIRIT_ZOO[kind]
    if timer >= _SPIRIT_ZOO["ramp2"]:
        return spec.get("max_late", spec["max"])
    if timer >= _SPIRIT_ZOO["ramp1"]:
        return spec.get("max_mid", spec["max"])
    return spec["max"]


def _spirit_zoo_init(boss):
    """Spirit Zoo 的全部战斗状态都挂在 boss 上，避免另建弹幕框架。"""
    boss.spirit_zoo = {
        "animals": [],
        "mines": [],
        "fx": [],
        "bear": None,
        "last_spawn": {kind: -999 for kind in _SPIRIT_KINDS},
        "rabbit_lane": 0,
        "ending": False,
        "ended": False,
    }


def _spirit_zoo_count_active(state, kind):
    return sum(1 for a in state["animals"]
               if a.get("alive", True) and a.get("kind") == kind)


def _spirit_zoo_add_fx(state, x, y, color, radius=16, max_age=18):
    state["fx"].append({
        "x": x, "y": y, "color": color, "radius": radius,
        "age": 0, "max_age": max_age,
    })


def _spirit_zoo_make_sprite(kind, x, y, height, color):
    """用项目现有 Enemy 承载 Spirit Animal 贴图；只负责绘制，不参与玩家弹碰撞。"""
    enemy = Enemy(
        x, y, hp=999999, score=0, size=12, color=color,
        sprite_paths=[_SPIRIT_SPRITE_PATHS[kind]],
        sprite_height=height, anim_speed=16)
    enemy.entry_done = True
    enemy.age = 0
    return enemy


def _spirit_zoo_sync_sprite(rec):
    sprite = rec.get("sprite")
    if sprite is not None:
        sprite.x = rec["x"]
        sprite.y = rec["y"]
        sprite.age = rec["age"]


def _spirit_zoo_clamp_field_x(x):
    return _clamp_x(x, 40)


def _spirit_zoo_clamp_field_y(y):
    return max(64, min(cfg.BATTLE_AREA_HEIGHT - 34, y))


def _spirit_zoo_drop_mine(state, x, y):
    """Chicken 留下 Chicken Mine；场上 Mine 数量有硬上限。"""
    mines = state["mines"]
    if len(mines) >= _SPIRIT_ZOO["mine"]["max"]:
        return False
    mines.append({
        "x": _spirit_zoo_clamp_field_x(x),
        "y": _spirit_zoo_clamp_field_y(y),
        "age": 0,
        "fuse": -1,
        "phase": random.random() * math.tau,
        "cause": "timeout",
    })
    _spirit_zoo_add_fx(state, mines[-1]["x"], mines[-1]["y"],
                       (180, 120, 255), radius=7, max_age=14)
    return True


def _spirit_zoo_set_mine_fuse(state, mine, cause):
    """让 Mine 进入爆炸倒计时。动物触发会很快，玩家贴近则留出反应时间。"""
    spec = _SPIRIT_ZOO["mine"]
    fuse = spec["animal_fuse"] if cause == "animal" else spec["player_fuse"]
    if mine.get("fuse", -1) < 0 or fuse < mine["fuse"]:
        mine["fuse"] = fuse
        mine["cause"] = cause


def _spirit_zoo_trigger_mines_near(state, x, y, radius, cause="animal"):
    """动物攻击/爆炸路径附近的 Mine 连锁触发。"""
    for mine in state["mines"]:
        if mine["age"] < _SPIRIT_ZOO["mine"]["warn"]:
            continue
        if math.hypot(mine["x"] - x, mine["y"] - y) <= radius:
            _spirit_zoo_set_mine_fuse(state, mine, cause)


def _spirit_zoo_trigger_segment(state, x1, y1, x2, y2, radius):
    """检查一段动物路径是否扫过 Mine（主要用于 Rabbit 冲刺）。"""
    for mine in state["mines"]:
        if mine["age"] < _SPIRIT_ZOO["mine"]["warn"]:
            continue
        if point_segment_distance(mine["x"], mine["y"], x1, y1, x2, y2) <= radius:
            _spirit_zoo_set_mine_fuse(state, mine, "animal")


def _spirit_zoo_explode_mine(state, bullet_manager, mine):
    """Chicken Mine 爆炸：少量固定环向碎片弹，不追踪玩家。"""
    spec = _SPIRIT_ZOO["mine"]
    for i in range(spec["fragment_count"]):
        angle = mine["phase"] + i * math.tau / spec["fragment_count"]
        speed = random.uniform(spec["fragment_speed_min"], spec["fragment_speed_max"])
        color = (178, 120, 255) if i % 2 == 0 else (122, 180, 255)
        b = create_bullet_angle(mine["x"], mine["y"], angle, speed,
                                Bullet.TYPE_RICE, radius=2.3, color=color)
        b.manager = bullet_manager
        _add(bullet_manager, b)
    _spirit_zoo_add_fx(state, mine["x"], mine["y"], (205, 165, 255),
                       radius=15, max_age=20)
    if mine in state["mines"]:
        state["mines"].remove(mine)


def _spirit_zoo_update_mines(boss, bullet_manager, player_x, player_y):
    """推进 Mine 预警、玩家贴近触发、动物触发与到期爆炸。"""
    state = boss.spirit_zoo
    spec = _SPIRIT_ZOO["mine"]
    for mine in state["mines"][:]:
        mine["age"] += 1

        if mine.get("fuse", -1) >= 0:
            mine["fuse"] -= 1
            if mine["fuse"] <= 0:
                _spirit_zoo_explode_mine(state, bullet_manager, mine)
            continue

        if mine["age"] >= spec["warn"]:
            dist = math.hypot(player_x - mine["x"], player_y - mine["y"])
            if dist <= spec["player_trigger_radius"]:
                _spirit_zoo_set_mine_fuse(state, mine, "player")
            elif mine["age"] >= spec["warn"] + spec["armed_life"]:
                _spirit_zoo_explode_mine(state, bullet_manager, mine)


def _spirit_zoo_spawn_animal(boss, kind, timer, player_x, player_y):
    """生成一只 Spirit Animal；各动物沿用 Enemy 贴图，行为由字典状态驱动。"""
    state = boss.spirit_zoo
    spec = _SPIRIT_ZOO[kind]

    if kind == "chicken":
        lane = random.choice(spec["lanes"])
        rec = {
            "kind": "chicken", "alive": True, "age": 0,
            "x": lane, "y": -26, "base_x": lane,
            "phase": random.random() * math.tau,
            "sprite": _spirit_zoo_make_sprite(kind, lane, -26, 34, (225, 235, 255)),
        }
    elif kind == "rabbit":
        lane_idx = state["rabbit_lane"] % len(spec["lanes"])
        state["rabbit_lane"] += 1
        lane_y = spec["lanes"][lane_idx]
        start_x = cfg.PLAY_AREA_LEFT if lane_idx % 2 == 0 else cfg.PLAY_AREA_RIGHT
        end_x = cfg.PLAY_AREA_RIGHT if start_x == cfg.PLAY_AREA_LEFT else cfg.PLAY_AREA_LEFT
        rec = {
            "kind": "rabbit", "alive": True, "age": 0,
            "x": start_x, "y": lane_y,
            "lane_idx": lane_idx, "lane_y": lane_y,
            "start_x": start_x, "end_x": end_x,
            "phase": "rest", "phase_timer": spec["rest_frames"],
            "trail": [],
            "sprite": _spirit_zoo_make_sprite(kind, start_x, lane_y, 32, (205, 180, 255)),
        }
    elif kind == "sheep":
        x = random.uniform(90, cfg.BATTLE_AREA_WIDTH - 90)
        y = random.uniform(82, 150)
        desired = math.atan2(player_y - y, player_x - x)
        desired = round(desired / (math.tau / 8)) * (math.tau / 8)
        rec = {
            "kind": "sheep", "alive": True, "age": 0,
            "x": x, "y": y,
            "phase": "approach", "phase_timer": spec["retarget_interval"],
            "desired_angle": desired, "vx": 0.0, "vy": 0.0,
            "phase_offset": random.random() * math.tau,
            "sprite": _spirit_zoo_make_sprite(kind, x, y, 34, (220, 220, 245)),
        }
    elif kind == "wolf":
        base_path = [(90, 170), (205, 120), (320, 185), (440, 125),
                     (530, 195), (380, 265), (180, 245)]
        shift_x = random.uniform(-14, 14)
        shift_y = random.uniform(-8, 8)
        waypoints = [(_spirit_zoo_clamp_field_x(x + shift_x),
                      _spirit_zoo_clamp_field_y(y + shift_y))
                     for x, y in base_path]
        rec = {
            "kind": "wolf", "alive": True, "age": 0,
            "x": waypoints[0][0], "y": waypoints[0][1],
            "waypoints": waypoints, "waypoint_idx": 0,
            "fire_timer": 30, "trail": [],
            "sprite": _spirit_zoo_make_sprite(kind, waypoints[0][0],
                                              waypoints[0][1], 42, (120, 105, 175)),
        }
    elif kind == "bat":
        direction = 1 if _spirit_zoo_count_active(state, "bat") % 2 == 0 else -1
        rec = {
            "kind": "bat", "alive": True, "age": 0,
            "x": spec["x_min"] if direction == 1 else spec["x_max"],
            "y": spec["y_base"], "dir": direction,
            "phase": random.random() * math.tau,
            "fire_timer": 60,
        }
        rec["sprites"] = []
        for i in range(spec["visual_count"]):
            dx = (i - (spec["visual_count"] - 1) / 2.0) * spec["visual_spread"]
            dy = math.sin(i * 0.9) * 4
            sprite = _spirit_zoo_make_sprite(kind, rec["x"] + dx,
                                             rec["y"] + dy, 18, (160, 150, 230))
            rec["sprites"].append({"sprite": sprite, "dx": dx, "dy": dy})
    else:
        return

    state["animals"].append(rec)


def _spirit_zoo_maybe_spawn(boss, timer, player_x, player_y):
    """按种类独立计时生成动物；数量上限和间隔都在 _SPIRIT_ZOO 中。"""
    state = boss.spirit_zoo
    if state.get("ending"):
        return
    for kind in _SPIRIT_KINDS:
        spec = _SPIRIT_ZOO[kind]
        if timer < spec["first_spawn"]:
            continue
        max_count = _spirit_zoo_max_for(kind, timer)
        if max_count <= 0:
            continue
        if _spirit_zoo_count_active(state, kind) >= max_count:
            continue
        if timer - state["last_spawn"][kind] < spec["interval"]:
            continue
        if len(state["animals"]) >= _SPIRIT_ZOO["max_total"]:
            break
        state["last_spawn"][kind] = timer
        _spirit_zoo_spawn_animal(boss, kind, timer, player_x, player_y)


def _spirit_zoo_update_chicken(boss, rec):
    spec = _SPIRIT_ZOO["chicken"]
    rec["age"] += 1
    rec["y"] += spec["speed"]
    rec["x"] = _spirit_zoo_clamp_field_x(
        rec["base_x"] + math.sin(rec["age"] * spec["x_freq"] + rec["phase"])
        * spec["x_amp"])

    # 进入路线中段后开始沿途布 Mine；最多同时保留 mine.max 个。
    if rec["age"] >= spec["first_mine"]:
        if (rec["age"] - spec["first_mine"]) % spec["mine_every"] == 0:
            _spirit_zoo_drop_mine(boss.spirit_zoo, rec["x"], rec["y"])

    if rec["age"] >= spec["life"] or rec["y"] > cfg.BATTLE_AREA_HEIGHT + 40:
        rec["alive"] = False
    _spirit_zoo_sync_sprite(rec)


def _spirit_zoo_update_rabbit(boss, rec):
    spec = _SPIRIT_ZOO["rabbit"]
    rec["age"] += 1

    if rec["phase"] == "rest":
        rec["phase_timer"] -= 1
        if rec["phase_timer"] <= 0:
            rec["phase"] = "telegraph"
            rec["phase_timer"] = spec["telegraph_frames"]
    elif rec["phase"] == "telegraph":
        rec["phase_timer"] -= 1
        if rec["phase_timer"] <= 0:
            rec["phase"] = "dash"
            rec["phase_timer"] = spec["dash_frames"]
            rec["dash_t"] = 0.0
            rec["prev_x"], rec["prev_y"] = rec["start_x"], rec["lane_y"]
            rec["x"], rec["y"] = rec["start_x"], rec["lane_y"]
    elif rec["phase"] == "dash":
        rec["phase_timer"] -= 1
        rec["dash_t"] = 1.0 - max(0, rec["phase_timer"]) / float(spec["dash_frames"])
        new_x = rec["start_x"] + (rec["end_x"] - rec["start_x"]) * rec["dash_t"]
        new_y = rec["lane_y"]
        # Rabbit 冲刺扫过的路径会触发 Chicken Mine。
        _spirit_zoo_trigger_segment(boss.spirit_zoo, rec["prev_x"], rec["prev_y"],
                                    new_x, new_y, spec["trigger_radius"])
        rec["prev_x"], rec["prev_y"] = new_x, new_y
        rec["x"], rec["y"] = new_x, new_y
        if rec["phase_timer"] <= 0:
            rec["x"], rec["y"] = rec["end_x"], rec["lane_y"]
            rec["phase"] = "pause"
            rec["phase_timer"] = spec["pause_frames"]
    elif rec["phase"] == "pause":
        rec["phase_timer"] -= 1
        if rec["phase_timer"] <= 0:
            rec["lane_idx"] = (rec["lane_idx"] + 1) % len(spec["lanes"])
            rec["lane_y"] = spec["lanes"][rec["lane_idx"]]
            rec["start_x"] = (cfg.PLAY_AREA_LEFT if rec["lane_idx"] % 2 == 0
                              else cfg.PLAY_AREA_RIGHT)
            rec["end_x"] = (cfg.PLAY_AREA_RIGHT
                            if rec["start_x"] == cfg.PLAY_AREA_LEFT
                            else cfg.PLAY_AREA_LEFT)
            rec["x"], rec["y"] = rec["start_x"], rec["lane_y"]
            rec["phase"] = "rest"
            rec["phase_timer"] = spec["rest_frames"]

    rec["trail"].append((rec["x"], rec["y"]))
    if len(rec["trail"]) > 12:
        rec["trail"].pop(0)
    if rec["age"] >= spec["life"]:
        rec["alive"] = False
    _spirit_zoo_sync_sprite(rec)


def _spirit_zoo_sheep_explode(boss, bullet_manager, rec):
    """Sheep 接近玩家后爆炸：固定方向放射弹，并引爆附近 Mine。"""
    spec = _SPIRIT_ZOO["sheep"]
    for i in range(spec["radial_count"]):
        angle = rec.get("phase_offset", 0.0) + i * math.tau / spec["radial_count"]
        color = (165, 120, 255) if i % 2 == 0 else (130, 185, 255)
        b = create_bullet_angle(rec["x"], rec["y"], angle, spec["radial_speed"],
                                Bullet.TYPE_CIRCLE, radius=2.6, color=color)
        b.manager = bullet_manager
        _add(bullet_manager, b)
    _spirit_zoo_add_fx(boss.spirit_zoo, rec["x"], rec["y"],
                       (190, 145, 255), radius=18, max_age=22)
    _spirit_zoo_trigger_mines_near(boss.spirit_zoo, rec["x"], rec["y"],
                                   spec["explosion_radius"], cause="animal")


def _spirit_zoo_update_sheep(boss, bullet_manager, rec, player_x, player_y):
    spec = _SPIRIT_ZOO["sheep"]
    rec["age"] += 1

    if rec["phase"] == "approach":
        rec["phase_timer"] -= 1
        if rec["phase_timer"] <= 0:
            rec["phase_timer"] = spec["retarget_interval"]
            target_x = player_x + random.uniform(-70, 70)
            target_y = player_y + random.uniform(-45, 45)
            desired = math.atan2(target_y - rec["y"], target_x - rec["x"])
            # 量化为 8 方向 + 有限转向，避免持续精准追踪。
            desired = round(desired / (math.tau / 8)) * (math.tau / 8)
            rec["desired_angle"] = desired

        if abs(rec["vx"]) + abs(rec["vy"]) < 0.001:
            cur_angle = rec.get("desired_angle", math.pi / 2)
        else:
            cur_angle = math.atan2(rec["vy"], rec["vx"])
        diff = (rec["desired_angle"] - cur_angle + math.pi) % math.tau - math.pi
        turn = max(-spec["turn_speed"], min(spec["turn_speed"], diff))
        new_angle = cur_angle + turn
        rec["vx"] = math.cos(new_angle) * spec["speed"]
        rec["vy"] = math.sin(new_angle) * spec["speed"]
        rec["x"] = _spirit_zoo_clamp_field_x(rec["x"] + rec["vx"])
        rec["y"] = _spirit_zoo_clamp_field_y(rec["y"] + rec["vy"])

        if math.hypot(player_x - rec["x"], player_y - rec["y"]) <= spec["explode_distance"]:
            rec["phase"] = "warn"
            rec["phase_timer"] = spec["warn_frames"]
    elif rec["phase"] == "warn":
        rec["phase_timer"] -= 1
        if rec["phase_timer"] <= 0:
            _spirit_zoo_sheep_explode(boss, bullet_manager, rec)
            rec["alive"] = False

    _spirit_zoo_sync_sprite(rec)


def _spirit_zoo_update_wolf(boss, bullet_manager, rec):
    spec = _SPIRIT_ZOO["wolf"]
    rec["age"] += 1

    target = rec["waypoints"][rec["waypoint_idx"]]
    dx = target[0] - rec["x"]
    dy = target[1] - rec["y"]
    dist = math.hypot(dx, dy)
    if dist <= 3.0:
        rec["waypoint_idx"] = (rec["waypoint_idx"] + 1) % len(rec["waypoints"])
    else:
        rec["x"] += dx / dist * spec["speed"]
        rec["y"] += dy / dist * spec["speed"]

    rec["fire_timer"] -= 1
    if rec["fire_timer"] <= 0:
        rec["fire_timer"] = spec["fire_interval"]
        base = math.pi / 2 + math.sin(rec["age"] * 0.023) * 0.38
        for j in range(spec["fire_count"]):
            offset = (j - (spec["fire_count"] - 1) / 2.0) * spec["fire_spread"]
            color = (80, 95, 155) if j % 2 == 0 else (105, 85, 175)
            b = create_bullet_angle(rec["x"], rec["y"], base + offset,
                                    spec["fire_speed"], Bullet.TYPE_KNIFE,
                                    radius=2.4, color=color)
            b.manager = bullet_manager
            _add(bullet_manager, b)
        # Wolf 巡逻到开火点时也可能引爆旁边的 Chicken Mine。
        _spirit_zoo_trigger_mines_near(boss.spirit_zoo, rec["x"], rec["y"],
                                       spec["trigger_radius"], cause="animal")

    rec["trail"].append((rec["x"], rec["y"]))
    if len(rec["trail"]) > 16:
        rec["trail"].pop(0)
    if rec["age"] >= spec["life"]:
        rec["alive"] = False
    _spirit_zoo_sync_sprite(rec)


def _spirit_zoo_update_bat(boss, bullet_manager, rec):
    spec = _SPIRIT_ZOO["bat"]
    rec["age"] += 1

    rec["x"] += rec["dir"] * spec["speed"]
    if rec["x"] <= spec["x_min"]:
        rec["x"] = spec["x_min"]
        rec["dir"] = 1
    elif rec["x"] >= spec["x_max"]:
        rec["x"] = spec["x_max"]
        rec["dir"] = -1
    rec["y"] = spec["y_base"] + math.sin(rec["age"] * spec["bob_speed"]
                                          + rec["phase"]) * spec["bob_amp"]

    rec["fire_timer"] -= 1
    if rec["fire_timer"] <= 0:
        rec["fire_timer"] = spec["fire_interval"]
        for i in range(spec["row_count"]):
            bx = rec["x"] + (i - (spec["row_count"] - 1) / 2.0) * spec["row_spread"]
            by = rec["y"] + 16
            angle = math.pi / 2 + math.sin(rec["age"] * 0.018 + i) * 0.045
            color = (108, 94, 210) if i % 2 == 0 else (126, 110, 235)
            b = create_bullet_angle(bx, by, angle, spec["bullet_speed"],
                                    Bullet.TYPE_RICE, radius=2.2, color=color)
            b.manager = bullet_manager
            _add(bullet_manager, b)

    for entry in rec["sprites"]:
        sprite = entry["sprite"]
        sprite.x = rec["x"] + entry["dx"]
        sprite.y = rec["y"] + entry["dy"] + math.sin(rec["age"] * 0.05 + entry["dx"]) * 3
        sprite.age = rec["age"]
    if rec["age"] >= spec["life"]:
        rec["alive"] = False


def _spirit_zoo_bear_burst(bullet_manager, x, y):
    """One Bigfoot-stomp-density final burst, recolored for Spirit Bear.

    Reuses the ring/rotation approach from stage4 Bigfoot slam rings: 4 layered
    orbit rings (13 bullets each) plus a 28-bullet fast debris ring.
    """
    layers = 4
    ring_count = 13
    for layer in range(layers):
        radius = 14 + layer * 15
        angle_offset = 0.0 if layer % 2 == 0 else math.tau / (ring_count * 2)
        for i in range(ring_count):
            angle = angle_offset + i * math.tau / ring_count
            b = create_bullet_angle(
                x, y, angle, 0.0, Bullet.TYPE_CIRCLE,
                radius=2.7 if layer % 2 == 0 else 2.2,
                color=(160, 130, 255) if layer % 2 == 0 else (120, 190, 255),
                lifetime=240)
            b.manager = bullet_manager
            b.orbit_center = (x, y)
            b.orbit_radius = radius
            b.orbit_angle = angle
            b.orbit_grow = max(1.6, 3.2 - layer * 0.14)
            b.orbit_speed = 0.0
            _add(bullet_manager, b)

    debris_count = 28
    for i in range(debris_count):
        angle = i * math.tau / debris_count
        b = create_bullet_angle(x, y, angle, 2.2, Bullet.TYPE_ARROW,
                                radius=2.1, color=(190, 150, 255),
                                lifetime=300)
        b.manager = bullet_manager
        _add(bullet_manager, b)


def _spirit_zoo_update_bear(boss, bullet_manager, timer):
    """Spirit Bear final exhibition: enter -> draw bow -> giant arrow + burst -> end."""
    state = boss.spirit_zoo
    spec = _SPIRIT_ZOO
    if timer < spec["bear_time"]:
        return

    bear = state["bear"]
    if bear is None:
        bear = {
            "phase": "enter", "age": 0,
            "x": cfg.BATTLE_AREA_WIDTH / 2, "y": -70, "target_y": 88,
        }
        bear["sprite"] = _spirit_zoo_make_sprite(
            "bear", bear["x"], bear["y"], 190, (185, 190, 255))
        bear["bow_sprite"] = _spirit_zoo_make_sprite(
            "bow", bear["x"], bear["y"] + 24, 64, (215, 190, 255))
        state["bear"] = bear
        return

    bear["age"] += 1
    if bear["phase"] == "enter":
        bear["y"] += (bear["target_y"] - bear["y"]) * min(1.0, 0.14)
        if abs(bear["target_y"] - bear["y"]) <= 2.0:
            bear["y"] = bear["target_y"]
            bear["phase"] = "aim"
            bear["phase_timer"] = spec["bear_aim_frames"]
    elif bear["phase"] == "aim":
        bear["phase_timer"] -= 1
        if bear["phase_timer"] <= 0:
            x = bear["x"]
            y = bear["y"] + 34
            # Giant vertical arrow uses the provided arrow.png as its bullet sprite.
            arrow = create_bullet_angle(x, y, math.pi / 2, 7.2,
                                        Bullet.TYPE_ARROW, radius=11,
                                        color=(235, 225, 255), lifetime=200)
            arrow.manager = bullet_manager
            arrow.custom_sprite_path = _SPIRIT_ARROW_SPRITE
            arrow.custom_sprite_height = 92
            arrow.collision_radius = 11
            _add(bullet_manager, arrow)

            _spirit_zoo_bear_burst(bullet_manager, x, y)
            _spirit_zoo_add_fx(state, x, y, (225, 205, 255), radius=28, max_age=30)
            boss.hp = 0
            state["ending"] = True
            bear["phase"] = "fired"
            bear["phase_timer"] = spec["bear_end_delay"]
    elif bear["phase"] == "fired":
        bear["phase_timer"] -= 1
        if bear["phase_timer"] <= 0 and not state.get("ended"):
            state["ended"] = True
            boss._end_spell()

    bear["sprite"].x = bear["x"]
    bear["sprite"].y = bear["y"]
    bear["sprite"].age = bear["age"]
    bear["bow_sprite"].x = bear["x"]
    bear["bow_sprite"].y = bear["y"] + 24
    bear["bow_sprite"].age = bear["age"]


def _spirit_zoo_update(boss, bullet_manager, timer, dt, player_x, player_y):
    state = boss.spirit_zoo

    # 先推进生成，再推进行为：同帧内新生成动物从下一帧开始活动。
    if not state.get("ending"):
        _spirit_zoo_maybe_spawn(boss, timer, player_x, player_y)

    for rec in state["animals"][:]:
        if rec["kind"] == "chicken":
            _spirit_zoo_update_chicken(boss, rec)
        elif rec["kind"] == "rabbit":
            _spirit_zoo_update_rabbit(boss, rec)
        elif rec["kind"] == "sheep":
            _spirit_zoo_update_sheep(boss, bullet_manager, rec, player_x, player_y)
        elif rec["kind"] == "wolf":
            _spirit_zoo_update_wolf(boss, bullet_manager, rec)
        elif rec["kind"] == "bat":
            _spirit_zoo_update_bat(boss, bullet_manager, rec)
        if not rec.get("alive", True):
            state["animals"].remove(rec)

    _spirit_zoo_update_mines(boss, bullet_manager, player_x, player_y)
    _spirit_zoo_update_bear(boss, bullet_manager, timer)

    for fx in state["fx"]:
        fx["age"] += 1
    state["fx"] = [fx for fx in state["fx"] if fx["age"] < fx["max_age"]]


def spell_thorn_spirit_zoo(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """灵符「Spirit Zoo」：五种 Spirit Animals 共存并靠行为链控制场地。"""
    if getattr(boss, "spirit_zoo", None) is None:
        _spirit_zoo_init(boss)

    # Thorn 本体只做轻微浮动，不亲自开火；所有威胁来自 Spirit Animals。
    if timer % 90 == 0 and not boss.spirit_zoo.get("ending"):
        boss.move_to(_clamp_x(cfg.BATTLE_AREA_WIDTH / 2
                              + math.sin(timer * 0.012) * 46), 104)

    _spirit_zoo_update(boss, bullet_manager, timer, dt, player_x, player_y)


def _spirit_zoo_draw_trail(screen, trail, color, offset_x, offset_y):
    """Wolf/Rabbit 的幽魂拖尾，直接用同心圆表现残影。"""
    for i, (x, y) in enumerate(trail):
        r = 2 + i * 1.1
        pygame.draw.circle(screen, color,
                           (int(x + offset_x), int(y + offset_y)), int(r), 1)


def _spirit_zoo_draw_bear(screen, bear, offset_x, offset_y):
    """Draw the provided Spirit Bear sprite, with Spirit Bow during aim/fired."""
    sprite = bear.get("sprite")
    if sprite is not None:
        sprite.draw(screen, offset_x, offset_y)
    if bear["phase"] in ("aim", "fired"):
        bow = bear.get("bow_sprite")
        if bow is not None:
            bow.draw(screen, offset_x, offset_y)


def _spirit_zoo_draw_animals(screen, boss, offset_x=0, offset_y=0):
    state = getattr(boss, "spirit_zoo", None)
    if state is None:
        return

    for rec in state["animals"]:
        if not rec.get("alive", True):
            continue
        if rec["kind"] == "bat":
            for entry in rec["sprites"]:
                entry["sprite"].draw(screen, offset_x, offset_y)
            continue
        if rec["kind"] == "rabbit":
            _spirit_zoo_draw_trail(screen, rec.get("trail", []),
                                   (185, 150, 250), offset_x, offset_y)
        elif rec["kind"] == "wolf":
            _spirit_zoo_draw_trail(screen, rec.get("trail", []),
                                   (75, 68, 125), offset_x, offset_y)
        if rec.get("sprite") is not None:
            rec["sprite"].draw(screen, offset_x, offset_y)

    if state.get("bear") is not None:
        _spirit_zoo_draw_bear(screen, state["bear"], offset_x, offset_y)


def _spirit_zoo_draw_hazards(screen, boss, offset_x=0, offset_y=0):
    """绘制 Mine 魔法阵、Rabbit 冲刺线、Sheep 爆炸圈与 Bear 巨箭预警。"""
    state = getattr(boss, "spirit_zoo", None)
    if state is None:
        return

    mine_spec = _SPIRIT_ZOO["mine"]
    for mine in state["mines"]:
        x = int(mine["x"] + offset_x)
        y = int(mine["y"] + offset_y)
        age = mine["age"]
        if age < mine_spec["warn"]:
            if (age // 6) % 2 == 0:
                pygame.draw.circle(screen, (190, 110, 255), (x, y), 3, 0)
            pygame.draw.circle(screen, (190, 110, 255), (x, y),
                               int(10 + age * 0.55), 1)
        else:
            color = (225, 120, 255) if mine.get("fuse", -1) >= 0 else (150, 90, 235)
            base_r = 15 + math.sin(age * 0.06) * 2
            for ring in range(3):
                pygame.draw.circle(screen, color, (x, y),
                                   int(base_r + ring * 4), 1)
            pts = []
            for i in range(6):
                ang = age * 0.05 + i * math.tau / 6 - math.pi / 2
                pts.append((x + math.cos(ang) * base_r,
                            y + math.sin(ang) * base_r))
            pygame.draw.polygon(screen, (185, 125, 255), pts, 1)

    rabbit_spec = _SPIRIT_ZOO["rabbit"]
    for rec in state["animals"]:
        if rec.get("kind") != "rabbit" or not rec.get("alive", True):
            continue
        if rec["phase"] == "telegraph":
            x1 = int(rec["start_x"] + offset_x)
            y1 = int(rec["lane_y"] + offset_y)
            x2 = int(rec["end_x"] + offset_x)
            y2 = int(rec["lane_y"] + offset_y)
            pygame.draw.line(screen, (95, 62, 135), (x1, y1), (x2, y2), 7)
            pygame.draw.line(screen, (205, 170, 255), (x1, y1), (x2, y2), 2)
            pygame.draw.circle(screen, (225, 190, 255), (x2, y2), 5, 1)

    sheep_spec = _SPIRIT_ZOO["sheep"]
    for rec in state["animals"]:
        if rec.get("kind") != "sheep" or not rec.get("alive", True):
            continue
        if rec["phase"] == "warn":
            x = int(rec["x"] + offset_x)
            y = int(rec["y"] + offset_y)
            pulse = int(sheep_spec["explode_distance"]
                        + math.sin(rec["age"] * 0.25) * 6)
            pygame.draw.circle(screen, (220, 125, 255), (x, y), pulse, 2)
            pygame.draw.circle(screen, (130, 90, 220), (x, y), pulse, 1)

    bear = state.get("bear")
    if bear is not None and bear["phase"] == "aim":
        x = int(bear["x"] + offset_x)
        top = int(bear["y"] + 34 + offset_y)
        bottom = int(cfg.BATTLE_AREA_HEIGHT - 10 + offset_y)
        pygame.draw.line(screen, (95, 65, 145), (x, top), (x, bottom), 9)
        pygame.draw.line(screen, (235, 210, 255), (x, top), (x, bottom), 3)
        for yy in range(top, bottom, 18):
            pygame.draw.circle(screen, (240, 220, 255), (x, yy), 2, 0)

    for fx in state.get("fx", []):
        t = fx["age"] / float(max(1, fx["max_age"]))
        radius = int(fx["radius"] + t * 20)
        pygame.draw.circle(screen, fx["color"],
                           (int(fx["x"] + offset_x), int(fx["y"] + offset_y)),
                           max(1, radius), 2)


def spell_livid_shadowstep(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """影符「Livid's Shadowstep」：连续瞬移，每次落地都释放青蓝圆环与刀扇。"""
    if timer % 55 == 0:
        boss.x = _clamp_x(random.uniform(120, cfg.BATTLE_AREA_WIDTH - 120))
        boss.y = _clamp_y(random.uniform(96, 190))
        boss.move_to(boss.x, boss.y)
        for i in range(20):
            angle = i * math.tau / 20 + timer * 0.04
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, angle, 2.1,
                                     Bullet.TYPE_KNIFE, radius=2.5, color=(70, 210, 245)))
    if timer % 21 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for offset in (-0.32, -0.11, 0.11, 0.32):
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, base + offset, 2.9,
                                     Bullet.TYPE_CIRCLE, radius=3, color=(90, 220, 240)))
    if timer % 39 == 0:
        for i in range(8):
            angle = timer * 0.045 + i * math.tau / 8
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, angle, 1.6,
                                     Bullet.TYPE_RICE, radius=2.5, color=(130, 235, 250)))


_LIVID_CLONE_SPRITE_HEIGHT = 58
_LIVID_CLONE_SIZE = 11
_LIVID_CLONE_COLORS = (
    (248, 248, 255),
    (255, 70, 225),
    (245, 75, 75),
    (158, 162, 176),
    (40, 150, 82),
    (158, 225, 68),
    (85, 150, 255),
    (188, 90, 255),
    (255, 235, 90),
)
_LIVID_ITEM_NAMES = ("warped_stone", "dark_orb", "livid_dagger",
                     "last_breath", "shadow_fury")
_LIVID_ITEM_FILES = {
    "warped_stone": "Warped_Stone.png",
    "dark_orb": "Dark_Orb.png",
    "livid_dagger": "Livid_Dagger.png",
    "last_breath": "Last_Breath.png",
    "shadow_fury": "Shadow_Fury.png",
}


_livid_clone_sprite_cache = {}


def _get_livid_clone_sprite(height):
    if height in _livid_clone_sprite_cache:
        return _livid_clone_sprite_cache[height]
    sprite = None
    try:
        image = pygame.image.load(cfg.STAGE5_LIVID_BOSS_SPRITE).convert_alpha()
        w, h = image.get_size()
        new_w = max(1, int(round(w * height / h)))
        sprite = pygame.transform.smoothscale(image, (new_w, height))
    except Exception as exc:
        print(f"[Stage5] Failed to load Livid clone sprite: {exc}")
    _livid_clone_sprite_cache[height] = sprite
    return sprite


_livid_item_sprite_cache = {}


def _get_livid_item_sprite(item_name, height=30):
    key = (item_name, height)
    if key in _livid_item_sprite_cache:
        return _livid_item_sprite_cache[key]
    sprite = None
    path = os.path.join(cfg.SPRITES_DIR, "enemies", "stage5", "livid",
                        _LIVID_ITEM_FILES[item_name])
    try:
        image = pygame.image.load(path).convert_alpha()
        w, h = image.get_size()
        new_w = max(1, int(round(w * height / h)))
        sprite = pygame.transform.smoothscale(image, (new_w, height))
    except Exception as exc:
        print(f"[Stage5] Failed to load Livid item sprite {path}: {exc}")
    _livid_item_sprite_cache[key] = sprite
    return sprite


_livid_glow_cache = {}


def _get_livid_glow(color, radius):
    key = (color, radius)
    if key in _livid_glow_cache:
        return _livid_glow_cache[key]
    outer = max(4, int(radius * 2))
    size = outer * 2 + 12
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    for r in range(outer, 0, -1):
        t = r / float(outer)
        alpha = int(120 * ((1.0 - t) ** 1.35))
        pygame.draw.circle(surf, (color[0], color[1], color[2], alpha), (cx, cy), r)
    _livid_glow_cache[key] = surf
    return surf


_livid_top_glow_cache = {}


def _get_livid_top_glow(color):
    if color in _livid_top_glow_cache:
        return _livid_top_glow_cache[color]
    width = cfg.BATTLE_AREA_WIDTH
    height = 118
    layer = pygame.Surface((width, height), pygame.SRCALPHA)
    cx = width // 2
    cy = 24
    for r in range(120, 0, -1):
        t = r / 120.0
        alpha = int(115 * ((1.0 - t) ** 1.35))
        rect = (cx - int(r * 3.0), cy - int(r * 0.85),
                int(r * 6.0), int(r * 1.7))
        pygame.draw.ellipse(layer, (color[0], color[1], color[2], alpha), rect)
    _livid_top_glow_cache[color] = layer
    return layer


def _livid_cleanup(boss):
    boss.livid_active = False
    boss.livid_clones = []
    boss.livid_clone_map = {}
    boss.livid_states = []
    boss.livid_blackout_frames = 0
    boss.livid_swap_pending = False
    if hasattr(boss, "_livid_original_size"):
        boss.size = boss._livid_original_size
        delattr(boss, "_livid_original_size")


def _livid_heal_from_fake(boss):
    amount = getattr(boss, "livid_heal_amount", 0.0)
    spell_hp = getattr(boss, "livid_spell_hp", boss.hp)
    boss.hp = min(spell_hp, boss.hp + amount)


class _LividClone:
    """非真身 Livid 分身：仅用于碰撞与绘制，攻击逻辑由符卡统一驱动。"""

    def __init__(self, index, boss, state):
        self.index = index
        self.boss = boss
        self.state = state
        self.x = state["x"]
        self.y = state["y"]
        self.alive = True
        self.age = 0
        self.size = _LIVID_CLONE_SIZE
        self.score = 0
        self.bonus_drops = None
        self.hp = boss.livid_spell_hp * 0.5
        self.max_hp = boss.livid_spell_hp * 0.5

    def get_hitbox(self):
        return (self.x, self.y, self.size * 0.85, self.size * 0.85)

    def collides_with_bullet(self, bx, by, br):
        r = self.size * 0.85
        dx = bx - self.x
        dy = by - self.y
        rr = br + r
        return dx * dx + dy * dy <= rr * rr

    def take_damage(self, damage):
        if not self.alive:
            return False
        self.hp -= damage * self.boss.spell_resistance
        if self.hp <= 0:
            self.alive = False
            _livid_heal_from_fake(self.boss)
        return False

    def draw(self, screen, offset_x=0, offset_y=0):
        px = int(self.x + offset_x)
        py = int(self.y + offset_y)
        state = self.state
        glow = _get_livid_glow(state["color"], 40)
        screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))
        sprite = _get_livid_clone_sprite(_LIVID_CLONE_SPRITE_HEIGHT)
        if sprite is not None:
            screen.blit(sprite, (px - sprite.get_width() // 2, py - sprite.get_height() // 2))
        item_sprite = _get_livid_item_sprite(state["item"], 30)
        if item_sprite is not None:
            bob = int(math.sin(self.age * 0.10) * 3)
            foot_y = py + int(_LIVID_CLONE_SPRITE_HEIGHT * 0.55)
            screen.blit(item_sprite, (px - item_sprite.get_width() // 2, foot_y + bob))


def _livid_eightfold_init(boss):
    if getattr(boss, "livid_active", False):
        _livid_cleanup(boss)

    boss.livid_active = True
    boss.livid_spell_hp = max(1.0, boss.hp * 0.5)
    boss.hp = boss.livid_spell_hp
    boss.max_hp = boss.livid_spell_hp
    boss.livid_heal_amount = boss.livid_spell_hp * 0.10
    boss.livid_real_index = random.randrange(8)
    boss.livid_blackout_frames = 0
    boss.livid_swap_pending = False

    colors = random.sample(_LIVID_CLONE_COLORS, 8)
    items = [random.choice(_LIVID_ITEM_NAMES) for _ in range(8)]
    slots = [
        (96, 104), (222, 100), (354, 104), (480, 100),
        (96, 176), (222, 180), (354, 176), (480, 180),
    ]
    random.shuffle(slots)

    states = []
    for i, (sx, sy) in enumerate(slots):
        states.append({
            "index": i,
            "base_x": sx + random.uniform(-18, 18),
            "base_y": sy + random.uniform(-8, 8),
            "x": sx,
            "y": sy,
            "phase_x": random.uniform(0, math.tau),
            "phase_y": random.uniform(0, math.tau),
            "amp_x": random.uniform(12, 24),
            "amp_y": random.uniform(7, 14),
            "speed_x": random.uniform(0.016, 0.030),
            "speed_y": random.uniform(0.022, 0.040),
            "item": items[i],
            "color": colors[i],
            "fire_seed": random.randrange(0, 240),
            "shadow_steps": 0,
            "shadow_tick": 0,
        })
    boss.livid_states = states
    boss.livid_clones = []
    boss.livid_clone_map = {}
    for i, state in enumerate(states):
        if i == boss.livid_real_index:
            continue
        clone = _LividClone(i, boss, state)
        boss.livid_clones.append(clone)
        boss.livid_clone_map[i] = clone

    boss._livid_original_size = boss.size
    boss.size = _LIVID_CLONE_SIZE
    boss._spell_sprite_restore = (boss.sprite_path, boss.sprite_height)
    boss.sprite_height = _LIVID_CLONE_SPRITE_HEIGHT
    real_state = states[boss.livid_real_index]
    boss.x = real_state["x"]
    boss.y = real_state["y"]
    boss.move_to(real_state["x"], real_state["y"])


def _livid_update_position(state, timer, dt):
    if state.get("shadow_steps", 0) > 0:
        return
    x = state["base_x"] + math.sin(timer * state["speed_x"] + state["phase_x"]) * state["amp_x"]
    y = state["base_y"] + math.cos(timer * state["speed_y"] + state["phase_y"]) * state["amp_y"]
    state["x"] = _clamp_x(x, margin=48)
    state["y"] = _clamp_y(y, low=82, high=252)


def _livid_entity_attack(boss, bullet_manager, state, timer, dt, player_x, player_y):
    item = state["item"]
    t = timer + state["fire_seed"]
    x = state["x"]
    y = state["y"]

    if item == "warped_stone":
        if t % 224 == 0:
            direction = random.choice((-1, 1))
            distance = random.uniform(62, 108)
            nx = _clamp_x(state["base_x"] + direction * distance, margin=54)
            state["base_x"] = nx
            state["x"] = nx
            for _ in range(random.randint(5, 7)):
                angle = math.pi / 2 + random.uniform(-0.30, 0.30)
                bullet = create_bullet_angle(
                    nx, state["y"], angle, random.uniform(1.5, 2.4),
                    Bullet.TYPE_RICE, radius=2.5, color=(200, 230, 255))
                bullet.sprite_slot = "g01_00"
                _add(bullet_manager, bullet)

    elif item == "dark_orb":
        if t % 264 == 0:
            count = random.randint(14, 18)
            for i in range(count):
                angle = i * math.tau / count + random.uniform(-0.04, 0.04)
                _add(bullet_manager,
                     create_bullet_angle(x, y, angle, 1.75,
                                         Bullet.TYPE_BIG, radius=4,
                                         color=(150, 70, 220)))

    elif item == "livid_dagger":
        if t % 68 == 0:
            base = math.atan2(player_y - y, player_x - x)
            for offset in (-0.12, 0.0, 0.12):
                _add(bullet_manager,
                     create_bullet_angle(x, y, base + offset, 3.05,
                                         Bullet.TYPE_KNIFE, radius=2.5,
                                         color=(80, 210, 240)))

    elif item == "last_breath":
        if t % 244 == 0:
            base = math.atan2(player_y - y, player_x - x)
            count = 8
            for i in range(count):
                offset = (i - (count - 1) / 2.0) * (0.92 / (count - 1))
                _add(bullet_manager,
                     create_bullet_angle(x, y, base + offset, 2.3,
                                         Bullet.TYPE_CIRCLE, radius=3,
                                         color=(225, 242, 255)))

    elif item == "shadow_fury":
        steps = state.get("shadow_steps", 0)
        if steps > 0:
            state["shadow_tick"] -= 1
            if state["shadow_tick"] <= 0:
                state["base_x"] = random.uniform(90, cfg.BATTLE_AREA_WIDTH - 90)
                state["base_y"] = random.uniform(94, 198)
                state["x"] = state["base_x"]
                state["y"] = state["base_y"]
                base_angle = random.uniform(0, math.tau)
                for i in range(9):
                    angle = base_angle + (i / 8.0) * math.pi
                    _add(bullet_manager,
                         create_bullet_angle(state["x"], state["y"], angle, 2.35,
                                             Bullet.TYPE_KNIFE, radius=2.5,
                                             color=(120, 90, 255)))
                state["shadow_steps"] = steps - 1
                state["shadow_tick"] = 8
        elif t % 312 == 0:
            state["shadow_steps"] = 4
            state["shadow_tick"] = 0


def _livid_sync_clones(boss):
    for i, state in enumerate(boss.livid_states):
        if i == boss.livid_real_index:
            boss.x = state["x"]
            boss.y = state["y"]
            boss.target_x = state["x"]
            boss.target_y = state["y"]
        else:
            clone = boss.livid_clone_map.get(i)
            if clone is not None:
                clone.x = state["x"]
                clone.y = state["y"]
                clone.age += 1


def _livid_swap_positions(boss):
    states = boss.livid_states
    positions = [(state["x"], state["y"]) for state in states]
    shuffled = positions[:]
    random.shuffle(shuffled)
    for state, (x, y) in zip(states, shuffled):
        state["x"] = x
        state["y"] = y
        state["base_x"] = x
        state["base_y"] = y
    _livid_sync_clones(boss)


def spell_livid_eightfold_existence(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """影符「八重存在」：Livid 分裂成八个分身，只有真身会扣减本体血量。"""
    if timer == 1:
        _livid_eightfold_init(boss)
    if not getattr(boss, "livid_active", False):
        return

    if timer % 300 == 0:
        boss.livid_blackout_frames = 10
        bullet_manager.enemy_pause_frames = 10
        boss.livid_swap_pending = True

    if boss.livid_blackout_frames > 0:
        return

    for state in boss.livid_states:
        _livid_update_position(state, timer, dt)
        _livid_entity_attack(boss, bullet_manager, state, timer, dt, player_x, player_y)
    _livid_sync_clones(boss)


# ---------------------------------------------------------------------------
# Phase1「Maxor's Frenzy」：高速穿梭 + Wither Skull 横穿 + TNT 延迟爆炸
# ---------------------------------------------------------------------------
_FRENZY_WITHER_SKULL_SPRITE = os.path.join(cfg.BACKGROUNDS_DIR, 'stage3', 'Wither_Skull.png')
_FRENZY_CRYSTAL_SPRITE = os.path.join(cfg.SPRITES_DIR, 'enemies', 'stage5', 'maxor', 'Nether_Star.png')

_FRENZY_DASH_SPEED = 6.6          # 前半高速穿梭速度（px/帧）
_FRENZY_RUSH_SPEED = 9.4          # Frenzy 移动速度（明显提高）
_FRENZY_TOP_Y = 92                # 屏幕上方横向移动高度
_FRENZY_EDGE_MARGIN = 46          # 折返边缘距离
_FRENZY_TURN_CROSSINGS = 5        # 完成几次折返后进入 Frenzy
_FRENZY_SKULL_COUNT = 3           # 每次折返释放的骷髅数量（3 颗）
_FRENZY_SKULL_SPEED = 5.6         # 骷髅初始速度（快速）
_FRENZY_SKULL_BRAKE_DELAY = 36    # 飞出一段距离后开始减速
_FRENZY_SKULL_BRAKE = 0.10        # 每帧减速量
_FRENZY_SKULL_FLOOR = 1.0         # 减速下限（保持巡航，不完全停止）
_FRENZY_TNT_INTERVAL = 26         # 路径上留 TNT 的间隔（帧）
_FRENZY_TNT_DELAY = 52            # TNT 引信时长（帧）
_FRENZY_SHOCK_COUNT = 12          # TNT 爆炸冲击弹数量（密度减半）
_FRENZY_SHOCK_RING = 8            # TNT 冲击弹初始环半径
_FRENZY_SHOCK_BREAK = 60          # TNT 冲击弹脱离半径
_FRENZY_SHOCK_GROW = 2.1          # TNT 冲击弹环外扩速度
_FRENZY_SHOCK_SPEED = 1.9         # 脱离后切线速度
_FRENZY_BIG_SHOCK_INTERVAL = 86   # Frenzy 大型冲击波间隔（帧）
_FRENZY_BIG_SHOCK_COUNT = 15      # 大型冲击波子弹数量（密度减半）
_FRENZY_BIG_SHOCK_GROW = 2.5      # 大型冲击波环外扩速度
_FRENZY_BIG_SHOCK_BREAK = 210     # 大型冲击波脱离半径
_FRENZY_BIG_SHOCK_SPEED = 2.1     # 大型冲击波脱离后切线速度
_FRENZY_CRYSTAL_COUNT = 2         # 掉落的水晶数量
_FRENZY_CRYSTAL_FALL = 2.0        # 水晶最大下落速度
_FRENZY_CRYSTAL_ACCEL = 0.014     # 水晶下落加速度
_FRENZY_CRYSTAL_RADIUS = 20       # 拾取半径（px）
_FRENZY_REVEAL_LASER_AT = 42      # 回中后第几帧红色激光命中
_FRENZY_LASER_DURATION = 90       # 红色激光持续帧数
_FRENZY_DAMAGE_MULT = 5.0         # 激光解封后受到的伤害倍率


_frenzy_crystal_sprite_cache = {}
_frenzy_crystal_sprite_attempted = set()


def _get_frenzy_crystal_sprite(target_height=40):
    """加载 power crystal 贴图（缩放并缓存）；失败返回 None。"""
    key = target_height
    if key in _frenzy_crystal_sprite_attempted:
        return _frenzy_crystal_sprite_cache.get(key)
    _frenzy_crystal_sprite_attempted.add(key)
    sprite = None
    try:
        img = pygame.image.load(_FRENZY_CRYSTAL_SPRITE).convert_alpha()
        w, h = img.get_size()
        if h > 0:
            new_w = max(1, round(w * target_height / h))
            sprite = pygame.transform.smoothscale(img, (new_w, target_height))
    except Exception as exc:
        print(f"[Stage5] Failed to load frenzy crystal sprite: {exc}")
    _frenzy_crystal_sprite_cache[key] = sprite
    return sprite


def _frenzy_init(boss):
    """Phase1 开符初始化：重置状态并进入前半高速穿梭。"""
    boss.frenzy_state = {
        "mode": "dash",            # dash -> frenzy -> reveal -> spiral
        "dir": 1.0,
        "crossings": 0,
        "setup": 22,                # 先滑入屏幕上方起跑位
        "tnt_timer": 0,
        "frenzy_timer": 0,
        "crystals_collected": 0,
        "reveal_timer": 0,
        "laser_fired": False,
        "spiral_timer": 0,
    }
    boss.frenzy_tnts = []
    boss.frenzy_crystals = []
    boss.frenzy_shockwaves = []
    boss.frenzy_laser = None
    boss.move_speed = 8.0
    boss.move_to(_FRENZY_EDGE_MARGIN, _FRENZY_TOP_Y)


def _frenzy_skull_row(boss, bullet_manager, travel_dir):
    """三颗 Wither Skull 散开在屏幕三条轨道：沿固定角度穿过屏幕，飞出一段距离后逐渐减速。"""
    # 骷髅不再挤在 Boss 身边，而是均匀散开在整个屏幕宽度上
    base_angle = math.pi * 0.38 if travel_dir > 0 else math.pi * 0.62
    for i in range(_FRENZY_SKULL_COUNT):
        frac = (i + 1) / (_FRENZY_SKULL_COUNT + 1)
        x = cfg.BATTLE_AREA_WIDTH * frac
        y = boss.y + 4
        # 每颗带一点角度差，三条轨道向下略微散开
        angle = base_angle + (i - (_FRENZY_SKULL_COUNT - 1) / 2) * 0.05
        bullet = create_bullet_angle(x, y, angle,
                                     _FRENZY_SKULL_SPEED,
                                     Bullet.TYPE_CIRCLE, radius=4.0,
                                     color=(170, 215, 255), lifetime=420)
        bullet.manager = bullet_manager
        bullet.custom_sprite_path = _FRENZY_WITHER_SKULL_SPRITE
        bullet.custom_sprite_height = 30
        bullet.glow_color = (255, 245, 225)
        bullet.glow_padding = 6
        bullet.brake_delay = _FRENZY_SKULL_BRAKE_DELAY + i * 3
        bullet.brake = _FRENZY_SKULL_BRAKE
        bullet.brake_floor = _FRENZY_SKULL_FLOOR
        bullet_manager.add_enemy_bullet(bullet)


def _frenzy_drop_tnt(boss, x, y):
    """在移动路径上留下 TNT 标记：延迟爆炸并产生向四周扩散的冲击弹。"""
    boss.frenzy_tnts.append({
        "x": x,
        "y": y + 10,
        "age": 0,
        "delay": _FRENZY_TNT_DELAY,
        "seed": random.uniform(0.0, math.tau),
    })


def _frenzy_explode_tnt(boss, bullet_manager, tnt):
    """TNT 爆炸：冲击弹圆环外扩，脱离后沿切线飞散 + 视觉爆炸环。"""
    x, y = tnt["x"], tnt["y"]
    seed = tnt["seed"]
    for i in range(_FRENZY_SHOCK_COUNT):
        ang = i * math.tau / _FRENZY_SHOCK_COUNT + seed * 0.3
        bullet = create_bullet_angle(x, y, ang, 0.0, Bullet.TYPE_CIRCLE,
                                     radius=3.0, color=(255, 150, 60), lifetime=320)
        bullet.manager = bullet_manager
        bullet.orbit_center = (x, y)
        bullet.orbit_radius = _FRENZY_SHOCK_RING
        bullet.orbit_angle = ang
        bullet.orbit_grow = _FRENZY_SHOCK_GROW
        bullet.orbit_break = _FRENZY_SHOCK_BREAK
        bullet.orbit_break_speed = _FRENZY_SHOCK_SPEED
        bullet_manager.add_enemy_bullet(bullet)
    boss.frenzy_shockwaves.append({
        "x": x, "y": y, "age": 0, "max_age": 30,
        "start_r": 10, "end_r": 78, "color": (255, 178, 90), "width": 3,
    })


def _frenzy_update_tnts(boss, bullet_manager, timer):
    """TNT 引信推进；到期后爆炸。"""
    for tnt in boss.frenzy_tnts[:]:
        tnt["age"] += 1
        if tnt["age"] >= tnt["delay"]:
            boss.frenzy_tnts.remove(tnt)
            _frenzy_explode_tnt(boss, bullet_manager, tnt)


def _frenzy_do_turn(boss, bullet_manager, new_dir):
    """折返：改变方向、释放一排 Wither Skull、并在折返点留一颗 TNT。"""
    state = boss.frenzy_state
    state["dir"] = new_dir
    state["crossings"] += 1
    _frenzy_skull_row(boss, bullet_manager, new_dir)
    _frenzy_drop_tnt(boss, boss.x, boss.y)


def _frenzy_check_turn(boss, bullet_manager, timer):
    state = boss.frenzy_state
    edge_l = _FRENZY_EDGE_MARGIN
    edge_r = cfg.BATTLE_AREA_WIDTH - _FRENZY_EDGE_MARGIN
    if state["dir"] > 0 and boss.x >= edge_r:
        boss.x = edge_r
        _frenzy_do_turn(boss, bullet_manager, -1.0)
    elif state["dir"] < 0 and boss.x <= edge_l:
        boss.x = edge_l
        _frenzy_do_turn(boss, bullet_manager, 1.0)


def _frenzy_dash_update(boss, bullet_manager, timer):
    """前半：屏幕上方高速横向穿梭 + 折返释放骷髅 + 路径上留 TNT。"""
    state = boss.frenzy_state
    if state["setup"] > 0:
        state["setup"] -= 1
        if state["setup"] == 0:
            boss.x = _FRENZY_EDGE_MARGIN
            boss.y = _FRENZY_TOP_Y
            boss.move_to(boss.x, boss.y)
        return
    boss.y = _FRENZY_TOP_Y + math.sin(timer * 0.021) * 4
    boss.x += state["dir"] * _FRENZY_DASH_SPEED
    boss.move_to(boss.x, boss.y)
    _frenzy_check_turn(boss, bullet_manager, timer)
    state["tnt_timer"] += 1
    if state["tnt_timer"] >= _FRENZY_TNT_INTERVAL:
        state["tnt_timer"] = 0
        _frenzy_drop_tnt(boss, boss.x, boss.y)
    if state["crossings"] >= _FRENZY_TURN_CROSSINGS:
        _frenzy_enter_frenzy(boss, timer)


def _frenzy_enter_frenzy(boss, timer):
    """完成数次穿梭后进入 Frenzy：速度提高、冲击波、两颗 power crystal 落下。"""
    state = boss.frenzy_state
    state["mode"] = "frenzy"
    state["frenzy_timer"] = 0
    state["tnt_timer"] = 0
    state["dir"] = -state["dir"]
    # 从上方中央缓慢落下两颗 power crystal
    boss.frenzy_crystals = []
    cx = cfg.BATTLE_AREA_WIDTH / 2
    for i in range(_FRENZY_CRYSTAL_COUNT):
        boss.frenzy_crystals.append({
            "x": cx + (i - (_FRENZY_CRYSTAL_COUNT - 1) / 2) * 30,
            "y": -16 - i * 26,
            "vy": 0.0,
            "sway_phase": random.uniform(0.0, math.tau),
            "collected": False,
        })


def _frenzy_big_shockwave(boss, bullet_manager):
    """大型圆形冲击波：以 Maxor 当前位置为中心，弹环高速外扩后飞散。"""
    x, y = boss.x, boss.y
    base = random.uniform(0.0, math.tau)
    for i in range(_FRENZY_BIG_SHOCK_COUNT):
        ang = base + i * math.tau / _FRENZY_BIG_SHOCK_COUNT
        bullet = create_bullet_angle(x, y, ang, 0.0, Bullet.TYPE_CIRCLE,
                                     radius=3.5, color=(255, 110, 60), lifetime=460)
        bullet.manager = bullet_manager
        bullet.orbit_center = (x, y)
        bullet.orbit_radius = 14
        bullet.orbit_angle = ang
        bullet.orbit_grow = _FRENZY_BIG_SHOCK_GROW
        bullet.orbit_break = _FRENZY_BIG_SHOCK_BREAK
        bullet.orbit_break_speed = _FRENZY_BIG_SHOCK_SPEED
        bullet_manager.add_enemy_bullet(bullet)
    boss.frenzy_shockwaves.append({
        "x": x, "y": y, "age": 0, "max_age": 68,
        "start_r": 18, "end_r": 220, "color": (255, 90, 50), "width": 4,
    })


def _frenzy_update_crystals(boss, player_x, player_y, timer):
    """power crystal 下落与拾取判定；掉出屏幕底部则重置回上方中央。"""
    state = boss.frenzy_state
    for crystal in boss.frenzy_crystals:
        if crystal["collected"]:
            continue
        crystal["vy"] = min(_FRENZY_CRYSTAL_FALL, crystal["vy"] + _FRENZY_CRYSTAL_ACCEL)
        crystal["y"] += crystal["vy"]
        crystal["x"] += math.sin(timer * 0.02 + crystal["sway_phase"]) * 0.4
        if crystal["y"] > cfg.BATTLE_AREA_HEIGHT + 30:
            crystal["y"] = -12
            crystal["vy"] = 0.0
            crystal["x"] = cfg.BATTLE_AREA_WIDTH / 2 + random.uniform(-34, 34)
        if math.hypot(crystal["x"] - player_x, crystal["y"] - player_y) <= _FRENZY_CRYSTAL_RADIUS:
            crystal["collected"] = True
            state["crystals_collected"] += 1
            boss.frenzy_shockwaves.append({
                "x": crystal["x"], "y": crystal["y"], "age": 0, "max_age": 28,
                "start_r": 6, "end_r": 44, "color": (160, 240, 255), "width": 2,
            })


def _frenzy_frenzy_update(boss, bullet_manager, timer, player_x, player_y):
    """Frenzy：明显提速 + 大型冲击波 + 继续骷髅 / TNT，等待收集两颗水晶。"""
    state = boss.frenzy_state
    state["frenzy_timer"] += 1
    t = state["frenzy_timer"]
    boss.y = _FRENZY_TOP_Y + math.sin(timer * 0.025) * 4
    boss.x += state["dir"] * _FRENZY_RUSH_SPEED
    boss.move_to(boss.x, boss.y)
    _frenzy_check_turn(boss, bullet_manager, timer)

    if t % _FRENZY_BIG_SHOCK_INTERVAL == 0:
        _frenzy_big_shockwave(boss, bullet_manager)

    state["tnt_timer"] += 1
    if state["tnt_timer"] >= 22:
        state["tnt_timer"] = 0
        _frenzy_drop_tnt(boss, boss.x, boss.y)

    _frenzy_update_crystals(boss, player_x, player_y, timer)
    if state["crystals_collected"] >= _FRENZY_CRYSTAL_COUNT:
        boss.frenzy_tnts = []          # 回中演出：清空未爆的 TNT，保持激光瞬间干净
        state["mode"] = "reveal"
        state["reveal_timer"] = 0
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 112)


def _frenzy_reveal_update(boss, bullet_manager, timer):
    """收集完成：回到中央，红色激光命中后立即转入螺旋终幕。"""
    state = boss.frenzy_state
    state["reveal_timer"] += 1
    t = state["reveal_timer"]
    boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 112)
    # 回中后红色激光自上而下命中：解封瞬间立即开始疯狂螺旋（激光本体继续绘制）
    if t == _FRENZY_REVEAL_LASER_AT:
        boss.frenzy_laser = {
            "x": cfg.BATTLE_AREA_WIDTH / 2,
            "y": boss.y,
            "top": 8,
            "age": 0,
            "max_age": _FRENZY_LASER_DURATION,
        }
        _frenzy_update_laser(boss, bullet_manager)
        state["mode"] = "spiral"
        state["spiral_timer"] = 0


def _frenzy_update_laser(boss, bullet_manager):
    """推进红色激光：命中瞬间解除无敌、伤害×5；到期后清除激光本体。"""
    laser = boss.frenzy_laser
    if laser is None:
        return
    laser["age"] += 1
    state = boss.frenzy_state
    if laser["age"] == 1:
        # 命中瞬间：解除无敌、伤害翻 5 倍
        state["laser_fired"] = True
        boss.invincible = False
        boss.invincible_timer = 0
        boss.resistance = boss.spell_resistance * _FRENZY_DAMAGE_MULT
        boss.frenzy_shockwaves.append({
            "x": laser["x"], "y": laser["y"], "age": 0, "max_age": 42,
            "start_r": 10, "end_r": 120, "color": (255, 60, 45), "width": 3,
        })
        # 竖直红色激光本体（带碰撞判定，玩家需避开中央通道）
        length = max(4.0, laser["y"] - laser["top"])
        beam = create_bullet_angle(laser["x"], laser["top"], math.pi / 2, 0.0,
                                   Bullet.TYPE_BEAM, radius=3.0,
                                   color=(255, 70, 50), lifetime=laser["max_age"])
        beam.manager = bullet_manager
        beam.angle = math.pi / 2
        beam.beam_length = length
        beam.sprite_slot = "s12"
        bullet_manager.add_enemy_bullet(beam)
    if laser["age"] >= laser["max_age"]:
        boss.frenzy_laser = None


def _frenzy_spiral_update(boss, bullet_manager, timer, player_x, player_y):
    """破防终幕：疯狂螺旋弹幕 + 自机狙大玉，直到被击破。"""
    state = boss.frenzy_state
    state["spiral_timer"] += 1
    t = state["spiral_timer"]
    boss.x = cfg.BATTLE_AREA_WIDTH / 2 + math.sin(t * 0.011) * 12
    boss.y = 112 + math.sin(t * 0.018) * 6
    boss.move_to(boss.x, boss.y)
    # 疯狂螺旋：四臂高速旋转，方向周期性反转
    if t % 6 == 0:
        spin = 1.0 if (t // 240) % 2 == 0 else -1.0
        base = t * 0.085 * spin
        for arm in range(4):
            ang = base + arm * math.tau / 4
            bullet = create_bullet_angle(boss.x, boss.y, ang, 2.7,
                                         Bullet.TYPE_RICE, radius=2.4,
                                         color=(255, 150, 80) if arm % 2 else (255, 214, 150))
            bullet.manager = bullet_manager
            bullet.turn_rate = 0.013 * spin * (1 if arm % 2 == 0 else -1)
            bullet_manager.add_enemy_bullet(bullet)
    # 自机狙大玉：保持路线压力
    if t % 68 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for offset in (-0.15, 0.15):
            bullet = create_bullet_angle(boss.x, boss.y, base + offset, 3.5,
                                         Bullet.TYPE_BIG, radius=4.0, color=(255, 90, 60))
            bullet_manager.add_enemy_bullet(bullet)


def _frenzy_update_shockwaves(boss):
    """推进视觉冲击环寿命。"""
    for wave in boss.frenzy_shockwaves[:]:
        wave["age"] += 1
        if wave["age"] >= wave["max_age"]:
            boss.frenzy_shockwaves.remove(wave)


def spell_maxor_frenzy(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """Phase1「Maxor's Frenzy」：Maxor 的高速领域压制。

    前半部分 Maxor 无法被攻击：在屏幕上方高速横向穿梭，每次折返释放一排快速
    Wither Skull（沿固定角度穿过屏幕并在飞出一段距离后逐渐减速），同时周期性
    在自己的移动路径上留下延迟爆炸的 TNT（爆炸产生向四周扩散的冲击弹）。
    完成数次穿梭后进入 Frenzy：移动速度明显提高，并周期性以自身位置为中心释放
    大型圆形冲击波；此时从上方中央缓慢落下两颗 power crystal，全部收集后 Maxor
    回到中央，被一道竖直红色激光解除无敌并进入伤害×5 的破防状态，同时疯狂释放
    螺旋弹幕，直到被击破为止。
    """
    if getattr(boss, "frenzy_state", None) is None:
        _frenzy_init(boss)
    state = boss.frenzy_state
    mode = state["mode"]

    # 前半 / 回中阶段全程无敌，直到红色激光命中才解除
    if mode in ("dash", "frenzy", "reveal") and not state.get("laser_fired", False):
        boss.invincible = True
        boss.invincible_timer = 0

    if mode == "dash":
        _frenzy_dash_update(boss, bullet_manager, timer)
    elif mode == "frenzy":
        _frenzy_frenzy_update(boss, bullet_manager, timer, player_x, player_y)
    elif mode == "reveal":
        _frenzy_reveal_update(boss, bullet_manager, timer)
    elif mode == "spiral":
        _frenzy_spiral_update(boss, bullet_manager, timer, player_x, player_y)

    # 红色激光推进（命中瞬间解封 + 到期清除）
    _frenzy_update_laser(boss, bullet_manager)
    # TNT 引信推进与爆炸
    _frenzy_update_tnts(boss, bullet_manager, timer)
    # 冲击波视觉环推进
    _frenzy_update_shockwaves(boss)


def _storm_giga_init(boss):
    """开符初始化：4 根方形避雷柱 + 阶段状态机（normal -> charge -> strike -> frenzy）。"""
    boss.storm_giga = {
        "loop": 1,
        "sub": "normal",
        "sub_timer": 0,
        "pillars": [{"x": x, "y": y, "alive": True}
                    for x, y in STORM_GIGA_PILLAR_POSITIONS],
        "safe_radius": STORM_GIGA_PILLAR_SAFE_RADIUS,
        "warnings": [],             # 普通雷击预警（绘制用，无判定）
        "lightning_wave": [],       # 本轮普通落雷的车道
        "last_refuge": 0,           # 玩家上次躲避雷电的柱子索引
        "target_pillar": None,      # 蓄力时被 Storm 破坏的柱子索引
        "pillar_flash": 0,          # 柱子被破坏的电光闪光倒计时
        "strike_active": False,     # 全屏雷击判定窗口（由战斗循环消费）
        "strike_checked": False,
        "strike_bolts": [],         # 全屏雷击视觉用的锯齿闪电
        "frenzy_goal": 0,           # 狂暴结束（失去半血）时的血量目标
    }
    boss.move_speed = 5.0


def _storm_giga_live_pillars(giga):
    return [i for i, p in enumerate(giga["pillars"]) if p["alive"]]


def _storm_giga_upper_pillars(giga):
    """Storm 只会停在上方两根柱子（索引 0/1）——下方两根是玩家最后的避雷区。"""
    return [i for i in (0, 1) if giga["pillars"][i]["alive"]]


def _storm_giga_lightning_strike(bullet_manager, x):
    """普通雷击：纵向短暂判定光束。"""
    top = 12.0
    bottom = cfg.BATTLE_AREA_HEIGHT - 8.0
    beam = create_bullet_angle(x, top, math.pi / 2, 0.0,
                               Bullet.TYPE_BEAM, radius=3.0,
                               color=(140, 230, 255), lifetime=24)
    beam.manager = bullet_manager
    beam.angle = math.pi / 2
    beam.beam_length = bottom - top
    beam.sprite_slot = "s12"
    bullet_manager.add_enemy_bullet(beam)


def _storm_giga_normal(boss, bullet_manager, player_x, player_y):
    """普通雷击阶段：Storm 无敌，持续落雷与弹幕迫使玩家移动。"""
    giga = boss.storm_giga
    t = giga["sub_timer"]

    if t % 90 == 0:
        boss.move_to(_clamp_x(boss.x + random.choice((-150, 150))), 104)

    # 弹幕（削弱版）：自机狙箭雨 + 旋转电环 + 侧翼刀弹
    if t % 22 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for offset in (-0.09, 0.09):
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, base + offset, 3.0,
                                     Bullet.TYPE_ARROW, radius=3, color=(120, 200, 255)))
    if t % 48 == 0:
        for i in range(14):
            angle = -t * 0.04 + i * math.tau / 14
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, angle, 1.8,
                                     Bullet.TYPE_CIRCLE, radius=3, color=(90, 190, 255)))
    if t % 80 == 0:
        for i in range(3):
            angle = t * 0.06 + i * math.tau / 3
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, angle, 2.2,
                                     Bullet.TYPE_KNIFE, radius=2.5, color=(160, 220, 255)))

    # 普通雷击（削弱版）：两条车道、更长间隔，随后落雷光束
    for warning in giga["warnings"]:
        warning["age"] += 1
    giga["warnings"] = [w for w in giga["warnings"] if w["age"] < w["max_age"]]
    cycle = t % 130
    if cycle == 0:
        lanes = random.sample([88, 200, 310, 420, 528], 2)
        giga["lightning_wave"] = lanes
        for x in lanes:
            giga["warnings"].append({"x": x, "age": 0, "max_age": 70})
    elif cycle == 70:
        for x in giga["lightning_wave"]:
            _storm_giga_lightning_strike(bullet_manager, x)
        giga["lightning_wave"] = []

    # 记录玩家上次躲避雷电的柱子（Storm 只会停在上方两根柱子上）
    upper = _storm_giga_upper_pillars(giga)
    if upper:
        giga["last_refuge"] = min(
            upper, key=lambda i: (giga["pillars"][i]["x"] - player_x) ** 2
                                 + (giga["pillars"][i]["y"] - player_y) ** 2)

    if t >= STORM_GIGA_NORMAL_DURATION:
        giga["sub"] = "charge"
        giga["sub_timer"] = 0
        giga["warnings"] = []
        giga["lightning_wave"] = []
        # 蓄力目标：玩家最近的上方存活柱（Storm 只停在上方两根柱子上）
        upper = _storm_giga_upper_pillars(giga)
        target = giga["last_refuge"]
        if target not in upper:
            target = (min(upper, key=lambda i: (giga["pillars"][i]["x"] - player_x) ** 2
                                               + (giga["pillars"][i]["y"] - player_y) ** 2)
                      if upper else None)
        giga["target_pillar"] = target


def _storm_giga_charge(boss, bullet_manager, player_x, player_y):
    """Giga Lightning 蓄力：Storm 逼近并破坏上方避雷柱，蓄力期间不释放弹幕。"""
    giga = boss.storm_giga
    t = giga["sub_timer"]
    if giga["pillar_flash"] > 0:
        giga["pillar_flash"] -= 1

    target = giga.get("target_pillar")
    if target is None:
        giga["sub"] = "strike"
        giga["sub_timer"] = 0
        _storm_giga_begin_strike(giga)
        return
    pillar = giga["pillars"][target]

    # Storm 缓缓逼近玩家上次躲避的柱子
    boss.move_to(pillar["x"], max(96, pillar["y"] - 120))

    if t == STORM_GIGA_PILLAR_DESTROY_AT:
        # 命中时刻：柱子被破坏，其安全区失效
        pillar["alive"] = False
        giga["pillar_flash"] = STORM_GIGA_PILLAR_FLASH
        giga["warnings"] = []
        for _ in range(10):
            ang = random.uniform(0, math.tau)
            spd = random.uniform(1.2, 3.0)
            f = create_bullet_angle(pillar["x"], pillar["y"] - 60, ang, spd,
                                    Bullet.TYPE_CIRCLE, radius=2.5, color=(210, 240, 255))
            f.harmless = True
            f.lifetime = 20
            _add(bullet_manager, f)

    if t >= STORM_GIGA_CHARGE_DURATION:
        giga["sub"] = "strike"
        giga["sub_timer"] = 0
        _storm_giga_begin_strike(giga)


def _storm_giga_make_bolt():
    """生成一条自上而下的锯齿闪电（仅视觉）。"""
    x = random.uniform(30, cfg.BATTLE_AREA_WIDTH - 30)
    y = 4.0
    pts = [(x, y)]
    while y < cfg.BATTLE_AREA_HEIGHT - 8:
        y += random.uniform(26, 60)
        x += random.uniform(-34, 34)
        x = max(6, min(cfg.BATTLE_AREA_WIDTH - 6, x))
        pts.append((x, min(y, cfg.BATTLE_AREA_HEIGHT - 8)))
    return pts


def _storm_giga_begin_strike(giga):
    """进入全屏雷击：打开玩家判定窗口并生成视觉闪电。"""
    giga["strike_active"] = True
    giga["strike_checked"] = False
    giga["strike_bolts"] = [_storm_giga_make_bolt() for _ in range(8)]


def _storm_giga_strike(boss, bullet_manager, player_x, player_y):
    """全屏毁灭性雷击：表现数帧后进入狂暴状态。"""
    giga = boss.storm_giga
    t = giga["sub_timer"]
    if t >= STORM_GIGA_STRIKE_DURATION:
        giga["strike_active"] = False
        giga["sub"] = "frenzy"
        giga["sub_timer"] = 0
        # 狂暴开始：解封可被攻击，受伤翻 4 倍；目标为失去当前一半血量
        # （第一轮 100%→50% 结束回普通雷击，第二轮 50%→0 击败）
        giga["frenzy_goal"] = max(0, boss.hp - boss.max_hp * 0.5)


def _storm_giga_frenzy(boss, bullet_manager, player_x, player_y):
    """狂暴状态（削弱版）：Storm 放射弹幕但可被攻击，受伤翻 4 倍。"""
    giga = boss.storm_giga
    t = giga["sub_timer"]

    boss.invincible = False
    boss.invincible_timer = 0
    boss.resistance = boss.spell_resistance * STORM_GIGA_FRENZY_DAMAGE_MULT

    if t % 90 == 0:
        boss.move_to(_clamp_x(random.choice((70, 170, 290, 400, 506))), 96)

    if t % 8 == 0:
        base = random.uniform(0, math.tau)
        for i in range(8):
            ang = base + i * math.tau / 8
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, ang, random.uniform(1.4, 2.2),
                                     Bullet.TYPE_CIRCLE, radius=2.5, color=(130, 210, 255)))
    if t % 20 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for offset in (-0.15, 0.15):
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, base + offset, 3.0,
                                     Bullet.TYPE_KNIFE, radius=2.5, color=(170, 225, 255)))
    if t % 52 == 0:
        for i in range(14):
            angle = t * 0.06 + i * math.tau / 14
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, angle, 1.8,
                                     Bullet.TYPE_ARROW, radius=3, color=(90, 190, 255)))
    if t % 150 == 0:
        for i in range(6):
            ang = random.uniform(0, math.tau)
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, ang, 2.6,
                                     Bullet.TYPE_BIG, radius=4, color=(200, 240, 255)))

    # 失去一半血量后：第一轮结束回普通雷击；第二轮打空血条由 take_damage 结算败北
    if boss.hp <= giga["frenzy_goal"]:
        if giga["loop"] == 1:
            giga["loop"] = 2
            giga["sub"] = "normal"
            giga["sub_timer"] = 0
            giga["warnings"] = []
            giga["lightning_wave"] = []
            giga["target_pillar"] = None
            boss.invincible = True
            boss.invincible_timer = 0
            boss.resistance = boss.spell_resistance
            bullet_manager.cancel_all_enemy_bullets()


def spell_storm_giga(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """雷符「Giga Lightning」：四柱避雷、蓄力破坏、全屏雷击与 4 倍伤害狂暴循环。"""
    if getattr(boss, "storm_giga", None) is None:
        _storm_giga_init(boss)
    giga = boss.storm_giga
    giga["sub_timer"] += 1

    if giga["sub"] == "normal":
        boss.invincible = True
        boss.invincible_timer = 0
        boss.resistance = boss.spell_resistance
        _storm_giga_normal(boss, bullet_manager, player_x, player_y)
    elif giga["sub"] == "charge":
        boss.invincible = True
        boss.invincible_timer = 0
        boss.resistance = boss.spell_resistance
        _storm_giga_charge(boss, bullet_manager, player_x, player_y)
    elif giga["sub"] == "strike":
        boss.invincible = True
        boss.invincible_timer = 0
        boss.resistance = boss.spell_resistance
        _storm_giga_strike(boss, bullet_manager, player_x, player_y)
    elif giga["sub"] == "frenzy":
        _storm_giga_frenzy(boss, bullet_manager, player_x, player_y)


def spell_necron_withering(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """凋符「Necron's Withering」：黑紫凋零头骨弹幕环绕并向玩家收缩。"""
    if timer % 84 == 0:
        boss.move_to(_clamp_x(player_x + random.choice((-60, 60))), 116)
    if timer % 22 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for i in range(5):
            offset = (i - 2) * 0.16
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, base + offset, 2.9,
                                     Bullet.TYPE_CIRCLE, radius=3, color=(180, 80, 235)))
    if timer % 41 == 0:
        for i in range(20):
            angle = timer * 0.038 + i * math.tau / 20
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, angle, 1.7,
                                     Bullet.TYPE_RICE, radius=2.5, color=(120, 50, 190)))
    if timer % 66 == 0:
        for side in (-1, 1):
            x = _clamp_x(boss.x + side * 88)
            _add(bullet_manager,
                 create_bullet_angle(x, boss.y, math.pi / 2, 2.2,
                                     Bullet.TYPE_KNIFE, radius=2.5, color=(210, 110, 250)))


def spell_necron_apocalypse(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """终符「Necron's Apocalypse」：最终连击，凋零环、刀扇与自机狙三线并行。"""
    if timer % 68 == 0:
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 110)
    if timer % 18 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for offset in (-0.34, -0.12, 0.12, 0.34):
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, base + offset, 3.1,
                                     Bullet.TYPE_CIRCLE, radius=3, color=(200, 90, 255)))
    if timer % 32 == 0:
        for i in range(24):
            angle = -timer * 0.055 + i * math.tau / 24
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, angle, 1.8,
                                     Bullet.TYPE_KNIFE, radius=2.5, color=(160, 60, 230)))
    if timer % 53 == 0:
        for i in range(12):
            angle = timer * 0.043 + i * math.tau / 12
            _add(bullet_manager,
                 create_bullet_angle(boss.x, boss.y, angle, 2.2,
                                     Bullet.TYPE_BIG, radius=4, color=(130, 40, 210)))


# ---------------------------------------------------------------------------
# Stage 5：BOSS RUSH 状态机
# ---------------------------------------------------------------------------

class Stage5_WitherLords(Stage):
    """Stage 5: The Catacombs - The Wither Lords（BOSS RUSH）"""

    BOSS_ORDER = ("watcher", "professor", "thorn", "livid",
                  "maxor", "storm", "goldor", "necron")

    def __init__(self):
        super().__init__(5, "凋零之厅 ~ The Wither Lords",
                         bg_color=(5, 5, 12))
        # 暂复用四面地下墓穴背景，后续可替换五面专属贴图。
        self.background = Pseudo3DFloor(
            cfg.STAGE5_FLOOR, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT,
            bg_color=self.bg_color,
            wall_texture_path=cfg.STAGE5_WALL,
            horizon_ratio=0.34, tunnel_width=1.7,
            far_opening=30, floor_stretch=3.4, wall_stretch=1.0,
            wall_align_to_floor=True)
        self.title_path = cfg.STAGE5_TITLE
        self.music_path = cfg.STAGE5_MUSIC_START
        self.music_loop_path = cfg.STAGE5_MUSIC_LOOP
        self.boss_music_start_path = cfg.STAGE5_BOSS_MUSIC_START
        self.boss_music_loop_path = cfg.STAGE5_BOSS_MUSIC_LOOP
        self.music_name = cfg.STAGE5_MUSIC_NAME
        self.boss_music_name = cfg.STAGE5_BOSS_MUSIC_NAME
        self.mid_boss_music_path = None
        self.background_darkness = 158
        self.phase = "opening"

        self.current_boss_id = None
        self.current_boss_index = -1
        self._opening_started = False
        self._boss_defeated_handled = False
        self._pending_dialogue_action = None

        self.boss_display_names = {
            "professor": "The Professor",
            "thorn": "Thorn",
            "livid": "Livid",
            "maxor": "Maxor",
            "storm": "Storm",
            "goldor": "Goldor",
            "necron": "Necron",
        }

    # ------------------------------------------------------------------
    # 基础接口（本面无道中杂鱼）
    # ------------------------------------------------------------------
    def setup_waves(self):
        pass

    def setup_mid_boss(self):
        pass

    def setup_boss(self):
        pass

    def get_active_enemies(self):
        """Professor 实验符卡中的小 guardian 可作为普通敌人被自机与 Homing 攻击。"""
        enemies = super().get_active_enemies()
        boss = self.boss
        if boss is not None and boss.alive and boss.combat_enabled:
            enemies.extend(
                guardian for guardian in getattr(boss, "professor_guardians", [])
                if guardian.alive)
            for clone in getattr(boss, "livid_clones", []):
                if clone.alive:
                    enemies.append(clone)
        return enemies

    @property
    def player_input_locked(self):
        """终端破解 / 中央演出期间锁定自机输入。"""
        boss = self.boss
        if boss is None:
            return False
        state = getattr(boss, "goldor_terminal", None)
        if state is None:
            return False
        return bool(state.get("input_locked"))

    def constrain_player(self, x, y):
        """机械符「Terminal Pursuit」：把自机约束在方形环路上；其它情况原样返回。"""
        boss = self.boss
        if boss is None:
            return x, y
        state = getattr(boss, "goldor_terminal", None)
        if state is None or state.get("spell_done"):
            return x, y
        return _gt_clamp_player(x, y, state)

    # ------------------------------------------------------------------
    # Boss 工厂
    # ------------------------------------------------------------------
    def _make_watcher(self):
        boss = Boss(
            "The Watcher", hp=WATCHER_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
            size=26, color=(90, 220, 230),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_min_duration=60,
            hp_bar_inset=16,
            sprite_path=cfg.STAGE5_WATCHER_BOSS_SPRITE,
            sprite_scale=2.4)
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 112)
        boss.add_spell_card(SpellCard(
            "展符「Undead Exhibition」", spell_watcher_undead_exhibition,
            hp_threshold=1.0, end_hp_threshold=0.0, bg_style="watcher"))
        return boss

    def _make_professor(self):
        boss = Boss(
            "The Professor", hp=PROFESSOR_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
            size=24, color=(150, 230, 120),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_min_duration=170,
            non_spell_func=_non_spell_professor,
            hp_bar_inset=16,
            sprite_path=cfg.STAGE5_PROFESSOR_BOSS_SPRITE,
            sprite_scale=2.2)
        boss.bonus_drops = ["overflux_power_orb"]
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 108)
        boss.add_spell_card(SpellCard(
            "实验「Professor's Experiment」", spell_professor_experiment,
            hp_threshold=0.5, end_hp_threshold=0.0, bg_style="professor"))
        return boss

    def _make_thorn(self):
        boss = Boss(
            "Thorn", hp=THORN_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
            size=24, color=(190, 110, 255),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_min_duration=170,
            non_spell_func=_non_spell_thorn,
            hp_bar_inset=16,
            sprite_path=cfg.STAGE5_THORN_BOSS_SPRITE,
            sprite_scale=2.2)
        boss.bonus_drops = ["overflux_power_orb"]
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 108)
        boss.add_spell_card(SpellCard(
            "灵符「Spirit Zoo」", spell_thorn_spirit_zoo,
            hp_threshold=0.5, end_hp_threshold=0.0, bg_style="thorn",
            time_spell=True))
        return boss

    def _make_livid(self):
        boss = Boss(
            "Livid", hp=LIVID_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
            size=24, color=(80, 210, 240),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_min_duration=170,
            non_spell_func=_non_spell_livid,
            hp_bar_inset=16,
            sprite_path=cfg.STAGE5_LIVID_BOSS_SPRITE,
            sprite_scale=2.2)
        boss.bonus_drops = ["overflux_power_orb"]
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 108)
        boss.add_spell_card(SpellCard(
            "影符「八重存在」", spell_livid_eightfold_existence,
            hp_threshold=0.5, end_hp_threshold=0.0, bg_style="livid"))
        return boss

    def _make_maxor(self):
        boss = Boss(
            "Maxor", hp=MAXOR_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
            size=26, color=(255, 130, 60),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_min_duration=1,
            hp_bar_inset=16,
            sprite_path=cfg.STAGE5_MAXOR_BOSS_SPRITE,
            sprite_scale=2.3)
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 108)
        boss.add_spell_card(SpellCard(
            "Phase1「Maxor's Frenzy」", spell_maxor_frenzy,
            hp_threshold=1.0, end_hp_threshold=0.0, bg_style="maxor"))
        return boss

    def _make_storm(self):
        boss = Boss(
            "Storm", hp=STORM_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
            size=26, color=(120, 200, 255),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_min_duration=1,
            hp_bar_inset=16,
            sprite_path=cfg.STAGE5_STORM_BOSS_SPRITE,
            sprite_scale=2.3)
        boss.bonus_drops = ["revive_stone"]
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 108)
        boss.add_spell_card(SpellCard(
            "雷符「Giga Lightning」", spell_storm_giga,
            hp_threshold=1.0, end_hp_threshold=0.0, bg_style="storm"))
        return boss

    def _make_goldor(self):
        boss = Boss(
            "Goldor", hp=GOLDOR_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
            size=27, color=(255, 205, 90),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_min_duration=1,
            hp_bar_inset=16,
            sprite_path=cfg.STAGE5_GOLDOR_BOSS_SPRITE,
            sprite_scale=2.3)
        boss.bonus_drops = ["overflux_power_orb"]
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 108)
        boss.add_spell_card(SpellCard(
            "机械符「Terminal Pursuit」", spell_goldor_terminal_pursuit,
            hp_threshold=1.0, end_hp_threshold=0.66,
            bg_style="stone", direct_next=True, time_spell=True))
        boss.add_spell_card(SpellCard(
            "Phase3「Infinite Rage」", spell_goldor_infinite_rage,
            hp_threshold=1.0, end_hp_threshold=0.0,
            bg_style="goldor", direct_next=True))
        return boss

    def _make_necron(self):
        boss = Boss(
            "Necron", hp=NECRON_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
            size=28, color=(190, 60, 235),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_min_duration=1,
            hp_bar_inset=16,
            sprite_path=cfg.STAGE5_NECRON_BOSS_SPRITE,
            sprite_scale=2.3)
        boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 108)
        boss.add_spell_card(SpellCard(
            "凋符「Necron's Withering」", spell_necron_withering,
            hp_threshold=0.66, end_hp_threshold=0.33,
            bg_style="necron", direct_next=True))
        boss.add_spell_card(SpellCard(
            "终符「Necron's Apocalypse」", spell_necron_apocalypse,
            hp_threshold=0.33, end_hp_threshold=0.0, bg_style="soul"))
        return boss

    def _build_boss(self, boss_id):
        factory = {
            "watcher": self._make_watcher,
            "professor": self._make_professor,
            "thorn": self._make_thorn,
            "livid": self._make_livid,
            "maxor": self._make_maxor,
            "storm": self._make_storm,
            "goldor": self._make_goldor,
            "necron": self._make_necron,
        }[boss_id]
        boss = factory()
        # 掉落表分组：五面前置三连（Professor/Thorn/Livid）为道中Boss，
        # 四凋零领主为关底Boss；所有五面 Boss 都属于 stage5_boss（任意Boss）。
        if boss_id == "watcher":
            boss.drop_group = ["stage5_boss"]
        elif boss_id in ("professor", "thorn", "livid"):
            groups = ["stage5_boss", "MidBoss"]
            if boss_id == "thorn":
                groups.append("stage5_midboss_thorn")
            elif boss_id == "livid":
                groups.append("stage5_midboss_livid")
            boss.drop_group = groups
        else:
            boss.drop_group = ["stage5_boss", "stage5_final_boss"]
        return boss

    def _set_boss_id(self, boss_id):
        self.current_boss_id = boss_id
        self.current_boss_index = self.BOSS_ORDER.index(boss_id)

    def _spawn_boss_for_dialogue(self, boss_id):
        self._set_boss_id(boss_id)
        self.boss = self._build_boss(boss_id)
        self.boss.hold_combat()
        self._boss_defeated_handled = False

    def _arm_current_boss_normal(self):
        """前置 Boss：对话结束后按普通流程入场（非符 -> 符卡）。"""
        boss = self.boss
        if boss is None:
            return
        boss.arm_combat(BOSS_COMBAT_DELAY)
        # 保持普通 entry：Boss 类会自动先走非符，血量到达阈值再开符。
        self.phase = "boss"
        self._boss_defeated_handled = False

    def skip_to_opening_boss(self, boss_id):
        """Watcher 开场对话中按 1/2/3 快捷进入前置 Boss 战。"""
        if (self.phase != "dialogue" or self.dialogue_is_defeat
                or self._pending_dialogue_action != "watcher"
                or boss_id not in ("professor", "thorn", "livid")):
            return False
        self._spawn_boss_for_dialogue(boss_id)
        self._arm_current_boss_normal()
        self._on_boss_combat_start()
        self.dialogue_active = False
        self._pending_dialogue_action = boss_id
        return True

    def _force_current_boss_spell(self):
        """Watcher / Wither Lords：跳过非符，直接展开第一张符卡。"""
        boss = self.boss
        if boss is None:
            return
        boss.arm_combat(0)
        boss.entering = False
        boss.entry_timer = 0
        if boss.spell_cards:
            boss.current_spell_idx = 0
            boss._start_spell(boss.spell_cards[0])
        self.phase = "boss"
        self._boss_defeated_handled = False

    def skip_to_spell_card(self, boss_id, spell_idx):
        """调试：五面战前对话中直接进入指定 Boss 的指定符卡（spell_idx 从 0 起）。"""
        if self.phase != "dialogue" or self.dialogue_is_defeat:
            return False
        self._spawn_boss_for_dialogue(boss_id)
        boss = self.boss
        if not (0 <= spell_idx < len(boss.spell_cards)):
            return False
        boss.arm_combat(0)
        boss.entering = False
        boss.entry_timer = 0
        boss.current_spell_idx = spell_idx
        boss._start_spell(boss.spell_cards[spell_idx])
        self.phase = "boss"
        self._boss_defeated_handled = False
        self._pending_dialogue_action = boss_id
        self.dialogue_active = False
        self._on_boss_combat_start()
        return True

    # ------------------------------------------------------------------
    # 更新循环
    # ------------------------------------------------------------------
    def update(self, dt, bullet_manager, player_x, player_y):
        if self.background:
            self.background.update(dt)
        self.timer += 1

        if self.phase == "opening" and not self._opening_started:
            self._start_opening_dialogue()

        if self.boss is not None and self.phase != "cleared":
            # 机械符：把鼠标/按键转发给符卡状态（终端破解 GUI）
            gt_state = getattr(self.boss, "goldor_terminal", None)
            if gt_state is not None:
                mbj = getattr(self, "mouse_buttons_just_pressed", None) or {}
                mp = getattr(self, "mouse_pos", None) or (0, 0)
                if mbj.get(1):
                    gt_state["mouse_clicked"] = (
                        mp[0] - cfg.BATTLE_OFFSET_X, mp[1] - cfg.BATTLE_OFFSET_Y)
                else:
                    gt_state["mouse_clicked"] = None
                gt_state["mouse_battle"] = (
                    mp[0] - cfg.BATTLE_OFFSET_X, mp[1] - cfg.BATTLE_OFFSET_Y)
                gt_state["keys_just_pressed"] = (
                    getattr(self, "keys_just_pressed", None) or {})
            # Boss 死亡后仍更新一帧，让符卡背景淡出播完。
            self.boss.update(dt, bullet_manager, player_x, player_y)
            livid_active = getattr(self.boss, "livid_active", False)
            if livid_active and (not self.boss.alive or self.boss.phase != "spell"):
                _livid_cleanup(self.boss)
                bullet_manager.enemy_pause_frames = 0
            # 机械符传送请求 -> 下一帧应用到自机
            if gt_state is not None and gt_state.get("teleport_to") is not None:
                self.player_teleport_target = gt_state["teleport_to"]
                gt_state["teleport_to"] = None

        if self.phase == "boss":
            if self.boss is None or not self.boss.alive:
                if not self._boss_defeated_handled:
                    self._boss_defeated_handled = True
                    self._on_current_boss_defeated()

    def draw(self, screen, offset_x=0, offset_y=0):
        super().draw(screen, offset_x, offset_y)
        boss = self.boss
        if boss is None or not boss.alive:
            return
        giant = getattr(boss, "professor_giant", None)
        if giant is not None:
            giant.draw(screen, offset_x, offset_y)
        for guardian in getattr(boss, "professor_guardians", []):
            if guardian.alive:
                guardian.draw(screen, offset_x, offset_y)
        if getattr(boss, "livid_active", False):
            for clone in getattr(boss, "livid_clones", []):
                if clone.alive:
                    clone.draw(screen, offset_x, offset_y)
            real_state = boss.livid_states[boss.livid_real_index]
            glow = _get_livid_glow(real_state["color"], 44)
            screen.blit(glow, (int(boss.x + offset_x) - glow.get_width() // 2,
                               int(boss.y + offset_y) - glow.get_height() // 2))
            real_item = _get_livid_item_sprite(real_state["item"], 30)
            if real_item is not None:
                bob = int(math.sin(self.timer * 0.10) * 3)
                foot_y = int(boss.y + offset_y + _LIVID_CLONE_SPRITE_HEIGHT * 0.55)
                screen.blit(real_item, (int(boss.x + offset_x) - real_item.get_width() // 2,
                                        foot_y + bob))
        self._draw_professor_lightning_warnings(screen, offset_x, offset_y)
        _spirit_zoo_draw_animals(screen, boss, offset_x, offset_y)
        _spirit_zoo_draw_hazards(screen, boss, offset_x, offset_y)
        self._draw_frenzy_effects(screen, offset_x, offset_y)
        self._draw_storm_giga(screen, offset_x, offset_y)

    def _draw_livid_top_glow(self, screen, offset_x=0, offset_y=0):
        boss = self.boss
        if boss is None or not getattr(boss, "livid_active", False):
            return
        color = boss.livid_states[boss.livid_real_index]["color"]
        layer = _get_livid_top_glow(color)
        screen.blit(layer, (offset_x, offset_y))


    def _draw_frenzy_effects(self, screen, offset_x=0, offset_y=0):
        """Phase1「Maxor's Frenzy」视觉层：无敌护盾 / TNT / 水晶 / 冲击环。"""
        boss = self.boss
        if boss is None or getattr(boss, "frenzy_state", None) is None:
            return
        self._draw_frenzy_shield(screen, boss, offset_x, offset_y)
        self._draw_frenzy_tnts(screen, boss, offset_x, offset_y)
        self._draw_frenzy_crystals(screen, boss, offset_x, offset_y)
        self._draw_frenzy_shockwaves(screen, boss, offset_x, offset_y)

    def _draw_frenzy_shield(self, screen, boss, offset_x, offset_y):
        """无敌护盾：六边形能量罩环绕高速移动的 Maxor。"""
        if not boss.invincible:
            return
        px = int(boss.x + offset_x)
        py = int(boss.y + offset_y)
        now = pygame.time.get_ticks()
        r = max(30, int(boss.sprite_height * 0.56))
        rot = now * 0.0022
        pulse = 0.82 + 0.18 * math.sin(now * 0.006)
        rr = int(r * pulse)
        for i in range(6):
            a0 = rot + i * math.tau / 6
            a1 = rot + (i + 1) * math.tau / 6
            x0 = px + math.cos(a0) * rr
            y0 = py + math.sin(a0) * rr
            x1 = px + math.cos(a1) * rr
            y1 = py + math.sin(a1) * rr
            pygame.draw.line(screen, (255, 205, 130),
                             (int(x0), int(y0)), (int(x1), int(y1)), 2)
        pygame.draw.circle(screen, (255, 178, 96), (px, py), rr, 1)
        pygame.draw.circle(screen, (255, 232, 190), (px, py), max(3, rr - 8), 1)

    def _draw_frenzy_tnts(self, screen, boss, offset_x, offset_y):
        """TNT 标记：红砖方块 + 引信火花，引信末期闪光预告爆炸。"""
        for tnt in getattr(boss, "frenzy_tnts", []):
            px = int(tnt["x"] + offset_x)
            py = int(tnt["y"] + offset_y)
            prog = tnt["age"] / max(1, tnt["delay"])
            s = 16
            rect = pygame.Rect(px - s // 2, py - s // 2, s, s)
            pygame.draw.rect(screen, (168, 60, 42), rect)
            pygame.draw.rect(screen, (110, 32, 24), rect, 2)
            pygame.draw.line(screen, (215, 88, 62), (px - s // 2 + 3, py - s // 2 + 2),
                             (px + s // 2 - 3, py - s // 2 + 2), 2)
            pygame.draw.line(screen, (215, 88, 62), (px - s // 2 + 3, py + s // 2 - 2),
                             (px + s // 2 - 3, py + s // 2 - 2), 2)
            # 引信火花
            if (pygame.time.get_ticks() * 0.05) % 4 < 2:
                pygame.draw.circle(screen, (255, 214, 100), (px, py - 8), 2)
            for k in range(2):
                a = tnt["seed"] + k * math.pi + tnt["age"] * 0.35
                sx = px + math.cos(a) * 9
                sy = py - 7 + math.sin(a) * 3
                pygame.draw.circle(screen, (255, 190, 80), (int(sx), int(sy)), 1)
            # 引信末期：白色脉冲圈预告爆炸
            if prog > 0.72:
                blink = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.03)
                pygame.draw.circle(screen, (255, 240, 200), (px, py), int(12 + blink * 8), 1)

    def _draw_frenzy_crystals(self, screen, boss, offset_x, offset_y):
        """power crystal：发光晶簇 + 拾取圈，引导玩家收集。"""
        for crystal in getattr(boss, "frenzy_crystals", []):
            if crystal["collected"]:
                continue
            px = int(crystal["x"] + offset_x)
            py = int(crystal["y"] + offset_y)
            now = pygame.time.get_ticks()
            t = now * 0.004
            pulse = 0.75 + 0.25 * math.sin(t + crystal["sway_phase"])
            glow_r = 26
            glow = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (150, 235, 255, 70), (glow_r, glow_r), glow_r)
            pygame.draw.circle(glow, (215, 250, 255, 150), (glow_r, glow_r), max(4, glow_r - 12))
            screen.blit(glow, (px - glow_r, py - glow_r))
            sprite = _get_frenzy_crystal_sprite()
            if sprite is not None:
                img = pygame.transform.rotate(sprite, math.sin(t * 0.9 + crystal["sway_phase"]) * 12)
                screen.blit(img, (px - img.get_width() // 2, py - img.get_height() // 2))
            pygame.draw.circle(screen, (190, 240, 255), (px, py), int(18 * pulse), 1)

    def _draw_frenzy_shockwaves(self, screen, boss, offset_x, offset_y):
        """冲击波视觉环：TNT 爆炸 / 大型冲击波 / 水晶拾取闪光。"""
        for wave in getattr(boss, "frenzy_shockwaves", []):
            prog = min(1.0, wave["age"] / max(1, wave["max_age"]))
            r = int(wave["start_r"] + (wave["end_r"] - wave["start_r"]) * prog)
            col = wave["color"]
            cx = int(wave["x"] + offset_x)
            cy = int(wave["y"] + offset_y)
            pygame.draw.circle(screen, col, (cx, cy), r, wave["width"])
            pygame.draw.circle(screen, col, (cx, cy), max(2, r - 8), 1)

    def _draw_frenzy_laser(self, screen, offset_x=0, offset_y=0):
        """解封激光：回中时的预警线 + 命中后贯穿中央的竖直红色激光。"""
        boss = self.boss
        if boss is None or getattr(boss, "frenzy_state", None) is None:
            return
        state = boss.frenzy_state
        laser = boss.frenzy_laser
        cx = cfg.BATTLE_AREA_WIDTH / 2
        # 回中预警：激光未发射时中央出现闪烁竖线
        if state["mode"] == "reveal" and laser is None:
            alpha = 70 + int(70 * math.sin(pygame.time.get_ticks() * 0.02))
            x = int(cx + offset_x)
            top = int(offset_y + 6)
            bottom = int(offset_y + 116)
            layer = pygame.Surface((4, bottom - top), pygame.SRCALPHA)
            pygame.draw.line(layer, (255, 90, 70, alpha), (2, 0), (2, bottom - top), 2)
            screen.blit(layer, (x - 2, top))
            return
        if laser is None:
            return
        age = laser["age"]
        max_age = max(1, laser["max_age"])
        x = int(laser["x"] + offset_x)
        top = int(laser["top"] + offset_y)
        bottom = int(laser["y"] + offset_y)
        fade = 1.0
        if age < 6:
            fade = age / 6.0
        elif age > max_age - 12:
            fade = max(0.0, (max_age - age) / 12.0)
        height = max(2, bottom - top)
        for w, alpha in ((16, 56), (8, 110), (3, 230)):
            layer = pygame.Surface((w * 2, height), pygame.SRCALPHA)
            pygame.draw.line(layer, (255, 64, 48, int(alpha * fade)),
                             (w, 0), (w, height), w)
            screen.blit(layer, (x - w, top))

    def draw_foreground(self, screen, offset_x=0, offset_y=0):
        boss = self.boss
        if boss is None:
            return
        # 机械符：警告红幕 / 破解 GUI / 通关演出（绘制在弹幕之上）
        _gt_draw_foreground(screen, boss, offset_x, offset_y)
        # Phase3：旋转剑盾（巨剑 / 盾环 / 剑隙提示，绘制在弹幕之上）
        draw_goldor_rage(screen, boss, offset_x, offset_y)
        self._draw_livid_top_glow(screen, offset_x, offset_y)
        self._draw_frenzy_laser(screen, offset_x, offset_y)
        self._draw_storm_giga_foreground(screen, offset_x, offset_y)
        if getattr(boss, "livid_blackout_frames", 0) <= 0:
            return
        overlay = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT),
                                 pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 255))
        screen.blit(overlay, (offset_x, offset_y))
        boss.livid_blackout_frames -= 1
        if boss.livid_blackout_frames == 0 and getattr(boss, "livid_swap_pending", False):
            _livid_swap_positions(boss)
            boss.livid_swap_pending = False

    def _draw_professor_lightning_warnings(self, screen, offset_x=0, offset_y=0):
        """半透明虚线预警：只提示落雷位置，不进入弹幕碰撞，视觉上远离真实雷束。"""
        boss = self.boss
        if boss is None:
            return
        top = offset_y + 14
        bottom = offset_y + cfg.BATTLE_AREA_HEIGHT - 16
        height = max(1, bottom - top)
        for warning in getattr(boss, "professor_lightning_warnings", []):
            age = warning["age"]
            max_age = warning["max_age"]
            fade = math.sin(math.pi * min(1.0, age / float(max_age)))
            alpha = int(92 + 44 * fade + 11 * math.sin(age * 0.22))
            alpha = max(80, min(150, alpha))
            x = int(warning["x"] + offset_x)

            layer = pygame.Surface((7, height), pygame.SRCALPHA)
            for yy in range(0, height, 15):
                seg = min(9, height - yy)
                pygame.draw.line(layer, (165, 238, 214, alpha),
                                 (3, yy), (3, yy + seg), 2)
            screen.blit(layer, (x - 3, top))

            marker = pygame.Surface((28, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(marker, (165, 238, 214, alpha // 3),
                                (3, 1, 22, 10), 0)
            pygame.draw.ellipse(marker, (165, 238, 214, alpha),
                                (3, 1, 22, 10), 2)
            screen.blit(marker, (x - 14, bottom - 5))


    def _draw_storm_giga(self, screen, offset_x=0, offset_y=0):
        """Storm 符卡 Phase2：4 根避雷柱、安全区光环、普通雷击预警与破坏闪光。"""
        boss = self.boss
        giga = getattr(boss, "storm_giga", None)
        if giga is None or not boss.alive:
            return
        now = pygame.time.get_ticks()
        safe_r = giga.get("safe_radius", STORM_GIGA_PILLAR_SAFE_RADIUS)

        for p in giga["pillars"]:
            px = int(p["x"] + offset_x)
            py = int(p["y"] + offset_y)
            if p["alive"]:
                # 地面避雷安全区：浅蓝脉冲光环
                ring = pygame.Surface((safe_r * 2 + 6, safe_r * 2 + 6), pygame.SRCALPHA)
                c = safe_r + 3
                pulse = 0.86 + 0.14 * math.sin(now * 0.012 + p["x"] * 0.05)
                pygame.draw.circle(ring, (70, 190, 255, 42), (c, c), int(safe_r * pulse), 0)
                pygame.draw.circle(ring, (140, 220, 255, 150), (c, c), safe_r, 2)
                pygame.draw.circle(ring, (225, 248, 255, 90), (c, c), safe_r - 5, 1)
                screen.blit(ring, (px - c, py - c))
                # 金属避雷杆与顶端雷球
                pole_top = py - 78
                pygame.draw.line(screen, (96, 116, 148), (px - 3, pole_top), (px - 3, py), 2)
                pygame.draw.line(screen, (170, 195, 225), (px, pole_top), (px, py), 3)
                pygame.draw.line(screen, (120, 140, 170), (px + 2, pole_top), (px + 2, py), 2)
                glow_r = 9 + int(2 * math.sin(now * 0.011 + p["x"] * 0.06))
                pygame.draw.circle(screen, (150, 210, 255), (px, pole_top), glow_r, 2)
                pygame.draw.circle(screen, (225, 248, 255), (px, pole_top), 4, 0)
            else:
                # 被破坏：焦黑残桩 + 地面焦痕
                pygame.draw.rect(screen, (46, 50, 60), (px - 3, py - 14, 6, 14))
                pygame.draw.ellipse(screen, (34, 38, 46), (px - 17, py - 7, 34, 12))
                pygame.draw.ellipse(screen, (20, 22, 28), (px - 12, py - 4, 24, 8))

        # 柱子被破坏瞬间的电光
        if giga.get("pillar_flash", 0) > 0:
            target = giga.get("target_pillar")
            if target is not None and 0 <= target < len(giga["pillars"]):
                p = giga["pillars"][target]
                px = int(p["x"] + offset_x)
                py = int(p["y"] + offset_y) - 78
                alpha = int(150 * giga["pillar_flash"] / float(STORM_GIGA_PILLAR_FLASH))
                flash = pygame.Surface((46, 46), pygame.SRCALPHA)
                pygame.draw.circle(flash, (210, 240, 255, alpha), (23, 23), 22, 0)
                pygame.draw.circle(flash, (255, 255, 255, alpha), (23, 23), 14, 3)
                screen.blit(flash, (px - 23, py - 23))

        # 普通雷击预警：浅蓝虚线车道
        top = offset_y + 14
        bottom = offset_y + cfg.BATTLE_AREA_HEIGHT - 16
        height = max(1, bottom - top)
        for warning in giga.get("warnings", []):
            age = warning["age"]
            max_age = warning["max_age"]
            fade = math.sin(math.pi * min(1.0, age / float(max_age)))
            alpha = int(90 + 50 * fade + 10 * math.sin(age * 0.22))
            alpha = max(80, min(160, alpha))
            x = int(warning["x"] + offset_x)
            layer = pygame.Surface((7, height), pygame.SRCALPHA)
            for yy in range(0, height, 15):
                seg = min(9, height - yy)
                pygame.draw.line(layer, (150, 220, 255, alpha), (3, yy), (3, yy + seg), 2)
            screen.blit(layer, (x - 3, top))
            marker = pygame.Surface((28, 12), pygame.SRCALPHA)
            pygame.draw.ellipse(marker, (150, 220, 255, alpha // 3), (3, 1, 22, 10), 0)
            pygame.draw.ellipse(marker, (150, 220, 255, alpha), (3, 1, 22, 10), 2)
            screen.blit(marker, (x - 14, bottom - 5))

        # 无敌电盾：普通雷击 / 蓄力 / 全屏雷击阶段包裹 Storm
        sub = giga.get("sub")
        if sub in ("normal", "charge", "strike") and boss.invincible:
            px = int(boss.x + offset_x)
            py = int(boss.y + offset_y)
            r = 30 + int(2 * math.sin(now * 0.02))
            for k in range(10):
                a0 = now * 0.0032 + k * math.tau / 10
                x0 = px + math.cos(a0) * r
                y0 = py + math.sin(a0) * r
                x1 = px + math.cos(a0 + 0.45) * (r + 7)
                y1 = py + math.sin(a0 + 0.45) * (r + 7)
                pygame.draw.line(screen, (140, 220, 255), (x0, y0), (x1, y1), 2)
                pygame.draw.line(screen, (220, 245, 255), (px, py), (x0, y0), 1)

    def _draw_storm_giga_foreground(self, screen, offset_x=0, offset_y=0):
        """Giga Lightning 蓄力阴影 / 全屏雷击闪光 / 狂暴红环，绘制在弹幕之上。"""
        boss = self.boss
        giga = getattr(boss, "storm_giga", None)
        if giga is None or not boss.alive:
            return
        now = pygame.time.get_ticks()
        safe_r = giga.get("safe_radius", STORM_GIGA_PILLAR_SAFE_RADIUS)
        sub = giga.get("sub")

        if sub == "charge":
            t = giga["sub_timer"]
            progress = min(1.0, t / float(STORM_GIGA_CHARGE_DURATION))
            # 危险区阴影：全屏压暗，存活避雷柱下方保持通透
            alpha = int(60 + 120 * progress)
            overlay = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT),
                                     pygame.SRCALPHA)
            overlay.fill((8, 6, 26, alpha))
            holes = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT),
                                   pygame.SRCALPHA)
            for p in giga["pillars"]:
                if p["alive"]:
                    pygame.draw.circle(holes, (0, 0, 0, 255),
                                       (int(p["x"]), int(p["y"])), safe_r)
            overlay.blit(holes, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
            screen.blit(overlay, (offset_x, offset_y))
            # 顶部蓄力读条
            bar_w = cfg.BATTLE_AREA_WIDTH - 80
            bx = offset_x + 40
            by = offset_y + 10
            pygame.draw.rect(screen, (30, 40, 60), (bx, by, bar_w, 8))
            fill_w = int(bar_w * progress)
            if fill_w > 0:
                pygame.draw.rect(screen, (120, 210, 255), (bx, by, fill_w, 8))
            # Storm 蓄力电弧
            px = int(boss.x + offset_x)
            py = int(boss.y + offset_y)
            for k in range(3):
                r = 34 + k * 8 + int(2 * math.sin(now * 0.02))
                pygame.draw.circle(screen, (130, 210, 255), (px, py), r, 2)
            # 目标柱子标记（破坏前）
            target = giga.get("target_pillar")
            if (target is not None and 0 <= target < len(giga["pillars"])
                    and giga["pillars"][target]["alive"]):
                p = giga["pillars"][target]
                mx = int(p["x"] + offset_x)
                my = int(p["y"] + offset_y) - 92
                pygame.draw.line(screen, (255, 120, 90), (mx - 8, my), (mx + 8, my), 3)
                pygame.draw.line(screen, (255, 120, 90), (mx, my - 8), (mx, my + 8), 3)

        elif sub == "strike":
            t = giga["sub_timer"]
            flash = max(0.0, 1.0 - t / float(STORM_GIGA_STRIKE_DURATION))
            overlay = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT),
                                     pygame.SRCALPHA)
            overlay.fill((225, 244, 255, int(150 * flash)))
            screen.blit(overlay, (offset_x, offset_y))
            bolts = giga.get("strike_bolts", [])
            for pts in bolts:
                for i in range(len(pts) - 1):
                    pygame.draw.line(screen, (240, 250, 255),
                                     (pts[i][0] + offset_x, pts[i][1] + offset_y),
                                     (pts[i + 1][0] + offset_x, pts[i + 1][1] + offset_y), 3)
                    pygame.draw.line(screen, (150, 210, 255),
                                     (pts[i][0] + offset_x, pts[i][1] + offset_y),
                                     (pts[i + 1][0] + offset_x, pts[i + 1][1] + offset_y), 1)

        elif sub == "frenzy":
            # 狂暴状态：红色脉冲光环
            px = int(boss.x + offset_x)
            py = int(boss.y + offset_y)
            pulse = 0.8 + 0.2 * math.sin(now * 0.02)
            for r, col in ((30, (255, 90, 70)), (42, (255, 150, 90))):
                pygame.draw.circle(screen, col, (px, py), int(r * pulse), 2)
            pygame.draw.circle(screen, (255, 60, 50), (px, py), 3, 0)


    def _on_current_boss_defeated(self):
        boss_id = self.current_boss_id
        if boss_id == "watcher":
            self._start_summon_dialogue("professor")
        elif boss_id == "professor":
            self._start_summon_dialogue("thorn")
        elif boss_id == "thorn":
            self._start_summon_dialogue("livid")
        elif boss_id == "livid":
            self._start_watcher_exit_dialogue()
        elif boss_id == "maxor":
            self._start_wither_battle("storm")
        elif boss_id == "storm":
            self._start_wither_battle("goldor")
        elif boss_id == "goldor":
            self._start_wither_battle("necron")
        elif boss_id == "necron":
            self._start_final_dialogue()

    # ------------------------------------------------------------------
    # 对话与转场
    # ------------------------------------------------------------------
    def _set_dialogue(self, lines, portraits, sides, pending_action, is_defeat=False):
        self.dialogue_lines = lines
        self.dialogue_portraits = portraits
        self.dialogue_portrait_sides = sides
        self.dialogue_is_defeat = is_defeat
        self._pending_dialogue_action = pending_action
        self.dialogue_active = True

    def _start_opening_dialogue(self):
        self._opening_started = True
        self._spawn_boss_for_dialogue("watcher")
        self._set_dialogue(
            [
                ("The Watcher", "终于来了。"),
                ("魔法使 Mage", "你就是一直在观察我的人？"),
                ("The Watcher", "从你踏入地下城的那一刻起。"),
                ("魔法使 Mage", "看来，你知道我要找什么。"),
                ("The Watcher", "知道。"),
                ("The Watcher", "但答案不是靠询问得到的。"),
                ("魔法使 Mage", "所以？"),
                ("The Watcher", "先证明自己吧。"),
            ],
            {
                "The Watcher": cfg.STAGE5_WATCHER_BOSS_SPRITE,
                "魔法使 Mage": cfg.SELF_SPRITE,
            },
            {"魔法使 Mage": "left", "The Watcher": "right"},
            "watcher")
        self.phase = "dialogue"
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)

    def _start_summon_dialogue(self, boss_id):
        self._spawn_boss_for_dialogue(boss_id)
        boss_name = self.boss_display_names[boss_id]
        boss_portrait = getattr(cfg, "STAGE5_" + boss_id.upper() + "_BOSS_SPRITE")
        if boss_id == "professor":
            lines = [
                ("The Watcher", "第一个试炼。"),
                ("The Watcher", "知识。"),
                ("The Professor", "哦？"),
                ("The Professor", "看来，今天来了位新的研究对象。"),
            ]
        elif boss_id == "thorn":
            lines = [
                ("The Watcher", "第二个试炼。"),
                ("The Watcher", "力量。"),
                ("Thorn", "人类。"),
                ("Thorn", "让我看看你有没有资格继续前进。"),
            ]
        else:
            lines = [
                ("The Watcher", "最后一个试炼。"),
                ("魔法使 Mage", "敏捷？"),
                ("The Watcher", "不。"),
                ("The Watcher", "欺骗。"),
                ("Livid", "呵。"),
                ("Livid", "希望你能找到真正的我。"),
            ]
        portraits = {
            "The Watcher": cfg.STAGE5_WATCHER_BOSS_SPRITE,
            boss_name: boss_portrait,
        }
        if boss_id == "livid":
            portraits["魔法使 Mage"] = cfg.SELF_SPRITE
            sides = {"魔法使 Mage": "left", "The Watcher": "right"}
        else:
            sides = {"The Watcher": "left"}
        self._set_dialogue(
            lines,
            portraits,
            sides,
            "normal_boss")
        self.phase = "dialogue"
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)

    def _start_watcher_exit_dialogue(self):
        """Livid 被击败后：The Watcher 退场对话。"""
        self._set_dialogue(
            [
                ("The Watcher", "看来，我已经没有继续观察的必要了。"),
                ("魔法使 Mage", "这就结束了？"),
                ("The Watcher", "不。"),
                ("The Watcher", "真正的守门人正在等你。"),
                ("魔法使 Mage", "Necron？"),
                ("The Watcher", "去寻找答案吧。"),
            ],
            {
                "The Watcher": cfg.STAGE5_WATCHER_BOSS_SPRITE,
                "魔法使 Mage": cfg.SELF_SPRITE,
            },
            {"魔法使 Mage": "left", "The Watcher": "right"},
            "watcher_exit")
        self.phase = "dialogue"
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)

    def _start_maxor_dialogue(self):
        self._spawn_boss_for_dialogue("maxor")
        self._set_dialogue(
            [
                ("Maxor", "哈哈！"),
                ("Maxor", "终于来了个有意思的家伙！"),
                ("魔法使 Mage", "看来，你们已经等我很久了。"),
                ("Maxor", "不。"),
                ("Maxor", "是他等你很久了。"),
                ("魔法使 Mage", "他？"),
                ("Maxor", "真奇怪。"),
                ("Maxor", "走到这里，你居然还不知道自己为什么会来到这里。"),
                ("魔法使 Mage", "我只是来调查地下城的异常。"),
                ("Maxor", "是吗？"),
                ("魔法使 Mage", "什么意思？"),
                ("Maxor", "自己去寻找答案吧。"),
            ],
            {
                "Maxor": cfg.STAGE5_MAXOR_BOSS_SPRITE,
                "魔法使 Mage": cfg.SELF_SPRITE,
            },
            {"魔法使 Mage": "left", "Maxor": "right"},
            "maxor")
        self.phase = "dialogue"
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)

    def _start_wither_battle(self, boss_id):
        self._spawn_boss_for_dialogue(boss_id)
        boss = self.boss
        boss.arm_combat(0)
        boss.entering = False
        boss.entry_timer = 0
        if boss.spell_cards:
            boss.current_spell_idx = 0
            boss._start_spell(boss.spell_cards[0])
        self.phase = "boss"
        self._boss_defeated_handled = False
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)

    def _start_final_dialogue(self):
        self._set_dialogue(
            [
                ("Necron", "看来，我们输了。"),
                ("魔法使 Mage", "所以，一切都是因为 Kaeman？"),
                ("Necron", "是。"),
                ("Necron", "也不是。"),
                ("魔法使 Mage", "什么意思？"),
                ("Necron", "没有人能够改变已经发生的事情。"),
                ("魔法使 Mage", "但他还在试图这么做。"),
                ("Necron", "正因如此，你才会来到这里。"),
                ("魔法使 Mage", "看来，最后的答案就在前面。"),
                ("Necron", "去吧。"),
                ("Necron", "他就在王座之间等着你。"),
            ],
            {
                "魔法使 Mage": cfg.SELF_SPRITE,
                "Necron": cfg.STAGE5_NECRON_BOSS_SPRITE,
            },
            {"魔法使 Mage": "left", "Necron": "right"},
            None,
            is_defeat=True)
        self.phase = "defeat_dialogue"
        self._ramp_background_speed(1.0, BOSS_BG_RAMP_TIME)

    # ------------------------------------------------------------------
    # PlayingState 对话结束回调
    # ------------------------------------------------------------------
    def on_dialogue_end(self):
        """普通战前对话结束：按当前转场类型启动 Boss。"""
        self.dialogue_active = False
        if self.dialogue_is_defeat:
            return
        action = self._pending_dialogue_action
        if action == "watcher_exit":
            self._start_maxor_dialogue()
            return
        if action in ("watcher", "maxor"):
            self._force_current_boss_spell()
        else:
            self._arm_current_boss_normal()
        self._on_boss_combat_start()

    def on_defeat_dialogue_end(self):
        """Necron 战后对话结束：五面通关结算。"""
        self.dialogue_active = False
        self.dialogue_is_defeat = False
        self.phase = "cleared"
        self._ramp_background_speed(1.0, BOSS_BG_RAMP_TIME)

    def _on_boss_combat_start(self):
        """每个 Boss 开战时都抬升视角，营造 BOSS RUSH 压迫感。"""
        if self.background is not None:
            self.background.ramp_view_height(122.0, 2.4)
