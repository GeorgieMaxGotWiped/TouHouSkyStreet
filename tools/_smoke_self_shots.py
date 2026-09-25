# 自机弹幕端到端冒烟：四位自机各打 600 帧第一面 Boss，核对能正常开火 / 命中 / 结算
# （配合 tools/_verify_shots.py 的离线逐发比对：那份管「发出来的弹对不对」，
#   这份管「真打起来不炸、伤害量级合理」）。
#
# 用法：python tools/_smoke_self_shots.py
import os
import random
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding="utf-8")

import pygame  # noqa: E402

pygame.init()
from src.engine import game as game_module  # noqa: E402

_orig = game_module.load_user_config
game_module.load_user_config = lambda: dict(_orig(), fullscreen=False,
                                            render_scale_index=0, game_speed=1.0)
game = game_module.Game()

from src.stages.stage1 import Stage1_SkyblockHub  # noqa: E402
from src.ui.menu import PlayingState  # noqa: E402

FRAMES = 600        # 10 秒满火力输出
NAMES = {"frozen_blaze": "冰焰", "mage": "魔法使", "archer": "弓手", "tank": "重装"}
PIERCE = {"frozen_blaze": False, "mage": True, "archer": False, "tank": False}


def run(character):
    game.set_player_character(character)
    stage = Stage1_SkyblockHub()
    state = PlayingState(game, stage)
    game.push_state(state)
    # 直接把第一面推到关底 Boss 战：正常时间轴要几十秒才到，测自机弹不用等
    stage.setup_boss()
    stage.phase = "boss"
    boss = stage.boss
    boss.entering = False
    boss.invincible = False
    boss.combat_enabled = True
    boss.phase = "non_spell"
    state.power = 400                    # 满火力：弹条数拉满
    game.keys_held = {pygame.K_z: True}
    game.keys_just_pressed = {}
    hp0 = boss.hp
    peak = 0
    for _ in range(FRAMES):
        state.update(1 / 60.0)
        peak = max(peak, len(state.bullet_manager.player_bullets))
    game.pop_state()
    return hp0 - boss.hp, peak, state


failures = []
# 固定随机种子：Boss 的弹幕与移动都吃随机数，不种种子的话同一位自机每次跑出来的
# 秒伤能差三成（弹幕把自机弹挡掉多少全看运气），这个数字就没法拿来做横向对比了
random.seed(20260925)
for character in ("frozen_blaze", "mage", "archer", "tank"):
    damage, peak, state = run(character)
    flags = {bullet.pierce for bullet in state.bullet_manager.player_bullets}
    ok = damage > 0 and flags == {PIERCE[character]}
    print(f"{'OK  ' if ok else 'FAIL'} {NAMES[character]}({character}): "
          f"10 秒伤害 {damage:.0f} / 玩家弹峰值 {peak} / 穿透标记 {flags}")
    if not ok:
        failures.append(character)

if failures:
    print(f"失败：{'、'.join(NAMES[key] for key in failures)}")
    sys.exit(1)
print("冒烟通过")
