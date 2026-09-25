# -*- coding: utf-8 -*-
# 立绘取景一览：把某套组的全部 Boss 立绘 + 自机立绘缩成缩略图拼成一张预览，
# 用来肉眼确认「哪些是半身特写、哪些是全身」——同一化后人物大小不一致的根因。
#
# 用法：python tools\_portrait_sheet.py [new|another] [每行张数]
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


def main():
    art = sys.argv[1] if len(sys.argv) > 1 else cfg.BOSS_ART_DEFAULT
    cols = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    pygame.init()
    pygame.display.set_mode((64, 64))
    font = pygame.font.SysFont("consolas", 14)

    entries = [("boss:" + key, cfg.boss_art_path(key, art)) for key in sorted(cfg.BOSS_ART_FILES)]
    entries += [("self:" + key, cfg.player_character_path("portrait", key))
                for key, _label in cfg.player_character_options()]

    thumb_h = 260
    pad = 8
    label_h = 18
    cells = []
    for label, path in entries:
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        scale = thumb_h / float(h)
        thumb = pygame.transform.smoothscale(img, (max(1, int(w * scale)), thumb_h))
        cells.append((label, thumb))

    cell_w = max(t.get_width() for _l, t in cells) + pad * 2
    cell_h = thumb_h + label_h + pad * 2
    rows = (len(cells) + cols - 1) // cols
    sheet = pygame.Surface((cell_w * cols, cell_h * rows))
    sheet.fill((28, 28, 36))
    for index, (label, thumb) in enumerate(cells):
        cx = (index % cols) * cell_w
        cy = (index // cols) * cell_h
        sheet.blit(font.render(label, True, (255, 230, 120)), (cx + pad, cy + pad))
        x = cx + (cell_w - thumb.get_width()) // 2
        y = cy + pad + label_h
        checker = pygame.Surface(thumb.get_size())
        checker.fill((70, 70, 84))
        sheet.blit(checker, (x, y))
        sheet.blit(thumb, (x, y))
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "_portrait_sheet_%s.png" % art)
    pygame.image.save(sheet, out)
    print("saved %s (%dx%d, %d 张)" % (out, sheet.get_width(), sheet.get_height(), len(cells)))
    pygame.quit()


if __name__ == "__main__":
    main()
