# 子弹系统
# 支持玩家弹和敌弹，多种渲染形状

import math
import pygame
from src.engine import settings as cfg
from src.engine.collision import circle_collision, point_segment_distance
from src.entities import bullet_atlas

# 消弹动画时长（帧）：弹幕变白自爆的持续时间
BULLET_CANCEL_DURATION = 20

# 玩家子弹贴图缓存
_player_bullet_sprite = None
_player_bullet_sprite_attempted = False


_custom_bullet_sprite_cache = {}
_custom_bullet_sprite_attempted = set()


def _get_custom_bullet_sprite(path, target_height):
    """Load and cache an arbitrary bullet sprite, scaled by height."""
    key = (path, target_height)
    if key in _custom_bullet_sprite_attempted:
        return _custom_bullet_sprite_cache.get(key)
    _custom_bullet_sprite_attempted.add(key)
    try:
        img = pygame.image.load(path).convert_alpha()
        w, h = img.get_size()
        if h <= 0:
            raise ValueError("invalid custom bullet sprite height")
        new_w = max(1, int(round(w * target_height / h)))
        _custom_bullet_sprite_cache[key] = pygame.transform.smoothscale(
            img, (new_w, target_height))
    except Exception as exc:
        print(f"[Bullet] Failed to load custom bullet sprite {path}: {exc}")
    return _custom_bullet_sprite_cache.get(key)


def _build_sprite_glow(sprite, color, pad):
    """沿贴图轮廓生成小范围高强度发光层（白色描边）；失败返回 None。"""
    try:
        mask = pygame.mask.from_surface(sprite)
    except Exception:
        return None
    w, h = sprite.get_size()
    glow = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
    try:
        # 多层半径同心外扩：内亮外柔的白色光晕
        for radius, alpha in (
            (pad, 200),
            (max(1, int(pad * 0.66)), 150),
            (max(1, int(pad * 0.33)), 80),
        ):
            layer = mask.to_surface(
                setcolor=(color[0], color[1], color[2], alpha),
                unsetcolor=(0, 0, 0, 0))
            for dx in (-radius, 0, radius):
                for dy in (-radius, 0, radius):
                    if dx == 0 and dy == 0:
                        continue
                    glow.blit(layer, (pad + dx, pad + dy))
    except Exception:
        return None
    return glow


def _get_player_bullet_sprite():
    """加载并缓存玩家子弹贴图；失败返回 None（回退原来的米弹绘制）"""
    global _player_bullet_sprite, _player_bullet_sprite_attempted
    if _player_bullet_sprite_attempted:
        return _player_bullet_sprite
    _player_bullet_sprite_attempted = True
    try:
        img = pygame.image.load(cfg.PLAYER_BULLET_SPRITE)
        try:
            img = img.convert_alpha()
        except Exception:
            pass
        size = cfg.PLAYER_BULLET_SPRITE_SIZE
        _player_bullet_sprite = pygame.transform.smoothscale(img, (size, size))
    except Exception as e:
        print(f"[Bullet] Failed to load player bullet sprite: {e}")
        _player_bullet_sprite = None
    return _player_bullet_sprite


class Bullet:
    """基础子弹类"""
    # 子弹类型
    TYPE_CIRCLE = "circle"        # 圆形（圆弹）
    TYPE_RICE = "rice"            # 米弹
    TYPE_ARROW = "arrow"          # 箭弹
    TYPE_BIG = "big"              # 大玉
    TYPE_LASER = "laser"          # 激光（特殊处理）
    TYPE_KNIFE = "knife"          # 刀弹
    TYPE_BEAM = "beam"            # 光束线（两点连线，电网连接用）
    size_scale_global = 1.0       # 敌弹全局尺寸倍率（末影龙放大子弹，其他 Boss 默认 1.0）

    def __init__(self, x, y, vx, vy, bullet_type=TYPE_CIRCLE, radius=3.0,
                 color=None, damage=10, is_player_bullet=False, lifetime=600,
                 homing=False):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.bullet_type = bullet_type
        self.size_scale = getattr(Bullet, "size_scale_global", 1.0)
        if is_player_bullet:
            self.radius = radius
            self.collision_radius = radius * 0.6
            self.visual_radius = self.radius
        else:
            # 敌弹：视觉放大；判定按 size_scale 同步缩放（默认 1.0 时判定不变）
            self.radius = radius * cfg.ENEMY_BULLET_RADIUS_SCALE * self.size_scale
            self.collision_radius = radius * 0.5 * self.size_scale
            self.visual_radius = self.radius
            # 有图集贴图的弹幕：判定改为按贴图原始像素尺寸换算（贴图不再随 radius 缩放）
            slot = cfg.ENEMY_BULLET_SPRITE_MAP.get(bullet_type)
            if slot and self.radius <= cfg.ENEMY_BULLET_SPRITE_MAX_RADIUS:
                native = bullet_atlas.get_native_size(slot)
                if native:
                    visual_r = min(native) / 2.0
                    self.visual_radius = visual_r
                    self.collision_radius = visual_r * cfg.ENEMY_BULLET_HITBOX_FACTOR * self.size_scale
        self.color = color or cfg.COLOR_RED
        self.damage = damage
        self.is_player_bullet = is_player_bullet
        self.lifetime = lifetime
        self.age = 0
        self.cancel_timer = 0   # 消弹剩余帧数（>0 时进入变白自爆动画）
        self.alive = True
        self.grazed = False  # 是否已被擦弹计数
        self.homing = homing    # 是否自动追踪敌人
        self.harmless = False    # 无判定子弹：绘制/成形期间不参与碰撞与擦弹（如蛛网）
        self.shootable = False   # 可被玩家子弹击破的敌弹（如展符缺口大玉）
        self.hp = 0              # 可击破敌弹的剩余生命值（<=0 时被击破）
        self.explode_radius = 0  # 击破后的爆炸清弹半径（0=无爆炸）
        self.sprite_slot = None      # 图集槽位覆盖（None=按弹种默认映射）
        self.custom_sprite_path = None      # optional external sprite
        self.custom_sprite_height = None
        self.custom_sprite_angle = 0.0  # external sprite rotation offset
        self.glow_color = None          # 外发光颜色（None=不发光；如骷髅暗色贴图用白色描边）
        self.glow_padding = 5           # 发光描边外扩像素
        self._sprite_cache = {}      # (slot, width, angle) -> Surface 旋转贴图缓存

        # 特殊弹幕行为（默认普通直线弹，符卡按需启用）
        self.manager = None          # 子弹管理器引用（转向/分裂瞄准用）
        self.accel = 0.0             # 沿当前方向每帧加速量（追魂大玉）
        self.brake = 0.0             # 每帧匀减速量（织网结点等）
        self.brake_delay = 0         # 延迟减速帧数：先匀速飞行，经过一段距离后再逐渐减速
        self.brake_floor = 0.0       # 匀减速下限速度（0=可减速到停止；>0 时不低于该速度）
        self.wobble_amp = 0.0        # 蛇形摆动幅度（垂直方向偏移）
        self.wobble_freq = 0.0       # 摆动频率（弧度/帧）
        self.wobble_phase = 0.0      # 摆动相位
        self.wobble_offset = 0.0     # 上一帧摆动偏移（用于增量计算）
        self.turn_rate = 0.0         # 恒定角速度（弧度/帧，螺旋弹）
        self.steer_speed = 0.0       # 朝玩家转向的角速度上限（0=不追踪）
        self.orbit_center = None     # 公转中心 (cx, cy)，None=不公转
        self.orbit_radius = 0.0      # 当前公转半径
        self.orbit_angle = 0.0       # 当前公转角度
        self.orbit_speed = 0.0       # 公转角速度（弧度/帧）
        self.orbit_grow = 0.0        # 公转半径每帧外扩量
        self.orbit_break = None      # 半径超过该值后脱离公转沿切线飞出
        self.orbit_break_speed = 0.0 # 脱离公转后的切线速度
        self.split_spec = None       # one-shot split config
        self.emit_spec = None        # continuous emitter config
        self.emit_timer = 0          # emitter frame counter
        self.beam_length = 0.0       # 光束线长度（TYPE_BEAM 专用）
        self.ignore_offscreen = False  # 桥/通道等长弹幕允许长时间待在屏幕外

        # 速度加速子弹
        self.ax = 0.0
        self.ay = 0.0

        # 角度（用于旋转弹）
        self.angle = math.atan2(vy, vx)
        self.base_speed = math.hypot(vx, vy)  # 初始速度（擦弹减速效果还原用）

    def update(self, dt):
        # 消弹中：冻结在原地播放变白自爆动画
        if self.cancel_timer > 0:
            self.cancel_timer -= 1
            if self.cancel_timer <= 0:
                self.alive = False
            return

        self.age += 1
        if self.age > self.lifetime:
            self.alive = False
            return

        # 分裂弹：计时结束后原地爆出一圈子弹，本体消失（已离开战场则直接消散，避免屏幕外乱入）
        if self.split_spec is not None:
            self.split_spec["timer"] -= 1
            if self.split_spec["timer"] <= 0:
                if (0 <= self.x <= cfg.BATTLE_AREA_WIDTH and
                        0 <= self.y <= cfg.BATTLE_AREA_HEIGHT):
                    self._do_split()
                self.alive = False
                return

        # 公转弹：绕中心旋转并外扩，半径超限后沿切线飞出
        # Continuous emitter: a stationary burst core releases bullets over time.
        if self.emit_spec is not None:
            self._update_emitter()
            return

        if self.orbit_center is not None:
            self.orbit_radius += self.orbit_grow
            self.orbit_angle += self.orbit_speed
            cx, cy = self.orbit_center
            if self.orbit_break is not None and self.orbit_radius >= self.orbit_break:
                self.orbit_center = None
                tangent = self.orbit_angle + math.pi / 2
                self.vx = math.cos(tangent) * self.orbit_break_speed
                self.vy = math.sin(tangent) * self.orbit_break_speed
                self.angle = tangent
            else:
                self.x = cx + math.cos(self.orbit_angle) * self.orbit_radius
                self.y = cy + math.sin(self.orbit_angle) * self.orbit_radius
                self.angle = self.orbit_angle + math.pi / 2
                return

        # 加速
        self.vx += self.ax * dt
        self.vy += self.ay * dt

        # 沿当前方向持续加速（追魂大玉逐渐加速）
        if self.accel > 0:
            speed = math.hypot(self.vx, self.vy)
            if speed > 0.001:
                self.vx += self.vx / speed * self.accel
                self.vy += self.vy / speed * self.accel

        # 朝玩家有限角速度转向（追魂）
        if self.steer_speed > 0 and self.manager is not None:
            target_angle = math.atan2(self.manager.player_y - self.y,
                                      self.manager.player_x - self.x)
            current_angle = math.atan2(self.vy, self.vx)
            diff = (target_angle - current_angle + math.pi) % (math.pi * 2) - math.pi
            max_turn = self.steer_speed
            if abs(diff) <= max_turn:
                new_angle = current_angle + diff
            else:
                new_angle = current_angle + math.copysign(max_turn, diff)
            speed = math.hypot(self.vx, self.vy)
            self.vx = math.cos(new_angle) * speed
            self.vy = math.sin(new_angle) * speed
            self.angle = new_angle

        # 恒定角速度转向（螺旋弹）
        if self.turn_rate != 0:
            c = math.cos(self.turn_rate)
            s = math.sin(self.turn_rate)
            vx = self.vx * c - self.vy * s
            vy = self.vx * s + self.vy * c
            self.vx, self.vy = vx, vy
            self.angle = math.atan2(vy, vx)

        # 匀减速（织网结点等）：减速到下限速度后保持巡航（下限 0 = 减速到停止）
        # 支持 brake_delay：先按初始速度飞行一段距离，再开始匀减速
        if self.brake_delay > 0:
            self.brake_delay -= 1
        elif self.brake > 0:
            speed = math.hypot(self.vx, self.vy)
            if speed > 0.0001:
                new_speed = max(self.brake_floor, speed - self.brake)
                if new_speed > speed:
                    new_speed = speed   # 下限高于当前速度时保持当前速度，不加速
                scale = new_speed / speed
                self.vx *= scale
                self.vy *= scale

        self.x += self.vx
        self.y += self.vy

        # 蛇形摆动（丝线/飘魂）：沿移动方向垂直侧按正弦偏移（增量式，避免累积漂移）
        if self.wobble_amp > 0:
            speed = math.hypot(self.vx, self.vy)
            if speed > 0.001:
                px = -self.vy / speed
                py = self.vx / speed
                target = math.sin(self.age * self.wobble_freq + self.wobble_phase) * self.wobble_amp
                delta = target - self.wobble_offset
                self.x += px * delta
                self.y += py * delta
                self.wobble_offset = target

        # 出界检查
        margin = 60
        if (not self.ignore_offscreen and
                (self.x < -margin or self.x > cfg.BATTLE_AREA_WIDTH + margin or
                 self.y < -margin or self.y > cfg.BATTLE_AREA_HEIGHT + margin)):
            self.alive = False

    def _update_emitter(self):
        """Stationary emitter used by stream bursts (e.g. Balloon Barrage).

        In downward mode the emission axis sweeps only around straight down,
        so every kunai starts in the lower half and never returns upward.
        """
        spec = self.emit_spec
        if self.manager is None:
            self.alive = False
            return

        duration = max(1, int(spec.get("duration", 60)))
        if self.emit_timer >= duration:
            self.alive = False
            return

        interval = max(1, int(spec.get("interval", 3)))
        if self.emit_timer % interval == 0:
            if spec.get("downward"):
                sweep = float(spec.get("sweep_amp", 0.58))
                sweep_speed = float(spec.get("sweep_speed", 0.055))
                base_angle = math.pi / 2 + math.sin(self.emit_timer * sweep_speed) * sweep
                arm_count = 1
            else:
                shots_fired = self.emit_timer // interval
                base_angle = (float(spec.get("base_angle", 0.0))
                              + shots_fired * float(spec.get("angle_step", 0.0)))
                arm_count = max(1, int(spec.get("count", 2)))

            group_count = max(1, int(spec.get("group_count", 3)))
            group_spread = float(spec.get("group_spread", 0.45))
            speed = float(spec.get("speed", 1.20))
            bullet_type = spec.get("type", Bullet.TYPE_KNIFE)
            radius = float(spec.get("radius", 2.3))
            color = spec.get("color", cfg.COLOR_RED)
            child_accel = float(spec.get("child_accel", 0.024))
            child_lifetime = int(spec.get("child_lifetime", 200))
            wobble_amp = float(spec.get("child_wobble_amp", 0.0))
            wobble_freq = float(spec.get("child_wobble_freq", 0.0))

            for arm in range(arm_count):
                arm_base = base_angle + arm * math.tau / arm_count
                for j in range(group_count):
                    if group_count == 1:
                        a = arm_base
                    else:
                        a = arm_base + (j - (group_count - 1) / 2) * group_spread
                    child = create_bullet_angle(self.x, self.y, a, speed,
                                                bullet_type, radius=radius,
                                                color=color)
                    child.manager = self.manager
                    child.accel = child_accel
                    child.wobble_amp = wobble_amp
                    child.wobble_freq = wobble_freq
                    child.lifetime = child_lifetime
                    self.manager.add_enemy_bullet(child)

        self.emit_timer += 1

    def _do_split(self):
        """分裂弹：在当前位置爆出扇形子弹（默认自机狙），本体随即消失"""
        spec = self.split_spec
        if spec is None or self.manager is None:
            return

        if spec.get("stream"):
            duration = max(1, int(spec.get("duration", 60)))
            emitter = Bullet(
                self.x, self.y, 0.0, 0.0,
                Bullet.TYPE_CIRCLE,
                radius=float(spec.get("core_radius", 6.0)),
                color=spec.get("core_color", cfg.COLOR_WHITE),
                lifetime=duration + 5,
            )
            emitter.manager = self.manager
            emitter.harmless = True
            emitter.emit_spec = {
                "duration": duration,
                "interval": spec.get("interval", 3),
                "count": spec.get("count", 4),
                "angle_step": spec.get("angle_step", 0.22),
                "downward": spec.get("downward", False),
                "sweep_amp": spec.get("sweep_amp", 0.58),
                "sweep_speed": spec.get("sweep_speed", 0.055),
                "group_count": spec.get("group_count", 3),
                "group_spread": spec.get("group_spread", 0.45),
                "base_angle": spec.get("base_angle", 0.0),
                "speed": spec.get("speed", 1.75),
                "type": spec.get("type", Bullet.TYPE_KNIFE),
                "radius": spec.get("radius", 2.3),
                "color": spec.get("color", cfg.COLOR_RED),
                "child_accel": spec.get("child_accel", 0.022),
                "child_wobble_amp": spec.get("child_wobble_amp", 0.0),
                "child_wobble_freq": spec.get("child_wobble_freq", 0.0),
                "child_lifetime": spec.get("child_lifetime", 600),
            }
            self.manager.add_enemy_bullet(emitter)
            return
        if spec.get("aimed", False):
            base = math.atan2(self.manager.player_y - self.y,
                              self.manager.player_x - self.x)
        else:
            base = spec.get("base_angle", math.atan2(self.vy, self.vx))
        count = spec.get("count", 5)
        spread = spec.get("spread", 0.35)
        speed = spec.get("speed", 2.4)
        bullet_type = spec.get("type", Bullet.TYPE_RICE)
        radius = spec.get("radius", 2.5)
        color = spec.get("color", cfg.COLOR_WHITE)
        if spec.get("ring", False):
            # 整圈碎裂：均匀散向四周（岩石碎裂成碎石）
            for i in range(count):
                angle = base + i * math.tau / count
                child = create_bullet_angle(self.x, self.y, angle, speed,
                                            bullet_type, radius=radius, color=color)
                child.manager = self.manager
                self.manager.add_enemy_bullet(child)
            return
        for i in range(count):
            angle = base + (i - (count - 1) / 2) * spread
            child = create_bullet_angle(self.x, self.y, angle, speed,
                                        bullet_type, radius=radius, color=color)
            child.manager = self.manager
            self.manager.add_enemy_bullet(child)

    def draw(self, screen, offset_x=0, offset_y=0):
        # 玩家子弹：优先使用贴图
        if self.is_player_bullet:
            self._draw_player_sprite(screen, offset_x, offset_y)
            return

        px = int(self.x + offset_x)
        py = int(self.y + offset_y)

        # 消弹动画：变白自爆
        if self.cancel_timer > 0:
            self._draw_cancelled(screen, px, py)
            return

        # 敌弹贴图：从图集裁剪（未配置/过大/加载失败时回退图元绘制）
        # Custom external sprite (Spirit Bear giant arrow) takes priority over atlas rendering.
        if self.custom_sprite_path:
            target_height = self.custom_sprite_height or max(1, int(self.visual_radius * 2))
            base = _get_custom_bullet_sprite(self.custom_sprite_path, target_height)
            if base is not None:
                rot_deg = -90.0 - math.degrees(self.angle + self.custom_sprite_angle)
                key = ("custom", self.custom_sprite_path, target_height, int(round(rot_deg)) % 360)
                if key not in self._sprite_cache:
                    self._sprite_cache[key] = pygame.transform.rotate(base, rot_deg)
                sprite = self._sprite_cache[key]
                if self.glow_color is not None and self.glow_padding > 0:
                    glow_key = ("glow", self.custom_sprite_path, target_height,
                                int(round(rot_deg)) % 360,
                                self.glow_color, self.glow_padding)
                    if glow_key not in self._sprite_cache:
                        self._sprite_cache[glow_key] = _build_sprite_glow(
                            sprite, self.glow_color, self.glow_padding)
                    glow = self._sprite_cache[glow_key]
                    if glow is not None:
                        screen.blit(glow, (px - glow.get_width() // 2,
                                           py - glow.get_height() // 2))
                screen.blit(sprite, (px - sprite.get_width() // 2, py - sprite.get_height() // 2))
                return

        sprite = self._get_atlas_sprite()
        if sprite is not None:
            screen.blit(sprite, (px - sprite.get_width() // 2, py - sprite.get_height() // 2))
            return

        if self.bullet_type == Bullet.TYPE_CIRCLE:
            self._draw_circle(screen, px, py)
        elif self.bullet_type == Bullet.TYPE_RICE:
            self._draw_rice(screen, px, py)
        elif self.bullet_type == Bullet.TYPE_ARROW:
            self._draw_arrow(screen, px, py)
        elif self.bullet_type == Bullet.TYPE_BIG:
            self._draw_big(screen, px, py)
        elif self.bullet_type == Bullet.TYPE_KNIFE:
            self._draw_knife(screen, px, py)
        elif self.bullet_type == Bullet.TYPE_BEAM:
            self._draw_beam(screen, px, py)
        else:
            self._draw_circle(screen, px, py)

    def _draw_player_sprite(self, screen, offset_x=0, offset_y=0):
        """玩家子弹贴图（失败时回退原来的米弹）"""
        sprite = _get_player_bullet_sprite()
        px = int(self.x + offset_x)
        py = int(self.y + offset_y)
        if sprite is None:
            self._draw_rice(screen, px, py)
            return
        screen.blit(sprite, (px - sprite.get_width() // 2, py - sprite.get_height() // 2))

    def _draw_circle(self, screen, px, py):
        """圆形弹（敌弹：白芯+彩边）"""
        r = int(self.radius)
        if self.is_player_bullet:
            pygame.draw.circle(screen, self.color, (px, py), r, 0)
            if r >= 3:
                bright = tuple(min(255, c + 100) for c in self.color)
                pygame.draw.circle(screen, bright, (px, py), max(1, r - 2), 0)
            return
        pygame.draw.circle(screen, cfg.COLOR_WHITE, (px, py), r, 0)
        pygame.draw.circle(screen, self.color, (px, py), r, 2)

    def _draw_rice(self, screen, px, py):
        """米弹（椭圆+旋转）"""
        a = self.angle
        l = self.radius * 2.5
        w = self.radius * 0.8
        # 两端
        x1 = px + math.cos(a) * l
        y1 = py + math.sin(a) * l
        x2 = px - math.cos(a) * l
        y2 = py - math.sin(a) * l
        points = [
            (x1, y1),
            (x2 + math.cos(a + math.pi/2) * w, y2 + math.sin(a + math.pi/2) * w),
            (x2, y2),
            (x2 + math.cos(a - math.pi/2) * w, y2 + math.sin(a - math.pi/2) * w),
        ]
        if self.is_player_bullet:
            pygame.draw.polygon(screen, self.color, points, 0)
        else:
            pygame.draw.polygon(screen, cfg.COLOR_WHITE, points, 0)
            pygame.draw.polygon(screen, self.color, points, 1)

    def _draw_arrow(self, screen, px, py):
        """箭弹（三角形）"""
        a = self.angle
        size = self.radius * 2
        tip_x = px + math.cos(a) * size
        tip_y = py + math.sin(a) * size
        left_x = px + math.cos(a + math.pi * 0.75) * size
        left_y = py + math.sin(a + math.pi * 0.75) * size
        right_x = px + math.cos(a - math.pi * 0.75) * size
        right_y = py + math.sin(a - math.pi * 0.75) * size
        if self.is_player_bullet:
            pygame.draw.polygon(screen, self.color, [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)], 0)
        else:
            pygame.draw.polygon(screen, cfg.COLOR_WHITE, [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)], 0)
            pygame.draw.polygon(screen, self.color, [(tip_x, tip_y), (left_x, left_y), (right_x, right_y)], 1)

    def _draw_big(self, screen, px, py):
        """大玉（白芯+彩边）"""
        r = int(self.radius)
        if self.is_player_bullet:
            pygame.draw.circle(screen, self.color, (px, py), r, 2)
            inner = tuple(min(255, c + 60) for c in self.color)
            pygame.draw.circle(screen, inner, (px, py), max(1, r - 3), 0)
            return
        pygame.draw.circle(screen, cfg.COLOR_WHITE, (px, py), r, 0)
        pygame.draw.circle(screen, self.color, (px, py), r, 3)
        pygame.draw.circle(screen, self.color, (px, py), max(1, r - 5), 1)

    def _draw_knife(self, screen, px, py):
        """刀弹（旋转细菱形）"""
        a = self.angle
        length = self.radius * 3
        width = self.radius * 0.6
        tip = (px + math.cos(a) * length, py + math.sin(a) * length)
        base1 = (px + math.cos(a + math.pi/2) * width, py + math.sin(a + math.pi/2) * width)
        base2 = (px + math.cos(a - math.pi/2) * width, py + math.sin(a - math.pi/2) * width)
        if self.is_player_bullet:
            pygame.draw.polygon(screen, self.color, [tip, base1, base2], 0)
        else:
            pygame.draw.polygon(screen, cfg.COLOR_WHITE, [tip, base1, base2], 0)
            pygame.draw.polygon(screen, self.color, [tip, base1, base2], 1)

    def _draw_beam(self, screen, px, py):
        """光束线：从当前位置沿角度延伸 beam_length 的直线（电网电流连接）"""
        a = self.angle
        length = self.beam_length
        ex = px + math.cos(a) * length
        ey = py + math.sin(a) * length
        if self.sprite_slot and length >= 2:
            sprite = self._get_beam_pattern()
            if sprite is not None:
                midx = px + math.cos(a) * length * 0.5
                midy = py + math.sin(a) * length * 0.5
                screen.blit(sprite, (midx - sprite.get_width() * 0.5,
                                     midy - sprite.get_height() * 0.5))
                return
        pygame.draw.line(screen, cfg.COLOR_WHITE, (px, py), (int(ex), int(ey)), 3)
        pygame.draw.line(screen, self.color, (px, py), (int(ex), int(ey)), 1)

    def _get_beam_pattern(self):
        """取 etama.png 第一行「射线」图案：白芯沿光束长度、有色在光束两侧。

        图案本身是「左右有色 + 中间白芯」的横条：白芯带沿图案纵向铺满。
        因此按纵向拉伸成光束长度（白芯变中线、两侧成色边），再旋转到光束方向。
        光束静止不动，同一颗弹的结果按 (length, angle) 缓存，避免每帧重复缩放旋转。
        """
        rot_deg = 90.0 - math.degrees(self.angle)
        key = ("beam", int(round(self.beam_length)), int(round(rot_deg)) % 360)
        cached = self._sprite_cache.get(key)
        if cached is not None:
            return cached
        native = bullet_atlas.get_native_size(self.sprite_slot)
        if native is None:
            return None
        # Preserve the original etama gradient: no tint for beam patterns.
        src = bullet_atlas.get_sprite(self.sprite_slot, native[0])
        if src is None:
            return None
        # 裁掉图案上下各 1px 透明边，避免沿光束方向拉伸后两端出现渐变淡出
        try:
            src = src.subsurface((0, 1, src.get_width(), src.get_height() - 2)).copy()
        except Exception:
            pass
        width = max(1, native[0])          # 光束厚度：图案原始宽度（含两侧色边）
        length = max(1, int(round(self.beam_length)))
        stretched = pygame.transform.smoothscale(src, (width, length))
        rotated = pygame.transform.rotate(stretched, rot_deg)
        self._sprite_cache[key] = rotated
        return rotated

    def _draw_cancelled(self, screen, px, py):
        """消弹动画：迅速变白并膨胀自爆"""
        progress = 1.0 - self.cancel_timer / BULLET_CANCEL_DURATION
        r = max(1, int(self.visual_radius * (1.0 + progress * 1.6)))
        pygame.draw.circle(screen, cfg.COLOR_WHITE, (px, py), r, 0)
        if progress > 0.55:
            ring_r = max(1, int(r * 1.35))
            pygame.draw.circle(screen, cfg.COLOR_WHITE, (px, py), ring_r, 1)

    def _get_atlas_sprite(self):
        """按弹种和颜色从图集取颜色最接近的原图贴图；无匹配时返回 None。"""
        if self.is_player_bullet:
            return None
        if self.bullet_type == Bullet.TYPE_BEAM:
            return None   # 光束线长度不定，改由 _draw_beam 做图案拉伸渲染
        slot = self.sprite_slot or cfg.ENEMY_BULLET_SPRITE_MAP.get(self.bullet_type)
        if not slot:
            return None
        if self.radius > cfg.ENEMY_BULLET_SPRITE_MAX_RADIUS:
            return None
        slot = bullet_atlas.pick_color_slot(slot, self.color)
        native = bullet_atlas.get_native_size(slot)
        if native is None:
            return None
        width = native[0]
        angle = None
        if self.bullet_type in (Bullet.TYPE_RICE, Bullet.TYPE_ARROW, Bullet.TYPE_KNIFE):
            # 贴图默认朝上（-90°），转到移动方向；pygame.rotate 逆时针为正
            angle = -90.0 - math.degrees(self.angle)
        key = (slot, width, angle)
        if key not in self._sprite_cache:
            self._sprite_cache[key] = bullet_atlas.get_sprite(slot, width, angle)
        return self._sprite_cache[key]

    def start_cancel(self):
        """进入消弹状态：变白自爆动画期间冻结且不参与碰撞"""
        if self.cancel_timer <= 0:
            self.cancel_timer = BULLET_CANCEL_DURATION

    def get_hitbox(self):
        return (self.x, self.y, self.collision_radius)

    def hits_player(self, px, py, pr):
        """玩家碰撞判定：光束按整条线段判定，其余弹按圆形判定"""
        if self.bullet_type == Bullet.TYPE_BEAM:
            ex = self.x + math.cos(self.angle) * self.beam_length
            ey = self.y + math.sin(self.angle) * self.beam_length
            return point_segment_distance(px, py, self.x, self.y, ex, ey) <= pr + self.collision_radius
        return circle_collision(self.x, self.y, self.collision_radius, px, py, pr)


def create_bullet_aimed(x, y, target_x, target_y, speed, bullet_type=Bullet.TYPE_CIRCLE,
                        radius=3.0, color=None, damage=10, lifetime=600):
    """创建瞄准玩家的子弹"""
    dx = target_x - x
    dy = target_y - y
    dist = math.sqrt(dx * dx + dy * dy)
    if dist < 0.001:
        vx, vy = 0, speed
    else:
        vx = dx / dist * speed
        vy = dy / dist * speed
    return Bullet(x, y, vx, vy, bullet_type, radius, color or cfg.COLOR_RED, damage, False, lifetime)


def create_bullet_angle(x, y, angle, speed, bullet_type=Bullet.TYPE_CIRCLE,
                        radius=3.0, color=None, damage=10, lifetime=600):
    """按角度创建子弹"""
    vx = math.cos(angle) * speed
    vy = math.sin(angle) * speed
    return Bullet(x, y, vx, vy, bullet_type, radius, color or cfg.COLOR_RED, damage, False, lifetime)


def create_player_bullet(x, y, vx=0, vy=None, homing=False):
    """创建玩家子弹"""
    if vy is None:
        vy = -cfg.BULLET_PLAYER_SPEED
    return Bullet(x, y, vx, vy, Bullet.TYPE_RICE, radius=2.0,
                  color=cfg.COLOR_BLUE, damage=cfg.BULLET_PLAYER_DAMAGE,
                  is_player_bullet=True, lifetime=60, homing=homing)


class BulletManager:
    """子弹管理器"""
    def __init__(self):
        self.player_bullets = []
        self.enemy_pause_frames = 0
        self.enemy_bullet_density = 1.0
        self._enemy_bullet_counter = 0
        self.enemy_bullets = []
        self.cancel_bullets = False  # 消弹标志
        self.player_x = 0.0          # 玩家位置（特殊弹幕转向/分裂瞄准用）
        self.player_y = 0.0

    def add_player_bullet(self, bullet):
        self.player_bullets.append(bullet)

    def add_enemy_bullet(self, bullet):
        self._enemy_bullet_counter += 1
        if self.enemy_bullet_density < 1.0 and not getattr(bullet, "harmless", False):
            keep_every = max(1, int(round(1.0 / self.enemy_bullet_density)))
            if self._enemy_bullet_counter % keep_every != 0:
                return
        self.enemy_bullets.append(bullet)
    def update(self, dt, player_x=None, player_y=None):
        # 记录玩家位置（供敌弹追踪/分裂瞄准）
        if player_x is not None:
            self.player_x = player_x
        if player_y is not None:
            self.player_y = player_y

        # 消弹处理：场上敌弹进入变白自爆动画（非瞬间消失）
        if self.cancel_bullets:
            for b in self.enemy_bullets:
                b.start_cancel()
            self.cancel_bullets = False

        # 更新玩家弹
        for b in self.player_bullets[:]:
            b.update(dt)
            if not b.alive:
                self.player_bullets.remove(b)

        # 更新敌弹（消弹中的子弹冻结在原地播放动画）
        if self.enemy_pause_frames > 0:
            self.enemy_pause_frames -= 1
        else:
            for b in self.enemy_bullets[:]:
                b.update(dt)

        # 去掉出界 / 自爆完成的敌弹
        self.enemy_bullets = [b for b in self.enemy_bullets if b.alive]

    def draw(self, screen, offset_x=0, offset_y=0):
        for b in self.enemy_bullets:
            b.draw(screen, offset_x, offset_y)
        for b in self.player_bullets:
            b.draw(screen, offset_x, offset_y)

    def clear_all(self):
        self.player_bullets.clear()
        self.enemy_bullets.clear()
        self.cancel_bullets = False
        self.enemy_pause_frames = 0
        self._enemy_bullet_counter = 0

    def cancel_all_enemy_bullets(self):
        """清屏消弹：场上敌弹变白自爆"""
        self.cancel_bullets = True
