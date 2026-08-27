# -*- coding: utf-8 -*-
"""整理网站图片资产：头图与人物图优化为 WebP，并生成图库数据。

用法（在项目根目录执行）：
    python web/tools/build_assets.py

产物：
    web/assets/img/hero.webp         # 网站头图（assets/backgrounds/bg_0.png）
    web/assets/gallery/<id>.webp     # 人物图（assets/sprites/...）
    web/data/gallery.json            # 图库元数据
"""
import json
import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GALLERY_DIR = os.path.join(ROOT, "web", "assets", "gallery")
IMG_DIR = os.path.join(ROOT, "web", "assets", "img")

# (id, 源文件, 名称, 分类)
GALLERY = [
    # —— 玩家 ——
    ("player", "assets/sprites/self/self1.png", "玩家（自机）", "player"),
    # —— Boss / 角色 ——
    ("arachne", "assets/sprites/bosses/arachne.png", "蛛后 Arachne", "boss"),
    ("bonzo", "assets/sprites/bosses/bonzo.png", "邦佐 Bonzo", "boss"),
    ("end_stone_protector", "assets/sprites/bosses/end_stone_protector.png", "末影石守卫", "boss"),
    ("ender_dragon", "assets/sprites/bosses/ender_dragon.png", "末影龙", "boss"),
    ("goldor", "assets/sprites/bosses/goldor.png", "戈尔铎 Goldor", "boss"),
    ("livid", "assets/sprites/bosses/livid.png", "利维德 Livid", "boss"),
    ("maxor", "assets/sprites/bosses/maxor.png", "马克索 Maxor", "boss"),
    ("necron", "assets/sprites/bosses/necron.png", "尼可隆 Necron", "boss"),
    ("professor", "assets/sprites/bosses/professor.png", "教授 Professor", "boss"),
    ("sadan", "assets/sprites/bosses/sadan.png", "萨丹 Sadan", "boss"),
    ("scarf", "assets/sprites/bosses/scarf.png", "斯卡夫 Scarf", "boss"),
    ("storm", "assets/sprites/bosses/storm.png", "风暴 Storm", "boss"),
    ("thorn", "assets/sprites/bosses/thorn.png", "荆棘 Thorn", "boss"),
    ("watcher", "assets/sprites/bosses/watcher.png", "守望者 Watcher", "boss"),
    ("wither_king", "assets/sprites/bosses/wither_king.png", "凋零之王 Wither King", "boss"),
]


def make_webp(src_rel, dst_abs, max_h=800, quality=82):
    """缩放并转 WebP，返回 (宽, 高)。"""
    src = os.path.join(ROOT, src_rel)
    im = Image.open(src).convert("RGB")
    if im.height > max_h:
        w = int(round(im.width * max_h / im.height))
        im = im.resize((w, max_h), Image.LANCZOS)
    im.save(dst_abs, "WEBP", quality=quality, method=6)
    return im.size


def main():
    os.makedirs(GALLERY_DIR, exist_ok=True)
    os.makedirs(IMG_DIR, exist_ok=True)

    # 头图
    hero = os.path.join(IMG_DIR, "hero.webp")
    size = make_webp("assets/backgrounds/bg_0.png", hero, max_h=1200, quality=80)
    print("头图 -> %s %s %dkB" % (hero, size, os.path.getsize(hero) // 1024))

    # 人物图
    items = []
    for gid, rel, name, category in GALLERY:
        dst = os.path.join(GALLERY_DIR, gid + ".webp")
        if not os.path.exists(os.path.join(ROOT, rel)):
            print("跳过（缺源）：%s" % rel)
            continue
        size = make_webp(rel, dst)
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
            {"id": "player", "label": "玩家"},
            {"id": "boss", "label": "Boss / 角色"},
        ], "items": items}, f, ensure_ascii=False, indent=2)
    print("图库数据 -> %s（%d 张）" % (out, len(items)))


if __name__ == "__main__":
    main()
