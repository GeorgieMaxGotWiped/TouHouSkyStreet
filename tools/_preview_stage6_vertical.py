# -*- coding: utf-8 -*-
# 临时脚本：六面行军小怪「正弦 → 竖直下落」对比（轨迹差分 + 实机帧）
import os, sys, math
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager
from src.stages import stage6 as s6

OUT = r"C:\Users\admin\.codex\visualizations\2026\09\25\01a0d626-88d7-7b43-be2a-ef20c066fb95"
pygame.init()
screen = pygame.display.set_mode((960, 720))
F = "Microsoft YaHei,SimHei,Arial"
f_head = pygame.font.SysFont(F, 15)
f_line = pygame.font.SysFont(F, 14)
f_small = pygame.font.SysFont(F, 12)

W, H = float(cfg.BATTLE_AREA_WIDTH), float(cfg.BATTLE_AREA_HEIGHT)
LIMIT = H + 50
Y0 = -24.0

# (标签, 构造器, 旧参数：下落速度/正弦幅, 正弦频率)
CASES = [
    ("Wither Husk  凋零游魂", lambda: s6.WitherHuskEnemy(288, Y0), 1.5, 2.2, 0.04),
    ("Wither Miner 凋零矿工", lambda: s6.WitherMinerEnemy(288, Y0), 0.8, 2.2, 0.04),
    ("Wither Knight 凋零骑士", lambda: s6.WitherKnightEnemy(288, Y0), 0.9, 2.4, 0.04),
]


def walk(enemy, mode):
    """mode: 'now' 用当前代码；'old' 复现改前的正弦横摆。"""
    enemy.x, enemy.y, enemy.age = 288.0, Y0, 0
    path = [(enemy.x, enemy.y)]
    for _ in range(1400):
        enemy.age += 1
        if mode == "old":
            enemy.y += enemy.move_speed
            enemy.x += math.sin(enemy.age * freq) * amp
        else:
            enemy._move()
        path.append((enemy.x, enemy.y))
        if enemy.x < -50 or enemy.x > W + 50 or enemy.y > LIMIT:
            break
    return path


rows = []
for label, factory, speed, amp, freq in CASES:
    e = factory()
    e.entry_done = True
    now = walk(e, "now")
    old = walk(e, "old")
    xs = [p[0] for p in now]
    rows.append(dict(label=label, speed=speed, amp=amp, old=old, now=now,
                     xspan=max(xs) - min(xs),
                     frames=len(now) - 1, exit_kind=("下缘" if now[-1][1] > LIMIT else "侧向")))
    print("%-24s 竖速 %.2f/帧（%.0f px/s）  改后横向位移 %.3fpx  在场 %.1fs（%s）" % (
        label, speed, speed * 60, max(xs) - min(xs), (len(now) - 1) / 60.0, rows[-1]["exit_kind"]))

# ---------------------------------------------------------------- 轨迹差分
pw, ph, pad = 300, 300, 10
pcy = 44
pch = 52
sheet = pygame.Surface((pad + 3 * (pw + pad), pcy + pad + pch + ph + pad))
sheet.fill((16, 17, 21))
for i, line in enumerate([
        "六面行军小怪：正弦横摆（红）→ 竖直下落（青，已实装）",
        "场地 576x670，中线为竖直下落轨迹；两者净下落速度相同"]):
    sheet.blit(f_head.render(line, True, (232, 234, 240)), (pad, 6 + i * 19))
for i, r in enumerate(rows):
    x = pad + i * (pw + pad)
    cell = pygame.Surface((pw, pch + ph))
    cell.fill((26, 28, 34))
    pygame.draw.rect(cell, (74, 78, 92), cell.get_rect(), 1)
    cell.blit(f_line.render(r["label"], True, (245, 226, 160)), (6, 4))
    cell.blit(f_small.render("下落 %.2f px/帧（%.0f px/s）　旧正弦幅 ±%.2f（周期 2.62s）" % (
        r["speed"], r["speed"] * 60, r["amp"]), True, (200, 208, 220)), (6, 24))
    cell.blit(f_small.render("改后横向位移 %.2f px　在场 %.1fs（%s离场）" % (
        r["xspan"], r["frames"] / 60.0, r["exit_kind"]), True, (188, 196, 210)), (6, 38))
    area = pygame.Rect(6, pch, pw - 12, ph - 12)
    pygame.draw.rect(cell, (18, 20, 26), area)
    pygame.draw.rect(cell, (56, 60, 72), area, 1)
    for gx in (0, W / 2, W):
        px = area.x + gx / W * area.w
        pygame.draw.line(cell, (46, 50, 60), (px, area.y), (px, area.bottom))
    ey = area.y + LIMIT / (LIMIT + 40) * area.h
    pygame.draw.line(cell, (120, 60, 60), (area.x, ey), (area.right, ey), 1)
    cell.blit(f_small.render("y=720", True, (150, 90, 90)), (area.x + 3, ey - 14))

    def to_px(p):
        return (area.x + p[0] / W * area.w, area.y + (p[1] + 40) / (LIMIT + 40) * area.h)

    pygame.draw.lines(cell, (215, 120, 120), False, [to_px(p) for p in r["old"][::3]], 2)
    pygame.draw.lines(cell, (110, 220, 230), False, [to_px(p) for p in r["now"][::3]], 2)
    sheet.blit(cell, (x, pcy + pad))

tr_out = os.path.join(OUT, "s6_vertical_motion.png")
pygame.image.save(sheet, tr_out)
print("saved", tr_out, sheet.get_size())

# ---------------------------------------------------------------- 实机帧
MARKS = [("9.0s  Undead Line", 9 * 60 + 40), ("14.0s  Miner Phalanx", 14 * 60 + 40),
         ("29.0s  Guard Wall", 29 * 60 + 40), ("82.0s  Knight Order", 82 * 60 + 40),
         ("90.0s  Golem Ward", 90 * 60 + 40), ("45.0s  游魂（Wisp 不变，仍正弦）", 45 * 60 + 60)]
stage = s6.Stage6_FinalApproach()
stage.setup_waves()
bm = BulletManager()
want = {t for _, t in MARKS}
frames, info = {}, {}
while stage.timer <= max(want):
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
    bm.update(1.0 / 60.0, 288.0, 560.0)
    if stage.timer in want:
        screen.fill((0, 0, 0))
        stage.draw(screen, 0, 0)
        bm.draw(screen, 0, 0)
        stage.draw_foreground(screen, 0, 0)
        frames[stage.timer] = screen.subsurface(pygame.Rect(
            0, 0, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT)).copy()
        live = [e for e in stage.enemy_manager.get_active_enemies() if e.alive]
        kinds = {}
        for e in live:
            kinds[type(e).__name__.replace("Enemy", "")] = kinds.get(
                type(e).__name__.replace("Enemy", ""), 0) + 1
        info[stage.timer] = "　".join("%s×%d" % kv for kv in sorted(kinds.items()))

tw, th, ipad, label_h, cols = 316, 368, 8, 40, 3
rows_n = (len(MARKS) + cols - 1) // cols
sheet2 = pygame.Surface(((tw + ipad) * cols + ipad, (label_h + th + ipad) * rows_n + ipad))
sheet2.fill((26, 28, 34))
for i, (title, t) in enumerate(MARKS):
    r, c = divmod(i, cols)
    x = ipad + c * (tw + ipad)
    y = ipad + r * (label_h + th + ipad)
    short = (info[t].replace("Wither", "").replace("SkeletonLord", "Lord")
             .replace("Terracotta", "Golem"))
    sheet2.blit(f_line.render(title.replace("  ", " "), True, (240, 240, 246)), (x, y + 2))
    sheet2.blit(f_small.render("在场：" + short, True, (176, 200, 228)), (x, y + 21))
    sheet2.blit(pygame.transform.smoothscale(frames[t], (tw, th)), (x, y + label_h))
    print("  %-34s %s" % (title, info[t]))
ig_out = os.path.join(OUT, "s6_vertical_ingame.png")
pygame.image.save(sheet2, ig_out)
print("saved", ig_out, sheet2.get_size())
print("RENDER_OK")
