# -*- coding: utf-8 -*-
# 改造前后并排对比：左=改造前，右=改造后，裁到立绘带。
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.getcwd())
import pygame

MEDIA = r"C:\Users\admin\.codex\visualizations\2026\09\21\01a0c242-d883-7dc0-9455-e08caaf22f33"
OUT = os.path.join(os.getcwd(), "previews")
BEFORE = os.path.join(OUT, "_before_dialogue")
CASES = ["s1_arachne", "s2_dragon", "s3_bonzo", "s4_sadan", "s5_watcher",
         "s5_professor", "s5_thorn", "s5_livid", "s5_maxor", "s5_necron",
         "s6_kaeman", "ex_wizardman", "ex_barry"]
TOP, BOTTOM = 170, 560
SCALE = 0.55


def main():
    pygame.init()
    pygame.display.set_mode((64, 64))
    font = pygame.font.SysFont("consolas", 18)
    band_h = int((BOTTOM - TOP) * SCALE)
    tiles = []
    for label in CASES:
        pair = []
        for src in (BEFORE, OUT):
            img = pygame.image.load(os.path.join(src, "_dialogue_%s.png" % label))
            band = img.subsurface(pygame.Rect(0, TOP, img.get_width(), BOTTOM - TOP)).copy()
            pair.append(pygame.transform.smoothscale(
                band, (int(band.get_width() * SCALE), band_h)))
        tiles.append((label, pair))
    tw = tiles[0][1][0].get_width() * 2 + 8
    th = band_h + 24
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    sheet = pygame.Surface((tw * cols, th * rows))
    sheet.fill((18, 18, 24))
    for i, (label, pair) in enumerate(tiles):
        x = (i % cols) * tw
        y = (i // cols) * th
        sheet.blit(font.render(label + "   [left=before  right=after]", True, (255, 220, 120)),
                   (x + 4, y + 2))
        sheet.blit(pair[0], (x, y + 22))
        sheet.blit(pair[1], (x + pair[0].get_width() + 8, y + 22))
        pygame.draw.line(sheet, (90, 90, 110), (x, y), (x, y + th - 1))
    path = os.path.join(MEDIA, "dialogue_harmonize_ab.png")
    pygame.image.save(sheet, path)
    print("saved", path, sheet.get_size())
    pygame.quit()


main()
