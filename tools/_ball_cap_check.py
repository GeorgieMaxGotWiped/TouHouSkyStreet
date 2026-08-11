# -*- coding: utf-8 -*-
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager
import src.entities.boss as boss_mod

pygame.init()
pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
from src.stages.stage2 import Stage2_DragonsNest

NAME = "闪符「Non-Directional Lightning」"
st = Stage2_DragonsNest()
st.setup_boss()
b = st.boss
b.entering = False
b.phase = "non_spell"
b.combat_enabled = True
bm = BulletManager()

counts = []
orig = boss_mod._lightning_wave_positions
def tracked(rng, count):
    counts.append(count)
    return orig(rng, count)
boss_mod._lightning_wave_positions = tracked

guard = 0
while (b.current_spell is None or b.current_spell.name != NAME) and guard < 5000 and b.alive:
    b.update(1/60, bm, cfg.BATTLE_AREA_WIDTH/2, cfg.BATTLE_AREA_HEIGHT-80)
    b.take_damage(500)
    guard += 1
if b.current_spell is None or b.current_spell.name != NAME:
    print(f"FAIL: never reached lightning spell (guard={guard}, alive={b.alive})")
    pygame.quit()
    sys.exit(1)

counts.clear()
for _ in range(4000):
    b.update(1/60, bm, cfg.BATTLE_AREA_WIDTH/2, cfg.BATTLE_AREA_HEIGHT-80)

print("per-wave strike counts (first 24):", counts[:24])
print("max:", max(counts) if counts else 0)
assert counts, "no waves observed"
assert max(counts) <= 5, f"cap violated: max={max(counts)}"
tail = counts[counts.index(5):] if 5 in counts else []
assert all(c <= 5 for c in tail)
print("RESULT: PASS (每波电球 <= 5，到 5 后不再增多)")
pygame.quit()