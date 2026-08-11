# 碰撞检测模块

import math

def circle_collision(x1, y1, r1, x2, y2, r2):
    """圆形碰撞检测"""
    dx = x1 - x2
    dy = y1 - y2
    dist = math.sqrt(dx * dx + dy * dy)
    return dist < (r1 + r2)


def point_segment_distance(px, py, x1, y1, x2, y2):
    """点到线段的最短距离（电网光束整条判定的基础）"""
    dx = x2 - x1
    dy = y2 - y1
    length_sq = dx * dx + dy * dy
    if length_sq <= 1e-9:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / length_sq))
    cx = x1 + t * dx
    cy = y1 + t * dy
    return math.hypot(px - cx, py - cy)


def circle_ellipse_collision(cx, cy, cr, ex, ey, rx, ry):
    """圆形 vs 轴对齐椭圆碰撞（圆半径相对椭圆较小时足够精确）"""
    def inside(px, py):
        dx = (px - ex) / rx
        dy = (py - ey) / ry
        return dx * dx + dy * dy <= 1.0
    if inside(cx, cy):
        return True
    for i in range(16):
        ang = i * math.pi * 2 / 16
        if inside(cx + math.cos(ang) * cr, cy + math.sin(ang) * cr):
            return True
    return False

def point_in_rect(px, py, rx, ry, rw, rh):
    """点是否在矩形内"""
    return rx <= px <= rx + rw and ry <= py <= ry + rh

def rect_collision(x1, y1, w1, h1, x2, y2, w2, h2):
    """矩形碰撞检测"""
    return (x1 < x2 + w2 and x1 + w1 > x2 and
            y1 < y2 + h2 and y1 + h1 > y2)
