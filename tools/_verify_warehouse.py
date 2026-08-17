# -*- coding: utf-8 -*-
# 本地仓库 / 出征准备 / 撤离功能验证
# 使用临时仓库文件，避免污染用户存档
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
import sys
import shutil
import tempfile

sys.path.insert(0, os.getcwd())
from src.engine import settings as cfg

tmpdir = tempfile.mkdtemp(prefix="wh_test_")
cfg.WAREHOUSE_PATH = os.path.join(tmpdir, "warehouse.json")

from src.systems.item_system import ItemInventory
from src.systems.warehouse import load_warehouse, save_warehouse

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
os.makedirs("previews", exist_ok=True)

# --- 1. 仓库读写往返 ---
wh = ItemInventory()
wh.add_item("undead_sword", 2)
wh.add_item("hyperion", 1)
wh.add_coins(5000)
wh.applied_reforges["hyperion"] = "fabled"
save_warehouse(wh)
wh2 = load_warehouse()
assert wh2.count_item("undead_sword") == 2
assert wh2.count_item("hyperion") == 1
assert wh2.coins == 5000
assert wh2.applied_reforges.get("hyperion") == "fabled"
print("[1] warehouse roundtrip OK")

# --- 2. 撤离合并（merge_from） ---
run = ItemInventory()
run.add_item("aspect_of_the_jerry", 3)
run.add_coins(1200)
run.applied_reforges["aspect_of_the_jerry"] = "necrotic"
wh2.merge_from(run)
assert wh2.count_item("aspect_of_the_jerry") == 3
assert wh2.coins == 6200
assert wh2.applied_reforges.get("aspect_of_the_jerry") == "necrotic"
save_warehouse(wh2)
print("[2] merge_from OK")

# --- 3. 出征准备：携带物品与金币，扣减仓库并写入本局背包 ---
from src.engine.game import Game
from src.ui.loadout import LoadoutState

g = Game()
st = LoadoutState(g)
st.carried["hyperion"] = 1
st.carried["undead_sword"] = 1
st.carried_coins = 300
st.draw(screen)
pygame.image.save(screen, os.path.join("previews", "_loadout_preview.png"))
st._start_run()

assert g.global_data["coins"] == 300
assert g.global_data["inventory"] == [
    {"id": "hyperion", "count": 1},
    {"id": "undead_sword", "count": 1},
]
assert g.global_data["reforges"] == {"hyperion": "fabled"}
assert g.global_data["lives"] == cfg.PLAYER_START_LIVES
assert g.global_data["power"] == 0

wh3 = load_warehouse()
assert wh3.count_item("hyperion") == 0
assert wh3.count_item("undead_sword") == 1
assert wh3.count_item("aspect_of_the_jerry") == 3
assert wh3.coins == 5900  # 6200 - 300 携带
assert wh3.applied_reforges.get("hyperion") is None      # 前缀随物品带走
assert wh3.applied_reforges.get("aspect_of_the_jerry") == "necrotic"
print("[3] loadout start OK")

# --- 4. 休整撤离：本局物资合并入仓库并返回主菜单 ---
from src.ui.intermission import IntermissionState
from src.ui.menu import MenuState

g2 = Game()
inv = ItemInventory()
inv.add_item("giants_sword", 1)
inv.add_coins(999)
inv.save_to_global_data(g2.global_data)
it = IntermissionState(g2, 1)
it._extract()
wh4 = load_warehouse()
assert wh4.count_item("giants_sword") == 1
assert wh4.coins == 5900 + 999
assert isinstance(g2.current_state, MenuState)
assert getattr(g2, "notice", None) == "已撤离：本局物资已存入仓库"
print("[4] intermission extract OK")

# --- 5. UI 渲染冒烟：主菜单提示 / 休整界面 ---
g2.current_state.draw(screen)
pygame.image.save(screen, os.path.join("previews", "_menu_notice_preview.png"))
it2 = IntermissionState(g2, 1)
it2.draw(screen)
pygame.image.save(screen, os.path.join("previews", "_intermission_preview.png"))
print("[5] UI render smoke OK")

pygame.quit()
shutil.rmtree(tmpdir, ignore_errors=True)
print("ALL WAREHOUSE TESTS PASSED")
