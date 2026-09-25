# -*- coding: utf-8 -*-
"""量同屏立绘的「视觉头高」：显示高度 x 登记头占比 = 观众看到的头有多大。

同一段对话里各人物的这个数字越接近，站在一起就越协调（取景补偿的目标）。
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
    # 可选用第一个参数切换 Boss 立绘套组（只在本进程内切，不动 config.json）
    art = sys.argv[1] if len(sys.argv) > 1 else None
    pygame.init()
    original = game_module.load_user_config
    game_module.load_user_config = lambda: dict(original(), fullscreen=False)
    game_module.Game()
    if art:
        cfg.set_boss_art(art)
    from src.ui import dialogue

    table = factories()
    print("套组=%s  目标头高 TARGET=%.3f  倍率区间=%s  宽度预算=%d" % (
        cfg.get_boss_art(), cfg.DIALOGUE_PORTRAIT_HEAD_TARGET,
        cfg.DIALOGUE_PORTRAIT_FACTOR_RANGE, cfg.DIALOGUE_PORTRAIT_MAX_WIDTH))
    for label, key, prep in CASES:
        stage = table[key]()
        prep(stage)
        harmonize = getattr(stage, "dialogue_portrait_harmonize", True)
        names = list(stage.dialogue_portraits.items())
        print("\n%s  (harmonize=%s)" % (label, harmonize))
        for name, path in names:
            scale = float(getattr(stage, "dialogue_portrait_scales", {}).get(name, 1.0))
            ratio = cfg.dialogue_portrait_head_ratio(path)
            row = []
            for mode in (False, True):
                sprite, _box = dialogue.get_portrait(path, scale, harmonize=mode)
                if sprite is None:
                    row.append("--")
                    continue
                w, h = sprite.get_size()
                head = (h * ratio) if ratio is not None else 0.0
                row.append("h=%3d w=%3d head=%5.1f" % (h, w, head))
            note = "" if ratio is None else ("  ratio=%.3f" % ratio)
            print("   %-22s before: %s  |  after: %s%s" % (name, row[0], row[1], note))
    pygame.quit()


if __name__ == "__main__":
    main()
