# -*- coding: utf-8 -*-
# 对话立绘排版预览：把各面对白渲染成 previews/_dialogue_<label>.png。
#
# 用途：肉眼核对「同屏立绘之间的相对大小」是否协调 —— 对话框只把立绘按内容高度
# 归一化，所以同屏的两张图各自「人物占画面多少」一旦差得多，看起来就会一大一小。
#
# 用法：
#   python tools\_dialogue_preview.py           # 全部
#   python tools\_dialogue_preview.py s5 ex     # 只跑标签含 s5 / ex 的
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pygame

from src.engine import game as game_module
from src.engine import settings as cfg

OUT_DIR = os.path.join(os.getcwd(), "previews")
DT = 1.0 / cfg.FPS


def _case_stage1(stage):
    stage.setup_waves()
    stage._start_dialogue()


def _case_stage2(stage):
    stage.setup_waves()
    stage._start_dialogue()


def _case_stage3(stage):
    stage.setup_waves()
    stage._start_dialogue()


def _case_stage4(stage):
    stage.setup_waves()
    stage._start_dialogue()


def _case_stage5_watcher(stage):
    stage.setup_waves()
    stage._start_opening_dialogue()


def _summon_case(boss_id):
    def prep(stage):
        stage.setup_waves()
        stage._start_summon_dialogue(boss_id)
    return prep


def _case_stage5_necron(stage):
    stage.setup_waves()
    stage._start_final_dialogue()


def _case_stage6_kaeman(stage):
    stage.setup_waves()
    stage._start_final_dialogue()


def _case_ex_wizardman(stage):
    stage.setup_waves()
    stage._begin_mid_boss()


def _case_ex_barry(stage):
    stage.setup_waves()
    stage._start_dialogue()


def cases():
    from src.stages.stage1 import Stage1_SkyblockHub
    from src.stages.stage2 import Stage2_DragonsNest
    from src.stages.stage3 import Stage3_CatacombsF1
    from src.stages.stage4 import Stage4_Catacombs
    from src.stages.stage5 import Stage5_WitherLords
    from src.stages.stage6 import Stage6_FinalApproach
    from src.stages.stage_ex import ExtraStageTheRift

    return [
        ("s1_arachne", Stage1_SkyblockHub, _case_stage1),
        ("s2_dragon", Stage2_DragonsNest, _case_stage2),
        ("s3_bonzo", Stage3_CatacombsF1, _case_stage3),
        ("s4_sadan", Stage4_Catacombs, _case_stage4),
        ("s5_watcher", Stage5_WitherLords, _case_stage5_watcher),
        ("s5_professor", Stage5_WitherLords, _summon_case("professor")),
        ("s5_thorn", Stage5_WitherLords, _summon_case("thorn")),
        ("s5_livid", Stage5_WitherLords, _summon_case("livid")),
        ("s5_maxor", Stage5_WitherLords, lambda s: (s.setup_waves(),
                                                    s._start_maxor_dialogue())),
        ("s5_necron", Stage5_WitherLords, _case_stage5_necron),
        ("s6_kaeman", Stage6_FinalApproach, _case_stage6_kaeman),
        ("ex_wizardman", ExtraStageTheRift, _case_ex_wizardman),
        ("ex_barry", ExtraStageTheRift, _case_ex_barry),
    ]


def main():
    wanted = [arg.lower() for arg in sys.argv[1:]]
    pygame.init()
    original_config = game_module.load_user_config
    game_module.load_user_config = lambda: dict(original_config(), fullscreen=False)
    game = game_module.Game()
    from src.ui.menu import PlayingState

    print("[cfg] 自机=%s Boss 套组=%s 渲染倍率=%dx" % (
        cfg.get_player_character(), cfg.get_boss_art(), game.render_scale))
    os.makedirs(OUT_DIR, exist_ok=True)

    for label, factory, prep in cases():
        if wanted and not any(w in label for w in wanted):
            continue
        stage = factory()
        prep(stage)
        assert stage.dialogue_active and stage.dialogue_portraits, label
        state = PlayingState(game, stage, skip_title=True)
        game.push_state(state)
        game._update_present_rect()
        for _ in range(90):
            state.update(DT)
            game._draw()
        assert state.dialogue is not None, "%s: 对话框没起来" % label
        surface = game.screen
        if game.presenter is not None:
            try:
                surface = game.presenter.renderer.to_surface()
            except Exception as exc:
                print("      presenter readback failed: %s" % exc)
        path = os.path.join(OUT_DIR, "_dialogue_%s.png" % label)
        pygame.image.save(surface, path)
        names = " / ".join(state.dialogue.portraits.keys())
        print("%-14s 说话者=%-16s 同屏=%s" % (
            label, state.dialogue.lines[0][0], names))
        game.pop_state()

    pygame.quit()
    print("OK")


if __name__ == "__main__":
    main()
