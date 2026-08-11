# -*- coding: utf-8 -*-
# 二面初始化冒烟测试：注册表 / 时间轴推进 / PlayingState 渲染
import os
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
from src.stages.stage2 import Stage2_DragonsNest

# --- 1. 注册表 ---
assert get_stage_class(1).__name__ == "Stage1_SkyblockHub", "stage1 registered"
assert get_stage_class(2) is Stage2_DragonsNest, "stage2 registered"
from src.stages.stage3 import Stage3_CatacombsF1
assert get_stage_class(3) is Stage3_CatacombsF1, "stage3 registered"
assert get_next_stage_class(1) is Stage2_DragonsNest, "stage1 -> stage2"
assert get_next_stage_class(2) is Stage3_CatacombsF1, "stage2 -> stage3"
print("[1] registry OK")

# --- 2. 二面实例化与时间轴 ---
stage = Stage2_DragonsNest()
assert stage.stage_num == 2
assert "Dragon's Nest" in stage.name
assert stage.title_path == cfg.STAGE2_TITLE
assert stage.music_path == cfg.STAGE2_MUSIC
assert stage.background is not None
stage.setup_waves()
bm = BulletManager()

# 快进到道中Boss出场（47s）
guard = 0
while stage.phase == "intro" and guard < 50 * 60:
    stage.update(1 / 60, bm, cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80)
    guard += 1
assert stage.phase == "mid_boss" and stage.mid_boss is not None, f"mid boss spawned (phase={stage.phase})"
print(f"[2] mid boss spawned at t={stage.timer} phase={stage.phase}")

stage.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
pygame.image.save(screen, os.path.join("previews", "_stage2_preview_mid.png"))

# 击破道中Boss -> post_midboss -> 清完追加小怪后进入对话
stage.mid_boss.alive = False
guard = 0
while stage.phase != "dialogue" and guard < 60 * 60:
    stage.update(1 / 60, bm, cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80)
    guard += 1
assert stage.phase == "dialogue", f"dialogue reached (phase={stage.phase} t={stage.timer})"
assert stage.boss is not None and stage.boss.alive and not stage.boss.combat_enabled
print(f"[3] dialogue at t={stage.timer}, boss entered (combat off)")

stage.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
pygame.image.save(screen, os.path.join("previews", "_stage2_preview_dialogue.png"))

# 对话结束 -> boss 战 -> 击破 -> 战后对话（Boss留场）-> cleared
stage.on_dialogue_end()
assert stage.phase == "boss" and stage.boss.combat_enabled or stage.boss.combat_delay > 0
stage.boss.alive = False
guard = 0
while stage.phase != "defeat_dialogue" and guard < 60 * 10:
    stage.update(1 / 60, bm, cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80)
    guard += 1
assert stage.phase == "defeat_dialogue" and stage.dialogue_active, f"defeat dialogue (phase={stage.phase})"
# 战后对话结束 -> 通关结算
stage.on_defeat_dialogue_end()
assert stage.phase == "cleared", f"cleared (phase={stage.phase})"
print(f"[4] boss defeated -> defeat dialogue -> cleared")

# --- 3. PlayingState 直接跑二面 ---
from src.engine.game import Game
from src.ui.menu import PlayingState
game = Game()
game.global_data["stage"] = 1
state = PlayingState(game, Stage2_DragonsNest())
state.stage.setup_waves()
game.push_state(state)
for _ in range(90):
    state.update(1 / 60)
state.draw(screen)
pygame.image.save(screen, os.path.join("previews", "_stage2_preview_play.png"))
assert game.global_data["stage"] == 2, "global stage recorded"
print("[5] PlayingState ran 90 frames OK, stage recorded =", game.global_data["stage"])
print("ALL OK")
