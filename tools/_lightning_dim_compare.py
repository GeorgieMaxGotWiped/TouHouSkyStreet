# -*- coding: utf-8 -*-
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
import numpy as np
from src.engine.spell_bg import SpellBackground, STYLES
from src.engine import settings as cfg

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
for dim in (0.38, 0.45, 0.52, 0.58):
    STYLES["lightning"]["dim"] = dim
    bg = SpellBackground("test", bg_style="lightning")
    for _ in range(40):
        bg.update(1 / 60)
    screen.fill((0, 0, 0))
    bg.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    arr = pygame.surfarray.array3d(screen).astype(np.float32)
    crop = arr[cfg.BATTLE_OFFSET_Y:cfg.BATTLE_OFFSET_Y+cfg.BATTLE_AREA_HEIGHT,
               cfg.BATTLE_OFFSET_X:cfg.BATTLE_OFFSET_X+cfg.BATTLE_AREA_WIDTH]
    g = crop.mean(axis=2)
    print(f"dim={dim}: mean={g.mean():.1f} bright%(>110)={(g>110).mean()*100:.2f} p95={np.percentile(g,95):.0f}")
pygame.quit()