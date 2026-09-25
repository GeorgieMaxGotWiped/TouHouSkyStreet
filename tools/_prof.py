import os, sys, cProfile, pstats, io as _io
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import game as game_module
orig = game_module.load_user_config
game_module.load_user_config = lambda: dict(orig(), fullscreen=False)
pygame.init()
game = game_module.Game()
from pygame._sdl2 import video as vm
vm.Window.from_display_module().size = (2880, 2160)
from src.ui.menu import PlayingState
from src.stages.stage3 import Stage3_CatacombsF1
state = PlayingState(game, Stage3_CatacombsF1())
game.push_state(state)
game._update_present_rect()
for _ in range(60):
    state.update(1/60.0)
    game._draw()
pr = cProfile.Profile()
pr.enable()
for _ in range(60):
    state.update(1/60.0)
    game._draw()
pr.disable()
buf = _io.StringIO()
pstats.Stats(pr, stream=buf).sort_stats("tottime").print_stats(18)
text = buf.getvalue()
open("tools/_prof_out.txt", "w", encoding="utf-8").write(text)
print("bullets:", len(state.bullet_manager.enemy_bullets))
