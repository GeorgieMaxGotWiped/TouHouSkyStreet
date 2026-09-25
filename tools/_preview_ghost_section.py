# -*- coding: utf-8 -*-
# 临时脚本：残影段实机画面（70~97s，模拟玩家已清掉首波两位 Lord，段内不应出现小怪）
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
f_l = pygame.font.SysFont(F, 14)
f_s = pygame.font.SysFont(F, 12)

MARKS = [(71.0, "71s Maxor"), (79.0, "79s Storm"), (87.0, "87s Goldor"), (95.0, "95s Necron")]

stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm = BulletManager()
want = {int(round(m * 60)): m for m, _ in MARKS}
frames, info = {}, {}
t = 0
while t <= max(want):
    # 首波两位 Skeleton Lord 一出现就击破 —— 模拟真实战斗中玩家早已清掉它们
    for e in stage.enemy_manager.get_active_enemies():
        if isinstance(e, s6.SkeletonLordEnemy):
            while e.alive:
                e.take_damage(9999)
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
    bm.update(1.0 / 60.0, 288.0, 560.0)
    if t in want:
        screen.fill((0, 0, 0))
        stage.draw(screen, 0, 0)
        bm.draw(screen, 0, 0)
        stage.draw_foreground(screen, 0, 0)
        frames[t] = screen.subsurface(pygame.Rect(
            0, 0, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT)).copy()
        info[t] = "小怪 %d 只　残影 %d 位　敌弹 %d 发" % (
            len(stage.enemy_manager.get_active_enemies()), len(stage.ghosts),
            len(bm.enemy_bullets))
    t += 1

tw, th, pad, label_h, cols = 300, 349, 8, 36, 4
sheet = pygame.Surface(((tw + pad) * cols + pad, 44 + pad + label_h + th + pad))
sheet.fill((26, 28, 34))
sheet.blit(pygame.font.SysFont(F, 16).render(
    "六面残影段（70~97s）：段内不再生成任何小怪，只有四位门徒接力登场 + 各自的加强弹幕", True, (240, 240, 246)), (pad + 2, 5))
sheet.blit(f_s.render("画面按真实时间轴跑，只是把首波那两位 Skeleton Lord 一出现就击破（真实战斗里它们早被玩家打掉了）",
                      True, (168, 186, 210)), (pad + 2, 26))
for i, (m, title) in enumerate(MARKS):
    x = pad + i * (tw + pad)
    tk = int(round(m * 60))
    sheet.blit(f_l.render("%s　%s" % (title, info[tk]), True, (240, 240, 246)), (x, 44 + pad - 18))
    sheet.blit(pygame.transform.smoothscale(frames[tk], (tw, th)), (x, 44 + pad + label_h - 18))
    print("  %-12s %s" % (title, info[tk]))
out = os.path.join(OUT, "s6_ghost_section.png")
pygame.image.save(sheet, out)
print("saved", out, sheet.get_size())
print("RENDER_OK")
