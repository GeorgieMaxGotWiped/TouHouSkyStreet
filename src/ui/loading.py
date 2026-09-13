# -*- coding: utf-8 -*-
# 关卡载入界面：进入某一面之前，先把该面的关卡数据与贴图资源准备妥当。
#
# 目的：
#   1) 把「点击进入关卡」时原本同步卡住主循环的构建成本（构造关卡 + 布置波次 +
#      组建 PlayingState + 首次贴图解码）搬到一张可见的载入画面上；
#   2) 预热战斗中途才会首次用到的贴图（Boss 立绘、小怪贴图与白色发光层、
#      玩家贴图与光晕、敌弹图集），消除开打后 100~780ms 的单帧毛刺。
#
# 载入步骤用生成器描述：生成器每个 yield 交出一个进度点 (进度, 提示文字)，
# 生成器的返回值就是载入完成后要切换到的状态。LoadingState 在每个进度点之间
# 刷新一次画面，所以进度是看得见的，而不是一段黑屏。

import os
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

import pygame

from src.engine import settings as cfg
from src.engine import boss_art
from src.engine.game import GameState


# 载入界面最短显示时间（秒）：很快的关卡也稍作停留，避免一闪而过
MIN_SHOW_TIME = 0.55
# 进度跑满后至少停留的时间（秒）：让「载入完成」看得清
HOLD_AFTER_DONE = 0.20
# 载入任务允许的最大进度点数（生成器异常时的兜底，避免死循环）
MAX_STEPS = 4096
# Boss 立绘白底抠图单张 300~450ms，交给线程池并行（numpy 会释放 GIL）
BOSS_ART_WORKERS = 4
# 并行阶段的进度上报间隔（秒）
BOSS_ART_POLL = 0.05
# 用进入前的画面当背景，按此色值做减法得到暗化底
BACKDROP_SUB = (112, 108, 132)


class LoadingState(GameState):
    """载入界面。

    task 可以是生成器，也可以是「接收本状态、返回生成器」的可调用对象
    （后者方便在解析出关卡信息后回填标题与副标题）。
    """

    def __init__(self, game, task, title="载入中", subtitle=""):
        super().__init__(game)
        # 生成器（或其它迭代器）直接用；可调用对象视为「按需构建生成器」的工厂
        self.task = task if hasattr(task, "__next__") else task(self)
        self.title = title
        self.subtitle = subtitle
        self.progress = 0.0
        self.message = "正在准备…"
        self.error = None
        self._result = None
        self._done = False
        self._backdrop = None
        self._start_time = pygame.time.get_ticks() / 1000.0
        self._show_until = self._start_time

    # --- 载入流程 ---

    def enter(self, game):
        # 此刻 screen 里还是进入前的画面，取来暗化后当底，切换时不突兀
        try:
            self._backdrop = game.screen.copy()
            self._backdrop.fill(BACKDROP_SUB, special_flags=pygame.BLEND_RGB_SUB)
        except Exception:
            self._backdrop = None
        self._flush()
        self._run_task()
        self._show_until = max(self._start_time + MIN_SHOW_TIME,
                               pygame.time.get_ticks() / 1000.0 + HOLD_AFTER_DONE)

    def _run_task(self):
        """跑完载入步骤；每步之间刷新画面并泵事件，窗口不会假死"""
        for _ in range(MAX_STEPS):
            pygame.event.pump()
            try:
                step = next(self.task)
            except StopIteration as finished:
                self._result = finished.value
                self.message = "载入完成"
                self._finish()
                return
            except Exception as exc:
                # 载入失败不能让游戏卡死：停在界面上等玩家按键回主菜单
                traceback.print_exc()
                self.error = str(exc)
                self.message = "载入失败"
                self._finish()
                return
            if step:
                self.progress, self.message = step
            self._flush()
        self.error = "载入步骤过多"
        self.message = "载入失败"
        self._finish()

    def _finish(self):
        self._done = True
        self.progress = 1.0
        self._flush()

    def update(self, dt):
        if not self._done:
            return
        # 进度已跑满：到达停留时间，或玩家按键/点击时立刻进入
        pressed = bool(self.game.keys_just_pressed) or self.game.mouse_clicked(1)
        if not pressed and pygame.time.get_ticks() / 1000.0 < self._show_until:
            return
        if self._result is None:
            from src.ui.menu import MenuState
            self.game.switch_state(MenuState(self.game))
            return
        self.game.switch_state(self._result)

    # --- 绘制 ---

    def _flush(self):
        """立即绘制并呈现一帧：载入步骤不在主循环的绘制节奏里，必须自己上屏"""
        self.draw(self.game.screen)
        if self.game.presenter is not None:
            self.game.presenter.present(self.game.screen, self.game.dst_rect)
        else:
            self.game._cpu_present()
            pygame.display.flip()

    def draw(self, screen):
        width, height = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT
        if self._backdrop is not None:
            screen.blit(self._backdrop, (0, 0))
        else:
            screen.fill((6, 6, 18))

        panel = pygame.Rect(0, 0, 560, 190)
        panel.center = (width // 2, height // 2)
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG, panel)
        pygame.draw.rect(screen, cfg.COLOR_GRAY, panel, 1)

        title = self.game.font_large.render(self.title, True, cfg.COLOR_YELLOW)
        screen.blit(title, ((width - title.get_width()) // 2, panel.y + 20))
        if self.subtitle:
            sub = self.game.font_small.render(self.subtitle, True, cfg.COLOR_GRAY)
            screen.blit(sub, ((width - sub.get_width()) // 2, panel.y + 64))

        color = cfg.COLOR_RED if self.error else cfg.COLOR_WHITE
        message = self.message if self.error is None else f"载入失败：{self.error}"
        text = self.game.font_small.render(message, True, color)
        screen.blit(text, ((width - text.get_width()) // 2, panel.y + 104))

        frac = max(0.0, min(1.0, self.progress))
        bar = pygame.Rect(panel.x + 46, panel.y + 132, panel.width - 92, 20)
        pygame.draw.rect(screen, (18, 18, 34), bar)
        inner = bar.inflate(-2, -2)
        filled = int(inner.width * frac)
        if filled > 0:
            pygame.draw.rect(screen, cfg.COLOR_GREEN,
                             pygame.Rect(inner.x, inner.y, filled, inner.height))
        pygame.draw.rect(screen, cfg.COLOR_GRAY, bar, 1)
        percent = self.game.font_small.render("%d%%" % int(frac * 100), True,
                                              cfg.COLOR_WHITE)
        screen.blit(percent, (bar.centerx - percent.get_width() // 2,
                              bar.centery - percent.get_height() // 2))

        if self.error:
            hint = "按任意键返回主菜单"
        elif self._done:
            hint = "按任意键立即开始"
        else:
            hint = "正在载入" + "·" * (1 + int(pygame.time.get_ticks() * 0.004) % 3)
        hint_surf = self.game.font_small.render(hint, True, cfg.COLOR_GRAY)
        screen.blit(hint_surf, ((width - hint_surf.get_width()) // 2,
                                panel.y + 162))


# ---------------------------------------------------------------------------
# 资源预热
# ---------------------------------------------------------------------------

def _boss_art_paths(stage):
    """本关要预热的立绘：自机对话立绘 + 面配置立绘 + 对话立绘 + 登场的 Boss。

    自机立绘固定带上：五面的对话立绘是开打后才填进 stage 的，等到那时候再抠图
    就会在对话首次绘制时卡一下。
    """
    paths = [cfg.SELF_SPRITE]
    paths.extend(cfg.stage_boss_art_paths(getattr(stage, "stage_num", 0)))
    for attr in ("dialogue_portraits", "defeat_dialogue_portraits"):
        portraits = getattr(stage, attr, None)
        if portraits:
            paths.extend(portraits.values())
    for boss in (getattr(stage, "mid_boss", None), getattr(stage, "boss", None)):
        path = getattr(boss, "sprite_path", None)
        if path:
            paths.append(path)
    return [path for path in dict.fromkeys(paths) if path]


def _iter_enemy_sprites(stage):
    """遍历本关已布下的所有小怪贴图，产出 (路径, 目标高度)"""
    manager = getattr(stage, "enemy_manager", None)
    waves = []
    if manager is not None:
        waves.extend(getattr(manager, "waves", None) or [])
        waves.extend(wave for _start, wave in getattr(manager, "timed_waves", None) or [])
    waves.extend(getattr(stage, "post_waves", None) or [])

    seen = set()
    for wave in waves:
        for enemy in getattr(wave, "enemies", None) or []:
            height = getattr(enemy, "sprite_height", None)
            if not isinstance(height, (int, float)) or height <= 0:
                continue
            for path in getattr(enemy, "sprite_paths", None) or []:
                key = (path, int(height))
                if path and key not in seen:
                    seen.add(key)
                    yield key


def _warm_enemy_sprite(path, height):
    """小怪贴图 + 白色发光层 + 贴合贴图的判定范围（三者都在首次出场时才算）"""
    from src.entities.enemy import _get_enemy_hitbox_radii, _get_enemy_sprite, _get_outlined_layers

    _get_enemy_sprite(path, height)
    _get_outlined_layers(path, height)
    _get_enemy_hitbox_radii(path, height)


def _warm_player_sprites():
    """自机贴图与光晕（左右朝向各一份，避免第一次横向移动时才生成）"""
    from src.entities import player as player_module

    for path in (cfg.PLAYER_SPRITE_IDLE, cfg.PLAYER_SPRITE_MOVE):
        for flipped in (False, True):
            player_module._get_player_sprite(path, flipped)
            player_module._get_player_glow(path, flipped)


def _warm_portrait(path, scales=(1.0,)):
    """立绘：Boss 白底抠图（战斗立绘用）+ 对话立绘（同一张图在对话里还要按内容裁剪缩放）

    对话立绘按当前渲染倍率生成，正好把这笔「首次生成」的成本从对话出现的那一刻
    挪到载入界面；scales 是本关对话真正会用到的缩放档位（默认 1.0）。
    """
    from src.ui import dialogue

    boss_art.load_sprite(path)
    for scale in scales:
        dialogue.get_portrait(path, scale)


def _warm_bullet_sprite():
    """敌弹图集与玩家子弹贴图"""
    from src.entities import bullet_atlas
    from src.entities.bullet import _get_player_bullet_sprite

    bullet_atlas._load_atlas()
    _get_player_bullet_sprite()


def _warm_spell_bg(stage):
    """符卡背景（暗角 / 中心微光 / 整幅贴图 / 全景贴图）

    这些原本都在「开符那一帧」现算：第 1 面约 12.5ms（暗角 + 微光），
    五面的整幅贴图风格（storm / goldor / maxor）要 80~100ms（PNG 解码为主），
    每次开符都掉帧。这里按风格提前建好，开符帧就只剩贴图。
    """
    from src.engine import spell_bg

    entries = []
    seen = set()
    for attr in ("mid_boss", "boss"):
        boss = getattr(stage, attr, None)
        if boss is None:
            continue
        cards = list(getattr(boss, "spell_cards", None) or [])
        last = getattr(boss, "last_spell", None)
        if last is not None:
            cards.append(last)
        for card in cards:
            key = (getattr(card, "name", "") or "", getattr(card, "bg_style", None))
            if key[0] and key not in seen:
                seen.add(key)
                entries.append(key)
    # 本关稍后才登场的 Boss（五面 BOSS RUSH）按面配置的风格表补齐
    for style in cfg.stage_spell_bg_styles(getattr(stage, "stage_num", 0)):
        entries.append(("", style))
    return spell_bg.preheat(entries)


def _warm_spell_banner(stage):
    """符卡宣言横幅的整幅 Boss 立绘（按渲染倍率缩放的成品）

    这张图只在「某个 Boss 的第一张符卡」才会用到，3x 下首次缩放约 13ms，
    正好落在开符那一帧上——每次打到一个新 Boss 的第一张卡都会卡一下。
    这里在载入界面把它先算好（本关稍后才登场的 Boss 用面配置的立绘表覆盖）。
    """
    from src.entities.boss import (_banner_target_height, _get_boss_sprite,
                                   _get_font, SPELL_BANNER_FONT_SIZE)

    bosses = [boss for boss in (getattr(stage, "mid_boss", None),
                                getattr(stage, "boss", None)) if boss]
    paths = list(cfg.stage_boss_art_paths(getattr(stage, "stage_num", 0)))
    for boss in bosses:
        path = getattr(boss, "sprite_path", None)
        if path:
            paths.append(path)
    for path in dict.fromkeys(paths):
        try:
            _get_boss_sprite(path, _banner_target_height(path), sharp=True)
        except Exception as exc:
            print(f"[Loading] 符卡横幅立绘预热失败 {path}: {exc}")

    # 符卡名字体：字号是这套字体的唯一用途，第一次用要解析字库并建字形缓存（约 5ms）；
    # 有 Boss 在场时连符卡名一起渲染一遍，把字形缓存也填上
    font = _get_font(SPELL_BANNER_FONT_SIZE, bold=True)
    names = []
    for boss in bosses:
        cards = list(getattr(boss, "spell_cards", None) or [])
        last = getattr(boss, "last_spell", None)
        if last is not None:
            cards.append(last)
        names.extend(getattr(card, "name", "") or "" for card in cards)
    # 一条符卡名都没有时（例如本关 Boss 要到中段才登场）也渲染一次，
    # 至少把字库解析与字形缓存建好
    for name in dict.fromkeys(n for n in names if n) or ("A",):
        font.render(name, True, cfg.COLOR_WHITE)


def _collect_assets(stage):
    """收集本关要预热的轻量资源，返回 [(提示文字, 预热函数)]（Boss 立绘另行并行处理）"""
    items = []
    for path, height in _iter_enemy_sprites(stage):
        items.append((os.path.basename(path),
                      lambda p=path, h=height: _warm_enemy_sprite(p, h)))
    items.append(("自机贴图", _warm_player_sprites))
    items.append(("符卡背景", lambda: _warm_spell_bg(stage)))
    items.append(("符卡横幅立绘", lambda: _warm_spell_banner(stage)))
    items.append(("弹幕贴图", _warm_bullet_sprite))
    return items


# ---------------------------------------------------------------------------
# 关卡入场
# ---------------------------------------------------------------------------

def stage_entry_task(game, factory, setup="waves", after=None, skip_title=False,
                     practice_info=None):
    """生成「构建关卡 → 预热资源 → 组建 PlayingState」的载入步骤。

    factory : 返回 Stage 实例的可调用对象
    setup   : "waves" / "mid_boss" / "boss" / None，进入前要预先布置的内容
    after   : 可选回调，接收 Stage 实例，做入口各自的额外调整
    """
    def task(loading):
        from src.ui.menu import PlayingState

        yield 0.04, "构建关卡数据…"
        stage = factory()
        stage_num = getattr(stage, "stage_num", 0)
        loading.title = f"第 {stage_num} 面"
        loading.subtitle = getattr(stage, "name", "") or ""

        yield 0.12, "布置敌机波次…"
        if setup == "waves":
            stage.setup_waves()
        elif setup == "mid_boss":
            stage.setup_mid_boss()
        elif setup == "boss":
            stage.setup_boss()
        if after is not None:
            after(stage)

        # Boss 立绘最重（单张 300~450ms 抠图 + 对话立绘裁剪）：先丢进线程池并行，
        # 主线程同时做轻量预热，进度条两边都在动
        portraits = _boss_art_paths(stage)
        # 对话里会用到 1.0 之外的缩放档（如 Kaeman 1.5），一并预热
        portrait_scales = [1.0]
        for value in (getattr(stage, "dialogue_portrait_scales", None) or {}).values():
            try:
                value = float(value)
            except (TypeError, ValueError):
                continue
            if value not in portrait_scales:
                portrait_scales.append(value)
        pool = None
        futures = []
        if portraits:
            pool = ThreadPoolExecutor(max_workers=min(BOSS_ART_WORKERS, len(portraits)))
            futures = [pool.submit(_warm_portrait, path, portrait_scales)
                       for path in portraits]

        assets = _collect_assets(stage)
        total = max(1, len(assets))
        for index, (label, warm) in enumerate(assets):
            yield 0.10 + 0.45 * index / total, f"载入贴图 {label}"
            warm()

        if futures:
            try:
                while any(not future.done() for future in futures):
                    loaded = sum(1 for future in futures if future.done())
                    yield (0.55 + 0.35 * loaded / len(futures),
                           f"载入 Boss 立绘 {loaded}/{len(futures)}")
                    time.sleep(BOSS_ART_POLL)
            finally:
                pool.shutdown()
        yield 0.92, "准备战斗界面…"
        state = PlayingState(game, stage, skip_title=skip_title,
                             practice_info=practice_info)
        return state

    return task


def start_stage(game, factory, setup="waves", after=None, skip_title=False,
                practice_info=None):
    """统一的关卡入场入口：先显示载入界面，构建完成后再切到战斗状态。"""
    game.switch_state(LoadingState(
        game, stage_entry_task(game, factory, setup=setup, after=after,
                               skip_title=skip_title,
                               practice_info=practice_info)))
