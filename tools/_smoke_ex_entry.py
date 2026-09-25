# -*- coding: utf-8 -*-
# Ex 面入口冒烟：主菜单「Extra Stage」-> 选自机 -> 选难度 -> 载入 -> 战斗。
#
# 顺带把 Ex 面的三条硬规矩钉住：
#   1) 不进仓库 / 携带 / 出装界面（选完难度直接开打）；
#   2) 局内装备物品效果一律不生效（无 C 技能、无掉落、无物品被动）；
#   3) 通关后回主菜单（不进休整 / 4 选 1 奖励）。
# 入口与战斗画面存到 previews/_stage_ex_entry_*.png，方便肉眼复核排版。
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.getcwd())

import pygame

from src.engine import game as game_module
from src.engine import painter
from src.engine import settings as cfg

OUT_DIR = os.path.join(os.getcwd(), "previews")
# 逻辑步长：直接驱动状态机时要自己给 dt（Game.dt 只在 run() 的循环里被时钟写入）
DT = 1.0 / cfg.FPS


def main():
    pygame.init()
    # 沿用用户配置，只把窗口模式固定成窗口（dummy 驱动下全屏没意义）
    original_config = game_module.load_user_config
    game_module.load_user_config = lambda: dict(original_config(), fullscreen=False)
    game = game_module.Game()

    from src.ui.menu import MenuState, PlayingState
    from src.ui.character_select import CharacterSelectState
    from src.ui.difficulty import DifficultySelectState
    from src.ui.loading import LoadingState

    visited = []
    original_switch = game.switch_state

    def switch_spy(state):
        visited.append(type(state).__name__)
        original_switch(state)

    game.switch_state = switch_spy

    def tick(keys=(), frames=1):
        for _ in range(frames):
            held = {key: True for key in keys}
            game.keys_held = dict(held)
            game.keys_just_pressed = dict(held)
            game.mouse_buttons_just_pressed = {}
            # 测试期间让自机不吃弹：这一趟只跑流程，不等玩家躲弹
            if isinstance(game.current_state, PlayingState):
                game.current_state.player.spell_invincible = True
            game.current_state.update(DT)
            game._draw()

    def shot(label):
        # 进场动效（错位淡入）走完再拍：否则刚切过去那一帧的元素还没淡上来
        game.settle_ui()
        game._draw()
        os.makedirs(OUT_DIR, exist_ok=True)
        path = os.path.join(OUT_DIR, "_stage_ex_entry_%s.png" % label)
        # 存显卡上真正呈现的那一帧：高分辨率图层（文字）与显卡指令都在里面，
        # 直接存画布会漏掉这些，复核时就看不到对话框 / HUD
        surface = None
        if game.presenter is not None:
            try:
                surface = game.presenter.renderer.to_surface()
            except Exception as exc:
                print("      presenter readback failed: %s" % exc)
        pygame.image.save(surface if surface is not None else game.screen, path)
        print("      saved %s" % os.path.basename(path))

    print("[1] 主菜单 -> Extra Stage -> 自机选择")
    menu = MenuState(game)
    game.switch_state(menu)
    assert "Extra Stage" in menu.options, menu.options
    tick([pygame.K_DOWN])
    assert menu.options[menu.selected] == "Extra Stage", menu.selected
    tick([pygame.K_RETURN])
    assert isinstance(game.current_state, CharacterSelectState), type(game.current_state)
    assert game.current_state.extra is True, "extra 标记要一路传到难度界面"
    shot("01_character")

    print("[2] 自机 -> 难度选择")
    tick([pygame.K_RETURN])
    assert isinstance(game.current_state, DifficultySelectState), type(game.current_state)
    assert game.current_state.extra is True
    shot("02_difficulty")

    print("[3] 难度 -> 直接载入 Ex 面")
    tick([pygame.K_RETURN])
    loading = game.current_state
    assert isinstance(loading, LoadingState), type(loading)
    assert "LoadoutState" not in visited, "Ex 面不能进携带/出装界面：%s" % visited
    assert "StorageState" not in visited, "Ex 面不能进仓库界面：%s" % visited
    assert loading.title == "Extra Stage", loading.title
    shot("03_loading")

    for _ in range(900):
        tick([pygame.K_RETURN])
        if isinstance(game.current_state, PlayingState):
            break
    ps = game.current_state
    assert isinstance(ps, PlayingState), type(ps)
    assert ps.stage.stage_num == cfg.EX_STAGE_NUM, ps.stage.stage_num
    assert ps.stage.name == cfg.EX_STAGE_NAME, ps.stage.name
    assert ps.item_free is True, "Ex 面必须走「无装备物品效果」分支"
    assert ps.c_skill_id is None, "Ex 面不应有 C 技能"
    assert ps.power == cfg.EX_STAGE_START_POWER, ps.power

    eff = ps.item_effects
    assert eff["drop_rate_mult"] == 1.0 and eff["epic_drop_rate_mult"] == 1.0, eff
    assert eff["damage_pct"] == 0.0 and eff["hitbox_scale"] == 1.0, eff

    print("[4] 局内：击破小怪不产生任何装备掉落")
    from src.entities.enemy import Enemy
    victim = Enemy(288.0, 120.0, hp=1, score=1200, size=12)
    score_before = ps.score
    inv_before = ps.item_inventory.to_data()
    ps._reward_enemy_kill(victim)
    assert ps.score == score_before + 1200, ps.score
    assert ps.item_popups == [], "Ex 面击破敌人不应弹出装备掉落"
    assert ps.item_inventory.to_data() == inv_before, "Ex 面不应改动仓库（金币 / 物品）"
    print("      score=%d popups=%d coins=%d" % (
        ps.score, len(ps.item_popups), ps.item_inventory.coins))
    tick(frames=200)   # 先让关卡标题卡淡出，画面里才看得到战斗区
    shot("04_battle_intro")

    print("[4b] Game Over 后按 R 重开：同样满火力、同样不碰仓库")
    ps.game_over = True
    tick([pygame.K_r])
    assert ps.game_over is False, "R 应当重开本局"
    assert ps.stage.stage_num == cfg.EX_STAGE_NUM, ps.stage.stage_num
    assert ps.power == cfg.EX_STAGE_START_POWER, ps.power
    assert ps.c_skill_id is None, ps.c_skill_id
    assert ps.item_inventory.to_data() == inv_before, "重开也不应改动仓库"

    print("[5] 道中Boss 对话（Wizardman）：对话框与立绘")
    from src.stages.stage_ex import MID_BOSS_APPEAR_TIME
    ps.stage.timer = MID_BOSS_APPEAR_TIME - 1
    tick(frames=4)
    assert ps.stage.phase == "dialogue", ps.stage.phase
    assert ps.dialogue is not None, "道中Boss 登场应当弹出对话框"
    tick(frames=200)   # 同上：标题卡淡出后再拍对话
    assert ps.dialogue is not None, "不按键时对话不应自动结束"
    shot("05_mid_dialogue")

    print("[6] 通关：确认后回主菜单")
    ps.ex_clear_timer = 0
    for _ in range(40):
        tick([pygame.K_RETURN])
        if isinstance(game.current_state, MenuState):
            break
    assert isinstance(game.current_state, MenuState), type(game.current_state)
    assert "通关" in (game.notice or ""), game.notice
    assert "IntermissionState" not in visited, visited
    assert "BossRewardState" not in visited, visited
    print("      switch 过的界面：%s" % " -> ".join(visited))
    print("      notice=%s" % game.notice)
    game.running = False
    pygame.quit()
    print("ALL OK")


if __name__ == "__main__":
    main()
