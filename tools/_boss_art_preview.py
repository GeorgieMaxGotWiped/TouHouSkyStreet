# -*- coding: utf-8 -*-
# Boss 立绘套组预览：把各套组的 Boss 立绘（含白底抠图结果）拼成对照图，
# 方便检查抠图效果与各套组在游戏内的展示大小。
# 用法（在项目根目录执行）：python tools/_boss_art_preview.py

import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

pygame.init()
pygame.display.set_mode((320, 240))
sys.path.insert(0, os.getcwd())

from src.engine import settings as cfg
from src.engine import boss_art
from src.entities.boss import _get_boss_sprite

CELL = 240          # 每格边长
SPRITE_H = 220      # 立绘展示高度（与 Boss 战贴图同量级）
OUT = os.path.join("previews", "_boss_art_preview.png")


def main():
    keys = list(cfg.BOSS_ART_FILES)
    sets = list(cfg.BOSS_ART_SETS)
    sheet = pygame.Surface((CELL * len(keys), CELL * len(sets)))
    sheet.fill((18, 18, 26))
    for row, art in enumerate(sets):
        cfg.set_boss_art(art)
        for col, key in enumerate(keys):
            path = cfg.boss_art_path(key)
            t0 = time.time()
            sprite = _get_boss_sprite(path, SPRITE_H)
            cost = time.time() - t0
            if sprite is None:
                print("  [缺失] %s %s" % (art, path))
                continue
            sheet.blit(sprite, (col * CELL + (CELL - sprite.get_width()) // 2,
                                row * CELL + (CELL - SPRITE_H) // 2))
            print("  %-8s %-22s 源 %s 展示 %s 耗时 %.2fs"
                  % (art, key, boss_art.load_sprite(path).get_size(), sprite.get_size(), cost))
    os.makedirs("previews", exist_ok=True)
    pygame.image.save(sheet, OUT)
    print("预览已保存：%s（%dx%d，行=%s）" % (OUT, sheet.get_width(), sheet.get_height(), "/".join(sets)))


if __name__ == "__main__":
    main()
