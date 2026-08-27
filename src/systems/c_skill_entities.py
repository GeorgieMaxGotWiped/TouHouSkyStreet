# C 技能实体：护盾 / 气球 / 玫瑰 / Orb / 召唤小怪 / 技能视觉特效
# 这些实体由 PlayingState 持有并在 update/draw 中驱动。

import math
import os
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


# ---------------------------------------------------------------------------
# 带透明度的绘制辅助（用于技能视觉特效）
# ---------------------------------------------------------------------------
def _draw_alpha_circle(screen, color, center, radius, width, alpha):
    """绘制带透明度的圆形（实心圆或圆环）。"""
    if alpha <= 0:
        return
    r = max(1, int(radius))
    size = (r + max(2, width)) * 2 + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, (color[0], color[1], color[2], int(alpha)),
                       (size // 2, size // 2), r, width)
    screen.blit(surf, (int(center[0]) - size // 2, int(center[1]) - size // 2))


def _draw_alpha_ellipse(screen, color, center, rx, ry, width, alpha):
    """绘制带透明度的椭圆环（水平冲击波）。"""
    if alpha <= 0:
        return
    rx = max(1, int(rx))
    ry = max(1, int(ry))
    size = (rx + max(2, width)) * 2 + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    rect = pygame.Rect(size // 2 - rx, size // 2 - ry, rx * 2, ry * 2)
    pygame.draw.ellipse(surf, (color[0], color[1], color[2], int(alpha)), rect, width)
    screen.blit(surf, (int(center[0]) - size // 2, int(center[1]) - size // 2))


# ---------------------------------------------------------------------------
# 龙怒（Aspect of the Dragons）：向上喷发的龙焰柱 + 冲击波（纯视觉）
# ---------------------------------------------------------------------------
class DragonRageBurst:
    """龙怒视觉特效：从自机位置向上喷发的多层龙焰柱，附带基座冲击环。"""
    DURATION = 50

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True
        self.timer = 0
        self.particles = []

    def update(self):
        if not self.alive:
            return
        self.timer += 1
        if self.timer > self.DURATION:
            self.alive = False
            return
        # 沿焰柱上升的火焰粒子
        if self.timer % 2 == 0:
            for _ in range(2):
                self.particles.append({
                    "x": self.x + random.uniform(-24, 24),
                    "y": self.y - random.uniform(6, 18),
                    "vy": random.uniform(-6.0, -2.8),
                    "life": random.randint(14, 26),
                    "size": random.randint(3, 7),
                })
        for p in self.particles[:]:
            p["y"] += p["vy"]
            p["life"] -= 1
            if p["life"] <= 0 or p["y"] < -20:
                self.particles.remove(p)

    def draw(self, screen, ox=0, oy=0):
        if not self.alive:
            return
        t = self.timer
        px = int(self.x + ox)
        py = int(self.y + oy)
        top = int(oy)
        height = max(1, py - top)

        # 焰柱宽度随火焰摆动
        sway = math.sin(t * 0.9) * 3.0 + math.sin(t * 2.3) * 1.5
        base_w = 30 + max(0, 8 - t) * 1.5 + sway
        layers = (
            (base_w, (255, 80, 20, 70)),
            (base_w * 0.78, (255, 140, 40, 95)),
            (base_w * 0.5, (255, 225, 130, 125)),
        )
        for w, color in layers:
            surf = pygame.Surface((int(w * 2) + 2, height), pygame.SRCALPHA)
            surf.fill(color)
            screen.blit(surf, (int(px - w), top))
        # 柱内纵向亮纹
        pygame.draw.line(screen, (255, 240, 180), (px, top), (px, py - 8), 2)

        # 上升火焰粒子
        for p in self.particles:
            a = int(200 * p["life"] / 26)
            c = (255, random.randint(120, 200), random.randint(40, 110))
            _draw_alpha_circle(screen, c, (p["x"] + ox, p["y"] + oy),
                               p["size"], 0, max(0, a))

        # 起手闪光（前 10 帧）
        if t <= 10:
            k = t / 10.0
            r = int(14 + k * 46)
            _draw_alpha_circle(screen, (255, 170, 60), (px, py), r, 0, int(200 * (1 - k)))

        # 基座水平冲击环（向两侧扩张）
        if t <= 26:
            k = t / 26.0
            rx = int(10 + k * 130)
            ry = max(3, int(rx * 0.22))
            _draw_alpha_ellipse(screen, (255, 150, 50), (px, py), rx, ry, 3, int(230 * (1 - k)))

        # 上行冲击波（从自机高度扫到屏幕顶端）
        if 4 <= t <= 30:
            k = (t - 4) / 26.0
            wy = py - k * (py - top)
            rx = int(14 + k * 150)
            ry = max(3, int(rx * 0.18))
            _draw_alpha_ellipse(screen, (255, 200, 90), (px, int(wy)), rx, ry, 3, int(220 * (1 - k)))

        # 顶端受击闪光
        if 20 <= t <= 36:
            k = (t - 20) / 16.0
            r = int(12 + k * 80)
            _draw_alpha_circle(screen, (255, 210, 110), (px, top), r, 0, int(180 * (1 - k)))


# ---------------------------------------------------------------------------
# 巨人之剑（Giant's Sword）：巨剑从天而降砸向目标 + 冲击波（纯视觉）
# ---------------------------------------------------------------------------
_GIANTS_SWORD_SPRITE_PATH = os.path.join(
    cfg.SPRITES_DIR, "enemies", "stage5", "goldor", "Big_Sword.png")
_giants_sword_base_attempted = set()
_giants_sword_base_cache = {}
_giants_sword_glow_cache = {}


def _get_giants_sword_base(sword_len):
    """加载金色巨剑贴图：抠除黑底，按剑身长度等比缩放，剑刃朝下。"""
    key = int(round(sword_len))
    if key in _giants_sword_base_attempted:
        return _giants_sword_base_cache.get(key)
    _giants_sword_base_attempted.add(key)
    sprite = None
    try:
        img = pygame.image.load(_GIANTS_SWORD_SPRITE_PATH).convert_alpha()
        w, h = img.get_size()
        arr = pygame.surfarray.array3d(img)
        alpha = pygame.surfarray.array_alpha(img)
        alpha[arr.max(axis=2) < 26] = 0
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.surfarray.pixels_alpha(surf)[:] = alpha
        red = pygame.surfarray.pixels_red(surf)
        green = pygame.surfarray.pixels_green(surf)
        blue = pygame.surfarray.pixels_blue(surf)
        red[:] = arr[:, :, 0]
        green[:] = arr[:, :, 1]
        blue[:] = arr[:, :, 2]
        del red, green, blue
        side = max(1, int(round(sword_len / math.sqrt(2))))
        base = pygame.transform.smoothscale(surf, (side, side))
        sprite = pygame.transform.rotate(base, 315)  # 让剑刃竖直向下
    except Exception as exc:
        print(f"[GiantsSwordStrike] Failed to load sword sprite: {exc}")
    _giants_sword_base_cache[key] = sprite
    return sprite


def _get_giants_sword_glow(radius):
    """落点金色辉光（缓存）。"""
    key = int(radius)
    glow = _giants_sword_glow_cache.get(key)
    if glow is not None:
        return glow
    size = key * 2
    glow = pygame.Surface((size, size), pygame.SRCALPHA)
    for r in range(key, 0, -1):
        alpha = int(50 * (1 - r / float(key)))
        pygame.draw.circle(glow, (255, 200, 110, alpha), (key, key), r)
    _giants_sword_glow_cache[key] = glow
    return glow


class GiantsSwordStrike:
    """巨人之剑视觉特效：巨剑从天而降砸向目标，落地产生冲击波与白闪。"""
    SWORD_LEN = 170
    DESCEND_FRAMES = 20
    DURATION = 66

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.alive = True
        self.timer = 0
        self.sword = _get_giants_sword_base(self.SWORD_LEN)
        self.glow = _get_giants_sword_glow(int(self.SWORD_LEN * 0.45))
        self.particles = []

    def _sword_center_y(self):
        """下落阶段返回剑中心 y（战斗区坐标，加速下落），落地后固定。"""
        if self.timer >= self.DESCEND_FRAMES:
            return self.y
        k = self.timer / float(self.DESCEND_FRAMES)
        start = -self.SWORD_LEN - 60
        return start + (self.y - start) * (k * k)

    def update(self):
        if not self.alive:
            return
        self.timer += 1
        if self.timer > self.DURATION:
            self.alive = False
            return
        # 落地后迸发金色火星
        if self.timer > self.DESCEND_FRAMES and self.timer % 2 == 0:
            for _ in range(3):
                angle = random.uniform(-math.pi, math.pi)
                speed = random.uniform(1.5, 6.5)
                self.particles.append({
                    "x": self.x,
                    "y": self.y,
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed - 1.0,
                    "life": random.randint(16, 30),
                    "size": random.randint(2, 5),
                })
        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vy"] += 0.12
            p["life"] -= 1
            if p["life"] <= 0:
                self.particles.remove(p)

    def draw(self, screen, ox=0, oy=0):
        if not self.alive:
            return
        t = self.timer
        px = int(self.x + ox)
        py = int(self.y + oy)
        sword = self.sword
        if sword is None:
            return

        if t < self.DESCEND_FRAMES:
            sword_y = self._sword_center_y() + oy
        else:
            shake = random.uniform(-1.5, 1.5) if t < self.DESCEND_FRAMES + 10 else 0.0
            sword_y = py + shake

        # 下落残影 + 金色光柱
        if t < self.DESCEND_FRAMES:
            pygame.draw.line(screen, (255, 235, 170),
                             (px, int(oy)), (px, int(sword_y - sword.get_height() // 2 + 6)), 2)
            for i, ghost_y in enumerate((sword_y - 26, sword_y - 52, sword_y - 78)):
                ghost = sword.copy()
                ghost.set_alpha(80 - i * 25)
                screen.blit(ghost, (px - ghost.get_width() // 2, int(ghost_y - ghost.get_height() // 2)))
        else:
            # 落点金色辉光（落地后渐强再渐弱）
            fade_k = max(0.0, 1.0 - (t - self.DESCEND_FRAMES) / float(self.DURATION - self.DESCEND_FRAMES + 8))
            glow = self.glow.copy()
            glow.set_alpha(int(255 * fade_k))
            screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))

            # 冲击波环（落地后向外扩张）
            k = (t - self.DESCEND_FRAMES) / 20.0
            if k <= 1.0:
                rx = int(30 + k * 300)
                ry = max(4, int(rx * 0.5))
                _draw_alpha_ellipse(screen, (255, 215, 120), (px, py), rx, ry, 4, int(230 * (1 - k)))
                _draw_alpha_ellipse(screen, (255, 160, 60), (px, py),
                                    max(2, rx - 26), max(3, ry - 14), 3, int(200 * (1 - k)))

            # 全屏白闪（前 8 帧渐隐）
            if t - self.DESCEND_FRAMES <= 8:
                a = int(150 * (1 - (t - self.DESCEND_FRAMES) / 8.0))
                if a > 0:
                    flash = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT), pygame.SRCALPHA)
                    flash.fill((255, 245, 220, a))
                    screen.blit(flash, (ox, oy))

        # 剑本体
        screen.blit(sword, (px - sword.get_width() // 2,
                            int(sword_y - sword.get_height() // 2)))

        # 金色火星
        for p in self.particles:
            a = int(220 * p["life"] / 30)
            c = (255, random.randint(170, 230), random.randint(60, 120))
            _draw_alpha_circle(screen, c, (p["x"] + ox, p["y"] + oy),
                               p["size"], 0, max(0, a))
