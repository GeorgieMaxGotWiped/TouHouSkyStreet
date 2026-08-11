
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
import numpy as np
sys.path.insert(0, os.getcwd())
from src.engine.spell_bg import SpellBackground, _pattern_cache, _get_pattern

pygame.init()
screen = pygame.display.set_mode((576, 670))

for style in ("spool", "thread", "tornado", "soul"):
    bg = SpellBackground("test", bg_style=style)
    for i in range(120):
        bg.update(1/60)
        bg.draw(screen)

print("cache keys:", sorted(_pattern_cache.keys()))
for k in sorted(_pattern_cache.keys()):
    if k.startswith("icon_"):
        s = _pattern_cache[k]
        print(k, "size=", s.get_size(), "alpha_px=", int((pygame.surfarray.array_alpha(s) > 8).mean()*100), "%")
pygame.quit()
print("DONE")
