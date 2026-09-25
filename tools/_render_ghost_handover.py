# -*- coding: utf-8 -*-
# 临时脚本：残影接力时间轴的画面（登场即弹幕 / 交接 / 收尾）
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager
from src.stages import stage6 as s6

OUT = r"C:\Users\admin\.codex\visualizations\2026\09\25\01a0d626-88d7-7b43-be2a-ef20c066fb95"
pygame.init()
screen = pygame.display.set_mode((960, 720))
font = pygame.font.SysFont("Microsoft YaHei,SimHei,Arial", 15)

# (标签, 采样帧)
MARKS = [
    ("maxor 登场 70.00s", (4200, 4203, 4218, 4240)),
    ("交接 maxor -> storm", (4678, 4680, 4686, 4700)),
    ("交接 goldor -> necron", (5638, 5640, 5650, 5680)),
    ("收尾 necron 退场", (5826, 5828, 5830, 5866)),
]


def make_stage():
    stage = s6.Stage6_FinalApproach()
    stage.setup_waves()
    return stage


def shot(stage, bm):
    screen.fill((0, 0, 0))
    stage.draw(screen, 0, 0)
    bm.draw(screen, 0, 0)
    stage.draw_foreground(screen, 0, 0)
    return screen.subsurface(pygame.Rect(0, 0, cfg.BATTLE_AREA_WIDTH,
                                         cfg.BATTLE_AREA_HEIGHT)).copy()


def main():
    stage, bm = make_stage(), BulletManager()
    frames = {}
    want = sorted({f for _, fs in MARKS for f in fs})
    last = want[-1]
    while stage.timer <= last:
        stage.update(1.0 / 60.0, bm, 288.0, 560.0)
        bm.update(1.0 / 60.0, 288.0, 560.0)
        if stage.timer in want:
            frames[stage.timer] = (shot(stage, bm),
                                   sorted(g["id"] for g in stage.ghosts))

    tw, th = 318, 370
    pad, label_h = 8, 24
    sheet = pygame.Surface(((tw + pad) * 4 + pad, (label_h + th + pad) * 4 + pad))
    sheet.fill((26, 28, 34))
    for r, (title, marks) in enumerate(MARKS):
        for c, frame_no in enumerate(marks):
            frame, ghosts = frames[frame_no]
            x = pad + c * (tw + pad)
            y = pad + r * (label_h + th + pad)
            label = "%s  %.2fs  在场:%s" % (title, frame_no / 60.0,
                                          "/".join(ghosts) or "无")
            sheet.blit(font.render(label, True, (235, 235, 240)), (x, y + 3))
            sheet.blit(pygame.transform.smoothscale(frame, (tw, th)), (x, y + label_h))
            print("  %-22s %.2fs  ghosts=%s" % (title, frame_no / 60.0, ghosts))
    out = os.path.join(OUT, "s6_ghost_handover.png")
    pygame.image.save(sheet, out)
    print("sheet:", out, sheet.get_size())
    print("RENDER_OK")


main()
