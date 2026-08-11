# -*- coding: utf-8 -*-
# 闪符电网高密度状态渲染耗时实测
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
from src.stages.stage2 import Stage2_DragonsNest

px, py = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80
st = Stage2_DragonsNest()
st.setup_boss()
b = st.boss
b.entering = False
b.phase = "non_spell"
b.combat_enabled = True
bm = BulletManager()
guard = 0
while (b.current_spell is None or b.current_spell.name != "闪符「Non-Directional Lightning」") and guard < 200000 and b.alive:
    b.update(1 / 60, bm, px, py)
    b.take_damage(500)
    guard += 1
for _ in range(614):
    b.update(1 / 60, bm, px, py)
print("bullets now:", len(bm.enemy_bullets))
# 计时完整一帧绘制（含背景/符卡背景/Boss/子弹）
t0 = time.perf_counter()
N = 120
for _ in range(N):
    screen.fill((0, 0, 0))
    st.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    bm.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
dt = (time.perf_counter() - t0) / N
print(f"full frame draw: {dt*1000:.2f} ms  -> 60fps 余量 {16.6-dt*1000:.2f} ms")
pygame.quit()