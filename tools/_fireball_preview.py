# -*- coding: utf-8 -*-
# 燃符「Fireball Barrage」新版预览：幕1轰炸阵列 / 幕2绕场封锁
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

# 冲到燃符
guard = 0
while (b.current_spell is None or b.current_spell.name != "燃符「Fireball Barrage」") and guard < 200000 and b.alive:
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
    print(f"{tag}: bullets={len(bm.enemy_bullets)}")

# 幕1 蓄力中
shot("dragon_fight_1a_fireball_charge.png", 30)
# 幕1 轰炸阵列进行中（含爆裂）
shot("dragon_fight_1b_fireball_bombard.png", 120)
# 幕1 后期（阵列更密）
shot("dragon_fight_1c_fireball_dense.png", 180)
# 幕2 绕场封锁（弹幕带 + 封锁线）
shot("dragon_fight_1d_fireball_lockdown.png", 420)

pygame.quit()
print("OK")