# 本地仓库：跨远征持久化的物资存档
# 撤离时把本局物品/金币合并入仓库；出征前可从仓库挑选携带物资。

import os
import json
from src.engine import settings as cfg
from src.systems.item_system import ItemInventory


def load_warehouse():
    """读取本地仓库；文件缺失或损坏时返回空仓库。"""
    inventory = ItemInventory()
    try:
        if os.path.exists(cfg.WAREHOUSE_PATH):
            with open(cfg.WAREHOUSE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                inventory = ItemInventory.from_global_data(data)
    except Exception as exc:
        print(f"[Warehouse] Failed to load {cfg.WAREHOUSE_PATH}: {exc}")
    return inventory


def save_warehouse(inventory):
    """把仓库写入本地文件。"""
    try:
        with open(cfg.WAREHOUSE_PATH, "w", encoding="utf-8") as f:
            json.dump(inventory.to_data(), f, ensure_ascii=False, indent=2)
    except Exception as exc:
        print(f"[Warehouse] Failed to save {cfg.WAREHOUSE_PATH}: {exc}")
