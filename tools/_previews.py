
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
sys.path.insert(0, os.getcwd())
from src.engine.spell_bg import SpellBackground, _get_pattern

pygame.init()
screen = pygame.display.set_mode((576, 670))
outdir = r"C:/Users/admin/.codex/visualizations/2026/08/08/019fe088-c704-7783-8622-d7523d22c933"

# 每套风格 3 帧拼接（展示旋转/流动）
for style in ("spool", "thread", "tornado", "soul"):
    bg = SpellBackground("test", bg_style=style)
    montage = pygame.Surface((576 * 3, 670))
    for i, ft in enumerate((40, 110, 200)):
        while bg.timer < ft:
            bg.update(1/60)
        bg.draw(screen)
        montage.blit(screen, (i * 576, 0))
    pygame.image.save(montage, os.path.join(outdir, "preview_%s_3frames.png" % style))

# 6 图标展示
tile = 190
canvas = pygame.Surface((tile*3, tile*2))
canvas.fill((14, 16, 26))
order = ["icon_spool", "icon_string", "icon_arack", "icon_fang", "icon_fragment", "icon_essence"]
for i, key in enumerate(order):
    pat = _get_pattern(key)
    sc = min((tile*0.82)/pat.get_width(), (tile*0.82)/pat.get_height())
    img = pygame.transform.smoothscale(pat, (max(1,int(pat.get_width()*sc)), max(1,int(pat.get_height()*sc))))
    tx, ty = (i % 3) * tile, (i // 3) * tile
    canvas.blit(img, (tx + (tile-img.get_width())//2, ty + (tile-img.get_height())//2))
pygame.image.save(canvas, os.path.join(outdir, "spellbg_icons.png"))
pygame.quit()
print("previews saved to", outdir)
