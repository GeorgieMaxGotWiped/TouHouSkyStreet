# -*- coding: utf-8 -*-
# 临时脚本：六面「正弦移动小怪」的移动速度差分（现状 vs 改成竖直下落）
import os, sys, math
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.engine import settings as cfg
from src.stages import stage6 as s6

OUT = r"C:\Users\admin\.codex\visualizations\2026\09\25\01a0d626-88d7-7b43-be2a-ef20c066fb95"
pygame.init()
screen = pygame.display.set_mode((960, 720))
F = "Microsoft YaHei,SimHei,Arial"
f_head = pygame.font.SysFont(F, 15)
f_line = pygame.font.SysFont(F, 14)
f_small = pygame.font.SysFont(F, 12)

W, H = float(cfg.BATTLE_AREA_WIDTH), float(cfg.BATTLE_AREA_HEIGHT)
LIMIT = H + 50          # 基类退场阈值：y > H+50
Y0 = -24.0

CASES = [
    ("Wither Husk  凋零游魂", lambda: s6.WitherHuskEnemy(288, Y0), 1.5, 2.2, "strafe"),
    ("Wither Miner 凋零矿工", lambda: s6.WitherMinerEnemy(288, Y0), 0.8, 2.2, "strafe"),
    ("Wither Knight 凋零骑士", lambda: s6.WitherKnightEnemy(288, Y0), 0.9, 2.4, "strafe"),
    ("Wither Wisp 黑能量游魂", lambda: s6.WitherWispEnemy(288, Y0), 0.9, 2.6, "sin"),
]


def simulate(enemy, vertical=False, max_frames=1400):
    """按真实移动规则步进，返回逐帧 (x, y)；vertical=True 时改成竖直下落。"""
    enemy.x, enemy.y = 288.0, Y0
    enemy.age = 0
    path = [(enemy.x, enemy.y)]
    for _ in range(max_frames):
        enemy.age += 1
        if vertical:
            enemy.y += enemy.move_speed
        else:
            enemy._move()
        path.append((enemy.x, enemy.y))
        if enemy.x < -50 or enemy.x > W + 50 or enemy.y > LIMIT:
            break
    return path


rows = []
for label, factory, speed, amp, pattern in CASES:
    e = factory()
    e.entry_done = True
    cur = simulate(e, vertical=False)
    new = simulate(e, vertical=True)
    cur_v = e.move_speed if pattern == "sin" else e.move_speed
    period = (2 * math.pi / (0.04 if pattern == "strafe" else 0.03))
    rows.append(dict(
        label=label, pattern=pattern, v_down=(0.0 if pattern == "sin" else e.move_speed),
        amp=(amp if pattern != "sin" else e.move_speed), wobble_amp=amp, period=period,
        v_peak=math.hypot(0.9 if pattern == "sin" else e.move_speed, amp),
        drift=(e.vx if pattern == "sin" else 0.0),
        cur_frames=len(cur) - 1, new_frames=len(new) - 1,
        cur_xspan=max(p[0] for p in cur) - min(p[0] for p in cur),
        cur_exit="出屏" if (cur[-1][0] < -50 or cur[-1][0] > W + 50) else "下缘",
        new_exit="下缘", cur=cur, new=new))

print("%-24s %-7s %8s %8s %8s %9s %10s %10s" % (
    "小怪", "模式", "净竖速", "摆动幅", "周期(帧)", "合成峰值", "现状在场", "改后在场"))
for r in rows:
    print("%-24s %-7s %8.2f %8.2f %8.1f %9.2f %9.1fs %9.1fs" % (
        r["label"], r["pattern"], r["v_down"], r["wobble_amp"], r["period"], r["v_peak"],
        r["cur_frames"] / 60.0, r["new_frames"] / 60.0))
print("横向漂移（Wisp 专用 vx）：%s" % ", ".join(
    "%.2f" % r["drift"] for r in rows if r["pattern"] == "sin"))

# ---------------------------------------------------------------- 轨迹图
panels = rows
pw, ph = 300, 350
pad = 10
cols = 4
label_h = 46
head = 44
sheet = pygame.Surface((pad + cols * (pw + pad), head + pad + label_h + ph + pad + 150))
sheet.fill((16, 17, 21))
for i, line in enumerate([
        "六面「正弦移动小怪」速度差分：现状（蓝，正弦）vs 改成竖直向下（绿）",
        "场地 576x670；竖线=场地左右边界与中线，虚线=下缘退场线（y=720）"]):
    sheet.blit(f_head.render(line, True, (232, 234, 240)), (pad, 6 + i * 19))
for i, r in enumerate(panels):
    x = pad + i * (pw + pad)
    y = head + pad
    cell = pygame.Surface((pw, label_h + ph))
    cell.fill((26, 28, 34))
    pygame.draw.rect(cell, (74, 78, 92), cell.get_rect(), 1)
    cell.blit(f_line.render(r["label"], True, (245, 226, 160)), (6, 4))
    cell.blit(f_small.render("模式 %s　净竖速 %.2f/帧　正弦幅 %.2f" % (
        r["pattern"], r["v_down"], r["wobble_amp"]), True, (200, 208, 220)), (6, 22))
    cell.blit(f_small.render("合成峰值 %.2f/帧　周期 %.1f 帧" % (
        r["v_peak"], r["period"]), True, (188, 196, 210)), (6, 36))
    area = pygame.Rect(6, label_h, pw - 12, ph - label_h - 42)
    pygame.draw.rect(cell, (18, 20, 26), area)
    pygame.draw.rect(cell, (56, 60, 72), area, 1)
    for gx in (0, W / 2, W):
        px = area.x + gx / W * area.w
        pygame.draw.line(cell, (46, 50, 60), (px, area.y), (px, area.bottom))
    pygame.draw.line(cell, (120, 60, 60), (area.x, area.y),
                     (area.x, area.y), 1)
    ey = area.y + LIMIT / (LIMIT + 40) * area.h
    pygame.draw.line(cell, (120, 60, 60), (area.x, ey), (area.right, ey), 1)
    cell.blit(f_small.render("y=720 退场线", True, (150, 90, 90)), (area.x + 3, ey - 14))

    def to_px(p):
        return (area.x + p[0] / W * area.w, area.y + (p[1] + 40) / (LIMIT + 40) * area.h)

    pygame.draw.lines(cell, (110, 160, 230), False,
                      [to_px(p) for p in r["cur"][::3]], 2)
    pygame.draw.lines(cell, (120, 220, 140), False,
                      [to_px(p) for p in r["new"][::3]], 2)
    for path, col in ((r["cur"], (110, 160, 230)), (r["new"], (120, 220, 140))):
        px, py = to_px(path[-1])
        pygame.draw.circle(cell, col, (int(px), int(py)), 3)
    cell.blit(f_small.render("蓝：现状 %.1fs（%s）" % (
        r["cur_frames"] / 60.0, r["cur_exit"]), True, (150, 190, 240)),
        (6, label_h + ph - 34))
    cell.blit(f_small.render("绿：竖直下落 %.1fs（下缘）　横移 %.0fpx" % (
        r["new_frames"] / 60.0, r["cur_xspan"]), True, (150, 230, 170)),
        (6, label_h + ph - 18))
    sheet.blit(cell, (x, y))

# 汇总表
ty = head + pad + label_h + ph + pad + 6
sheet.blit(f_line.render("汇总（速度单位 px/帧 @60FPS；在场=从 y=-24 入场到离场）",
                         True, (232, 234, 240)), (pad, ty))
ty += 22
heads = ["小怪", "竖直净速度", "横向摆动", "摆动周期", "合成峰值速度", "现状在场时间", "竖直下落后在场时间"]
colx = [pad + 4, pad + 150, pad + 260, pad + 370, pad + 480, pad + 610, pad + 750]
for cx, h in zip(colx, heads):
    sheet.blit(f_small.render(h, True, (200, 206, 218)), (cx, ty))
ty += 18
for r in rows:
    vals = [r["label"],
            ("%.2f ↓" % r["v_down"]) if r["v_down"] > 0 else "0（纯上下摆动）",
            "±%.2f" % r["wobble_amp"],
            "%.0f 帧（%.2fs）" % (r["period"], r["period"] / 60.0),
            "%.2f" % r["v_peak"],
            "%.1fs" % (r["cur_frames"] / 60.0),
            "%.1fs" % (r["new_frames"] / 60.0)]
    for cx, v in zip(colx, vals):
        sheet.blit(f_small.render(v, True, (222, 226, 234)), (cx, ty))
    ty += 17

REF = [("（参考）Golem / Colossus 停驻微摆", "0（停驻）", "±0.35", "524 帧（8.7s）", "0.35", "停驻不退场", "—"),
       ("（参考）黑能量游魂（环境）", "1.05 ↓", "±1.30", "179 帧（3.0s）", "1.66", "下缘", "1.05")]
for label, a, b, c, d, e, f in REF:
    for cx, v in zip(colx, [label, a, b, c, d, e, f]):
        sheet.blit(f_small.render(v, True, (170, 176, 190)), (cx, ty))
    ty += 17
out = os.path.join(OUT, "s6_sine_motion_diff.png")
pygame.image.save(sheet, out)
print("saved", out, sheet.get_size())
print("RENDER_OK")
