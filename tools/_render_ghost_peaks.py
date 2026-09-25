# -*- coding: utf-8 -*-
# 临时脚本：逐帧扫描四位残影的片段，取弹幕密度最大的那一帧
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
TAIL = 40          # 残影退场后再多跑几帧，看弹幕有没有继续变密


def make_stage():
    stage = s6.Stage6_FinalApproach()
    stage.setup_waves()
    return stage


def run_to(stage, bm, target):
    while stage.timer < target:
        stage.update(1.0 / 60.0, bm, 288.0, 560.0)
        bm.update(1.0 / 60.0, 288.0, 560.0)


def quiet_field(stage, bm):
    """把小怪 / 游魂（黑能量）这些干扰源全部停掉，只留这位残影的弹幕"""
    for e in stage.enemy_manager.get_active_enemies():
        while e.alive:
            e.take_damage(9999)
    stage.enemy_manager.waves = []
    stage.enemy_manager.timed_waves = []
    stage.enemy_manager.update = lambda *a, **k: None
    stage._update_energy = lambda *a, **k: None
    stage._update_kaeman = lambda *a, **k: None
    stage.energy_wisps = []
    stage.kaeman_skull = None
    stage.kaeman_warnings = []
    stage.mist_particles = []
    bm.enemy_bullets.clear()
    bm.player_bullets.clear()


def shot(stage, bm):
    screen.fill((0, 0, 0))
    stage.draw(screen, 0, 0)
    bm.draw(screen, 0, 0)
    stage.draw_foreground(screen, 0, 0)
    return screen.subsurface(pygame.Rect(0, 0, cfg.BATTLE_AREA_WIDTH,
                                         cfg.BATTLE_AREA_HEIGHT)).copy()


def main():
    rows, report = [], []
    for gid in IDS:
        stage, bm = make_stage(), BulletManager()
        run_to(stage, bm, SPAWNS[gid] + 1)
        quiet_field(stage, bm)
        peak_alive = (-1, None, 0)      # (数量, 帧, 年龄)
        peak_any = (-1, None, 0)
        for _ in range(190 + TAIL):
            stage.update(1.0 / 60.0, bm, 288.0, 560.0)
            bm.update(1.0 / 60.0, 288.0, 560.0)
            n = len(bm.enemy_bullets)
            ghosts = [g for g in stage.ghosts if g["id"] == gid]
            age = ghosts[0]["age"] if ghosts else 0
            if ghosts and n > peak_alive[0]:
                peak_alive = (n, shot(stage, bm), age)
            if n > peak_any[0]:
                peak_any = (n, shot(stage, bm), age)
        report.append((gid, peak_alive, peak_any))
        rows.append((gid, peak_alive[1], peak_alive[0], peak_alive[2]))
        print("  %-7s 存活期内峰值 %2d 发（登场后第 %3d 帧）；全程峰值 %2d 发（第 %3d 帧）"
              % (gid, peak_alive[0], peak_alive[2], peak_any[0], peak_any[2]))

    tw, th = 430, 500
    pad, label_h = 8, 24
    sheet = pygame.Surface(((tw + pad) * 2 + pad, (label_h + th + pad) * 2 + pad))
    sheet.fill((26, 28, 34))
    for i, (gid, frame, n, age) in enumerate(rows):
        x = pad + (i % 2) * (tw + pad)
        y = pad + (i // 2) * (label_h + th + pad)
        sheet.blit(font.render("%s  峰值 %d 发 / 登场后第 %d 帧" % (gid, n, age),
                               True, (235, 235, 240)), (x, y + 3))
        sheet.blit(pygame.transform.smoothscale(frame, (tw, th)), (x, y + label_h))
    out = os.path.join(OUT, "s6_ghost_spell_peaks.png")
    pygame.image.save(sheet, out)
    print("sheet:", out, sheet.get_size())
    print("RENDER_OK")


main()
