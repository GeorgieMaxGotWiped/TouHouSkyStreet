
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
import numpy as np
sys.path.insert(0, os.getcwd())
import src.engine.spell_bg as sb

pygame.init()
screen = pygame.display.set_mode((576, 670))

files = ["Luxurious_Spool.png", "Soul_String.png", "Arachne's_Fang.png",
         "Arachne_Fragment.png", "Arack.png", "Spider_Essence.png"]
for f in files:
    path = os.path.join(sb.cfg.ASSETS_DIR, "backgrounds", "stage1", f)
    img = pygame.image.load(path)
    a3 = pygame.surfarray.array3d(img)
    lum = a3.mean(axis=2)
    print("====", f)
    print("  a3 range:", a3.min(), a3.max(), "lum mean:", round(float(lum.mean()), 2))
    print("  lum hist:", np.histogram(lum, bins=[0,6,12,24,48,96,192,256])[0].tolist())
    pa = pygame.surfarray.array_alpha(img) if (img.get_flags() & pygame.SRCALPHA) else None
    if pa is not None:
        print("  alpha range:", pa.min(), pa.max())
    print("  get_palette head:", img.get_palette()[:6])
pygame.quit()
