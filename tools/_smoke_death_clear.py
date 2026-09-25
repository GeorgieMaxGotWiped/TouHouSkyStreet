# -*- coding: utf-8 -*-
# 临时脚本：六面「击破清弹 / 离场清弹」与最后一波编成的验证
import os, sys, math
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.engine import settings as cfg
from src.engine import game as game_module
from src.entities.bullet import BulletManager, create_bullet_angle, Bullet
from src.stages import stage6 as s6

pygame.init()
_orig = game_module.load_user_config
game_module.load_user_config = lambda: dict(_orig(), fullscreen=False, render_scale_index=0)
game = game_module.Game()
from src.ui.menu import PlayingState


def seed(bm, x, y, n=12, ring=120.0):
    """在 (x, y) 周围放 n 发静止敌弹（半径 10 ~ ring 均匀铺开）"""
    for i in range(n):
        r = 10.0 + (ring - 10.0) * i / max(1, n - 1)
        b = create_bullet_angle(x + r, y, 0.0, 0.0, Bullet.TYPE_CIRCLE, radius=2.5,
                                color=(255, 255, 255), lifetime=600)
        bm.add_enemy_bullet(b)
    return n


def dist(b, x, y):
    return math.hypot(b.x - x, b.y - y)


# ---------- 1. 小怪被击破：半径内清掉、半径外不动（走真实的击破奖励路径） ----------
state = PlayingState(game, s6.Stage6_FinalApproach())
game.push_state(state)
state.stage.setup_waves()
guards = []
for _ in range(3000):                      # 跑到守卫真的登场（玩家中弹会拖慢关卡计时）
    state.update(1 / 60.0)
    guards = [e for e in state.stage.enemy_manager.get_active_enemies()
              if isinstance(e, s6.WitherGuardEnemy)]
    if guards:
        break
assert guards, "no guard"
g = guards[0]
radius = state.stage.enemy_death_clear_radius(g)
bm = state.bullet_manager
bm.enemy_bullets.clear()
seed(bm, g.x, g.y, n=12, ring=110.0)
inside = [b for b in bm.enemy_bullets if dist(b, g.x, g.y) <= radius]
outs = [b for b in bm.enemy_bullets if dist(b, g.x, g.y) > radius]
calls = []
orig_clear = state._death_clear_bullets
state._death_clear_bullets = lambda e: (calls.append(e), orig_clear(e))[1]
while g.alive:
    g.take_damage(9999)
state._reward_enemy_kill(g)
state._death_clear_bullets = orig_clear
hung_in = [b for b in inside if b.cancel_timer > 0]
hung_out = [b for b in outs if b.cancel_timer > 0]
print("[1] 守护 size=%d -> 半径 %.0f：击破奖励里调用清弹 %d 次；半径内 %d 发全清=%s；半径外 %d 发被误清=%d"
      % (g.size, radius, len(calls), len(hung_in), len(hung_in) == len(inside),
         len(outs), len(hung_out)))
assert calls and len(hung_in) == len(inside) and not hung_out

# ---------- 2. 残影离场：大范围清弹 ----------
stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm2 = BulletManager()
for _ in range(78 * 60 - 3):               # 停在 Storm 登场前几帧：此刻 Maxor 仍在场
    stage.update(1 / 60.0, bm2, 288.0, 560.0); bm2.update(1 / 60.0, 288.0, 560.0)
assert [x["id"] for x in stage.ghosts] == ["maxor"], [x["id"] for x in stage.ghosts]
bm2.enemy_bullets.clear()
near = {}
for gid in ("maxor", "storm"):
    gx, gy = s6.GHOST_POSITIONS[gid]
    seed(bm2, gx, gy, n=14, ring=260.0)
    near[gid] = [b for b in bm2.enemy_bullets if dist(b, gx, gy) <= s6.GHOST_CLEAR_RADIUS]
for _ in range(12):                        # 跨过 78s：Maxor 离场 + Storm 登场
    stage.update(1 / 60.0, bm2, 288.0, 560.0); bm2.update(1 / 60.0, 288.0, 560.0)
assert [x["id"] for x in stage.ghosts] == ["storm"], [x["id"] for x in stage.ghosts]
mx, my = s6.GHOST_POSITIONS["maxor"]
hung = [b for b in bm2.enemy_bullets if b.cancel_timer > 0]
mx_clear = [b for b in hung if dist(b, mx, my) <= s6.GHOST_CLEAR_RADIUS]
print("[2] 残影离场半径 %.0f：Maxor 周围 %d 发里清了 %d 发（离场那一帧）"
      % (s6.GHOST_CLEAR_RADIUS, len(near["maxor"]), len(mx_clear)))
assert len(mx_clear) >= len(near["maxor"])   # 可能顺带清到刚登场的下一位的起手弹

# Storm 离场（86s、Goldor 登场）同样清弹
while stage.timer < 86 * 60 - 3:
    stage.update(1 / 60.0, bm2, 288.0, 560.0); bm2.update(1 / 60.0, 288.0, 560.0)
sx, sy = s6.GHOST_POSITIONS["storm"]
near_st = [b for b in bm2.enemy_bullets if dist(b, sx, sy) <= s6.GHOST_CLEAR_RADIUS]
for _ in range(12):
    stage.update(1 / 60.0, bm2, 288.0, 560.0); bm2.update(1 / 60.0, 288.0, 560.0)
st_clear = [b for b in bm2.enemy_bullets
            if b.cancel_timer > 0 and dist(b, sx, sy) <= s6.GHOST_CLEAR_RADIUS]
print("    Storm 离场时：周围 %d 发里清了 %d 发" % (len(near_st), len(st_clear)))
miss = [b for b in near_st if b.alive and b.cancel_timer <= 0
        and dist(b, sx, sy) <= s6.GHOST_CLEAR_RADIUS]
assert not miss, len(miss)      # 半径内还「活着且没被清」的应为 0

# ---------- 3. 最后一波编成 ----------
stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm3 = BulletManager()
for _ in range(100 * 60 + 2):
    stage.update(1 / 60.0, bm3, 288.0, 560.0); bm3.update(1 / 60.0, 288.0, 560.0)
kinds = {}
for e in stage.final_wave.enemies:
    kinds[type(e).__name__] = kinds.get(type(e).__name__, 0) + 1
print("[3] Final Defense 编成:", kinds)
assert kinds == {"WitherColossusEnemy": 1, "SkeletonLordEnemy": 2,
                 "WitherGuardEnemy": 2}, kinds
for e in sorted(stage.final_wave.enemies, key=lambda e: e.x):
    print("       %-22s x=%-4.0f y=%-4.0f" % (type(e).__name__, e.x, e.y))
print("[4] 各小怪击破清弹半径:",
      {c.__name__.replace("Enemy", ""): c(0, 0).size * s6.CLEAR_RADIUS_PER_SIZE
       for c in (s6.WitherHuskEnemy, s6.WitherMinerEnemy, s6.WitherKnightEnemy,
                 s6.WitherGuardEnemy, s6.SkeletonLordEnemy)})
game.running = False
print("CLEAR_OK")
