# -*- coding: utf-8 -*-
# 临时脚本：六面道中「守卫/矿工直接在画面内上部出现 + 游魂变快变多」实机预览
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

MARKS = [(9.2, "9s Undead Line"), (14.2, "14s Miner Phalanx"),
         (19.2, "19s Fortress Gate"), (29.2, "29s Guard Wall"),
         (34.2, "34s Last March"), (68.2, "68s Fortress Wall"),
         (82.2, "82s Knight Order"), (100.2, "100s Final Defense")]


def tally(alive):
    out = {}
    for e in alive:
        k = type(e).__name__.replace("Enemy", "").replace("Wither", "").replace("Skeleton", "Skel")
        out[k] = out.get(k, 0) + 1
    return " ".join("%s%d" % (k, v) for k, v in sorted(out.items()))


stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm = BulletManager()
want = {int(round(m * 60)): m for m, _ in MARKS}
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
        frames[t] = screen.subsurface(pygame.Rect(
            0, 0, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT)).copy()
        alive = [e for e in stage.enemy_manager.active_enemies if e.alive]
        inside = [e.y for e in alive if e.y > 0]
        info[t] = ("弹 %-3d 框内最高 y=%-4.0f　%s" % (
            len(bm.enemy_bullets), min(inside) if inside else -1, tally(alive)),)
    t += 1

tw, th, pad, label_h, cols = 302, 351, 8, 34, 4
rows = (len(MARKS) + cols - 1) // cols
sheet = pygame.Surface(((tw + pad) * cols + pad, 40 + pad + (label_h + th + pad) * rows))
sheet.fill((26, 28, 34))
sheet.blit(pygame.font.SysFont(F, 15).render(
    "六面道中：凋零守卫 / 凋零矿工改为直接在画面内上部出现（不再从区域外落下）；凋零游魂速度 1.5→3.0、每波数量 ×2",
    True, (240, 240, 246)), (pad + 2, 5))
sheet.blit(pygame.font.SysFont(F, 13).render(
    "凋零游魂（Husk）仍从区域外落下：框内最高 y 是它的位置；守卫 / 矿工的落点固定在 y=220~330，开场就在画面里",
    True, (168, 186, 210)), (pad + 2, 23))
for i, (m, title) in enumerate(MARKS):
    r, c = divmod(i, cols)
    x, y = pad + c * (tw + pad), 40 + pad + r * (label_h + th + pad)
    tk = int(round(m * 60))
    sheet.blit(f_l.render(title, True, (240, 240, 246)), (x, y + 1))
    sheet.blit(f_s.render(info[tk][0], True, (176, 200, 228)), (x, y + 18))
    sheet.blit(pygame.transform.smoothscale(frames[tk], (tw, th)), (x, y + label_h))
    print("  %-20s %s" % (title, info[tk][0]))
out = os.path.join(OUT, "s6_topspawn_hardline.png")
pygame.image.save(sheet, out)
print("saved", out, sheet.get_size())
print("RENDER_OK")
