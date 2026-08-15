# -*- coding: utf-8 -*-
# 三面冒烟测试：注册表 / 时间轴推进 / Watcher 道中符卡 / Bonzo 双阶段复活 / PlayingState 渲染
import os
import math
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
import sys
sys.path.insert(0, os.getcwd())
from src.engine import settings as cfg
from src.entities.bullet import BulletManager

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
os.makedirs("previews", exist_ok=True)

from src.stages import get_stage_class, get_next_stage_class
from src.stages.stage3 import (Stage3_CatacombsF1, WATCHER_MAX_HP,
                               BONZO_MAX_HP, BONZO_REVIVE_HP)

PX, PY = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80


def run(stage, bm, frames, damage=None, dmg=25, per=4):
    """推进 frames 帧；若 damage 对象存活则每帧对其造成 dmg*per 伤害"""
    for _ in range(frames):
        stage.update(1 / 60, bm, PX, PY)
        if damage is not None and damage.alive:
            for _ in range(per):
                if damage.take_damage(dmg):
                    break


# --- 1. 注册表 ---
assert get_stage_class(1).__name__ == "Stage1_SkyblockHub"
assert get_stage_class(2).__name__ == "Stage2_DragonsNest"
assert get_stage_class(3) is Stage3_CatacombsF1, "stage3 registered"
assert get_next_stage_class(2) is Stage3_CatacombsF1, "stage2 -> stage3"
assert get_next_stage_class(3) is None, "stage3 -> menu"
print("[1] registry OK")

# --- 2. 实例化与资源 ---
stage = Stage3_CatacombsF1()
assert stage.stage_num == 3
assert "Catacombs" in stage.name
assert stage.title_path == cfg.STAGE3_TITLE
assert stage.music_path == cfg.STAGE3_MUSIC_START
assert stage.music_loop_path == cfg.STAGE3_MUSIC_LOOP
assert stage.boss_music_start_path == cfg.STAGE3_BOSS_MUSIC_START
assert stage.background is not None
stage.setup_waves()
bm = BulletManager()
print("[2] stage resources OK")

# --- 3. 快进到道中Boss（47s）---
guard = 0
while stage.phase == "intro" and guard < 50 * 60:
    stage.update(1 / 60, bm, PX, PY)
    guard += 1
assert stage.phase == "mid_boss" and stage.mid_boss is not None
assert stage.mid_boss.name == "The Watcher"
mb = stage.mid_boss
print(f"[3] Watcher spawned at t={stage.timer} hp={mb.hp}")

# --- 4. Watcher 完整流程：非符 -> 展符 -> 击破 ---
seen = []
while stage.phase == "mid_boss" and mb.alive and guard < 60 * 60:
    run(stage, bm, 30, damage=mb)
    guard += 30
    if mb.current_spell is not None and mb.current_spell.name not in seen:
        seen.append(mb.current_spell.name)
        print(f"    watcher spell active: {mb.current_spell.name} (phase={mb.phase})")
assert not mb.alive, "watcher defeated"
assert stage.phase == "post_midboss"
assert any("Undead Exhibition" in s for s in seen), f"watcher spell seen: {seen}"
print(f"[4] Watcher defeated at t={stage.timer} (spells={seen})")

stage.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
pygame.image.save(screen, os.path.join("previews", "_stage3_preview_postmid.png"))

# --- 5. 清完小怪 -> 对话 -> Bonzo 入场 ---
guard = 0
while stage.phase != "dialogue" and guard < 60 * 60:
    stage.update(1 / 60, bm, PX, PY)
    guard += 1
assert stage.phase == "dialogue", f"dialogue (phase={stage.phase} t={stage.timer})"
assert stage.boss is not None and stage.boss.alive and not stage.boss.combat_enabled
assert stage.boss.name == "Bonzo"
print(f"[5] dialogue at t={stage.timer}, Bonzo entered (combat off)")

# --- 6. Bonzo 双阶段：一阶段三符 -> 死亡复活 -> 气符 -> 秘仪 -> 击破 ---
stage.on_dialogue_end()
assert stage.phase == "boss" and (stage.boss.combat_enabled or stage.boss.combat_delay > 0)
bonzo = stage.boss
revive_seen = False
spell_names = []
while stage.phase not in ("cleared", "defeat_dialogue") and guard < 60 * 90:
    run(stage, bm, 15, damage=bonzo)
    guard += 15
    if bonzo.current_spell is not None:
        nm = bonzo.current_spell.name
        if not spell_names or spell_names[-1] != nm:
            spell_names.append(nm)
            print(f"    bonzo phase: {bonzo.phase} spell={nm} hp={bonzo.hp:.0f}/{bonzo.max_hp}")
    if bonzo.phase == "reviving" and not revive_seen:
        revive_seen = True
        assert bonzo.hp == 0, f"revive start hp {bonzo.hp} != 0"
        print("    REVIVING")
if stage.phase == "defeat_dialogue":
    stage.on_defeat_dialogue_end()
assert stage.phase == "cleared", f"cleared (phase={stage.phase} t={stage.timer})"
assert revive_seen, "Bonzo revived"
expected = ("Undead Revival", "Skull Dreadlord", "Grand Illusion", "Balloon", "Showtime")
assert len(spell_names) == 5 and all(k in s for k, s in zip(expected, spell_names)), spell_names
print(f"[6] Bonzo defeated after revive (spells={spell_names})")

# --- 7. PlayingState 渲染（含标题卡/曲名）---
from src.engine.game import Game
from src.ui.menu import PlayingState
game = Game()
game.global_data["stage"] = 2
state = PlayingState(game, Stage3_CatacombsF1())
state.stage.setup_waves()
game.push_state(state)
for _ in range(90):
    state.update(1 / 60)
state.draw(screen)
pygame.image.save(screen, os.path.join("previews", "_stage3_preview_play.png"))
assert game.global_data["stage"] == 3, "global stage recorded"
print("[7] PlayingState ran 90 frames OK, stage recorded =", game.global_data["stage"])

# --- 8. 关底对话渲染（跳过标题，直接进对话）---
stage2 = Stage3_CatacombsF1()
stage2._start_dialogue()
state2 = PlayingState(game, stage2, skip_title=True)
game.push_state(state2)
for _ in range(8):
    state2.update(1 / 60)
state2.draw(screen)
pygame.image.save(screen, os.path.join("previews", "_stage3_preview_dialogue.png"))
print("[8] dialogue rendered OK")

# --- 9. 新小怪：墓穴唤魂者（GraveCasterEnemy）---
from src.entities.enemy import GraveCasterEnemy

# 9a. 入场：快速下坠到部署位（150）后转为正常下落
caster = GraveCasterEnemy(cfg.BATTLE_AREA_WIDTH / 2, -30, deploy_y=150)
assert caster.phase == "dive"
for _ in range(40):
    caster.update(1 / 60, PX, PY)
    if caster.phase == "descend":
        break
assert caster.phase == "descend" and caster.y == 150, (caster.phase, caster.y)

# 9b. 五环方向一致、初始速度一致（不逐环错开）
caster_bm = BulletManager()
ring_angles, ring_speeds = [], []
for _ in range(70):   # 覆盖 5 环
    caster.update(1 / 60, PX, PY)
    if caster.can_shoot():
        n0 = len(caster_bm.enemy_bullets)
        caster.shoot(caster_bm, PX, PY)
        if len(caster_bm.enemy_bullets) > n0:
            first = caster_bm.enemy_bullets[n0]   # 本环第 1 发
            ring_angles.append(math.atan2(first.vy, first.vx))
            ring_speeds.append(math.hypot(first.vx, first.vy))
assert len(ring_angles) == 5, f"一组 5 环={len(ring_angles)}"
assert max(ring_angles) - min(ring_angles) < 1e-6, "五环方向一致"
assert max(ring_speeds) - min(ring_speeds) < 1e-6, "五环初始速度一致"

# 9c. 弹速随该弹自身存在时间递减（而非怪物年龄）
caster2 = GraveCasterEnemy(cfg.BATTLE_AREA_WIDTH / 2, -30, deploy_y=150)
caster_bm2 = BulletManager()
for _ in range(40):
    caster2.update(1 / 60, PX, PY)
    if caster2.phase == "descend":
        break
for _ in range(5):
    caster2.update(1 / 60, PX, PY)
    if caster2.can_shoot():
        caster2.shoot(caster_bm2, PX, PY)
        break
b0 = caster_bm2.enemy_bullets[0]
s0 = math.hypot(b0.vx, b0.vy)
for _ in range(40):
    caster_bm2.update(1 / 60, PX, PY)
    if caster_bm2.enemy_bullets:
        b0 = caster_bm2.enemy_bullets[0]
s1 = math.hypot(b0.vx, b0.vy)
assert s1 < s0 - 0.3, f"弹速随弹自身存在时间递减：{s0:.2f} -> {s1:.2f}"
# 9d. 减速到下限后保持巡航（不低于下限），且最终全部飞出屏幕
for _ in range(120):
    caster_bm2.update(1 / 60, PX, PY)
    if caster_bm2.enemy_bullets:
        b0 = caster_bm2.enemy_bullets[0]
        spd = math.hypot(b0.vx, b0.vy)
        assert spd >= 2.2 - 1e-6, f"弹速不低于下限：{spd:.2f}"
for _ in range(700):
    caster_bm2.update(1 / 60, PX, PY)
    if not caster_bm2.enemy_bullets:
        break
assert not caster_bm2.enemy_bullets, "环弹最终全部飞出屏幕"
print(f"[9] GraveCaster OK: 5 环方向一致, 弹自身减速 {s0:.2f} -> {s1:.2f} (下限 2.2, 全部出屏)")

# --- 10. 三面小怪渲染（含新唤魂者）---
from src.entities.enemy import EnemyManager, EnemyWave
mgr = EnemyManager()
mgr.add_timed_wave(0, EnemyWave([
    GraveCasterEnemy(cfg.BATTLE_AREA_WIDTH / 2, -20, deploy_y=120),
    GraveCasterEnemy(cfg.BATTLE_AREA_WIDTH / 4, -20, deploy_y=140),
]))
for _ in range(90):
    mgr.update(1 / 60, caster_bm, PX, PY, stage_time=90)
screen.fill((20, 20, 30))
mgr.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
pygame.image.save(screen, os.path.join("previews", "_stage3_preview_caster.png"))
print("[10] caster rendering OK")

print("ALL OK")
