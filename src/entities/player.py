# 玩家角色
# 支持：移动（普通/低速）、射击、炸弹、判定点

import math
import pygame
from src.engine import settings as cfg
from src.engine.collision import circle_collision


_player_sprite_cache = {}
_player_sprite_attempted = set()
_player_glow_cache = {}


def _load_player_sprite(path):
    key = path
    if key in _player_sprite_attempted:
        return _player_sprite_cache.get(key)
    _player_sprite_attempted.add(key)
    try:
        img = pygame.image.load(path).convert_alpha()
        bbox = img.get_bounding_rect(min_alpha=8)
        if bbox.width <= 0 or bbox.height <= 0:
            bbox = img.get_rect()
        img = img.subsurface(bbox)
        target_h = max(1, cfg.PLAYER_SPRITE_HEIGHT)
        target_w = max(1, int(round(img.get_width() * target_h / img.get_height())))
        _player_sprite_cache[key] = pygame.transform.smoothscale(img, (target_w, target_h))
    except Exception as exc:
        print(f"[Player] Failed to load sprite {path}: {exc}")
        _player_sprite_cache[key] = None
    return _player_sprite_cache[key]


def _get_player_sprite(path, flipped=False):
    base = _load_player_sprite(path)
    if base is None:
        return None
    key = (path, flipped)
    if key not in _player_sprite_cache:
        _player_sprite_cache[key] = (
            pygame.transform.flip(base, True, False) if flipped else base
        )
    return _player_sprite_cache[key]


def _get_player_glow(path, flipped=False):
    sprite = _get_player_sprite(path, flipped)
    if sprite is None:
        return None

    key = ("glow", path, flipped)
    if key in _player_glow_cache:
        return _player_glow_cache[key]

    try:
        radius = max(1, cfg.PLAYER_SPRITE_GLOW_RADIUS)
        sw, sh = sprite.get_size()
        glow = pygame.Surface((sw + radius * 2, sh + radius * 2), pygame.SRCALPHA)
        mask = pygame.mask.from_surface(sprite, threshold=32)
        silhouette = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
        max_alpha = max(1, cfg.PLAYER_SPRITE_GLOW_ALPHA)
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                dist = math.hypot(dx, dy)
                if dist <= radius:
                    t = dist / radius
                    silhouette.set_alpha(int(max_alpha * (1.0 - t)))
                    glow.blit(silhouette, (radius + dx, radius + dy))
        _player_glow_cache[key] = glow
    except Exception as exc:
        print(f"[Player] Failed to build glow for {path}: {exc}")
        _player_glow_cache[key] = None
    return _player_glow_cache[key]

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.speed = cfg.PLAYER_SPEED_NORMAL

        # 判定点
        self.hitbox_radius = cfg.PLAYER_HITBOX_RADIUS
        self.hitbox_visible = False
        self.graze_radius = cfg.PLAYER_GRAZE_RADIUS

        # 状态
        self.focused = False       # 低速模式
        self.invincible = 0        # 无敌帧数
        self.spell_invincible = False  # Bomb/自机符卡期间免疫攻击
        self.dead = False
        self.respawning = False

        # 射击
        self.shoot_cooldown = 0
        self.power = 0             # 0-128 (1.00 = 100)
        self.max_power = 400       # 4.00

        # 绘制用（无贴图时的占位矩形）
        self.width = 8
        self.height = 12

    @property
    def hitbox(self):
        return (self.x, self.y, self.hitbox_radius)

    def handle_input(self, keys, keys_held, keys_just_pressed):
        """处理输入"""
        self.vx = 0.0
        self.vy = 0.0
        self.focused = keys_held.get(pygame.K_LSHIFT, False) or keys_held.get(pygame.K_RSHIFT, False)

        self.speed = cfg.PLAYER_SPEED_FOCUSED if self.focused else cfg.PLAYER_SPEED_NORMAL

        if keys_held.get(pygame.K_LEFT, False) or keys_held.get(pygame.K_a, False):
            self.vx = -self.speed
        if keys_held.get(pygame.K_RIGHT, False) or keys_held.get(pygame.K_d, False):
            self.vx = self.speed
        if keys_held.get(pygame.K_UP, False) or keys_held.get(pygame.K_w, False):
            self.vy = -self.speed
        if keys_held.get(pygame.K_DOWN, False) or keys_held.get(pygame.K_s, False):
            self.vy = self.speed

        # 斜向移动速度修正
        if self.vx != 0 and self.vy != 0:
            self.vx *= 0.707
            self.vy *= 0.707

        # 射击键
        self.shooting = keys_held.get(pygame.K_z, False) or keys_held.get(pygame.K_SPACE, False)

        # 炸弹键
        self.want_bomb = keys_just_pressed.get(pygame.K_x, False)

    def update(self, dt):
        """更新玩家位置和状态"""
        # 移动
        self.x += self.vx
        self.y += self.vy

        # 边界限制
        self.x = max(cfg.PLAY_AREA_LEFT, min(cfg.PLAY_AREA_RIGHT, self.x))
        self.y = max(cfg.PLAY_AREA_TOP, min(cfg.PLAY_AREA_BOTTOM, self.y))

        # 无敌倒计时
        if self.invincible > 0:
            self.invincible -= 1

        # 射击冷却
        if self.shoot_cooldown > 0:
            self.shoot_cooldown -= 1

        # 低速时显示判定点
        self.hitbox_visible = self.focused

    def can_shoot(self):
        if self.shoot_cooldown <= 0 and self.shooting:
            self.shoot_cooldown = cfg.PLAYER_SHOOT_COOLDOWN
            return True
        return False

    def can_be_hit(self):
        return self.invincible <= 0 and not self.spell_invincible and not self.dead

    def hit(self):
        """被击中处理"""
        if not self.can_be_hit():
            return False
        self.invincible = 120  # 2秒无敌
        return True

    def _current_sprite_spec(self):
        if self.vx < 0:
            return cfg.PLAYER_SPRITE_MOVE, True
        if self.vx > 0:
            return cfg.PLAYER_SPRITE_MOVE, False
        return cfg.PLAYER_SPRITE_IDLE, False

    def _current_sprite(self):
        path, flipped = self._current_sprite_spec()
        return _get_player_sprite(path, flipped)

    def draw_sprite(self, screen, offset_x=0, offset_y=0):
        px = int(self.x + offset_x)
        py = int(self.y + offset_y)

        if self.invincible > 0 and self.invincible % 6 < 3:
            return

        path, flipped = self._current_sprite_spec()
        sprite = _get_player_sprite(path, flipped)
        if sprite is None:
            self._draw_placeholder(screen, px, py)
            return

        sprite_h = sprite.get_height()
        anchor_y = int(round(sprite_h * cfg.PLAYER_SPRITE_HITBOX_Y_RATIO))
        sprite_x = px - sprite.get_width() // 2
        sprite_y = py - anchor_y

        glow = _get_player_glow(path, flipped)
        if glow is not None:
            radius = max(1, cfg.PLAYER_SPRITE_GLOW_RADIUS)
            screen.blit(glow, (sprite_x - radius, sprite_y - radius))

        screen.blit(sprite, (sprite_x, sprite_y))

    def draw_hitbox(self, screen, offset_x=0, offset_y=0):
        if self.invincible > 0 and self.invincible % 6 < 3:
            return

        px = int(self.x + offset_x)
        py = int(self.y + offset_y)
        dot_radius = int(round(self.hitbox_radius * cfg.PLAYER_HITBOX_DRAW_RADIUS_FACTOR))
        pygame.draw.circle(screen, cfg.COLOR_WHITE, (px, py), dot_radius, 0)
        if self.hitbox_visible:
            pygame.draw.circle(screen, cfg.COLOR_RED, (px, py), dot_radius, 1)
        if self.focused:
            pygame.draw.circle(screen, cfg.COLOR_GREEN, (px, py), int(self.graze_radius), 1)

    def _draw_placeholder(self, screen, px, py):
        points = [
            (px, py - 6),
            (px + 4, py),
            (px, py + 6),
            (px - 4, py),
        ]
        color = cfg.COLOR_BLUE if not self.focused else cfg.COLOR_RED
        pygame.draw.polygon(screen, color, points, 0)

    def draw(self, screen, offset_x=0, offset_y=0):
        self.draw_sprite(screen, offset_x, offset_y)
        self.draw_hitbox(screen, offset_x, offset_y)

    def reset_position(self):
        """复活回到屏幕底部中央"""
        self.x = cfg.BATTLE_AREA_WIDTH / 2
        self.y = cfg.BATTLE_AREA_HEIGHT - 80
        self.invincible = 120

