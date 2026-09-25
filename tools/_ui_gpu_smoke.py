# -*- coding: utf-8 -*-
# 界面绘制冒烟：把各个界面在「显卡路径 关 / 开」两种模式下各画一帧，报告异常与指令数。
# 用法：python tools\_ui_gpu_smoke.py [界面] [before|after] [输出png]
#   给了第 3 个参数就把显卡上真正呈现的那一帧读回存成 PNG（同目录另存一张 960 宽的 _view_ 版）
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"
sys.path.insert(0, os.getcwd())

import pygame
from src.engine import painter
from src.engine import game as game_module

MODE_ARGS = ("before", "after")


def build(game, name):
    from src.ui.menu import MenuState, SettingsState
    from src.ui.storage import StorageState
    from src.ui.intermission import IntermissionState
    from src.ui.loadout import LoadoutState
    from src.ui.difficulty import DifficultySelectState
    from src.ui.character_select import CharacterSelectState
    if name == "menu":
        return MenuState(game)
    if name == "settings":
        return SettingsState(game)
    if name == "character":
        return CharacterSelectState(game)
    if name == "difficulty":
        return DifficultySelectState(game)
    if name == "storage":
        return StorageState(game)
    if name == "shop":
        st = IntermissionState(game, 1)
        st.page_idx = 2
        return st
    if name == "forge":
        st = StorageState(game)
        st.page_idx = 1
        return st
    if name == "loadout":
        return LoadoutState(game)
    if name == "prep":
        # 出发前休整：从携带界面确认之后进入的就是这个界面（pre_start=True）
        return IntermissionState(game, 0, pre_start=True)
    if name == "practice":
        from src.ui.practice import PracticeSelectState
        return PracticeSelectState(game)
    if name in ("boss_reward", "reward_confirm"):
        from src.ui.boss_reward import BossRewardState
        from src.systems.item_system import BOSS_REWARD_POOLS
        import random
        # 战利品是从池子里随机抽 3 件：固定种子，好让「改前 / 改后」两张图
        # 抽到同一批、同一顺序，对比才有意义
        random.seed(20260913)
        stage_num = 1 if name == "boss_reward" else 5
        return BossRewardState(game, stage_num, list(BOSS_REWARD_POOLS[stage_num]))
    if name == "loading":
        from src.ui.loading import LoadingState

        def task(loading):
            loading.title = "第 1 面"
            loading.subtitle = "天空街 Skyblock Hub"
            yield 0.1, "构建关卡数据…"
            yield 0.55, "载入贴图 弹幕贴图"
            yield 0.9, "载入 Boss 立绘 1/2"
        return LoadingState(game, task)
    raise SystemExit("unknown screen " + name)


SCREENS = ("menu", "settings", "difficulty", "storage", "shop", "forge", "loadout",
           "prep", "practice", "boss_reward", "reward_confirm", "loading", "character")


def run(mode):
    original = game_module.load_user_config
    game_module.load_user_config = lambda: dict(original(), fullscreen=False)
    painter.set_enabled(mode == "after")
    results = []
    for name in SCREENS:
        try:
            game = game_module.Game()
            game.push_state(build(game, name))
            game.settle_ui()   # 黑场过渡 + 进场动效走完，拍到的是落定后的画面
            from pygame._sdl2 import video as video_module
            video_module.Window.from_display_module().size = (1920, 1440)
            game._update_present_rect()
            game.screen.cache.clear()
            for _ in range(2):
                game._draw()
            results.append((name, len(game.screen.gpu.ops), None))
            game.running = False
            del game
        except Exception as e:
            import traceback
            results.append((name, -1, traceback.format_exc(limit=3)))
        # 同一个进程里反复重建窗口不可靠：每个界面单开一个进程
        break
    return results


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else SCREENS[0]
    mode = sys.argv[2] if len(sys.argv) > 2 else "after"
    pygame.init()
    original = game_module.load_user_config
    game_module.load_user_config = lambda: dict(original(), fullscreen=False)
    painter.set_enabled(mode == "after")
    game = game_module.Game()
    game.push_state(build(game, name))
    game.settle_ui()      # 黑场过渡 + 进场动效走完，拍到的是落定后的画面
    if name == "reward_confirm":
        # 顺带把「确认领取」的弹窗（半透明遮罩 + 弹窗）也画出来；
        # 只能在 enter() 之后设置——enter() 本身会把弹窗重置掉
        game.current_state.selected = 1
        game.current_state.confirming = True
    from pygame._sdl2 import video as video_module
    video_module.Window.from_display_module().size = (1920, 1440)
    game._update_present_rect()
    game.screen.cache.clear()
    for _ in range(2):
        game._draw()
    print(f"[smoke] {name:<11} mode={mode:<6} ok  gpu_ops={len(game.screen.gpu.ops)}")

    if len(sys.argv) > 3:
        save_shot(game, sys.argv[3])

    game.running = False
    pygame.quit()


def save_shot(game, path):
    """把显卡上真正呈现出来的那一帧读回并存成 PNG（另存一张缩小版便于查看）"""
    if game.presenter is None:
        raise SystemExit("GPU presenter unavailable; nothing to read back")
    surface = game.presenter.renderer.to_surface()
    path = os.path.abspath(path)
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    pygame.image.save(surface, path)
    w, h = surface.get_size()
    view = pygame.transform.smoothscale(surface, (960, int(round(960 * h / float(w)))))
    view_path = os.path.join(parent, "_view_" + os.path.basename(path))
    pygame.image.save(view, view_path)
    print(f"[smoke] saved {path} {w}x{h}  ->  {view_path}")


if __name__ == "__main__":
    main()
