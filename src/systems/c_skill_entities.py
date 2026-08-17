# C 技能实体：护盾 / 气球 / 玫瑰 / Orb / 召唤小怪
# 这些实体由 PlayingState 持有并在 update/draw 中驱动。

import math
import random
import pygame
from src.engine import settings as cfg
from src.engine.collision import circle_collision

# 凋零护盾：围绕自机旋转，碰到敌弹抵消并失去该护盾
class WitherShield:
    def __init__(self, player, index, total=6):
        self.radius = player.graze_radius + 4
        self.angle = (math.tau * index / total) + random.uniform(-0.2, 0.2)
        self.alive = True
        self.size = 7
        self.x = player.x
        self.y = player.y

    def update(self, player):
        self.angle += 0.06
        self.x = player.x + math.cos(self.angle) * self.radius
        self.y = player.y + math.sin(self.angle) * self.radius

    def draw(self, screen, ox=0, oy=0):
        if not self.alive:
            return
        px = int(self.x + ox)
        py = int(self.y + oy)
        pygame.draw.circle(screen, (120, 200, 255), (px, py), self.size, 0)
        pygame.draw.circle(screen, (20, 60, 120), (px, py), self.size, 1)


# 气球：随机方向飞行，碰到敌弹爆炸并清掉周围弹幕
class BonzoBalloon:
    EXPLODE_RADIUS = 70
    SPEED = 3.2

    def __init__(self, x, y):
        angle = random.uniform(-math.pi, math.pi)
        self.vx = math.cos(angle) * self.SPEED
        self.vy = math.sin(angle) * self.SPEED
        self.x = x
        self.y = y
        self.radius = 13
        self.alive = True
        self.lifetime = 360
        self.anim = random.randint(0, 20)

    def update(self):
        if not self.alive:
            return
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            return
        self.x += self.vx
        self.y += self.vy
        if self.x < 8 or self.x > cfg.BATTLE_AREA_WIDTH - 8:
            self.vx *= -1
        if self.y < 8 or self.y > cfg.BATTLE_AREA_HEIGHT - 8:
            self.vy *= -1
        self.anim += 1

    def explode(self, bullet_manager):
        if not self.alive:
            return False
        self.alive = False
        hit = False
        for b in bullet_manager.enemy_bullets[:]:
            if not b.alive or b.cancel_timer > 0:
                continue
            if circle_collision(self.x, self.y, self.EXPLODE_RADIUS,
                                b.x, b.y, b.collision_radius):
                b.start_cancel()
                hit = True
        return hit

    def draw(self, screen, ox=0, oy=0):
        if not self.alive:
            return
        px = int(self.x + ox)
        py = int(self.y + oy)
        bob = int(math.sin(self.anim * 0.18) * 3)
        color = (240, 130, 150) if (self.anim // 12) % 2 == 0 else (255, 170, 190)
        pygame.draw.circle(screen, color, (px, py + bob), self.radius, 0)
        pygame.draw.line(screen, (120, 60, 80), (px, py + bob + self.radius),
                         (px, py + bob + self.radius + 8), 2)


# 玫瑰：追踪消灭最近敌弹，3 次后飞向 BOSS 造成 1200 伤害
class FlowerRose:
    HUNT_SPEED = 6.0
    BOSS_SPEED = 9.0
    BOSS_DAMAGE = 1200
    TARGET_HITS = 3

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True
        self.hits = 0
        self.state = "hunt"
        self.radius = 9
        self.lifetime = 900

    def update(self, bullet_manager, boss):
        if not self.alive:
            return
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            return
        if self.state == "hunt":
            target = None
            best = 1e18
            for b in bullet_manager.enemy_bullets:
                if not b.alive or b.cancel_timer > 0 or b.harmless:
                    continue
                d = (b.x - self.x) ** 2 + (b.y - self.y) ** 2
                if d < best:
                    best = d
                    target = b
            if target is not None:
                dx = target.x - self.x
                dy = target.y - self.y
                dist = math.hypot(dx, dy)
                if dist < 1:
                    dist = 1
                step = min(self.HUNT_SPEED, dist)
                self.x += dx / dist * step
                self.y += dy / dist * step
                if dist <= self.HUNT_SPEED:
                    target.start_cancel()
                    self.hits += 1
                    if self.hits >= self.TARGET_HITS:
                        self.state = "boss"
            else:
                self.y -= self.HUNT_SPEED * 0.6  # 无弹幕时缓慢上飘
                if self.y < 20:
                    self.alive = False
            return
        # state == "boss"
        boss = boss if (boss is not None and boss.alive) else None
        if boss is None or not getattr(boss, "combat_enabled", True):
            self.y -= self.BOSS_SPEED * 0.5
            if self.y < 20:
                self.alive = False
            return
        dx = boss.x - self.x
        dy = boss.y - self.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            dist = 1
        step = min(self.BOSS_SPEED, dist)
        self.x += dx / dist * step
        self.y += dy / dist * step
        if dist <= self.BOSS_SPEED:
            if boss.take_damage(self.BOSS_DAMAGE, source="main"):
                pass  # 击破由 PlayingState 的奖励回调处理
            self.alive = False

    def draw(self, screen, ox=0, oy=0):
        if not self.alive:
            return
        px = int(self.x + ox)
        py = int(self.y + oy)
        pygame.draw.circle(screen, (255, 90, 140), (px, py), self.radius, 0)
        pygame.draw.circle(screen, (255, 220, 230), (px, py), self.radius // 2, 0)
        pygame.draw.circle(screen, (180, 30, 90), (px, py), self.radius, 1)


# Overflux 能量核心：玩家持续处于范围内 10 秒后获得 1 残机
class OverfluxOrb:
    CHARGE_FRAMES = int(cfg.FPS * 10)
    RADIUS = 26

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True
        self.charge = 0
        self.lifetime = 1200

    def update(self, player):
        if not self.alive:
            return
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            return
        dist = math.hypot(player.x - self.x, player.y - self.y)
        if dist <= self.RADIUS + player.hitbox_radius:
            self.charge += 1
        else:
            self.charge = 0
        return self.charge >= self.CHARGE_FRAMES

    def draw(self, screen, ox=0, oy=0):
        if not self.alive:
            return
        px = int(self.x + ox)
        py = int(self.y + oy)
        pulse = 0.6 + 0.4 * math.sin(pygame.time.get_ticks() * 0.008)
        r = int(self.RADIUS * pulse) + 2
        pygame.draw.circle(screen, (60, 220, 120), (px, py), r, 2)
        pygame.draw.circle(screen, (120, 255, 170), (px, py), max(4, r // 3), 0)
        # 充能进度环
        progress = min(1.0, self.charge / float(self.CHARGE_FRAMES))
        if progress > 0:
            pygame.draw.arc(screen, (255, 255, 255), (px - r - 4, py - r - 4, (r + 4) * 2, (r + 4) * 2),
                            0, progress * math.tau, 3)


# 召唤小怪：反向移动（缓慢下移），自机狙锁定 Boss 射击，弹幕可抵消敌弹 / 对敌伤害 150
class SummonedMinion:
    SHOOT_INTERVAL = 26
    BULLET_DAMAGE = 150
    BULLET_SPEED = 8.0

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True
        self.timer = random.randint(0, 10)
        self.lifetime = 900
        self.radius = 8
        self.hue = random.choice(((90, 200, 255), (255, 180, 90), (190, 120, 255)))

    def update(self, bullet_manager, boss):
        if not self.alive:
            return
        self.lifetime -= 1
        if self.lifetime <= 0:
            self.alive = False
            return
        self.timer += 1
        # 反向移动：缓慢向下漂移，左右小幅摆动
        self.y = min(cfg.BATTLE_AREA_HEIGHT - 20, self.y + 0.8)
        self.x += math.sin(self.timer * 0.08) * 0.5

        if self.timer % self.SHOOT_INTERVAL == 0:
            if boss is not None and boss.alive and getattr(boss, "combat_enabled", True):
                tx, ty = boss.x, boss.y
            else:
                tx, ty = self.x, self.y - 200
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist < 1:
                dist = 1
            from src.entities import bullet as bm
            b = bm.create_player_bullet(self.x, self.y,
                                        dx / dist * self.BULLET_SPEED,
                                        dy / dist * self.BULLET_SPEED)
            b.damage = self.BULLET_DAMAGE
            b.cancels_bullets = True
            b.radius = 5
            bullet_manager.add_player_bullet(b)

    def draw(self, screen, ox=0, oy=0):
        if not self.alive:
            return
        px = int(self.x + ox)
        py = int(self.y + oy)
        pygame.draw.circle(screen, self.hue, (px, py), self.radius, 0)
        pygame.draw.circle(screen, (30, 30, 60), (px, py), self.radius, 1)
        pygame.draw.circle(screen, (255, 255, 255), (px - 2, py - 2), 2, 0)