# -*- coding: utf-8 -*-
# 五面 Livid 影符「八重存在」冒烟测试：被击破的分身不得再发弹 / 再移动。
#
# 分身的攻击与移动由 boss.livid_states 统一驱动（分身实体只负责碰撞与绘制），
# 所以「分身死了」必须同时把所属状态标掉，否则空位上会照常出弹。
# 本工具逐帧记录「哪个状态发了弹」，并带一条复刻修复前写法的自证：
# 旧循环忽略 state["alive"]，同一探针下死亡分身照常发弹。
import os
import random
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame

pygame.init()
pygame.display.set_mode((960, 720))
sys.path.insert(0, os.getcwd())

from src.engine import settings as cfg
from src.entities.bullet import BulletManager
from src.stages.stage5 import Stage5_WitherLords
import src.stages.stage5 as s5


def _make_boss(seed=1234):
    random.seed(seed)
    stage = Stage5_WitherLords()
    stage.setup_waves()
    return stage._build_boss("livid")


def _probe(boss, frames, timer_from=1, dt=1 / 60.0, px=None, py=None):
    """跑符卡若干帧，返回「发过弹的状态下标」列表。

    探针挂在 s5._livid_entity_attack 上（符卡内部按模块属性查表，patch 生效），
    按「本帧敌弹数量是否增加」判断该状态这一帧是否发了弹。
    """
    fired = []
    orig = s5._livid_entity_attack

    def wrapped(b, bm, state, timer, d, p_x, p_y):
        before = len(bm.enemy_bullets)
        orig(b, bm, state, timer, d, p_x, p_y)
        if len(bm.enemy_bullets) > before:
            fired.append(state["index"])

    s5._livid_entity_attack = wrapped
    bm = BulletManager()
    px = cfg.BATTLE_AREA_WIDTH / 2 if px is None else px
    py = cfg.BATTLE_AREA_HEIGHT - 80 if py is None else py
    try:
        for timer in range(timer_from, timer_from + frames):
            s5.spell_livid_eightfold_existence(boss, bm, timer, dt, px, py)
            # 复刻 Stage5_WitherLords.draw_foreground 的黑幕回退（本工具不跑绘制）
            if getattr(boss, "livid_blackout_frames", 0) > 0:
                boss.livid_blackout_frames -= 1
                if boss.livid_blackout_frames == 0 and getattr(boss, "livid_swap_pending", False):
                    s5._livid_swap_positions(boss)
                    boss.livid_swap_pending = False
    finally:
        s5._livid_entity_attack = orig
    return fired, bm


def main():
    # [1] 全员存活：八个状态都在发弹（真身 + 七个分身）
    boss = _make_boss()
    fired, _ = _probe(boss, 1200)
    all_fired = sorted(set(fired))
    assert all_fired == list(range(8)), f"expected all 8 states to fire, got {all_fired}"
    real = boss.livid_real_index
    print(f"[1] 全员存活：8 个状态都发弹（真身下标 {real}）")

    # [2] 击破三个分身：它们不再发弹，其余状态照常
    victims = [i for i in range(8) if i != real][:3]
    for i in victims:
        clone = boss.livid_clone_map[i]
        clone.take_damage(10 ** 9)
        assert not clone.alive, f"clone {i} should be dead"
        assert clone.state["alive"] is False, f"clone {i} state should be marked dead"
    fired, _ = _probe(boss, 1800, timer_from=1201)
    after = sorted(set(fired))
    leaked = [i for i in victims if i in after]
    assert not leaked, f"被击破的分身仍在发弹：{leaked}"
    alive_states = [i for i in range(8) if i not in victims]
    missing = [i for i in alive_states if i not in after]
    assert not missing, f"存活的状态不再发弹：{missing}"
    print(f"[2] 击破分身 {victims} 后：只有存活状态 {alive_states} 发弹")

    # [3] 死亡状态不再自己移动（黑幕换位仍会重排它，与改前一致）
    frozen = {i: (boss.livid_states[i]["x"], boss.livid_states[i]["y"]) for i in victims}
    swaps = 0
    checked = 0
    for timer in range(3001, 3601):
        s5.spell_livid_eightfold_existence(boss, BulletManager(), timer, 1 / 60.0, 240, 500)
        if getattr(boss, "livid_blackout_frames", 0) > 0:
            boss.livid_blackout_frames -= 1
            if boss.livid_blackout_frames == 0 and getattr(boss, "livid_swap_pending", False):
                s5._livid_swap_positions(boss)
                boss.livid_swap_pending = False
                swaps += 1
                for i in victims:
                    frozen[i] = (boss.livid_states[i]["x"], boss.livid_states[i]["y"])
                continue
        for i in victims:
            st = boss.livid_states[i]
            fx, fy = frozen[i]
            assert abs(st["x"] - fx) < 1e-6 and abs(st["y"] - fy) < 1e-6, \
                f"死亡状态 {i} 仍在移动"
        checked += 1
    assert swaps >= 1, "本段应至少覆盖一次黑幕换位"
    print(f"[3] 死亡状态不再自行移动（{checked} 帧逐帧核对，期间黑幕换位 {swaps} 次）")

    # [4] 死亡分身不再可被击中，也不会再次给真身回血
    clone = boss.livid_clone_map[victims[0]]
    hp_before = boss.hp
    assert clone.take_damage(999) is False
    assert boss.hp == hp_before, "death handling healed the boss again"
    print("[4] 死亡分身不可再被击中，也不会重复回血")

    # [5] 自证：复刻修复前的循环（无视 state["alive"]）时，死亡分身照常发弹
    boss = _make_boss()
    s5.spell_livid_eightfold_existence(boss, BulletManager(), 1, 1 / 60.0, 240, 500)
    real = boss.livid_real_index
    victims = [i for i in range(8) if i != real][:2]
    for i in victims:
        boss.livid_clone_map[i].take_damage(10 ** 9)
    bm = BulletManager()
    fired = []
    orig = s5._livid_entity_attack

    def wrapped(b, b_manager, state, timer, d, p_x, p_y):
        before = len(b_manager.enemy_bullets)
        orig(b, b_manager, state, timer, d, p_x, p_y)
        if len(b_manager.enemy_bullets) > before:
            fired.append(state["index"])

    s5._livid_entity_attack = wrapped
    try:
        for timer in range(2, 700):
            if timer % 300 == 0:
                boss.livid_blackout_frames = 10
                boss.livid_swap_pending = True
            if boss.livid_blackout_frames > 0:
                boss.livid_blackout_frames -= 1
                if boss.livid_blackout_frames == 0 and boss.livid_swap_pending:
                    s5._livid_swap_positions(boss)
                    boss.livid_swap_pending = False
                continue
            for state in boss.livid_states:      # 修复前的写法：不看 state["alive"]
                s5._livid_update_position(state, timer, 1 / 60.0)
                s5._livid_entity_attack(boss, bm, state, timer, 1 / 60.0, 240, 500)
    finally:
        s5._livid_entity_attack = orig
    repro = sorted(set(fired) & set(victims))
    assert repro == sorted(victims), f"复现失败：旧写法下死亡分身应照常发弹，实际 {repro}"
    print(f"[5] 自证有效：旧写法下死亡分身 {repro} 照常发弹")
    print("ALL OK")


if __name__ == "__main__":
    main()
