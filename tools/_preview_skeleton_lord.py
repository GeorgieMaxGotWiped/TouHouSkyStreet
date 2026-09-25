# -*- coding: utf-8 -*-
# 临时脚本：Skeleton Lord 第一波预览（入场 / 到位即开火 / 螺旋铺开 / 密度）
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from src.engine import settings as cfg
from src.entities.bullet import Bullet, BulletManager, create_bullet_angle
from src.stages import stage6 as s6

OUT = r"C:\Users\admin\.codex\visualizations\2026\09\25\01a0d626-88d7-7b43-be2a-ef20c066fb95"
pygame.init()
screen = pygame.display.set_mode((960, 720))
F = "Microsoft YaHei,SimHei,Arial"
f_line = pygame.font.SysFont(F, 15)
f_small = pygame.font.SysFont(F, 12)

MARKS = [("4.00s 左右同时切入", 240), ("4.35s 切入中", 261),
         ("4.47s 到位", 268), ("4.72s 首轮螺旋", 283), ("5.00s 螺旋成形", 300),
         ("6.00s 铺开", 360), ("8.00s 满密度", 480), ("10.00s 稳定密度", 600)]

stage = s6.Stage6_FinalApproach()
stage.setup_waves()
bm = BulletManager()
want = {t for _, t in MARKS}
frames, info, peak = {}, {}, (0, 0)
while stage.timer <= max(want):
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
    bm.update(1.0 / 60.0, 288.0, 560.0)
    if len(bm.enemy_bullets) > peak[1]:
        peak = (stage.timer, len(bm.enemy_bullets))
    if stage.timer in want:
        screen.fill((0, 0, 0))
        stage.draw(screen, 0, 0)
        bm.draw(screen, 0, 0)
        stage.draw_foreground(screen, 0, 0)
        frames[stage.timer] = screen.subsurface(pygame.Rect(
            0, 0, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT)).copy()
        lords = [e for e in stage.enemy_manager.get_active_enemies()
                 if isinstance(e, s6.SkeletonLordEnemy)]
        info[stage.timer] = "鳞弹 %d　Lord x=%s 到位=%s" % (
            len(bm.enemy_bullets),
            "/".join("%.0f" % e.x for e in lords) or "-",
            "/".join("是" if e.entered else "否" for e in lords) or "-")

tw, th, pad, label_h, cols = 384, 447, 8, 24, 3
rows = (len(MARKS) + cols - 1) // cols
sheet = pygame.Surface(((tw + pad) * cols + pad, (label_h + th + pad) * rows + pad))
sheet.fill((26, 28, 34))
for i, (title, t) in enumerate(MARKS):
    r, c = divmod(i, cols)
    x, y = pad + c * (tw + pad), pad + r * (label_h + th + pad)
    sheet.blit(f_line.render("%s　%s" % (title, info[t]), True, (240, 240, 246)), (x, y + 3))
    sheet.blit(pygame.transform.smoothscale(frames[t], (tw, th)), (x, y + label_h))
    print("  %-20s %s" % (title, info[t]))
print("弹量峰值 %d 发 @ 第 %d 帧（%.2fs）" % (peak[1], peak[0], peak[0] / 60.0))
out = os.path.join(OUT, "s6_skeleton_lord_wave.png")
pygame.image.save(sheet, out)
print("saved", out, sheet.get_size())
print("RENDER_OK")
