# -*- coding: utf-8 -*-
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
import numpy as np
from src.engine.spell_bg import SpellBackground
from src.engine import settings as cfg

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
OUT = r"C:\Users\admin\.codex\visualizations\2026\08\09\019fe5b0-4b9f-7312-99f1-6acd0c432c4f"

for style in ("lightning", "fire", "dragon", "superiority"):
    bg = SpellBackground("test", bg_style=style)
    for _ in range(40):
        bg.update(1 / 60)
    screen.fill((0, 0, 0))
    pygame.draw.rect(screen, (10, 14, 26), (0, 0, cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    bg.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    out = os.path.join(OUT, f"dragon_spellbg_{style}.png")
    pygame.image.save(screen, out)
    arr = pygame.surfarray.array3d(screen).astype(np.float32)
    crop = arr[cfg.BATTLE_OFFSET_Y:cfg.BATTLE_OFFSET_Y+cfg.BATTLE_AREA_HEIGHT,
               cfg.BATTLE_OFFSET_X:cfg.BATTLE_OFFSET_X+cfg.BATTLE_AREA_WIDTH]
    g = crop.mean(axis=2)
    print(f"{style}: mean={g.mean():.1f} bright%={(g>110).mean()*100:.2f}")
pygame.quit()
print("OK")