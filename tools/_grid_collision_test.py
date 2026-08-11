# -*- coding: utf-8 -*-
# 端到端验证：电网光束整条线有伤害判定（玩家站到线上会触发死亡）
import os, sys, math
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import settings as cfg
from src.engine.game import Game
from src.ui.menu import PlayingState
from src.stages.stage2 import Stage2_DragonsNest

pygame.init()
game = Game()
st = Stage2_DragonsNest()
st.setup_boss()
ps = PlayingState(game, st)
b = st.boss
b.entering = False
b.phase = "non_spell"
b.combat_enabled = True

NAME = "闪符「Non-Directional Lightning」"
guard = 0
while (b.current_spell is None or b.current_spell.name != NAME) and guard < 5000 and b.alive:
    b.update(1/60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH/2, cfg.BATTLE_AREA_HEIGHT-80)
    b.take_damage(500)
    guard += 1
assert b.current_spell is not None and b.current_spell.name == NAME, "not in lightning spell"

# 推进到电网出现（timer 138 左右）
for _ in range(200):
    b.update(1/60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH/2, cfg.BATTLE_AREA_HEIGHT-80)

beams = [eb for eb in ps.bullet_manager.enemy_bullets if eb.bullet_type == "beam"]
assert beams, "no grid beams spawned"
print(f"grid beams spawned: {len(beams)} at spell timer={b.current_spell.timer}")

# 对照1：玩家站在远离电网的安全位置，不应死亡
lives_before = ps.lives
ps.player.x, ps.player.y = cfg.BATTLE_AREA_WIDTH/2, cfg.BATTLE_AREA_HEIGHT-120
ps._check_collisions()
assert ps.lives == lives_before, "player died at safe spot!"
print("safe spot: no death OK")

# 对照2：玩家站在某条光束的中点（线上），应死亡
beam = beams[0]
mx = beam.x + math.cos(beam.angle) * beam.beam_length * 0.5
my = beam.y + math.sin(beam.angle) * beam.beam_length * 0.5
lives_before = ps.lives
ps.player.x, ps.player.y = mx, my
ps.player._invincible_timer = 0  # 确保可被击中
ps._check_collisions()
assert ps.lives == lives_before - 1, f"standing on grid should kill player (lives {lives_before} -> {ps.lives})"
print(f"on-grid: death triggered OK (lives {lives_before} -> {ps.lives})")

# 对照3：玩家贴着光束但距离超出判定（垂直偏移 6px，判定 1.5+2.0=3.5），不应死亡
beam2 = [eb for eb in ps.bullet_manager.enemy_bullets if eb.bullet_type == "beam" and eb is not beam]
if beam2:
    b2 = beam2[0]
    px2 = b2.x + math.cos(b2.angle) * b2.beam_length * 0.5
    py2 = b2.y + math.sin(b2.angle) * b2.beam_length * 0.5
    offx = math.cos(b2.angle + math.pi/2)
    offy = math.sin(b2.angle + math.pi/2)
    lives_before = ps.lives
    ps.player.x, ps.player.y = px2 + offx * 8, py2 + offy * 8
    ps.player._invincible_timer = 0
    ps._check_collisions()
    assert ps.lives == lives_before, "player should NOT die 8px off the beam"
    print("8px off beam: no death OK")

# 对照4：玩家站在预警大圆标记中心（harmless），不应死亡
warn = [eb for eb in ps.bullet_manager.enemy_bullets if eb.bullet_type == "circle" and eb.harmless]
if warn:
    w = warn[0]
    lives_before = ps.lives
    ps.player.x, ps.player.y = w.x, w.y
    ps.player._invincible_timer = 0
    ps._check_collisions()
    assert ps.lives == lives_before, "warning marker should be harmless"
    print("warning marker center: no death OK")

print("ALL OK")
pygame.quit()