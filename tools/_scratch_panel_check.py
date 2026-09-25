# -*- coding: utf-8 -*-
"""复用面板池正确性检查：同一状态、冻结时钟下，复用池与「每帧新建面板」必须逐像素一致

复用池（hires.scratch_panel）省掉的是每帧新建表面与首次上传；风险在于同一块表面
跨帧复用后，显卡上那张纹理如果不重传，就会一直显示旧内容。检查办法是先把池子用脏
（同一状态连画两帧），推进到新状态后再用池子画一帧，和同状态下「每帧新建」画出来的
那一帧逐像素比对 —— 有残留就一定对不上。

用法：python tools\\_scratch_panel_check.py <符卡序号> [帧数] [倍率]
"""
import os
import random
import sys

OUT_DIR = os.path.join(os.getcwd(), "previews", "scratch_panel")

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import pygame

from src.engine import game as game_module, settings as cfg, hires, painter


def run(idx, frames, scale):
    random.seed(20260918)
    ticks = pygame.time.get_ticks
    pygame.time.get_ticks = lambda: 654321     # 冻结动画相位，几次绘制才可比
    orig_cfg = game_module.load_user_config
    game_module.load_user_config = lambda: dict(orig_cfg(), fullscreen=False,
                                                render_scale_index=scale - 1)
    pygame.init()
    game = game_module.Game()
    from pygame._sdl2 import video as video_module
    video_module.Window.from_display_module().size = (960 * scale, 720 * scale)
    from src.ui.menu import PlayingState
    from src.stages.stage6 import Stage6_FinalApproach

    real_scratch = hires.scratch_panel

    def fresh(screen, size):
        return hires.panel(size, hires.entity_factor(screen))

    try:
        state = PlayingState(game, Stage6_FinalApproach())
        game.push_state(state)
        game._update_present_rect()
        stage = state.stage
        stage.setup_boss()
        stage.phase = "dialogue"
        from src.entities import player as player_module
        player_module.Player.can_be_hit = lambda self: False
        assert stage.skip_to_kaeman_spell(idx)
        boss = stage.boss
        boss.spell_banner_active = False
        boss._spell_settle_frames = 99
        boss.x, boss.y = boss.target_x, boss.target_y
        for _ in range(frames):
            state.update(1 / 60.0)
            boss.hp = max(boss.hp, boss.max_hp)
        painter.set_enabled(True)
        name = boss.current_spell.name
        # 先把复用池用脏：同一状态连画两帧，池里面板就带着上一帧的内容
        game._draw()
        game._draw()
        # 推进到新状态，再用复用池画一帧：重传没生效的话这里会显示旧内容
        for _ in range(6):
            state.update(1 / 60.0)
            boss.hp = max(boss.hp, boss.max_hp)
        if os.environ.get("S6_NO_BG"):
            boss.spell_bg = None      # 排除符卡背景（1x 那层）的干扰
        game._draw()
        a = game.presenter.renderer.to_surface().copy()
        # 同一状态换成「每帧新建面板」再画一帧：基准
        hires.scratch_panel = fresh
        game._draw()
        b = game.presenter.renderer.to_surface().copy()
        # 换回复用池再画一遍（池里仍是该状态的旧内容）：应当仍等于基准
        hires.scratch_panel = real_scratch
        game._draw()
        c = game.presenter.renderer.to_surface().copy()
        # 对照：同一状态、连续两次都用「新建面板」画 —— 两次之间的差异只可能来自
        # 与面板无关的东西（符卡背景那层是按真实时钟动的），用它当噪声本底
        hires.scratch_panel = fresh
        game._draw()
        d = game.presenter.renderer.to_surface().copy()
    finally:
        hires.scratch_panel = real_scratch
        pygame.time.get_ticks = ticks
        game.running = False
        pygame.quit()
    return (a, b, c, d), name


def diff(img, ref, rect):
    worst = 0
    worst_at = None
    total = 0
    count = 0
    for y in range(0, rect.height, 2):
        for x in range(0, rect.width, 2):
            ca = img.get_at((rect.x + x, rect.y + y))
            cb = ref.get_at((rect.x + x, rect.y + y))
            d = max(abs(ca[0] - cb[0]), abs(ca[1] - cb[1]), abs(ca[2] - cb[2]))
            total += d
            count += 1
            if d > worst:
                worst = d
                worst_at = (x, y)
    return worst, worst_at, total / float(count)


def main():
    idx = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    frames = int(sys.argv[2]) if len(sys.argv) > 2 else 120
    scale = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    (a, b, c, d), name = run(idx, frames, scale)
    k = a.get_width() / float(cfg.SCREEN_WIDTH)
    rect = pygame.Rect(int(cfg.BATTLE_OFFSET_X * k), int(cfg.BATTLE_OFFSET_Y * k),
                       int(cfg.BATTLE_AREA_WIDTH * k),
                       int(cfg.BATTLE_AREA_HEIGHT * k))
    for label, img in (("复用池(第 1 次)", a), ("复用池(第 2 次)", c),
                       ("对照：新建(第 2 次)", d)):
        worst, at, avg = diff(img, b, rect)
        print("spell%d [%s] %s vs 每帧新建：最大通道差=%d（%s）平均差=%.4f"
              % (idx, name, label, worst, at, avg))
    os.makedirs(OUT_DIR, exist_ok=True)
    for label, img in (("pool", a), ("fresh", b)):
        out = pygame.Surface((rect.width, rect.height))
        out.blit(img, (0, 0), rect)
        pygame.image.save(out, os.path.join(OUT_DIR, "pool_%s_%d.png" % (label, idx)))


if __name__ == "__main__":
    main()
