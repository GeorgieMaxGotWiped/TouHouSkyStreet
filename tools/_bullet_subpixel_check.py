# -*- coding: utf-8 -*-
# 弹幕子像素位置检查：斜飞的弹还被吸在 1 逻辑像素的网格上吗
#
# 改前的画法在贴图之前把坐标 int() 成整数逻辑像素，再乘渲染倍率 —— 位置只能落在
# 1 逻辑像素 = 渲染倍率个物理像素的网格上；3x 下就是一帧停住、下一帧跳 3 个像素。
# 现在绘制保留浮点坐标、取整挪到图层空间（painter._dest_scaled）。
#
# 本脚本走真实绘制路径（Bullet.draw -> blit_gpu_over）取每帧登记给显卡的贴图坐标，
# 逐帧看步进：整帧位置都是渲染倍数的整数倍 = 仍被吸在逻辑网格上（FAIL）。
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import math
import pygame

pygame.init()
pygame.display.set_mode((960, 720))

from src.engine import painter, hires
from src.entities import bullet as bmod

FRAMES = 14
ANGLE_DEG = 10.0     # 浅角度最能看出纵向台阶
SPEED = 3.0          # 逻辑像素/帧


def collect(scale, angle_deg=ANGLE_DEG, speed=SPEED, frames=FRAMES):
    """返回 (改后位置, 改前位置, 理想位置)，单位都是图层像素（含贴图中心）"""
    hires.set_scale(scale)
    canvas = painter.Painter.create((960, 720))
    canvas.set_hires_factor(scale)
    canvas.begin_gpu_frame(scale, True)
    if not canvas.gpu.enabled:
        return None
    b = bmod.create_bullet_angle(100.0, 200.0, math.radians(angle_deg), speed,
                                 bmod.Bullet.TYPE_RICE)
    sprite = b._get_atlas_sprite(scale)
    if sprite is None:
        return None
    half_w = sprite.get_width() * scale / 2.0
    half_h = sprite.get_height() * scale / 2.0
    now, before, ideal = [], [], []
    for _ in range(frames):
        canvas.gpu.begin(scale, True)
        b.draw(canvas)
        op = canvas.gpu.ops_over[-1][2]
        now.append((op[0] + half_w, op[1] + half_h))
        # 改前写法：先在逻辑坐标取整，再乘倍率
        before.append(((int(b.x) * scale) + half_w, (int(b.y) * scale) + half_h))
        ideal.append((b.x * scale + half_w, b.y * scale + half_h))
        b.update(1.0)
    return now, before, ideal


def steps(pts):
    return [(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1])
            for i in range(len(pts) - 1)]


def max_error(st, ideal):
    st_ideal = steps(ideal)
    return max(max(abs(a[0] - b[0]), abs(a[1] - b[1]))
               for a, b in zip(st, st_ideal))


def main():
    scale = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    got = collect(scale)
    if got is None:
        print(f"FAIL: 取不到贴图或显卡指令层没开（scale={scale}）")
        return 1
    now, before, ideal = got
    on_grid = all(x % scale == 0 and y % scale == 0 for x, y in now)
    before_grid = all(x % scale == 0 and y % scale == 0 for x, y in before)
    err_now, err_before = max_error(steps(now), ideal), max_error(steps(before), ideal)
    print(f"渲染倍率 {scale}x，速度 {SPEED} 逻辑像素/帧、{ANGLE_DEG} 度，"
          f"理想步进 = {ideal[1][0] - ideal[0][0]:.2f} / {ideal[1][1] - ideal[0][1]:.2f} 图层像素")
    print("改前每帧步进:", [(round(dx), round(dy)) for dx, dy in steps(before)][:8], "...")
    print("改后每帧步进:", [(round(dx), round(dy)) for dx, dy in steps(now)][:8], "...")
    print(f"改前位置全落在 {scale} 的倍数上（被吸在逻辑网格）: {before_grid}")
    print(f"改后位置全落在 {scale} 的倍数上: {on_grid}（应为 False）")
    print(f"最大步进误差：改前 {err_before:.2f} -> 改后 {err_now:.2f} 图层像素")
    ok = (before_grid and not on_grid and err_now <= 1.0 and err_before > 1.0)
    pygame.quit()
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
