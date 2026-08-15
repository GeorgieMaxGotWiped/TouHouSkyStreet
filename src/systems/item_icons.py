# 物品图标加载与绘制
# 图标文件位于 assets/items/<item_id>.png，缺失时优雅回退（不显示图标）

import os
import pygame
from src.engine import settings as cfg

_icon_cache = {}
_attempted = set()


def get_item_icon_path(item_id):
    """返回物品图标文件路径（可能不存在）"""
    return os.path.join(cfg.ITEMS_DIR, f"{item_id}.png")


def get_item_icon(item_id, size=32):
    """加载物品图标并等比缩放到边长不超过 size 的方形区域；失败返回 None"""
    key = (item_id, size)
    if key in _attempted:
        return _icon_cache.get(key)
    _attempted.add(key)
    path = get_item_icon_path(item_id)
    try:
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            w, h = img.get_size()
            if w <= 0 or h <= 0:
                raise ValueError("bad icon size")
            scale = size / max(w, h)
            new_w = max(1, int(round(w * scale)))
            new_h = max(1, int(round(h * scale)))
            _icon_cache[key] = pygame.transform.smoothscale(img, (new_w, new_h))
    except Exception as e:
        print(f"[ItemIcon] Failed to load {path}: {e}")
    return _icon_cache.get(key)


def draw_item_icon(screen, item_id, x, y, size=32):
    """在屏幕坐标 (x, y) 处绘制物品图标（居中于 size x size 方格）；无图标时跳过"""
    icon = get_item_icon(item_id, size)
    if icon is None:
        return
    screen.blit(icon, (x + (size - icon.get_width()) // 2,
                       y + (size - icon.get_height()) // 2))
