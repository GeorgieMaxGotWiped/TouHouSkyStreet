# -*- coding: utf-8 -*-
"""终仪「The Wither King's Final Slumber」预览：驱动 Kaeman Last Spell 并渲染若干帧。"""
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from src.entities.bullet import BulletManager
from src.engine.spell_bg import SpellBackground
from src.stages.stage6 import (
    Stage6_FinalApproach, spell_kaeman_last_spell,
)

OUT = os.path.join(os.getcwd(), "previews", "kaeman_slumber")
os.makedirs(OUT, exist_ok=True)
pygame.init()
screen = pygame.display.set_mode((960, 720))

stage = Stage6_FinalApproach()
stage.setup_boss()
boss = stage.boss
stage.phase = "boss"
boss.phase = "spell"
boss.combat_enabled = True
boss.x = boss.target_x = 288.0
boss.y = boss.target_y = 112.0
boss.spell_bg = SpellBackground("终仪「The Wither King's Final Slumber」", "kaeman_slumber")
bm = BulletManager()
px, py = 288.0, 560.0
t = 0


def run(n, px0=None, py0=None):
    global t, px, py
    if px0 is not None:
        px, py = px0, py0
    for _ in range(n):
        t += 1
        spell_kaeman_last_spell(boss, bm, t, 1.0 / 60, px, py)
        bm.update(1.0 / 60, px, py)
        boss.spell_bg.update(1.0 / 60)


def render(name):
    screen.fill((0, 0, 0))
    stage.draw(screen, 50, 25)
    bm.draw(screen, 50, 25)
    stage.draw_foreground(screen, 50, 25)
    path = os.path.join(OUT, name)
    pygame.image.save(screen, path)
    st = getattr(boss, "kaeman_slumber", None)
    gather = sum(1 for b in bm.enemy_bullets if getattr(b, "_slumber_gather", False))
    print("saved %-26s t=%4d phase=%-7s cycle=%d bullets=%3d gather=%3d absorbed=%3d" % (
        name, t, st["phase"] if st else "-", st["cycle"] if st else -1,
        len(bm.enemy_bullets), gather, st["absorbed"] if st else -1))


# --- 第一轮吸收 ---
run(75)                              # 吸收初期：场外弹开始涌入
render("01_gather_early.png")
run(110)                             # 吸收中段（t≈185）
render("02_gather_mid.png")
run(115)                             # 吸收末段（t≈300，即将放出）
render("03_gather_late.png")

# --- 狂暴放出 ---
run(1)                               # 放出瞬间
render("04_release_burst.png")
run(20)                              # 放出中：三层圆环 + 喷涌
render("05_release_mid.png")
run(45)                              # 放出持续（t≈366）
render("06_release_surge.png")
run(90)                              # 放出收尾 / 下一轮吸收开始
render("07_release_tail.png")
run(60)                              # 第二轮吸收
render("08_gather_cycle2.png")
print("RESULT_OK")
