# -*- coding: utf-8 -*-
# Phase3「Infinite Rage」预览：旋转剑盾 / 剑隙骷髅 / 圆弹米弹海
import os, sys, math
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
from src.stages.stage5 import Stage5_WitherLords

OUT = r"C:\Users\admin\.codex\visualizations\2026\08\15\01a00493-a5fa-7140-b7d9-c1db196c70e0"

st = Stage5_WitherLords()
st.phase = "dialogue"
boss = st._build_boss("goldor")
st.boss = boss
boss.arm_combat(0)
boss.entering = False
boss.entry_timer = 0
boss.current_spell_idx = 1
boss._start_spell(boss.spell_cards[1])
st.phase = "boss"
st._boss_defeated_handled = False
st._on_boss_combat_start = lambda: None

bm = BulletManager()

def player_pos(t):
    # 自机在下方做小幅横向摆动，展示瞄准弹的散开
    px = cfg.BATTLE_AREA_WIDTH / 2 + math.sin(t * 0.018) * 130
    py = cfg.BATTLE_AREA_HEIGHT - 90 + math.sin(t * 0.011) * 40
    return px, py

def snap(tag, frames, label):
    for _ in range(frames):
        px, py = player_pos(boss.current_spell.timer if boss.current_spell else 0)
        st.update(1 / 60, bm, px, py)
    px, py = player_pos(boss.current_spell.timer if boss.current_spell else 0)
    screen.fill((0, 0, 0))
    st.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    bm.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    st.draw_foreground(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    out = os.path.join(OUT, tag)
    pygame.image.save(screen, out)
    print(f"{label}: timer={boss.current_spell.timer} bullets={len(bm.enemy_bullets)} "
          f"swords={boss.goldor_rage is not None and boss.goldor_rage.get('angle') is not None} "
          f"saved={out}")

snap("goldor_rage_a_open.png", 40, "开符初期")
snap("goldor_rage_b_early.png", 90, "早期")
snap("goldor_rage_c_mid.png", 200, "中期")
snap("goldor_rage_d_dense.png", 300, "高密度")
snap("goldor_rage_e_late.png", 520, "后期")

pygame.quit()
print("OK")