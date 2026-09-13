# -*- coding: utf-8 -*-
# Boss 立绘「外圈半透明白框」剥离：把立绘最外圈那层柔边白带清成完全透明。
#
# 背景：新立绘导出时在画布四边各叠了一条固定的柔边白带（贴边 α=119，向内约 12px
# 衰减到 0；四角是两条边叠加，α=183）。游戏之前只为白底图做抠图，这种「已带 alpha
# 但边缘有一圈半透明白」的图会被原样使用，叠在战斗背景上就露出一圈白框。
#
# 判定依据：白框只垫在最外圈、与画布四边相连，且 α 恰好等于那条固定剖面；角色本体
# 的 α 一律高于剖面值（贴边处的实测颜色也明显暗于剖面，说明白框没有压在角色上）。
# 因此逐像素按「α <= 该处的剖面合成值」剥离即可，不会啃到角色。画布尺寸与角色像素
# 与原图完全一致：不缩放、不裁剪，可直接覆盖原文件。
#
# 用法（项目根目录执行）：
#   python tools/_strip_boss_border.py                # 处理 assets/sprites/bosses/new 下全部 PNG
#   python tools/_strip_boss_border.py --dry-run      # 只报告不写文件
#   python tools/_strip_boss_border.py a.png b.png    # 处理指定文件（相对项目根目录）

import argparse
import glob
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_DIR = os.path.join(ROOT, "assets", "sprites", "bosses", "new")

# 参考剖面：距画布边缘 d 像素处的白框 α（15 张新立绘实测完全一致）
REFERENCE_PROFILE = [119, 98, 81, 63, 48, 34, 24, 16, 11, 6, 2, 1, 0]
# 某条边贴边 α 低于该值就认为这条边没有白框（如 Bonzo / End_Stone_Protector）
RING_MIN_ALPHA = 64


def _side_profile(alpha, side, span):
    """量一条边的柔边剖面：每个距离取该行/列上出现次数最多的 α（背景占绝大多数）

    返回长度 span 的列表；贴边 α 太小说明这条边没有白框，返回全 0。
    """
    height, width = alpha.shape
    profile = []
    for dist in range(span):
        if side == "top":
            line = alpha[dist]
        elif side == "bottom":
            line = alpha[height - 1 - dist]
        elif side == "left":
            line = alpha[:, dist]
        else:
            line = alpha[:, width - 1 - dist]
        values, counts = np.unique(line, return_counts=True)
        profile.append(int(values[counts.argmax()]))
    if profile[0] < RING_MIN_ALPHA:
        return [0] * span
    return profile


def border_ring_alpha(alpha):
    """按四边剖面合成整幅图的「白框 α 上限」图（与原图同尺寸的 int 数组）

    同一条像素同时落在横带与纵带上时按 alpha 合成叠加，与实测角部 α=183 吻合。
    """
    height, width = alpha.shape
    span = len(REFERENCE_PROFILE)
    top = _side_profile(alpha, "top", span)
    bottom = _side_profile(alpha, "bottom", span)
    left = _side_profile(alpha, "left", span)
    right = _side_profile(alpha, "right", span)
    if not any(top) and not any(bottom) and not any(left) and not any(right):
        return np.zeros_like(alpha, dtype=np.int16), None

    dy = np.minimum(np.arange(height), np.arange(height)[::-1])
    dx = np.minimum(np.arange(width), np.arange(width)[::-1])
    prof_y = np.maximum(top, bottom)[np.clip(dy, 0, span - 1)]
    prof_x = np.maximum(left, right)[np.clip(dx, 0, span - 1)]
    inside_y = dy < span
    inside_x = dx < span
    ry = np.where(inside_y, prof_y, 0).astype(np.float64) / 255.0
    rx = np.where(inside_x, prof_x, 0).astype(np.float64) / 255.0
    ring = 1.0 - (1.0 - ry[:, None]) * (1.0 - rx[None, :])
    info = {"top": top, "bottom": bottom, "left": left, "right": right}
    return np.rint(ring * 255.0).astype(np.int16), info


def content_bbox(alpha, cutoff=8):
    """不透明内容的外接框 (left, top, right, bottom)；全透明时返回 None"""
    rows = np.where((alpha > cutoff).any(axis=1))[0]
    cols = np.where((alpha > cutoff).any(axis=0))[0]
    if rows.size == 0 or cols.size == 0:
        return None
    return int(cols[0]), int(rows[0]), int(cols[-1]), int(rows[-1])


def strip_file(path, dry_run=False):
    """剥离单个立绘文件的外圈白框，返回 (是否改动, 说明)"""
    image = Image.open(path)
    if image.mode != "RGBA":
        return False, "非 RGBA（%s），跳过" % image.mode
    rgba = np.array(image)
    alpha = rgba[:, :, 3].astype(np.int16)
    ring, info = border_ring_alpha(alpha)
    if info is None:
        return False, "四边均无白框，跳过"
    # 只统计真正被清掉的白框像素（本来就全透明的背景不计）
    mask = (alpha <= ring) & (alpha > 0)
    removed = int(mask.sum())
    if removed == 0:
        return False, "未发现白框像素，跳过"
    before = content_bbox(alpha)
    alpha_out = np.where(mask, 0, alpha).astype(np.uint8)
    after = content_bbox(alpha_out)
    note = ("剥离白框 %d 像素（占画布 %.2f%%），内容框 %s -> %s"
            % (removed, 100.0 * removed / alpha.size, before, after))
    if dry_run:
        return True, "将" + note
    rgba[:, :, 3] = alpha_out
    dpi = image.info.get("dpi")
    Image.fromarray(rgba, "RGBA").save(path, dpi=dpi)
    return True, note


def main():
    parser = argparse.ArgumentParser(description="剥离 Boss 立绘外圈半透明白框（原地改写 PNG）")
    parser.add_argument("paths", nargs="*", help="要处理的 PNG；缺省处理 new 套组全部")
    parser.add_argument("--dry-run", action="store_true", help="只报告，不写文件")
    args = parser.parse_args()

    paths = args.paths or sorted(glob.glob(os.path.join(DEFAULT_DIR, "*.png")))
    if not paths:
        print("没有找到待处理的 PNG")
        return 1
    changed = 0
    for path in paths:
        path = path if os.path.isabs(path) else os.path.join(ROOT, path)
        if not os.path.exists(path):
            print("%-28s 缺失，跳过" % os.path.basename(path))
            continue
        ok, note = strip_file(path, dry_run=args.dry_run)
        changed += 1 if ok else 0
        print("%-28s %s" % (os.path.basename(path), note))
    print("=" * 72)
    print("%s：%d/%d 张%s" % ("待处理" if args.dry_run else "已处理", changed, len(paths),
                              "（dry-run，未写文件）" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
