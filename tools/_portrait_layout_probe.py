# -*- coding: utf-8 -*-
"""量对话里每张立绘的实际落位：屏幕 x 区间、可见高度、头高（逻辑像素）。

用来判断「同屏两张会不会互相压住」以及「各人物看起来是不是一样大」。
"""
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

CASES = [
    ("s1_arachne", "stage1", lambda s: (s.setup_waves(), s._start_dialogue())),
    ("s2_dragon", "stage2", lambda s: (s.setup_waves(), s._start_dialogue())),
    ("s3_bonzo", "stage3", lambda s: (s.setup_waves(), s._start_dialogue())),
    ("s4_sadan", "stage4", lambda s: (s.setup_waves(), s._start_dialogue())),
    ("s5_watcher", "stage5", lambda s: (s.setup_waves(), s._start_opening_dialogue())),
    ("s5_professor", "stage5", lambda s: (s.setup_waves(), s._start_summon_dialogue("professor"))),
    ("s5_thorn", "stage5", lambda s: (s.setup_waves(), s._start_summon_dialogue("thorn"))),
    ("s5_livid", "stage5", lambda s: (s.setup_waves(), s._start_summon_dialogue("livid"))),
    ("s5_maxor", "stage5", lambda s: (s.setup_waves(), s._start_maxor_dialogue())),
    ("s5_necron", "stage5", lambda s: (s.setup_waves(), s._start_final_dialogue())),
    ("s6_kaeman", "stage6", lambda s: (s.setup_waves(), s._start_final_dialogue())),
    ("ex_wizardman", "ex", lambda s: (s.setup_waves(), s._begin_mid_boss())),
    ("ex_barry", "ex", lambda s: (s.setup_waves(), s._start_dialogue())),
]


def factories():
    from src.stages.stage1 import Stage1_SkyblockHub
    from src.stages.stage2 import Stage2_DragonsNest
    from src.stages.stage3 import Stage3_CatacombsF1
    from src.stages.stage4 import Stage4_Catacombs
    from src.stages.stage5 import Stage5_WitherLords
    from src.stages.stage6 import Stage6_FinalApproach
    from src.stages.stage_ex import ExtraStageTheRift
    return {"stage1": Stage1_SkyblockHub, "stage2": Stage2_DragonsNest,
            "stage3": Stage3_CatacombsF1, "stage4": Stage4_Catacombs,
            "stage5": Stage5_WitherLords, "stage6": Stage6_FinalApproach,
            "ex": ExtraStageTheRift}


def main():
    pygame.init()
    original = game_module.load_user_config
    game_module.load_user_config = lambda: dict(original(), fullscreen=False)
    game = game_module.Game()
    from src.ui.menu import PlayingState

    table = factories()
    band = cfg.BATTLE_OFFSET_X + 12
    span = cfg.BATTLE_AREA_WIDTH - 24
    print("战斗区可视横向 %d .. %d（宽 %d）" % (band, band + span, span))
    for label, key, prep in CASES:
        stage = table[key]()
        prep(stage)
        state = PlayingState(game, stage, skip_title=True)
        game.push_state(state)
        state.update(1.0 / cfg.FPS)
        box = state.dialogue
        assert box is not None and box.portraits, label
        from src.ui.dialogue import get_portrait
        print("\n%s  (harmonize=%s)" % (label, box.harmonize))
        edges = []
        for name, path in box.portraits.items():
            sprite, (bl, br, ctop) = get_portrait(path, box.portrait_scales.get(name, 1.0),
                                                  harmonize=box.harmonize)
            if sprite is None:
                continue
            w, h = sprite.get_size()
            side = box.portrait_sides.get(name)
            if side is None:
                side = "left" if path == cfg.SELF_SPRITE else "right"
            off = box.portrait_offsets.get(name, 0)
            if side == "left":
                px = band - bl
            else:
                px = band + span - br + off
            visible = band + span - px if side == "left" else px + w
            ratio = cfg.dialogue_portrait_head_ratio(path)
            head = (h * ratio) if ratio else 0.0
            print("   %-22s side=%-5s 外框 x=%4d..%4d  内容 x=%4d..%4d  显示高=%3d 头高=%5.1f%s"
                  % (name, side, px, px + w, px + bl, px + br, h, head,
                     "" if ratio else "  (未登记)"))
            edges.append((px + bl, px + br))
        if len(edges) == 2:
            (a0, a1), (b0, b1) = edges
            overlap = min(a1, b1) - max(a0, b0)
            print("   -> 内容重叠 = %d px（负值=中间留白）" % overlap)
        game.pop_state()
    pygame.quit()


if __name__ == "__main__":
    main()
