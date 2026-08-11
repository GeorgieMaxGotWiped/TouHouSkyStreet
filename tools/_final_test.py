
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
import numpy as np
sys.path.insert(0, os.getcwd())
from src.engine.spell_bg import SpellBackground, _get_pattern, EFFECT_CENTER

pygame.init()
screen = pygame.display.set_mode((576, 670))

# 1) 图标亮度复核
for key in ("icon_spool", "icon_arack", "icon_essence"):
    pat = _get_pattern(key)
    arr = pygame.surfarray.array3d(pat).astype(np.float32)
    a = pygame.surfarray.array_alpha(pat)
    lum = arr.mean(axis=2)
    px = lum[a > 8]
    print("%-13s max_lum=%.0f mean_lum=%.0f" % (key, px.max(), px.mean()))

# 2) 每风格 300 帧稳定性 + 性能（含 orbit 层）
for style in ("spool", "thread", "tornado", "soul"):
    bg = SpellBackground("test", bg_style=style)
    t0 = time.perf_counter()
    for i in range(300):
        bg.update(1/60)
        bg.draw(screen)
    dt = (time.perf_counter() - t0) / 300.0
    print("%-8s 300f ok, avg=%.2fms" % (style, dt * 1000))

# 3) orbit 位置随时间变化检查（tornado: essence 在 t=60 vs t=180 位置应不同）
bg = SpellBackground("test", bg_style="tornado")
positions = []
for target_t in (60, 180):
    while bg.timer < target_t:
        bg.update(1/60)
    bg.draw(screen)
    arr = pygame.surfarray.array3d(screen).astype(np.float32)
    lum = arr.mean(axis=2)
    cx, cy = int(EFFECT_CENTER[0]), int(EFFECT_CENTER[1])
    ring = lum[cy-190:cy+190, cx-160:cx+160]
    ys, xs = np.nonzero(ring > 60)
    if len(ys):
        positions.append((float(xs.mean()) + cx - 160, float(ys.mean()) + cy - 190))
print("orbit centroid t60:", [round(p[0],1) for p in positions], [round(p[1],1) for p in positions])
print("orbit moved:", len(positions) == 2 and abs(positions[0][0]-positions[1][0]) > 3)
pygame.quit()
print("ALL OK")
