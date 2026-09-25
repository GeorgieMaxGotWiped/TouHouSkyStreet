# -*- coding: utf-8 -*-
# 自机选择界面：主菜单「开始游戏」之后、难度选择之前，选一位自机
#
# 构图：整幅键艺图压暗做底（这张图里本来就有自机立绘与标题 LOGO，所以先压暗，立绘
# 与列表才立得住）—— 立绘不再套进面板，而是直接站在背景上；右侧一列是全部自机，
# 选中的那一位在列表里展开称号与介绍；左下角是当前选择的徽记与名牌；右下角「确定」。
# 一屏之内既能看清「这一位是谁」，也能看到「还有哪几位」。
#
# 自机清单、名字、介绍文字都来自 src/engine/settings.py 的自机登记表，这一屏只管
# 排版与交互：以后加角色只需在 settings 里登记一行，这里会自动多出一位。

import pygame

from src.engine import settings as cfg
from src.engine import hires
from src.engine import painter
from src.engine.game import GameState
from src.ui.menu import load_background, refresh_background
from src.ui.anim import Entrance


# --- 布局（逻辑坐标 960x720）---
TITLE_Y = 16
SUBTITLE_DY = 46            # 副标题贴着标题右缘、压在它右下角
# 立绘：站在键艺图上，四位自机脚底对齐同一条线
PORTRAIT_CENTER_X = 312
PORTRAIT_FEET_Y = 616
PORTRAIT_HEIGHT = 548
# 右列：自机列表
INFO_RECT = pygame.Rect(448, 88, 494, 518)
INFO_HEAD_DY = 18           # 顶部「自机选择」那一行
INFO_PAD = 26
LIST_DY = 74                # 列表首行
ROW_STEP = 58               # 每行名字的纵向步长
ROW_TITLE_DY = 30           # 选中行里称号相对于名字的偏移
ROW_INTRO_STEP = 24         # 展开的介绍行行距
ROW_EXTRA_GAP = 10          # 展开的行与下一行之间额外留出的距离
# 左下角：当前选择徽记 + 名牌
BADGE_RECT = pygame.Rect(48, 610, 60, 60)
PLATE_RECT = pygame.Rect(120, 616, 340, 48)
# 右下角的「确定」（鼠标用户的落点；键盘是 Enter/Z）
CONFIRM_BTN = pygame.Rect(760, 620, 140, 46)
# 底部一条操作提示（贴屏幕下缘居中）
HINT_Y = 688
HINT_TEXT = "↑↓←→ / 滚轮 切换选择    点击列表换人    Enter/Z 确定    Esc 返回"
# 背景压暗层：主菜单那张键艺图里本来就有自机立绘与标题 LOGO，不压暗的话这一屏
# 会变成「两个自机打架」，压暗后立绘与列表才立得住（其余界面没有这个冲突）
BACKGROUND_DIM = 195
# 立绘那一侧的渐暗：键艺图左边站着的就是主菜单那位自机，与本屏的立绘叠在一起会糊
# 成一团。所以从画面左缘到 LEFT_SHADE_W 再压一层由深到无的黑色 —— 立绘画在这一层
# 之上，于是背景里的人物沉下去、立绘浮起来（预烤成一张图，每帧只有一次贴图；渐变
# 是低频的，竖带按逻辑像素烤出来也看不出台阶）
LEFT_SHADE_W = 560
LEFT_SHADE_ALPHA = 130
LEFT_SHADE_COLS = 56
# 未选中行的名字：用自机代表色压暗后的颜色（看得出来是谁，但不抢选中那一位）
ROW_IDLE_DIM = 0.45

# 立绘缓存：key = (贴图路径, 目标高度, 渲染倍率)
_PORTRAIT_CACHE = {}


def _portrait(path, height):
    """立绘：按内容裁剪后缩放到目标高度，并写成带倍率标记的高分辨率表面。

    与对话立绘同理 —— 画在 1x 画布上的图会被整幅放大糊掉，这里直接按渲染倍率
    缩放到该倍率的原生像素，显卡可以 1:1 贴出来。
    """
    factor = hires.scale()
    key = (path, int(height), factor)
    if key in _PORTRAIT_CACHE:
        return _PORTRAIT_CACHE[key]
    surf = None
    try:
        img = pygame.image.load(path).convert_alpha()
        bbox = img.get_bounding_rect(min_alpha=8)
        if bbox.width > 0 and bbox.height > 0:
            img = img.subsurface(bbox)
        size = (max(1, int(round(img.get_width() * height / img.get_height()))),
                int(height))
        surf = hires.scaled_image(img, size, factor)
    except Exception as exc:
        print(f"[CharacterSelect] Failed to load portrait {path}: {exc}")
    if len(_PORTRAIT_CACHE) > 8:
        _PORTRAIT_CACHE.clear()
    _PORTRAIT_CACHE[key] = surf
    return surf


def _bake_plate(logical_size, fill=None, border=None, border_w=1):
    """一块底板的预烤画法（与练习界面同一套路：按倍率作画，边框才不会被放大糊掉）"""
    def build(target, k):
        rect = (0, 0, logical_size[0], logical_size[1])
        if fill is not None:
            painter.bake_rect(target, k, fill, rect)
        if border is not None:
            painter.bake_rect(target, k, border, rect, border_w)
    return build


def _draw_plate(screen, tag, rect, fill=None, border=None, border_w=1, opacity=255):
    """把一块底板交给显卡贴出（按参数烤成图并缓存，之后每帧只剩一次贴图）"""
    screen.blit_baked((tag, rect.size, fill and tuple(fill),
                       border and tuple(border), border_w),
                      rect.topleft, rect.size,
                      _bake_plate(rect.size, fill, border, border_w), opacity)


def _panel(screen, rect, alpha=160, opacity=255):
    """半透明底板（右列自机列表的底）：不描边 —— 立绘压过来时描边会露出「盒子」"""
    _draw_plate(screen, "chara_panel", rect, fill=(0, 0, 0, alpha),
                opacity=opacity)


def _bake_left_shade(size):
    """左侧渐暗层的预烤画法：一条条竖带拼出「由深到无」的黑色"""
    def build(target, k):
        step = size[0] / float(LEFT_SHADE_COLS)
        for i in range(LEFT_SHADE_COLS):
            k_i = 1.0 - i / float(LEFT_SHADE_COLS - 1)
            alpha = int(round(LEFT_SHADE_ALPHA * k_i ** 1.7))
            if alpha <= 0:
                continue
            x0 = int(round(i * step))
            x1 = int(round((i + 1) * step))
            painter.bake_rect(target, k, (0, 0, 0, alpha),
                              (x0, 0, max(1, x1 - x0), size[1]))
    return build


def _draw_marker(screen, center, color, selected, opacity=255):
    """行首的圆点：选中的填实、其余空心（不依赖字体里的 ● / ○ 字形）"""
    size = 14
    rect = pygame.Rect(center[0] - size // 2, center[1] - size // 2, size, size)

    def build(target, k):
        middle = (size // 2, size // 2)
        if selected:
            painter.bake_circle(target, k, color, middle, size // 2)
        else:
            painter.bake_circle(target, k, (108, 108, 116), middle, size // 2, 1)

    screen.blit_baked(("chara_mark", size, tuple(color), bool(selected)),
                      rect.topleft, rect.size, build, opacity)


def _dim(color, factor):
    """把代表色压暗一档（未选中行的名字用）"""
    return tuple(int(v * factor) for v in color)


def _blit_centered(screen, surf, rect, opacity=255):
    """把一张（逻辑尺寸的）表面贴到矩形正中"""
    screen.blit_gpu(surf, (rect.x + (rect.width - surf.get_width()) // 2,
                           rect.y + (rect.height - surf.get_height()) // 2),
                    alpha=opacity)


def _initial(label):
    """名片 / 徽记里用的一个字母（取显示名里的第一个西文字符）"""
    for char in label:
        if char.isascii() and char.isalpha():
            return char.upper()
    return label[:1]


class CharacterSelectState(GameState):
    """出征前选择自机：左边立绘站在键艺图上，右边一列自机，左下角徽记 + 名牌。"""

    def __init__(self, game, extra=False):
        super().__init__(game)
        # extra=True：从主菜单「Extra Stage」进来的 Ex 面流程（不经仓库出征）
        self.extra = bool(extra)
        self.background = load_background(cfg.MENU_BACKGROUND,
                                          (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT),
                                          game.screen.bake_factor())
        self.keys = list(cfg.PLAYER_CHARACTER_KEYS)
        current = cfg.get_player_character()
        self.index = self.keys.index(current) if current in self.keys else 0
        self.intro = Entrance()

    def enter(self, game):
        self.game.stop_music()
        self.intro.reset()

    @property
    def character(self):
        return self.keys[self.index]

    def _rows(self):
        """自机列表的每一行：(角色键, 可点击区域)。

        选中的那一行在列表里展开（称号 / 分隔线 / 介绍），所以下面的行会整体下移 ——
        绘制与点击判定都从这里取矩形，两边不会各写一套。
        """
        rows = []
        y = INFO_RECT.y + LIST_DY
        for key in self.keys:
            height = ROW_STEP
            if key == self.character:
                height += (ROW_TITLE_DY + 22
                           + len(cfg.PLAYER_CHARACTER_INTROS.get(key, ())) * ROW_INTRO_STEP
                           + ROW_EXTRA_GAP)
            rows.append((key, pygame.Rect(INFO_RECT.x + INFO_PAD - 12, y - 8,
                                          INFO_RECT.width - 2 * INFO_PAD + 24,
                                          height)))
            y += height
        return rows

    def _move(self, direction):
        if len(self.keys) < 2:
            return
        self.index = (self.index + direction) % len(self.keys)
        self.game.play_sfx("cursor")

    def _confirm(self):
        self.game.set_player_character(self.character)
        self.game.play_sfx("ok")
        from src.ui.difficulty import DifficultySelectState
        self.game.switch_state(DifficultySelectState(self.game, extra=self.extra))

    def update(self, dt):
        self.intro.update(dt)
        keys = self.game.keys_just_pressed
        if (keys.get(pygame.K_ESCAPE, False) or keys.get(pygame.K_x, False)
                or keys.get(pygame.K_BACKSPACE, False)):
            from src.ui.menu import MenuState
            self.game.switch_state(MenuState(self.game))
            return

        # 列表是竖排的，所以上下与左右四个方向都收（上下更顺手，左右是老习惯）
        if keys.get(pygame.K_LEFT, False) or keys.get(pygame.K_a, False):
            self._move(-1)
        if keys.get(pygame.K_RIGHT, False) or keys.get(pygame.K_d, False):
            self._move(1)
        if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
            self._move(-1)
        if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
            self._move(1)
        wheel = self.game.wheel_direction()
        if wheel:
            self._move(wheel)

        if (keys.get(pygame.K_RETURN, False) or keys.get(pygame.K_z, False)
                or keys.get(pygame.K_SPACE, False)):
            self._confirm()
            return

        # 鼠标：点列表里的一行换人，点「确定」出征
        mp = self.game.mouse_pos
        if self.game.mouse_clicked(1):
            if CONFIRM_BTN.collidepoint(mp):
                self._confirm()
                return
            for key, rect in self._rows():
                if rect.collidepoint(mp):
                    if key != self.character:
                        self.index = self.keys.index(key)
                        self.game.play_sfx("cursor")
                    return

    # --- 绘制 ---

    def draw(self, screen):
        background = refresh_background(self, screen)
        if background:
            screen.blit_gpu(background, (0, 0))
        else:
            screen.fill_gpu((4, 4, 16))
        _draw_plate(screen, "chara_dim",
                    pygame.Rect(0, 0, cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT),
                    fill=(0, 0, 0, BACKGROUND_DIM))
        # 立绘那一侧的渐暗（画在立绘之下：背景里的人物沉下去，立绘浮起来）
        shade = (LEFT_SHADE_W, cfg.SCREEN_HEIGHT)
        screen.blit_baked(("chara_shade", shade), (0, 0), shade,
                          _bake_left_shade(shade))

        title = self.game.font_large.render("选择自机", True, cfg.COLOR_YELLOW)
        title_x = (cfg.SCREEN_WIDTH - title.get_width()) // 2
        # 进场动效：标题 -> 副标题 -> 立绘 -> 列表 -> 徽记 -> 按钮，依次错位淡入
        alpha, dy = self.intro.item(0)
        screen.blit_gpu(title, (title_x, TITLE_Y - dy), alpha=alpha)

        sub_text = ("Extra Stage · 裂隙 ~ The Rift" if self.extra
                    else "Character Select")
        sub = self.game.font_small.render(
            sub_text, True, cfg.COLOR_YELLOW if self.extra else cfg.COLOR_GRAY)
        alpha, dy = self.intro.item(0.4)
        # 副标题右对齐标题右缘（而不是整幅居中）：标题下面挂着一行小字
        screen.blit_gpu(sub, (title_x + title.get_width() - sub.get_width(),
                              TITLE_Y + SUBTITLE_DY - dy), alpha=alpha)

        self._draw_portrait(screen, self.intro.item(1.0))
        self._draw_info(screen, self.intro.item(1.5))
        self._draw_nameplate(screen, self.intro.item(2.2))
        self._draw_confirm(screen, self.intro.item(2.6))
        self._draw_hint(screen, self.intro.item(3.0))

    def _draw_portrait(self, screen, tint=(255, 0)):
        """立绘直接站在键艺图上（不套面板）：底对齐同一条线，四位自机一样高"""
        alpha, dy = tint
        if alpha <= 0:
            return
        sprite = _portrait(cfg.player_character_path("portrait", self.character),
                           PORTRAIT_HEIGHT)
        if sprite is None:
            missing = self.game.font_medium.render("（缺立绘）", True, cfg.COLOR_GRAY)
            screen.blit_gpu(missing, (PORTRAIT_CENTER_X - missing.get_width() // 2,
                                      PORTRAIT_FEET_Y - 240 - dy), alpha=alpha)
            return
        width, height = sprite.get_size()
        screen.blit_gpu(sprite, (PORTRAIT_CENTER_X - width // 2,
                                 PORTRAIT_FEET_Y - height - dy), alpha=alpha)

    def _draw_info(self, screen, tint=(255, 0)):
        """右列：自机列表（选中的一位在列表里展开称号与介绍）"""
        alpha, dy = tint
        if alpha <= 0:
            return
        panel = INFO_RECT.move(0, -dy)
        _panel(screen, panel, opacity=alpha)

        x = panel.x + INFO_PAD
        right = panel.right - INFO_PAD

        # 顶部一行：两段横线夹着「自机选择」
        head = self.game.font_small.render("自机选择", True, cfg.COLOR_GRAY)
        head_y = panel.y + INFO_HEAD_DY
        head_x = panel.centerx - head.get_width() // 2
        if alpha >= 255:
            # 1px 的线，看不到「突然出现」：淡入期间先不画，等这一组落定再出现
            mid_y = head_y + head.get_height() // 2
            hires.ui_line(screen, cfg.COLOR_DARK_GRAY, (x, mid_y),
                          (head_x - 14, mid_y), 1)
            hires.ui_line(screen, cfg.COLOR_DARK_GRAY,
                          (head_x + head.get_width() + 14, mid_y), (right, mid_y), 1)
        screen.blit_gpu(head, (head_x, head_y), alpha=alpha)

        hover = self.game.mouse_pos
        for key, row in self._rows():
            rect = row.move(0, -dy)
            selected = key == self.character
            color = cfg.player_character_color(key)
            # 悬停只是亮一下边框、不换人：列表会随选择展开，行会在鼠标底下移位，
            # 悬停即选中就会来回抖（换人只认点击，见 update()）
            hovering = (not selected) and row.collidepoint(hover)
            if selected:
                _draw_plate(screen, "chara_row", rect,
                            fill=_dim(color, 0.20) + (150,), opacity=alpha)
            elif hovering:
                _draw_plate(screen, "chara_row", rect, fill=(255, 255, 255, 16),
                            border=cfg.COLOR_DARK_GRAY, border_w=1, opacity=alpha)

            _draw_marker(screen, (rect.x + 16, rect.y + 22), color,
                         selected, opacity=alpha)
            # 选中行不再走呼吸高亮：这一行已经有底板 + 实心圆点 + 展开的介绍三层
            # 标记，名字再一闪一闪反而吵（各界面呼吸高亮的相位差也是残留检查里的噪声）
            name_color = color if selected else _dim(color, ROW_IDLE_DIM)
            name = self.game.font_medium.render(cfg.PLAYER_CHARACTER_LABELS.get(key, key),
                                                True, name_color)
            screen.blit_gpu(name, (rect.x + 32, rect.y + 8), alpha=alpha)

            if not selected:
                continue
            # 选中行展开：称号 + 分隔线 + 介绍三行
            title = self.game.font_small.render(cfg.PLAYER_CHARACTER_TITLES.get(key, ""),
                                                True, cfg.COLOR_GRAY)
            detail_y = rect.y + ROW_TITLE_DY + 8
            screen.blit_gpu(title, (rect.x + 32, detail_y), alpha=alpha)
            line_y = detail_y + 24
            if alpha >= 255:
                hires.ui_line(screen, cfg.COLOR_DARK_GRAY, (rect.x + 32, line_y),
                              (rect.right - 16, line_y), 1)
            text_y = line_y + 10
            for text in cfg.PLAYER_CHARACTER_INTROS.get(key, ()):
                surf = self.game.font_small.render(text, True, cfg.COLOR_WHITE)
                screen.blit_gpu(surf, (rect.x + 32, text_y), alpha=alpha)
                text_y += ROW_INTRO_STEP

        # 面板底部：一位一位地翻到了哪里 + 说明
        counter = self.game.font_small.render(f"{self.index + 1} / {len(self.keys)}",
                                              True, cfg.COLOR_GRAY)
        screen.blit_gpu(counter, (right - counter.get_width(), panel.bottom - 40),
                        alpha=alpha)
        note_text = (f"当前 {len(self.keys)} 位自机的弹条数 / 扩散 / 穿透 / 追踪弹各不相同"
                     if not self.extra else
                     "Ex 面：不经仓库出征，局内装备物品效果不生效")
        note = self.game.font_small.render(note_text, True, cfg.COLOR_GRAY)
        screen.blit_gpu(note, (x, panel.bottom - 40), alpha=alpha)

    def _draw_nameplate(self, screen, tint=(255, 0)):
        """左下角：当前选择的徽记 + 名牌（大字用代表色描一层影，压在深底上才清楚）"""
        alpha, dy = tint
        if alpha <= 0:
            return
        key = self.character
        color = cfg.player_character_color(key)
        label = cfg.PLAYER_CHARACTER_LABELS.get(key, key)

        badge = BADGE_RECT.move(0, -dy)

        def build(target, k):
            middle = (badge.width // 2, badge.height // 2)
            painter.bake_circle(target, k, (0, 0, 0, 175), middle, badge.width // 2)
            painter.bake_circle(target, k, color, middle, badge.width // 2, 2)

        screen.blit_baked(("chara_badge", badge.size, tuple(color)),
                          badge.topleft, badge.size, build, alpha)
        glyph = self.game.font_medium.render(_initial(label), True, color)
        _blit_centered(screen, glyph, badge, opacity=alpha)

        plate = PLATE_RECT.move(0, -dy)
        _draw_plate(screen, "chara_plate", plate, fill=(0, 0, 0, 165), opacity=alpha)
        shadow = self.game.font_medium.render(label, True, _dim(color, 0.55))
        text = self.game.font_medium.render(label, True, cfg.COLOR_WHITE)
        text_y = plate.y + (plate.height - text.get_height()) // 2
        screen.blit_gpu(shadow, (plate.x + 18 + 2, text_y + 2), alpha=alpha)
        screen.blit_gpu(text, (plate.x + 18, text_y), alpha=alpha)

        tag = self.game.font_small.render("当前选择", True, cfg.COLOR_GRAY)
        screen.blit_gpu(tag, (plate.right - 18 - tag.get_width(),
                              plate.y + (plate.height - tag.get_height()) // 2),
                        alpha=alpha)

    def _draw_confirm(self, screen, tint=(255, 0)):
        alpha, dy = tint
        if alpha <= 0:
            return
        rect = CONFIRM_BTN.move(0, -dy)
        # 悬停判定用未位移的矩形：与 update() 的点击判定保持一致（进场只有 0.3 秒，
        # 这期间按绘制位置判定会出现「看着高亮却点不动」）
        hover = CONFIRM_BTN.collidepoint(self.game.mouse_pos)
        _draw_plate(screen, "chara_btn", rect, fill=cfg.COLOR_PANEL_BG,
                    border=cfg.COLOR_GREEN if hover else cfg.COLOR_GRAY,
                    border_w=2 if hover else 1, opacity=alpha)
        label = self.game.font_medium.render(
            "确定", True, cfg.COLOR_GREEN if hover else cfg.COLOR_WHITE)
        _blit_centered(screen, label, rect, opacity=alpha)

    def _draw_hint(self, screen, tint=(255, 0)):
        alpha, dy = tint
        if alpha <= 0:
            return
        hint = self.game.font_small.render(HINT_TEXT, True, cfg.COLOR_GRAY)
        x = (cfg.SCREEN_WIDTH - hint.get_width()) // 2
        rect = pygame.Rect(x - 14, HINT_Y - 7, hint.get_width() + 28,
                           hint.get_height() + 14).move(0, -dy)
        _draw_plate(screen, "chara_hint", rect, fill=(0, 0, 0, 150), opacity=alpha)
        screen.blit_gpu(hint, (x, HINT_Y - dy), alpha=alpha)
