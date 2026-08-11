# -*- coding: utf-8 -*-
# 敌弹图集预览：裁剪槽位 + 染色 + 游戏内渲染效果
# 运行：python tools\_bullet_atlas_preview.py
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
import sys
import pygame

sys.path.insert(0, os.getcwd())
pygame.init()
screen = pygame.display.set_mode((960, 720))

from src.entities import bullet_atlas
from src.entities.bullet import create_bullet_angle
from src.engine import settings as cfg

canvas = pygame.Surface((960, 720))
canvas.fill((16, 20, 30))
font = pygame.font.SysFont("consolas", 15)
font_b = pygame.font.SysFont("consolas", 18, bold=True)

# --- 左区：整张图集 + 槽位框 ---
atlas = bullet_atlas._load_atlas()
zoom = 2
ax, ay = 20, 46
canvas.blit(pygame.transform.scale(atlas, (256 * zoom, 256 * zoom)), (ax, ay))
for slot, rect in bullet_atlas.SLOT_RECTS.items():
    x, y, w, h = rect
    color = (255, 170, 60) if slot != "big" else (80, 220, 255)
    pygame.draw.rect(canvas, color, (ax + x * zoom, ay + y * zoom, w * zoom, h * zoom), 1)
    canvas.blit(font.render(slot, True, color), (ax + x * zoom + 2, ay + y * zoom + 2))
canvas.blit(font_b.render("SLOT_RECTS over etama.png", True, (230, 230, 230)), (ax, ay - 24))

# --- 右上：槽位放大（原色 + 红/蓝染色示例） ---
sx, sy = 20 + 256 * zoom + 44, 46
cell = 92
canvas.blit(font_b.render("slots: native / red / blue", True, (230, 230, 230)), (sx, sy - 24))
for i, slot in enumerate(sorted(bullet_atlas.SLOT_RECTS)):
    col = i % 3
    row = i // 3
    cx = sx + col * (cell + 30)
    cy = sy + row * (cell + 34)
    for k, tint in enumerate((None, (255, 60, 60), (60, 160, 255))):
        spr = bullet_atlas.get_sprite(slot, 56, tint_color=tint)
        tx = cx + k * (cell // 3)
        if spr is not None:
            canvas.blit(spr, (tx + (cell // 3 - spr.get_width()) // 2, cy + 10))
    rect = bullet_atlas.SLOT_RECTS[slot]
    canvas.blit(font.render(f"{slot} {rect[2]}x{rect[3]}", True, (200, 200, 200)), (cx, cy + cell - 14))

# --- 下区：游戏内渲染（旋转 + 染色） ---
py = 46 + 6 * (cell + 34) + 10
canvas.blit(font_b.render("in-game (type, radius, angle, color)", True, (230, 230, 230)), (20, py - 24))
samples = [
    ("circle", 3.0, 0.0, (255, 60, 60)),
    ("circle", 3.0, 0.0, (60, 160, 255)),
    ("rice", 2.5, -0.7, (255, 200, 60)),
    ("arrow", 3.0, 2.2, (120, 255, 120)),
    ("knife", 2.5, 0.9, (255, 140, 60)),
    ("big", 5.0, 0.0, (170, 90, 255)),
]
for i, (btype, radius, ang, color) in enumerate(samples):
    b = create_bullet_angle(90 + i * 145, py + 55, ang, 1.0, btype, radius=radius, color=color)
    b.draw(canvas, 0, 0)
    canvas.blit(font.render(f"{btype} r={radius}", True, (210, 210, 210)), (90 + i * 145 - 50, py + 85))

out1 = os.path.join(os.getcwd(), "previews", "bullet_atlas_preview.png")
os.makedirs(os.path.dirname(out1), exist_ok=True)
pygame.image.save(canvas, out1)
print("saved:", out1)
pygame.quit()
