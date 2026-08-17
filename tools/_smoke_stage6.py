# -*- coding: utf-8 -*-
# 六面冒烟测试：无头跑完整流程（110s 进军 -> 对话 -> Kaeman 战（五符 + Last Spell）-> 通关）
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
stage.setup_waves()
bm = BulletManager()

def run_frames(n, label):
    px, py = 288.0, 560.0
    for _ in range(n):
        stage.update(1.0 / 60.0, bm, px, py)
        bm.update(1.0 / 60.0, px, py)
    print("%-26s timer=%d phase=%s enemies=%d bullets=%d" % (
        label, stage.timer, stage.phase,
        len(stage.enemy_manager.get_active_enemies()), len(bm.enemy_bullets)))

run_frames(20 * 60, "march-20s")
run_frames(22 * 60, "march->interference")
run_frames(8 * 60, "interference-50s")
assert stage.phase == "interference", stage.phase
print("  skull_active=%s warnings=%d wisps=%d" % (
    stage.kaeman_skull is not None, len(stage.kaeman_warnings),
    len(stage.energy_wisps)))

run_frames(24 * 60, "->fortress-74s")
assert stage.phase == "fortress", stage.phase
print("  ghosts=%d skull_active=%s" % (len(stage.ghosts), stage.kaeman_skull is not None))

run_frames(30 * 60, "fortress->final_wave")
assert stage.phase == "final_wave", stage.phase
print("  ghosts=%d final_wave spawned=%s active=%d" % (
    len(stage.ghosts),
    stage.final_wave.spawned if stage.final_wave else False,
    len(stage.enemy_manager.get_active_enemies())))

# 清空全部敌人以触发最后防线突破
for e in stage.enemy_manager.get_active_enemies():
    while e.alive:
        e.take_damage(9999)
run_frames(2, "clear-final")
print("  -> after clear: phase=%s dialogue=%s" % (stage.phase, stage.dialogue_active))
assert stage.phase == "dialogue", stage.phase
assert stage.boss is not None and stage.boss.alive

# 对话结束 -> Wither King 开战
stage.on_dialogue_end()
assert stage.phase == "boss", stage.phase
print("  boss=%s hp=%d spell_cards=%d" % (
    stage.boss.name, stage.boss.hp, len(stage.boss.spell_cards)))

# 运行 Boss 战一段时间（含入场）
run_frames(4 * 60, "boss-4s")
print("  boss entering=%s phase=%s combat=%s hp=%d bullets=%d" % (
    stage.boss.entering, stage.boss.phase, stage.boss.combat_enabled,
    stage.boss.hp, len(bm.enemy_bullets)))
run_frames(6 * 60, "boss-10s")
assert stage.boss.phase in ("non_spell", "spell"), stage.boss.phase
assert len(stage.boss.spell_cards) == 5, len(stage.boss.spell_cards)
assert stage.boss.last_spell is not None
print("  spell_cards=%d last_spell=%s phase=%s" % (
    len(stage.boss.spell_cards),
    stage.boss.last_spell.name if stage.boss.last_spell else None,
    stage.boss.phase))

# 打空 Boss 血量 -> 战后对话 -> 通关
for _ in range(600):
    if not stage.boss.alive:
        break
    stage.boss.take_damage(1000)
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
    bm.update(1.0 / 60.0, 288.0, 560.0)
print("  after-damage: alive=%s phase=%s dialogue_is_defeat=%s" % (
    stage.boss.alive, stage.phase, stage.dialogue_is_defeat))
assert stage.phase == "defeat_dialogue", stage.phase
stage.on_defeat_dialogue_end()
assert stage.phase == "cleared", stage.phase
assert stage.is_cleared()

# 各阶段绘制冒烟
stage.draw(screen, 50, 25)
stage.draw_foreground(screen, 50, 25)
print("SMOKE_OK")
