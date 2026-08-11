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

NAME = "闪符「Non-Directional Lightning」"
st = Stage2_DragonsNest()
st.setup_boss()
b = st.boss
b.entering = False
b.phase = "non_spell"
b.combat_enabled = True
bm = BulletManager()

spawn_log = []
_orig_add = bm.add_enemy_bullet
def tracked_add(bullet):
    spawn_log.append((bullet.x, bullet.y, b.x, b.y))
    return _orig_add(bullet)
bm.add_enemy_bullet = tracked_add

guard = 0
while (b.current_spell is None or b.current_spell.name != NAME) and guard < 5000 and b.alive:
    b.update(1/60, bm, cfg.BATTLE_AREA_WIDTH/2, cfg.BATTLE_AREA_HEIGHT-80)
    b.take_damage(500)
    guard += 1

if b.current_spell is None or b.current_spell.name != NAME:
    print(f"FAIL: never reached lightning spell (guard={guard}, alive={b.alive})")
    pygame.quit()
    sys.exit(1)

print(f"entered {NAME} at timer={b.current_spell.timer} boss_hp={b.hp} guard={guard}")
spawn_log.clear()
frames = 0
while frames < 2000 and b.alive and b.current_spell.name == NAME:
    b.update(1/60, bm, cfg.BATTLE_AREA_WIDTH/2, cfg.BATTLE_AREA_HEIGHT-80)
    frames += 1

sky = [s for s in spawn_log if s[1] < 0]
from_boss = [s for s in spawn_log if ((s[0]-s[2])**2 + (s[1]-s[3])**2) < 40**2]
print(f"simulated frames={frames} spell_timer_end={b.current_spell.timer} boss_hp={b.hp}")
print(f"sky spawns (y<0): {len(sky)}")
print(f"boss-position spawns (<40px): {len(from_boss)}")
for s in from_boss[:10]:
    print("  boss-near:", tuple(round(v,1) for v in s))
print("RESULT:", "PASS" if not sky and not from_boss and frames > 300 else "FAIL")
pygame.quit()