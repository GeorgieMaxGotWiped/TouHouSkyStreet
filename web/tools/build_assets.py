# -*- coding: utf-8 -*-
"""整理网站图片资产：头图与人物图优化为 WebP，并生成图库数据。

用法（在项目根目录执行）：
    python web/tools/build_assets.py

产物：
    web/assets/img/hero.webp         # 网站头图（assets/backgrounds/bg_0.png）
    web/assets/img/<界面>.webp        # 新版界面的实机截图（previews/...）
    web/assets/gallery/<id>.webp     # 人物图（assets/sprites/...）
    web/data/gallery.json            # 图库元数据

注意：画廊 webp 不会自动跟随素材更新——立绘换新（如 assets/sprites/bosses/new/、
assets/sprites/self/<角色>/ 被替换）后必须重跑本脚本，否则站点仍会用上一版的出图。
"""
import json
import os

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GALLERY_DIR = os.path.join(ROOT, "web", "assets", "gallery")
IMG_DIR = os.path.join(ROOT, "web", "assets", "img")

# (id, 源文件, 名称, 分类)：Boss 立绘取自 assets/sprites/bosses/new（游戏内默认套组）
GALLERY = [
    # —— 自机（四位，对应游戏内「选择自机」界面）——
    ("mage", "assets/sprites/self/Mage/self1.png", "魔法使 Mage", "player"),
    ("archer", "assets/sprites/self/Archer/Archer.png", "弓手 Archer", "player"),
    ("berserk", "assets/sprites/self/Berserk/Berserk.png", "狂战士 Berserk", "player"),
    ("tank", "assets/sprites/self/Tank/Tank.png", "重装 Tank", "player"),
    # —— Boss / 角色 ——
    ("arachne", "assets/sprites/bosses/new/Arachne.png", "蛛后 Arachne", "boss"),
    ("bonzo", "assets/sprites/bosses/new/Bonzo.png", "邦佐 Bonzo", "boss"),
    ("end_stone_protector", "assets/sprites/bosses/new/End_Stone_Protector.png", "末影石守卫", "boss"),
    ("ender_dragon", "assets/sprites/bosses/new/Ender_Dragon.png", "末影龙", "boss"),
    ("goldor", "assets/sprites/bosses/new/Goldor.png", "戈尔铎 Goldor", "boss"),
    ("livid", "assets/sprites/bosses/new/Livid.png", "利维德 Livid", "boss"),
    ("maxor", "assets/sprites/bosses/new/Maxor.png", "马克索 Maxor", "boss"),
    ("necron", "assets/sprites/bosses/new/Necron.png", "尼可隆 Necron", "boss"),
    ("professor", "assets/sprites/bosses/new/The_Professor.png", "教授 Professor", "boss"),
    ("sadan", "assets/sprites/bosses/new/Sadan.png", "萨丹 Sadan", "boss"),
    ("scarf", "assets/sprites/bosses/new/Scarf.png", "斯卡夫 Scarf", "boss"),
    ("storm", "assets/sprites/bosses/new/Storm.png", "风暴 Storm", "boss"),
    ("thorn", "assets/sprites/bosses/new/Thorn.png", "荆棘 Thorn", "boss"),
    ("watcher", "assets/sprites/bosses/new/The_Watcher.png", "守望者 Watcher", "boss"),
    ("wither_king", "assets/sprites/bosses/new/Wither_King.png", "凋零之王 Wither King", "boss"),
]

# 实机截图：(产物名, 源文件)。源文件取自开发期预览 previews/（由 tools/ 下的脚本生成）；
# 早期四张 PNG 截图（gameplay-1/2、loadout、shop）保持原样，不在此表内。
SCREENSHOTS = [
    ("chara-select.webp", "previews/_chara_select/_view_chara_0.png"),
    ("difficulty.webp", "previews/_chara_select/_view_difficulty_after.png"),
    ("settings.webp", "previews/_self_mage/_view_settings_after.png"),
]


def load_portrait(src_rel):
    """读入立绘：统一转 RGBA（立绘本身即透明背景 PNG，无需再抠图）"""
    return Image.open(os.path.join(ROOT, src_rel)).convert("RGBA")


def make_webp(src_rel, dst_abs, max_h=800, quality=82, portrait=False):
    """缩放并转 WebP，返回 (宽, 高)；portrait=True 时先抠掉立绘白底"""
    if portrait:
        im = load_portrait(src_rel)
    else:
        im = Image.open(os.path.join(ROOT, src_rel)).convert("RGB")
    if im.height > max_h:
        w = int(round(im.width * max_h / im.height))
        im = im.resize((w, max_h), Image.LANCZOS)
    im.save(dst_abs, "WEBP", quality=quality, method=6)
    return im.size


def make_screenshot(src_rel, dst_abs, quality=82):
    """实机截图转 WebP（截图已是 960x720 的逻辑分辨率，直接转码即可）"""
    im = Image.open(os.path.join(ROOT, src_rel)).convert("RGB")
    im.save(dst_abs, "WEBP", quality=quality, method=6)
    return im.size


def main():
    os.makedirs(GALLERY_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)

    # 头图
    hero = os.path.join(IMG_DIR, "hero.webp")
    size = make_webp("assets/backgrounds/bg_0.png", hero, max_h=1200, quality=80)
    print("头图 -> %s %s %dkB" % (hero, size, os.path.getsize(hero) // 1024))

    # 实机截图
    for name, rel in SCREENSHOTS:
        if not os.path.exists(os.path.join(ROOT, rel)):
            print("跳过（缺源）：%s" % rel)
            continue
        dst = os.path.join(IMG_DIR, name)
        size = make_screenshot(rel, dst)
        print("截图 -> %-18s %s %dkB" % (name, size, os.path.getsize(dst) // 1024))

    # 人物图
    items = []
    for gid, rel, name, category in GALLERY:
        dst = os.path.join(GALLERY_DIR, gid + ".webp")
        if not os.path.exists(os.path.join(ROOT, rel)):
            print("跳过（缺源）：%s" % rel)
            continue
        size = make_webp(rel, dst, portrait=True)
        items.append({
            "id": gid,
            "name": name,
            "category": category,
            "image": "assets/gallery/%s.webp" % gid,
        })
        print("  %-18s %-16s %s %dkB" % (gid, name, size, os.path.getsize(dst) // 1024))

    out = os.path.join(ROOT, "web", "data", "gallery.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"categories": [
            {"id": "player", "label": "自机"},
            {"id": "boss", "label": "Boss / 角色"},
        ], "items": items}, f, ensure_ascii=False, indent=2)
    print("图库数据 -> %s（%d 张）" % (out, len(items)))


if __name__ == "__main__":
    main()
