# -*- coding: utf-8 -*-
# 立绘头部高度测量 v3 + 目视校验（红线 = 测出来的「肩线/脖子」）。
# 判据：取内容顶部 15% 的行宽中位数当头宽 W0，往下第一行宽度 > 1.25*W0 即视作肩线。
#
# 用法：python tools\_portrait_head_probe.py [new|another]
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
TARGET_H = 320
COLS = 6
PAD = 10
LABEL_H = 18


def row_widths(mask, rect):
    widths = {}
    for y in range(rect.top, rect.bottom):
        x0 = x1 = None
        for x in range(rect.left, rect.right):
            if mask.get_at((x, y)):
                if x0 is None:
                    x0 = x
                x1 = x
        if x0 is not None:
            widths[y] = x1 - x0 + 1
    return widths


def smooth(series, k):
    if k <= 1:
        return list(series)
    half = k // 2
    return [sum(series[max(0, i - half):min(len(series), i + half + 1)])
            / float(min(len(series), i + half + 1) - max(0, i - half))
            for i in range(len(series))]


def head_height(widths):
    rows = sorted(widths)
    series = [widths[y] for y in rows]
    H = len(series)
    if H < 16:
        return H
    k = max(3, (int(H * 0.02) // 2) * 2 + 1)
    sm = smooth(series, k)
    band = sm[:max(2, int(H * 0.15))]
    w0 = sorted(band)[len(band) // 2]
    thr = w0 * 1.25
    for i in range(int(H * 0.10), int(H * 0.60)):
        if sm[i] > thr:
            return i
    return int(H * 0.45)


def main():
    art = sys.argv[1] if len(sys.argv) > 1 else cfg.BOSS_ART_DEFAULT
    pygame.init()
    pygame.display.set_mode((64, 64))
    font = pygame.font.SysFont("consolas", 13)

    entries = [("boss:" + k, cfg.boss_art_path(k, art)) for k in sorted(cfg.BOSS_ART_FILES)]
    entries += [("self:" + k, cfg.player_character_path("portrait", k))
                for k, _l in cfg.player_character_options()]

    cells = []
    print("=== 套组 %s ===" % art)
    for label, path in entries:
        img = pygame.image.load(path).convert_alpha()
        mask = pygame.mask.from_surface(img)
        rects = mask.get_bounding_rects()
        rect = rects[0]
        for r in rects[1:]:
            rect = rect.union(r)
        widths = row_widths(mask, rect)
        head = head_height(widths)
        frac = head / float(rect.height)
        print("%-26s 头高 %4d / 内容高 %4d = %.3f" % (label, head, rect.height, frac))
        scale = TARGET_H / float(rect.height)
        thumb = pygame.transform.smoothscale(
            img.subsurface(rect), (max(1, int(rect.width * scale)), TARGET_H))
        cells.append((label, thumb, frac))

    cell_w = max(t.get_width() for _l, t, _f in cells) + PAD * 2
    cell_h = TARGET_H + LABEL_H + PAD * 2
    rows = (len(cells) + COLS - 1) // COLS
    sheet = pygame.Surface((cell_w * COLS, cell_h * rows))
    sheet.fill((24, 24, 32))
    for index, (label, thumb, frac) in enumerate(cells):
        cx = (index % COLS) * cell_w
        cy = (index // COLS) * cell_h
        sheet.blit(font.render("%s h=%.2f" % (label, frac), True, (255, 230, 120)),
                   (cx + PAD, cy + PAD))
        x = cx + (cell_w - thumb.get_width()) // 2
        y = cy + PAD + LABEL_H
        bg = pygame.Surface(thumb.get_size())
        bg.fill((64, 64, 78))
        sheet.blit(bg, (x, y))
        sheet.blit(thumb, (x, y))
        for step in range(1, 20):
            gy = y + TARGET_H * step // 20
            pygame.draw.line(sheet, (120, 120, 130), (cx + 1, gy), (cx + cell_w - 2, gy), 1)
            if step % 5 == 0:
                sheet.blit(font.render(str(step * 5), True, (200, 200, 210)), (cx + 2, gy - 13))
        neck_y = y + int(TARGET_H * frac)
        pygame.draw.line(sheet, (255, 60, 60), (x, neck_y), (x + thumb.get_width(), neck_y), 2)
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "_portrait_head_%s.png" % art)
    pygame.image.save(sheet, out)
    print("saved %s" % out)
    pygame.quit()


if __name__ == "__main__":
    main()
