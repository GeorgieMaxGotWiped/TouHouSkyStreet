# src/ui/skyblock_ui.py
"""Hypixel SkyBlock 原版 Minecraft GUI 风格绘制辅助。

参考 Hypixel SkyBlock 的 “Your Equipment and Stats” 菜单：
- 整屏浅灰容器 #C6C6C6 + 黑色外框；顶部深灰标题栏 + 右上角橙色刷新图标。
- 内容主体为 9 列方形槽位网格，槽位为 Minecraft 凹陷样式（左上深边、右下高光）。
- 物品只画图标；悬停时用 Minecraft 暗色提示框显示名称 / 稀有度 / 属性 / lore。

所有文字默认绘制黑色 1px 偏移阴影（Minecraft 文本风格）。
"""

import math
import random
import pygame

# --- 原版配色（取自 Minecraft 1.8.9 + 参考截图采样） ---
MENU_BG = (198, 198, 198)          # 容器浅灰 #C6C6C6
MENU_HEADER = (198, 198, 198)      # 标题栏底色（与容器同色，仅以分隔线区分）
MENU_MID = (139, 139, 139)         # 槽位亮灰 / 次级文字 #8B8B8B
SLOT_INNER = (87, 87, 87)          # 槽位内部 #575757
SLOT_DARK = (55, 55, 55)           # 槽位深边 / 标题文字 #373737
SLOT_LIGHT = (255, 255, 255)       # 槽位高光 #FFFFFF
EDGE = (0, 0, 0)                   # 外框黑边 #000000
EDGE_DARK = (45, 45, 45)           # 外框内暗边（近似原版内框阴影像素）
TIMBER = (60, 60, 60)              # 标题文字灰 #3C3C3C
SELECT_COLOR = (255, 206, 0)       # 选中高亮（SkyBlock 金） #FFCE00
ORANGE = (255, 170, 0)             # 刷新图标橙 #FFAA00
COIN_GOLD = (255, 215, 0)          # 金币黄 #FFD700
TEXT_SHADOW = (20, 20, 20)         # 文字阴影

# 深灰分区（比按钮深的界面底板，用于承载内容）
PANEL_BG = (62, 62, 62)
PANEL_BG_DARK = (46, 46, 46)
PANEL_TEXT = (240, 240, 240)         # 深灰分区上的主文字
PANEL_TEXT_DIM = (170, 170, 170)     # 深灰分区上的次级文字

# 现代 Minecraft 提示框：暗底 + 紫蓝渐变边框
TOOLTIP_BG = (16, 4, 16)
TOOLTIP_BORDER = (80, 0, 255)
TOOLTIP_BORDER_DARK = (45, 20, 200)

GRID_COLS = 9
SLOT_SIZE = 56
SLOT_GAP = 6

# --- 缓存背景（备用，浅灰界面通常不再需要渐变背景） ---
_backdrop = None


def _make_backdrop(width, height, top=(216, 216, 216), bottom=(176, 176, 176)):
    """生成浅灰渐变背景 Surface（供不使用整屏容器时的次要界面使用）。"""
    surf = pygame.Surface((width, height))
    for y in range(height):
        t = y / max(1, height - 1)
        color = (
            int(top[0] + (bottom[0] - top[0]) * t),
            int(top[1] + (bottom[1] - top[1]) * t),
            int(top[2] + (bottom[2] - top[2]) * t),
        )
        pygame.draw.line(surf, color, (0, y), (width, y))
    rng = random.Random(1234)
    for _ in range(int(width * height * 0.002)):
        x = rng.randrange(width)
        y = rng.randrange(height)
        v = rng.randrange(-4, 5)
        try:
            r, g, b = surf.get_at((x, y))[:3]
            surf.set_at((x, y), (max(0, min(255, r + v)),
                                 max(0, min(255, g + v)),
                                 max(0, min(255, b + v))))
        except Exception:
            pass
    return surf


def draw_backdrop(screen, dim=255):
    """绘制整屏浅灰渐变背景（保留兼容；主要界面改用 draw_menu_frame）。"""
    global _backdrop
    if _backdrop is None or _backdrop.get_size() != screen.get_size():
        _backdrop = _make_backdrop(*screen.get_size())
    screen.blit(_backdrop, (0, 0))
    if dim < 255:
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 255 - dim))
        screen.blit(overlay, (0, 0))


def draw_refresh_icon(screen, rect, color=ORANGE):
    """绘制橙色环形刷新箭头图标（圆形箭头 + 实心三角）。"""
    r = pygame.Rect(rect)
    box = r.inflate(-8, -8)
    if box.width < 4 or box.height < 4:
        return
    cx, cy = box.center
    radius = min(box.width, box.height) / 2
    width = max(2, min(5, radius // 3))
    # pygame.draw.arc 角度：0=右，顺时针（y 向下）。绘制 340° 的环，留一个缺口。
    start = math.radians(20)
    stop = math.radians(250)
    pygame.draw.arc(screen, color, box, start, stop, width)
    # 箭头：在 stop 端点沿顺时针切线方向画实心三角
    tip = (cx + radius * math.cos(stop), cy + radius * math.sin(stop))
    tangent = (-math.sin(stop), math.cos(stop))
    length = max(6, radius * 0.55)
    half = max(3, radius * 0.28)
    perp = (-tangent[1], tangent[0])
    apex = (tip[0] + tangent[0] * length, tip[1] + tangent[1] * length)
    p1 = (tip[0] + perp[0] * half, tip[1] + perp[1] * half)
    p2 = (tip[0] - perp[0] * half, tip[1] - perp[1] * half)
    pygame.draw.polygon(screen, color, [apex, p1, p2])


def draw_menu_frame(screen, title=None, subtitle=None, coins=None,
                    font_title=None, font_small=None, refresh=True,
                    refresh_rect=None):
    """绘制 SkyBlock 菜单外框：浅灰容器 + 黑外框 + 顶栏 + 橙色刷新图标。

    coins: 若为 int，则在右上角显示“金币”金色数字。
    返回标题栏下方的内容区 Rect。
    """
    w, h = screen.get_size()
    screen.fill(MENU_BG)
    pygame.draw.rect(screen, EDGE, (0, 0, w, h), 4)
    pygame.draw.rect(screen, EDGE_DARK, (3, 3, w - 6, h - 6), 1)

    header_h = 66
    if font_title and title:
        draw_text(screen, title, 26, 6, TIMBER, font_title)
    if subtitle and font_small:
        draw_text(screen, subtitle, 28, header_h - 20, MENU_MID, font_small)

    # 金币显示（右上角，刷新图标左侧）
    if coins is not None and font_small:
        coin_s = f"{coins:,}"
        draw_text(screen, coin_s, w - 120, 22, COIN_GOLD, font_small, align="right")
        # 金币小圆点
        pygame.draw.circle(screen, COIN_GOLD, (w - 104, 30), 8)
        pygame.draw.circle(screen, (180, 140, 0), (w - 104, 30), 8, 1)

    if refresh:
        rr = refresh_rect or pygame.Rect(w - 56, 8, 40, 40)
        draw_refresh_icon(screen, rr)

    # 顶栏与内容区的分隔线
    line_y = header_h + 10
    pygame.draw.line(screen, SLOT_DARK, (18, line_y), (w - 18, line_y), 3)
    pygame.draw.line(screen, SLOT_LIGHT, (18, line_y + 1), (w - 18, line_y + 1), 2)
    return pygame.Rect(18, line_y + 8, w - 36, h - line_y - 8)


def draw_container(screen, rect, fill=MENU_BG, bevel=3):
    """绘制 Minecraft 原版容器面板：黑外框 + 上/左白高光 + 下/右暗影 + 灰底。"""
    r = pygame.Rect(rect)
    pygame.draw.rect(screen, EDGE, r)
    pygame.draw.rect(screen, SLOT_LIGHT, (r.x, r.y, r.w, bevel))
    pygame.draw.rect(screen, SLOT_LIGHT, (r.x, r.y, bevel, r.h))
    pygame.draw.rect(screen, EDGE_DARK, (r.x, r.bottom - bevel, r.w, bevel))
    pygame.draw.rect(screen, EDGE_DARK, (r.right - bevel, r.y, bevel, r.h))
    inner = r.inflate(-2 * bevel, -2 * bevel)
    pygame.draw.rect(screen, fill, inner)


def draw_section(screen, rect, fill=PANEL_BG, bevel=3):
    """绘制有层次感的深灰分区板：垂直渐变 + 斜面高光 + 投影 + 噪点纹理。"""
    r = pygame.Rect(rect)
    if r.width < 4 or r.height < 4:
        return r
    # 投影（浮在浅灰背景上的柔和暗影）
    pygame.draw.rect(screen, (140, 140, 140), r.move(2, 3))
    pygame.draw.rect(screen, (100, 100, 100), r.move(3, 4))
    # 垂直渐变填充（上亮下暗）
    top = tuple(min(255, c + 16) for c in fill)
    bottom = tuple(max(0, c - 20) for c in fill)
    for y in range(r.height):
        t = y / max(1, r.height - 1)
        c = tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
        pygame.draw.line(screen, c, (r.x, r.y + y), (r.right, r.y + y))
    # 轻噪点（原版背景质感）
    rng = random.Random((r.x * 73856093) ^ (r.y * 19349663) ^ (r.w * 83492791))
    count = max(1, int(r.width * r.height * 0.002))
    for _ in range(count):
        x = r.x + 1 + rng.randrange(max(1, r.width - 2))
        y = r.y + 1 + rng.randrange(max(1, r.height - 2))
        v = rng.randrange(-5, 6)
        try:
            rr, gg, bb = screen.get_at((x, y))[:3]
            screen.set_at((x, y), (max(0, min(255, rr + v)),
                                   max(0, min(255, gg + v)),
                                   max(0, min(255, bb + v))))
        except Exception:
            pass
    # 内分线 + 斜面高光 + 黑边
    pygame.draw.rect(screen, (124, 124, 124), r.inflate(-2, -2), 1)
    pygame.draw.rect(screen, SLOT_LIGHT, (r.x, r.y, r.w, bevel))
    pygame.draw.rect(screen, SLOT_LIGHT, (r.x, r.y, bevel, r.h))
    pygame.draw.rect(screen, EDGE_DARK, (r.x, r.bottom - bevel, r.w, bevel))
    pygame.draw.rect(screen, EDGE_DARK, (r.right - bevel, r.y, bevel, r.h))
    pygame.draw.rect(screen, EDGE, r, 1)
    return r


def draw_slot(screen, rect, selected=False, hover=False, fill=SLOT_INNER, bevel=3):
    """绘制向内凹陷的物品槽位：上/左暗边 + 下/右实心白光。"""
    r = pygame.Rect(rect)
    if r.width < bevel * 2 or r.height < bevel * 2:
        bevel = max(1, min(r.width, r.height) // 4)
    pygame.draw.rect(screen, EDGE, r, 1)
    # 上、左暗边（阴影，近黑色以便在深灰分区上清晰可见）
    pygame.draw.rect(screen, (26, 26, 28), (r.x + 1, r.y + 1, r.w - 2, bevel))
    pygame.draw.rect(screen, (26, 26, 28), (r.x + 1, r.y + 1, bevel, r.h - 2))
    # 下、右实心白光（高光），模拟向内凹陷
    pygame.draw.rect(screen, SLOT_LIGHT, (r.x + 1, r.bottom - 1 - bevel, r.w - 2, bevel))
    pygame.draw.rect(screen, SLOT_LIGHT, (r.right - 1 - bevel, r.y + 1, bevel, r.h - 2))
    inner = r.inflate(-2 * bevel - 2, -2 * bevel - 2)
    if inner.width > 0 and inner.height > 0:
        pygame.draw.rect(screen, fill, inner)
    if selected:
        pygame.draw.rect(screen, SELECT_COLOR, r, 3)
    elif hover:
        pygame.draw.rect(screen, SLOT_LIGHT, r, 2)


def draw_button(screen, rect, text, font, enabled=True, selected=False,
                hover=False, text_color=(255, 255, 255)):
    """绘制 Minecraft 风格按钮（灰底 + 黑边 + 上下明暗）。"""
    r = pygame.Rect(rect)
    if not enabled:
        fill = (85, 85, 85)
        txt = (170, 170, 170)
        top = (110, 110, 110)
        bot = (50, 50, 50)
    else:
        fill = (106, 106, 106)
        txt = text_color
        top = (170, 170, 170)
        bot = (55, 55, 55)
    # 垂直渐变（上亮下暗，增加立体感）
    top_c = tuple(min(255, c + 22) for c in fill)
    bot_c = tuple(max(0, c - 18) for c in fill)
    for y in range(r.height):
        t = y / max(1, r.height - 1)
        c = tuple(int(top_c[i] + (bot_c[i] - top_c[i]) * t) for i in range(3))
        pygame.draw.line(screen, c, (r.x, r.y + y), (r.right, r.y + y))
    pygame.draw.rect(screen, top, pygame.Rect(r.x, r.y, r.w, 3))
    pygame.draw.rect(screen, bot, pygame.Rect(r.x, r.bottom - 3, r.w, 3))
    pygame.draw.rect(screen, EDGE, r, 1)
    if selected:
        pygame.draw.rect(screen, SELECT_COLOR, r, 3)
    elif hover and enabled:
        pygame.draw.rect(screen, SLOT_LIGHT, r, 2)
    surf = font.render(text, True, txt)
    screen.blit(surf, (r.x + (r.w - surf.get_width()) // 2,
                       r.y + (r.h - surf.get_height()) // 2))


def draw_text(screen, text, x, y, color, font, shadow=True, align="left"):
    """绘制带阴影的文本（Minecraft 风格），返回文本底边 y。"""
    surf = font.render(text, True, color)
    rect = surf.get_rect()
    rect.top = y
    if align == "center":
        rect.centerx = x
    elif align == "right":
        rect.right = x
    else:
        rect.left = x
    if shadow:
        sh = font.render(text, True, TEXT_SHADOW)
        screen.blit(sh, (rect.x + 1, rect.y + 1))
    screen.blit(surf, rect.topleft)
    return rect.bottom


def draw_tooltip_box(screen, rect):
    """绘制 Minecraft 风格暗色提示框（边框紫蓝渐变、内部暗底）。"""
    r = pygame.Rect(rect)
    pygame.draw.rect(screen, TOOLTIP_BORDER, r)
    pygame.draw.rect(screen, TOOLTIP_BORDER_DARK, r.inflate(-2, -2))
    pygame.draw.rect(screen, TOOLTIP_BG, r.inflate(-4, -4))


def draw_item_tooltip(screen, mouse_pos, lines, font_small, pad=6, line_h=19):
    """在鼠标旁绘制物品提示框。lines: [(text, color), ...]。"""
    if not lines:
        return
    max_w = max(font_small.size(text)[0] for text, _color in lines)
    box_w = max_w + pad * 2 + 6
    box_h = len(lines) * line_h + pad * 2
    x = mouse_pos[0] + 14
    y = mouse_pos[1] + 10
    w, h = screen.get_size()
    if x + box_w > w - 4:
        x = mouse_pos[0] - box_w - 14
    if y + box_h > h - 4:
        y = h - box_h - 4
    rect = pygame.Rect(x, y, box_w, box_h)
    draw_tooltip_box(screen, rect)
    ty = y + pad - 2
    for text, color in lines:
        ty = draw_text(screen, text, x + pad, ty, color, font_small, shadow=True) + 2


def draw_grid(origin, cols=GRID_COLS, rows=1, slot_size=SLOT_SIZE,
              gap=SLOT_GAP):
    """计算 cols x rows 槽位网格，返回每个槽位的 Rect 列表（行优先）。"""
    x0, y0 = origin
    rects = []
    for r in range(rows):
        for c in range(cols):
            rects.append(pygame.Rect(x0 + c * (slot_size + gap),
                                     y0 + r * (slot_size + gap),
                                     slot_size, slot_size))
    return rects


def draw_row_frame(screen, rect, selected=False, hover=False):
    """绘制列表行选中/悬停框架（浅灰主题：选中金框，悬停白框）。"""
    r = pygame.Rect(rect)
    if selected:
        pygame.draw.rect(screen, (232, 232, 200), r)
        pygame.draw.rect(screen, SELECT_COLOR, r, 3)
    elif hover:
        pygame.draw.rect(screen, (216, 216, 216), r)
        pygame.draw.rect(screen, SLOT_LIGHT, r, 2)
    else:
        # 默认给行一个细轮廓，避免深灰分区上的行显得没有边界
        pygame.draw.rect(screen, (100, 100, 100), r, 1)


def draw_count_badge(screen, rect, count, font_small):
    """在槽位右下角绘制堆叠数量（白色小字 + 阴影）。"""
    if count <= 1:
        return
    text = str(count)
    surf = font_small.render(text, True, SLOT_LIGHT)
    sh = font_small.render(text, True, TEXT_SHADOW)
    bx = rect.right - surf.get_width() - 4
    by = rect.bottom - surf.get_height() - 2
    screen.blit(sh, (bx + 1, by + 1))
    screen.blit(surf, (bx, by))


def rarity_bg(rarity):
    """根据稀有度返回 SkyBlock 徽标配色（供工具类背景使用）。"""
    return {
        "COMMON": (170, 170, 170),
        "UNCOMMON": (85, 255, 85),
        "RARE": (85, 85, 255),
        "EPIC": (170, 0, 170),
        "LEGENDARY": (255, 170, 0),
        "MYTHIC": (255, 85, 255),
        "DIVINE": (85, 255, 255),
        "SPECIAL": (255, 85, 85),
        "VERY_SPECIAL": (255, 85, 85),
    }.get(rarity, (170, 170, 170))
