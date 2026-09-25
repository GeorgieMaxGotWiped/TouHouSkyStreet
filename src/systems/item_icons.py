# 物品图标加载与绘制
# 图标文件位于 assets/items/<item_id>.png，缺失时优雅回退（不显示图标）

import os
import pygame
from src.engine import hires
from src.engine import settings as cfg

_icon_cache = {}
_attempted = set()


def get_item_icon_path(item_id):
    """返回物品图标文件路径（可能不存在）"""
    return os.path.join(cfg.ITEMS_DIR, f"{item_id}.png")


def get_item_icon(item_id, size=32, factor=1):
    """加载物品图标并等比缩放到边长不超过 size 的方形区域；失败返回 None。

    factor 为渲染倍率：>1 时直接缩放到高分辨率表面，图标保持原始像素，
    不再经历「先缩到逻辑尺寸、再被整幅放大」的二次损失。
    返回表面的度量接口仍按逻辑尺寸上报，调用方的居中计算不用改。
    """
    factor = max(1, int(factor))
    key = (item_id, size, factor)
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
            _icon_cache[key] = hires.scaled_image(img, (new_w, new_h), factor)
    except Exception as e:
        print(f"[ItemIcon] Failed to load {path}: {e}")
    return _icon_cache.get(key)


def draw_item_icon(screen, item_id, x, y, size=32, padding=0, ui_layer=False):
    """在屏幕坐标 (x, y) 处绘制物品图标（居中于 size x size 方格）；无图标时跳过。
    padding 会在四周留白，使图标缩进并完整落在框内。

    ui_layer=True 时走 screen.blit（高分辨率图层：与文字 / 面板同层），图标排在该层
    的最后，所以压得住同样画在这一层上的底板；默认走 blit_gpu（显卡实体层，回放时
    在所有图层之下），只适合底板也画在同一层的界面 —— 底板画在高分辨率图层、图标
    画在显卡实体层时，图标会被底板盖住（STG 右侧的掉落弹窗就是这么错的）。
    """
    inner = size - 2 * padding
    if inner <= 0:
        return
    factor = screen.bake_factor() if hasattr(screen, "bake_factor") else 1
    icon = get_item_icon(item_id, inner, factor)
    if icon is None:
        return
    dest = (x + (size - icon.get_width()) // 2,
            y + (size - icon.get_height()) // 2)
    blit_gpu = getattr(screen, "blit_gpu", None)
    if ui_layer or blit_gpu is None:
        screen.blit(icon, dest)
    else:
        blit_gpu(icon, dest)
