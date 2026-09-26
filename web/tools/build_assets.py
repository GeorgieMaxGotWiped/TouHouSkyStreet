# -*- coding: utf-8 -*-
"""为官网（web/）生成位图素材与数据。

用法（在项目根目录执行）：
    python web/tools/build_assets.py            # 全量
    python web/tools/build_assets.py shots      # 只重跑某一步

步骤名：title / stage / chara / boss / item / shots / icon / data

做的事：
  1. 首页标题画面底图  assets/backgrounds/bg_0.png  -> assets/img/title-bg.webp（两档宽度）
  2. 关卡标题卡        assets/titles/stage*.png     -> assets/img/stage/*.webp（保留透明）
  3. 自机立绘与战斗形象 assets/sprites/self/...      -> assets/chara/*.webp（保留透明）
  4. Boss 立绘         assets/sprites/bosses/<套组>/... -> assets/boss/*.webp（保留透明）
  5. 物品图标          assets/items/*.png            -> assets/item/*.webp
  6. 实机截图          previews/_*.png               -> assets/img/shot/*.webp
  7. 站点图标          assets/gui/icon.png           -> assets/img/favicon*.png
  8. 物品图鉴数据      -> data/items.json（从游戏源码导出）

本脚本只读取仓库里的原始素材，并只写入 web/ 目录，不改动游戏本体。
"""
import json
import os
import sys

from PIL import Image

WEB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT = os.path.dirname(WEB_ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

ASSETS = os.path.join(WEB_ROOT, "assets")


def _open(path):
    return Image.open(path)


def _save_webp(img, out_path, quality=86, max_w=None, max_h=None, lossless=False):
    """等比缩放后存 WebP；已在目标尺寸以内则只转码。"""
    w, h = img.size
    scale = 1.0
    if max_w and w > max_w:
        scale = min(scale, max_w / w)
    if max_h and h > max_h:
        scale = min(scale, max_h / h)
    if scale < 1.0:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    img.save(out_path, "WEBP", quality=quality, method=6, lossless=lossless)
    return img.size


def _report(label, out_path, size, src_path):
    rel = os.path.relpath(out_path, WEB_ROOT).replace("\\", "/")
    kb = os.path.getsize(out_path) / 1024
    print("  %-26s %-38s %5dx%-5d %8.1f KB   <- %s"
          % (label, rel, size[0], size[1], kb, os.path.relpath(src_path, ROOT).replace("\\", "/")))


# ---------------------------------------------------------------- 立绘归一化

# 立绘素材的画幅与取景都不统一：多数是 1024×1536，少数偏方（1200×1200 那几张），
# 人物在画布里的落位也各不一样——弓手整张偏右 85px，石守卫上下留白 38/56px、身高只有画布的 92%。
# 页面把这些图按高度缩放并排时，上面这些差别就变成「每行人物左右跳 + 个别明显偏小」。
# 所以构建时先重排一次：墨迹拉平到画布高度、底边贴齐画布底、左右居中。
# 画布尺寸保持不变，舞台页的小缩略图不会因此变小。
PORTRAIT_ALPHA_MIN = 12   # 墨迹判定阈值（0-255），低于它的按柔边/杂点处理


def _fit_portrait(src_path, alpha_min=PORTRAIT_ALPHA_MIN):
    """把立绘重排进它原有的画布：按墨迹范围拉平大小、底边对齐、水平居中。"""
    img = _open(src_path).convert("RGBA")
    w, h = img.size
    box = img.getchannel("A").point(lambda v: 255 if v > alpha_min else 0).getbbox()
    if not box:
        return img
    x0, y0, x1, y1 = box
    scale = h / float(y1 - y0)          # 让墨迹高度正好等于画布高度
    if abs(scale - 1.0) > 0.002:
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
    ink_cx = (x0 + x1) * scale / 2.0    # 缩放后墨迹的横向中心与底边
    ink_bottom = y1 * scale
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    out.paste(img, (round(w / 2.0 - ink_cx), round(h - ink_bottom)), img)
    return out


# ---------------------------------------------------------------- 1. 首页底图

def build_title():
    print("[title] 首页标题画面底图")
    src = os.path.join(ROOT, "assets", "backgrounds", "bg_0.png")
    img = _open(src).convert("RGB")
    for width, name in ((2400, "title-bg.webp"), (1200, "title-bg-1200.webp")):
        out = os.path.join(ASSETS, "img", name)
        _report("title-bg", out, _save_webp(img, out, quality=88, max_w=width), src)


# ---------------------------------------------------------------- 2. 关卡标题卡

STAGE_ART = [
    ("stage1", "stage1.png"), ("stage2", "stage2.png"), ("stage3", "stage3.png"),
    ("stage4", "stage4.png"), ("stage5", "stage5.png"), ("stage6", "stage6.png"),
    ("ex", "stage_ex.png"),
]


def build_stage():
    """关卡标题卡是「白字 + 透明底」的图形，四周留白极多。
    这里按非透明像素的包围盒裁掉空白，网页里才能按宽度正常排版。"""
    print("[stage] 关卡标题卡")
    for key, name in STAGE_ART:
        src = os.path.join(ROOT, "assets", "titles", name)
        img = _open(src).convert("RGBA")
        box = img.split()[3].getbbox()
        if box:
            pad = 6
            box = (max(0, box[0] - pad), max(0, box[1] - pad),
                   min(img.width, box[2] + pad), min(img.height, box[3] + pad))
            img = img.crop(box)
        out = os.path.join(ASSETS, "img", "stage", key + ".webp")
        _report("stage/" + key, out, _save_webp(img, out, quality=92, max_h=420), src)


# ---------------------------------------------------------------- 3. 自机

# 键 -> (立绘, 战斗形象)；键与顺序取自 src/engine/settings.py 的 PLAYER_CHARACTER_KEYS
CHARA_FILES = {
    "mage": ("Mage/self1.png", "Mage/stg1.png"),
    "archer": ("Archer/Archer.png", "Archer/stg1.png"),
    "tank": ("Tank/Tank.png", "Tank/stg1.png"),
    "frozen_blaze": ("FB/FB.png", "FB/stg1.png"),
}


def build_chara():
    print("[chara] 自机立绘")
    base = os.path.join(ROOT, "assets", "sprites", "self")
    for key, (portrait, fight) in CHARA_FILES.items():
        src = os.path.join(base, portrait)
        out = os.path.join(ASSETS, "chara", key + ".webp")
        _report(key, out, _save_webp(_fit_portrait(src), out, quality=90, max_h=1400), src)

        src = os.path.join(base, fight)
        out = os.path.join(ASSETS, "chara", key + "-fight.webp")
        _report(key + "-fight", out, _save_webp(_open(src).convert("RGBA"), out, quality=90, max_h=420), src)


# ---------------------------------------------------------------- 4. Boss 立绘

# 立绘套组：new = 新版，another = 另一版，游戏设置界面里可切换（src/engine/settings.py:196）。
# 站点统一使用「另一版」：舞台页与人物页共用同一批图，换套组只改这一个常量再重跑 boss。
BOSS_ART_SET = "another"

# 站点里的 Boss id（与 data/stages.json 对齐）-> 套组目录内的文件名。
# 各套组内部的文件名大小写不统一（watcher.png 与 The_Professor.png 并存），所以显式列出。
BOSS_ART_FILES = {
    "arachne": "Arachne.png",
    "bonzo": "Bonzo.png",
    "end_stone_protector": "end_stone_protector.png",
    "ender_dragon": "ender_dragon.png",
    "goldor": "Goldor.png",
    "livid": "Livid.png",
    "maxor": "Maxor.png",
    "necron": "Necron.png",
    "the_professor": "The_Professor.png",
    "sadan": "Sadan.png",
    "scarf": "Scarf.png",
    "storm": "storm.png",
    "thorn": "thorn.png",
    "the_watcher": "watcher.png",
    "wither_king": "Wither_King.png",
    "wizardman": "Wizardman.png",
    "barry": "barry.png",
}


def build_boss():
    print("[boss] Boss 立绘（%s 套组）" % BOSS_ART_SET)
    base = os.path.join(ROOT, "assets", "sprites", "bosses", BOSS_ART_SET)
    for key in sorted(BOSS_ART_FILES):
        src = os.path.join(base, BOSS_ART_FILES[key])
        out = os.path.join(ASSETS, "boss", key + ".webp")
        _report(key, out, _save_webp(_fit_portrait(src), out, quality=88, max_h=1200), src)


# ---------------------------------------------------------------- 5. 物品图标

def build_item():
    print("[item] 物品图标")
    base = os.path.join(ROOT, "assets", "items")
    for name in sorted(f for f in os.listdir(base) if f.lower().endswith(".png")):
        key = os.path.splitext(name)[0]
        src = os.path.join(base, name)
        out = os.path.join(ASSETS, "item", key + ".webp")
        # 图标很小（多为 160x160），无损存以维持像素边缘干净
        _report("item/" + key, out, _save_webp(_open(src).convert("RGBA"), out, lossless=True), src)


# ---------------------------------------------------------------- 6. 实机截图

SHOTS = [
    ("title", "_boot_menu.png"),
    ("stage2", "_stage2_preview_play.png"),
    ("stage3", "_stage3_preview_play.png"),
    ("stage5", "_stage5_preview_opening.png"),
    ("battle", "_fb_battle.png"),
    ("character", "_stage_ex_entry_01_character.png"),
    ("loading", "_stage_ex_entry_03_loading.png"),
]


def build_shots():
    print("[shots] 实机截图")
    base = os.path.join(ROOT, "previews")
    for key, name in SHOTS:
        src = os.path.join(base, name)
        if not os.path.exists(src):
            print("  - 跳过（不存在）", name)
            continue
        out = os.path.join(ASSETS, "img", "shot", key + ".webp")
        _report("shot/" + key, out, _save_webp(_open(src).convert("RGB"), out, quality=86, max_w=1400), src)


# ---------------------------------------------------------------- 7. 站点图标

def build_icon():
    print("[icon] 站点图标")
    src = os.path.join(ROOT, "assets", "gui", "icon.png")
    img = _open(src).convert("RGBA")
    w, h = img.size
    side = min(w, h)
    img = img.crop(((w - side) // 2, (h - side) // 2, (w + side) // 2, (h + side) // 2))
    for px, name in ((32, "favicon-32.png"), (180, "apple-touch-icon.png"), (512, "icon-512.png")):
        out = os.path.join(ASSETS, "img", name)
        img.resize((px, px), Image.LANCZOS).save(out, "PNG", optimize=True)
        _report(name, out, (px, px), src)


# ---------------------------------------------------------------- 8. 物品数据

RARITY_ORDER = [
    "COMMON", "UNCOMMON", "RARE", "EPIC", "LEGENDARY",
    "MYTHIC", "DIVINE", "SPECIAL", "VERY_SPECIAL",
]


def build_data():
    print("[data] 物品图鉴数据")
    from src.systems.item_system import SKYBLOCK_ITEMS, ITEM_TYPE_LABELS, SLOT_LABELS
    from src.engine import settings as cfg

    def rgb_to_hex(rgb):
        try:
            r, g, b = rgb[:3]
            return "#%02x%02x%02x" % (int(r), int(g), int(b))
        except Exception:
            return "#888888"

    items = []
    missing = []
    for item in SKYBLOCK_ITEMS.values():
        if not os.path.exists(os.path.join(ROOT, "assets", "items", item.id + ".png")):
            missing.append(item.id)
        items.append({
            "id": item.id,
            "name": item.name,
            "rarity": item.rarity,
            "rarity_label": item.rarity.replace("_", " ").title(),
            "rarity_color": rgb_to_hex(cfg.RARITY_COLORS.get(item.rarity, (136, 136, 136))),
            "type": item.item_type,
            "type_label": ITEM_TYPE_LABELS.get(item.item_type, item.item_type),
            "slot": item.slot,
            "slot_label": SLOT_LABELS.get(item.slot, item.slot),
            "equippable": bool(item.is_equippable),
            "reforgeable": bool(item.can_reforge),
            "stats": dict(item.stats or {}),
            "lore": list(item.lore or []),
            "buy_price": item.buy_price,
            "sell_price": item.sell_price,
            "icon": "assets/item/%s.webp" % item.id,
        })

    def sort_key(e):
        idx = RARITY_ORDER.index(e["rarity"]) if e["rarity"] in RARITY_ORDER else len(RARITY_ORDER)
        return (idx, e["type"], e["name"].lower())

    items.sort(key=sort_key)

    data = {
        "meta": {
            "count": len(items),
            "rarities": [{"id": r, "label": r.replace("_", " ").title(),
                          "color": rgb_to_hex(cfg.RARITY_COLORS.get(r, (136, 136, 136)))}
                         for r in RARITY_ORDER],
            "types": [{"id": k, "label": v} for k, v in ITEM_TYPE_LABELS.items()],
        },
        "items": items,
    }

    out = os.path.join(WEB_ROOT, "data", "items.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("  %-26s %-38s %26.1f KB   %d 件"
          % ("items.json", "data/items.json", os.path.getsize(out) / 1024, len(items)))
    if missing:
        print("  ! 以下物品没有对应图标文件：", ", ".join(missing))


STEPS = {
    "title": build_title,
    "stage": build_stage,
    "chara": build_chara,
    "boss": build_boss,
    "item": build_item,
    "shots": build_shots,
    "icon": build_icon,
    "data": build_data,
}


def main():
    wanted = sys.argv[1:] or list(STEPS)
    for name in wanted:
        build = STEPS.get(name)
        if build is None:
            print("未知步骤：%s（可选：%s）" % (name, " / ".join(STEPS)))
            continue
        build()
    print("\n完成。产物位于 web/assets 与 web/data。")


if __name__ == "__main__":
    main()
