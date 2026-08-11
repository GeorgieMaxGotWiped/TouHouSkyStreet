# -*- coding: utf-8 -*-
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager
pygame.init()
pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
from src.stages.stage2 import Stage2_DragonsNest

NAME = "龙符「One with the Dragons」"
st = Stage2_DragonsNest()
st.setup_boss()
boss = st.boss
boss.entering = False
boss.phase = "non_spell"
boss.combat_enabled = True
bm = BulletManager()
px, py = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80

guard = 0
while (boss.current_spell is None or boss.current_spell.name != NAME) and guard < 200000 and boss.alive:
    boss.update(1/60, bm, px, py)
    bm.update(1/60)
    boss.take_damage(500)
    guard += 1
assert boss.current_spell is not None and boss.current_spell.name == NAME

# 开符后第一帧清空，推进几帧让符卡填充幻影龙
for _ in range(5):
    boss.update(1/60, bm, px, py)
    bm.update(1/60)
assert len(boss.phantom_dragons) >= 2, "phantoms missing during spell"
print("龙符中幻影龙数量:", len(boss.phantom_dragons))

# 打完龙符（进入下一张符/非符），幻影龙应被清空
while boss.current_spell is not None and boss.current_spell.name == NAME and boss.alive:
    boss.update(1/60, bm, px, py)
    bm.update(1/60)
    boss.take_damage(500)
assert boss.phantom_dragons == [], f"phantoms not cleared: {boss.phantom_dragons}"
print("龙符结束后幻影龙清空: PASS")
print("RESULT: PASS")
pygame.quit()