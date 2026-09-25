# -*- coding: utf-8 -*-
# 临时脚本：六面道中小怪资料（图鉴 / 出场时间轴 / 实机波次截图）
# 产出 - s6_zako_roster.png / s6_zako_waves.png / s6_zako_ingame.png
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager
from src.stages import stage6 as s6

OUT = r"C:\Users\admin\.codex\visualizations\2026\09\25\01a0d626-88d7-7b43-be2a-ef20c066fb95"
F = "Microsoft YaHei,SimHei,Arial"
pygame.init()
screen = pygame.display.set_mode((960, 720))
f_head = pygame.font.SysFont(F, 15)
f_name = pygame.font.SysFont(F, 20)
f_line = pygame.font.SysFont(F, 15)
f_small = pygame.font.SysFont(F, 13)

ROSTER = [
    (s6.WitherHuskEnemy, "Wither Husk  凋零游魂",
     "横移 1.5（振幅 2.2）", "每 96 帧：1 发自机狙圆弹 2.6"),
    (s6.WitherGuardEnemy, "Wither Guard 凋零守卫",
     "缓降 0.7", "每 100 帧奇偶交替：3 发米弹扇 2.5 / 14 发旋转圆环 1.6"),
    (s6.WitherMinerEnemy, "Wither Miner 凋零矿工",
     "横移 0.8（振幅 2.2）", "每 105 帧：5 发米弹扇 2.2，每 2 轮补 1 发缓速大玉 1.1"),
    (s6.WitherKnightEnemy, "Wither Knight 凋零骑士",
     "横移 0.9（振幅 2.4）", "每 110 帧：5 发刀弹扇 2.6，每 3 轮补 12 发旋转圆环 1.5"),
    (s6.WitherTerracottaEnemy, "Wither Golem 兵马俑守卫",
     "降到 y=150 停驻，之后左右微摆", "每 115 帧奇偶交替：1 发自机狙圆弹 3.0 / 16 发旋转米弹环 1.6"),
    (s6.WitherColossusEnemy, "Wither Colossus 巨像",
     "降到 y=150 停驻，之后左右微摆", "每 72 帧奇偶交替：1 大玉 1.9 + 8 发米弹 1.2 / 16 发圆环 1.5"),
    (s6.WitherWispEnemy, "Wither Wisp 黑能量游魂",
     "正弦飘落 0.9（振幅 2.6）", "每 150 帧：1 发自机狙圆弹 2.1"),
]
ORDER = [r[0] for r in ROSTER]
COLORS = [(180, 110, 150), (205, 180, 90), (110, 178, 146), (152, 178, 96),
          (192, 136, 92), (152, 102, 202), (124, 74, 164)]
MARKS = [("4.0s  Wither Vanguard", 4 * 60), ("29.0s  Guard Wall", 29 * 60),
         ("47.0s  Kaeman 干涉 / 游魂", 47 * 60), ("82.0s  Knight Order", 82 * 60),
         ("90.0s  Golem Ward", 90 * 60), ("101.0s  Final Defense", 101 * 60)]


def wrap(font_obj, text, max_w):
    out, cur = [], ""
    for chx in text:
        if font_obj.size(cur + chx)[0] > max_w and cur:
            out.append(cur)
            cur = chx
        else:
            cur += chx
    if cur:
        out.append(cur)
    return out


def header(sheet, text, pad):
    for i, line in enumerate(wrap(f_head, text, sheet.get_width() - 2 * pad)):
        sheet.blit(f_head.render(line, True, (232, 234, 240)), (pad, 8 + i * 20))


def draw_enemy(enemy, box_w, box_h):
    surf = pygame.Surface((box_w, box_h))
    surf.fill((20, 22, 28))
    for gx in range(0, box_w, 16):
        pygame.draw.line(surf, (26, 28, 36), (gx, 0), (gx, box_h))
    enemy.x, enemy.y = box_w / 2, box_h / 2
    enemy.age = 20
    enemy.draw(surf, 0, 0)
    pygame.draw.rect(surf, (62, 66, 78), surf.get_rect(), 1)
    return surf


def roster_sheet():
    cw, ch, pad, cols, head = 400, 176, 10, 2, 54
    rows = (len(ROSTER) + cols - 1) // cols
    sheet = pygame.Surface((pad + cols * (cw + pad), head + pad + rows * (ch + pad)))
    sheet.fill((16, 17, 21))
    header(sheet, "六面道中 小怪图鉴   Stage 6 / Final Approach（道中小怪 7 种，无道中 Boss）  "
                  "黑色 Wither 能量持续入侵：游魂 + 侵入波，压迫感来自「被注视」", pad)
    for idx, (cls, title, move, shot) in enumerate(ROSTER):
        r, c = divmod(idx, cols)
        x, y = pad + c * (cw + pad), head + pad + r * (ch + pad)
        cell = pygame.Surface((cw, ch))
        cell.fill((26, 28, 34))
        pygame.draw.rect(cell, (74, 78, 92), cell.get_rect(), 1)
        e = cls(0, 0, deploy_y=150) if issubclass(cls, s6._DeployEnemy) else cls(0, 0)
        e.entry_done = True
        cell.blit(draw_enemy(e, 140, ch - 16), (8, 8))
        lines = [(f_name, title, (245, 226, 160)),
                 (f_line, "HP %d     分数 %d" % (e.hp, e.score), (208, 216, 228)),
                 (f_line, "判定半径 %.0f     立绘高 %.0f" % (e.size, e.sprite_height), (172, 180, 194)),
                 (f_small, "移动：" + move, (168, 196, 230)),
                 (f_small, "射击：" + shot, (204, 172, 204))]
        ty = 10
        for font_obj, text, color in lines:
            for chunk in wrap(font_obj, text, cw - 166):
                cell.blit(font_obj.render(chunk, True, color), (156, ty))
                ty += font_obj.get_linesize() - 2
            ty += 4
        sheet.blit(cell, (x, y))
    out = os.path.join(OUT, "s6_zako_roster.png")
    pygame.image.save(sheet, out)
    print("saved", out, sheet.get_size())


def gather_waves():
    stage = s6.Stage6_FinalApproach()
    stage.setup_waves()
    return sorted(stage.enemy_manager.timed_waves, key=lambda tw: tw[0])


def wave_sheet():
    waves = gather_waves()
    cw, ch, pad, cols, head = 232, 210, 8, 4, 52
    rows = (len(waves) + cols - 1) // cols
    sheet = pygame.Surface((pad + cols * (cw + pad), head + pad + rows * (ch + pad)))
    sheet.fill((16, 17, 21))
    header(sheet, "六面道中 出场时间轴（共 15 波，60FPS）　行军 4~34s → Kaeman 干涉 42~66s（只留游魂）"
                  "→ 要塞 68~90s → 王座前最后防线 100s，突破后直接进入 Kaeman 战", pad)
    for idx, (t, wave) in enumerate(waves):
        r, c = divmod(idx, cols)
        x, y = pad + c * (cw + pad), head + pad + r * (ch + pad)
        cell = pygame.Surface((cw, ch))
        cell.fill((26, 28, 34))
        pygame.draw.rect(cell, (74, 78, 92), cell.get_rect(), 1)
        cell.blit(f_line.render("%5.1fs  %s" % (t / 60.0, wave.name), True, (245, 226, 160)), (8, 6))
        area = pygame.Rect(8, 28, cw - 16, 120)
        pygame.draw.rect(cell, (19, 21, 27), area)
        pygame.draw.rect(cell, (56, 60, 72), area, 1)
        cell.blit(f_small.render("战斗区（俯视）", True, (92, 96, 108)), (area.x + 4, area.y + 2))
        cell.blit(f_small.render("编队：横向=出生 X", True, (104, 108, 120)), (area.x + 4, area.bottom - 32))
        cell.blit(f_small.render("纵向=出生高度 -95~-20", True, (104, 108, 120)), (area.x + 4, area.bottom - 16))
        groups = {}
        for e in wave.enemies:
            g = groups.setdefault((e.x, e.y), [0, (150, 150, 160)])
            g[0] += 1
            for oi, oc in enumerate(ORDER):
                if isinstance(e, oc):
                    g[1] = COLORS[oi]
                    break
        for (ex, ey), (n, col) in sorted(groups.items(), key=lambda kv: kv[0][1]):
            px = area.x + ex / float(cfg.BATTLE_AREA_WIDTH) * area.w
            py = area.y + 46 + (ey + 95) / 75.0 * 34
            pygame.draw.circle(cell, col, (int(px), int(py)), 6)
            pygame.draw.circle(cell, (238, 238, 244), (int(px), int(py)), 6, 1)
            if n > 1:
                cell.blit(f_small.render("x%d" % n, True, (238, 238, 244)), (int(px) + 8, int(py) - 7))
        items = {}
        for e in wave.enemies:
            for oi, oc in enumerate(ORDER):
                if isinstance(e, oc):
                    items[oi] = items.get(oi, 0) + 1
                    break
        ty = 154
        for oi in sorted(items):
            cell.blit(f_small.render("· %s ×%d" % (ORDER[oi].__name__.replace("Enemy", ""), items[oi]),
                                     True, COLORS[oi]), (10, ty))
            ty += 17
        sheet.blit(cell, (x, y))
    out = os.path.join(OUT, "s6_zako_waves.png")
    pygame.image.save(sheet, out)
    print("saved", out, sheet.get_size())


def ingame_sheet():
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
            alive = [e for e in stage.enemy_manager.active_enemies if e.alive]
            info[stage.timer] = ("在场敌机 %d　敌弹 %d" % (len(alive), len(bm.enemy_bullets)),
                                 "+".join(sorted({type(e).__name__.replace("Enemy", "")
                                                  for e in alive})) or "无")
    tw, th, pad, label_h, cols = 316, 368, 8, 40, 3
    rows = (len(MARKS) + cols - 1) // cols
    sheet = pygame.Surface(((tw + pad) * cols + pad, (label_h + th + pad) * rows + pad))
    sheet.fill((26, 28, 34))
    for i, (title, t) in enumerate(MARKS):
        r, c = divmod(i, cols)
        x, y = pad + c * (tw + pad), pad + r * (label_h + th + pad)
        l1, l2 = info[t]
        sheet.blit(f_line.render("%s　%s" % (title, l1), True, (240, 240, 246)), (x, y + 2))
        sheet.blit(f_small.render(l2, True, (176, 200, 228)), (x, y + 21))
        sheet.blit(pygame.transform.smoothscale(frames[t], (tw, th)), (x, y + label_h))
        print("  %-26s %s  %s" % (title, l1, l2))
    out = os.path.join(OUT, "s6_zako_ingame.png")
    pygame.image.save(sheet, out)
    print("saved", out, sheet.get_size())


roster_sheet()
wave_sheet()
ingame_sheet()
print("RENDER_OK")
