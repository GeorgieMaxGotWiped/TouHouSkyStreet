# -*- coding: utf-8 -*-
# 伪3D圆柱投影全景（bg1.png）预览：输出旋转 GIF（投影展示 + 真实转速） + PNG + 打印性能。
# 验证：射线-圆柱求交投影、无缝循环、环绕速度、垂直真实投影、边缘放大倍数。
import os
import sys
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
import pygame
import numpy as np
from PIL import Image

sys.path.insert(0, os.getcwd())
from src.engine.panorama3d import CylinderPanorama, DEFAULT_FOV
from src.engine.spell_bg import SpellBackground, AREA_W, AREA_H

OUT = r"C:/Users/admin/.codex/visualizations/2026/08/12/019ff64c-eedd-7723-a592-58d6beff830f"
TEX = r"assets/backgrounds/stage3/bg1.png"
FLOOR_TEX = r"assets/backgrounds/stage3/bossfloor1.png"


def save_gif(pan, tag, yaw_step, duration, n=30, full_loop=False):
    frames = []
    step = yaw_step
    for i in range(n):
        yaw = (i * step) % 360.0 if full_loop else i * step
        pan.yaw = float(yaw)
        pan.draw(screen)
        frames.append(Image.fromarray(pygame.surfarray.array3d(screen).swapaxes(0, 1)).convert("RGB"))
    frames[0].save("%s/%s.gif" % (OUT, tag), save_all=True,
                   append_images=frames[1:], duration=duration, loop=0)
    print("saved %s.gif (%d frames, %.1f deg total)" % (tag, n, (n - 1) * step))


def main():
    pygame.init()
    global screen
    screen = pygame.display.set_mode((AREA_W, AREA_H))

    # 1) 真正的圆柱投影（射线求交，默认）——投影展示（快速旋转便于看透视）
    pan = CylinderPanorama(TEX, AREA_W, AREA_H, fov=DEFAULT_FOV, speed=28.0,
                            projection="cylinder", floor_texture_path=FLOOR_TEX)
    print("floor: y0=%d h=%d (junction v=%.3f)" % (pan.floor_y0, pan.floor_h, pan.floor_y0 / AREA_H))
    pan.yaw = 0.0
    pan.draw(screen)
    a0 = pygame.surfarray.array3d(screen).copy()
    pygame.image.save(screen, "%s/cylinder_yaw0.png" % OUT)
    pan.yaw = 360.0
    pan.draw(screen)
    print("cylinder loop seamless:", bool((a0 == pygame.surfarray.array3d(screen)).all()))
    d = np.abs(np.diff(pan._col_base))
    cx_i = AREA_W // 2
    mag = d[cx_i - 5:cx_i + 5].mean() / d[:8].mean()
    print("fov: %.0f  edge magnification vs center: %.2fx" % (pan.fov, mag))
    save_gif(pan, "cylinder_spin", 12.0, 50, full_loop=True)

    # 2) 真实转速取景（按游戏内速度推进）
    save_gif(pan, "cylinder_realspeed", pan.speed * 0.15, 150)
    print("cylinder real-speed pacing: %.2f deg/s" % pan.speed)

    # 3) 外贴圆柱（arcsin，边缘压缩）作为对比
    pan2 = CylinderPanorama(TEX, AREA_W, AREA_H, fov=DEFAULT_FOV, speed=28.0, projection="banner")
    save_gif(pan2, "banner_spin", 12.0, 50, full_loop=True)

    # 4) Bonzo 球符完整符卡背景
    bg = SpellBackground("球符「Balloon Barrage」", "bonzo")
    for i in range(30):
        bg.update(1 / 60.0)
    t0 = time.perf_counter()
    N = 120
    for i in range(N):
        bg.update(1 / 60.0)
        bg.draw(screen)
    dt = (time.perf_counter() - t0) / N * 1000.0
    bg.draw(screen)
    pygame.image.save(screen, "%s/spellbg_bonzo.png" % OUT)
    pan0 = bg.panoramas[0]
    print("bonzo panorama speed: %.1f deg/s, fov: %.1f, projection: %s" % (pan0.speed, pan0.fov, pan0.projection))
    print("spellbg draw+update: %.2f ms/frame" % dt)
    pygame.quit()
    print("ALL OK -> %s" % OUT)


if __name__ == "__main__":
    main()
