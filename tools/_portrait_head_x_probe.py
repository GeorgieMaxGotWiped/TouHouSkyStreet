# -*- coding: utf-8 -*-
"""量每张对话立绘「头部」在屏幕上的横向落点。

头部 = 内容框顶部的 head_ratio x 内容高 那一条里的不透明像素范围（head_ratio 见表），
只看这些行就能知道人物的脸落在哪。用来判断有没有把脸推出战斗框。
"""
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

from src.engine import game as game_module
from src.engine import settings as cfg
from src.engine import boss_art

import _portrait_harmony_check as check

SIDE_SHIFT = 60
RETREAT = 30


def head_span(path, ratio):
    """返回 (content_l, content_r, content_top, head_l, head_r)，逻辑像素"""
    img = boss_art.load_sprite(path)
    w, h = img.get_size()
    mask = pygame.mask.from_surface(img)
    rects = mask.get_bounding_rects()
    if not rects:
        return None
    cr = rects[0]
    for r in rects[1:]:
        cr = cr.union(r)
    # 头部那一条：内容顶部往下 head_ratio x 内容高
    rows = max(1, int(round(ratio * cr.height)))
    cols = []
    for y in range(cr.top, min(h, cr.top + rows)):
        for x in range(cr.left, cr.left + cr.width):
            if mask.get_at((x, y)):
                cols.append(x)
    if not cols:
        cols = [cr.left, cr.left + cr.width - 1]
    return cr.left, cr.left + cr.width, cr.top, min(cols), max(cols) + 1


def main():
    art = sys.argv[1] if len(sys.argv) > 1 else None
    pygame.init()
    original = game_module.load_user_config
    game_module.load_user_config = lambda: dict(original(), fullscreen=False)
    game_module.Game()
    if art:
        cfg.set_boss_art(art)
    from src.ui import dialogue

    table = check.factories()
    band_l = cfg.BATTLE_OFFSET_X + 12
    band_r = band_l + cfg.BATTLE_AREA_WIDTH - 24
    box_l = cfg.BATTLE_OFFSET_X
    box_r = cfg.BATTLE_OFFSET_X + cfg.BATTLE_AREA_WIDTH
    print("战斗区可视 %d..%d  裁剪 %d..%d  套组=%s" % (band_l, band_r, box_l, box_r, cfg.get_boss_art()))
    for label, key, prep in check.CASES:
        stage = table[key]()
        prep(stage)
        harmonize = not getattr(stage, "items_disabled", False)
        print("\n%s" % label)
        for name, path in stage.dialogue_portraits.items():
            ratio = cfg.dialogue_portrait_head_ratio(path)
            if ratio is None:
                print("   %-22s (未登记，不补偿也不摆位)" % name)
                continue
            scale = float(getattr(stage, "dialogue_portrait_scales", {}).get(name, 1.0))
            sprite, (b_l, b_r, ctop) = dialogue.get_portrait(path, scale, harmonize=harmonize)
            if sprite is None:
                continue
            sw, sh = sprite.get_size()
            span = head_span(path, ratio)
            k = sh / float(boss_art.load_sprite(path).get_height())
            _, _, _, hl, hr = span
            # 按 _draw_portrait 的算法复算屏幕坐标（说话者状态：retreat=SIDE_SHIFT）
            side = stage.dialogue_portrait_sides.get(name)
            if side is None:
                side = "left" if path == cfg.SELF_SPRITE else "right"
            off = (getattr(stage, "dialogue_portrait_offsets", None) or {}).get(name, 0)
            speaker = stage.dialogue_lines[0][0] == name
            retreat = SIDE_SHIFT if speaker else SIDE_SHIFT + RETREAT
            if side == "left":
                px = band_l - b_l - retreat
            else:
                px = band_r - b_r + off + retreat
            hx0, hx1 = int(px + hl * k), int(px + hr * k)
            flag = ""
            if hx1 > box_r:
                flag = "  <== 头被右裁剪 %d px" % (hx1 - box_r)
            if hx0 < box_l:
                flag += "  <== 头被左裁剪 %d px" % (box_l - hx0)
            print("   %-22s side=%-5s %s 头 x=%4d..%4d  外框 %4d..%4d%s"
                  % (name, side, "说话" if speaker else "旁观", hx0, hx1, px, px + sw, flag))
    pygame.quit()


main()
