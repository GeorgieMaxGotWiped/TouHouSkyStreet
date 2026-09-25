# -*- coding: utf-8 -*-
# 临时脚本：游魂队形（V / 斜线）+ 守卫矿工落点上移 预览（出生点示意图 + 实机各一行）
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
f_t = pygame.font.SysFont(F, 15)
f_s = pygame.font.SysFont(F, 12)

WAVES = [(9, "9s Undead Line"), (14, "14s Miner Phalanx"),
         (19, "19s Fortress Gate"), (29, "29s Guard Wall"),
         (34, "34s Last March")]
SHAPES = {9: "两个斜臂（左 \\ + 右 /）＝ V", 14: "两个斜臂（左 \\ + 右 /）＝ V",
          19: "V 字（3 只）", 29: "V 字（6 只）", 34: "双层 V 字（5 + 5 只）"}
LATER = 2.6
ABOVE = 200          # 示意图里画出战斗区上缘之外多少 px（游魂的出生带）
stage = s6.Stage6_FinalApproach(); stage.setup_waves()
spawn = {}
for tw, wave in stage.enemy_manager.timed_waves:
    if tw // 60 in dict(WAVES):
        spawn[tw // 60] = [(type(e).__name__, e.x, e.y) for e in wave.enemies]

bm = BulletManager()
want = {int(round((t + LATER) * 60)): t for t, _ in WAVES}
frames, live = {}, {}
t = 0
while t <= max(want):
    stage.update(1.0 / 60.0, bm, 288.0, 560.0)
    bm.update(1.0 / 60.0, 288.0, 560.0)
    if t in want:
        screen.fill((0, 0, 0))
        stage.draw(screen, 0, 0)
        bm.draw(screen, 0, 0)
        stage.draw_foreground(screen, 0, 0)
        wt = want[t]
        frames[wt] = screen.subsurface(pygame.Rect(
            0, 0, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT)).copy()
        w = [wv for tt, wv in stage.enemy_manager.timed_waves if tt == wt * 60][0]
        live[wt] = sorted([(e.x, e.y) for e in w.enemies
                           if isinstance(e, s6.WitherHuskEnemy) and e.alive])
    t += 1

cw, ch, pad, head = 214, 249, 8, 58
sheet = pygame.Surface((pad + len(WAVES) * (cw + pad), head + pad + 2 * (ch + 26 + pad)))
sheet.fill((26, 28, 34))
sheet.blit(pygame.font.SysFont(F, 16).render(
    "六面道中：凋零守卫 / 凋零矿工落点上移到 y=64~180（仍保持原来的高低先后）；同一批凋零游魂摆成 V 字或斜线",
    True, (240, 240, 246)), (pad + 2, 5))
sheet.blit(f_s.render("上排＝出生点示意（俯视战斗区 + 上缘之外 200px；黄＝守卫 青＝矿工 红＝游魂）　下排＝该波出场后 %.1fs 的实机画面（红圈圈出游魂）" % LATER,
                      True, (168, 186, 210)), (pad + 2, 27))
sheet.blit(f_s.render("游魂整队下落速度相同（3.0 px/帧），进画面后队形保持不变",
                      True, (168, 186, 210)), (pad + 2, 42))

for i, (wt, title) in enumerate(WAVES):
    x = pad + i * (cw + pad)
    sheet.blit(f_t.render(title, True, (240, 240, 246)), (x, head))
    sheet.blit(f_s.render(SHAPES[wt], True, (176, 200, 228)), (x, head + 17))
    # --- 出生点示意 ---
    dia = pygame.Surface((cw, ch))
    dia.fill((19, 21, 27))
    kx = cw / 576.0
    ky = (ch - 8) / float(670 + ABOVE)
    top = 4 + ABOVE * ky
    pygame.draw.rect(dia, (40, 44, 54), (0, 0, cw, top))          # 上缘之外的出生带
    pygame.draw.line(dia, (120, 126, 140), (0, top), (cw, top))   # 战斗区上缘
    dia.blit(f_s.render("画面顶边 y=0", True, (140, 146, 160)), (4, top + 2))
    husk_pts = []
    for name, ex, ey in spawn[wt]:
        px, py = ex * kx, 4 + (ey + ABOVE) * ky
        if name == "WitherHuskEnemy":
            husk_pts.append((px, py))
        else:
            pygame.draw.circle(dia, (222, 196, 92) if name == "WitherGuardEnemy" else (92, 208, 186),
                               (int(px), int(py)), 4)
    for a, b in zip(husk_pts, husk_pts[1:]):
        pygame.draw.line(dia, (150, 70, 70), a, b, 1)
    for px, py in husk_pts:
        pygame.draw.circle(dia, (238, 96, 96), (int(px), int(py)), 4)
    yy = 4
    for name, ex, ey in spawn[wt]:
        if name != "WitherHuskEnemy":
            continue
        dia.blit(f_s.render("(%d, %d)" % (ex, ey), True, (226, 150, 150)), (4, yy))
        yy += 13
    pygame.draw.rect(dia, (56, 60, 72), dia.get_rect(), 1)
    sheet.blit(dia, (x, head + 34))
    # --- 实机画面 + 游魂标记 ---
    shot = pygame.transform.smoothscale(frames[wt], (cw, ch))
    kx2, ky2 = cw / 576.0, ch / 670.0
    pts = [(p[0] * kx2, p[1] * ky2) for p in live[wt]]
    for a, b in zip(pts, pts[1:]):
        pygame.draw.line(shot, (255, 120, 120), a, b, 1)
    for px, py in pts:
        pygame.draw.circle(shot, (255, 120, 120), (int(px), int(py)), 11, 1)
    sheet.blit(shot, (x, head + 34 + ch + 26))

out = os.path.join(OUT, "s6_husk_formation.png")
pygame.image.save(sheet, out)
print("saved", out, sheet.get_size())
for wt, title in WAVES:
    print("  %-20s" % title, " ".join("(%d,%d)" % p for p in live[wt]))
print("RENDER_OK")
