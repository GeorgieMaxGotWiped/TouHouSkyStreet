# -*- coding: utf-8 -*-
"""导出物品图鉴数据到 web/data/items.json

用法（在项目根目录执行）：
    python web/tools/export_items.py

产物：web/data/items.json，包含 meta 信息与全部物品条目，
供 web/items.html 用前端渲染，避免每次改游戏物品都要改网页。
"""
import json
import os
import sys

# 让 `src` 成为可导入包：脚本位于 web/tools/，项目根为上级两级
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.systems.item_system import (      # noqa: E402
    SKYBLOCK_ITEMS,
    ITEM_TYPE_LABELS,
    SLOT_LABELS,
    EQUIPMENT_SLOTS,
)
from src.engine import settings as cfg       # noqa: E402

# 罕见度排序（普通 -> 极稀有）
RARITY_ORDER = [
    "COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY",
    "MYTHIC", "DIVINE", "SPECIAL", "VERY_SPECIAL",
]


def _rgb_to_hex(rgb):
    try:
        r, g, b = rgb[:3]
        return "#%02x%02x%02x" % (int(r), int(g), int(b))
    except Exception:
        return "#888888"


def main():
    items = []
    for item in SKYBLOCK_ITEMS.values():
        entry = {
            "id": item.id,
            "name": item.name,
            "rarity": item.rarity,
            "rarity_label": item.rarity.capitalize(),
            "rarity_color": _rgb_to_hex(cfg.RARITY_COLORS.get(item.rarity, (136, 136, 136))),
            "item_type": item.item_type,
            "type_label": ITEM_TYPE_LABELS.get(item.item_type, item.item_type),
            "slot": item.slot,
            "slot_label": SLOT_LABELS.get(item.slot, item.slot),
            "equippable": item.is_equippable,
            "can_reforge": item.can_reforge,
            "stats": dict(item.stats or {}),
            "effects": dict(item.effects or {}),
            "lore": list(item.lore or []),
            "buy_price": item.buy_price,
            "sell_price": item.sell_price,
            "image": "../assets/items/%s.png" % item.id,
        }
        items.append(entry)

    def sort_key(e):
        rarity_idx = RARITY_ORDER.index(e["rarity"]) if e["rarity"] in RARITY_ORDER else len(RARITY_ORDER)
        return (rarity_idx, e["item_type"], e["name"].lower())

    items.sort(key=sort_key)

    meta = {
        "project": "东方天空街 ~ Touhou Sky Street",
        "count": len(items),
        "rarities": [{"id": r, "label": r.capitalize(),
                      "color": _rgb_to_hex(cfg.RARITY_COLORS.get(r, (136, 136, 136)))} for r in RARITY_ORDER],
        "types": [{"id": k, "label": v} for k, v in ITEM_TYPE_LABELS.items()],
    }

    out_path = os.path.join(ROOT, "web", "data", "items.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump({"meta": meta, "items": items}, f, ensure_ascii=False, indent=2)

    print("已导出 %d 件物品 -> %s" % (len(items), out_path))


if __name__ == "__main__":
    main()

