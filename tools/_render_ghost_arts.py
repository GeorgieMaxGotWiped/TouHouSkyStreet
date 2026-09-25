# -*- coding: utf-8 -*-
# 临时脚本：new / another 两套立绘的原图对比（同高）+ 像素差异校验，并渲染残影近景
import os, sys, time
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
IDS = ("maxor", "storm", "goldor", "necron")


def art_sheet():
    th = 330
    tiles = {}
    for art in ("new", "another"):
        cfg.set_boss_art(art)
        for gid in IDS:
            p = cfg.boss_art_path(gid)
            img = pygame.image.load(p)
            w, h = img.get_size()
            tiles[(art, gid)] = pygame.transform.smoothscale(
                img, (max(1, int(round(w * th / h))), th))
    pad, label_h = 10, 26
    colw = max(t.get_width() for t in tiles.values()) + pad
    W = pad + 4 * colw
    H = pad + 2 * (label_h + th + pad)
    sheet = pygame.Surface((W, H))
    sheet.fill((30, 32, 40))
    for r, art in enumerate(("new", "another")):
        for c, gid in enumerate(IDS):
            x = pad + c * colw
            y = pad + r * (label_h + th + pad)
            sheet.blit(font.render("%s  /  %s" % (art, gid), True, (235, 235, 240)),
                       (x + 4, y + 4))
            sheet.blit(tiles[(art, gid)], (x + 4, y + label_h))
    out = os.path.join(OUT, "wither_art_sets_2x4.png")
    pygame.image.save(sheet, out)
    print("art sheet:", out, sheet.get_size())


def pixel_diff():
    thumbs = {}
    for art in ("new", "another"):
        cfg.set_boss_art(art)
        for gid in IDS:
            img = pygame.image.load(cfg.boss_art_path(gid))
            thumbs[(art, gid)] = pygame.transform.smoothscale(img, (64, 96))
    for gid in IDS:
        a = pygame.surfarray.array3d(thumbs[("new", gid)]).astype(int)
        b = pygame.surfarray.array3d(thumbs[("another", gid)]).astype(int)
        print("  %-7s new vs another mean|diff| = %.1f" % (gid, abs(a - b).mean()))


def make_stage():
    stage = s6.Stage6_FinalApproach()
    stage.setup_waves()
    return stage


def run_to(stage, bm, target):
    px, py = 288.0, 560.0
    while stage.timer < target:
        stage.update(1.0 / 60.0, bm, px, py)
        bm.update(1.0 / 60.0, px, py)


def ghost_shot(stage, bm, gid):
    screen.fill((0, 0, 0))
    stage.draw(screen, 50, 25)
    bm.draw(screen, 50, 25)
    stage.draw_foreground(screen, 50, 25)
    cx = s6.GHOST_POSITIONS[gid][0]
    return screen.subsurface(pygame.Rect(50 + cx - 112, 25, 224, 232)).copy()


def ghost_sheet():
    spawns = {"maxor": 70 * 60, "storm": 78 * 60, "goldor": 86 * 60, "necron": 94 * 60}
    rows = []
    for art in ("new", "another"):
        cfg.set_boss_art(art)
        stage, bm = make_stage(), BulletManager()
        frames = []
        for gid in IDS:
            run_to(stage, bm, spawns[gid] + 84)
            assert stage.ghosts and stage.ghosts[0]["id"] == gid
            frames.append(ghost_shot(stage, bm, gid))
        rows.append((art, frames))
    scale = 1.45
    tw, th = int(224 * scale), int(232 * scale)
    pad, label_h = 8, 24
    sheet = pygame.Surface(((tw + pad) * 4 + pad, (label_h + th + pad) * 2 + pad))
    sheet.fill((26, 28, 34))
    for r, (art, frames) in enumerate(rows):
        for c, (gid, frame) in enumerate(zip(IDS, frames)):
            x = pad + c * (tw + pad)
            y = pad + r * (label_h + th + pad)
            sheet.blit(font.render("%s  /  %s" % (art, gid), True, (235, 235, 240)),
                       (x, y + 3))
            sheet.blit(pygame.transform.smoothscale(frame, (tw, th)), (x, y + label_h))
    out = os.path.join(OUT, "s6_ghost_art_sets.png")
    pygame.image.save(sheet, out)
    print("ghost sheet:", out, sheet.get_size())


art_sheet()
pixel_diff()
ghost_sheet()
print("RENDER_OK")

