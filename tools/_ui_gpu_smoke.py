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
    if name == "menu":
        return MenuState(game)
    if name == "settings":
        return SettingsState(game)
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
    raise SystemExit("unknown screen " + name)


SCREENS = ("menu", "settings", "difficulty", "storage", "shop", "forge", "loadout")


def run(mode):
    original = game_module.load_user_config
    game_module.load_user_config = lambda: dict(original(), fullscreen=False)
    painter.set_enabled(mode == "after")
    results = []
    for name in SCREENS:
        try:
            game = game_module.Game()
            game.push_state(build(game, name))
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
