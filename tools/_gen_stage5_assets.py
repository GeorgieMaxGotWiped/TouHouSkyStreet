# -*- coding: utf-8 -*-
# 生成五面占位素材：关卡标题卡与 7 名 BOSS RUSH Boss 贴图。
# 运行：python tools/_gen_stage5_assets.py
import math
import os

from PIL import Image, ImageDraw, ImageFont

os.makedirs(os.path.join("assets", "titles"), exist_ok=True)
os.makedirs(os.path.join("assets", "sprites", "bosses"), exist_ok=True)

FONT = os.path.join("assets", "fonts", "font2.otf")


def fit_font_width(text, target_w, max_size=150):
    lo, hi, best = 8, max_size, 8
    while lo <= hi:
        mid = (lo + hi) // 2
        font = ImageFont.truetype(FONT, mid)
        bb = font.getbbox(text)
        if bb[2] - bb[0] <= target_w:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def text_shadow(draw, text, font, cx, y, shadow=(2, 2), fill=(242, 246, 250, 255)):
    bb = draw.textbbox((0, 0), text, font=font)
    x = cx - (bb[2] - bb[0]) // 2 - bb[0]
    draw.text((x + shadow[0], y + shadow[1]), text, font=font, fill=(5, 7, 13, 255))
    draw.text((x, y), text, font=font, fill=fill)


def gen_title(path):
    w, h = 576, 670
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    label = ImageFont.truetype(FONT, fit_font_width("STAGE 5", 150))
    draw.text((36, 190), "STAGE 5", font=label, fill=(245, 245, 245, 255))

    main = ImageFont.truetype(FONT, fit_font_width("凋零之厅", 330))
    text_shadow(draw, "凋零之厅", main, w // 2, 250)

    sub = ImageFont.truetype(FONT, fit_font_width("The Wither Lords - Boss Rush", 420))
    text_shadow(draw, "The Wither Lords - Boss Rush", sub, w // 2, 338, shadow=(2, 2))

    # 凋零三头意象
    ex, ey = w // 2, 470
    for r, col, a in ((62, (90, 50, 120), 45), (46, (150, 70, 190), 70), (32, (230, 90, 120), 90)):
        oval = Image.new("RGBA", (r * 2 + 4, r * 2 + 4), (0, 0, 0, 0))
        od = ImageDraw.Draw(oval)
        od.ellipse((2, 2, r * 2 + 2, r * 2 + 2), fill=col + (a,))
        img.alpha_composite(oval, (ex - r - 2, ey - r - 2))
    for dx in (-60, 0, 60):
        draw.ellipse((ex + dx - 18, ey - 18, ex + dx + 18, ey + 18), fill=(20, 16, 26, 235))
        draw.ellipse((ex + dx - 4, ey - 8, ex + dx + 4, ey + 2), fill=(255, 120, 150, 255))

    img.save(path)
    print("saved", path)


def draw_wither_core(draw, cx, cy, main, glow, eye):
    # 外圈柔光
    for r, a in ((96, 24), (78, 38), (62, 58)):
        draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=glow + (a,))
    # 肩部
    draw.ellipse((cx - 84, cy - 14, cx + 84, cy + 98), fill=main + (255,))
    draw.ellipse((cx - 70, cy + 8, cx + 70, cy + 78), fill=tuple(min(255, c + 24) for c in main) + (255,))
    # 头部
    draw.ellipse((cx - 52, cy - 92, cx + 52, cy + 12), fill=main + (255,))
    draw.ellipse((cx - 40, cy - 80, cx + 40, cy - 4), fill=tuple(min(255, c + 22) for c in main) + (255,))
    # 双眼
    draw.ellipse((cx - 30, cy - 52, cx - 12, cy - 34), fill=eye + (255,))
    draw.ellipse((cx + 12, cy - 52, cx + 30, cy - 34), fill=eye + (255,))
    draw.ellipse((cx - 25, cy - 47, cx - 16, cy - 38), fill=(255, 255, 255, 220))
    draw.ellipse((cx + 17, cy - 47, cx + 26, cy - 38), fill=(255, 255, 255, 220))
    # 嘴
    draw.rectangle((cx - 22, cy - 18, cx + 22, cy - 12), fill=(12, 10, 16, 230))


def gen_boss(path, main, glow, eye, kind):
    w, h = 260, 240
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = w // 2, 120

    draw_wither_core(draw, cx, cy, main, glow, eye)

    if kind == "professor":
        # 学者兜帽
        draw.polygon([(cx - 70, cy - 80), (cx, cy - 122), (cx + 70, cy - 80),
                      (cx + 52, cy - 58), (cx - 52, cy - 58)], fill=tuple(max(0, c - 26) for c in main) + (255,))
        draw.line((cx - 66, cy + 56, cx + 86, cy - 30), fill=(90, 180, 90, 230), width=7)
    elif kind == "thorn":
        for i in range(12):
            a = i * math.tau / 12 + 0.26
            x0 = cx + math.cos(a) * 62
            y0 = cy - 10 + math.sin(a) * 62
            x1 = cx + math.cos(a) * 108
            y1 = cy - 10 + math.sin(a) * 108
            draw.line((x0, y0, x1, y1), fill=(180, 90, 255, 230), width=4)
    elif kind == "livid":
        draw.polygon([(cx, cy - 110), (cx - 58, cy - 24), (cx - 44, cy + 2),
                      (cx + 44, cy + 2), (cx + 58, cy - 24)], fill=tuple(min(255, c + 18) for c in main) + (255,))
        for dx in (-70, 70):
            draw.line((cx + dx, cy + 30, cx + dx - 16, cy - 16), fill=(80, 210, 240, 220), width=5)
    elif kind == "fire":
        for dx in (-72, 0, 72):
            draw.polygon([(cx + dx - 16, cy - 92), (cx + dx, cy - 130), (cx + dx + 16, cy - 92)],
                         fill=(255, 130, 40, 210))
    elif kind == "storm":
        for dx in (-60, 60):
            x = cx + dx
            pts = [(x, cy - 110), (x - 18, cy - 56), (x, cy - 58),
                   (x - 10, cy - 16), (x + 14, cy - 16)]
            draw.line(pts, fill=(130, 210, 255, 235), width=5, joint="curve")
    elif kind == "goldor":
        for dy in (-54, -14, 26):
            draw.rectangle((cx - 82, cy + dy, cx + 82, cy + dy + 16),
                           outline=(255, 210, 90, 220), width=5)
    elif kind == "necron":
        for dx in (-56, 0, 56):
            sx = cx + dx
            sy = cy - 100
            draw.ellipse((sx - 22, cy - 122, sx + 22, cy - 78), fill=(60, 24, 80, 235))
            draw.ellipse((sx - 6, sy, sx + 6, sy + 14), fill=(255, 90, 120, 255))

    img.save(path)
    print("saved", path)


def main():
    gen_title(os.path.join("assets", "titles", "stage5.png"))

    bosses = [
        ("professor.png", (94, 190, 116), (150, 230, 120), (235, 255, 220), "professor"),
        ("thorn.png", (120, 72, 180), (190, 110, 255), (255, 190, 250), "thorn"),
        ("livid.png", (56, 148, 182), (80, 210, 240), (220, 255, 255), "livid"),
        ("maxor.png", (176, 66, 42), (255, 130, 60), (255, 230, 140), "fire"),
        ("storm.png", (52, 112, 178), (120, 200, 255), (220, 245, 255), "storm"),
        ("goldor.png", (176, 128, 40), (255, 205, 90), (255, 250, 200), "goldor"),
        ("necron.png", (84, 36, 104), (190, 60, 235), (255, 90, 140), "necron"),
    ]
    for name, main, glow, eye, kind in bosses:
        gen_boss(os.path.join("assets", "sprites", "bosses", name), main, glow, eye, kind)


if __name__ == "__main__":
    main()
