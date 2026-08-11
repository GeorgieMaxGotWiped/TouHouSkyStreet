# 弹幕模式生成器
# 各种可复用的弹幕生成函数

import math
import random
from src.entities.bullet import Bullet, create_bullet_aimed, create_bullet_angle

class BulletPatterns:
    """弹幕模式集合"""

    @staticmethod
    def aimed_shot(source_x, source_y, target_x, target_y, speed=3.0):
        """基础自机狙"""
        return create_bullet_aimed(source_x, source_y, target_x, target_y, speed,
                                   Bullet.TYPE_CIRCLE, radius=3)

    @staticmethod
    def aimed_n_way(source_x, source_y, target_x, target_y, n=3, spread=0.3, speed=3.0):
        """N方向自机狙"""
        bullets = []
        base_angle = math.atan2(target_y - source_y, target_x - source_x)
        for i in range(n):
            offset = (i - (n - 1) / 2) * spread
            angle = base_angle + offset
            b = create_bullet_angle(source_x, source_y, angle, speed,
                                    Bullet.TYPE_CIRCLE, radius=3)
            bullets.append(b)
        return bullets

    @staticmethod
    def circle_burst(source_x, source_y, count=12, speed=2.0, offset_angle=0):
        """圆形爆发"""
        bullets = []
        for i in range(count):
            angle = offset_angle + i * math.pi * 2 / count
            b = create_bullet_angle(source_x, source_y, angle, speed,
                                    Bullet.TYPE_CIRCLE, radius=3)
            bullets.append(b)
        return bullets

    @staticmethod
    def spiral(source_x, source_y, count=6, speed=2.0, rotation_speed=0.05, timer=0):
        """旋转弹幕"""
        bullets = []
        for i in range(count):
            angle = timer * rotation_speed + i * math.pi * 2 / count
            b = create_bullet_angle(source_x, source_y, angle, speed,
                                    Bullet.TYPE_RICE, radius=2.5)
            bullets.append(b)
        return bullets

    @staticmethod
    def wave_from_edges(screen_width, screen_height, timer=0, speed=2.0):
        """从屏幕边缘发射波状弹"""
        bullets = []
        wave_count = 6
        for i in range(wave_count):
            x = screen_width * i / (wave_count - 1)
            angle = math.pi / 2 + math.sin(timer * 0.02 + i * 0.5) * 0.3
            b = create_bullet_angle(x, -10, angle, speed,
                                    Bullet.TYPE_ARROW, radius=3)
            bullets.append(b)
        return bullets

    @staticmethod
    def random_barrage(source_x, source_y, count=10, speed_range=(1.5, 3.5)):
        """随机弹幕"""
        bullets = []
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            speed = random.uniform(*speed_range)
            b = create_bullet_angle(source_x, source_y, angle, speed,
                                    Bullet.TYPE_KNIFE, radius=2.5)
            bullets.append(b)
        return bullets

    @staticmethod
    def laser_curtain(source_x, source_y, width, count=8, speed=2.0):
        """激光帷幕（垂直排列的弹列）"""
        bullets = []
        for i in range(count):
            x = source_x - width / 2 + i * width / (count - 1)
            b = Bullet(x, source_y, 0, speed, Bullet.TYPE_ARROW,
                       radius=3, color=(255, 200, 50))
            bullets.append(b)
        return bullets
