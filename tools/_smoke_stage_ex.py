# -*- coding: utf-8 -*-
# Ex 面（裂隙 ~ The Rift）冒烟测试：无头跑完整流程，并把关键节点渲染成 PNG。
#
# 流程：0~45s 道中（裂隙生物）-> Wizardman 登场（先对话）-> 对话结束开打（无符卡）
#       -> 道中Boss击破 -> 后段小怪清空 -> Barry 登场的战前对话 -> Barry 战（无符卡）
#       -> 战后对话 -> 通关 cleared。
# 渲染结果落在 previews/_stage_ex_*.png，用来肉眼确认立绘 / 弹幕 / 裂隙背景。
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

pygame.init()
screen = pygame.display.set_mode((960, 720))

from src.engine import settings as cfg
from src.entities.bullet import BulletManager
from src.stages import get_extra_stage_class

OUT_DIR = os.path.join(os.getcwd(), "previews")


def main():
    stage = get_extra_stage_class()()
    assert stage.stage_num == cfg.EX_STAGE_NUM, stage.stage_num
    assert getattr(stage, "items_disabled", False), "Ex 面必须标记 items_disabled（无装备物品效果）"
    assert stage.loading_title == "Extra Stage", stage.loading_title
    for path in (stage.title_path, stage.music_path, stage.music_loop_path,
                 stage.boss_music_start_path, stage.boss_music_loop_path,
                 cfg.EX_STAGE_FLOOR, cfg.EX_STAGE_WALL):
        assert os.path.exists(path), path
    assert type(stage.background).__name__ == "Pseudo3DFloor", type(stage.background)
    stage.setup_waves()
    bm = BulletManager()
    px, py = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80

    def step(n):
        for _ in range(n):
            stage.update(1.0 / 60.0, bm, px, py)
            bm.update(1.0 / 60.0, px, py)

    def shot(label):
        screen.fill((0, 0, 0))
        stage.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
        bm.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
        stage.draw_foreground(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
        os.makedirs(OUT_DIR, exist_ok=True)
        path = os.path.join(OUT_DIR, "_stage_ex_%s.png" % label)
        pygame.image.save(screen, path)
        print("      saved %s" % os.path.basename(path))

    def report(label):
        print("%-22s t=%5.1fs phase=%-14s enemies=%d bullets=%d" % (
            label, stage.timer / 60.0, stage.phase,
            len(stage.enemy_manager.get_active_enemies()), len(bm.enemy_bullets)))

    # ---------------------------------------------------------------- 道中
    print("[1] 道中：裂隙生物按时间轴涌入（20s / 46s 渲染两帧）")
    step(20 * 60)
    report("mid-20s")
    shot("mid_20s")
    step(26 * 60)
    report("mid-46s")
    assert stage.phase == "dialogue", stage.phase
    assert stage.dialogue_target == "mid", stage.dialogue_target
    assert stage.mid_boss is not None and stage.mid_boss.alive
    assert not stage.mid_boss.combat_enabled, "对话期间 Wizardman 不应开打"
    assert stage.mid_boss_dialogue_lines, "道中Boss 必须有对话"
    print("      Wizardman 登场：%d 句对话，暂不开打" % len(stage.mid_boss_dialogue_lines))
    shot("wizardman_dialogue")

    # ------------------------------------------------- Wizardman 战（无符卡）
    print("[2] Wizardman 战（暂不配符卡）")
    stage.on_dialogue_end()
    assert stage.phase == "mid_boss", stage.phase
    assert stage.mid_boss.spell_cards == [], "Ex 面道中Boss 暂不配符卡"
    step(6 * 60)
    assert stage.mid_boss.combat_enabled, "对话结束后应当开打"
    assert stage.mid_boss.current_spell is None
    report("wizardman-6s")
    shot("wizardman_fight")
    step(12 * 60)
    report("wizardman-18s")
    shot("wizardman_fight_18s")

    while stage.mid_boss.alive:
        stage.mid_boss.take_damage(600)
        step(1)
    step(2)
    assert stage.phase == "post_midboss", stage.phase
    print("      道中Boss击破 -> post_midboss")

    # ------------------------------------------------ 后段小怪 -> Barry 对话
    print("[3] 道中Boss后的残兵清空 -> Barry 登场对话")
    guard = 0
    while stage.phase == "post_midboss" and guard < 3 * 60 * 60:
        for enemy in stage.enemy_manager.get_active_enemies():
            while enemy.alive:
                enemy.take_damage(9999)
        step(1)
        guard += 1
    report("post-midboss-end")
    assert stage.phase == "dialogue", stage.phase
    assert stage.dialogue_target == "final", stage.dialogue_target
    assert stage.boss is not None and stage.boss.alive
    assert not stage.boss.combat_enabled, "对话期间 Barry 不应开打"
    assert not stage.boss.spell_cards, "Ex 面关底Boss 暂不配符卡"
    print("      Barry 登场：%d 句对话" % len(stage.dialogue_lines))
    shot("barry_dialogue")

    # ------------------------------------------------------ Barry 战（无符卡）
    print("[4] Barry 战（暂不配符卡，全程非符）")
    stage.on_dialogue_end()
    assert stage.phase == "boss", stage.phase
    step(6 * 60)
    assert stage.boss.combat_enabled
    assert stage.boss.current_spell is None
    report("barry-6s")
    shot("barry_fight")
    for _ in range(40 * 60):
        assert stage.boss.current_spell is None, "Ex 面关底Boss 不应开符卡"
        stage.boss.take_damage(120)
        step(1)
        if stage.boss.hp <= 0:
            break
    report("barry-low-hp")
    shot("barry_fight_late")
    while stage.boss.alive:
        stage.boss.take_damage(900)
        step(1)
    step(2)
    assert stage.phase == "defeat_dialogue", stage.phase
    assert stage.defeat_dialogue_lines, "关底Boss 必须有战后对话"
    print("      Barry 击破：%d 句战后对话" % len(stage.defeat_dialogue_lines))
    shot("barry_defeat_dialogue")

    # -------------------------------------------------------------- 通关
    stage.on_defeat_dialogue_end()
    assert stage.phase == "cleared", stage.phase
    assert stage.is_cleared()
    report("cleared")
    print("ALL OK")


if __name__ == "__main__":
    main()
