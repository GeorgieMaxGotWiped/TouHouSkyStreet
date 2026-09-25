# -*- coding: utf-8 -*-
# 临时脚本：由 skeletor.png 生成 Skeleton Lord 立绘（凋零紫配色），并出对比图
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
pygame.init(); pygame.display.set_mode((64, 64))

SRC = r"assets/sprites/enemies/stage6/skeletor.png"
DST = r"assets/sprites/enemies/stage6/skeleton_lord.png"
OUT = r"C:\Users\admin\.codex\visualizations\2026\09\25\01a0d626-88d7-7b43-be2a-ef20c066fb95\s6_skeleton_lord.png"

# 凋零紫渐变：暗部（深紫黑）→ 中间（凋零紫）→ 亮部（苍白骨色）
STOPS = [(0.00, (34, 20, 46)), (0.32, (86, 52, 128)), (0.62, (150, 106, 206)),
         (0.85, (206, 186, 236)), (1.00, (240, 236, 248))]


def ramp(l):
    for i in range(len(STOPS) - 1):
        a, ca = STOPS[i]
        b, cb = STOPS[i + 1]
        if l <= b or i == len(STOPS) - 2:
            t = 0.0 if b <= a else max(0.0, min(1.0, (l - a) / (b - a)))
            return tuple(int(round(ca[k] + (cb[k] - ca[k]) * t)) for k in range(3))
    return STOPS[-1][1]


def recolor(src):
    out = pygame.Surface(src.get_size(), pygame.SRCALPHA, 32)
    w, h = src.get_size()
    for y in range(h):
        for x in range(w):
            r, g, b, a = src.get_at((x, y))
            if a == 0:
                continue
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
            nr, ng, nb = ramp(lum ** 0.92)
            out.set_at((x, y), (nr, ng, nb, a))
    return out


src = pygame.image.load(SRC).convert_alpha()
lord = recolor(src)
pygame.image.save(lord, DST)
print("saved", DST, lord.get_size())

cell = 300
sheet = pygame.Surface((cell * 3 + 40, cell + 40))
sheet.fill((30, 32, 40))
font = pygame.font.SysFont("Microsoft YaHei", 14)
items = [("原 skeletor.png（凋零骑士）", src), ("新 skeleton_lord.png", lord)]
for i, (label, im) in enumerate(items):
    k = min(cell / im.get_width(), (cell - 10) / im.get_height())
    im2 = pygame.transform.smoothscale(im, (max(1, int(im.get_width() * k)),
                                            max(1, int(im.get_height() * k))))
    x = 10 + i * (cell + 10)
    sheet.blit(font.render(label, True, (240, 240, 240)), (x, 8))
    sheet.blit(im2, (x + (cell - im2.get_width()) // 2, 28))
pygame.image.save(sheet, OUT)
print("saved", OUT)
