# -*- coding: utf-8 -*-
# 临时脚本：渲染四位残影的「一小段削弱版符卡」并统计弹量
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

IDS = ("maxor", "storm", "goldor", "necron")
SPAWNS = {"maxor": 70 * 60, "storm": 78 * 60, "goldor": 86 * 60, "necron": 94 * 60}
SHOTS = (2, 24, 46, 74)


def make_stage():
    stage = s6.Stage6_FinalApproach()
    stage.setup_waves()
    return stage


def run_to(stage, bm, target):
    while stage.timer < target:
        stage.update(1.0 / 60.0, bm, 288.0, 560.0)
        bm.update(1.0 / 60.0, 288.0, 560.0)


def clear_field(stage, bm):
    for e in stage.enemy_manager.get_active_enemies():
        while e.alive:
            e.take_damage(9999)
    bm.enemy_bullets.clear()


def shot(stage, bm):
    screen.fill((0, 0, 0))
    stage.draw(screen, 0, 0)
    bm.draw(screen, 0, 0)
    stage.draw_foreground(screen, 0, 0)
    return screen.subsurface(pygame.Rect(0, 0, cfg.BATTLE_AREA_WIDTH,
                                         cfg.BATTLE_AREA_HEIGHT)).copy()


def count_ghost_bullets():
    """只统计 _ghost_spell 自己打出来的弹（干净弹幕管理器，不看小怪）"""
    print("残影片段弹量（单位：发；每段 80 帧）")
    for gid in IDS:
        bm = BulletManager()
        ghost = {"id": gid, "x": s6.GHOST_POSITIONS[gid][0],
                 "y": s6.GHOST_POSITIONS[gid][1], "age": 0, "max_age": 190}
        kinds = {}
        for age in range(1, 191):
            ghost["age"] = age
            before = len(bm.enemy_bullets)
            s6._ghost_spell(ghost, bm, 288.0, 560.0)
            for b in bm.enemy_bullets[before:]:
                kinds[b.bullet_type] = kinds.get(b.bullet_type, 0) + 1
        print("  %-7s 合计 %2d 发  %s" % (gid, sum(kinds.values()), kinds))


def main():
    count_ghost_bullets()
    rows = []
    for gid in IDS:
        stage, bm = make_stage(), BulletManager()
        run_to(stage, bm, SPAWNS[gid] + s6.GHOST_SPELL_AT)
        clear_field(stage, bm)
        frames = []
        for at in SHOTS:
            while stage.ghosts[0]["age"] < s6.GHOST_SPELL_AT + at:
                stage.update(1.0 / 60.0, bm, 288.0, 560.0)
                bm.update(1.0 / 60.0, 288.0, 560.0)
            frames.append(shot(stage, bm))
        rows.append((gid, frames))

    tw, th = 318, 370
    pad, label_h = 8, 24
    sheet = pygame.Surface(((tw + pad) * 4 + pad, (label_h + th + pad) * 4 + pad))
    sheet.fill((26, 28, 34))
    for r, (gid, frames) in enumerate(rows):
        for c, (at, frame) in enumerate(zip(SHOTS, frames)):
            x = pad + c * (tw + pad)
            y = pad + r * (label_h + th + pad)
            sheet.blit(font.render("%s   +%d帧" % (gid, at), True, (235, 235, 240)),
                       (x, y + 3))
            sheet.blit(pygame.transform.smoothscale(frame, (tw, th)), (x, y + label_h))
    out = os.path.join(OUT, "s6_ghost_spells.png")
    pygame.image.save(sheet, out)
    print("sheet:", out, sheet.get_size())
    print("RENDER_OK")


main()
