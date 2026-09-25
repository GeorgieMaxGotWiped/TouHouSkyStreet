import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.getcwd())
import pygame
pygame.init(); pygame.display.set_mode((64, 64))
MEDIA = r"C:\Users\admin\.codex\visualizations\2026\09\21\01a0c242-d883-7dc0-9455-e08caaf22f33"
OUT = os.path.join(os.getcwd(), "previews")
CASES = ["s1_arachne", "s2_dragon", "s4_sadan", "s5_watcher", "s5_professor", "s5_thorn",
         "s5_livid", "s5_maxor", "s5_necron", "s6_kaeman", "ex_wizardman", "ex_barry"]
font = pygame.font.SysFont("consolas", 16)
scale = 0.42
tiles = []
for label in CASES:
    img = pygame.image.load(os.path.join(OUT, "_dialogue_%s.png" % label))
    tiles.append((label, pygame.transform.smoothscale(
        img, (int(img.get_width() * scale), int(img.get_height() * scale)))))
cols = 3
tw = tiles[0][1].get_width(); th = tiles[0][1].get_height()
rows = (len(tiles) + cols - 1) // cols
sheet = pygame.Surface((tw * cols, (th + 22) * rows))
sheet.fill((18, 18, 24))
for i, (label, t) in enumerate(tiles):
    x = (i % cols) * tw
    y = (i // cols) * (th + 22)
    sheet.blit(font.render(label, True, (255, 220, 120)), (x + 4, y + 2))
    sheet.blit(t, (x, y + 22))
pygame.image.save(sheet, os.path.join(MEDIA, "dialogue_all.png"))
print("saved", sheet.get_size())
pygame.quit()
