# -*- coding: utf-8 -*-
# 界面绘制「改前 / 改后」对比截图（每个模式一个进程：SDL 在同一个进程里重建窗口会失败）
#
#   before = 关掉开关（面板按 1x 画在画布上，再整幅放大 == 旧版行为）
#   after  = 打开开关（背景 / 面板 / 图标按渲染倍率由显卡原生绘制）
#
# 运行：
#   界面名与 tools\_ui_gpu_smoke.py 共用一份（menu / settings / difficulty /
#   storage / shop / forge / loadout / practice / boss_reward / reward_confirm /
#   loading）：
#   python tools\_ui_gpu_compare.py <界面> before [宽x高]
#   python tools\_ui_gpu_compare.py <界面> after  [宽x高]
#   python tools\_ui_gpu_compare.py <界面> combine [x,y,w,h]   # 逻辑坐标，默认取画面中偏上一块
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["SDL_RENDER_SCALE_QUALITY"] = "1"
sys.path.insert(0, os.getcwd())

import pygame

OUT_DIR = os.path.join(os.getcwd(), "previews", "ui_gpu")


def build_state(game, name):
    # 界面清单与冒烟工具共用一份，免得两边各写一遍（支持 menu / settings /
    # difficulty / storage / shop / forge / loadout / practice / boss_reward / loading）
    from tools._ui_gpu_smoke import build
    return build(game, name)


def capture(name, mode, size):
    from src.engine import game as game_module
    from src.engine import painter

    # 无头环境没有真的显示器：强制窗口模式，尺寸由工具指定
    original = game_module.load_user_config

    def _config():
        cfg = dict(original())
        cfg["fullscreen"] = False
        return cfg

    game_module.load_user_config = _config
    painter.set_enabled(mode == "after")

    game = game_module.Game()
    game.push_state(build_state(game, name))
    game.settle_ui()      # 黑场过渡 + 进场动效走完，与「改前」的落定画面才可比
    if name == "reward_confirm":
        # enter() 会把确认弹窗重置掉，只能在进入之后再打开
        game.current_state.selected = 1
        game.current_state.confirming = True
    if game.presenter is None:
        raise SystemExit("GPU presenter unavailable; cannot capture")

    from pygame._sdl2 import video as video_module
    try:
        video_module.Window.from_display_module().size = size
    except Exception as e:
        print(f"[compare] resize failed: {e}")
    game._update_present_rect()
    print(f"[compare] mode={mode} window={pygame.display.get_window_size()} "
          f"dst_rect={game.dst_rect} display_scale={game.display_scale:.3f} "
          f"render_scale={game.render_scale} hires={game.screen.hires_factor}")

    for _ in range(3):
        game._draw()
    print(f"[compare] gpu ops = {len(game.screen.gpu.ops)} "
          f"enabled = {game.screen.gpu.enabled}")

    surface = game.presenter.renderer.to_surface()
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{name}_{mode}.png")
    pygame.image.save(surface, path)
    print(f"[compare] saved {path} {surface.get_size()}")
    game.running = False


def combine(name, crop=None):
    before = os.path.join(OUT_DIR, f"{name}_before.png")
    after = os.path.join(OUT_DIR, f"{name}_after.png")
    for p in (before, after):
        if not os.path.exists(p):
            raise SystemExit(f"missing {p}; run before/after first")
    a = pygame.image.load(before)
    b = pygame.image.load(after)
    w, h = a.get_size()
    if crop is not None:
        # 逻辑坐标 -> 真实像素（渲染倍率取 3x，与实际采样一致）
        cx, cy, cw, ch = (crop[0] * 3, crop[1] * 3, crop[2] * 3, crop[3] * 3)
    else:
        cw, ch = min(880, w // 3), min(560, h // 3)
        cx, cy = int(w * 0.28), int(h * 0.22)
    pad, label_h = 12, 34
    out = pygame.Surface((cw * 2 + pad * 3, ch + label_h + pad * 2))
    out.fill((28, 28, 32))
    out.blit(a, (pad, pad + label_h), pygame.Rect(cx, cy, cw, ch))
    out.blit(b, (pad * 2 + cw, pad + label_h), pygame.Rect(cx, cy, cw, ch))
    font = pygame.font.SysFont("consolas", 19, bold=True)
    out.blit(font.render("BEFORE  1x canvas upscaled", True, (255, 200, 120)),
             (pad, pad + 7))
    out.blit(font.render("AFTER  GPU native at render scale", True, (140, 255, 170)),
             (pad * 2 + cw, pad + 7))
    path = os.path.join(OUT_DIR, f"{name}_compare.png")
    pygame.image.save(out, path)
    print(f"[compare] saved {path}")


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "menu"
    mode = sys.argv[2] if len(sys.argv) > 2 else "before"
    pygame.init()
    if mode == "combine":
        crop = None
        if len(sys.argv) > 3 and "," in sys.argv[3]:
            crop = [int(v) for v in sys.argv[3].split(",")]
        combine(name, crop)
    else:
        size = (2880, 2160)
        if len(sys.argv) > 3 and "x" in sys.argv[3]:
            w, h = sys.argv[3].split("x")
            size = (int(w), int(h))
        capture(name, mode, size)
    pygame.quit()


if __name__ == "__main__":
    main()
