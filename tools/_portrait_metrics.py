# -*- coding: utf-8 -*-
# 立绘取景度量：打印各张对话立绘的「画面内容框 / 人物占画面比例 / 头部高度估计」，
# 用来判断同屏两张立绘看起来一大一小的原因（取景不同 = 同一化后人物大小不同）。
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

pygame.init()
pygame.display.set_mode((64, 64))


def profile(surface):
    """按行统计不透明像素的左右边界，返回 (行宽数组, 行上下界)"""
    mask = pygame.mask.from_surface(surface)
    rects = mask.get_bounding_rects()
    if not rects:
        return None
    rect = rects[0]
    for r in rects[1:]:
        rect = rect.union(r)
    widths = {}
    for y in range(rect.top, rect.bottom):
        x0, x1 = None, None
        for x in range(rect.left, rect.right):
            if mask.get_at((x, y)):
                if x0 is None:
                    x0 = x
                x1 = x
        if x0 is not None:
            widths[y] = x1 - x0 + 1
    return rect, widths


def head_estimate(rect, widths):
    """头高估计：从内容顶往下，行宽第一次超过「初始宽度 * 1.75」的那一行当作肩线"""
    rows = sorted(widths)
    if len(rows) < 8:
        return 0
    top = rows[0]
    content_h = rows[-1] - top + 1
    probe = rows[:max(2, len(rows) // 12)]          # 顶部 1/12 的宽度当中位数（近似头宽）
    head_w = sorted(widths[y] for y in probe)[len(probe) // 2]
    for y in rows:
        if widths[y] > head_w * 1.75:
            return max(1, y - top)
    return content_h


def report(label, path):
    img = pygame.image.load(path)
    img = img.convert_alpha()
    w, h = img.get_size()
    prof = profile(img)
    if prof is None:
        print("%-28s %s" % (label, "空图"))
        return
    rect, widths = prof
    ch = rect.height
    head = head_estimate(rect, widths)
    print("%-28s 图 %4dx%-5d 内容 %4dx%-5d 内容高/图高 %.2f 内容宽/高 %.2f 头顶留白 %.2f 头高/内容高 %.2f"
          % (label, w, h, rect.width, rect.height, ch / float(h),
             rect.width / float(ch), rect.top / float(h), head / float(ch)))


def main():
    print("=== Boss 立绘（当前套组 %s） ===" % cfg.get_boss_art())
    for key in sorted(cfg.BOSS_ART_FILES):
        report(key, cfg.boss_art_path(key))
    print("=== 另一套组 ===")
    for key in sorted(cfg.BOSS_ART_FILES):
        other = "new" if cfg.get_boss_art() == "another" else "another"
        report(key, cfg.boss_art_path(key, other))
    print("=== 自机立绘 ===")
    for key, _label in cfg.player_character_options():
        report(key, cfg.player_character_path("portrait", key))
    pygame.quit()


if __name__ == "__main__":
    main()
