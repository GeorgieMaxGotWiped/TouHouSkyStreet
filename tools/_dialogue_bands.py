# -*- coding: utf-8 -*-
# 从已渲染的对话预览里裁出「立绘带」，堆成一张对比图：同屏两张立绘的头部大小一目了然。
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.getcwd())
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pygame

OUT_DIR = os.path.join(os.getcwd(), "previews")
CASES = ["s1_arachne", "s2_dragon", "s4_sadan", "s5_professor", "s5_necron", "s6_kaeman"]
BAND_TOP, BAND_BOTTOM = 240, 620      # 立绘带（hires 像素）
MEDIA = r"C:\Users\admin\.codex\visualizations\2026\09\21\01a0c242-d883-7dc0-9455-e08caaf22f33"


def main():
    pygame.init()
    pygame.display.set_mode((64, 64))
    font = pygame.font.SysFont("consolas", 20)
    strips = []
    for label in CASES:
        img = pygame.image.load(os.path.join(OUT_DIR, "_dialogue_%s.png" % label))
        strip = img.subsurface(pygame.Rect(0, BAND_TOP, img.get_width(), BAND_BOTTOM - BAND_TOP))
        strips.append((label, strip.copy()))
    width = max(s.get_width() for _l, s in strips) + 200
    height = sum(s.get_height() + 34 for _l, s in strips)
    sheet = pygame.Surface((width, height))
    sheet.fill((20, 20, 26))
    y = 0
    for label, strip in strips:
        sheet.blit(font.render(label, True, (255, 220, 120)), (8, y + 6))
        sheet.blit(strip, (200, y + 28 - 6))
        y += strip.get_height() + 34
    os.makedirs(MEDIA, exist_ok=True)
    out = os.path.join(MEDIA, "dialogue_bands.png")
    pygame.image.save(sheet, out)
    print("saved %s (%dx%d)" % (out, sheet.get_width(), sheet.get_height()))
    pygame.quit()


if __name__ == "__main__":
    main()
