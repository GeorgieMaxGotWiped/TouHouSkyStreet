# -*- coding: utf-8 -*-
# 立绘取景标尺：立绘按内容框统一缩到 400px 高，叠加 5% 刻度线（每 20% 标注数字），
# 用来读每张立绘「头部高度 / 内容高度」——这个比例决定同屏时人物看起来谁大谁小。
#
# 用法：python tools\_portrait_ruler.py [new|another] [每张图多少格]
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.getcwd())
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pygame

from src.engine import settings as cfg

OUT_DIR = os.path.join(os.getcwd(), "previews")
MEDIA = r"C:\Users\admin\.codex\visualizations\2026\09\21\01a0c242-d883-7dc0-9455-e08caaf22f33"
TILE_H = 400
COLS = 3
PAD = 12
LABEL_H = 22


def content_rect(surface):
    rects = pygame.mask.from_surface(surface).get_bounding_rects()
    if not rects:
        return pygame.Rect(0, 0, *surface.get_size())
    rect = rects[0]
    for r in rects[1:]:
        rect = rect.union(r)
    return rect


def main():
    art = sys.argv[1] if len(sys.argv) > 1 else cfg.BOSS_ART_DEFAULT
    per_sheet = int(sys.argv[2]) if len(sys.argv) > 2 else 9
    pygame.init()
    pygame.display.set_mode((64, 64))
    font = pygame.font.SysFont("consolas", 16)
    small = pygame.font.SysFont("consolas", 13)

    entries = [("boss:" + k, cfg.boss_art_path(k, art)) for k in sorted(cfg.BOSS_ART_FILES)]
    entries += [("self:" + k, cfg.player_character_path("portrait", k))
                for k, _l in cfg.player_character_options()]

    cells = []
    for label, path in entries:
        img = pygame.image.load(path).convert_alpha()
        rect = content_rect(img)
        scale = TILE_H / float(rect.height)
        thumb = pygame.transform.smoothscale(
            img.subsurface(rect), (max(1, int(rect.width * scale)), TILE_H))
        cells.append((label, thumb, rect))

    sheet_index = 0
    for start in range(0, len(cells), per_sheet):
        chunk = cells[start:start + per_sheet]
        rows = (len(chunk) + COLS - 1) // COLS
        cell_w = max(t.get_width() for _l, t, _r in chunk) + PAD * 2
        cell_h = TILE_H + LABEL_H + PAD * 2
        sheet = pygame.Surface((cell_w * COLS, cell_h * rows))
        sheet.fill((22, 22, 30))
        for index, (label, thumb, rect) in enumerate(chunk):
            cx = (index % COLS) * cell_w
            cy = (index // COLS) * cell_h
            sheet.blit(font.render("%s  内容 %dx%d" % (label, rect.width, rect.height),
                                   True, (255, 230, 120)), (cx + PAD, cy + PAD))
            x = cx + (cell_w - thumb.get_width()) // 2
            y = cy + PAD + LABEL_H
            bg = pygame.Surface(thumb.get_size())
            bg.fill((62, 62, 76))
            sheet.blit(bg, (x, y))
            sheet.blit(thumb, (x, y))
            for step in range(1, 20):
                gy = y + TILE_H * step // 20
                color = (120, 120, 132) if step % 2 else (210, 210, 220)
                pygame.draw.line(sheet, color, (x, gy), (x + thumb.get_width() - 1, gy), 1)
                if step % 4 == 0:
                    sheet.blit(small.render(str(step * 5), True, color), (x + 2, gy - 13))
        out = os.path.join(OUT_DIR, "_portrait_ruler_%s_%d.png" % (art, sheet_index))
        pygame.image.save(sheet, out)
        os.makedirs(MEDIA, exist_ok=True)
        pygame.image.save(sheet, os.path.join(MEDIA, "portrait_ruler_%s_%d.png" % (art, sheet_index)))
        print("saved %s (%dx%d)" % (out, sheet.get_width(), sheet.get_height()))
        sheet_index += 1
    pygame.quit()


if __name__ == "__main__":
    main()
