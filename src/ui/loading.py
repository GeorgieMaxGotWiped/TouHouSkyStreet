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
from src.engine import painter
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
# 底图暗化：按此色值从背景图里做减法
BACKDROP_SUB = (112, 108, 132)
# 载入面板与进度条的逻辑尺寸（进度条左右各留 46）
PANEL_W, PANEL_H = 560, 190
BAR_W, BAR_H = PANEL_W - 92, 20

# 暗化后的底图缓存：同一张背景图只做一次减法（键含源图引用，防止 id 复用）
_BACKDROP_CACHE = {}


def _dimmed_backdrop(source):
    """把一张背景图按 BACKDROP_SUB 压暗（结果缓存，同一张图不重复压）"""
    if source is None:
        return None
    entry = _BACKDROP_CACHE.get(id(source))
    if entry is not None and entry[0] is source:
        return entry[1]
    try:
        surf = source.copy()
        surf.fill(BACKDROP_SUB, special_flags=pygame.BLEND_RGB_SUB)
    except Exception:
        return None
    if len(_BACKDROP_CACHE) > 4:
        _BACKDROP_CACHE.clear()
    _BACKDROP_CACHE[id(source)] = (source, surf)
    return surf


def _default_backdrop(game):
    """拿不到来源界面背景图时的兜底：暗化的主菜单背景"""
    try:
        from src.ui.menu import load_background
        return load_background(cfg.MENU_BACKGROUND,
                               (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT),
                               game.screen.bake_factor())
    except Exception:
        return None


def _build_panel(target, k):
    """载入面板底 / 外框的预烤画法（尺寸见 PANEL_W / PANEL_H）"""
    rect = (0, 0, PANEL_W, PANEL_H)
    painter.bake_rect(target, k, cfg.COLOR_PANEL_BG, rect)
    painter.bake_rect(target, k, cfg.COLOR_GRAY, rect, 1)


def _build_bar(filled):
    """进度条的底 / 进度 / 外框预烤画法（filled 已量化到整像素）"""
    def build(target, k):
        rect = (0, 0, BAR_W, BAR_H)
        painter.bake_rect(target, k, (18, 18, 34), rect)
        if filled > 0:
            painter.bake_rect(target, k, cfg.COLOR_GREEN, (1, 1, filled, BAR_H - 2))
        painter.bake_rect(target, k, cfg.COLOR_GRAY, rect, 1)
    return build


class LoadingState(GameState):
    """载入界面。

    task 可以是生成器，也可以是「接收本状态、返回生成器」的可调用对象
    （后者方便在解析出关卡信息后回填标题与副标题）。

    backdrop 是底图（一般由 start_stage 传来源界面的背景图），不给时退回主菜单背景。
    """

    def __init__(self, game, task, title="载入中", subtitle="", backdrop=None):
        super().__init__(game)
        # 生成器（或其它迭代器）直接用；可调用对象视为「按需构建生成器」的工厂
        self.task = task if hasattr(task, "__next__") else task(self)
        self.title = title
        self.subtitle = subtitle
        self._backdrop_src = backdrop
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
        # 底图取「进入前那个界面」的背景图（start_stage 带过来），暗化后当底，切换时
        # 不突兀。早先这里是抓 1x 画布的快照——但界面都改走显卡路径之后画布上什么都
        # 没有了（快照全透明），所以不能再靠画布。
        source = self._backdrop_src or _default_backdrop(game)
        self._backdrop = _dimmed_backdrop(source)
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
        self.game.draw_frame()

    def draw(self, screen):
        width, height = cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT
        # 底图 / 面板 / 进度条都走显卡层（与主菜单同一套路）：底图直接贴，矩形先在
        # 「逻辑尺寸 x 渲染倍率」的表面上烤好，再由显卡 1:1 贴出，边框不会被放大糊掉
        if self._backdrop is not None:
            screen.blit_gpu(self._backdrop, (0, 0))
        else:
            screen.fill_gpu((6, 6, 18))

        panel = pygame.Rect(0, 0, PANEL_W, PANEL_H)
        panel.center = (width // 2, height // 2)
        screen.blit_baked(("loading_panel", PANEL_W, PANEL_H), panel.topleft,
                          (PANEL_W, PANEL_H), _build_panel)

        title = self.game.font_large.render(self.title, True, cfg.COLOR_YELLOW)
        screen.blit_gpu(title, ((width - title.get_width()) // 2, panel.y + 20))
        if self.subtitle:
            sub = self.game.font_small.render(self.subtitle, True, cfg.COLOR_GRAY)
            screen.blit_gpu(sub, ((width - sub.get_width()) // 2, panel.y + 64))

        color = cfg.COLOR_RED if self.error else cfg.COLOR_WHITE
        message = self.message if self.error is None else f"载入失败：{self.error}"
        text = self.game.font_small.render(message, True, color)
        screen.blit_gpu(text, ((width - text.get_width()) // 2, panel.y + 104))

        frac = max(0.0, min(1.0, self.progress))
        bar = pygame.Rect(panel.x + 46, panel.y + 132, BAR_W, BAR_H)
        # 进度量化到整像素做缓存 key：不量化的话每帧都会烤一张新图（缓存永远命不中）
        filled = int((BAR_W - 2) * frac)
        screen.blit_baked(("loading_bar", BAR_W, BAR_H, filled), bar.topleft,
                          (BAR_W, BAR_H), _build_bar(filled))
        percent = self.game.font_small.render("%d%%" % int(frac * 100), True,
                                              cfg.COLOR_WHITE)
        screen.blit_gpu(percent, (bar.centerx - percent.get_width() // 2,
                                  bar.centery - percent.get_height() // 2))

        if self.error:
            hint = "按任意键返回主菜单"
        elif self._done:
            hint = "按任意键立即开始"
        else:
            hint = "正在载入" + "·" * (1 + int(pygame.time.get_ticks() * 0.004) % 3)
        hint_surf = self.game.font_small.render(hint, True, cfg.COLOR_GRAY)
        screen.blit_gpu(hint_surf, ((width - hint_surf.get_width()) // 2,
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
    from src.engine import hires

    _get_enemy_sprite(path, height)
    # 战斗中实际画的是按渲染倍率放大的那一张（战斗区实体层），一并算好
    _get_enemy_sprite(path, height, hires.scale())
    _get_outlined_layers(path, height)
    _get_enemy_hitbox_radii(path, height)


def _warm_player_sprites():
    """自机贴图与光晕（左右朝向各一份，避免第一次横向移动时才生成）"""
    from src.entities import player as player_module
    from src.engine import hires

    factor = hires.scale()
    for path in (cfg.PLAYER_SPRITE_IDLE, cfg.PLAYER_SPRITE_MOVE):
        for flipped in (False, True):
            player_module._get_player_sprite(path, flipped, factor)
            player_module._get_player_glow(path, flipped, factor)


def _warm_portrait(path, scales=(1.0,), harmonize=True):
    """立绘：Boss 白底抠图（战斗立绘用）+ 对话立绘（同一张图在对话里还要按内容裁剪缩放）

    对话立绘按当前渲染倍率生成，正好把这笔「首次生成」的成本从对话出现的那一刻
    挪到载入界面；scales 是本关对话真正会用到的缩放档位（默认 1.0）。
    harmonize 与建对话框时的取值一致，免得预热了另一套、对话开场还是现算。
    """
    from src.ui import dialogue

    boss_art.load_sprite(path)
    for scale in scales:
        dialogue.get_portrait(path, scale, harmonize=harmonize)


def _warm_bullet_sprite():
    """敌弹图集与当前自机的子弹贴图"""
    from src.entities import bullet_atlas
    from src.engine import hires
    from src.entities.bullet import _get_player_bullet_sprite

    bullet_atlas._load_atlas()
    # 自机弹贴图在战斗区是按渲染倍率原生绘制的，预热要算同一个倍率的那一份；
    # 1x 那份顺带备着（没有显卡路径时战斗区用的正是它）
    #
    # 自机弹贴图还要按「当前运动方向」转正（见 bullet._draw_player_sprite）：每个方向在
    # 缓存里都是独立一张，所以这里连同方向一起烤 —— 弓手的扇形箭各自朝不同方向，
    # 只预热朝上那一张的话，第一次五连发会一路现转（每转一个档就是一次缩放 +
    # 旋转）。方向枚举与发射共用一份公式（cfg.player_shot_headings）。
    # (贴图路径, 转正角)：None = 当前自机默认那一张
    variants = [(None, None)]
    # 机体弹幕差分里额外登记的贴图（弓手中间那条爆炸箭）：同场混发，
    # 只预热机体默认那一张的话，爆炸箭第一次出现的那几帧要现读现缩
    for extra in cfg.player_shot_extra_sprites():
        variants.append((extra["path"], extra["angle"]))
    # None = 不转的那张（贴图读取失败退回图元绘制时用不上，但老路径会取它）
    headings = [None] + list(cfg.player_shot_headings())
    for factor in sorted({1, hires.scale()}):
        for path, angle in variants:
            for heading in headings:
                _get_player_bullet_sprite(factor, path, angle, heading)
    # 弹种配色是逐像素扫原图算出来的（每个槽位一次，之后缓存）——第一次用到
    # 某个弹种的那几帧会平白多出几毫秒，索性在载入界面把所有槽位一次算完
    bullet_atlas.warm_color_signatures()


def _warm_spell_sprites(stage):
    """开打之后才会第一次现读的贴图（见 cfg.stage_spell_sprites）

    这些图第一次用是在符卡展开后的头几帧：第 4/6 面的巨人解码 12ms、石像兵 7ms，
    第 6 面凋零幽影更是 25~45ms —— 一次就是好几帧的卡顿。载入界面按表提前解码，
    开符帧只剩一次缩放。

    六面要塞段的四位王之门徒残影也算这一档：它们用的是「Boss 立绘套组」里那四位
    的立绘（new 套组 2040x3072，解码 55~85ms），登场那一帧正好是残影淡入的头几帧。
    """
    from src.engine import boss_art

    done = 0
    for path in cfg.stage_spell_sprites(getattr(stage, "stage_num", 0)):
        if boss_art.load_sprite(path) is not None:
            done += 1
    return done


def _warm_spell_effects(stage):
    """符卡演出的「关卡专属」重资源：由各面自己申报（Stage.warm_spell_effects）

    背景 / 立绘 / 贴图那三步是引擎通用表，够不到关卡自己写在 draw_foreground 里的
    东西。例如五面焚符「Nuclear Frenzy」的白热太阳底图要在开符后第一次绘制时
    现算 44ms，正好卡在开符第 2 帧上。
    """
    hook = getattr(stage, "warm_spell_effects", None)
    if hook is None:
        return 0
    try:
        return int(hook() or 0)
    except Exception as exc:
        print(f"[Loading] 符卡演出特效预热失败: {exc}")
        return 0


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


def _warm_spell_banner(stage, game=None):
    """符卡宣言横幅的整幅 Boss 立绘（按渲染倍率缩放的成品）

    这张图只在「某个 Boss 的第一张符卡」才会用到，3x 下首次缩放约 13ms，
    正好落在开符那一帧上——每次打到一个新 Boss 的第一张卡都会卡一下。
    这里在载入界面把它先算好（本关稍后才登场的 Boss 用面配置的立绘表覆盖）。
    成品还顺手传成显卡纹理：1728x1728（11.9MB）第一次上屏要 3.5ms，同样是
    开符那一帧的固定开销，载入界面的显卡缓存与战斗时是同一份。
    """
    from src.entities.boss import (_banner_target_height, _get_boss_sprite,
                                   _get_banner_text, _get_font,
                                   SPELL_BANNER_FONT_SIZE)

    presenter = getattr(game, "presenter", None) if game is not None else None
    bosses = [boss for boss in (getattr(stage, "mid_boss", None),
                                getattr(stage, "boss", None)) if boss]
    paths = list(cfg.stage_boss_art_paths(getattr(stage, "stage_num", 0)))
    for boss in bosses:
        path = getattr(boss, "sprite_path", None)
        if path:
            paths.append(path)
    # 符卡演出会临时换上来的立绘（例如第 4 面变巨人）也算「横幅立绘」：
    # 换图那一帧要把整幅图按横幅高度现缩一次（3x 实测 5.7ms）
    swaps = cfg.stage_boss_art_swaps(getattr(stage, "stage_num", 0))
    paths.extend(path for path, _ in swaps)
    for path in dict.fromkeys(paths):
        try:
            sprite = _get_boss_sprite(path, _banner_target_height(path), sharp=True)
            if sprite is not None and presenter is not None:
                presenter.warm_texture(sprite)
        except Exception as exc:
            print(f"[Loading] 符卡横幅立绘预热失败 {path}: {exc}")

    # 战斗中的 Boss 本体是一张按自身高度缩的小图，走战斗区实体层（见 hires.blit_entity）：
    # 首次登场 / 符卡换装那一帧同样要现缩一次（3x 实测 2ms 上下）。1x 那一份也要备好，
    # 它仍是碰撞 Mask 的来源（判定范围不随画面设置变）。
    battle_sprites = [(boss.sprite_path, getattr(boss, "sprite_height", None))
                      for boss in bosses]
    battle_sprites.extend(swaps)
    for path, battle_h in battle_sprites:
        if not path or not battle_h:
            continue
        try:
            _get_boss_sprite(path, battle_h)
            sprite = _get_boss_sprite(path, battle_h, sharp=True)
            if sprite is not None and presenter is not None:
                presenter.warm_texture(sprite)
        except Exception as exc:
            print(f"[Loading] Boss 本体立绘预热失败 {path}: {exc}")

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

    # 上面只填了字形缓存，开符那一帧还要现 render 两遍（带色投影 + 白字）再各
    # 抠一份半透明副本（_get_banner_text，实测 1.4ms）。宣言用的颜色是 Boss 自己
    # 的 color，和 _draw_spell_banner 里的调用保持一致，这里按 Boss 各烤一份。
    for boss in bosses:
        color = getattr(boss, "color", None)
        if color is None:
            continue
        cards = list(getattr(boss, "spell_cards", None) or [])
        last = getattr(boss, "last_spell", None)
        if last is not None:
            cards.append(last)
        for name in dict.fromkeys(getattr(card, "name", "") or ""
                                  for card in cards):
            if name:
                try:
                    _get_banner_text(name, color)
                except Exception as exc:
                    print(f"[Loading] 符卡宣言文字预热失败 {name}: {exc}")


def _collect_assets(stage, game=None):
    """收集本关要预热的轻量资源，返回 [(提示文字, 预热函数)]（Boss 立绘另行并行处理）"""
    items = []
    for path, height in _iter_enemy_sprites(stage):
        items.append((os.path.basename(path),
                      lambda p=path, h=height: _warm_enemy_sprite(p, h)))
    items.append(("自机贴图", _warm_player_sprites))
    items.append(("符卡背景", lambda: _warm_spell_bg(stage)))
    items.append(("符卡横幅立绘", lambda: _warm_spell_banner(stage, game)))
    items.append(("符卡贴图", lambda: _warm_spell_sprites(stage)))
    items.append(("符卡演出特效", lambda: _warm_spell_effects(stage)))
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
        # 关卡可以自带标题（Ex 面显示「Extra Stage」而不是「第 7 面」）
        loading.title = getattr(stage, "loading_title", None) or f"第 {stage_num} 面"
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
            # 取景补偿取值与建对话框时一致（见 ui/menu.py），否则预热的是另一套、开场还要现算
            harmonize = getattr(stage, "dialogue_portrait_harmonize", True)
            futures = [pool.submit(_warm_portrait, path, portrait_scales, harmonize)
                       for path in portraits]

        assets = _collect_assets(stage, game)
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
                practice_info=None, backdrop=None):
    """统一的关卡入场入口：先显示载入界面，构建完成后再切到战斗状态。

    backdrop 是载入界面的底图；不给时自动取「来源界面」的背景图（主菜单 / 练习 /
    休整这类界面都有一张背景图），再退到主菜单背景。
    """
    if backdrop is None:
        candidate = getattr(game.current_state, "background", None)
        # 战斗界面（Stage）也有同名属性，但那是伪 3D 地面对象，不能当底图用
        backdrop = candidate if isinstance(candidate, pygame.Surface) else None
    game.switch_state(LoadingState(
        game, stage_entry_task(game, factory, setup=setup, after=after,
                               skip_title=skip_title,
                               practice_info=practice_info),
        backdrop=backdrop))
