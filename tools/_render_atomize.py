# -*- coding: utf-8 -*-
import os, sys, math
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.entities.bullet import BulletManager
from src.stages.stage6 import Stage6_FinalApproach, BOSS_COMBAT_DELAY

OUT = r"C:\Users\admin\.codex\visualizations\2026\08\16\01a008b4-8764-7e73-b3e7-9ad765702e29"
os.makedirs(OUT, exist_ok=True)
pygame.init()
screen = pygame.display.set_mode((960, 720))
stage = Stage6_FinalApproach()
stage.setup_waves()
bm = BulletManager()

def run_frames(n, px, py):
    for _ in range(n):
        stage.update(1.0 / 60.0, bm, px, py)
        bm.update(1.0 / 60.0, px, py)

def shot(path):
    screen.fill((0, 0, 0))
    stage.draw(screen, 50, 25)
    bm.draw(screen, 50, 25)
    stage.draw_foreground(screen, 50, 25)
    pygame.image.save(screen, path)
    print("saved", path)

run_frames(20*60, 288, 560); run_frames(22*60, 288, 560); run_frames(8*60, 288, 560)
run_frames(24*60, 288, 560); run_frames(30*60, 288, 560)
for e in stage.enemy_manager.get_active_enemies():
    while e.alive: e.take_damage(9999)
run_frames(3, 288, 560)
assert stage.phase == "dialogue"
stage.on_dialogue_end()
# 等待入场结束
run_frames(BOSS_COMBAT_DELAY + 130, 320, 420)
print("boss entering=%s combat=%s phase=%s" % (
    stage.boss.entering, stage.boss.combat_enabled, stage.boss.phase))
# 直接展开第 5 张符卡
stage.boss.current_spell_idx = 4
stage.boss._start_spell()
run_frames(120, 320, 420)   # 就位 + 蓄力
st = stage.boss.kaeman_atomize
print("atomize phase=%s round=%d beams=%d t=%d" % (st["phase"], st["round"], st["beam_count"], st["t"]))
shot(os.path.join(OUT, "atom_charge.png"))

labels = {0: "atom_r1_beam", 1: "atom_r2_2beams", 2: "atom_r3_3beams",
          3: "atom_r4_4beams", 4: "atom_r5_5beams", 5: "atom_r6_6beams"}
shot_rounds = set()
guard = 0
while len(shot_rounds) < len(labels) and guard < 4200:
    px = 300 + 130 * math.cos(guard * 0.02)
    py = 380 + 100 * math.sin(guard * 0.013)
    stage.update(1.0 / 60.0, bm, px, py)
    bm.update(1.0 / 60.0, px, py)
    st = stage.boss.kaeman_atomize
    if st is None:
        print("st None at guard", guard); break
    r = st["round"]
    if r in labels and r not in shot_rounds and st["phase"] == "sweep" and st["t"] > 220:
        shot(os.path.join(OUT, labels[r] + ".png"))
        shot_rounds.add(r)
    guard += 1
print("screenshotted rounds:", sorted(shot_rounds), "bullets=%d" % len(bm.enemy_bullets))
print("RENDER_OK")
