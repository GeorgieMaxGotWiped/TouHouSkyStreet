# -*- coding: utf-8 -*-
# 临时脚本：最后一波编成 + 击破 / 离场清弹 的实机预览
import os, sys, math
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager, create_bullet_angle, Bullet, burst_cancel_bullets
from src.stages import stage6 as s6

OUT = r"C:\Users\admin\.codex\visualizations\2026\09\25\01a0d626-88d7-7b43-be2a-ef20c066fb95"
F = "Microsoft YaHei,SimHei,Arial"
pygame.init()
screen = pygame.display.set_mode((960, 720))
f_t = pygame.font.SysFont(F, 16)
f_l = pygame.font.SysFont(F, 14)
f_s = pygame.font.SysFont(F, 12)
AW, AH = cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT

ORDER = ["WitherColossusEnemy", "SkeletonLordEnemy", "WitherGuardEnemy"]
DOT = {"WitherColossusEnemy": (196, 150, 255), "SkeletonLordEnemy": (225, 205, 90),
       "WitherGuardEnemy": (150, 205, 110)}
SHORT = {"WitherColossusEnemy": "Colossus", "SkeletonLordEnemy": "Skeleton Lord",
         "WitherGuardEnemy": "Wither Guard"}


def shot(stage, bm):
    screen.fill((0, 0, 0))
    stage.draw(screen, 0, 0)
    bm.draw(screen, 0, 0)
    stage.draw_foreground(screen, 0, 0)
    return screen.subsurface(pygame.Rect(0, 0, AW, AH)).copy()


def roster(stage):
    live = [e for e in stage.enemy_manager.get_active_enemies() if e.alive]
    live.sort(key=lambda e: (ORDER.index(type(e).__name__)
                             if type(e).__name__ in ORDER else 9, e.x))
    return live


def kill_lords(stage):
    """只清掉 4s 开场那两位 Lord，别动最后防线（135s 之后）那两位。"""
    if stage.timer >= 95 * 60:
        return
    for e in stage.enemy_manager.get_active_enemies():
        if isinstance(e, s6.SkeletonLordEnemy):
            while e.alive:
                e.take_damage(9999)


def run(stage, bm, frames):
    for _ in range(frames):
        kill_lords(stage)
        stage.update(1 / 60.0, bm, 288.0, 560.0)
        bm.update(1 / 60.0, bm.player_y and 1 / 60.0 or 1 / 60.0, 288.0, 560.0)


# ---------- A. 最后一波 ----------
stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm = BulletManager()
marks = [100.3, 101.0, 101.8, 103.0]
want = {int(round(m * 60)): m for m in marks}
frames_a, live_a = {}, {}
state = {"t": 0}
pending = sorted(want.items())
while pending:
    kill_lords(stage)
    stage.update(1 / 60.0, bm, 288.0, 560.0)
    bm.update(1 / 60.0, 288.0, 560.0)
    state["t"] = int(stage.timer)
    while pending and state["t"] >= pending[0][0]:
        m = pending.pop(0)[1]
        frames_a[m] = shot(stage, bm)
        live_a[m] = [(type(e).__name__, int(e.x), int(e.y)) for e in roster(stage)]

cw, ch, pad = 346, 393, 8
head = 74
rows = 6
cell = 18 + ch + 8 + rows * 13 + 8
sheet = pygame.Surface((pad * 2 + len(marks) * cw + (len(marks) - 1) * pad,
                        head + cell + pad))
sheet.fill((26, 28, 34))
sheet.blit(f_t.render(
    "六面最后一波 Final Defense（100s）：左右两位 Skeleton Lord + 上方一位 Colossus + 两位 Wither Guard",
    True, (240, 240, 246)), (pad + 2, 6))
sheet.blit(f_s.render(
    "Colossus 在 y=-70 出场、下降到 y=94 悬停；两位 Wither Guard 直接落在 y=118（x=196 / 380）；两位 Lord 从画面左右外侧 x=±622 横向切入、停在 y=204",
    True, (168, 186, 210)), (pad + 2, 28))
sheet.blit(f_s.render(
    "数字 = 画面上该帧在场的敌机（同一编号对应下方清单；本预览把两位 Lord 的伤害拉满，好让镜头只留最终编成）",
    True, (168, 186, 210)), (pad + 2, 44))
for i, m in enumerate(marks):
    x = pad + i * (cw + pad)
    lv = live_a[m]
    sheet.blit(f_l.render("%.1fs　在场 %d 只" % (m, len(lv)), True, (240, 240, 246)),
               (x, head))
    fr = pygame.transform.smoothscale(frames_a[m], (cw, ch))
    kx, ky = cw / float(AW), ch / float(AH)
    for n, (name, ex, ey) in enumerate(lv, 1):
        px, py = int(ex * kx), int(ey * ky)
        pygame.draw.circle(fr, (20, 22, 28), (px, py), 11, 0)
        pygame.draw.circle(fr, DOT.get(name, (220, 220, 220)), (px, py), 10, 2)
        fr.blit(f_s.render(str(n), True, (255, 255, 255)), (px - 4, py - 7))
    sheet.blit(fr, (x, head + 18))
    yy = head + 18 + ch + 8
    for n, (name, ex, ey) in enumerate(lv, 1):
        sheet.blit(f_s.render("%d  %s  (%d, %d)" % (n, SHORT.get(name, name), ex, ey),
                              True, DOT.get(name, (220, 220, 220))), (x, yy))
        yy += 13
out = os.path.join(OUT, "s6_final_wave.png")
pygame.image.save(sheet, out)
print("saved", out, sheet.get_size())

# ---------- B. 清弹 ----------
panels = []

stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm = BulletManager()
for _ in range(9 * 60 + 30):
    kill_lords(stage)
    stage.update(1 / 60.0, bm, 288.0, 560.0)
    bm.update(1 / 60.0, 288.0, 560.0)
g = [e for e in stage.enemy_manager.get_active_enemies()
     if isinstance(e, s6.WitherGuardEnemy)][0]
bm.enemy_bullets.clear()
for i in range(26):
    a = i * math.tau / 26
    for rr in (46.0, 96.0):
        bm.add_enemy_bullet(create_bullet_angle(
            g.x + math.cos(a) * rr, g.y + math.sin(a) * rr, 0.0, 0.0,
            Bullet.TYPE_CIRCLE, radius=3, color=(255, 120, 120), lifetime=600))
panels.append(("小怪被击破：Wither Guard（size 20 → 半径 60）",
               "击破前：圈内 26 发 / 圈外 26 发", shot(stage, bm)))
r = stage.enemy_death_clear_radius(g)
burst_cancel_bullets(bm, g.x, g.y, r, g.color)
while g.alive:
    g.take_damage(9999)
bm.update(1 / 60.0, 288.0, 560.0)
panels.append(("",
               "击破后 2 帧：圈内 26 发变白自爆，圈外 26 发原样", shot(stage, bm)))

stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm = BulletManager()
while stage.timer < 78 * 60 - 3:
    kill_lords(stage)
    stage.update(1 / 60.0, bm, 288.0, 560.0); bm.update(1 / 60.0, 288.0, 560.0)
mx, my = s6.GHOST_POSITIONS["maxor"]
for i in range(20):
    a = i * math.tau / 20
    for rr in (90.0, 150.0):
        bm.add_enemy_bullet(create_bullet_angle(
            mx + math.cos(a) * rr, my + math.sin(a) * rr, 0.0, 0.0,
            Bullet.TYPE_CIRCLE, radius=3, color=(255, 120, 120), lifetime=600))
panels.append(("残影离场：Maxor（半径 180）",
               "离场前：一圈 40 发环绕 + 残影本体的弹幕", shot(stage, bm)))
for _ in range(4):
    kill_lords(stage)
    stage.update(1 / 60.0, bm, 288.0, 560.0); bm.update(1 / 60.0, 288.0, 560.0)
panels.append(("", "离场后 4 帧：范围内敌弹整片变白自爆", shot(stage, bm)))

cw2, ch2, pad2, head2, rows2 = 400, 465, 8, 62, 2
cell2 = 18 + ch2 + 8 + rows2 * 13 + 8
sheet2 = pygame.Surface((pad2 * 2 + len(panels) * cw2 + (len(panels) - 1) * pad2,
                         head2 + cell2 + pad2))
sheet2.fill((26, 28, 34))
sheet2.blit(f_t.render(
    "六面击破 / 离场清弹：小怪被击破（半径 = 判定半径 × 3）与残影离场（半径 180）都炸掉范围内的敌弹",
    True, (240, 240, 246)), (pad2 + 2, 6))
sheet2.blit(f_s.render(
    "半径表（判定半径×3）：凋零游魂 42 / 矿工 48 / 骑士 57 / 守卫·兵马俑 60 / Skeleton Lord 66 / 巨像 90 / 残影 180",
    True, (168, 186, 210)), (pad2 + 2, 28))
sheet2.blit(f_s.render(
    "清掉的弹走游戏里原有的「变白自爆」动画（不是瞬间消失），另外补两圈无害白光把它包住",
    True, (168, 186, 210)), (pad2 + 2, 44))
for i, (t1, t2, fr) in enumerate(panels):
    x = pad2 + i * (cw2 + pad2)
    sheet2.blit(f_l.render(t1 or " ", True, (240, 240, 246)), (x, head2))
    sheet2.blit(pygame.transform.smoothscale(fr, (cw2, ch2)), (x, head2 + 18))
    sheet2.blit(f_s.render(t2, True, (176, 200, 228)), (x, head2 + 18 + ch2 + 8))
out2 = os.path.join(OUT, "s6_death_clear.png")
pygame.image.save(sheet2, out2)
print("saved", out2, sheet2.get_size())
print("RENDER_OK")
