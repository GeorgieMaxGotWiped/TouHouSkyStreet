# 玩家角色
# 支持：移动（普通/低速）、射击、炸弹、判定点

import math
import pygame
from src.engine import settings as cfg
from src.engine.collision import circle_collision

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
        return self.invincible <= 0 and not self.dead

    def hit(self):
        """被击中处理"""
        if not self.can_be_hit():
            return False
        self.invincible = 120  # 2秒无敌
        return True

    def draw(self, screen, offset_x=0, offset_y=0):
        """绘制玩家"""
        px = int(self.x + offset_x)
        py = int(self.y + offset_y)

        # 无敌闪烁
        if self.invincible > 0 and self.invincible % 6 < 3:
            return

        # 绘制身体（菱形）
        points = [
            (px, py - 6),
            (px + 4, py),
            (px, py + 6),
            (px - 4, py),
        ]
        color = cfg.COLOR_BLUE if not self.focused else cfg.COLOR_RED
        pygame.draw.polygon(screen, color, points, 0)

        # 判定点
        if self.hitbox_visible:
            pygame.draw.circle(screen, cfg.COLOR_RED, (px, py), int(self.hitbox_radius), 1)

        # 擦弹圈
        if self.focused:
            pygame.draw.circle(screen, cfg.COLOR_GREEN, (px, py), int(self.graze_radius), 1)

    def reset_position(self):
        """复活回到屏幕底部中央"""
        self.x = cfg.BATTLE_AREA_WIDTH / 2
        self.y = cfg.BATTLE_AREA_HEIGHT - 80
        self.invincible = 120

