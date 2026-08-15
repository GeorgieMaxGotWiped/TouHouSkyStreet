# -*- coding: utf-8 -*-
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
from src.stages.stage5 import Stage5_WitherLords

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
bm = BulletManager()

assert boss.current_spell.name == "Phase3「Infinite Rage」", boss.current_spell.name
print("spell 1 active:", boss.current_spell.name)

# 运行 90 帧后确认状态存在
for t in range(90):
    st.update(1 / 60, bm, 288, 520)
assert boss.goldor_rage is not None
print("goldor_rage active, angle=", round(boss.goldor_rage["angle"], 3))

# 打空当前符卡血量（0.66 -> 0.0），触发结符 -> 已无后续符卡（Fist 已删除）
guard = 0
while boss.current_spell is boss.spell_cards[1] and guard < 200000 and boss.alive:
    boss.take_damage(400)
    st.update(1 / 60, bm, 288, 520)
    guard += 1
    if guard % 120 == 0:
        print("  hp_ratio=", round(boss.hp / boss.max_hp, 3))

assert boss.current_spell_idx == 2, boss.current_spell_idx
assert boss.current_spell is None, boss.current_spell
assert boss.goldor_rage is None, "goldor_rage 未在结符时清理"
assert not boss.alive and boss.phase == "defeated", (boss.alive, boss.phase)
print("rage 结束后 Goldor 直接败北（无 Last Spell）| goldor_rage cleared =", boss.goldor_rage is None)
print("INTEGRATION OK")
pygame.quit()