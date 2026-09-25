# -*- coding: utf-8 -*-
# 开符基准：把关卡推到关底 Boss，逐张符卡量「普通帧 / 横幅期 / 符卡后期」的帧时间。
#
# 用法：python tools\_bench_spellcard.py [关卡] [渲染倍率] [每张符卡帧数] [张数]
#   关卡：stage1 / stage2 / stage3 / stage4 / stage5 / stage6（默认 stage6）
#   渲染倍率：1 / 2 / 3 / 4（默认 3，即 2880x2160 窗口）
#
# 它先走一遍载入界面那套预热（符卡背景 / 横幅立绘 / 符卡贴图 / 符卡演出特效），
# 所以量到的是玩家真实开符时的帧时间，而不是「预热前」的数字。
#
# 默认走真实显示驱动（显卡呈现路径），因为那条路才是玩家跑的；纯软件回退路径
# 慢一个数量级，只适合查正确性，不适合当基准——要跑它设 PROBE_DUMMY=1。
import os
import sys
import time
import importlib
import statistics

os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
if os.environ.get("PROBE_DUMMY") == "1":
    os.environ["SDL_VIDEODRIVER"] = "dummy"
else:
    os.environ["SDL_VIDEODRIVER"] = "windows"
sys.path.insert(0, os.getcwd())

import pygame

from src.engine import game as game_module

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

STAGES = {
    "stage1": ("src.stages.stage1", "Stage1_SkyblockHub"),
    "stage2": ("src.stages.stage2", "Stage2_DragonsNest"),
    "stage3": ("src.stages.stage3", "Stage3_CatacombsF1"),
    "stage4": ("src.stages.stage4", "Stage4_Catacombs"),
    "stage5": ("src.stages.stage5", "Stage5_WitherLords"),
    "stage6": ("src.stages.stage6", "Stage6_FinalApproach"),
}

# 五面是 BOSS RUSH：setup_boss 是空实现，Boss 由对话动作延迟生成，
# 这里直接走工厂拿关底的那位（Necron）当基准对象。
RUSH_BOSS = {"stage5": "necron"}

BUDGET_MS = 1000.0 / 60.0


def stat(xs):
    xs = sorted(xs)
    over = sum(1 for x in xs if x > BUDGET_MS)
    return (f"中位 {statistics.median(xs):5.2f}  最小 {xs[0]:5.2f}  最大 {xs[-1]:6.2f}  "
            f"超 16.7ms {over:>3}/{len(xs)}")


def build(game, stage_name, scale):
    module_name, class_name = STAGES[stage_name]
    module = importlib.import_module(module_name)
    stage = getattr(module, class_name)()
    from src.ui.menu import PlayingState
    from src.ui import loading

    state = PlayingState(game, stage)
    game.push_state(state)
    game._update_present_rect()
    boss_id = RUSH_BOSS.get(stage_name)
    if boss_id:
        stage._spawn_boss_for_dialogue(boss_id)
    else:
        stage.setup_boss()
    stage.phase = "boss"
    stage.timer = 0
    boss = stage.boss
    boss.arm_combat(0)
    boss.entering = False
    boss.entry_timer = 0

    # 载入界面那套预热（顺序与 ui/loading.py 的 _collect_assets 一致）
    t0 = time.perf_counter()
    loading._warm_spell_bg(stage)
    loading._warm_spell_banner(stage, game)
    loading._warm_spell_sprites(stage)
    loading._warm_spell_effects(stage)
    loading._warm_bullet_sprite()
    warm_ms = (time.perf_counter() - t0) * 1000
    return state, stage, boss, warm_ms


def main():
    stage_name = sys.argv[1] if len(sys.argv) > 1 else "stage6"
    scale = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    frames = int(sys.argv[3]) if len(sys.argv) > 3 else 200
    cards = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    if stage_name not in STAGES:
        print(f"未知关卡 {stage_name}，可选：{' / '.join(STAGES)}")
        return 1

    orig = game_module.load_user_config
    game_module.load_user_config = lambda: dict(orig(), fullscreen=False,
                                                render_scale_index=scale - 1)
    pygame.init()
    game = game_module.Game()
    from pygame._sdl2 import video as video_module
    video_module.Window.from_display_module().size = (960 * scale, 720 * scale)

    state, stage, boss, warm_ms = build(game, stage_name, scale)
    # 探针里的自机站着不动，命中判定一开就会死，死后整屏 GAME OVER 遮罩会盖住
    # 真正要量的东西（7.9ms/帧），所以直接关掉判定。
    from src.entities import player as player_module
    player_module.Player.can_be_hit = lambda self: False

    dt = 1.0 / 60.0

    def frame():
        t0 = time.perf_counter()
        state.update(dt)
        t1 = time.perf_counter()
        game._draw()
        t2 = time.perf_counter()
        return (t1 - t0) * 1000, (t2 - t1) * 1000

    for _ in range(150):
        frame()
    base = [sum(frame()) for _ in range(60)]

    print(f"\n===== 开符基准 {stage_name} 渲染倍率 {scale}x "
          f"presenter={'有' if game.presenter is not None else '无'} "
          f"载入预热 {warm_ms:.1f}ms =====")
    print(f"  普通帧      : {stat(base)}")
    for ci, card in enumerate(list(boss.spell_cards or [])[:cards]):
        boss.current_spell_idx = ci
        t0 = time.perf_counter()
        boss._start_spell(card)
        decl = (time.perf_counter() - t0) * 1000
        rows = [sum(frame()) for _ in range(frames)]
        print(f"  符{ci}「{getattr(card, 'name', '?')}」声明 {decl:.2f}ms")
        print(f"    横幅期(2-100): {stat(rows[1:100])}")
        if len(rows) > 101:
            print(f"    符卡后期(101+): {stat(rows[101:])}")
        worst = sorted(range(len(rows)), key=lambda i: -rows[i])[:5]
        print("    最慢 5 帧   : " + ", ".join(f"第{i + 1}帧={rows[i]:.1f}ms" for i in worst))
        boss._end_spell()
        for _ in range(40):
            frame()

    game.running = False
    pygame.quit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
