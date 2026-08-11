
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
import numpy as np
sys.path.insert(0, os.getcwd())
from src.engine.spell_bg import _get_pattern

pygame.init()
screen = pygame.display.set_mode((576, 670))

order = [("icon_spool", "Luxurious Spool"), ("icon_string", "Soul String"),
         ("icon_arack", "Arack"), ("icon_fang", "Arachne Fang"),
         ("icon_fragment", "Arachne Fragment"), ("icon_essence", "Spider Essence")]
tile = 190
canvas = pygame.Surface((tile*3, tile*2))
canvas.fill((14, 16, 26))
for i, (key, name) in enumerate(order):
    pat = _get_pattern(key)
    scale = min((tile*0.82)/pat.get_width(), (tile*0.82)/pat.get_height())
    img = pygame.transform.smoothscale(pat, (max(1,int(pat.get_width()*scale)), max(1,int(pat.get_height()*scale))))
    tx, ty = (i % 3) * tile, (i // 3) * tile
    canvas.blit(img, (tx + (tile-img.get_width())//2, ty + (tile-img.get_height())//2))
    arr = pygame.surfarray.array3d(pat).astype(np.float32)
    a = pygame.surfarray.array_alpha(pat)
    lum = arr.mean(axis=2)
    px = lum[a > 8]
    print("%-18s max_lum=%.0f mean_lum=%.0f p99=%.0f" % (key, px.max() if len(px) else 0, px.mean() if len(px) else 0, np.percentile(px, 99) if len(px) else 0))
out = r"C:/Users/admin/.codex/visualizations/2026/08/08/019fe088-c704-7783-8622-d7523d22c933/spellbg_icons.png"
pygame.image.save(canvas, out)
print("saved", out)
pygame.quit()
