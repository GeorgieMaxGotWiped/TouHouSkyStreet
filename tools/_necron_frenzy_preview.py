# -*- coding: utf-8 -*-
# 终符「Necron's Frenzy」预览 + 端到端验证：
#   八臂螺旋弹速渐快 / 大玉环 / 底部烈焰上涌 / 密度随时间攀升
import math
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())

import pygame

from src.engine import settings as cfg
from src.engine.game import Game
from src.entities.bullet import BulletManager
from src.ui.menu import PlayingState
from src.stages.stage5 import Stage5_WitherLords
from src.stages import stage5 as s5

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))

OUT = r"C:\Users\admin\.codex\visualizations\2026\08\15\01a00525-d36f-7dc1-8124-66de8da7792d"
os.makedirs(OUT, exist_ok=True)


def _build_necron_spell(stage):
    boss = stage._build_boss("necron")
    stage.boss = boss
    stage.phase = "boss"
    stage._boss_defeated_handled = False
    stage._on_boss_combat_start = lambda: None
    boss.arm_combat(0)
    boss.entering = False
    boss.entry_timer = 0
    boss.current_spell_idx = 1
    boss._start_spell(boss.spell_cards[1])
    assert boss.current_spell.name == "终符「Necron's Frenzy」"
    return boss


def _snap(stage, bm, tag, label):
    screen.fill((0, 0, 0))
    stage.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    bm.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    stage.draw_foreground(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    out = os.path.join(OUT, tag)
    pygame.image.save(screen, out)
    counts = {}
    for eb in bm.enemy_bullets:
        counts[eb.bullet_type] = counts.get(eb.bullet_type, 0) + 1
    fire = sum(1 for eb in bm.enemy_bullets
                if eb.bullet_type == "rice"
                and (eb.wobble_amp > 0 or eb.turn_rate != 0))
    print(f"{label}: timer={stage.boss.current_spell.timer} total={len(bm.enemy_bullets)} "
          f"fire={fire} types={counts} saved={out}")


def _preview():
    stage = Stage5_WitherLords()
    stage.phase = "dialogue"
    _build_necron_spell(stage)
    bm = BulletManager()
    px, py = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 90

    t0 = time.perf_counter()
    early = None
    for frame in range(1, 2200):
        bm.update(1 / 60, px, py)
        stage.update(1 / 60, bm, px, py)
        if frame == 150:
            _snap(stage, bm, "necron_frenzy_early.png", "开场")
        if frame == 900:
            _snap(stage, bm, "necron_frenzy_mid.png", "中段")
        if frame == 2100:
            _snap(stage, bm, "necron_frenzy_full.png", "狂暴满潮")
        if frame == 2200 - 1:
            early = len(bm.enemy_bullets)
    elapsed = time.perf_counter() - t0
    print(f"2200 frames in {elapsed:.2f}s ({2200 / elapsed:.0f} fps)")
    return stage, bm


def _e2e():
    game = Game()
    stage = Stage5_WitherLords()
    stage.phase = "dialogue"
    ps = PlayingState(game, stage)
    boss = _build_necron_spell(stage)

    # 1) 弹幕密度随时间攀升（狂暴度生效）
    def counts():
        c = {}
        for eb in ps.bullet_manager.enemy_bullets:
            c[eb.bullet_type] = c.get(eb.bullet_type, 0) + 1
        return c

    for _ in range(150):
        ps.bullet_manager.update(1 / 60, cfg.BATTLE_AREA_WIDTH / 2,
                                 cfg.BATTLE_AREA_HEIGHT - 90)
        stage.update(1 / 60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH / 2,
                     cfg.BATTLE_AREA_HEIGHT - 90)
    early_total = len(ps.bullet_manager.enemy_bullets)
    early_c = counts()
    assert early_total > 40, f"开场应已有可观弹量（{early_total}）"
    assert early_c.get("circle", 0) > 0, "应有圆弹"
    assert early_c.get("rice", 0) > 0, "应有米弹"
    assert early_c.get("big", 0) > 0, "应有大玉"

    # 地狱火从屏幕底端下方不可见处逐渐浮现
    for _ in range(400):
        ps.bullet_manager.update(1 / 60, cfg.BATTLE_AREA_WIDTH / 2,
                                 cfg.BATTLE_AREA_HEIGHT - 90)
        stage.update(1 / 60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH / 2,
                     cfg.BATTLE_AREA_HEIGHT - 90)
    emerging = [eb for eb in ps.bullet_manager.enemy_bullets
                if eb.bullet_type == "rice"
                and (eb.wobble_amp > 0 or eb.turn_rate != 0)
                and eb.y > 600]
    assert emerging, "地狱火应从屏幕底端下方逐渐浮现"
    print(f"[1b] 地狱火浮现 OK emerging_near_bottom={len(emerging)}")

    for _ in range(1600):
        ps.bullet_manager.update(1 / 60, cfg.BATTLE_AREA_WIDTH / 2,
                                 cfg.BATTLE_AREA_HEIGHT - 90)
        stage.update(1 / 60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH / 2,
                     cfg.BATTLE_AREA_HEIGHT - 90)
    late_total = len(ps.bullet_manager.enemy_bullets)
    assert late_total > early_total + 30, \
        f"烈焰铺满后弹量应继续上升（{early_total} -> {late_total}）"
    # 大玉：整圈径向直线外扩（无公转环）
    bigs = [eb for eb in ps.bullet_manager.enemy_bullets
            if eb.bullet_type == "big"]
    assert bigs, "应有大玉"
    assert all(eb.orbit_center is None for eb in bigs), "大玉应为匀速直线外扩"

    # 烈火：底部喷发的密集不稳定火焰弹（蛇形摆动 + 转向）
    fire = [eb for eb in ps.bullet_manager.enemy_bullets
            if eb.bullet_type == "rice"
            and (eb.wobble_amp > 0 or eb.turn_rate != 0)]
    assert fire, "应有从底端下方浮现的密集不稳定火焰弹"
    assert len(fire) > 300, f"地狱火应非常密集（{len(fire)}）"
    # 上跳高度只与火墙当前高度相关：顶部不越过火线上方固定距离
    wall_y = max(s5._FRENZY_FIRE_TOP_Y,
                 s5._FRENZY_FIRE_START_Y - s5._FRENZY_FIRE_RISE * 2150)
    flame_top = min(eb.y for eb in fire)
    assert flame_top > wall_y - 230, \
        f"火焰上跳应显著降低并随火墙整体上移（top={flame_top:.0f} wall={wall_y:.0f}）"
    assert flame_top < wall_y - 60, \
        f"火焰仍应在火墙上方喷发（top={flame_top:.0f} wall={wall_y:.0f}）"

    # 八臂螺旋：圆弹匀速直线，且弹速随时间逐渐加快
    circles = [eb for eb in ps.bullet_manager.enemy_bullets
               if eb.bullet_type == "circle" and eb.orbit_center is None]
    assert circles, "应有八臂螺旋圆弹"
    assert len(circles) > 160, f"螺旋密度应翻倍（{len(circles)}）"
    speeds = [math.hypot(eb.vx, eb.vy) for eb in circles]
    avg_speed = sum(speeds) / len(speeds)
    assert avg_speed > 1.5, f"螺旋初速应恢复原值 1.55 且随时间加快（avg={avg_speed:.2f}）"
    print(f"[1] 开场弹量 OK early={early_total} types={early_c}")
    print(f"[2] 满潮 OK {early_total} -> {late_total} big={len(bigs)} "
          f"fire={len(fire)} flame_top={flame_top:.0f} wall={wall_y:.0f} "
          f"avg_spiral_speed={avg_speed:.2f} "
          f"types={counts()}")

    # 2) Necron 保持在场地中央附近且存活
    assert boss.alive, "终符进行中 Boss 应存活"
    assert abs(boss.x - cfg.BATTLE_AREA_WIDTH / 2) < 120, "Necron 不应离开场地中央"
    print(f"[3] Necron 居中悬浮 OK x={boss.x:.0f} y={boss.y:.0f}")

    # 3) 击破终符：血量打空后结束战斗
    boss.hp = 1
    boss.take_damage(99999)
    assert boss.phase == "defeated" or not boss.alive, "终符血量打空应结束战斗"
    print("[4] 终符击破结算 OK")
    print("E2E ALL OK")


if __name__ == "__main__":
    _preview()
    _e2e()
    pygame.quit()
    print("PREVIEW OK")
