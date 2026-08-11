
import os, sys, traceback
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
    print(f, "->", img.get_size(), "depth:", img.get_bitsize(), "flags:", img.get_flags())
    try:
        s = sb._load_item_icon(f, tint=(1,1,1), target_h=100, dim=1.0, glow=0.3)
        print("   OK size:", None if s is None else s.get_size())
    except Exception:
        print("   EXC:")
        traceback.print_exc()
pygame.quit()
