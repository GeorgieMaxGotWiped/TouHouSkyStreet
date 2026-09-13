# 对话系统
# 底部对话框：Z/Enter 继续，ESC 跳过

import math
import re
import pygame
from src.engine import settings as cfg
from src.engine import boss_art
from src.engine import hires

# 对话说话名只显示英文：去掉中文前缀（如「魔法使 Mage」→「Mage」）
_CJK_LEAD = re.compile(r"^[\u4e00-\u9fff\uff00-\uffef\u3000-\u303f]+\s*")

# 对话框高度（px）
DIALOGUE_BOX_HEIGHT = 112
# 立绘目标：头顶对齐战斗框上 1/3 线（半身露在对话框上方，下半被遮挡）
DIALOGUE_PORTRAIT_TOP_TARGET = cfg.BATTLE_OFFSET_Y + cfg.BATTLE_AREA_HEIGHT // 3
# 立绘状态平滑速率（越大过渡越快）：控制说话者/非说话者透明度与后退的渐变
DIALOGUE_PORTRAIT_STATE_RATE = 10.0
# 立绘投影：偏移 (右, 下) 与基准不透明度（随立绘淡入）
DIALOGUE_PORTRAIT_SHADOW_OFFSET = (8, 10)
DIALOGUE_PORTRAIT_SHADOW_ALPHA = 120
# 立绘基准缩放：避免半身立绘占满整条对话区，使自机/boss 左右站位一目了然
DIALOGUE_PORTRAIT_BASE_SCALE = 0.62
# 非当前说话角色的立绘：半透明，并向自己一侧后退一定像素
DIALOGUE_PORTRAIT_INACTIVE_ALPHA = 110
DIALOGUE_PORTRAIT_RETREAT = 30
# 所有人物统一向自己一侧外移的像素（说话者/非说话者都移动；非说话者再叠加 RETREAT）
DIALOGUE_PORTRAIT_SIDE_SHIFT = 60


# 立绘缓存：key = (贴图路径, 角色缩放) -> (Surface, 内容框)。
# 放在模块级是为了跨对话框复用：同一张立绘在整局里只做一次抠图 / 遮罩 / 缩放。
# 遮罩要扫整张立绘，是这里最贵的一步，所以两个用途（立绘高度、内容框）共用一次结果。
_PORTRAIT_CACHE = {}
# 立绘合成图缓存（立绘 + 柔化投影烘成一张）：key 与立绘缓存一致
_PORTRAIT_COMPOSITE_CACHE = {}
# 缓存条数上限：一张 3x 立绘加投影可达数 MB，跨关卡一直累积会白占内存
_PORTRAIT_CACHE_LIMIT = 8
# 缓存键的先进先出顺序（超上限时丢最旧的）
_PORTRAIT_ORDER = []


def _remember_portrait(key, value):
    """写入立绘缓存，超过上限就丢掉最旧的一条（连同它的投影）"""
    if key not in _PORTRAIT_CACHE and len(_PORTRAIT_ORDER) >= _PORTRAIT_CACHE_LIMIT:
        old = _PORTRAIT_ORDER.pop(0)
        _PORTRAIT_CACHE.pop(old, None)
        _PORTRAIT_COMPOSITE_CACHE.pop(old, None)
    _PORTRAIT_CACHE[key] = value
    if key in _PORTRAIT_ORDER:
        _PORTRAIT_ORDER.remove(key)
    _PORTRAIT_ORDER.append(key)


def _portrait_target_height(h, content_top):
    """立绘目标高度：贴图内头顶（首个不透明像素行）对齐战斗框上1/3线；
    draw 中按 py = box_top - ph/2 放置，使立绘下半正好被对话框遮挡。"""
    box_top = cfg.BATTLE_OFFSET_Y + cfg.BATTLE_AREA_HEIGHT - DIALOGUE_BOX_HEIGHT - 12
    denom = 0.5 - content_top / h
    if denom <= 0:
        return h
    return max(1, int(round((box_top - DIALOGUE_PORTRAIT_TOP_TARGET) / denom)))


def _union_content_rect(rects, w, h):
    """遮罩矩形并成一个内容框；没有内容时退回整张图"""
    if not rects:
        return pygame.Rect(0, 0, w, h)
    rect = rects[0]
    for r in rects[1:]:
        rect = rect.union(r)
    return rect


def get_portrait(path, scale):
    """取（并缓存）立绘贴图与内容框；失败返回 (None, (0, 0, 0))，不重复重试。

    立绘按基准缩放等比缩小（自机/boss 左右站位更清晰），内容框为
    (内容左, 内容右, 内容顶)（逻辑像素，即排版坐标）。

    贴图本身按渲染倍率放大像素（文字/立绘的高分辨率图层用），内容框仍是逻辑
    尺寸，所以 draw 里的站位计算一行都不用改。
    """
    factor = hires.scale()
    key = (path, scale, factor)
    cached = _PORTRAIT_CACHE.get(key)
    if cached is not None:
        return cached
    sprite = None
    box = (0, 0, 0)
    try:
        # 白底立绘（如新版 Boss 立绘）在这里抠掉背景并按内容裁剪
        img = boss_art.load_sprite(path)
        if img is None:
            raise ValueError("portrait unavailable")
        w, h = img.get_size()
        if h <= 0:
            raise ValueError("invalid portrait height")
        try:
            rects = pygame.mask.from_surface(img).get_bounding_rects()
        except Exception:
            rects = []
        content_top = min(r.top for r in rects) if rects else 0
        ph = _portrait_target_height(h, content_top)
        ph = max(1, int(round(ph * scale * DIALOGUE_PORTRAIT_BASE_SCALE)))
        sprite = hires.scaled_image(img, (max(1, int(round(w * ph / h))), ph), factor)
        cr = _union_content_rect(rects, w, h)
        kx = ph / float(h)
        box = (max(0, int(round(cr.left * kx))),
               max(0, int(round((cr.left + cr.width) * kx))),
               max(0, int(round(cr.top * kx))))
    except Exception as e:
        print(f"[Dialogue] Failed to load portrait {path}: {e}")
    _remember_portrait(key, (sprite, box))
    return sprite, box


def get_portrait_composite(key, sprite):
    """取（并缓存）「柔化投影 + 立绘」烘在一起的合成图，以及它的左上角偏移。

    投影是纯黑剪影，所以「先贴投影、再贴立绘」与「贴一张合成图」结果一致
    （逐像素对比最大只差 1/255 的取整），但每帧少贴一半像素：3x 立绘有
    1.3M 像素，两张一起贴是对话帧里最贵的一笔（实测约 6ms/帧，合成后约 3ms）。
    """
    entry = _PORTRAIT_COMPOSITE_CACHE.get(key)
    if entry is None:
        shadow = _build_shadow(sprite)
        sx, sy = DIALOGUE_PORTRAIT_SHADOW_OFFSET
        ox, oy = max(0, -sx), max(0, -sy)          # 投影往左上偏时的补边
        w, h = pygame.Surface.get_size(sprite)
        canvas = hires.HiresSurface((w + abs(sx), h + abs(sy)),
                                    getattr(sprite, "hi_scale", 1))
        canvas.blit(shadow, (sx + ox, sy + oy))
        canvas.blit(sprite, (ox, oy))
        entry = (canvas, ox, oy)
        _PORTRAIT_COMPOSITE_CACHE[key] = entry
    return entry


def _build_shadow(sprite):
    """根据立绘透明通道生成柔化投影（黑色 + 降采样模糊），
    并把基准不透明度烘焙进 alpha 通道，便于后续整体淡入。

    模糊始终按「真实像素」做，最后再恢复倍率标记，否则投影会被当 1x 贴出去。
    """
    shadow = sprite.copy()
    shadow.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
    factor = getattr(shadow, "hi_scale", 1)
    w, h = pygame.Surface.get_size(shadow)
    small = pygame.transform.smoothscale(
        shadow, (max(1, w // 6), max(1, h // 6)))
    if factor > 1:
        blurred = hires.HiresSurface((w, h), factor)
        pygame.transform.smoothscale(small, (w, h), blurred)
        shadow = blurred
    else:
        shadow = pygame.transform.smoothscale(small, (w, h))
    shadow.fill((255, 255, 255, DIALOGUE_PORTRAIT_SHADOW_ALPHA),
                special_flags=pygame.BLEND_RGBA_MULT)
    return shadow


class DialogueBox:
    """底部对话框（逐条推进）"""
    def __init__(self, game, lines, portraits=None, portrait_sides=None,
                 portrait_scales=None, portrait_offsets=None,
                 portrait_vertical_offsets=None):
        self.game = game
        self.lines = lines          # [(name, text), ...]
        self.portraits = portraits or {}   # {角色名: 贴图路径}
        self.portrait_sides = portrait_sides or {}   # {角色名: "left"/"right"}，默认右侧
        self.portrait_scales = portrait_scales or {}   # {角色名: 立绘放大倍率}，默认 1.0
        self.portrait_offsets = portrait_offsets or {}   # {角色名: 立绘水平偏移px}，正值右移
        self.portrait_vertical_offsets = portrait_vertical_offsets or {}   # {角色名: 立绘垂直偏移px}，正值上移
        self.index = 0
        self.finished = False
        self.wait_frames = 20       # 换行后输入缓冲，防止误跳过
        # 立绘与投影缓存在模块级（见文件顶部 _PORTRAIT_CACHE），跨对话框复用
        self._portrait_states = {}   # 角色名 -> [当前透明度, 当前后退像素]（平滑过渡用）
        self.boss_card = self._find_boss_card()   # 本段对话涉及的 BOSS 英文名，无则 None

    @staticmethod
    def _display_name(name):
        """对话中的显示名：只保留英文名（去掉中文前缀）。"""
        return _CJK_LEAD.sub('', name)

    def _find_boss_card(self):
        """从本段对话的说话人中找出头衔表里的 BOSS（英文名），没有则返回 None。"""
        for name, _text in self.lines:
            display = self._display_name(name)
            if display in cfg.BOSS_TITLES:
                return display
        return None

    @staticmethod
    def _blit_alpha(screen, surf, alpha, pos):
        """按整体不透明度 alpha(0-255) 贴一张立绘。

        这里刻意不用「复制一份再 BLEND_RGBA_MULT」的写法：3x 立绘有 5MB 像素，
        复制 + 逐像素乘法实测约 8ms/张，而对话淡入时每帧都要做，直接把帧率打穿。
        改成临时改表面 alpha（贴完还原）后，缩放倍数交给混合沿用，结果一致
        （逐像素对比最大只差 1/255），开销几乎为零。
        """
        if alpha >= 255:
            screen.blit(surf, pos)
            return
        old = surf.get_alpha()
        surf.set_alpha(alpha)
        try:
            screen.blit(surf, pos)
        finally:
            surf.set_alpha(old)

    def _draw_portrait(self, screen, name, portrait_path, alpha, retreat):
        """绘制单个立绘：alpha 为整体不透明度(0-255)，retreat 为向自己一侧后退像素。"""
        key = (portrait_path, self.portrait_scales.get(name, 1.0))
        sprite, (box_l, box_r, content_top) = get_portrait(*key)
        if sprite is None:
            return
        composite, ox, oy = get_portrait_composite(key, sprite)
        # 侧位规则：显式配置优先；未配置时自机靠左，其余靠右
        side = self.portrait_sides.get(name)
        if side is None:
            side = "left" if portrait_path == cfg.SELF_SPRITE else "right"
        box_w = cfg.BATTLE_AREA_WIDTH - 24
        x = cfg.BATTLE_OFFSET_X + 12
        if side == "left":
            px = x - box_l - retreat
        else:
            px = x + box_w - box_r + self.portrait_offsets.get(name, 0) + retreat
        # 头顶对齐战斗框上1/3线，立绘下半被对话框遮挡（半身效果）
        py = (DIALOGUE_PORTRAIT_TOP_TARGET - content_top
              - self.portrait_vertical_offsets.get(name, 0))
        # 超出战斗框的部分裁剪掉，不显示
        old_clip = screen.get_clip()
        screen.set_clip((cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y,
                         cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT))
        # 投影与立绘已经烘在同一张图上（见 get_portrait_composite），一次贴完
        self._blit_alpha(screen, composite, alpha, (px - ox, py - oy))
        screen.set_clip(old_clip)

    def update(self, dt):
        if self.finished:
            return

        # 立绘平滑过渡：说话者 全透明+正常位，其余 半透明+向自己一侧后退
        name, _text = self.lines[self.index]
        k = 1.0 - math.exp(-dt * DIALOGUE_PORTRAIT_STATE_RATE)
        for cname in self.portraits:
            alpha_t = 255.0 if cname == name else float(DIALOGUE_PORTRAIT_INACTIVE_ALPHA)
            retreat_t = float(
                DIALOGUE_PORTRAIT_SIDE_SHIFT
                if cname == name
                else DIALOGUE_PORTRAIT_SIDE_SHIFT + DIALOGUE_PORTRAIT_RETREAT)
            cur = self._portrait_states.setdefault(
                cname, [0.0, float(DIALOGUE_PORTRAIT_SIDE_SHIFT + DIALOGUE_PORTRAIT_RETREAT)])
            cur[0] += (alpha_t - cur[0]) * k
            cur[1] += (retreat_t - cur[1]) * k

        if self.wait_frames > 0:
            self.wait_frames -= 1
            return

        keys = self.game.keys_just_pressed
        if (keys.get(pygame.K_z, False) or keys.get(pygame.K_RETURN, False)
                or keys.get(pygame.K_SPACE, False) or self.game.mouse_clicked(1)):
            self.index += 1
            if self.index >= len(self.lines):
                self.finished = True
            else:
                self.wait_frames = 20
        elif keys.get(pygame.K_ESCAPE, False):
            # 跳过全部对话
            self.index = len(self.lines)
            self.finished = True

    def draw(self, screen):
        if self.finished:
            return
        name, text = self.lines[self.index]

        box_w = cfg.BATTLE_AREA_WIDTH - 24
        box_h = DIALOGUE_BOX_HEIGHT
        x = cfg.BATTLE_OFFSET_X + 12
        y = cfg.BATTLE_OFFSET_Y + cfg.BATTLE_AREA_HEIGHT - box_h - 12

        # 立绘：说话者正常不透明度、正常位置；其他角色半透明并向自己一侧后退。
        # 先画非说话者，最后画说话者，保证说话者叠在最上层。
        for cname, cpath in self.portraits.items():
            if cname == name:
                continue
            alpha, retreat = self._portrait_states.get(
                cname, (DIALOGUE_PORTRAIT_INACTIVE_ALPHA, DIALOGUE_PORTRAIT_RETREAT))
            self._draw_portrait(screen, cname, cpath,
                                int(round(alpha)), int(round(retreat)))
        speaker_path = self.portraits.get(name)
        if speaker_path:
            alpha, retreat = self._portrait_states.get(name, (255.0, 0.0))
            self._draw_portrait(screen, name, speaker_path,
                                int(round(alpha)), int(round(retreat)))

        # 对话框底与边框走文字同一张高分辨率图层，否则锐利的字会贴在发虚的框上
        if hasattr(screen, "new_panel"):
            box = screen.new_panel((box_w, box_h))
            box.fill((10, 10, 28, 235))
            screen.blit(box, (x, y))
            screen.hi_rect(cfg.COLOR_GRAY, (x, y, box_w, box_h), 2)
        else:
            box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            box.fill((10, 10, 28, 235))
            screen.blit(box, (x, y))
            pygame.draw.rect(screen, cfg.COLOR_GRAY, (x, y, box_w, box_h), 2)

        # 角色名（只显示英文名）
        name_text = self.game.font_medium.render(self._display_name(name), True, cfg.COLOR_YELLOW)
        screen.blit(name_text, (x + 16, y + 12))

        # 对话框右上角：本段对话涉及的 BOSS 头衔一行 + 名字一行（放到框外上方，x 不变）
        if self.boss_card:
            title_surf = self.game.font_small.render(
                cfg.BOSS_TITLES[self.boss_card], True, cfg.COLOR_GRAY)
            boss_name_surf = self.game.font_medium.render(
                self.boss_card, True, cfg.COLOR_YELLOW)
            right_x = x + box_w - 16
            screen.blit(title_surf, (right_x - title_surf.get_width(), y - 52))
            screen.blit(boss_name_surf, (right_x - boss_name_surf.get_width(), y - 30))

        # 正文（自动换行）
        body_font = self.game.font_small
        max_w = box_w - 32
        ty = y + 46
        for line in self._wrap_text(text, body_font, max_w):
            t = body_font.render(line, True, cfg.COLOR_WHITE)
            screen.blit(t, (x + 16, ty))
            ty += 24

        # 继续提示
        if self.wait_frames <= 0:
            hint = body_font.render("▼", True, cfg.COLOR_YELLOW)
            screen.blit(hint, (x + box_w - 28, y + box_h - 26))

    def _wrap_text(self, text, font, max_w):
        if font.size(text)[0] <= max_w:
            return [text]
        result = []
        cur = ""
        for ch in text:
            if font.size(cur + ch)[0] > max_w:
                result.append(cur)
                cur = ch
            else:
                cur += ch
        if cur:
            result.append(cur)
        return result
