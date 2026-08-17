# -*- coding: utf-8 -*-
"""终仪「The Wither King's Final Slumber」冒烟测试：
贴近真实循环顺序（bullet_manager.update 先于 stage.update），直入 Last Spell，
验证吸收/放出循环重复运行、弹量有界、最终击破 Boss。"""
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from src.entities.bullet import BulletManager
from src.stages.stage6 import Stage6_FinalApproach

pygame.init()
screen = pygame.display.set_mode((960, 720))

stage = Stage6_FinalApproach()
stage.setup_boss()
boss = stage.boss
stage.phase = "boss"
bm = BulletManager()
px, py = 288.0, 560.0

# 直入 Last Spell
boss.current_spell_idx = len(boss.spell_cards)
boss.arm_combat(0)
boss.entering = False
boss.entry_timer = 0
boss._start_spell(boss.last_spell)

assert boss.last_spell_active, "last spell should be active"
assert boss.phase == "spell", boss.phase

max_bullets = 0
cycle_seen = set()
frames = 0
guard = 0
while frames < 60 * 30 and boss.alive and guard < 120000:
    guard += 1
    # 真实循环顺序：子弹先更新，再更新 stage（内含 boss）
    bm.update(1.0 / 60.0, px, py)
    stage.update(1.0 / 60.0, bm, px, py)
    frames += 1
    max_bullets = max(max_bullets, len(bm.enemy_bullets))
    st = getattr(boss, "kaeman_slumber", None)
    if st is not None:
        cycle_seen.add(st["cycle"])
    # 玩家不开火（仅验证弹幕循环稳定性）；打到剩少量血便于观察多轮
    if frames in (60 * 12, 60 * 18):
        boss.take_damage(3000)

st = getattr(boss, "kaeman_slumber", None)
print("frames=%d alive=%s phase=%s bullets=%d max_bullets=%d cycles=%s" % (
    frames, boss.alive, boss.phase, len(bm.enemy_bullets), max_bullets,
    sorted(cycle_seen)))
assert boss.alive, "boss should still be alive after 30s of dodging"
assert st is not None and st["cycle"] >= 1, "spell should have repeated at least once"
assert max_bullets < 900, "bullet count should stay bounded"
assert len(cycle_seen) >= 2, "multiple gather/release cycles observed"

# 击破：打空 Last Spell 血量
for _ in range(3000):
    if not boss.alive:
        break
    bm.update(1.0 / 60.0, px, py)
    stage.update(1.0 / 60.0, bm, px, py)
    boss.take_damage(2000)
assert not boss.alive, "boss should be defeated after emptying last spell hp"
print("defeated phase=%s" % stage.phase)

# 绘制冒烟（吸收核心 + 冲击环路径）
stage.draw(screen, 50, 25)
stage.draw_foreground(screen, 50, 25)
print("SMOKE_OK")
