
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
import numpy as np
sys.path.insert(0, os.getcwd())
from src.engine.spell_bg import SpellBackground, detect_style, _pattern_cache, _get_pattern, STYLES

pygame.init()
screen = pygame.display.set_mode((576, 670))

names = ["罠符「Luxurious Spool」", "丝符「Soul String」", "蛛符「Tarantula's Tornado」", "魂符「Dark Queen's Soul」"]
for n in names:
    print("detect:", n, "->", detect_style(n))

icon_keys = [k for k in _pattern_cache if k.startswith("icon_")]
print("icon patterns:", sorted(icon_keys))

results = {}
for style in ("spool", "thread", "tornado", "soul"):
    bg = SpellBackground("test", bg_style=style)
    for i in range(40):
        bg.update(1/60)
    # 预热后计时 60 帧
    t0 = time.perf_counter()
    for i in range(60):
        bg.update(1/60)
        bg.draw(screen)
    dt = (time.perf_counter() - t0) / 60.0
    # 最终帧存盘
    bg.draw(screen)
    out = r"C:/Users/admin/.codex/visualizations/2026/08/08/019fe088-c704-7783-8622-d7523d22c933/spellbg_" + style + ".png"
    pygame.image.save(screen, out)
    arr = pygame.surfarray.array3d(screen).astype(np.float32)
    mean = arr.mean()
    p95 = np.percentile(arr, 95)
    bright = (arr.mean(axis=2) > 110).mean()
    print("%s: mean=%.1f p95=%.1f bright_frac=%.4f  draw=%.2fms" % (style, mean, p95, bright, dt*1000))
    results[style] = dt*1000

# 生命周期：淡出到 done
bg = SpellBackground("test", bg_style="spool")
for i in range(25):
    bg.update(1/60)
bg.begin_fade_out()
for i in range(40):
    bg.update(1/60)
print("fade done:", bg.done)
print("icons sizes:", {k: _get_pattern(k).get_size() for k in sorted(icon_keys)})
pygame.quit()
print("ALL OK")
