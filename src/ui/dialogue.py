# 对话系统
# 底部对话框：Z/Enter 继续，ESC 跳过

import pygame
from src.engine import settings as cfg

# 对话框高度（px）
DIALOGUE_BOX_HEIGHT = 112
# 立绘目标：头顶对齐战斗框上 1/3 线（半身露在对话框上方，下半被遮挡）
DIALOGUE_PORTRAIT_TOP_TARGET = cfg.BATTLE_OFFSET_Y + cfg.BATTLE_AREA_HEIGHT // 3
# 立绘淡入帧数（快速由透明变实心）
DIALOGUE_PORTRAIT_FADE_FRAMES = 15


class DialogueBox:
    """底部对话框（逐条推进）"""
    def __init__(self, game, lines, portraits=None, portrait_sides=None):
        self.game = game
        self.lines = lines          # [(name, text), ...]
        self.portraits = portraits or {}   # {角色名: 贴图路径}
        self.portrait_sides = portrait_sides or {}   # {角色名: "left"/"right"}，默认右侧
        self.index = 0
        self.finished = False
        self.wait_frames = 20       # 换行后输入缓冲，防止误跳过
        self._portrait_cache = {}   # 贴图路径 -> Surface
        self._portrait_attempted = set()
        self.portrait_path = None     # 当前显示的立绘路径（换行时重新淡入）
        self.portrait_fade = 0        # 立绘当前透明度（0-255）
        self.portrait_fade_timer = 0  # 立绘淡入剩余帧数

    def _get_portrait(self, path):
        """加载并缓存立绘：等比放大到「头顶对齐战斗框上1/3线」，失败返回 None"""
        if path in self._portrait_attempted:
            return self._portrait_cache.get(path)
        self._portrait_attempted.add(path)
        try:
            img = pygame.image.load(path)
            try:
                img = img.convert_alpha()
            except Exception:
                pass
            w, h = img.get_size()
            if h <= 0:
                raise ValueError("invalid portrait height")
            ph = self._portrait_height(img, h)
            new_w = max(1, round(w * ph / h))
            self._portrait_cache[path] = pygame.transform.smoothscale(
                img, (new_w, ph))
        except Exception as e:
            print(f"[Dialogue] Failed to load portrait {path}: {e}")
        return self._portrait_cache.get(path)

    @staticmethod
    def _portrait_height(img, h):
        """计算立绘目标高度：贴图内头顶（首个不透明像素行）对齐战斗框上1/3线；
        draw 中按 py = box_top - ph/2 放置，使立绘下半正好被对话框遮挡。"""
        box_top = cfg.BATTLE_OFFSET_Y + cfg.BATTLE_AREA_HEIGHT - DIALOGUE_BOX_HEIGHT - 12
        try:
            rects = pygame.mask.from_surface(img).get_bounding_rects()
            content_top = min(r.top for r in rects) if rects else 0
        except Exception:
            content_top = 0
        ratio = content_top / h
        denom = 0.5 - ratio
        if denom <= 0:
            return h
        return max(1, int(round((box_top - DIALOGUE_PORTRAIT_TOP_TARGET) / denom)))

    def _with_alpha(self, surf, alpha):
        """返回带整体透明度 alpha(0-255) 的表面副本（不修改原表面）"""
        if alpha >= 255:
            return surf
        result = surf.copy()
        result.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
        return result

    def update(self, dt):
        if self.finished:
            return

        # 立绘淡入：当前说话角色带立绘且与上次不同时，快速由透明变实心
        name, _text = self.lines[self.index]
        portrait_path = self.portraits.get(name)
        if portrait_path != self.portrait_path:
            self.portrait_path = portrait_path
            self.portrait_fade_timer = (DIALOGUE_PORTRAIT_FADE_FRAMES
                                        if portrait_path else 0)
            self.portrait_fade = 0
        if self.portrait_fade_timer > 0:
            self.portrait_fade_timer -= 1
            self.portrait_fade = min(255, int(
                255 * (1 - self.portrait_fade_timer / DIALOGUE_PORTRAIT_FADE_FRAMES)))

        if self.wait_frames > 0:
            self.wait_frames -= 1
            return

        keys = self.game.keys_just_pressed
        if (keys.get(pygame.K_z, False) or keys.get(pygame.K_RETURN, False)
                or keys.get(pygame.K_SPACE, False)):
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

        # 说话角色的立绘：贴在对话框上方（无边框），默认右侧；自机在左侧
        portrait_path = self.portraits.get(name)
        if portrait_path:
            sprite = self._get_portrait(portrait_path)
            if sprite is not None:
                if self.portrait_fade < 255:
                    sprite = self._with_alpha(sprite, self.portrait_fade)
                pw, ph = sprite.get_size()
                if self.portrait_sides.get(name) == "left":
                    px = x
                else:
                    px = x + box_w - pw
                py = y - ph // 2   # 立绘下半部分被对话框遮挡（半身效果）
                # 超出战斗框的部分裁剪掉，不显示
                old_clip = screen.get_clip()
                screen.set_clip((cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y,
                                 cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT))
                screen.blit(sprite, (px, py))
                screen.set_clip(old_clip)

        box = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        box.fill((10, 10, 28, 235))
        screen.blit(box, (x, y))
        pygame.draw.rect(screen, cfg.COLOR_GRAY, (x, y, box_w, box_h), 2)

        # 角色名
        name_text = self.game.font_medium.render(name, True, cfg.COLOR_YELLOW)
        screen.blit(name_text, (x + 16, y + 12))

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
