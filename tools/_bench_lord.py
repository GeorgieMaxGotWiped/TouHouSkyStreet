# -*- coding: utf-8 -*-
# 临时脚本：量 Skeleton Lords 波（7.5s 附近）在真实绘制路径下的帧时间
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import game as game_module
from src.engine import settings as cfg

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

original = game_module.load_user_config
game_module.load_user_config = lambda: dict(original(), fullscreen=False, render_scale_index=2)
pygame.init()
game = game_module.Game()
from pygame._sdl2 import video as video_module
video_module.Window.from_display_module().size = (2880, 2160)
from src.ui.menu import PlayingState
from src.stages.stage6 import Stage6_FinalApproach
state = PlayingState(game, Stage6_FinalApproach())
game.push_state(state)
game._update_present_rect()

TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 450
for _ in range(TARGET):
    state.update(1 / 60.0)
    game._draw()

def measure(n=30):
    best = None
    for _ in range(n):
        t0 = time.perf_counter()
        game._draw()
        dt = time.perf_counter() - t0
        best = dt if best is None else min(best, dt)
    return best * 1000.0

with_b = measure()
kept = state.bullet_manager.enemy_bullets
state.bullet_manager.enemy_bullets = []
without_b = measure()
state.bullet_manager.enemy_bullets = kept
print("[bench] 时刻 %.1fs 敌弹=%d 敌机=%d" % (
    state.stage.timer / 60.0, len(kept),
    len([e for e in state.stage.enemy_manager.active_enemies if e.alive])))
print("[bench] 整帧绘制 = %.2f ms（无弹幕 %.2f ms，弹幕层 = %.2f ms）" % (
    with_b, without_b, with_b - without_b))
game.running = False
pygame.quit()
