# Pickups: red Power blocks and boss reward drops.
# Drops fall downward and are collected by the player.

import math
import os
import pygame
from src.engine import settings as cfg


# Boss-specific reward drop identifiers.
DROP_OVERFLUX_POWER_ORB = "overflux_power_orb"
DROP_REVIVE_STONE = "revive_stone"


_pickup_sprite_cache = {}


def _get_pickup_sprite(path, target_size):
    """Load and scale a pickup sprite. Returns None when unavailable."""
    key = (path, target_size)
    if key in _pickup_sprite_cache:
        return _pickup_sprite_cache[key]

    sprite = None
    try:
        if os.path.exists(path):
            img = pygame.image.load(path)
            if img.get_bitsize() < 24:
                converted = pygame.Surface(img.get_size(), pygame.SRCALPHA)
                converted.blit(img, (0, 0))
                img = converted
            else:
                try:
                    img = img.convert_alpha()
                except Exception:
                    pass
            w, h = img.get_size()
            if w > 0 and h > 0:
                scale = target_size / max(w, h)
                new_w = max(1, round(w * scale))
                new_h = max(1, round(h * scale))
                sprite = pygame.transform.smoothscale(img, (new_w, new_h))
    except Exception as exc:
        print(f"[Pickup] Failed to load sprite {path}: {exc}")

    _pickup_sprite_cache[key] = sprite
    return sprite


class PowerPickup:
    """Red Power block."""

    SIZE = 14            # block edge length (px)
    PICKUP_RADIUS = 20   # pickup radius (px)
    VALUE = 5            # power granted per block
    LAUNCH_SPEED = -3.0  # initial upward pop speed
    GRAVITY = 0.08       # pop phase gravity
    FALL_SPEED = 2.0     # steady fall speed after popping
    SUCK_TIME = 0.2      # top-area suction duration (seconds)

    def __init__(self, x, y, vx=0.0, value=VALUE):
        self.x = x
        self.y = y
        self.spawn_y = y
        self.vx = 0.0
        self.vy = self.LAUNCH_SPEED
        self.thrown = True
        self.value = value
        self.alive = True
        self.age = 0
        self.sucking = False
        self.suck_frames = 0

    def update(self, dt):
        self.age += 1
        self.x += self.vx
        if self.thrown:
            self.vy += self.GRAVITY
            self.y += self.vy
            if self.vy >= 0 and self.y >= self.spawn_y:
                self.thrown = False
                self.y = self.spawn_y
                self.vy = self.FALL_SPEED
        else:
            self.y += self.vy
        if self.y > cfg.BATTLE_AREA_HEIGHT + 40 or self.age > 900:
            self.alive = False

    def start_suck(self, frames):
        if not self.sucking:
            self.sucking = True
            self.suck_frames = frames

    def end_suck(self):
        self.sucking = False
        self.suck_frames = 0

    def suck_toward(self, px, py):
        if not self.sucking:
            return
        dx = px - self.x
        dy = py - self.y
        dist = math.hypot(dx, dy)
        if self.suck_frames <= 1:
            self.x = px
            self.y = py
            self.suck_frames = 0
            self.sucking = False
            return
        if dist > 0:
            step = dist / self.suck_frames
            self.x += dx / dist * step
            self.y += dy / dist * step
        self.suck_frames -= 1

    def draw(self, screen, offset_x=0, offset_y=0):
        px = int(self.x + offset_x)
        py = int(self.y + offset_y)
        s = self.SIZE
        rect = pygame.Rect(px - s // 2, py - s // 2, s, s)
        pygame.draw.rect(screen, cfg.COLOR_RED, rect, 0)
        pygame.draw.rect(screen, cfg.COLOR_WHITE, rect, 2)

    def get_hitbox(self):
        return (self.x, self.y, self.SIZE / 2)


class OverfluxPowerOrbPickup(PowerPickup):
    """Overflux Power Orb: grants +1 bomb and is not cleared at max power."""

    SIZE = 22
    PICKUP_RADIUS = 22
    SPRITE_PATH = os.path.join(cfg.SPRITES_DIR, "bullets", "Overflux_Power_Orb.png")
    FALLBACK_COLOR = (90, 220, 255)

    def __init__(self, x, y, vx=0.0):
        super().__init__(x, y, vx=vx, value=0)

    def draw(self, screen, offset_x=0, offset_y=0):
        sprite = _get_pickup_sprite(self.SPRITE_PATH, self.SIZE)
        px = int(self.x + offset_x)
        py = int(self.y + offset_y)
        if sprite is not None:
            screen.blit(sprite, sprite.get_rect(center=(px, py)))
            return
        pygame.draw.circle(screen, self.FALLBACK_COLOR, (px, py), self.SIZE // 2, 0)
        pygame.draw.circle(screen, cfg.COLOR_WHITE, (px, py), self.SIZE // 2, 2)


class ReviveStonePickup(PowerPickup):
    """Revive Stone: grants +1 life and is not cleared at max power."""

    SIZE = 22
    PICKUP_RADIUS = 22
    SPRITE_PATH = os.path.join(cfg.SPRITES_DIR, "bullets", "Revive_Stone.png")
    FALLBACK_COLOR = (255, 130, 190)

    def __init__(self, x, y, vx=0.0):
        super().__init__(x, y, vx=vx, value=0)

    def draw(self, screen, offset_x=0, offset_y=0):
        sprite = _get_pickup_sprite(self.SPRITE_PATH, self.SIZE)
        px = int(self.x + offset_x)
        py = int(self.y + offset_y)
        if sprite is not None:
            screen.blit(sprite, sprite.get_rect(center=(px, py)))
            return
        pygame.draw.circle(screen, self.FALLBACK_COLOR, (px, py), self.SIZE // 2, 0)
        pygame.draw.circle(screen, cfg.COLOR_WHITE, (px, py), self.SIZE // 2, 2)
