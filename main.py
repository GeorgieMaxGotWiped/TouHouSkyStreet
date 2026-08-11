# 东方天空街 ~ Touhou Sky Street
# 基于 Hypixel Skyblock 的东方Project同人STG
# 入口文件

import sys
import os

# 确保项目根目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.engine.game import Game
from src.engine import settings as cfg
from src.ui.menu import MenuState


def main():
    game = Game()

    # 如有命令行参数，可以调整难度等
    if len(sys.argv) > 1:
        if sys.argv[1].lower() in ("easy", "normal", "hard", "lunatic"):
            game.global_data["difficulty"] = sys.argv[1].upper()

    game.push_state(MenuState(game))
    game.run()


if __name__ == "__main__":
    main()
