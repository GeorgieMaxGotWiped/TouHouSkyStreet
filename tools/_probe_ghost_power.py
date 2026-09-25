# -*- coding: utf-8 -*-
# 临时脚本：四残影片段的「发弹数」与峰值帧（安静场地，只留残影弹幕）
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
TAIL = 30
counter = {"n": 0}
_orig_add = s6._add


def _counting_add(bm, bullet):
    counter["n"] += 1
    return _orig_add(bm, bullet)


s6._add = _counting_add


def quiet_field(stage, bm):
    for e in stage.enemy_manager.get_active_enemies():
        while e.alive:
            e.take_damage(9999)
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


rows = []
for gid in IDS:
    stage = s6.Stage6_FinalApproach(); stage.setup_waves()
    bm = BulletManager()
    while stage.timer < SPAWNS[gid] + 1:
        stage.update(1 / 60.0, bm, 288.0, 560.0); bm.update(1 / 60.0, bm and 288.0, 560.0)
    quiet_field(stage, bm)
    counter["n"] = 0
    peak = (-1, None, 0)
    for _ in range(s6.GHOST_SPELL_FRAMES + TAIL):
        stage.update(1 / 60.0, bm, 288.0, 560.0); bm.update(1 / 60.0, 288.0, 560.0)
        n = len(bm.enemy_bullets)
        ghosts = [g for g in stage.ghosts if g["id"] == gid]
        if ghosts and n > peak[0]:
            peak = (n, shot(stage, bm), ghosts[0]["age"])
    rows.append((gid, counter["n"], peak[0], peak[2], peak[1]))
    print("  %-7s 片段发弹 %3d 发　同屏峰值 %3d 发（登场后第 %3d 帧）" % (gid, counter["n"], peak[0], peak[2]))

tw, th, pad, label_h = 430, 500, 8, 24
sheet = pygame.Surface(((tw + pad) * 2 + pad, (label_h + th + pad) * 2 + pad))
sheet.fill((26, 28, 34))
for i, (gid, total, peak, age, frame) in enumerate(rows):
    x = pad + (i % 2) * (tw + pad)
    y = pad + (i // 2) * (label_h + th + pad)
    sheet.blit(font.render("%s  片段发弹 %d 发　峰值 %d 发 / 第 %d 帧" % (gid, total, peak, age),
                           True, (235, 235, 240)), (x, y + 3))
    sheet.blit(pygame.transform.smoothscale(frame, (tw, th)), (x, y + label_h))
out = os.path.join(OUT, "s6_ghost_power.png")
pygame.image.save(sheet, out)
print("sheet:", out, sheet.get_size())
print("RENDER_OK")
