# 自机弹幕差分的离线自检（不启动游戏窗口）：
#   1) FB（默认机体）与改前的旧版 _player_shoot 逐发比对（含 Terminator / Loving / 低速）
#   2) Mage / Archer / Tank 按登记的条数、扩散、穿透、追踪弹逐档核对
#      （含弓手的起始点收束 / 爆炸箭贴图 / 命中清弹）
#   3) 穿透弹的命中结算（同一目标只结算一次，含真实 _check_collisions 那一遍）
#
# 用法：python tools/_verify_shots.py
import math
import os
import random
import sys
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pygame  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")
pygame.init()
pygame.display.set_mode((1, 1))

from src.engine import settings as cfg  # noqa: E402
from src.entities import bullet as bm  # noqa: E402
from src.entities.bullet import Bullet  # noqa: E402
from src.ui.menu import PlayingState  # noqa: E402

FIXED_DY = -8.0     # 固定弹在自机上方的发射高度（py = player.y - 8）
HOMING_DY = -12.0   # 追踪弹的发射高度（py - 4）


class _Manager:
    def __init__(self):
        self.player_bullets = []

    def add_player_bullet(self, bullet):
        self.player_bullets.append(bullet)


class _FakeState(PlayingState):
    """只带 _player_shoot / _bullet_damage / _weapon_damage 需要的字段（不走 __init__）"""

    def __init__(self, power, focused, effects):
        self.power = power
        self.item_effects = effects
        self.spirit_bow_timer = 0
        self.homing_shot_skip = False
        self.shadow_damage = 0.0
        self.bad_health_timer = 0
        self.arack_timer = 0
        self.bullet_manager = _Manager()
        self.explosive_shot_timer = 0
        self.game = SimpleNamespace(play_sfx=lambda name: None)
        self.player = SimpleNamespace(x=100.0, y=400.0, focused=focused,
                                      max_power=400, hitbox_radius=2.0,
                                      graze_radius=8.0, can_be_hit=lambda: False)


def _state(character, power, focused, **effects):
    eff = {key: 0.0 for key in (
        "damage_pct", "non_tracking_damage_pct", "tracking_damage_pct",
        "tracking_high_speed_damage_pct", "fixed_bullet_add",
        "tracking_bullet_add", "fixed_double_damage_chance", "arack_pct",
        "minion_damage_pct")}
    eff["terminator"] = False
    eff.update(effects)
    cfg.set_player_character(character)
    return _FakeState(power, focused, eff)


def _rows(state):
    """(横向落点, vx, vy, 伤害, 是否追踪, 是否穿透, 纵向落点)"""
    return [(round(b.x - state.player.x, 4), round(b.vx, 6), round(b.vy, 6),
             round(b.damage, 4), bool(b.homing), bool(b.pierce),
             round(b.y - state.player.y, 4))
            for b in state.bullet_manager.player_bullets]


def shoot(character, power, focused, **effects):
    state = _state(character, power, focused, **effects)
    PlayingState._player_shoot(state)
    return _rows(state)


def legacy_shoot(power, focused, fixed_bullet_add=0, tracking_bullet_add=0,
                 terminator=False):
    """改前的 _player_shoot（FB 的参照实现，逐字照抄改动前的版本）"""
    state = _state("frozen_blaze", power, focused,
                   fixed_bullet_add=fixed_bullet_add,
                   tracking_bullet_add=tracking_bullet_add,
                   terminator=terminator)
    eff = state.item_effects
    px, py = state.player.x, state.player.y - 8
    power_level = power // 100
    lines = max(1, min(3, power_level + 1 + int(eff["fixed_bullet_add"])))
    if eff["terminator"]:
        per_side_deg = 4.5 if not focused else 0.5
    else:
        per_side_deg = 2.25
    tilt_vx = math.tan(math.radians(per_side_deg)) * 12.0
    tilt_vy = -11.96
    if lines >= 3:
        bullets = [bm.create_player_bullet(px - 10, py, -tilt_vx, tilt_vy),
                   bm.create_player_bullet(px, py),
                   bm.create_player_bullet(px + 10, py, tilt_vx, tilt_vy)]
    elif lines == 2:
        bullets = [bm.create_player_bullet(px - 10, py, -tilt_vx, tilt_vy),
                   bm.create_player_bullet(px + 10, py, tilt_vx, tilt_vy)]
    else:
        bullets = [bm.create_player_bullet(px, py)]
    for b in bullets:
        b.damage = cfg.BULLET_PLAYER_DAMAGE
        state.bullet_manager.add_player_bullet(b)

    track_count = 1 + int(eff["tracking_bullet_add"])
    if power >= 15:
        full_power = power >= 400
        if full_power or not state.homing_shot_skip:
            ratio = 1 / 3 + (1 / 3) * (power - 15) / (400 - 15)
            offsets = (-4, 4) if track_count >= 2 else (0,)
            for off in offsets:
                hb = bm.create_player_bullet(px + off, py - 4, homing=True)
                hb.damage = round(cfg.BULLET_PLAYER_DAMAGE * ratio, 1)
                state.bullet_manager.add_player_bullet(hb)
        if not full_power:
            state.homing_shot_skip = not state.homing_shot_skip
    return _rows(state)


def fixed_of(rows):
    return [row for row in rows if row[6] == FIXED_DY]


def homing_of(rows):
    return [row for row in rows if row[6] == HOMING_DY]


def angles(rows):
    """每发弹相对「笔直向上」的倾角（度）"""
    return sorted(round(math.degrees(math.atan2(row[1], -row[2])), 4)
                  for row in rows)


def tilt_step(rows):
    """相邻弹条的夹角步长（= 最小的那个非零倾角）"""
    positive = [abs(angle) for angle in angles(rows) if abs(angle) > 1e-6]
    return round(min(positive), 2) if positive else 0.0


failures = []


def check(label, ok, detail=""):
    print(f"{'OK  ' if ok else 'FAIL'} {label}{('  -> ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)


def close(actual, expected, tol=0.05):
    return (len(actual) == len(expected)
            and all(abs(a - e) <= tol for a, e in zip(actual, expected)))


# --- 1) FB（默认）与改前逐发一致 ---
diffs = []
for power in (0, 15, 99, 100, 199, 200, 399, 400):
    for focused in (False, True):
        for fixed_add in (0, -1, 1):
            for track_add in (0, 1):
                for terminator in (False, True):
                    new = shoot("frozen_blaze", power, focused,
                                fixed_bullet_add=fixed_add,
                                tracking_bullet_add=track_add,
                                terminator=terminator)
                    old = legacy_shoot(power, focused, fixed_add, track_add,
                                       terminator)
                    if new != old:
                        diffs.append((power, focused, fixed_add, track_add,
                                      terminator, new, old))
check("FB 与改前逐发一致（8 档火力 x 低速 x Loving x Terminator）",
      not diffs,
      f"差异 {len(diffs)} 组" + (f"，首组 {diffs[0][:5]}" if diffs else ""))
if diffs:
    print("   new:", diffs[0][5])
    print("   old:", diffs[0][6])

# --- 2) Mage：1/3/5 条、扩散两倍、穿透、没有追踪弹 ---
for power, expect in ((0, 1), (100, 3), (200, 5), (400, 5)):
    rows = fixed_of(shoot("mage", power, False))
    check(f"Mage power={power} 固定弹 {len(rows)} 条", len(rows) == expect,
          f"实际 {len(rows)}")
check("Mage 没有追踪弹", not homing_of(shoot("mage", 400, False)))
check("Mage 固定弹全部穿透", all(row[5] for row in shoot("mage", 400, False)))
check("Mage 固定弹落点 ±20 / ±10 / 0",
      sorted(row[0] for row in fixed_of(shoot("mage", 400, False)))
      == [-20.0, -10.0, 0.0, 10.0, 20.0])
check("Mage 扩散为旧版两倍（±9 / ±4.5 / 0）",
      close(angles(fixed_of(shoot("mage", 400, False))),
            [-9.0, -4.5, 0.0, 4.5, 9.0]),
      str(angles(fixed_of(shoot("mage", 400, False)))))
check("Mage 低速时扩散与条数不变",
      close(angles(fixed_of(shoot("mage", 400, True))),
            [-9.0, -4.5, 0.0, 4.5, 9.0]))

# --- 3) Archer：条数同 Mage、扩散同 Mage（两倍）、低速减半、不穿透 ---
for power, expect in ((0, 1), (100, 3), (200, 5)):
    rows = fixed_of(shoot("archer", power, False))
    check(f"Archer power={power} 固定弹 {len(rows)} 条", len(rows) == expect,
          f"实际 {len(rows)}")
check("Archer 没有追踪弹", not homing_of(shoot("archer", 400, False)))
check("Archer 固定弹不穿透", all(not row[5] for row in shoot("archer", 400, False)))
check("Archer 高速扩散与 Mage 相同（±9 / ±4.5 / 0）",
      close(angles(fixed_of(shoot("archer", 400, False))),
            [-9.0, -4.5, 0.0, 4.5, 9.0]),
      str(angles(fixed_of(shoot("archer", 400, False)))))
check("Archer 低速扩散减半（±4.5 / ±2.25 / 0）",
      close(angles(fixed_of(shoot("archer", 400, True))),
            [-4.5, -2.25, 0.0, 2.25, 4.5]),
      str(angles(fixed_of(shoot("archer", 400, True)))))

# --- 4) Tank：1/2/3 条笔直向上 + 与旧版一样的追踪弹 ---
for power, expect in ((0, 1), (100, 2), (200, 3), (400, 3)):
    rows = fixed_of(shoot("tank", power, False))
    check(f"Tank power={power} 固定弹 {len(rows)} 条", len(rows) == expect,
          f"实际 {len(rows)}")
tank_fixed = fixed_of(shoot("tank", 400, False))
check("Tank 固定弹笔直向上（vx = 0、vy = -12）",
      all(row[1] == 0.0 and row[2] == -12.0 for row in tank_fixed))
check("Tank 落点 ±10 / 0",
      sorted(row[0] for row in tank_fixed) == [-10.0, 0.0, 10.0],
      str(sorted(row[0] for row in tank_fixed)))
mismatch = [power for power in (15, 100, 200, 399, 400)
            if homing_of(shoot("tank", power, False))
            != homing_of(legacy_shoot(power, False))]
check("Tank 追踪弹逐档与旧版一致", not mismatch, str(mismatch))

# --- 4b) 弓手：起始点收束 + 中间那条每 240 帧一根爆炸箭 ---
def bullets_of(character, power, focused, **effects):
    """发一次弹，返回 (state, 固定弹列表)（固定弹 = 发射高度 py = y - 8 那批）"""
    state = _state(character, power, focused, **effects)
    PlayingState._player_shoot(state)
    fixed = [b for b in state.bullet_manager.player_bullets
             if abs(b.y - (state.player.y + FIXED_DY)) < 1e-6]
    return state, fixed


state, archer_fixed = bullets_of("archer", 400, False)
check("Archer 起始点收束：五条箭的横向落点全为 0（只靠倾角分开）",
      all(abs(b.x - state.player.x) < 1e-6 for b in archer_fixed),
      str(sorted(round(b.x - state.player.x, 4) for b in archer_fixed)))
check("Archer 起始点收束：低速同样收束",
      all(abs(b.x - state.player.x) < 1e-6
          for b in bullets_of("archer", 400, True)[1]))


def sprite_name(bullet):
    """这发弹实际会贴的图（没单独指定就是机体默认弹贴图）"""
    return os.path.basename(bullet.player_sprite_path or cfg.PLAYER_BULLET_SPRITE)


names = sorted(sprite_name(b) for b in archer_fixed)
check("Archer 贴图：轮到的那一轮中间是 Explosive_Arrow、其余是 Iron_Arrow",
      names == ["Explosive_Arrow.png", "Iron_Arrow.png", "Iron_Arrow.png",
                "Iron_Arrow.png", "Iron_Arrow.png"], str(names))
explosive = [b for b in archer_fixed if b.clear_radius_on_hit > 0]
check("Archer 爆炸箭：恰好中间那条（vx = 0）带清弹半径",
      len(explosive) == 1
      and explosive[0].clear_radius_on_hit
      == cfg.PLAYER_SHOT_EXPLOSIVE_CLEAR_RADIUS
      and abs(explosive[0].vx) < 1e-6,
      f"{len(explosive)} 条")
check("Archer 爆炸箭：Loving 变成偶数条时也恰好一条（取靠左的那条）",
      sum(1 for b in bullets_of("archer", 200, False, fixed_bullet_add=-1)[1]
          if b.clear_radius_on_hit > 0) == 1)
check("其余机体没有爆炸箭（清弹半径全 0）",
      all(not [b for b in bullets_of(name, 400, False)[1]
               if b.clear_radius_on_hit > 0]
          for name in ("frozen_blaze", "mage", "tank")))

# 发射节奏：进关第一发就是一根爆炸箭，之后每 240 帧才轮到一根，其余轮次中间
# 那条也是普通箭 —— 按真实帧走一遍（每帧推 timer，每 4 帧开一次枪）
state = _state("archer", 400, False)
fired = []
for frame in range(1, 721):
    PlayingState._tick_shot_cadence(state)
    if frame % 4 == 0:                       # Player.can_shoot 的 4 帧冷却
        state.bullet_manager.player_bullets.clear()
        PlayingState._player_shoot(state)
        middle = min(state.bullet_manager.player_bullets,
                     key=lambda b: abs(b.vx))    # 中间那条：vx = 0
        fired.append((frame, sprite_name(middle)))
due = [frame for frame, name in fired if name == "Explosive_Arrow.png"]
check("Archer 爆炸箭按帧节流：720 帧里只有第 4 / 244 / 484 帧那三根",
      due == [4, 244, 484], str(due))
check("Archer 其余轮次中间那条是 Iron_Arrow",
      {name for frame, name in fired if frame not in due} == {"Iron_Arrow.png"},
      str(len(fired)) + " 轮")

# --- 5) 穿透弹只对同一目标结算一次 ---
class _Target:
    pass


piercing = Bullet(0, 0, 0, -12, is_player_bullet=True)
piercing.pierce = True
target_a, target_b = _Target(), _Target()
check("穿透弹：首次结算、同目标不再结算、换目标继续结算且弹体存活",
      piercing.try_hit(target_a) and not piercing.try_hit(target_a)
      and piercing.try_hit(target_b) and piercing.alive)
plain = Bullet(0, 0, 0, -12, is_player_bullet=True)
check("普通弹：命中即消失（旧版行为）", plain.try_hit(target_a) and not plain.alive)


# --- 6) 战斗里的命中结算：穿透弹打穿两个敌人、每个只结算一次 ---
class _FakeEnemy:
    def __init__(self, x, y, radius=6.0):
        self.x = x
        self.y = y
        self.radius = radius
        self.alive = True
        self.damage_taken = 0.0
        self.hits = 0

    def collides_with_bullet(self, bx, by, br):
        return (abs(bx - self.x) <= self.radius + br
                and abs(by - self.y) <= self.radius + br)

    def take_damage(self, damage, source=None):
        self.damage_taken += damage
        self.hits += 1
        return False


def _battle_state(character="mage", power=400, focused=False):
    state = _state(character, power, focused)
    state.bullet_manager = bm.BulletManager()
    enemies = [_FakeEnemy(100.0, 300.0), _FakeEnemy(100.0, 316.0)]
    state.enemies = enemies
    state.stage = SimpleNamespace(
        get_active_enemies=lambda: [e for e in enemies if e.alive], boss=None)
    state.wither_shields = []
    state.bonzo_balloons = []
    state.graze = 0
    state.score = 0
    return state


def _fly(state, pierce):
    bullet = Bullet(state.player.x, 390.0, 0.0, -12.0, is_player_bullet=True)
    bullet.pierce = pierce
    bullet.damage = 10.0
    state.bullet_manager.add_player_bullet(bullet)
    for _ in range(12):
        state.bullet_manager.update(1, state.player.x, state.player.y)
        PlayingState._check_collisions(state)
    return bullet


state = _battle_state()
bullet = _fly(state, True)
enemy_a, enemy_b = state.enemies
check("穿透弹：一发打穿两个敌人（各 10 点、一次）",
      enemy_a.damage_taken == 10.0 and enemy_b.damage_taken == 10.0,
      f"{enemy_a.damage_taken} / {enemy_b.damage_taken}")
check("穿透弹：穿过同一敌人时不会每帧重复扣血",
      (enemy_a.hits, enemy_b.hits) == (1, 1),
      f"命中次数 {enemy_a.hits} / {enemy_b.hits}")
check("穿透弹：打穿两个敌人后仍在飞", bullet.alive)

state = _battle_state()
bullet = _fly(state, False)
enemy_a, enemy_b = state.enemies
# 弹从下往上飞，先遇到位置靠下的那个（316）
check("普通弹：只打中先遇到的那个敌人就消失（旧版行为）",
      enemy_b.damage_taken == 10.0 and enemy_a.damage_taken == 0.0
      and not bullet.alive,
      f"{enemy_a.damage_taken} / {enemy_b.damage_taken}")

# --- 6b) 爆炸箭命中敌人时炸掉小范围敌弹（走真实 _check_collisions） ---
state = _battle_state("archer")
target = state.enemies[0]
state.enemies = [target]
state.stage = SimpleNamespace(get_active_enemies=lambda: [target], boss=None)
near_eb = Bullet(target.x + 10.0, target.y, 0.0, 0.0)
far_eb = Bullet(target.x + 100.0, target.y, 0.0, 0.0)
state.bullet_manager.enemy_bullets.extend([near_eb, far_eb])
arrow = Bullet(target.x, target.y + 20.0, 0.0, -12.0, is_player_bullet=True)
arrow.damage = 10.0
arrow.clear_radius_on_hit = cfg.PLAYER_SHOT_EXPLOSIVE_CLEAR_RADIUS
arrow.manager = state.bullet_manager
state.bullet_manager.add_player_bullet(arrow)
for _ in range(6):
    state.bullet_manager.update(1, state.player.x, state.player.y)
    PlayingState._check_collisions(state)
check("爆炸箭命中敌人：半径内敌弹进消弹、半径外不受影响",
      near_eb.cancel_timer > 0 and far_eb.cancel_timer == 0 and not arrow.alive,
      f"内 {near_eb.cancel_timer} / 外 {far_eb.cancel_timer}")
check("爆炸箭命中敌人：伤害照常结算且只结算一次",
      target.damage_taken == 10.0 and target.hits == 1,
      f"{target.damage_taken} / {target.hits}")

# --- 7) 与物品 / C 技能的组合（和发弹有关的效果逐条过一遍） ---
CHARACTERS = ("frozen_blaze", "mage", "archer", "tank")
# 表里的键与 item_effects 的口径一致（Terminator / Loving / Withered / Fabled /
# Necrotic 重铸石），直接喂给 _player_shoot 的聚合结果
ITEMS = {
    "无装备": {},
    "Terminator": {"terminator": True, "non_tracking_damage_pct": 35},
    "Loving": {"fixed_bullet_add": -1, "tracking_bullet_add": 1,
               "bomb_damage_pct": 8},
    "Withered": {"tracking_damage_pct": 20},
    "Fabled": {"non_tracking_damage_pct": 15},
    "Necrotic": {"fixed_double_damage_chance": 3},
    "上述全带": {"terminator": True, "non_tracking_damage_pct": 50,
                 "fixed_bullet_add": -1, "tracking_bullet_add": 1,
                 "tracking_damage_pct": 20,
                 "fixed_double_damage_chance": 3},
}


def geom(rows):
    """弹道几何（去掉伤害）：落点 / 速度 / 追踪 / 穿透 / 纵向落点"""
    return [(row[0], row[1], row[2], row[4], row[5], row[6]) for row in rows]


crashes = []
for label, effect in ITEMS.items():
    for character in CHARACTERS:
        for power in (0, 200, 400):
            for focused in (False, True):
                try:
                    shoot(character, power, focused, **effect)
                except Exception as exc:  # noqa: BLE001
                    crashes.append((label, character, power, focused, repr(exc)))
check("物品组合下四位自机都正常发弹（7 组效果 x 4 机体 x 3 档火力 x 低速）",
      not crashes, str(crashes[:2]))

geom_diffs = []
for label, effect in ITEMS.items():
    for power in (0, 200, 400):
        for focused in (False, True):
            new = geom(shoot("frozen_blaze", power, focused, **effect))
            old = geom(legacy_shoot(
                power, focused,
                fixed_bullet_add=int(effect.get("fixed_bullet_add", 0)),
                tracking_bullet_add=int(effect.get("tracking_bullet_add", 0)),
                terminator=bool(effect.get("terminator", False))))
            if new != old:
                geom_diffs.append((label, power, focused, new, old))
check("冰焰的弹道几何在全部物品组合下仍与改前逐发一致", not geom_diffs,
      str(geom_diffs[:1]))

term_bad = []
for character in CHARACTERS:
    for focused, expect in ((False, 4.5), (True, 0.5)):
        step = tilt_step(fixed_of(shoot(character, 400, focused,
                                        terminator=True)))
        if abs(step - expect) > 0.05:
            term_bad.append((character, focused, step))
check("Terminator 覆盖夹角：四机体高速 ±4.5°/条、低速 ±0.5°/条",
      not term_bad, str(term_bad))

loving = {name: len(fixed_of(shoot(name, 200, False, fixed_bullet_add=-1,
                                   tracking_bullet_add=1)))
          for name in CHARACTERS}
check("Loving（-1 固定弹）火力 200：冰焰 2 / 魔法使 4 / 弓手 4 / 重装 2 条",
      loving == {"frozen_blaze": 2, "mage": 4, "archer": 4, "tank": 2},
      str(loving))
capped = {name: len(fixed_of(shoot(name, 400, False, fixed_bullet_add=-1)))
          for name in CHARACTERS}
check("满火力时 Loving 的 -1 被上限吃掉（冰焰 3 / 魔法使 5，与旧版同口径）",
      capped == {"frozen_blaze": 3, "mage": 5, "archer": 5, "tank": 3},
      str(capped))
check("Loving 的 +1 追踪弹：冰焰 / 重装照旧生效，魔法使 / 弓手没有追踪弹可加",
      len(homing_of(shoot("frozen_blaze", 400, True,
                          tracking_bullet_add=1))) == 2
      and not homing_of(shoot("mage", 400, False, tracking_bullet_add=1))
      and not homing_of(shoot("archer", 400, False, tracking_bullet_add=1)))

check("Fabled（非追踪弹 +15%）：固定弹 10 -> 11.5（冰焰 / 魔法使同口径）",
      all(abs(row[3] - 11.5) < 1e-6
          for row in fixed_of(shoot("frozen_blaze", 400, False,
                                    non_tracking_damage_pct=15)))
      and all(abs(row[3] - 11.5) < 1e-6
              for row in fixed_of(shoot("mage", 400, False,
                                        non_tracking_damage_pct=15))))
check("Withered（追踪弹 +20%）：冰焰追踪弹 6.7 -> 8.0，魔法使固定弹不受影响",
      all(abs(row[3] - 8.0) < 1e-6
          for row in homing_of(shoot("frozen_blaze", 400, False,
                                     tracking_damage_pct=20)))
      and all(abs(row[3] - 10.0) < 1e-6
              for row in fixed_of(shoot("mage", 400, False,
                                        tracking_damage_pct=20))))

# Necrotic（重铸前缀）：低速状态下每颗固定弹有概率造成双倍伤害
check("Necrotic 只在低速生效：高速 + 100% 概率也不翻倍",
      all(abs(row[3] - 10.0) < 1e-6
          for row in fixed_of(shoot("frozen_blaze", 400, False,
                                    fixed_double_damage_chance=100))))
check("Necrotic 低速 + 100% 概率：固定弹全打 20，追踪弹仍是 6.7（不翻倍）",
      all(abs(row[3] - 20.0) < 1e-6
          for row in fixed_of(shoot("frozen_blaze", 400, True,
                                    fixed_double_damage_chance=100)))
      and all(abs(row[3] - 6.7) < 1e-6
              for row in homing_of(shoot("frozen_blaze", 400, True,
                                         fixed_double_damage_chance=100))))
check("Necrotic 对四位自机的固定弹都生效（含穿透弹 / 直立弹 / 扇形弹）",
      all(any(abs(row[3] - 20.0) < 1e-6
              for row in fixed_of(shoot(name, 400, True,
                                        fixed_double_damage_chance=100)))
          for name in CHARACTERS))
random.seed(20260925)
rows = []
for _ in range(200):                       # 200 轮齐射 = 1000 发固定弹
    rows += fixed_of(shoot("mage", 400, True,
                           fixed_double_damage_chance=3))
doubled = [row for row in rows if abs(row[3] - 20.0) < 1e-6]
ratio = len(doubled) / len(rows)
check("Necrotic 3%：低速下 1000 发固定弹里约 3% 打双倍",
      0.02 <= ratio <= 0.04, f"实测 {ratio:.1%}（{len(doubled)}/{len(rows)}）")

spirit = {}
for character in CHARACTERS:
    state = _state(character, 400, False)
    state.spirit_bow_timer = 600          # Spirit Bow 的 C 技能「追踪领域」
    PlayingState._player_shoot(state)
    rows = _rows(state)
    spirit[character] = (all(row[4] for row in rows), {row[5] for row in rows})
check("Spirit Bow（追踪领域）：四机体固定弹全部变追踪弹，穿透标记各自保持",
      all(homing for homing, _ in spirit.values())
      and spirit["mage"][1] == {True}
      and spirit["archer"][1] == {False}
      and spirit["tank"][1] == {False},
      str(spirit))


def _fly_homing(state, frames=24):
    for _ in range(frames):
        state.bullet_manager.update(1, state.player.x, state.player.y)
        PlayingState._update_homing_bullets(state)
        PlayingState._check_collisions(state)


state = _battle_state()
state.spirit_bow_timer = 600
PlayingState._player_shoot(state)          # 魔法使：5 条穿透弹，且被 Spirit Bow 变成追踪弹
_fly_homing(state)
enemy_a, enemy_b = state.enemies
check("魔法使 + Spirit Bow：每个目标的伤害 = 10 × 命中次数（同一发弹不会重复扣血）",
      abs(enemy_a.damage_taken - 10.0 * enemy_a.hits) < 1e-6
      and abs(enemy_b.damage_taken - 10.0 * enemy_b.hits) < 1e-6
      and enemy_a.hits > 0,
      f"A {enemy_a.damage_taken:.0f} 点/{enemy_a.hits} 次、"
      f"B {enemy_b.damage_taken:.0f} 点/{enemy_b.hits} 次")


# --- 8) 自机弹贴图按「当前运动方向」转正 ---
# 自机弹贴图按这一发的飞行方向转正（见 bullet._draw_player_sprite）：发射时就是发射
# 方向，追踪弹被 _update_homing_bullets 改向时同步刷新 angle，所以扇形弹与追踪弹
# 都跟着自己的方向走。敌弹那条路仍按原来的 angle 贴，本次不动。核对两件事：
#   8a) 飞行中的自机弹：贴图旋转角与飞行方向一致，扇形五条各不相同
#   8b) 载入界面的方向预热把本机体要用的每个方向都烤齐（第一发不现转）
import src.entities.bullet_atlas as bullet_atlas  # noqa: E402
from src.engine import hires  # noqa: E402
from src.ui import loading  # noqa: E402


def expected_rot(heading_deg, factor):
    """bullet._get_player_bullet_sprite 的旋转角口径（heading_deg：运动方向角）"""
    step = bullet_atlas.angle_step() if factor > 1 else 1
    return int(round((-90.0 - heading_deg) / step)) * step % 360


def player_shot_sprite_key(shot, factor=1):
    """这发自机弹绘制时会去取的缓存键（与 _get_player_bullet_sprite 同口径）"""
    path = shot.player_sprite_path or cfg.PLAYER_BULLET_SPRITE
    angle = shot.player_sprite_angle
    if angle is None:
        angle = float(getattr(cfg, "PLAYER_BULLET_SPRITE_ANGLE", 0.0) or 0.0)
    return (path, float(angle), expected_rot(math.degrees(shot.angle), factor),
            max(1, int(factor)))


def fly(shot, frames=8):
    """按真实帧推这发弹（战斗里 BulletManager 就是这么调的）"""
    for _ in range(frames):
        shot.update(1.0)
    return shot


state, fan = bullets_of("archer", 400, False)
for shot in fan:
    fly(shot)
fan_angles = [round(math.degrees(shot.angle), 4) for shot in fan]
check("飞行中的自机弹：贴图朝向 = 飞行方向，扇形五条各不相同",
      all(abs(shot.angle - math.atan2(shot.vy, shot.vx)) < 1e-9 for shot in fan)
      and len(set(fan_angles)) == len(fan), str(fan_angles))
fan_keys = [player_shot_sprite_key(shot) for shot in fan]
check("弓手扇形箭：五条各自一张按方向转好的贴图（中间那条是爆炸箭）",
      len(set(fan_keys)) == len(fan)
      and sum(1 for key in fan_keys if key[0].endswith("Explosive_Arrow.png")) == 1,
      str(sorted(os.path.basename(key[0]) + f"@{key[2]}" for key in fan_keys)))

# 追踪弹：_update_homing_bullets 改向时会同步刷新 angle（见 ui/menu.py），
# 贴图因此跟着转向走 —— 不是一直贴着发射那一刻的朝向
cfg.set_player_character("frozen_blaze")
homing_shot = bm.create_player_bullet(100.0, 400.0, homing=True)
launch_deg = math.degrees(homing_shot.angle)
homing_shot.vx, homing_shot.vy = 12.0, 0.0            # 模拟追踪逻辑把弹拉平
homing_shot.angle = math.atan2(homing_shot.vy, homing_shot.vx)
fly(homing_shot, 6)
check("自机追踪弹：改向之后贴图朝向跟着改（不再是发射方向）",
      abs(math.degrees(homing_shot.angle) - launch_deg) > 45.0
      and player_shot_sprite_key(homing_shot)
      != player_shot_sprite_key(bm.create_player_bullet(100.0, 400.0, homing=True)),
      f"{launch_deg:.1f}° -> {math.degrees(homing_shot.angle):.1f}°")

# 敌弹不受影响：没有新增朝向字段，贴图仍按原来的 angle（发射时给的角度，
# 螺旋弹由转向分支自己刷新，成网静止弹由 boss 那边显式赋值）
spiral = Bullet(400.0, 400.0, 0.0, -4.0, Bullet.TYPE_RICE, radius=3.0)
spiral.turn_rate = 0.06
spin_deg = math.degrees(spiral.angle)
fly(spiral, 12)
check("敌弹路径不受影响（仍按 angle 贴，没有新增朝向字段）",
      not hasattr(spiral, "facing") and not hasattr(spiral, "_last_x")
      and abs(spiral.angle - math.atan2(spiral.vy, spiral.vx)) < 1e-9
      and abs(math.degrees(spiral.angle) - spin_deg) > 1.0,
      f"{spin_deg:.2f}° -> {math.degrees(spiral.angle):.2f}°")


def prewarm_gaps(character, factor):
    """按载入界面预热一遍（见 loading._warm_bullet_sprite），返回仍缺的方向"""
    cfg.set_player_character(character)
    scale = hires.scale()
    hires.set_scale(factor)
    loading._warm_bullet_sprite()
    hires.set_scale(scale)
    probe = Bullet(0.0, 0.0, 0.0, -1.0)
    gaps = []
    for extra in [None] + cfg.player_shot_extra_sprites():
        path, angle = (None, None) if extra is None else (extra["path"], extra["angle"])
        probe.player_sprite_path = path
        probe.player_sprite_angle = angle
        for heading in cfg.player_shot_headings():
            probe.angle = heading
            if player_shot_sprite_key(probe, factor) not in bm._player_bullet_sprite:
                gaps.append(os.path.basename(path or cfg.PLAYER_BULLET_SPRITE)
                            + f"@{round(math.degrees(heading), 2)}°")
    return gaps


gaps = {(character, factor): prewarm_gaps(character, factor)
        for character in ("frozen_blaze", "mage", "archer", "tank")
        for factor in (1, 2, 3)}
check("载入界面预热：四位自机 x 三个倍率 x 每个可能方向都已烤齐（第一发不现转）",
      not any(gaps.values()), str({key: value for key, value in gaps.items() if value}))

print()
if failures:
    print(f"失败 {len(failures)} 项：" + "、".join(failures))
    sys.exit(1)
print("全部通过")
