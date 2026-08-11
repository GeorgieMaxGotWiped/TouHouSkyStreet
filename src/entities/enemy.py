# 敌人系统
# 基础敌人、波次管理、敌人生成器

import math
import random
import pygame
from src.engine import settings as cfg
from src.engine.collision import circle_collision, circle_ellipse_collision
from src.entities.bullet import Bullet, create_bullet_aimed, create_bullet_angle

# 小怪贴图缓存（路径 + 目标高度 -> Surface）
_enemy_sprite_cache = {}
_enemy_sprite_attempted = set()


def _get_enemy_sprite(path, target_height):
    key = (path, target_height)
    if key in _enemy_sprite_attempted:
        return _enemy_sprite_cache.get(key)
    _enemy_sprite_attempted.add(key)
    try:
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        if h <= 0:
            raise ValueError("invalid sprite height")
        new_w = max(1, int(round(w * target_height / h)))
        _enemy_sprite_cache[key] = pygame.transform.smoothscale(img, (new_w, target_height))
    except Exception as exc:
        print(f"[Enemy] Failed to load enemy sprite {path}: {exc}")
    return _enemy_sprite_cache.get(key)


# 贴图判定范围缓存（(路径, 目标高度) -> (半宽, 半高)）
_enemy_hitbox_cache = {}


def _get_enemy_hitbox_radii(path, target_height, alpha_threshold=32):
    """按贴图不透明像素包围盒生成椭圆判定半轴（不含发光边缘）"""
    key = (path, target_height)
    if key in _enemy_hitbox_cache:
        return _enemy_hitbox_cache[key]
    sprite = _get_enemy_sprite(path, target_height)
    if sprite is None:
        _enemy_hitbox_cache[key] = None
        return None
    w, h = sprite.get_size()
    minx, miny, maxx, maxy = w, h, -1, -1
    for y in range(h):
        for x in range(w):
            if sprite.get_at((x, y))[3] > alpha_threshold:
                minx, miny = min(minx, x), min(miny, y)
                maxx, maxy = max(maxx, x), max(maxy, y)
    if maxx < 0:
        _enemy_hitbox_cache[key] = None
        return None
    _enemy_hitbox_cache[key] = ((maxx - minx + 1) / 2.0, (maxy - miny + 1) / 2.0)
    return _enemy_hitbox_cache[key]


# 呼吸透明度：围绕 mid 以 amp 幅度正弦波动（慢速、最大亮度较低）
def _breath_alpha(age, mid=120, amp=35, speed=0.04):
    return int(mid + amp * math.sin(age * speed))


# 白色发光层缓存（(贴图路径, 目标高度) -> (贴图, 白色层)）
_outlined_layers_cache = {}


def _get_outlined_layers(path, target_height, outline_width=2, glow_radius=7):
    key = (path, target_height, outline_width, glow_radius)
    if key in _outlined_layers_cache:
        return _outlined_layers_cache[key]
    sprite = _get_enemy_sprite(path, target_height)
    if sprite is None:
        _outlined_layers_cache[key] = (None, None)
        return (None, None)
    sw, sh = sprite.get_size()
    pad = outline_width + glow_radius
    out = pygame.Surface((sw + pad * 2, sh + pad * 2), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(sprite, threshold=32)
    silhouette = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    # 外层柔光：向四周扩散，且从贴图边缘向外亮度递减
    for dy in range(-glow_radius, glow_radius + 1):
        for dx in range(-glow_radius, glow_radius + 1):
            dist = math.hypot(dx, dy)
            if dist <= glow_radius:
                t = dist / glow_radius
                silhouette.set_alpha(int(90 * (1 - t)))
                out.blit(silhouette, (pad + dx, pad + dy))
    # 内层白边（紧贴轮廓；透明度由呼吸统一控制）
    silhouette.set_alpha(255)
    for dy in range(-outline_width, outline_width + 1):
        for dx in range(-outline_width, outline_width + 1):
            if dx * dx + dy * dy <= outline_width * outline_width:
                out.blit(silhouette, (pad + dx, pad + dy))
    _outlined_layers_cache[key] = (sprite, out)
    return sprite, out


# 六边形白色光晕缓存（按半径）
_hexagon_glow_cache = {}


def _get_hexagon_glow(radius):
    if radius in _hexagon_glow_cache:
        return _hexagon_glow_cache[radius]
    r = radius + 2
    size = int(r * 2) + 4
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    pts = []
    for i in range(6):
        a = i * math.pi / 3 - math.pi / 6
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    pygame.draw.polygon(surf, (255, 255, 255, 255), pts, 0)
    _hexagon_glow_cache[radius] = surf
    return surf


class Enemy:
    """基础敌人类"""
    def __init__(self, x, y, hp=100, score=1000, size=12, color=None,
                 sprite_paths=None, sprite_height=None, anim_speed=15):
        self.x = x
        self.y = y
        self.vx = 0.0
        self.vy = 0.0
        self.hp = hp
        self.max_hp = hp
        self.score = score
        self.size = size
        self.color = color or cfg.COLOR_RED
        self.alive = True
        self.age = 0
        self.defense = 1.0  # 防御力：实际受伤 = 伤害 / defense（1.0 = 原版）

        # 贴图（多帧循环动画）
        self.sprite_paths = sprite_paths or []
        self.sprite_height = sprite_height
        self.anim_speed = anim_speed

        # 射击
        self.shoot_timer = 0
        self.shoot_interval = 60   # 射击间隔（帧）
        self.shoot_pattern = "aimed"  # aimed / spread / circle / none

        # 移动模式
        self.move_pattern = "static"  # static / linear / sin / descend
        self.move_speed = 1.0
        self.move_amplitude = 0.0

        # 道具掉落
        self.drop_item = None
        self.drop_chance = 0.0

        # 入场计时
        self.entry_done = False
        self.entry_timer = 60

    def update(self, dt, player_x=0, player_y=0):
        self.age += 1

        # 入场
        if not self.entry_done:
            self.entry_timer -= 1
            if self.entry_timer <= 0:
                self.entry_done = True
            return

        # 移动
        self._move()

        # 离开战斗区域则自动退场（防止漏怪导致卡关）
        if (self.x < -50 or self.x > cfg.BATTLE_AREA_WIDTH + 50
                or self.y > cfg.BATTLE_AREA_HEIGHT + 50):
            self.alive = False
            return

        # 射击
        self.shoot_timer -= 1

    def _move(self):
        if self.move_pattern == "static":
            pass
        elif self.move_pattern == "linear":
            self.x += self.vx
            self.y += self.vy
        elif self.move_pattern == "sin":
            self.x += self.vx
            self.y += math.sin(self.age * 0.03) * self.move_amplitude
        elif self.move_pattern == "strafe":
            # 下降推进 + 水平小幅横移（适合射手类敌人，如二面骷髅射手）
            self.y += self.move_speed
            self.x += math.sin(self.age * 0.04) * self.move_amplitude
        elif self.move_pattern == "descend":
            self.y += self.move_speed

    def can_shoot(self):
        if self.shoot_timer <= 0 and self.entry_done:
            self.shoot_timer = self.shoot_interval
            return True
        return False

    def shoot(self, bullet_manager, player_x, player_y):
        """默认射击：瞄准玩家"""
        if self.shoot_pattern == "aimed":
            b = create_bullet_aimed(self.x, self.y, player_x, player_y, 2.5,
                                    Bullet.TYPE_CIRCLE, radius=3, color=cfg.COLOR_RED)
            bullet_manager.add_enemy_bullet(b)
        elif self.shoot_pattern == "spread":
            for angle_offset in [-0.3, -0.15, 0, 0.15, 0.3]:
                angle = math.atan2(player_y - self.y, player_x - self.x) + angle_offset
                b = create_bullet_angle(self.x, self.y, angle, 2.0,
                                        Bullet.TYPE_RICE, radius=2.5, color=cfg.COLOR_ORANGE)
                bullet_manager.add_enemy_bullet(b)
        elif self.shoot_pattern == "circle":
            for i in range(12):
                angle = i * math.pi * 2 / 12
                b = create_bullet_angle(self.x, self.y, angle, 1.5,
                                        Bullet.TYPE_CIRCLE, radius=2.5, color=cfg.COLOR_PURPLE)
                bullet_manager.add_enemy_bullet(b)

    def take_damage(self, damage):
        self.hp -= damage / self.defense
        if self.hp <= 0:
            self.alive = False
            return True  # 被击破
        return False

    def draw(self, screen, offset_x=0, offset_y=0):
        px = int(self.x + offset_x)
        py = int(self.y + offset_y)

        if not self.entry_done:
            # 入场动画：闪烁
            if self.entry_timer % 10 < 5:
                return

        # HP条
        if self.hp < self.max_hp:
            bar_w = self.size * 2
            bar_h = 3
            bar_x = px - self.size
            bar_y = py - self.size - 6
            hp_ratio = self.hp / self.max_hp
            pygame.draw.rect(screen, cfg.COLOR_DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
            pygame.draw.rect(screen, cfg.COLOR_RED, (bar_x, bar_y, int(bar_w * hp_ratio), bar_h))

        # 贴图（若有）：多帧循环 + 半透明白色呼吸描边
        if self.sprite_paths:
            frame = (self.age // self.anim_speed) % len(self.sprite_paths)
            sprite, white_layer = _get_outlined_layers(self.sprite_paths[frame], self.sprite_height)
            if sprite is not None and white_layer is not None:
                glow = white_layer.copy()
                glow.set_alpha(_breath_alpha(self.age))
                screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))
                screen.blit(sprite, (px - sprite.get_width() // 2, py - sprite.get_height() // 2))
                return

        # 本体（六边形）+ 半透明白色呼吸描边
        glow = _get_hexagon_glow(self.size)
        g = glow.copy()
        g.set_alpha(_breath_alpha(self.age))
        screen.blit(g, (px - g.get_width() // 2, py - g.get_height() // 2))
        self._draw_hexagon(screen, px, py)

    def _draw_hexagon(self, screen, px, py):
        r = self.size
        points = []
        for i in range(6):
            angle = i * math.pi / 3 - math.pi / 6
            points.append((px + math.cos(angle) * r, py + math.sin(angle) * r))
        pygame.draw.polygon(screen, self.color, points, 0)
        # 内圈
        inner = tuple(min(255, c + 80) for c in self.color)
        pygame.draw.polygon(screen, inner, points, 2)

    def get_hitbox(self):
        """返回 (x, y, 半宽, 半高)；有贴图时贴合贴图（不含发光），否则回退圆形"""
        if self.sprite_paths:
            radii = _get_enemy_hitbox_radii(self.sprite_paths[0], self.sprite_height)
            if radii is not None:
                return (self.x, self.y, radii[0], radii[1])
        return (self.x, self.y, self.size * 0.85, self.size * 0.85)

    def collides_with_bullet(self, bx, by, br):
        """子弹 vs 椭圆判定：贴合贴图（不含发光边缘）"""
        hx, hy, hrx, hry = self.get_hitbox()
        return circle_ellipse_collision(bx, by, br, hx, hy, hrx, hry)


class FairyEnemy(Enemy):
    """妖精敌人（最基础的小怪）"""
    def __init__(self, x, y, move_pattern="descend", sprite_paths=None, sprite_height=None):
        super().__init__(x, y, hp=40, score=500, size=13, color=cfg.COLOR_GREEN,
                         sprite_paths=sprite_paths if sprite_paths is not None else cfg.FAIRY_SPRITES,
                         sprite_height=sprite_height if sprite_height is not None else cfg.FAIRY_SPRITE_HEIGHT)
        self.move_pattern = move_pattern
        self.move_speed = 1.2
        self.shoot_interval = 90
        self.shoot_pattern = "aimed"


class FairyVolleyEnemy(FairyEnemy):
    """齐射妖精：数值与普通妖精完全一致，但按一串阵型降下后，以极短间隔依次开火。

    串首（volley_index=0）先开火，其余按 volley_stagger 帧依次跟上；
    首轮延迟 lead_in 帧让整串先降入画面，之后每轮保持普通妖精的 90 帧射击间隔。
    """
    def __init__(self, x, y, volley_index=0, volley_stagger=8, lead_in=120,
                 sprite_paths=None, sprite_height=None):
        super().__init__(x, y, "descend",
                         sprite_paths=sprite_paths,
                         sprite_height=sprite_height)
        self.volley_index = volley_index
        self.volley_stagger = volley_stagger   # 相邻两只的开火间隔（帧）
        # 首弹延迟：串尾最晚开火；射完由基类重置为 90 帧间隔
        self.shoot_timer = lead_in + volley_index * volley_stagger


class SpiritEnemy(Enemy):
    """灵体敌人（散射弹）"""
    def __init__(self, x, y, move_pattern="sin", sprite_paths=None, sprite_height=None):
        super().__init__(x, y, hp=80, score=800, size=15, color=cfg.COLOR_PURPLE,
                         sprite_paths=sprite_paths if sprite_paths is not None else cfg.SPIRIT_SPRITES,
                         sprite_height=sprite_height if sprite_height is not None else cfg.SPIRIT_SPRITE_HEIGHT,
                         anim_speed=20)
        self.move_pattern = move_pattern
        self.move_speed = 0.8
        self.move_amplitude = 2.0
        self.vx = random.choice([-1.0, 1.0]) * 0.8
        self.shoot_interval = 120
        self.shoot_pattern = "spread"


class GuardEnemy(Enemy):
    """守卫敌人（圆形弹幕）"""
    def __init__(self, x, y, sprite_paths=None, sprite_height=None):
        super().__init__(x, y, hp=200, score=2000, size=19, color=cfg.COLOR_ORANGE,
                         sprite_paths=sprite_paths if sprite_paths is not None else cfg.GUARD_SPRITES,
                         sprite_height=sprite_height if sprite_height is not None else cfg.GUARD_SPRITE_HEIGHT,
                         anim_speed=30)
        self.move_pattern = "static"
        self.shoot_interval = 150
        self.shoot_pattern = "circle"


class GraveCasterEnemy(Enemy):
    """墓穴唤魂者（三面小怪）：入场快速下坠到部署位后转为缓慢下落；
    部署完成后以 5 连环形弹幕齐射（每环弹速随存在时间递减），略作停顿后循环，直至被消灭"""

    def __init__(self, x, y, deploy_y=165, ring_count=14,
                 sprite_paths=None, sprite_height=None):
        super().__init__(x, y, hp=120, score=1500, size=15, color=(96, 224, 200),
                         sprite_paths=sprite_paths if sprite_paths is not None else cfg.STAGE3_CASTER_SPRITES,
                         sprite_height=sprite_height if sprite_height is not None else cfg.STAGE3_CASTER_SPRITE_HEIGHT,
                         anim_speed=18)
        self.deploy_y = deploy_y          # 快速下坠的目标位置
        self.ring_count = ring_count      # 每环子弹数
        self.dive_speed = 7.0             # 入场快速下坠速度
        self.move_speed = 0.8             # 部署后的正常下落速度
        self.defense = 2.0
        self.phase = "dive"               # dive -> descend
        self.entry_done = True            # 入场动画由 dive 阶段承担
        self.shoot_pattern = "none"       # 不使用基类射击
        # 5 连环形齐射状态机
        self.volley_shot = 0              # 本组已发射环数
        self.volley_ring_count = 5        # 每组环数
        self.volley_timer = 0             # 环间间隔倒计时
        self.volley_interval = 9          # 环间帧数（快速连发）
        self.pause_timer = 0              # 组间停顿倒计时
        self.pause_frames = 110           # 组间停顿帧数
        # 环形弹速：初始速度 + 随弹自身存在时间匀减速，下限保证能飞出屏幕
        self.ring_speed = 2.8             # 初始速度
        self.ring_brake = 0.015           # 每帧减速量（弹速随该弹存在时间递减）
        self.ring_brake_floor = 2.2       # 减速下限（保证即使最远斜角也能飞出屏幕）
        self.ring_lifetime = 400          # 环形弹寿命

    def update(self, dt, player_x=0, player_y=0):
        self.age += 1

        # 入场：快速下坠一小段距离
        if self.phase == "dive":
            self.y += self.dive_speed
            if self.y >= self.deploy_y:
                self.y = self.deploy_y
                self.phase = "descend"
            return

        # 正常下落
        self.y += self.move_speed

        # 离开战斗区域则自动退场（防止漏怪导致卡关）
        if (self.x < -50 or self.x > cfg.BATTLE_AREA_WIDTH + 50
                or self.y > cfg.BATTLE_AREA_HEIGHT + 50):
            self.alive = False
            return

        # 齐射状态机：连发 5 环 -> 组间停顿 -> 循环
        if self.volley_shot >= self.volley_ring_count:
            self.pause_timer += 1
            if self.pause_timer >= self.pause_frames:
                self.volley_shot = 0
                self.volley_timer = 0
                self.pause_timer = 0
        else:
            self.volley_timer -= 1

    def can_shoot(self):
        """基类按 shoot_interval 触发单次射击；此处改为按齐射状态机触发"""
        return (self.phase == "descend"
                and self.volley_shot < self.volley_ring_count
                and self.volley_timer <= 0)

    def shoot(self, bullet_manager, player_x, player_y):
        """每调用一次发射一环；连发 5 环后进入组间停顿"""
        if self.volley_shot >= self.volley_ring_count:
            return
        self.volley_shot += 1
        self.volley_timer = self.volley_interval
        # 五环方向保持一致（不逐环旋转错开）；环速随该弹自身存在时间匀减速
        for i in range(self.ring_count):
            angle = i * math.tau / self.ring_count
            b = create_bullet_angle(self.x, self.y, angle, self.ring_speed,
                                    Bullet.TYPE_CIRCLE, radius=2.5,
                                    color=(96, 216, 196), lifetime=self.ring_lifetime)
            b.brake = self.ring_brake
            b.brake_floor = self.ring_brake_floor
            bullet_manager.add_enemy_bullet(b)


class EnemyWave:
    """敌机波次"""
    def __init__(self, enemies, delay=0, name=""):
        self.enemies = enemies          # 该波次的敌人列表
        self.delay = delay              # 波次开始前延迟（帧）
        self.name = name
        self.spawned = False
        self.delay_timer = delay

    def update(self, dt):
        if not self.spawned:
            self.delay_timer -= 1
            if self.delay_timer <= 0:
                self.spawned = True

    @property
    def all_dead(self):
        if not self.spawned:
            return False
        return all(not e.alive for e in self.enemies)


class EnemyManager:
    """敌机管理器"""
    def __init__(self):
        self.waves = []             # 波次队列（顺序模式）
        self.timed_waves = []       # 定时波次 [(start_time, wave)]
        self.active_enemies = []    # 当前活跃敌人
        self.current_wave_idx = 0
        self.wave_complete = False

    def add_wave(self, wave):
        self.waves.append(wave)

    def add_timed_wave(self, start_time, wave):
        """添加按时间轴生成的波次（帧，到时间即出，不依赖上一波清空）"""
        self.timed_waves.append((start_time, wave))

    def update(self, dt, bullet_manager, player_x, player_y, stage_time=None):
        self.active_enemies = []

        # 定时波次：到时间即生成
        if stage_time is not None:
            for t, wave in self.timed_waves:
                if not wave.spawned and stage_time >= t:
                    wave.spawned = True

        # 检查当前顺序波次
        if self.current_wave_idx < len(self.waves):
            wave = self.waves[self.current_wave_idx]
            wave.update(dt)

            if wave.spawned:
                self.active_enemies.extend(wave.enemies)

            if wave.all_dead:
                self.current_wave_idx += 1
                if self.current_wave_idx >= len(self.waves):
                    self.wave_complete = True
        else:
            self.wave_complete = True

        # 已生成的定时波次同样计入活跃敌人
        for t, wave in self.timed_waves:
            if wave.spawned:
                self.active_enemies.extend(wave.enemies)

        # 更新活跃敌人
        for enemy in self.active_enemies[:]:
            if enemy.alive:
                enemy.update(dt, player_x, player_y)
                if enemy.can_shoot():
                    enemy.shoot(bullet_manager, player_x, player_y)

    def draw(self, screen, offset_x=0, offset_y=0):
        for enemy in self.active_enemies:
            if enemy.alive:
                enemy.draw(screen, offset_x, offset_y)

    def get_active_enemies(self):
        return [e for e in self.active_enemies if e.alive]

    def is_cleared(self):
        if not self.wave_complete:
            return False
        return all(wave.all_dead for _, wave in self.timed_waves)

    def reset(self):
        self.waves.clear()
        self.timed_waves.clear()
        self.active_enemies.clear()
        self.current_wave_idx = 0
        self.wave_complete = False

