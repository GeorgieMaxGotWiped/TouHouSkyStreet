# 掉落物：红色 Power 方块
# 击败敌人掉落，向下飘落，拾取后获得 Power

import math
import pygame
from src.engine import settings as cfg


class PowerPickup:
    """红色 Power 方块"""

    SIZE = 14            # 方块边长（px）
    PICKUP_RADIUS = 20   # 拾取判定半径（px）
    VALUE = 5            # 每个方块提供的 power
    LAUNCH_SPEED = -3.0  # 爆出时向上抛出的初速度
    GRAVITY = 0.08       # 抛出阶段重力加速度
    FALL_SPEED = 2.0     # 落回爆出高度后的均速下落速度
    SUCK_TIME = 0.2      # 顶部低速吸收耗时（秒），任意位置相同

    def __init__(self, x, y, vx=0.0, value=VALUE):
        self.x = x
        self.y = y
        self.spawn_y = y      # 爆出高度
        self.vx = 0.0
        self.vy = self.LAUNCH_SPEED
        self.thrown = True    # 先向上抛出
        self.value = value
        self.alive = True
        self.age = 0
        self.sucking = False    # 是否正在被顶部低速吸收
        self.suck_frames = 0    # 吸收剩余帧数（任意位置相同）

    def update(self, dt):
        self.age += 1
        self.x += self.vx
        if self.thrown:
            self.vy += self.GRAVITY
            self.y += self.vy
            # 落回爆出高度后改为均速下落
            if self.vy >= 0 and self.y >= self.spawn_y:
                self.thrown = False
                self.y = self.spawn_y
                self.vy = self.FALL_SPEED
        else:
            self.y += self.vy
        # 飘出屏幕底部或超时后消失
        if self.y > cfg.BATTLE_AREA_HEIGHT + 40 or self.age > 900:
            self.alive = False

    def start_suck(self, frames):
        """开始吸收：记录固定帧数，任意位置耗时相同"""
        if not self.sucking:
            self.sucking = True
            self.suck_frames = frames

    def end_suck(self):
        """中断吸收：恢复正常下落"""
        self.sucking = False
        self.suck_frames = 0

    def suck_toward(self, px, py):
        """吸收中：按剩余帧数等分距离飞向玩家，最后一帧到达"""
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
