# -*- coding: utf-8 -*-
# 末影龙各符卡实战预览（推进若干帧后截图）
import os, sys
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
px, py = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80

st = Stage2_DragonsNest()
st.setup_boss()
b = st.boss
b.entering = False
b.phase = "non_spell"
b.combat_enabled = True
bm = BulletManager()

for target_name, extra_frames in (
        ("燃符「Fireball Barrage」", 150),
        ("闪符「Non-Directional Lightning」", 130),
        ("龙符「One with the Dragons」", 240),
        ("超符「Superiority」", 200)):
    guard = 0
    while (b.current_spell is None or b.current_spell.name != target_name) and guard < 200000 and b.alive:
        b.update(1 / 60, bm, px, py)
        b.take_damage(500)
        guard += 1
    for _ in range(extra_frames):
        b.update(1 / 60, bm, px, py)
    screen.fill((0, 0, 0))
    st.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    bm.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    safe = target_name.replace("「", "").replace("」", "").replace(" ", "_")
    out = os.path.join(OUT, f"dragon_fight_{safe}.png")
    pygame.image.save(screen, out)
    print(f"{target_name}: bullets={len(bm.enemy_bullets)} -> {out}")

pygame.quit()
print("OK")