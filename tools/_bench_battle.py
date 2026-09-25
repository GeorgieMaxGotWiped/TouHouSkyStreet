# -*- coding: utf-8 -*-
# 战斗场景基准：造一场真实弹幕，报告「帧时间 / 弹幕条数 / 贴图种类」。
#
# 用法：python tools\_bench_battle.py [关卡] [测量帧数] [渲染倍率] [热身帧数]
#   关卡：stage1 / stage2 / stage3 / stage4 / stage5 / stage6（默认 stage3）
#   渲染倍率：1 / 2 / 3 / 4（默认 3，即 2880x2160 窗口）
#   第 5 个参数是输出 PNG 时，顺便存一张图（便于肉眼看弹幕清晰度）
#
# 它跑的是真实主循环那条绘制路径（game._draw），所以「画布弹幕 -> 显卡弹幕」
# 这类改动的收益可以直接比。弹幕贴图统计用来确认旋转缓存的实际规模。
import os
import sys
import time

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"
sys.path.insert(0, os.getcwd())

import pygame

from src.engine import game as game_module
from src.engine import settings as cfg

# 控制台默认不是 UTF-8（中文会乱码），这里强制一下
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

STAGES = {
    "stage1": ("src.stages.stage1", "Stage1_SkyblockHub"),
    "stage2": ("src.stages.stage2", "Stage2_DragonsNest"),
    "stage3": ("src.stages.stage3", "Stage3_CatacombsF1"),
    "stage4": ("src.stages.stage4", "Stage4_Catacombs"),
    "stage5": ("src.stages.stage5", "Stage5_WitherLords"),
    "stage6": ("src.stages.stage6", "Stage6_FinalApproach"),
}

SCALE_INDEX = {1: 0, 2: 1, 3: 2, 4: 3}


def build_stage(name):
    module_name, class_name = STAGES[name]
    module = __import__(module_name, fromlist=[class_name])
    return getattr(module, class_name)()


def sprite_stats(bullets):
    """弹幕实际用到的 (槽位, 宽度) 组合与旋转角度分布"""
    from src.engine import settings as cfg
    from src.entities import bullet_atlas
    from src.entities.bullet import Bullet
    combos = {}
    angles = set()
    for b in bullets:
        if b.is_player_bullet or b.bullet_type == Bullet.TYPE_BEAM:
            continue
        if b.radius > cfg.ENEMY_BULLET_SPRITE_MAX_RADIUS:
            continue
        slot = b.sprite_slot or cfg.ENEMY_BULLET_SPRITE_MAP.get(b.bullet_type)
        if not slot:
            continue
        slot = bullet_atlas.pick_color_slot(slot, b.color)
        native = bullet_atlas.get_native_size(slot)
        if native is None:
            continue
        rotating = b.bullet_type in (Bullet.TYPE_RICE, Bullet.TYPE_ARROW,
                                     Bullet.TYPE_KNIFE)
        combos[(slot, native[0], rotating)] = combos.get(
            (slot, native[0], rotating), 0) + 1
        if rotating:
            import math
            angles.add(round(-90.0 - math.degrees(b.angle), 1))
    return combos, angles


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
    print(f"[bench] saved {path} {w}x{h}  ->  {view_path}")


def _dense_region(points, size, bounds):
    """在 bounds（窗口像素）里找一块 size 的矩形，让落进去的弹幕中心最多"""
    step = 24
    best = (0, bounds[0], bounds[1])
    y = bounds[1]
    while y + size[1] <= bounds[3]:
        x = bounds[0]
        while x + size[0] <= bounds[2]:
            n = sum(1 for px, py in points
                    if x <= px < x + size[0] and y <= py < y + size[1])
            if n > best[0]:
                best = (n, x, y)
            x += step
        y += step
    return pygame.Rect(best[1], best[2], size[0], size[1]), best[0]


def _label_font(size=22):
    """对比图的说明字体：用带中文字形的 font2（缺字时退回 pygame 默认字体）"""
    path = os.path.join(os.getcwd(), "assets", "fonts", "font2.otf")
    try:
        return pygame.font.Font(path, size)
    except Exception:
        return pygame.font.SysFont(None, size)


def _label(text, width, font):
    """对比图的一行说明条"""
    bar = pygame.Surface((width, 34))
    bar.fill((24, 24, 28))
    bar.blit(font.render(text, True, (240, 240, 240)), (8, 5))
    return bar


def save_bullet_compare(game, path, state, label, crop_size=(660, 420)):
    """同一帧分别按「显卡弹幕」与「1x 画布弹幕」呈现，裁同一块拼成对比图

    两次呈现只差弹幕这一层（其余管线完全一样），所以两幅里的弹幕必须落在完全相同的
    像素上：这张图既能肉眼看清晰度，也能一眼看出位置有没有跑偏。第三行是差分（放大
    4 倍）：位置一致时只该看到弹幕的边缘轮廓。
    """
    from src.engine import painter
    shots = {}
    try:
        for tag, on in (("显卡弹幕（原生像素）", True), ("1x 画布弹幕（旧版）", False)):
            painter.set_enabled(on)
            game._draw()
            shots[tag] = game.presenter.renderer.to_surface()
    finally:
        painter.set_enabled(True)

    gpu_shot = shots["显卡弹幕（原生像素）"]
    k = gpu_shot.get_width() / float(cfg.SCREEN_WIDTH)
    points = [((b.x + state.offset_x) * k, (b.y + state.offset_y) * k)
              for b in state.bullet_manager.enemy_bullets]
    battle = game._battle_dst_rect()
    region, hits = _dense_region(points, crop_size, battle)
    print(f"[bench] 对比图取样区 {region}（{hits} 发弹幕，窗口像素）")

    crops = {}
    for name, shot in shots.items():
        crops[name] = shot.subsurface(region).copy()
    labels = list(crops.keys())
    font = _label_font()
    w, h = crops[labels[0]].get_size()
    diff = _diff_tile(crops[labels[0]], crops[labels[1]])
    rows = [(labels[0], crops[labels[0]]), (labels[1], crops[labels[1]])]
    if diff is not None:
        rows.append(("差分 x4（位置一致 => 只有边缘）", diff))

    sheet = pygame.Surface((w, sum(34 + r[1].get_height() for r in rows)))
    sheet.fill((12, 12, 14))
    y = 0
    for text, image in rows:
        sheet.blit(_label(text, w, font), (0, y))
        y += 34
        sheet.blit(image, (0, y))
        y += image.get_height()
    out = os.path.join(os.path.dirname(os.path.abspath(path)),
                       f"_clarity_{label}.png")
    pygame.image.save(sheet, out)
    print(f"[bench] saved {out} {sheet.get_width()}x{sheet.get_height()}")


def _diff_tile(a, b):
    """两幅同尺寸画面的差分（放大 4 倍）；没有 numpy 时返回 None"""
    try:
        import numpy as np
    except Exception:
        return None
    da = np.asarray(pygame.surfarray.array3d(a), dtype=np.int16)
    db = np.asarray(pygame.surfarray.array3d(b), dtype=np.int16)
    d = np.clip(np.abs(da - db) * 4, 0, 255).astype(np.uint8)
    tile = pygame.Surface(a.get_size())
    pygame.surfarray.blit_array(tile, d)
    return tile


def check_battle_clip(game, state):
    """弹幕出框检查：沿战斗框四边塞一圈「骑在边框上」的弹，框外不该有任何红色像素

    弹幕改由显卡直绘后不再经过画布的 set_clip，不小心就会在边框外露出来。这里拿
    同一帧分别按「显卡弹幕」与「1x 画布弹幕」（后者仍走画布的 set_clip，是正确
    参考）各呈现一次，再数战斗框内 / 框外的红色像素：出框、少裁、多裁都会露出来。
    """
    from src.engine import painter
    from src.entities.bullet import Bullet

    battle = pygame.Rect(0, 0, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT)
    kept = list(state.bullet_manager.enemy_bullets)

    # 骑在四边上的弹 + 几个完全在框外的弹（战斗区坐标：0,0 是战斗框左上角）
    spots = []
    for i in range(4):
        t = (i + 1) / 5.0
        spots += [(battle.width * t, 0), (battle.width * t, battle.height),
                  (0, battle.height * t), (battle.width, battle.height * t)]
    spots += [(0, 0), (battle.width, battle.height),
              (-40, battle.height / 2), (battle.width + 40, battle.height / 2),
              (battle.width / 2, -40), (battle.width / 2, battle.height + 40)]

    def shoot(use_edges):
        """同一场景按两种绘制路径各呈现一次"""
        bullets = []
        if use_edges:
            for x, y in spots:
                b = Bullet(x, y, 0.0, 0.0, Bullet.TYPE_CIRCLE, radius=6.0,
                           color=(255, 70, 70), lifetime=600)
                b.manager = state.bullet_manager
                bullets.append(b)
        state.bullet_manager.enemy_bullets = bullets
        shots = {}
        for tag, on in (("gpu", True), ("canvas", False)):
            painter.set_enabled(on)
            game._draw()
            shots[tag] = game.presenter.renderer.to_surface()
        painter.set_enabled(True)
        return shots

    empty = shoot(False)
    probe = shoot(True)
    state.bullet_manager.enemy_bullets = kept

    k = probe["gpu"].get_width() / float(cfg.SCREEN_WIDTH)
    inner = pygame.Rect(int(cfg.BATTLE_OFFSET_X * k), int(cfg.BATTLE_OFFSET_Y * k),
                        int(battle.width * k), int(battle.height * k))
    whole = probe["gpu"].get_rect()
    report = {}
    for tag in ("gpu", "canvas"):
        added = _red_pixels(probe[tag], inner) - _red_pixels(empty[tag], inner)
        leak = (_red_pixels(probe[tag], whole, exclude=inner)
                - _red_pixels(empty[tag], whole, exclude=inner))
        report[tag] = (added, leak)
        print(f"[bench] 弹幕出框检查[{tag}]：框内新增红色像素={added}，"
              f"框外新增红色像素={leak}")
    ref = report["canvas"][0]
    ratio = report["gpu"][0] / float(max(1, ref))
    ok = (report["gpu"][1] == 0 and report["canvas"][1] == 0
          and 0.75 <= ratio <= 1.35)
    print(f"[bench] 弹幕出框检查：{len(spots)} 发骑边弹，框内两路比值={ratio:.2f}"
          f"（画布参考 {ref} px，应接近 1）"
          f"  -> {'OK（框外干净、裁剪一致）' if ok else '不合格'}")

    pad = int(60 * k)
    out = os.path.join("previews", "battle", "_clip_probe.png")
    pygame.image.save(probe["gpu"].subsurface(inner.inflate(pad, pad).clip(whole)),
                      os.path.abspath(out))
    print(f"[bench] saved {os.path.abspath(out)}（战斗框四边；红点应被边框切掉）")


def _red_pixels(surface, rect, exclude=None):
    """数一块区域里的「红色弹」像素（红通道高、绿蓝低），用来量弹幕露出多少"""
    import numpy as np
    area = surface.subsurface(rect)
    a = np.asarray(pygame.surfarray.array3d(area), dtype=np.int16)
    mask = (a[:, :, 0] > 140) & (a[:, :, 1] < 110) & (a[:, :, 2] < 110)
    if exclude is not None:
        m = pygame.Rect(rect.x - exclude.x, rect.y - exclude.y,
                        rect.width, rect.height)
        keep = np.ones(mask.shape, dtype=bool)
        keep[max(0, m.x):max(0, m.right), max(0, m.y):max(0, m.bottom)] = False
        mask = mask & keep
    return int(mask.sum())




def main():
    stage_name = sys.argv[1] if len(sys.argv) > 1 else "stage3"
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    warm = int(sys.argv[4]) if len(sys.argv) > 4 else 900
    out_path = sys.argv[5] if len(sys.argv) > 5 else None

    original = game_module.load_user_config
    game_module.load_user_config = lambda: dict(
        original(), fullscreen=False, render_scale_index=SCALE_INDEX[scale])
    pygame.init()
    game = game_module.Game()
    from pygame._sdl2 import video as video_module
    video_module.Window.from_display_module().size = (960 * scale, 720 * scale)

    from src.ui.menu import PlayingState
    state = PlayingState(game, build_stage(stage_name))
    game.push_state(state)
    game._update_present_rect()

    # 直接把关卡推到关底 Boss 战：正常时间轴要 47 秒才出道中 Boss，测弹幕不用等
    state.stage.setup_boss()
    state.stage.phase = "boss"
    state.stage.timer = 0

    for _ in range(warm):
        state.update(1 / 60.0)

    bullets = list(state.bullet_manager.enemy_bullets)
    combos, angles = sprite_stats(bullets)

    def measure(label):
        """量同一帧的绘制耗时（不推进逻辑，画的是同一幅静态画面）"""
        best = None
        for _ in range(frames):
            t0 = time.perf_counter()
            game._draw()
            dt = time.perf_counter() - t0
            best = dt if best is None else min(best, dt)
        return best * 1000.0

    with_bullets = measure("弹幕")
    if out_path:
        save_shot(game, out_path)
        save_bullet_compare(game, out_path, state, stage_name)
    if game.presenter is not None:
        # 弹幕上显卡后不再经过画布的裁剪，框外露弹是回归重点，每次跑都查一遍
        check_battle_clip(game, state)
    # 同一帧里把弹幕抽掉再量一次：两次的差值就是弹幕这一层的绘制开销
    kept = state.bullet_manager.enemy_bullets
    state.bullet_manager.enemy_bullets = []
    without_bullets = measure("无弹幕")
    state.bullet_manager.enemy_bullets = kept

    for _ in range(frames):
        state.update(1 / 60.0)
        game._draw()

    from src.engine import painter
    print(f"[bench] {stage_name} scale={scale} 渲染倍率={game.render_scale} "
          f"窗口={video_module.Window.from_display_module().size}")
    print(f"[bench] 弹幕 敌方={len(state.bullet_manager.enemy_bullets)} "
          f"玩家={len(state.bullet_manager.player_bullets)}")
    print(f"[bench] 整帧绘制 = {with_bullets:.2f} ms（无弹幕 {without_bullets:.2f} ms，"
          f"弹幕这一层 = {with_bullets - without_bullets:.2f} ms）")
    ops = game.screen.gpu.ops
    over = getattr(game.screen.gpu, "ops_over", None)
    print(f"[bench] 显卡指令 下层={len(ops)} 上层={len(over) if over is not None else '-'}"
          f" 开关={'开' if painter.enabled() else '关'}")
    print(f"[bench] 弹幕贴图组合 {len(combos)} 种，旋转角度 {len(angles)} 种：")
    for (slot, width, rotating), count in sorted(combos.items(),
                                                 key=lambda kv: -kv[1])[:12]:
        print(f"[bench]    {slot:<8} 宽={width:<3} 旋转={int(rotating)} 数量={count}")
    game.running = False
    pygame.quit()


if __name__ == "__main__":
    main()
