# -*- coding: utf-8 -*-
# 焚符「Nuclear Frenzy」预览 + 端到端验证：
#   领域半径随火力压制收缩 / 停止攻击后扩张 / 过载惩罚 / 领域内中弹判定
import os
import sys
import math

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())

import pygame

from src.engine import settings as cfg
from src.engine.game import Game
from src.entities.bullet import BulletManager
from src.ui.menu import PlayingState
from src.stages.stage5 import (Stage5_WitherLords, _NUKE_HIT_WINDOW,
                              _NUKE_HIT_FULL)

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))

OUT = r"C:\Users\admin\.codex\visualizations\2026\08\15\01a004f3-1870-72a3-956d-6017b596595d"
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
    boss.current_spell_idx = 0
    boss._start_spell(boss.spell_cards[0])
    assert boss.current_spell.name == "焚符「Nuclear Frenzy」"
    return boss


def _snap(stage, bm, tag, label):
    screen.fill((0, 0, 0))
    stage.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    bm.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    stage.draw_foreground(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    out = os.path.join(OUT, tag)
    pygame.image.save(screen, out)
    nuke = stage.boss.necron_nuclear
    print(f"{label}: timer={stage.boss.current_spell.timer} "
          f"radius={nuke['radius']:.1f} growth={nuke['growth']:.2f} "
          f"hits={nuke['hit_total']} bullets={len(bm.enemy_bullets)} saved={out}")


def _preview():
    stage = Stage5_WitherLords()
    stage.phase = "dialogue"
    boss = _build_necron_spell(stage)
    bm = BulletManager()
    px, py = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 90

    # 持续火力阶段：领域几乎不因输出收缩，仍缓慢扩张
    for _ in range(130):
        boss.take_damage(20)
        bm.update(1 / 60, px, py)
        stage.update(1 / 60, bm, px, py)
    _snap(stage, bm, "necron_nuclear_attack.png", "持续火力下领域仍扩张")

    # 短暂停火：领域开始扩大
    for _ in range(150):
        bm.update(1 / 60, px, py)
        stage.update(1 / 60, bm, px, py)
    _snap(stage, bm, "necron_nuclear_growing.png", "停止攻击继续扩张")

    # 持续停火：领域逼近上限并进入过载
    for _ in range(300):
        bm.update(1 / 60, px, py)
        stage.update(1 / 60, bm, px, py)
    _snap(stage, bm, "necron_nuclear_overload.png", "领域持续扩张")
    return stage, bm


def _e2e():
    game = Game()
    stage = Stage5_WitherLords()
    stage.phase = "dialogue"
    ps = PlayingState(game, stage)
    boss = _build_necron_spell(stage)

    # 1) Necron 停留在场地中央
    for _ in range(90):
        stage.update(1 / 60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH / 2,
                     cfg.BATTLE_AREA_HEIGHT - 90)
    assert abs(boss.x - cfg.BATTLE_AREA_WIDTH / 2) < 12, "Necron 应停留在场地中央"
    r_no_fire = boss.necron_nuclear["radius"]
    assert r_no_fire > 70, f"未攻击时领域应持续扩张（radius={r_no_fire}）"
    print(f"[1] 停留中央 + 无攻击扩张 OK radius={r_no_fire:.1f}")

    # 0) 来源判定：追踪弹与主弹权重相同（各计 1 点命中量）
    hp_before = boss.hp
    boss.take_damage(10, source="homing")
    assert boss.hp < hp_before, "追踪弹应造成伤害"
    assert boss.necron_nuclear["hits_this_frame"] == 1, "追踪弹应计入 1 点命中量"
    boss.take_damage(10, source="main")
    assert boss.necron_nuclear["hits_this_frame"] == 2, "主弹应同样计入 1 点命中量"
    boss.necron_nuclear["hits_this_frame"] = 0
    boss.hp = hp_before
    print("[0] 追踪弹/主弹同权重计命中量 OK")

    # 1b) 仅追踪弹持续输出（模拟原地按住开火）：领域应继续扩张、无法被压制
    for _ in range(120):
        boss.take_damage(8, source="homing")
        stage.update(1 / 60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH / 2,
                     cfg.BATTLE_AREA_HEIGHT - 90)
    r_homing = boss.necron_nuclear["radius"]
    assert r_homing > r_no_fire + 25, f"仅追踪弹不应明显压慢领域（{r_no_fire:.1f} -> {r_homing:.1f}）"
    print(f"[1b] 仅追踪弹几乎不压慢领域 OK {r_no_fire:.1f} -> {r_homing:.1f}")

    # 2) 持续最大火力（主+追踪，4 发/帧）下领域压到最慢 0.3 px/帧
    for _ in range(120):
        for _ in range(4):
            boss.take_damage(1)
        stage.update(1 / 60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH / 2,
                     cfg.BATTLE_AREA_HEIGHT - 90)
    r_fire = boss.necron_nuclear["radius"]
    assert r_fire - r_homing >= 9, f"满火力下应压到最慢膨胀（120 帧 {r_fire - r_homing:.1f}px）"
    assert r_fire - r_homing < 25, f"满火力下膨胀不应过快（120 帧 {r_fire - r_homing:.1f}px）"
    print(f"[2] 满火力压到最慢 OK {r_homing:.1f} -> {r_fire:.1f}")

    # 2b) 停火后命中窗口清空，领域回升到最快扩张（1.0 px/帧）
    g_steady = boss.necron_nuclear["growth"]
    for _ in range(30):
        stage.update(1 / 60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH / 2,
                     cfg.BATTLE_AREA_HEIGHT - 90)
    g_stop = boss.necron_nuclear["growth"]
    assert g_stop > g_steady, f"停火后应比持续输出更快（{g_steady:.2f} -> {g_stop:.2f}）"
    for _ in range(30):
        stage.update(1 / 60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH / 2,
                     cfg.BATTLE_AREA_HEIGHT - 90)
    g_max = boss.necron_nuclear["growth"]
    assert g_max >= 1.0 / 3.0 - 0.001, f"停火后应回到最快扩张（当前 {g_max:.2f}）"
    print(f"[2b] 停火回升到最快 OK {g_steady:.2f} -> {g_stop:.2f} -> {g_max:.2f}")

    # 2c) 稀疏命中（1-2 发）时膨胀更快，满负荷命中时最慢，速度随命中量递减
    def _growth_with_hits(n):
        nk = boss.necron_nuclear
        nk["hit_window"] = [0] * _NUKE_HIT_WINDOW
        nk["hit_total"] = 0
        nk["hits_this_frame"] = 0
        for _ in range(n):
            boss.take_damage(1)
        for _ in range(30):
            stage.update(1 / 60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH / 2,
                         cfg.BATTLE_AREA_HEIGHT - 90)
        return nk["growth"]
    g1 = _growth_with_hits(1)
    g2 = _growth_with_hits(2)
    g100 = _growth_with_hits(_NUKE_HIT_FULL)
    assert g1 > 0.3, f"1 发命中应接近最快 1/3（g1={g1:.3f}）"
    assert g1 > g2, f"1 发命中应比 2 发更快（g1={g1:.3f} g2={g2:.3f}）"
    assert g100 <= 0.12, f"满命中量应压到最慢（g100={g100:.3f}）"
    print(f"[2c] 命中量反比 OK 1发={g1:.2f} 2发={g2:.2f} 满={g100:.2f}")

    # 3) 领域内中弹判定：玩家在领域内被击中
    nuke = boss.necron_nuclear
    ps.player.x, ps.player.y = nuke["cx"], nuke["cy"] + 10
    ps.player.invincible = 0
    lives_before = ps.lives
    ps._check_collisions()
    assert ps.death_window > 0 or ps.lives < lives_before, "领域内应触发中弹"
    print(f"[3] 领域内中弹 OK (death_window={ps.death_window})")

    # 4) 领域外安全
    ps.player.x, ps.player.y = 40, cfg.BATTLE_AREA_HEIGHT - 30
    ps.player.invincible = 0
    ps.death_window = 0
    lives_before = ps.lives
    ps._check_collisions()
    assert ps.death_window == 0 and ps.lives == lives_before, "领域外不应中弹"
    print("[4] 领域外安全 OK")

    # 5) 无最大扩张封顶：停火足够久后领域持续扩张越过旧上限 340 且不回缩
    for _ in range(700):
        stage.update(1 / 60, ps.bullet_manager, cfg.BATTLE_AREA_WIDTH / 2,
                     cfg.BATTLE_AREA_HEIGHT - 90)
    nuke = boss.necron_nuclear
    assert nuke["radius"] > 400, f"领域应无封顶持续扩张（radius={nuke['radius']:.1f}）"
    assert nuke["growth"] >= 1.0 / 3.0 - 0.001, f"停火时扩张应保持最快（{nuke['growth']:.2f}）"
    print(f"[5] 无封顶持续扩张 OK radius={nuke['radius']:.1f}")

    # 6) 转盘/冲击环弹幕存在
    orbit = [eb for eb in ps.bullet_manager.enemy_bullets if eb.orbit_center is not None]
    assert orbit, "应生成公转环弹幕"
    print(f"[6] 旋转公转环弹幕 OK orbit={len(orbit)}")

    # 7) 领域外弹幕密度：弹墙数量再次减半后，120 帧喷发量约为初版的 1/4（≈1.05/帧 -> ≥ 110）
    stage7 = Stage5_WitherLords()
    stage7.phase = "dialogue"
    boss7 = _build_necron_spell(stage7)
    bm7 = BulletManager()
    spawned = [0]
    orig_add = bm7.add_enemy_bullet
    bm7.add_enemy_bullet = lambda b: (orig_add(b), spawned.__setitem__(0, spawned[0] + 1))
    for _ in range(120):
        stage7.update(1 / 60, bm7, cfg.BATTLE_AREA_WIDTH / 2,
                      cfg.BATTLE_AREA_HEIGHT - 90)
    bm7.add_enemy_bullet = orig_add
    assert spawned[0] >= 110, f"领域外弹幕密度约为初版 1/4（120 帧喷发 {spawned[0]}）"
    print(f"[7] 领域外海量弹幕 OK 120 帧喷发 {spawned[0]} 颗")

    # 8) 弹墙贯穿全屏：480 帧模拟中边缘米弹应能飞到屏幕底部而不中途消失
    stage9 = Stage5_WitherLords()
    stage9.phase = "dialogue"
    boss9 = _build_necron_spell(stage9)
    bm9 = BulletManager()
    max_y = 0.0
    px9, py9 = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 90
    for _ in range(480):
        bm9.update(1 / 60, px9, py9)
        stage9.update(1 / 60, bm9, px9, py9)
        for eb in bm9.enemy_bullets:
            if eb.bullet_type == "rice":
                max_y = max(max_y, eb.y)
    assert max_y > cfg.BATTLE_AREA_HEIGHT - 110,         f"弹墙应贯穿全屏（最大 y={max_y:.1f}）"
    print(f"[8] 弹墙贯穿全屏 OK 最大 y={max_y:.1f} / {cfg.BATTLE_AREA_HEIGHT}")
    print("E2E ALL OK")


if __name__ == "__main__":
    _preview()
    _e2e()
    pygame.quit()
    print("PREVIEW OK")
