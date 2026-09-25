# -*- coding: utf-8 -*-
# 打印对话立绘在屏幕上实际被缩放到的尺寸（走 get_portrait 的真实代码路径），
# 用来核对「同一化后每张立绘到底多大」。
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pygame

pygame.init()
pygame.display.set_mode((960, 720))

from src.engine import settings as cfg
from src.ui import dialogue

cfg.set_boss_art("another")
cfg.set_player_character("archer")

print("BASE_SCALE=%.2f TOP_TARGET=%d" % (dialogue.DIALOGUE_PORTRAIT_BASE_SCALE,
                                         dialogue.DIALOGUE_PORTRAIT_TOP_TARGET))
print("%-24s %-18s %-12s %-10s" % ("label", "原图/内容", "屏幕尺寸(逻辑px)", "宽度"))
for label, path in ([("self:" + k, cfg.player_character_path("portrait", k))
                     for k, _l in cfg.player_character_options()]
                    + [("boss:" + k, cfg.boss_art_path(k, "another"))
                       for k in sorted(cfg.BOSS_ART_FILES)]):
    sprite, box = dialogue.get_portrait(path, 1.0)
    if sprite is None:
        print("%-24s 载入失败" % label)
        continue
    ph = sprite.get_height() // max(1, getattr(sprite, "hi_scale", 1))
    pw = sprite.get_width() // max(1, getattr(sprite, "hi_scale", 1))
    src = pygame.image.load(path)
    print("%-24s %4dx%-5d 高%4d 宽%4d 头宽比 %.2f 内容左右(%d,%d) 内容顶 %d"
          % (label, src.get_width(), src.get_height(), ph, pw,
             pw / float(ph), box[0], box[1], box[2]))
pygame.quit()
