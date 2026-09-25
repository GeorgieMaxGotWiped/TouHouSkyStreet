# -*- coding: utf-8 -*-
# 临时脚本：核对残影接力时间轴（登场/退场/起手/背景交接）
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from src.entities.bullet import BulletManager
from src.stages import stage6 as s6

pygame.init()
screen = pygame.display.set_mode((320, 240))

stage = s6.Stage6_FinalApproach()
stage.setup_waves()
bm = BulletManager()
px, py = 288.0, 560.0
events = {}
prev_ids = set()
prev_bg = None
first_bullet = {}
for _ in range(s6.GHOST_PLAN[-1][0] + 260):
    stage.update(1.0 / 60.0, bm, px, py)
    bm.update(1.0 / 60.0, px, py)
    ids = {g["id"]: g for g in stage.ghosts}
    for gid, g in ids.items():
        if gid not in events:
            events[gid] = {"in": stage.timer, "age_in": g["age"]}
    for gid in list(events):
        if gid not in ids and "out" not in events[gid]:
            events[gid]["out"] = stage.timer
    if stage.ghost_bg is not prev_bg:
        if stage.ghost_bg is not None and prev_bg is None:
            pass
        prev_bg = stage.ghost_bg
    n = len(bm.enemy_bullets)
    for gid, g in ids.items():
        if gid not in first_bullet and n:
            first_bullet[gid] = (stage.timer, g["age"] - 1)   # 读取时 age 已自增

print("残影时间轴（帧；60FPS）")
for t0, gid in s6.GHOST_PLAN:
    e = events[gid]
    span = e.get("out", stage.timer) - e["in"]
    print("  %-7s 登场 %5d (%.2fs)  退场 %s  存活 %3d 帧 (%.2fs)  首个弹幕帧 age=%s（0 = 登场那一帧）"
          % (gid, e["in"], e["in"] / 60.0, e.get("out"), span, span / 60.0,
             first_bullet.get(gid, (None, None))[1]))
end = events["necron"].get("out")
print("  残影段：%d .. %d 帧 = %.2fs .. %.2fs（合计 %.2fs）"
      % (s6.GHOST_PLAN[0][0], end, s6.GHOST_PLAN[0][0] / 60.0, end / 60.0,
         (end - s6.GHOST_PLAN[0][0]) / 60.0))
print("  对照（旧版 4x190 帧 + 间隔）：70.00s .. %.2fs" % ((94 * 60 + 190) / 60.0))
print("OK")
