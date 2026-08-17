# -*- coding: utf-8 -*-
"""裂符「Dimensional Slash」预览：驱动 Kaeman 第四符卡并渲染若干帧。"""
import os
import sys

sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from src.entities.bullet import BulletManager
from src.engine.spell_bg import SpellBackground
from src.stages.stage6 import (
    Stage6_FinalApproach, spell_kaeman_dimensional_slash,
)

OUT = os.path.join(os.getcwd(), "previews", "kaeman_slash")
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
boss.spell_bg = SpellBackground("裂符「Dimensional Slash」", "kaeman_slash")
bm = BulletManager()
px, py = 288.0, 560.0
t = 0


def apply_teleport():
    global px, py
    sl = getattr(boss, "kaeman_slash", None)
    if sl is not None and sl.get("tentacle") is not None:
        tt = sl["tentacle"].get("teleport_target")
        if tt is not None:
            px, py = tt
            sl["tentacle"]["teleport_target"] = None


def run(n, px0=None, py0=None):
    global t, px, py
    if px0 is not None:
        px, py = px0, py0
    for _ in range(n):
        t += 1
        spell_kaeman_dimensional_slash(boss, bm, t, 1.0 / 60, px, py)
        bm.update(1.0 / 60, px, py)
        boss.spell_bg.update(1.0 / 60)
        apply_teleport()


def render(name):
    screen.fill((0, 0, 0))
    stage.draw(screen, 50, 25)
    bm.draw(screen, 50, 25)
    stage.draw_foreground(screen, 50, 25)
    path = os.path.join(OUT, name)
    pygame.image.save(screen, path)
    st = getattr(boss, "kaeman_slash", None)
    print("saved %-28s t=%4d bullets=%3d cracks=%d tent=%s px=%s py=%s" % (
        name, t, len(bm.enemy_bullets),
        len(st["cracks"]) if st else -1,
        (st["tentacle"]["phase"] if st and st["tentacle"] else None),
        round(px, 1), round(py, 1)))


# --- 第一道裂痕：预警 -> 斩击 -> 碎片 ---
run(60, 288.0, 560.0)          # 开场空窗
render("01_idle.png")
run(35)                        # 预警开始（t=95）
render("02_warn_start.png")
run(40)                        # 预警中段
render("03_warn_mid.png")
run(32)                        # 预警末段（t=167 前）
render("04_warn_late.png")
run(6)                         # 斩击延伸中（t~172）
render("05_slash_extend.png")
run(14)                        # 延伸完成（t~186）
render("06_slash_full.png")
run(20)                        # 碎片残留（t~206）
render("07_fragments.png")
run(60)                        # 多道裂痕交错（t~266）
render("08_overlap.png")

# --- 推进到弧线斩击 ---
run(60 * 9, 288.0, 560.0)      # 约 540 帧，多道裂痕交错（含弧形）
render("09_arc_overlap.png")
run(60 * 6, 288.0, 560.0)
render("10_late.png")
print("spawn_count", boss.kaeman_slash["spawn_count"], "bullets", len(bm.enemy_bullets))

# --- 触手：玩家靠近 Kaeman -> 预警 -> 拉拽 -> 中弹标记 ---
run(6, 330.0, 200.0)           # 靠近危险范围（距 Kaeman ~97px）
render("11_tentacle_warn.png")
run(8)                         # 预警中
render("12_tentacle_pull.png")
run(18)                        # 拉拽中
render("13_tentacle_pull2.png")
print("grab_hit_active", boss.kaeman_slash.get("grab_hit_active"))
run(10)                        # 拉拽完成 / release
render("14_release.png")
print("after-release grab_hit_active", boss.kaeman_slash.get("grab_hit_active"))
print("player pos after grab:", px, py)
print("RENDER_OK")