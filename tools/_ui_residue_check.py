# -*- coding: utf-8 -*-
# 界面残留检查：从可退出界面按 Esc 返回后，画面上不该留下上一个界面的任何像素。
#
# SDL 在同一个进程里重建窗口会失败，所以「上一个界面 -> 返回后的界面」和「直接打开
# 返回后的界面」必须各开一个进程，最后再比较两张图。
#
# 用法：
#   python tools\_ui_residue_check.py <界面> clean              # 直接打开该界面
#   python tools\_ui_residue_check.py <界面> via <上一个界面>    # 先开上一个界面再返回
#   python tools\_ui_residue_check.py report                    # 比较已采样的组合
#
# 想确认这套检查真的抓得到残留时，设 TOUHOU_HIRES_LEGACY_CLEAR=1 再采样一遍：
# 它会把高分辨率图层换回「修复前的清屏写法」，report 应当报出残留。
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"
sys.path.insert(0, os.getcwd())

import pygame

OUT_DIR = os.path.join(os.getcwd(), "previews", "ui_gpu", "residue")
# 覆盖所有「按 Esc 会返回上一个界面」的界面，以及它们各自的返回目标
TRANSITIONS = (
    ("menu", "settings"),
    ("menu", "difficulty"),
    ("menu", "storage"),
    ("menu", "loadout"),
    ("menu", "shop"),
    # 自机选择：这一屏整幅都是「预烤贴图 + 显卡指令」，从难度界面退回时最容易
    # 留下上一屏的底板 / 文字，一并盖上
    ("character", "difficulty"),
    # 上面这一组的目标都是主菜单，而主菜单整屏都是「预烤贴图 + 显卡指令」，一个字
    # 都不往高分辨率图层（hi）上画 —— hi 那张纹理里留着什么，这一帧根本不会被合成
    # 出来，所以「设置 -> 出发休整」这类残留是抓不到的：上一帧留在 hi 纹理里的文字
    # 会在新界面上原地停着（大量字符额外停留）。下面这组的目标界面自己会往 hi 上
    # 写字，残留才会显形，所以必须一起看。
    ("loadout", "settings"),
    ("storage", "settings"),
    ("shop", "storage"),
    ("loadout", "shop"),
    ("prep", "loadout"),
)
SCREENS = ("menu", "settings", "difficulty", "character", "storage", "shop", "forge",
           "loadout", "prep")

# 修复前的 begin_frame：清掉上一帧占用 hi 图层的区域，却把这些矩形从「本帧要上传的
# 脏区」里一起丢了 —— 显卡纹理上那一块就还留着上一帧的像素。设这个环境变量可以复现
# 那处残留，用来证明本检查确实抓得到它（采样完两种模式再跑 report 对比）。
LEGACY = os.environ.get("TOUHOU_HIRES_LEGACY_CLEAR", "0") == "1"


def install_legacy_clear():
    from src.engine import hires

    def begin_frame(self, frame_id=None):
        if frame_id is not None:
            if self._hi_frame == frame_id:
                return
            self._hi_frame = frame_id
        if self.hi is None:
            return
        for rect in self._hi_prev_rects:
            self.hi.fill((0, 0, 0, 0), rect)
        del self._hi_prev_rects[:]
        del self._hi_rects[:]
        self._hi_prev = None
        self._hi_cur = None

    hires.HiResCanvas.begin_frame = begin_frame


def build(game, name):
    # 界面清单与冒烟 / 对比工具共用一份，免得三处各写一遍、改了这边忘了那边
    from tools._ui_gpu_smoke import build as build_screen
    return build_screen(game, name)


def capture(name, previous):
    """previous 为 None 时直接打开 name；否则先画 previous 再切到 name"""
    from src.engine import game as game_module
    from src.engine import painter

    original = game_module.load_user_config
    game_module.load_user_config = lambda: dict(original(), fullscreen=False)
    painter.set_enabled(True)
    if LEGACY:
        install_legacy_clear()

    pygame.init()
    game = game_module.Game()
    from pygame._sdl2 import video as video_module
    video_module.Window.from_display_module().size = (1920, 1440)
    game.push_state(build(game, previous or name))
    game.settle_ui()      # 黑场过渡 + 进场动效走完，拍到的是落定后的画面
    game._update_present_rect()
    for _ in range(3):
        game._draw()
    if previous is not None:
        game.switch_state(build(game, name))
        game.settle_ui()
        game.screen.cache.clear()
        for _ in range(2):
            game._draw()

    surface = game.presenter.renderer.to_surface()
    os.makedirs(OUT_DIR, exist_ok=True)
    tag = name if previous is None else f"{name}_via_{previous}"
    if LEGACY:
        tag += "_legacy"
    path = os.path.join(OUT_DIR, f"{tag}.png")
    pygame.image.save(surface, path)
    print(f"[residue] saved {path} sys_path={sys.path[0]} canvas={game.screen.get_size()}")
    game.running = False


def report():
    suffix = "_legacy" if LEGACY else ""
    worst = 0.0
    for name, previous in TRANSITIONS:
        clean = os.path.join(OUT_DIR, f"{name}.png")
        via = os.path.join(OUT_DIR, f"{name}_via_{previous}{suffix}.png")
        if not (os.path.exists(clean) and os.path.exists(via)):
            print(f"[residue] {name} <- {previous:<11} 缺采样（先跑 clean / via）")
            continue
        a = pygame.image.load(clean)
        b = pygame.image.load(via)
        w, h = a.get_size()
        total = peak = 0
        n = 0
        for y in range(0, h, 3):
            for x in range(0, w, 3):
                ca, cb = a.get_at((x, y)), b.get_at((x, y))
                d = max(abs(ca[i] - cb[i]) for i in range(3))
                total += d
                peak = max(peak, d)
                n += 1
        worst = max(worst, peak)
        print(f"[residue] {name} <- {previous:<11} mean={total / n:6.3f} peak={peak:3d}")
    # 阈值放宽到 16：主菜单选中项的呼吸高亮按 16 档量化，两次采样落在不同档位时
    # 本来就会差几个色阶（那不是残留）
    ok = worst <= 16
    if LEGACY:
        print("[residue] 修复前写法：" + ("本检查抓到了残留（符合预期）" if not ok
                                          else "没抓到残留，检查本身可能失效了"))
    else:
        print("[residue] " + ("OK（无残留）" if ok else f"仍有残留 peak={worst}"))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__ or "usage: <name> clean|via ...")
    if sys.argv[1] == "report":
        pygame.init()
        report()
        pygame.quit()
        return
    name = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "clean"
    if name not in SCREENS:
        raise SystemExit(f"unknown screen: {name}")
    capture(name, previous=None if mode == "clean" else sys.argv[3])


if __name__ == "__main__":
    main()
