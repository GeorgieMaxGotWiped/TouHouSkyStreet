# -*- coding: utf-8 -*-
# 闪符「Non-Directional Lightning」新版预览
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

guard = 0
while (b.current_spell is None or b.current_spell.name != "闪符「Non-Directional Lightning」") and guard < 200000 and b.alive:
    b.update(1 / 60, bm, px, py)
    b.take_damage(500)
    guard += 1
assert b.current_spell is not None

def shot(tag, frames):
    for _ in range(frames):
        b.update(1 / 60, bm, px, py)
    screen.fill((0, 0, 0))
    st.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    bm.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    out = os.path.join(OUT, tag)
    pygame.image.save(screen, out)
    print(f"{tag}: t={b.current_spell.timer} bullets={len(bm.enemy_bullets)}")

shot("dragon_fight_2a_lightning_warn.png", 74)     # 大圆预警标记（开场缓冲后）
shot("dragon_fight_2e_lightning_pulse.png", 30)    # 前摇脉冲
shot("dragon_fight_2b_lightning_strike.png", 28)   # 落雷+电弧
shot("dragon_fight_2c_lightning_grid.png", 6)      # 电网连接
shot("dragon_fight_2d_lightning_dense.png", 482)   # 多轮叠加

pygame.quit()
print("OK")