# -*- coding: utf-8 -*-
# 龙符新版预览（含子弹生命周期更新，贴近实机）
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
from src.stages.stage2 import Stage2_DragonsNest

OUT = r"C:\Users\admin\.codex\visualizations\2026\08\09\019fe5b0-4b9f-7312-99f1-6acd0c432c4f"
NAME = "龙符「One with the Dragons」"
px, py = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80

st = Stage2_DragonsNest()
st.setup_boss()
b = st.boss
b.entering = False
b.phase = "non_spell"
b.combat_enabled = True
bm = BulletManager()

guard = 0
while (b.current_spell is None or b.current_spell.name != NAME) and guard < 200000 and b.alive:
    b.update(1/60, bm, px, py)
    bm.update(1/60)
    b.take_damage(500)
    guard += 1
assert b.current_spell is not None and b.current_spell.name == NAME

def shot(tag, frames, label):
    for _ in range(frames):
        b.update(1/60, bm, px, py)
        bm.update(1/60)
    screen.fill((0, 0, 0))
    t0 = time.perf_counter()
    st.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    bm.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    dt = (time.perf_counter() - t0) * 1000
    out = os.path.join(OUT, tag)
    pygame.image.save(screen, out)
    print(f"{tag}: t={b.current_spell.timer} {label} phantoms={len(b.phantom_dragons)} "
          f"bullets={len(bm.enemy_bullets)} draw_ms={dt:.2f}")
    return out

shot("dragon_fight_3a_wing.png", 120, "phase0-wing")
shot("dragon_fight_3b_scale.png", 200, "phase1-scale")
shot("dragon_fight_3c_dense.png", 240, "phase2-dense")
shot("dragon_fight_3d_many.png", 760, "late-5phantoms")

pygame.quit()
print("OK")