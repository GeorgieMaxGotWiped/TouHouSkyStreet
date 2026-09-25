# -*- coding: utf-8 -*-
# 临时脚本：Skeleton Lord 黄绿交替螺旋弹 实机预览
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager
from src.stages import stage6 as s6

OUT = r"C:\Users\admin\.codex\visualizations\2026\09\25\01a0d626-88d7-7b43-be2a-ef20c066fb95"
F = "Microsoft YaHei,SimHei,Arial"
pygame.init()
screen = pygame.display.set_mode((960, 720))
f_l = pygame.font.SysFont(F, 15)
f_s = pygame.font.SysFont(F, 13)

MARKS = [4.6, 5.0, 5.5, 6.0, 6.6, 7.5, 9.0, 11.0]


def audit(surf):
    """统计画面里黄鳞弹 / 绿鳞弹的像素量。"""
    yellow = green = 0
    for y in range(0, surf.get_height(), 2):
        for x in range(0, surf.get_width(), 2):
            r, g, b, a = surf.get_at((x, y))
            if a < 200:
                continue
            if r > 140 and g > 110 and b < 90:
                yellow += 1
            elif g > 110 and r < 90 and b < 90:
                green += 1
    return yellow, green


stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm = BulletManager()
want = {int(round(m * 60)): m for m in MARKS}
frames, info = {}, {}
t = 0
while t <= max(want):
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
    bm.update(1.0 / 60.0, 288.0, 560.0)
    if t in want:
        screen.fill((0, 0, 0))
        stage.draw(screen, 0, 0)
        bm.draw(screen, 0, 0)
        stage.draw_foreground(screen, 0, 0)
        area = screen.subsurface(pygame.Rect(0, 0, cfg.BATTLE_AREA_WIDTH,
                                             cfg.BATTLE_AREA_HEIGHT)).copy()
        frames[t] = area
        yl, gr = audit(area)
        lords = [e for e in stage.enemy_manager.active_enemies
                 if isinstance(e, s6.SkeletonLordEnemy) and e.alive]
        info[t] = ("弹 %d（螺旋鳞弹 %d）　黄像素 %d / 绿像素 %d" % (
            len(bm.enemy_bullets),
            len([b for b in bm.enemy_bullets if b.bullet_type == "scale"]), yl, gr),
            "轮次 %s" % "+".join(str(e.volley) for e in lords))
    t += 1

tw, th, pad, label_h, cols = 300, 349, 8, 38, 4
rows = (len(MARKS) + cols - 1) // cols
sheet = pygame.Surface(((tw + pad) * cols + pad, (label_h + th + pad) * rows + pad + 26))
sheet.fill((26, 28, 34))
sheet.blit(pygame.font.SysFont(F, 16).render(
    "六面首波 Skeleton Lords：黄绿交替螺旋鳞弹（每 6 帧一轮 5 发、每轮偏转 1.10 弧度，左右镜像）",
    True, (240, 240, 246)), (pad + 2, 5))
for i, m in enumerate(MARKS):
    r, c = divmod(i, cols)
    x, y = pad + c * (tw + pad), 26 + pad + r * (label_h + th + pad)
    t_key = int(round(m * 60))
    l1, l2 = info[t_key]
    sheet.blit(f_l.render("%.2fs　%s" % (m, l1), True, (240, 240, 246)), (x, y + 2))
    sheet.blit(f_s.render(l2, True, (176, 200, 228)), (x, y + 20))
    sheet.blit(pygame.transform.smoothscale(frames[t_key], (tw, th)), (x, y + label_h))
    print("  %.2fs  %s  %s" % (m, l1, l2))
out = os.path.join(OUT, "s6_lord_colors.png")
pygame.image.save(sheet, out)
print("saved", out, sheet.get_size())
print("RENDER_OK")
