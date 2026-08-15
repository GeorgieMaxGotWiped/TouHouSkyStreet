# Boss 系统
# 符卡战斗、阶段切换、Boss弹幕模式

import math
import random
import os
import pygame
from src.engine import settings as cfg
from src.engine.collision import circle_collision
from src.engine.fallback_font import FallbackFont
from src.engine.spell_bg import SpellBackground
from src.entities.bullet import Bullet, create_bullet_aimed, create_bullet_angle

# 模块级字体缓存
_boss_fonts = {}

def _get_font(size):
    key = size
    if key not in _boss_fonts:
        font_path = os.path.join(cfg.ASSETS_DIR, "fonts", "font1.ttf")
        fallback_path = os.path.join(cfg.ASSETS_DIR, "fonts", "font2.otf")
        _boss_fonts[key] = FallbackFont(font_path, fallback_path, size)
    return _boss_fonts[key]


# 血条与名字行布局（相对战斗区左上角）
HP_BAR_TOP = 10             # 血条顶部
HP_BAR_HEIGHT = 8           # 血条高度
BOSS_NAME_Y = HP_BAR_TOP + HP_BAR_HEIGHT + 4   # Boss 名 / 符卡名共用行


def _english_only(text):
    """Boss 显示名：只保留 ASCII 英文部分（删除中文），避免名字过长超出战斗区域"""
    return "".join(ch for ch in (text or "") if ord(ch) < 128).strip()


# Boss 贴图缓存：key = (贴图路径, 目标高度)
_boss_sprite_cache = {}
_boss_sprite_attempted = set()


def _get_boss_sprite(path, target_height):
    """加载并缓存 Boss 贴图（按目标高度等比缩放）；失败返回 None（回退几何绘制）"""
    key = (path, target_height)
    if key in _boss_sprite_attempted:
        return _boss_sprite_cache.get(key)
    _boss_sprite_attempted.add(key)
    try:
        img = pygame.image.load(path)
        try:
            img = img.convert_alpha()
        except Exception:
            pass
        w, h = img.get_size()
        if h <= 0:
            raise ValueError("invalid sprite height")
        new_w = max(1, round(w * target_height / h))
        _boss_sprite_cache[key] = pygame.transform.smoothscale(img, (new_w, target_height))
    except Exception as e:
        print(f"[Boss] Failed to load boss sprite {path}: {e}")
    return _boss_sprite_cache.get(key)


# 符卡横幅立绘目标高度缓存：key = 贴图路径
_banner_height_cache = {}
_banner_height_attempted = set()


def _banner_target_height(path):
    """符卡宣言立绘目标高度：默认达 SPELL_BANNER_SPRITE_HEIGHT，
    但再受『不超过战斗区宽度』约束（防止方形图超边溢出）"""
    key = path
    if key in _banner_height_attempted:
        return _banner_height_cache.get(key)
    _banner_height_attempted.add(key)
    try:
        img = pygame.image.load(path)
        w, h = img.get_size()
        if h <= 0:
            raise ValueError("invalid sprite height")
        max_w = cfg.BATTLE_AREA_WIDTH
        _banner_height_cache[key] = int(min(SPELL_BANNER_SPRITE_HEIGHT, max_w * h / w))
    except Exception:
        _banner_height_cache[key] = SPELL_BANNER_SPRITE_HEIGHT
    return _banner_height_cache[key]

# Boss 贴图 Mask 缓存：key = (贴图路径, 目标高度)
_boss_mask_cache = {}
_bullet_mask_cache = {}


def _get_boss_mask(path, target_height):
    """获取 Boss 贴图的碰撞 Mask（透明区域不参与判定）"""
    key = (path, target_height)
    if key not in _boss_mask_cache:
        sprite = _get_boss_sprite(path, target_height)
        try:
            _boss_mask_cache[key] = pygame.mask.from_surface(sprite) if sprite is not None else None
        except Exception:
            _boss_mask_cache[key] = None
    return _boss_mask_cache[key]


def _get_bullet_mask(radius):
    """按子弹碰撞半径生成圆形 Mask（用于贴图形状判定）"""
    r = max(1, int(round(radius)))
    if r not in _bullet_mask_cache:
        size = r * 2 + 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255, 255, 255, 255), (size // 2, size // 2), r)
        _bullet_mask_cache[r] = pygame.mask.from_surface(surf)
    return _bullet_mask_cache[r]


_sadan_sword_sprite_cache = {}


def _get_sadan_sword_sprite(path, target_height):
    """Loads the diamond sword asset and rotates it to fall vertically.

    The source icon is a square with a diagonal sword, so it is scaled to
    target_height / sqrt(2) and then rotated +45 degrees. The returned surface
    has the sword blade running straight down.
    """
    key = (path, target_height)
    if key in _sadan_sword_sprite_cache:
        return _sadan_sword_sprite_cache[key]
    sprite = None
    try:
        side = max(1, int(round(target_height / math.sqrt(2))))
        source = _get_boss_sprite(path, side)
        if source is not None:
            sprite = pygame.transform.rotate(source, 45)
    except Exception as e:
        print(f"[Boss] Failed to load Sadan sword sprite {path}: {e}")
    _sadan_sword_sprite_cache[key] = sprite
    return sprite


def _with_alpha(surf, alpha):
    """返回带整体透明度 alpha(0-255) 的表面副本（不修改原表面）"""
    if alpha >= 255:
        return surf
    result = surf.copy()
    result.fill((255, 255, 255, alpha), special_flags=pygame.BLEND_RGBA_MULT)
    return result


# 亡灵展品柔光层缓存：key = (半径, 颜色)
_watcher_glow_cache = {}


def _get_watcher_glow(radius, color):
    """生成亡灵展品的圆形柔光层：中心亮、边缘淡的幽蓝光晕（SRCALPHA 叠加）"""
    key = (radius, color)
    if key in _watcher_glow_cache:
        return _watcher_glow_cache[key]
    size = radius * 2 + 2
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx = cy = size // 2
    steps = max(4, radius)
    for i in range(steps):
        rr = max(1, int(radius * (1.0 - i / steps)))
        alpha = int(8 + 60 * (i / steps))   # 边缘淡、中心亮（同心圆叠加）
        pygame.draw.circle(surf, (*color, alpha), (cx, cy), rr)
    _watcher_glow_cache[key] = surf
    return surf


# 幻影龙柔光层缓存：key = (目标高度, 光晕半径, 颜色)
_phantom_dragon_glow_cache = {}


def _get_phantom_dragon_glow(glow_radius=10, color=(232, 200, 255)):
    """生成幻影龙贴图的柔和光晕层（沿剪影向外扩散的淡紫柔光，轻微发光）"""
    key = (PHANTOM_DRAGON_HEIGHT, glow_radius, color)
    if key in _phantom_dragon_glow_cache:
        return _phantom_dragon_glow_cache[key]
    sprite = _get_boss_sprite(cfg.END_DRAGON_PET_SPRITE, PHANTOM_DRAGON_HEIGHT)
    if sprite is None:
        _phantom_dragon_glow_cache[key] = None
        return None
    sw, sh = sprite.get_size()
    pad = glow_radius
    out = pygame.Surface((sw + pad * 2, sh + pad * 2), pygame.SRCALPHA)
    mask = pygame.mask.from_surface(sprite, threshold=32)
    silhouette = mask.to_surface(setcolor=(*color, 255), unsetcolor=(0, 0, 0, 0))
    for dy in range(-glow_radius, glow_radius + 1):
        for dx in range(-glow_radius, glow_radius + 1):
            dist = math.hypot(dx, dy)
            if dist <= glow_radius:
                t = dist / glow_radius
                silhouette.set_alpha(int(64 * (1 - t)))
                out.blit(silhouette, (pad + dx, pad + dy))
    _phantom_dragon_glow_cache[key] = out
    return out


# 符卡宣言横幅参数
SPELL_BANNER_DURATION = 100       # 总时长（帧）
SPELL_BANNER_FADE_IN = 12         # 淡入帧数
SPELL_BANNER_FADE_OUT = 40        # 淡出帧数
SPELL_BANNER_SPRITE_HEIGHT = 648  # 立绘展示高度（px）
PHANTOM_DRAGON_HEIGHT = 52        # 龙符幻影龙贴图展示高度（px）
SPELL_BANNER_DROP = 36            # 淡出时向下平移距离（px）


class SpellCard:
    """符卡（一个攻击阶段）"""
    def __init__(self, name, pattern_func, hp_threshold=None, end_hp_threshold=None,
                 bg_style=None, direct_next=False, time_spell=False):
        self.name = name
        self.pattern_func = pattern_func
        self.hp_threshold = hp_threshold
        self.end_hp_threshold = end_hp_threshold   # 独立结束阈值（None 时用下一张符的 hp_threshold）
        self.bg_style = bg_style   # 符卡背景风格（None 时按名字自动判断）
        self.direct_next = direct_next   # True 时结束后不进入非符，直接开下一张符卡
        self.time_spell = time_spell     # 时符：无 Boss 血量，攻击不会提前结束符卡
        self.timer = 0
        self.active = False
        self.completed = False

    def start(self):
        self.active = True
        self.timer = 0
        self.completed = False

    def update(self, boss, bullet_manager, dt, player_x=0, player_y=0):
        # 符卡无时间限制：只有血量压到阈值/清空才会结束
        if not self.active:
            return
        self.timer += 1
        self.pattern_func(boss, bullet_manager, self.timer, dt, player_x, player_y)

    def reset(self):
        self.active = False
        self.timer = 0
        self.completed = False


class Boss:
    """Boss类"""
    def __init__(self, name, hp, x=None, y=None, size=20, color=None, score=10000,
                 spell_by_hp_only=False, spell_resistance=1.0, non_spell_min_duration=0,
                 non_spell_level=0, sprite_path=None, sprite_height=None, sprite_scale=1.0,
                 non_spell_func=None, non_spell_funcs=None, hp_bar_inset=30,
                 bullet_size_scale=1.0, bullet_density=1.0):
        self.name = name
        self.bullet_size_scale = bullet_size_scale
        self.bullet_density = bullet_density
        Bullet.size_scale_global = bullet_size_scale   # 末影龙放大敌弹，其他 Boss 默认 1.0
        self.x = x or cfg.BATTLE_AREA_WIDTH / 2
        self.y = y or 100
        self.hp = hp
        self.max_hp = hp
        self.size = size
        # 贴图：配置后优先用贴图替换几何绘制，目标高度默认与八角形直径一致
        self.sprite_path = sprite_path
        self.sprite_height = sprite_height or int(size * 2 * sprite_scale)
        self.color = color or cfg.COLOR_RED
        self.alive = True
        self.score = score

        # 符卡阶段：只能通过血量触发 / 受伤抵抗
        self.spell_by_hp_only = spell_by_hp_only
        self.spell_resistance = spell_resistance
        self.resistance = 1.0

        # 移动
        self.target_x = self.x
        self.target_y = self.y
        self.move_speed = 2.0

        # 符卡
        self.spell_cards = []
        self.current_spell_idx = 0
        self.current_spell = None
        self.non_spell_active = True
        self.non_spell_timer = 0
        self.non_spell_duration = 300
        self.non_spell_min_duration = non_spell_min_duration   # 非符最短持续时间（帧）
        self.non_spell_level = non_spell_level   # 非符强度：0=基础，1=道中Boss级，2=Boss级
        self.non_spell_func = non_spell_func   # 自定义非符攻击（None 时使用内置等级模板）
        self.non_spell_funcs = non_spell_funcs or {}   # 分阶段非符：{下一张符卡索引: 攻击函数}
        self.hp_bar_inset = hp_bar_inset           # 血条左右边距（px）
        self._bullet_manager = None   # 最近一次 update 传入的子弹管理器（符卡切换清屏用）
        # Last Spell（彩蛋挑战）：Bomb 禁用，Miss 强制结束不损残机
        self.last_spell = None
        self.last_spell_active = False
        self.last_spell_hp = 3600        # 超符「Superiority」展开时补充的黄金领域血量
        self.revive_after_spell_idx = None  # 指定符卡被击破后进入复活演出（None=不复活）
        self.revive_hp = None              # 复活后回满的血量（None=使用 max_hp）
        self.revive_max_hp = None           # 复活后重新计算阈值使用的 max_hp（None=沿用原 max_hp）
        self.revive_duration = 180         # 复活演出持续帧数（60FPS 下约 3 秒）
        self.revive_timer = 0
        self.revive_skips_non_spell = False  # ????????????????????
        self.superior_circles = []       # 超符黄金魔法阵（位置/旋转/生命由符卡每帧更新）
        self.protector_barriers = []     # 石符固定石柱结界（位置固定，由符卡维护）
        self.protector_shock = None      # 石符震荡冲击环（绘制用动画状态）
        self.protector_fortress = False  # 石符岩石堡垒轮廓是否绘制
        self.protector_pulse_dir = 1     # 石符震荡方向：+1 扩散 / -1 收缩        # 状态
        self.watcher_exhibits = []     # 展符亡灵展品（位置/贴图/预警由符卡维护，纯视觉无判定）
        self.bonzo_undeads = []        # 死符 Undead Revival 的 Undead（生命周期由符卡维护）
        self.bonzo_dreadlord_skulls = []   # 骸符 Skull Dreadlord 的骷髅头阵列（生命周期由符卡维护）
        self.bonzo_dreadlord_rebuild = 0   # 骸符骷髅全部消散后的重建等待帧数
        self.bonzo_dreadlord_wave = 0       # 骸符骷髅阵列轮次（骨刺隔波交替用）
        self.bonzo_masks = []          # 戏符 Grand Illusion 的小丑面具幻象节点（生命周期由符卡维护）
        self.scarf_squad = []          # 队符「Necrotic Squad」的四名亡灵固定成员（生命周期由符卡维护）
        self.scarf_active_squad = None # 队符当前主攻击职业名（Warrior/Archer/Mage/Priest）
        self.scarf_buff_circle = None  # 兼容旧单法阵引用（保留但不再由符卡写入）
        self.scarf_buff_circles = []   # 队符中牧师生成的多个紫色强化法阵（生命周期由符卡维护）
        self.sadan_army = []           # 兵符「Terracotta Army」的兵马俑军阵（生命周期由符卡维护）
        self.sadan_giant_state = {}    # Giant cycle visual state for "Precursors' Return" spell card.
        self.bridge_worlds_state = None  # 终符「Bridge Between Worlds」的桥与黑暗遮罩状态
        self.frenzy_state = None       # Phase1「Maxor's Frenzy」主状态（None=未展开）
        self.frenzy_tnts = []          # Frenzy TNT 标记（延迟爆炸，纯视觉）
        self.frenzy_crystals = []      # Frenzy power crystal 收集物
        self.frenzy_shockwaves = []    # Frenzy 冲击波视觉环（TNT 爆炸 / 大型冲击波 / 拾取闪光）
        self.frenzy_laser = None       # Frenzy 解封红色激光状态
        self.entering = True
        self.entry_timer = 120
        self.invincible = False
        self.invincible_timer = 0   # 开符免疫倒计时
        self.phase = "entry"

        # 战斗开关：未开启时（对话/登场等待）不攻击、不显示血条、不可受伤
        self.combat_enabled = True
        self.combat_delay = 0       # 开战延迟帧数（对话结束后 0.6s）

        # 符卡宣言横幅（开符时整幅立绘 + 符卡名，向下平移淡出）
        self.spell_banner_active = False
        self.spell_banner_timer = 0
        self.spell_banner_name = ""

        # 符卡特殊背景（开符时生成，结符时淡出）
        self.spell_bg = None

        # 龙符幻影龙：龙形能量体（位置由符卡每帧更新，绘制时贴图渲染）
        self.phantom_dragons = []

        self.start_x = self.x
        self.start_y = self.y

    def add_spell_card(self, spell_card):
        self.spell_cards.append(spell_card)

    def set_last_spell(self, spell_card):
        """注册 Last Spell：三张通常符全部击破后自动展开（彩蛋挑战）"""
        self.last_spell = spell_card

    def is_last_spell_active(self):
        """Last Spell 进行中：Bomb 禁用、Miss 强制结束不损残机"""
        return (self.last_spell is not None and self.last_spell_active
                and self.phase == "spell" and self.current_spell is self.last_spell)

    def _is_time_spell_active(self):
        """时符进行中：没有 Boss 血量，玩家攻击不会使符卡提前结束。"""
        return (self.phase == "spell" and self.current_spell is not None
                and getattr(self.current_spell, "time_spell", False))

    def force_end_last_spell(self):
        """Last Spell 被 Miss 时强制结束：Boss 视为已被击破（不扣残机）"""
        if not self.is_last_spell_active():
            return False
        self._cancel_screen_bullets()
        self._begin_spell_bg_fade()
        self.current_spell = None
        self.last_spell_active = False
        self.resistance = 1.0
        self.phase = "defeated"
        self._clear_spell_effects()
        self.alive = False
        return True
    def move_to(self, x, y):
        self.target_x = x
        self.target_y = y
        self.start_x = self.x
        self.start_y = self.y

    def hold_combat(self):
        """进入待机：Boss在场但不攻击、不显示血条、不可受伤"""
        self.combat_enabled = False
        self.combat_delay = 0

    def arm_combat(self, delay_frames):
        """延迟 delay_frames 帧后开启战斗（0 表示立即开战）"""
        self.combat_enabled = delay_frames <= 0
        self.combat_delay = max(0, delay_frames)

    def _move_toward_target(self, dt):
        """平滑移动到目标点"""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dist = math.sqrt(dx*dx + dy*dy)
        if dist > 0.5:
            self.x += dx * min(1.0, self.move_speed / dist) * dt * 60
            self.y += dy * min(1.0, self.move_speed / dist) * dt * 60

    def update(self, dt, bullet_manager, player_x, player_y):
        # 符卡背景独立推进：Boss 死亡/结符后的淡出也能继续播放
        if self.spell_bg is not None:
            self.spell_bg.update(dt)
            if self.spell_bg.done:
                self.spell_bg = None
        if not self.alive:
            return
        self._bullet_manager = bullet_manager

        # 开战延迟倒计时（对话结束后 0.6s，期间每帧推进）
        if not self.combat_enabled and self.combat_delay > 0:
            self.combat_delay -= 1
            if self.combat_delay <= 0:
                self.combat_enabled = True

        if self.entering:
            self.entry_timer -= 1
            if self.entry_timer <= 0:
                self.entering = False
                self.phase = "non_spell"
                self.non_spell_timer = 0
            self.y += 0.5
            return

        # 尚未开战（对话阶段/登场等待）：只做入场定位移动，不攻击
        if not self.combat_enabled:
            self._move_toward_target(dt)
            return

        # 开符免疫倒计时
        if self.invincible_timer > 0:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False

        # 平滑移动
        self._move_toward_target(dt)

        if self.phase == "non_spell":
            self.non_spell_timer += 1
            self._non_spell_attack(bullet_manager, player_x, player_y)

            if self.current_spell_idx < len(self.spell_cards):
                card = self.spell_cards[self.current_spell_idx]
                hp_trigger = (card.hp_threshold is not None
                              and self.hp / self.max_hp <= card.hp_threshold)
                time_trigger = (not self.spell_by_hp_only
                                and self.non_spell_timer >= self.non_spell_duration)
                min_elapsed = self.non_spell_timer >= self.non_spell_min_duration
                if (hp_trigger or time_trigger) and min_elapsed:
                    self._start_spell()
            elif self.last_spell is not None:
                # 兜底：三张通常符后若意外进入非符，短暂停顿即展开 Last Spell
                if self.non_spell_timer >= max(30, self.non_spell_min_duration):
                    self._start_spell(self.last_spell)

        elif self.phase == "spell":
            if self.current_spell:
                self.current_spell.update(self, bullet_manager, dt, player_x, player_y)

        elif self.phase == "reviving":
            self.revive_timer -= 1
            if self.revive_timer <= 0:
                if self.revive_max_hp is not None:
                    self.max_hp = self.revive_max_hp
                self.hp = self.revive_hp if self.revive_hp is not None else self.max_hp
                self.invincible = False
                self.invincible_timer = 0
                if self.revive_skips_non_spell:
                    self._start_spell()
                else:
                    self.phase = "non_spell"
                    self.non_spell_timer = 0
                    self.non_spell_duration = 240

        elif self.phase == "defeated":
            pass

    def _non_spell_attack(self, bullet_manager, player_x, player_y):
        """非符攻击：按 non_spell_level 决定密度（0=基础，1=道中Boss级，2=Boss级）"""
        timer = self.non_spell_timer
        base_angle = math.atan2(player_y - self.y, player_x - self.x)

        # 分阶段非符：每两张符之间各一种（key = 下一张符卡索引）
        if self.current_spell_idx in self.non_spell_funcs:
            self.non_spell_funcs[self.current_spell_idx](self, bullet_manager, timer,
                                                         player_x, player_y)
            return

        # 自定义非符：覆盖内置等级模板（Boss 专属弹幕）
        if self.non_spell_func is not None:
            self.non_spell_func(self, bullet_manager, timer, player_x, player_y)
            return

        # 基础非符：较弱的单发自机狙
        if self.non_spell_level == 0:
            if timer % 20 == 0:
                b = create_bullet_angle(self.x, self.y, base_angle, 2.5,
                                        Bullet.TYPE_CIRCLE, radius=3, color=cfg.COLOR_RED)
                bullet_manager.add_enemy_bullet(b)
            return

        # 道中Boss级：三发自机狙扇形 + 周期圆环
        if timer % 15 == 0:
            for offset in (-0.16, 0.0, 0.16):
                b = create_bullet_angle(self.x, self.y, base_angle + offset, 2.6,
                                        Bullet.TYPE_CIRCLE, radius=3, color=cfg.COLOR_RED)
                bullet_manager.add_enemy_bullet(b)
        if timer % 50 == 0:
            for i in range(10):
                angle = timer * 0.02 + i * math.pi * 2 / 10
                b = create_bullet_angle(self.x, self.y, angle, 1.7,
                                        Bullet.TYPE_CIRCLE, radius=2.5, color=cfg.COLOR_PURPLE)
                bullet_manager.add_enemy_bullet(b)

        if self.non_spell_level < 2:
            return

        # Boss级：五发扇形 + 圆环 + 侧翼刀弹（末影龙子弹放大后按密度降频减量）
        _d = self.bullet_density
        if timer % int(12 * _d) == 0:
            # 自机狙扇形：Boss 同步沿攻击方向位移，玩家被压向一侧时也能正面击中
            self.target_x = self.x + math.cos(base_angle) * 48
            self.target_y = self.y + math.sin(base_angle) * 48
            self.target_x = max(40, min(cfg.BATTLE_AREA_WIDTH - 40, self.target_x))
            self.target_y = max(60, min(280, self.target_y))
            _n = max(2, (5 + int(_d) - 1) // int(_d))
            for i in range(_n):
                offset = (i - (_n - 1) / 2) * 0.13
                b = create_bullet_angle(self.x, self.y, base_angle + offset, 2.8,
                                        Bullet.TYPE_RICE, radius=2.5, color=cfg.COLOR_RED)
                bullet_manager.add_enemy_bullet(b)
        if timer % int(40 * _d) == 0:
            _n = max(6, (12 + int(_d) - 1) // int(_d))
            for i in range(_n):
                angle = timer * 0.03 + i * math.pi * 2 / _n
                b = create_bullet_angle(self.x, self.y, angle, 1.8,
                                        Bullet.TYPE_CIRCLE, radius=3, color=cfg.COLOR_PURPLE)
                bullet_manager.add_enemy_bullet(b)
        if timer % int(30 * _d) == 0:
            for offset in (-0.4, 0.4):
                b = create_bullet_angle(self.x, self.y, base_angle + offset, 3.0,
                                        Bullet.TYPE_KNIFE, radius=2.5, color=cfg.COLOR_ORANGE)
                bullet_manager.add_enemy_bullet(b)
    def _cancel_screen_bullets(self):
        """符卡开始/结束时清屏：场上敌弹全部进入变白自爆动画"""
        if self._bullet_manager is not None:
            self._bullet_manager.cancel_all_enemy_bullets()

    def _begin_spell_bg_fade(self):
        """让符卡特殊背景淡出（幂等，可重复调用）"""
        if self.spell_bg is not None and not self.spell_bg.fading:
            self.spell_bg.begin_fade_out()

    def _start_spell(self, spell=None):
        self._cancel_screen_bullets()   # 开符：清屏
        self.phantom_dragons = []       # 开符：清空幻影龙
        self.superior_circles = []      # 开符：清空超符魔法阵
        self.protector_barriers = []    # 开符：清空石符石柱结界
        self.protector_shock = None
        self.protector_fortress = False
        self.protector_pulse_dir = 1
        self.watcher_exhibits = []
        self.bonzo_undeads = []
        self.bonzo_dreadlord_skulls = []
        self.bonzo_dreadlord_rebuild = 0
        self.bonzo_dreadlord_wave = 0
        self.bonzo_masks = []
        self.scarf_squad = []
        self.scarf_active_squad = None
        self.scarf_buff_circle = None
        self.scarf_buff_circles = []
        self.sadan_army = []
        self.sadan_giant_state = {}
        self.bridge_worlds_state = None
        self.frenzy_state = None
        self.frenzy_tnts = []
        self.frenzy_crystals = []
        self.frenzy_shockwaves = []
        self.frenzy_laser = None
        self.storm_giga = None
        self.goldor_terminal = None
        self.goldor_rage = None
        if spell is None:
            if self.current_spell_idx >= len(self.spell_cards):
                return
            spell = self.spell_cards[self.current_spell_idx]
        if spell is None:
            return
        self.phase = "spell"
        self.current_spell = spell
        self.current_spell.start()
        self.resistance = self.spell_resistance
        self.move_to(cfg.BATTLE_AREA_WIDTH / 2, 120)
        # 刚开符时给予一段免疫时间
        self.invincible = True
        self.invincible_timer = 60
        # 触发符卡宣言横幅
        self.spell_banner_active = True
        self.spell_banner_timer = 0
        self.spell_banner_name = self.current_spell.name
        # 生成与符卡名印象/背景风格对应的动态特殊背景
        self.spell_bg = SpellBackground(self.current_spell.name,
                                        self.current_spell.bg_style)
        # 标记 Last Spell 状态（Bomb 禁用 / Miss 强制结束）
        self.last_spell_active = (spell is self.last_spell)
        # Last Spell 展开：血量已打空，补充黄金领域独立血量并清空旧阵
        if self.last_spell_active:
            if getattr(spell, "time_spell", False):
                self.hp = 0
            else:
                self.hp = self.last_spell_hp
            self.superior_circles = []
    def _clear_spell_effects(self):
        """Boss 战败时清除符卡视觉残留（黄金魔法阵/幻影龙/石柱等）"""
        self.phantom_dragons = []
        self.superior_circles = []
        self.protector_barriers = []
        self.protector_shock = None
        self.protector_fortress = False
        self.protector_pulse_dir = 1
        self.watcher_exhibits = []
        self.bonzo_undeads = []
        self.bonzo_dreadlord_skulls = []
        self.bonzo_dreadlord_rebuild = 0
        self.bonzo_dreadlord_wave = 0
        self.bonzo_masks = []
        self.scarf_squad = []
        self.scarf_active_squad = None
        self.scarf_buff_circle = None
        self.scarf_buff_circles = []
        self.sadan_army = []
        self.sadan_giant_state = {}
        self.bridge_worlds_state = None
        self.frenzy_state = None
        self.frenzy_tnts = []
        self.frenzy_crystals = []
        self.frenzy_shockwaves = []
        self.frenzy_laser = None
        self.storm_giga = None
        self.goldor_terminal = None
        self.goldor_rage = None

    def _end_spell(self):
        self._cancel_screen_bullets()   # 结符：清屏
        self._begin_spell_bg_fade()     # 结符：特殊背景淡出
        self.bonzo_undeads = []         # 结符：清空死符召唤的 Undead
        self.bonzo_dreadlord_skulls = []   # 结符：清空骸符骷髅头
        self.bonzo_dreadlord_rebuild = 0
        self.bonzo_dreadlord_wave = 0
        self.bonzo_masks = []           # 结符：清空戏符面具幻象
        self.scarf_squad = []           # 结符：清空队符小队
        self.scarf_active_squad = None
        self.scarf_buff_circle = None   # 结符：清空牧师强化法阵
        self.scarf_buff_circles = []    # 结符：清空多个牧师强化法阵
        self.sadan_army = []            # 结符：清空兵马俑军阵
        self.sadan_giant_state = {}   # Clear giant cycle visual state at spell end.
        self.bridge_worlds_state = None  # 结符：清空终符桥与黑暗遮罩状态
        self.frenzy_state = None
        self.frenzy_tnts = []
        self.frenzy_crystals = []
        self.frenzy_shockwaves = []
        self.frenzy_laser = None
        self.storm_giga = None
        self.goldor_rage = None
        self.current_spell_idx += 1
        self.current_spell = None
        restore_sprite = getattr(self, "_spell_sprite_restore", None)
        if restore_sprite is not None:
            self.sprite_path, self.sprite_height = restore_sprite
            del self._spell_sprite_restore
        self.resistance = 1.0
        self.last_spell_active = False
        if (self.revive_after_spell_idx is not None
                and self.current_spell_idx == self.revive_after_spell_idx):
            self.phase = "reviving"
            self.revive_timer = self.revive_duration
            self.invincible = True
            self.invincible_timer = self.revive_duration
            return
        if (0 < self.current_spell_idx < len(self.spell_cards)
                and self.spell_cards[self.current_spell_idx - 1].direct_next):
            self._start_spell(self.spell_cards[self.current_spell_idx])
            return
        if self.current_spell_idx >= len(self.spell_cards):
            if self.last_spell is not None:
                # 所有通常符全部击破：立即展开 Last Spell（彩蛋挑战）
                self._start_spell(self.last_spell)
            else:
                self.phase = "defeated"
                self.alive = False
        else:
            self.phase = "non_spell"
            self.non_spell_timer = 0
            self.non_spell_duration = 240

    def take_damage(self, damage):
        if (self.entering or self.invincible or not self.combat_enabled
                or self.phase == "reviving"):
            return False
        if self._is_time_spell_active():
            return False
        self.hp -= damage * self.resistance
        # 血量钳制：确保三张符卡按序完整演出，Boss不会在最后一张符前被击杀
        if self.current_spell_idx < len(self.spell_cards):
            if self.phase == "spell" and self.current_spell:
                # 符卡进行中：优先用符卡自己的结束阈值，否则压到下一张符卡的阈值即视为击破
                next_idx = self.current_spell_idx + 1
                if self.current_spell.end_hp_threshold is not None:
                    threshold = self.current_spell.end_hp_threshold
                else:
                    threshold = (self.spell_cards[next_idx].hp_threshold
                                 if next_idx < len(self.spell_cards)
                                 else (self.last_spell.hp_threshold
                                       if self.last_spell is not None else None))
            else:
                # 非符中：压到本符卡触发阈值即钳制，等待最短非符时长后开符
                threshold = self.spell_cards[self.current_spell_idx].hp_threshold
            if threshold is not None:
                floor = self.max_hp * threshold
                if self.hp <= floor:
                    self.hp = floor
                    if self.phase == "spell" and self.current_spell:
                        self._end_spell()
                    return False
        elif self.last_spell is not None and not self.last_spell_active:
            # 通常符结束→Last Spell 前的极短过渡：仍钳制在 Last Spell 阈值
            threshold = self.last_spell.hp_threshold
            if threshold is not None:
                floor = self.max_hp * threshold
                if self.hp <= floor:
                    self.hp = floor
                    return False
        if self.hp <= 0:
            self._cancel_screen_bullets()   # 击败/击破符卡时清屏，避免弹幕残留
            self._begin_spell_bg_fade()
            self.phase = "defeated"   # 战后对话期间不再绘制符卡特效/光环
            self._clear_spell_effects()
            self.alive = False
            return True
        return False

    def draw(self, screen, offset_x=0, offset_y=0):
        px = int(self.x + offset_x)
        py = int(self.y + offset_y)

        if self.entering and self.entry_timer % 6 < 3:
            return

        # 龙符幻影龙：绘制在 Boss 本体之下
        self._draw_phantom_dragons(screen, offset_x, offset_y)
        # 超符黄金魔法阵：绘制在 Boss 本体之下
        self._draw_superior_circles(screen, offset_x, offset_y)
        # 石符：石柱结界与堡垒石环（绘制在 Boss 本体之下）
        self._draw_protector_effects(screen, offset_x, offset_y)
        # 展符：亡灵展品（绘制在 Boss 本体之下）
        self._draw_watcher_exhibits(screen, offset_x, offset_y)
        # 死符：Bonzo 召唤的 Undead（绘制在 Boss 本体之下）
        self._draw_bonzo_undeads(screen, offset_x, offset_y)
        # 骸符：Bonzo 的骷髅头阵列（绘制在 Boss 本体之下）
        self._draw_bonzo_dreadlord_skulls(screen, offset_x, offset_y)
        # 戏符：Bonzo 的小丑面具幻象节点（绘制在 Boss 本体之下）
        self._draw_bonzo_masks(screen, offset_x, offset_y)
        # 队符：Scarf 的四名亡灵成员与牧师强化法阵（绘制在 Boss 本体之下）
        self._draw_scarf_squad(screen, offset_x, offset_y)
        # 兵符：Sadan 的兵马俑军阵（绘制在 Boss 本体之下）
        self._draw_sadan_army(screen, offset_x, offset_y)
        # Sadan giant cycle visual layer: draw below Boss body.
        self._draw_sadan_giants(screen, offset_x, offset_y)
        # 机械符：金色环路走廊、终端与追击标记（绘制在 Boss 本体之下）
        if getattr(self, "goldor_terminal", None) is not None:
            from src.stages.goldor_terminal import _gt_draw_boss_layer
            _gt_draw_boss_layer(screen, self, offset_x, offset_y)
        # 超符：金色龙之核心光环（Last Spell 展开时）
        if self.is_last_spell_active():
            self._draw_core_aura(screen, px, py)
        # Boss 本体：配置了贴图时用贴图替换几何绘制（加载失败则回退八角形）
        if self.sprite_path:
            sprite = _get_boss_sprite(self.sprite_path, self.sprite_height)
            if sprite is not None:
                screen.blit(sprite, (px - sprite.get_width() // 2, py - sprite.get_height() // 2))
            else:
                self._draw_boss_body(screen, px, py)
        else:
            self._draw_boss_body(screen, px, py)

        # HP条（屏幕顶端）——未开战（对话阶段）不显示；战败后不再显示；时符无血量也不显示
        if self.combat_enabled and self.alive and not self._is_time_spell_active():
            self._draw_hp_bar(screen, offset_y + HP_BAR_TOP, offset_x)

        # 符卡名：与 Boss 名同一高度，顶格战斗框右侧
        if self.phase == "spell" and self.current_spell:
            font = _get_font(20)
            text = font.render(self.current_spell.name, True, cfg.COLOR_WHITE)
            screen.blit(text, (offset_x + cfg.BATTLE_AREA_WIDTH - text.get_width(),
                               offset_y + BOSS_NAME_Y))

        # 符卡宣言横幅：整幅立绘 + 符卡名，向下平移淡出
        self._draw_spell_banner(screen, offset_x, offset_y)


    def _draw_phantom_dragons(self, screen, offset_x=0, offset_y=0):
        """龙符幻影龙：龙形能量体沿固定轨迹环绕/穿越场地（带柔和光晕）"""
        if not self.phantom_dragons:
            return
        sprite = _get_boss_sprite(cfg.END_DRAGON_PET_SPRITE, PHANTOM_DRAGON_HEIGHT)
        if sprite is None:
            return
        glow = _get_phantom_dragon_glow()
        for i, ph in enumerate(self.phantom_dragons):
            px = int(ph["x"] + offset_x)
            py = int(ph["y"] + offset_y)
            ang = ph.get("angle", 0.0)
            flip = ph.get("flip", False)
            alpha = ph.get("alpha", 200)

            img = sprite
            glow_img = glow
            if ang:
                img = pygame.transform.rotate(sprite, -math.degrees(ang))
                if glow_img is not None:
                    glow_img = pygame.transform.rotate(glow_img, -math.degrees(ang))
            if flip:
                img = pygame.transform.flip(img, True, False)
                if glow_img is not None:
                    glow_img = pygame.transform.flip(glow_img, True, False)

            # 柔和光晕：亮度随整体透明度缩放，带轻微呼吸脉动
            if glow_img is not None:
                pulse = 0.72 + 0.28 * math.sin(pygame.time.get_ticks() * 0.004 + i * 1.9)
                glow_alpha = max(0, min(255, int(alpha * 0.55 * pulse)))
                if glow_alpha > 0:
                    g = _with_alpha(glow_img, glow_alpha)
                    screen.blit(g, (px - g.get_width() // 2, py - g.get_height() // 2))

            if alpha < 255:
                img = _with_alpha(img, alpha)
            screen.blit(img, (px - img.get_width() // 2, py - img.get_height() // 2))

    def _draw_core_aura(self, screen, px, py):
        """金色龙之核心：脉动金环 + 旋转符文环（Last Spell 期间围绕本体）"""
        t = pygame.time.get_ticks() * 0.003
        for i, (base_r, width, col) in enumerate((
                (34, 2, _SUPER_GOLD_DIM), (44, 1, _SUPER_GOLD), (54, 1, _SUPER_WHITE))):
            rr = int(base_r + math.sin(t + i * 1.4) * 2)
            pygame.draw.circle(screen, col, (px, py), rr, width)
        a = t * 0.9
        for k in range(4):
            ang = a + k * math.pi / 2
            x = px + math.cos(ang) * 30
            y = py + math.sin(ang) * 30
            pygame.draw.circle(screen, _SUPER_GOLD, (int(x), int(y)), 2, 0)

    def _draw_superior_circles(self, screen, offset_x=0, offset_y=0):
        """超符黄金魔法阵：双环 + 旋转辐条 + 阵眼符文（纯视觉，无判定）"""
        if not self.superior_circles:
            return
        for c in self.superior_circles:
            fade = min(1.0, c["life"] / 45.0)
            k = 0.30 + 0.70 * fade
            gold = tuple(int(ch * k) for ch in _SUPER_GOLD)
            gold_dim = tuple(int(ch * k * 0.8) for ch in _SUPER_GOLD_DIM)
            cx = int(c["x"] + offset_x)
            cy = int(c["y"] + offset_y)
            r = c["radius"]
            a = c["angle"]
            pygame.draw.circle(screen, gold_dim, (cx, cy), r, 2)
            pygame.draw.circle(screen, gold, (cx, cy), int(r * 0.72), 1)
            for i in range(8):
                ang = a + i * math.tau / 8
                x0 = cx + math.cos(ang) * r * 0.72
                y0 = cy + math.sin(ang) * r * 0.72
                x1 = cx + math.cos(ang) * r
                y1 = cy + math.sin(ang) * r
                pygame.draw.line(screen, gold_dim, (int(x0), int(y0)), (int(x1), int(y1)), 1)
            for i in range(4):
                ang = a + i * math.pi / 2 + math.pi / 4
                x = cx + math.cos(ang) * r * 0.86
                y = cy + math.sin(ang) * r * 0.86
                pygame.draw.circle(screen, gold, (int(x), int(y)), 3, 0)
    def _draw_protector_effects(self, screen, offset_x=0, offset_y=0):
        """石符：固定石柱结界 + 堡垒石环 + 震荡冲击环（纯视觉，无判定）"""
        # 固定石柱结界
        for p in self.protector_barriers:
            px = int(p["x"] + offset_x)
            py = int(p["y"] + offset_y)
            w, h = p["w"], p["h"]
            pygame.draw.rect(screen, _STONE_DIM, (px - w // 2, py - h // 2, w, h))
            pygame.draw.rect(screen, _STONE_COLOR, (px - w // 2, py - h // 2, w, h), 1)
            pygame.draw.rect(screen, _STONE_COLOR, (px - w // 2, py - h // 2 - 4, w, 5))
        # 堡垒石环：围绕本体的「岩石堡垒」轮廓
        if self.protector_fortress:
            cx = int(self.x + offset_x)
            cy = int(self.y + offset_y)
            t = pygame.time.get_ticks() * 0.002
            pygame.draw.circle(screen, _STONE_DIM, (cx, cy), 30, 2)
            pygame.draw.circle(screen, _STONE_COLOR, (cx, cy), 37, 1)
            for k in range(4):
                a = t + k * math.pi / 2
                tx = cx + math.cos(a) * 30
                ty = cy + math.sin(a) * 30
                pygame.draw.rect(screen, _STONE_DIM, (int(tx) - 5, int(ty) - 5, 10, 10))
                pygame.draw.rect(screen, _STONE_COLOR, (int(tx) - 5, int(ty) - 5, 10, 10), 1)
        # 震荡冲击环
        shock = self.protector_shock
        if shock is not None:
            prog = 1.0 - shock["life"] / shock["max_life"]
            r = int(22 + prog * 190)
            col = tuple(int(c * (0.55 + 0.45 * (1.0 - prog))) for c in _STONE_COLOR)
            pygame.draw.circle(screen, col,
                               (int(self.x + offset_x), int(self.y + offset_y)), r, 2)

    def _draw_watcher_exhibits(self, screen, offset_x=0, offset_y=0):
        """展符亡灵展品：屏幕上方一排亡灵幻影（贴图发光渲染 + 预警光环，纯视觉无判定）"""
        if not self.watcher_exhibits:
            return
        for ex in self.watcher_exhibits:
            height = ex.get("height", 56)
            sprite = _get_boss_sprite(ex["sprite"], height)
            if sprite is None:
                continue
            px = int(ex["x"] + offset_x)
            py = int(ex["y"] + offset_y)
            # 常驻幽蓝亡灵能量光晕
            glow = _get_watcher_glow(int(height * 0.95),
                                     ex.get("glow_color", (70, 110, 200)))
            if glow is not None:
                screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))
            # 预警：幽蓝脉冲光环（符卡点亮 ex["warn"] 期间持续闪烁）
            if ex.get("warn"):
                pulse = (pygame.time.get_ticks() * 0.012) % (math.tau)
                rr = int(height * 0.62) + int(math.sin(pulse) * 6)
                warn_col = ex.get("warn_color", (130, 220, 255))
                pygame.draw.circle(screen, warn_col, (px, py), rr, 2)
                pygame.draw.circle(screen, (240, 250, 255), (px, py), max(4, rr - 9), 1)
            # 亡灵幻影贴图：加法混合发光渲染（黑色背景不叠加）
            screen.blit(sprite, (px - sprite.get_width() // 2, py - sprite.get_height() // 2),
                        special_flags=pygame.BLEND_ADD)

    def _draw_revival_circle(self, screen, px, py, prog, color, now):
        """亡灵魔法阵：旋转六芒星紫环 + 内圈亮纹（Undead 召唤/复活共用，纯视觉）"""
        r = 15 + int(8 * (1.0 - prog))
        rot = now * 0.004
        bright = tuple(min(255, c + 60) for c in color)
        pygame.draw.circle(screen, color, (px, py), r, 2)
        pygame.draw.circle(screen, bright, (px, py), max(3, r - 5), 1)

        def _triangle(radius, offset):
            pts = [
                (px + math.cos(rot + offset + k * math.tau / 3) * radius,
                 py + math.sin(rot + offset + k * math.tau / 3) * radius)
                for k in range(3)
            ]
            pygame.draw.polygon(screen, color, pts, 1)

        _triangle(r, 0.0)
        _triangle(max(3, int(r * 0.6)), math.pi / 3)

    def _draw_bonzo_undeads(self, screen, offset_x=0, offset_y=0):
        """死符「Undead Revival」的 Undead 四态渲染：
        summoning 召唤魔法阵淡入 -> active 存活发光 -> dying 灵魂消散 -> reviving 魔法阵重组。
        纯视觉（含召唤/复活魔法阵、消散收缩、灵魂光点），命中与发射判定由符卡负责。"""
        if not self.bonzo_undeads:
            return
        now = pygame.time.get_ticks()
        for u in self.bonzo_undeads:
            height = u.get("height", 46)
            sprite = _get_boss_sprite(u["sprite"], height)
            px = int(u["x"] + offset_x)
            py = int(u["y"] + offset_y)
            phase = u["phase"]
            timer = u["timer"]
            glow_color = u.get("glow_color", (160, 80, 220))
            summon_color = u.get("summon_color", (180, 95, 235))
            soul_color = u.get("soul_color", (100, 225, 190))

            # 常驻亡灵能量光晕（所有状态都有一层淡紫柔光）
            glow = _get_watcher_glow(int(height * 0.9), glow_color)
            if glow is not None:
                screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))

            if phase == "summoning":
                # 召唤魔法阵 + 贴图随进度淡入（期间不可命中、不发射）
                prog = min(1.0, timer / max(1, u.get("summon_time", 24)))
                self._draw_revival_circle(screen, px, py, prog, summon_color, now)
                if sprite is not None:
                    sprite = _with_alpha(sprite, int(255 * prog))
                    screen.blit(sprite, (px - sprite.get_width() // 2,
                                         py - sprite.get_height() // 2))
            elif phase == "active":
                # 存活：贴图 + 青绿灵魂火核心
                if sprite is not None:
                    screen.blit(sprite, (px - sprite.get_width() // 2,
                                         py - sprite.get_height() // 2))
                pygame.draw.circle(screen, soul_color, (px, py), 4, 1)
            elif phase == "dying":
                # 灵魂消散：贴图淡出收缩 + 青绿残焰
                prog = 1.0 - min(1.0, timer / max(1, u.get("die_time", 22)))
                if sprite is not None:
                    w = max(1, int(sprite.get_width() * max(0.4, prog)))
                    h = max(1, int(sprite.get_height() * max(0.4, prog)))
                    small = pygame.transform.smoothscale(sprite, (w, h))
                    small = _with_alpha(small, int(255 * prog))
                    screen.blit(small, (px - w // 2, py - h // 2))
                pygame.draw.circle(screen, soul_color, (px, py),
                                   max(2, int(8 * prog)), 1)
            elif phase == "reviving":
                # 亡灵魔法阵重组：紫环旋转 + 青绿灵魂能量朝中心汇聚
                prog = min(1.0, timer / max(1, u.get("revive_time", 90)))
                self._draw_revival_circle(screen, px, py, prog, summon_color, now)
                for k in range(4):
                    a = now * 0.004 + k * math.pi / 2
                    rr = 6 + (1.0 - prog) * 26
                    gx = px + math.cos(a) * rr
                    gy = py + math.sin(a) * rr
                    pygame.draw.circle(screen, soul_color, (int(gx), int(gy)), 2, 0)

    def _draw_bonzo_dreadlord_skulls(self, screen, offset_x=0, offset_y=0):
        """骸符「Skull Dreadlord」的巨大骷髅头印记（纯视觉，弹幕判定由符卡负责）：
        预警浮现（紫色召唤环 + 脉冲光环）→ 张嘴（下颌开合 + 青色灵魂火眼窝/口）
        → 待命 → 消散淡出。"""
        if not self.bonzo_dreadlord_skulls:
            return
        now = pygame.time.get_ticks()
        for sk in self.bonzo_dreadlord_skulls:
            if not sk.get("alive", True):
                continue
            px = int(sk["x"] + offset_x)
            py = int(sk["y"] + offset_y)
            r = sk.get("radius", 17)
            phase = sk["phase"]
            timer = sk["timer"]
            bone = sk.get("bone_color", (250, 246, 235))
            teal = sk.get("soul_teal", (110, 235, 210))
            purple = sk.get("soul_purple", (170, 95, 235))
            warn = sk.get("warn_color", (150, 220, 255))
            mouth = max(0.0, min(1.0, sk.get("mouth", 0.0)))

            # 常驻亡灵能量光晕（柔和紫光）
            glow = _get_watcher_glow(int(r * 2.2), purple)
            if glow is not None:
                screen.blit(glow, (px - glow.get_width() // 2, py - glow.get_height() // 2))

            # 预警：扩张的紫色召唤环 + 脉冲光环（骷髅淡入浮现）
            alpha = 255
            scale = 1.0
            if phase == "warn":
                prog = min(1.0, timer / max(1, sk.get("warn_frames", 30)))
                ring_r = int(r * (1.3 + (1.0 - prog) * 2.0))
                pygame.draw.circle(screen, purple, (px, py), ring_r, 2)
                pulse = 0.5 + 0.5 * math.sin(now * 0.02)
                pygame.draw.circle(screen, warn, (px, py), int(r * (1.15 + pulse * 0.55)), 1)
                alpha = int(255 * min(1.0, prog * 1.5))
            elif phase == "despawn":
                prog = min(1.0, timer / max(1, sk.get("despawn_frames", 36)))
                alpha = int(255 * (1.0 - prog))
                scale = 1.0 - 0.4 * prog

            # 喷射闪光：嘴部一亮（纯视觉）
            flash = sk.get("flash", 0)
            if flash > 0:
                fl = min(1.0, flash / 6.0)
                pygame.draw.circle(screen, (215, 245, 255), (px, py),
                                   int(r * (0.9 + 0.6 * (1.0 - fl))), 1)

            if alpha <= 0:
                continue

            # 骷髅头绘制到临时表面（支持整体淡入淡出 / 缩小）
            size = int(r * 2.7) + 8
            surf = pygame.Surface((size, size), pygame.SRCALPHA)
            cx = cy = size // 2
            rr = r
            bone_dim = tuple(int(c * 0.80) for c in bone)
            socket = (26, 15, 42)
            mouth_dark = (20, 12, 32)

            # 颅顶骨冠（骷髅王尖刺）
            for k in (-2, -1, 1, 2):
                spx = cx + k * int(rr * 0.30)
                spy = int(cy - rr * 0.98)
                tip = (spx, spy - int(rr * (0.42 - abs(k) * 0.06)))
                base_l = (spx - int(rr * 0.16), spy + int(rr * 0.10))
                base_r = (spx + int(rr * 0.16), spy + int(rr * 0.10))
                pygame.draw.polygon(surf, bone, [tip, base_l, base_r])
                pygame.draw.polygon(surf, purple, [tip, base_l, base_r], 1)
            # 颅顶圆 + 颧骨/上颌（头骨下半变宽）
            pygame.draw.circle(surf, bone, (cx, int(cy - rr * 0.32)), int(rr * 0.78))
            for sx in (-1, 1):
                pygame.draw.circle(surf, bone, (cx + sx * int(rr * 0.42), int(cy + rr * 0.10)),
                                   int(rr * 0.42))
            # 骨缝线（颅顶细线）
            pygame.draw.line(surf, bone_dim, (cx - int(rr * 0.30), int(cy - rr * 0.62)),
                             (cx + int(rr * 0.30), int(cy - rr * 0.62)), 1)

            # 眼窝 + 青色灵魂火
            for sx in (-1, 1):
                ex = cx + sx * int(rr * 0.33)
                ey = int(cy - rr * 0.16)
                pygame.draw.circle(surf, socket, (ex, ey), int(rr * 0.24))
                flicker = 0.75 + 0.25 * math.sin(now * 0.02 + sx * 2.1)
                pygame.draw.circle(surf, teal, (ex, ey), max(2, int(rr * 0.13 * flicker)))
                pygame.draw.circle(surf, (205, 255, 235),
                                   (ex - int(rr * 0.06), ey - int(rr * 0.06)),
                                   max(1, int(rr * 0.04)))
                pygame.draw.circle(surf, purple, (ex, ey), int(rr * 0.24), 1)

            # 鼻洞（倒三角）
            nose_top = (cx, int(cy + rr * 0.06))
            nose_l = (cx - int(rr * 0.10), int(cy + rr * 0.22))
            nose_r = (cx + int(rr * 0.10), int(cy + rr * 0.22))
            pygame.draw.polygon(surf, socket, [nose_top, nose_l, nose_r])

            # 嘴部：开口高度随 mouth 张合，含上下牙齿与口腔灵魂火
            mouth_top = int(cy + rr * 0.52)
            gap = int(rr * 0.45 * mouth)
            mouth_bottom = mouth_top + gap
            mouth_w = int(rr * 0.66)
            pygame.draw.rect(surf, mouth_dark,
                             (cx - mouth_w // 2, mouth_top, mouth_w, max(1, gap)))
            if mouth > 0.02:
                if mouth > 0.3:
                    flame_r = max(2, int(rr * 0.18 * mouth))
                    pygame.draw.circle(surf, teal, (cx, mouth_top + gap // 2), flame_r)
                teeth = 5
                for k in range(teeth):
                    tx = cx + (k - (teeth - 1) / 2) * int(rr * 0.15)
                    tw = max(2, int(rr * 0.09))
                    th = max(2, int(rr * 0.13))
                    pygame.draw.rect(surf, bone, (tx - tw // 2, mouth_top - th // 2, tw, th))
                    pygame.draw.rect(surf, bone, (tx - tw // 2, mouth_bottom - th // 2, tw, th))
                pygame.draw.rect(surf, purple, (cx - mouth_w // 2, mouth_top,
                                                mouth_w, max(1, gap)), 1)

            # 下颌骨（随开口下移）
            jaw_cy = int(cy + rr * 0.62 + gap)
            pygame.draw.ellipse(surf, bone, (cx - int(rr * 0.55), jaw_cy - int(rr * 0.30),
                                             int(rr * 1.10), int(rr * 0.60)))
            pygame.draw.ellipse(surf, purple, (cx - int(rr * 0.55), jaw_cy - int(rr * 0.30),
                                               int(rr * 1.10), int(rr * 0.60)), 1)

            # 颅骨外轮廓（紫色描边）
            pygame.draw.circle(surf, purple, (cx, int(cy - rr * 0.32)), int(rr * 0.78), 1)
            for sx in (-1, 1):
                pygame.draw.circle(surf, purple, (cx + sx * int(rr * 0.42), int(cy + rr * 0.10)),
                                   int(rr * 0.42), 1)

            # 整体淡入淡出 / 缩放后贴回屏幕
            if scale != 1.0:
                new_w = max(1, int(size * scale))
                surf = pygame.transform.smoothscale(surf, (new_w, new_w))
            if alpha < 255:
                surf = _with_alpha(surf, alpha)
            screen.blit(surf, (px - surf.get_width() // 2, py - surf.get_height() // 2))

    def _draw_bonzo_masks(self, screen, offset_x=0, offset_y=0):
        """戏符「Grand Illusion」的小丑面具幻象节点：
        紫色柔光 + Bonzo 面具贴图，消失/重生时按 alpha 淡入淡出。纯视觉，无判定。"""
        if not self.bonzo_masks:
            return
        now = pygame.time.get_ticks()
        for mask in self.bonzo_masks:
            x = mask.get("x")
            y = mask.get("y")
            if x is None or y is None:
                continue
            px = int(x + offset_x)
            py = int(y + offset_y)
            height = mask.get("height", 54)
            alpha = mask.get("alpha", 255)
            if alpha <= 0:
                continue
            color = mask.get("glow_color", (205, 105, 245))
            glow = _get_watcher_glow(int(height * 0.95), color)
            if glow is not None:
                screen.blit(glow, (px - glow.get_width() // 2,
                                   py - glow.get_height() // 2))
            # 存活期间缓慢呼吸的紫色外环
            pulse = 0.5 + 0.5 * math.sin(now * 0.006 + mask.get("phase", 0.0))
            ring_r = int(height * 0.58 + pulse * 5)
            pygame.draw.circle(screen, color, (px, py), ring_r, 1)
            sprite = _get_boss_sprite(cfg.STAGE3_BONZO_MASK_SPRITE, height)
            if sprite is None:
                continue
            if alpha < 255:
                sprite = _with_alpha(sprite, alpha)
            screen.blit(sprite, (px - sprite.get_width() // 2,
                                 py - sprite.get_height() // 2),
                        special_flags=pygame.BLEND_ADD)

    def _draw_scarf_squad(self, screen, offset_x=0, offset_y=0):
        """队符「Necrotic Squad」的小队视觉层：
        四名亡灵固定站位；当前主攻成员有脉冲光环和名字标识；
        牧师紫色强化法阵旋转显示（纯视觉，命中与强化判定由符卡负责）。"""
        now = pygame.time.get_ticks()

        # 牧师强化法阵：多个小法阵，均绘制外环、内圈符文辐条并在生命末端淡出。
        for circle in self.scarf_buff_circles:
            cx = int(circle["x"] + offset_x)
            cy = int(circle["y"] + offset_y)
            r = int(circle["radius"])
            max_life = max(1, circle.get("max_life", 1))
            fade = min(1.0, circle.get("life", 0) / min(45.0, max_life * 0.12))
            bright = tuple(int(ch * (0.45 + 0.55 * fade)) for ch in (180, 95, 240))
            dim = tuple(int(ch * 0.55) for ch in bright)
            pulse = 0.5 + 0.5 * math.sin(now * 0.006 + circle["x"] * 0.02)
            pygame.draw.circle(screen, bright, (cx, cy), r, 2)
            pygame.draw.circle(screen, dim, (cx, cy), int(r * 0.82), 1)
            rot = now * 0.0012
            for i in range(8):
                a = rot + i * math.tau / 8
                x0 = cx + math.cos(a) * r * 0.60
                y0 = cy + math.sin(a) * r * 0.60
                x1 = cx + math.cos(a) * r * (0.90 + pulse * 0.08)
                y1 = cy + math.sin(a) * r * (0.90 + pulse * 0.08)
                pygame.draw.line(screen, dim, (int(x0), int(y0)),
                                 (int(x1), int(y1)), 1)
            pygame.draw.circle(screen, bright, (cx, cy), 4, 0)

        if not self.scarf_squad:
            return

        font = _get_font(11)
        for idx, member in enumerate(self.scarf_squad):
            px = int(member["x"] + offset_x)
            py = int(member["y"] + offset_y)
            height = member.get("height", 64)
            color = member.get("color", (200, 200, 200))
            active = bool(member.get("active", False))

            # 亡灵成员常驻柔和光晕。
            glow = _get_watcher_glow(int(height * 0.95), color)
            if glow is not None:
                screen.blit(glow, (px - glow.get_width() // 2,
                                   py - glow.get_height() // 2))

            # 当前主攻成员：脉冲光环 + 高亮小核。
            if active:
                pulse = 0.5 + 0.5 * math.sin(now * 0.008 + idx * 0.9)
                ring_r = int(height * 0.58 + pulse * 7)
                pygame.draw.circle(screen, color, (px, py), ring_r, 2)
                pygame.draw.circle(screen, (255, 255, 255),
                                   (px, py), max(3, ring_r - 6), 1)
                pygame.draw.circle(screen, (255, 255, 255), (px, py), 3, 0)

            sprite = _get_boss_sprite(member["sprite"], height)
            if sprite is not None:
                screen.blit(sprite, (px - sprite.get_width() // 2,
                                     py - sprite.get_height() // 2))

            # 当前主攻者名字：让玩家能明确识别这一轮是谁在攻击。
            if active and member.get("label"):
                text = font.render(member["label"], True, cfg.COLOR_WHITE)
                screen.blit(text, (px - text.get_width() // 2,
                                   py + int(height * 0.52) + 2))

    def _draw_sadan_army(self, screen, offset_x=0, offset_y=0):
        """兵符「Terracotta Army」的兵马俑军阵视觉层。
        active 存活/冲锋、down 石质头骨标记、reviving 复活法阵。
        纯视觉，命中与发射判定由 stage4 符卡函数负责。"""
        if not self.sadan_army:
            return
        now = pygame.time.get_ticks()
        for s in self.sadan_army:
            px = int(s["x"] + offset_x)
            py = int(s["y"] + offset_y)
            phase = s.get("phase", "active")
            timer = s.get("timer", 0)
            attack_active = bool(s.get("attack_active", False))

            if phase == "down":
                self._draw_terracotta_skull(screen, px, py, timer,
                                            s.get("down_time", 190))
                continue
            if phase == "reviving":
                prog = min(1.0, timer / max(1, s.get("revive_time", 38)))
                self._draw_revival_circle(screen, px, py, prog,
                                          (206, 126, 74), now)
                self._draw_terracotta_soldier(screen, px, py, s, now,
                                              alpha=70 + int(150 * prog),
                                              attack_active=False)
                continue
            self._draw_terracotta_soldier(screen, px, py, s, now,
                                          alpha=255,
                                          attack_active=attack_active)

    def _draw_sadan_giants(self, screen, offset_x=0, offset_y=0):
        """Visual layer for Sadan's "Precursors' Return" giant cycle.

        The state machine and all collision bullets are handled by stage4.
        This layer only draws the telegraph, giant sprites, laser warnings,
        shockwave fronts and the oversized boulder frame.
        """
        state = getattr(self, "sadan_giant_state", None)
        if not state:
            return
        now = pygame.time.get_ticks()

        # Shockwave fronts: non-collision animation rings managed by the spell.
        for wave in state.get("waves", []):
            x = wave.get("x")
            y = wave.get("y")
            life = wave.get("life", 0)
            if x is None or y is None or life <= 0:
                continue
            max_life = max(1, wave.get("max_life", life))
            prog = 1.0 - life / max_life
            start_r = wave.get("start_radius", 18)
            end_r = wave.get("end_radius", 210)
            r = int(start_r + prog * (end_r - start_r))
            alpha = int(255 * (1.0 - prog))
            if alpha <= 0:
                continue
            color = wave.get("color", (255, 255, 255))
            width = max(1, wave.get("width", 2))
            cx = int(x + offset_x)
            cy = int(y + offset_y)
            pygame.draw.circle(screen, color, (cx, cy), max(1, r), width)
            if r > 7:
                pygame.draw.circle(screen, color, (cx, cy), max(1, r - 6), 1)

        # Telegraph: player can identify the next giant and its fixed spawn slot.
        telegraph = state.get("telegraph")
        if telegraph:
            px = int(telegraph["x"] + offset_x)
            py = int(telegraph["y"] + offset_y)
            pulse = 0.5 + 0.5 * math.sin(now * 0.012 + telegraph.get("phase", 0.0))
            radius = int(telegraph.get("radius", 30) + pulse * 8)
            color = telegraph.get("color", (255, 220, 150))
            pygame.draw.circle(screen, color, (px, py), radius, 2)
            pygame.draw.circle(screen, (255, 255, 255), (px, py), max(4, radius - 7), 1)
            pygame.draw.circle(screen, color, (px, py), 4, 0)
            label = telegraph.get("label")
            if label:
                font = _get_font(11)
                text = font.render(label, True, color)
                screen.blit(text, (px - text.get_width() // 2, py - radius - 12))

        # L.A.S.R. laser warning line and eye glow.
        laser = state.get("laser")
        if laser:
            self._draw_sadan_laser_visual(screen, laser, now, offset_x, offset_y)

        # Diamond Giant: square frames around all live boulders.
        for ref in state.get("boulder_refs", []):
            boulder = ref.get("b") if isinstance(ref, dict) else ref
            if boulder is None or not getattr(boulder, "alive", False):
                continue
            bx = int(boulder.x + offset_x)
            by = int(boulder.y + offset_y)
            half = 12
            pygame.draw.rect(screen, (120, 205, 255),
                             (bx - half, by - half, half * 2, half * 2), 3)
            pygame.draw.rect(screen, (230, 245, 255),
                             (bx - half + 3, by - half + 3,
                              half * 2 - 6, half * 2 - 6), 1)

        # Diamond Giant's falling sword is visual-only; the landing burst is
        # created by stage4 when its y coordinate reaches land_y.
        sword = state.get("sword")
        if sword:
            sx = int(sword.get("x", cfg.BATTLE_AREA_WIDTH / 2) + offset_x)
            sy = int(sword.get("y", -200) + offset_y)
            sword_sprite = _get_sadan_sword_sprite(
                sword.get("sprite"), int(sword.get("height", 660)))
            if sword_sprite is not None:
                screen.blit(sword_sprite,
                            (sx - sword_sprite.get_width() // 2,
                             sy - sword_sprite.get_height() // 2))
            else:
                half_w = 18
                sword_h = int(sword.get("height", 660))
                pygame.draw.rect(screen, (140, 215, 255),
                                 (sx - half_w, sy - sword_h, half_w * 2, sword_h), 3)

        if state.get("hide_giant"):
            return
        giant = state.get("giant")
        if not giant:
            return
        x = giant.get("x")
        y = giant.get("y")
        if x is None or y is None:
            return
        px = int(x + offset_x)
        py = int(y + offset_y)
        height = giant.get("height", 150)
        alpha = int(giant.get("alpha", 255))
        if alpha <= 0:
            return
        color = giant.get("color", (200, 180, 150))
        sprite_path = giant.get("sprite")
        sprite = _get_boss_sprite(sprite_path, height) if sprite_path else None

        glow = _get_watcher_glow(int(height * 0.85), color)
        if glow is not None:
            draw_glow = glow if alpha >= 255 else _with_alpha(glow, alpha)
            screen.blit(draw_glow, (px - draw_glow.get_width() // 2,
                                    py - draw_glow.get_height() // 2))

        if sprite is not None:
            draw_sprite = sprite if alpha >= 255 else _with_alpha(sprite, alpha)
            screen.blit(draw_sprite, (px - draw_sprite.get_width() // 2,
                                      py - draw_sprite.get_height() // 2))
        else:
            # Distinct colored silhouette fallback if a sprite is missing.
            hw = max(1, int(height * 0.22))
            hh = max(1, int(height * 0.50))
            pygame.draw.ellipse(screen, color, (px - hw, py - hh, hw * 2, hh * 2))
            pygame.draw.circle(screen, color, (px, py - int(height * 0.36)),
                               max(1, int(height * 0.14)), 0)

        label = giant.get("label")
        if label and giant.get("phase") in ("entering", "attack"):
            font = _get_font(11)
            text = font.render(label, True, cfg.COLOR_WHITE)
            label_y = py + int(height * 0.52) + 2
            screen.blit(text, (px - text.get_width() // 2, label_y))

            max_hp = max(1, int(giant.get("max_hp", 1)))
            hp = max(0, int(giant.get("hp", max_hp)))
            bar_w = int(height * 0.46)
            bar_h = 6
            bar_x = px - bar_w // 2
            bar_y = label_y + 14
            pygame.draw.rect(screen, (24, 26, 36), (bar_x, bar_y, bar_w, bar_h))
            fill_w = int(bar_w * min(1.0, hp / max_hp))
            pygame.draw.rect(screen, color, (bar_x, bar_y, fill_w, bar_h))
            pygame.draw.rect(screen, cfg.COLOR_WHITE,
                             (bar_x, bar_y, bar_w, bar_h), 1)

    def _draw_sadan_laser_visual(self, screen, laser, now, offset_x=0, offset_y=0):
        """Draws L.A.S.R.'s warning line and eye source without re-adding collision."""
        x = int(laser["x"] + offset_x)
        y = int(laser["y"] + offset_y)
        angle = laser.get("angle", 0.0)
        length = laser.get("length", 0.0)
        ex = int(x + math.cos(angle) * length)
        ey = int(y + math.sin(angle) * length)
        color = laser.get("color", (255, 70, 70))
        phase = laser.get("phase")

        if phase == "warn":
            pulse = 0.5 + 0.5 * math.sin(now * 0.02)
            bright = tuple(int(ch * (0.35 + 0.65 * pulse)) for ch in color)
            pygame.draw.line(screen, bright, (x, y), (ex, ey), 5)
            pygame.draw.line(screen, (255, 255, 255), (x, y), (ex, ey), 1)
        elif phase == "active":
            pygame.draw.line(screen, color, (x, y), (ex, ey), 8)
            pygame.draw.circle(screen, (255, 255, 255), (x, y), 5, 0)
        elif phase == "recover":
            pygame.draw.line(screen, color, (x, y), (ex, ey), 2)

        if phase in ("warn", "active", "recover"):
            r = 6 if phase == "active" else 5
            pygame.draw.circle(screen, color, (x, y), r, 1)

    def _draw_terracotta_soldier(self, screen, px, py, s, now, alpha=255,
                                 attack_active=False):
        """兵马俑贴图渲染；贴图缺失时回退到简单陶土人形。"""
        sprite_path = s.get("sprite", cfg.STAGE4_TERRACOTTA_SPRITE)
        height = s.get("sprite_height", 38)
        sprite = _get_boss_sprite(sprite_path, height)

        if sprite is not None:
            draw_sprite = sprite if alpha >= 255 else _with_alpha(sprite, alpha)
            screen.blit(draw_sprite,
                        (px - draw_sprite.get_width() // 2,
                         py - draw_sprite.get_height() // 2))
        else:
            pygame.draw.ellipse(screen, (35, 25, 22),
                                (px - 11, py - 12, 22, 26))
            pygame.draw.rect(screen, (196, 112, 62),
                             (px - 7, py - 6, 14, 18), border_radius=4)
            pygame.draw.circle(screen, (196, 112, 62), (px, py - 12), 7)

        if attack_active and alpha >= 255:
            pulse = 0.5 + 0.5 * math.sin(now * 0.012 + px * 0.03)
            ring = int(14 + pulse * 3)
            pygame.draw.circle(screen, (255, 190, 120), (px, py), ring, 1)

    def _draw_terracotta_skull(self, screen, px, py, timer, down_time):
        """被击破后留在原阵位的石质头骨标记，外圈显示复活进度。"""
        base = (122, 102, 88)
        dark = (40, 34, 30)
        light = (188, 146, 106)

        pygame.draw.ellipse(screen, (45, 38, 33), (px - 9, py - 8, 18, 18))
        pygame.draw.circle(screen, base, (px, py), 9)
        pygame.draw.rect(screen, base, (px - 6, py + 1, 12, 7), border_radius=2)
        pygame.draw.circle(screen, dark, (px - 3, py - 2), 2)
        pygame.draw.circle(screen, dark, (px + 3, py - 2), 2)
        pygame.draw.line(screen, dark, (px - 2, py + 6), (px + 2, py + 6), 1)

        prog = min(1.0, timer / max(1, down_time))
        rect = (px - 12, py - 12, 24, 24)
        start = math.pi / 2
        end = start + math.tau * prog
        pygame.draw.arc(screen, light, rect, start, end, 2)

    def _draw_boss_body(self, screen, px, py):
        """Boss 本体（八角形 + 魔法阵光环）"""
        r = self.size
        points = []
        for i in range(8):
            angle = i * math.pi / 4
            points.append((px + math.cos(angle) * r, py + math.sin(angle) * r))
        pygame.draw.polygon(screen, self.color, points, 0)
        pygame.draw.polygon(screen, cfg.COLOR_WHITE, points, 2)

        # 魔法阵光环
        glow_r = r + 6 + math.sin(pygame.time.get_ticks() * 0.003) * 3
        pygame.draw.circle(screen, self.color, (px, py), int(glow_r), 2)

    def _draw_spell_banner(self, screen, offset_x=0, offset_y=0):
        """符卡宣言：整幅 Boss 立绘 + 符卡名，居中显示后向下略平移淡出"""
        if not self.spell_banner_active:
            return
        self.spell_banner_timer += 1
        if self.spell_banner_timer > SPELL_BANNER_DURATION:
            self.spell_banner_active = False
            return

        # 透明度：快速淡入，后段淡出
        t = self.spell_banner_timer / SPELL_BANNER_DURATION
        if t < SPELL_BANNER_FADE_IN / SPELL_BANNER_DURATION:
            alpha = int(255 * t * SPELL_BANNER_DURATION / SPELL_BANNER_FADE_IN)
        elif t > 1 - SPELL_BANNER_FADE_OUT / SPELL_BANNER_DURATION:
            alpha = int(255 * (1 - t) * SPELL_BANNER_DURATION / SPELL_BANNER_FADE_OUT)
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))
        drop = int(t * SPELL_BANNER_DROP)

        cx = offset_x + cfg.BATTLE_AREA_WIDTH // 2
        cy = offset_y + cfg.BATTLE_AREA_HEIGHT // 2 + drop

        # 整幅立绘（等比放大铺满战斗区域中部）
        if self.sprite_path:
            banner_h = _banner_target_height(self.sprite_path)
            sprite = _get_boss_sprite(self.sprite_path, banner_h)
            if sprite is not None:
                if alpha < 255:
                    sprite = _with_alpha(sprite, alpha)
                screen.blit(sprite, (cx - sprite.get_width() // 2, cy - sprite.get_height() // 2))

        # 符卡名（中间附近，带半透明底框）
        if self.spell_banner_name:
            font = _get_font(34)
            text = font.render(self.spell_banner_name, True, cfg.COLOR_WHITE)
            text = _with_alpha(text, alpha)
            pad_x, pad_y = 18, 8
            box = pygame.Surface((text.get_width() + pad_x * 2, text.get_height() + pad_y * 2), pygame.SRCALPHA)
            box.fill((10, 14, 26, int(alpha * 0.62)))
            pygame.draw.rect(box, (255, 255, 255, int(alpha * 0.85)), box.get_rect(), 2, border_radius=6)
            box.blit(text, (pad_x, pad_y))
            screen.blit(box, (cx - box.get_width() // 2, cy + 150 - box.get_height() // 2))

    def _draw_hp_bar(self, screen, y, offset_x=0):
        inset = self.hp_bar_inset          # 血条左右边距（默认 30）
        bar_w = cfg.BATTLE_AREA_WIDTH - inset * 2
        bar_h = HP_BAR_HEIGHT
        bar_x = inset + offset_x

        hp_ratio = max(0, self.hp / self.max_hp)

        pygame.draw.rect(screen, cfg.COLOR_DARK_GRAY, (bar_x, y, bar_w, bar_h))
        if hp_ratio > 0.3:
            color = cfg.COLOR_RED
        elif hp_ratio > 0.15:
            color = cfg.COLOR_YELLOW
        else:
            color = cfg.COLOR_WHITE
        pygame.draw.rect(screen, color, (bar_x, y, int(bar_w * hp_ratio), bar_h))
        pygame.draw.rect(screen, cfg.COLOR_WHITE, (bar_x, y, bar_w, bar_h), 1)

        for i in range(1, 4):
            mx = bar_x + bar_w * i / 4
            pygame.draw.line(screen, cfg.COLOR_WHITE, (mx, y - 2), (mx, y + bar_h + 2), 1)

        # Boss 名（只保留英文）：血量下方一行，左侧略缩进避免贴边被遮挡
        font = _get_font(16)
        name_text = font.render(_english_only(self.name), True, cfg.COLOR_WHITE)
        screen.blit(name_text, (offset_x + 6, y + bar_h + 4))

    def get_hitbox(self):
        return (self.x, self.y, self.size * 0.6)

    def collides_with_bullet(self, bx, by, br):
        """贴图形状判定：有贴图时按贴图 Mask 逐像素判定；无贴图时回退圆形判定"""
        if self.sprite_path:
            sprite = _get_boss_sprite(self.sprite_path, self.sprite_height)
            mask = _get_boss_mask(self.sprite_path, self.sprite_height)
            if sprite is not None and mask is not None:
                w, h = sprite.get_size()
                rect = pygame.Rect(self.x - w / 2, self.y - h / 2, w, h)
                # 粗略包围盒提前排除，避免频繁 Mask 运算
                if not (rect.left - br <= bx <= rect.right + br
                        and rect.top - br <= by <= rect.bottom + br):
                    return False
                # 将子弹圆形 Mask 对齐到贴图 Mask 上检测重叠
                r = max(1, int(round(br)))
                c = r + 1
                offset = (int(round(bx - c - rect.left)), int(round(by - c - rect.top)))
                return mask.overlap(_get_bullet_mask(br), offset) is not None
        # 无贴图或贴图加载失败：回退为原圆形判定
        return circle_collision(bx, by, br, self.x, self.y, self.size * 0.6)


# --- 预定义符卡弹幕模式 ---

def spell_rain_homing(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    if timer % 8 == 0:
        angle = random.uniform(-0.5, 0.5) - math.pi / 2
        for offset in [0, random.uniform(-0.1, 0.1)]:
            b = create_bullet_angle(boss.x, boss.y, angle + offset, 3.5,
                                    Bullet.TYPE_RICE, radius=2.5, color=cfg.COLOR_BLUE)
            bullet_manager.add_enemy_bullet(b)

def spell_spiral_wave(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    if timer % 12 == 0:
        for i in range(6):
            angle = timer * 0.04 + i * math.pi * 2 / 6
            b = create_bullet_angle(boss.x, boss.y, angle, 1.8,
                                    Bullet.TYPE_CIRCLE, radius=3, color=cfg.COLOR_PURPLE)
            bullet_manager.add_enemy_bullet(b)

def spell_cross_rings(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    if timer % 20 == 0:
        base = timer * 0.03
        for i in range(8):
            angle = base + i * math.pi / 4
            b = create_bullet_angle(boss.x, boss.y, angle, 2.5,
                                    Bullet.TYPE_BIG, radius=5, color=cfg.COLOR_ORANGE)
            bullet_manager.add_enemy_bullet(b)

def spell_laser_web(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    if timer % 30 == 0:
        for i in range(3):
            angle = timer * 0.02 + i * math.pi * 2 / 3
            for j in range(5):
                offset = (j - 2) * 0.15
                b = create_bullet_angle(boss.x, boss.y, angle + offset, 3.0,
                                        Bullet.TYPE_ARROW, radius=3, color=cfg.COLOR_GREEN)
                bullet_manager.add_enemy_bullet(b)

def spell_chaos_storm(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    if timer % 5 == 0:
        angle = random.uniform(0, math.pi * 2)
        speed = random.uniform(1.5, 4.0)
        b = create_bullet_angle(boss.x, boss.y, angle, speed,
                                Bullet.TYPE_KNIFE, radius=2.5,
                                color=(255, random.randint(50, 200), random.randint(50, 200)))
        bullet_manager.add_enemy_bullet(b)

def spell_luxurious_spool(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """罠符「Luxurious Spool」：蜘蛛网状的旋转弹幕（降低密度后）"""
    # 旋转辅条：沿辅条铺开的丝线弹，整体缓慢旋转
    if timer % 12 == 0:
        spokes = 5
        base_angle = timer * 0.02
        for i in range(spokes):
            angle = base_angle + i * math.pi * 2 / spokes
            for j in range(3):
                b = create_bullet_angle(boss.x, boss.y, angle, 1.0 + j * 0.35,
                                        Bullet.TYPE_RICE, radius=2.5,
                                        color=cfg.COLOR_PURPLE if j % 2 == 0 else cfg.COLOR_YELLOW)
                bullet_manager.add_enemy_bullet(b)

    # 横向扩张的蜘蛛网圆环
    if timer % 45 == 0:
        for i in range(10):
            angle = i * math.pi * 2 / 10
            b = create_bullet_angle(boss.x, boss.y, angle, 0.7,
                                    Bullet.TYPE_CIRCLE, radius=3, color=cfg.COLOR_GREEN)
            bullet_manager.add_enemy_bullet(b)
            b = create_bullet_angle(boss.x, boss.y, angle, 0.7,
                                    Bullet.TYPE_CIRCLE, radius=3, color=cfg.COLOR_GREEN)
            bullet_manager.add_enemy_bullet(b)


# --- 丝符「Soul String」：织网（Arachne 一符） ---

_SOUL_STRING_CYCLE = 240          # 每轮“织网→成网→收网”总帧数
_SOUL_STRING_ARM_AT = 160         # 蛛网绘制完成并激活判定的帧
_SOUL_STRING_CLEAR_AT = 215       # 蛛网开始消散的帧
_SOUL_STRING_SPOKES = 16          # 辐条数量
_SOUL_STRING_RINGS = (80, 140, 200, 260, 320, 380)   # 环形层半径（6圈）
_SOUL_STRING_WEB_RADIUS = 400     # 辐条最远半径（一直延伸到屏幕外）
_SOUL_STRING_STRAND_STEP = 20     # 丝线段间距（px，略重叠形成连续线）
_SOUL_STRING_STRAND_RADIUS = 3.0  # 丝线段（米弹）基础半径


def _build_soul_string_web(cx, cy, rot=0.0):
    """生成一张铺满屏幕并延伸到屏幕外的蛛网丝线段：辐条（径向米弹）+ 环形层（切向米弹）"""
    points = []
    # 辐条：从蛛网中心向外铺开的径向丝线段
    for i in range(_SOUL_STRING_SPOKES):
        angle = i * math.pi * 2 / _SOUL_STRING_SPOKES + rot
        for r in range(40, _SOUL_STRING_WEB_RADIUS + 1, _SOUL_STRING_STRAND_STEP):
            points.append((cx + math.cos(angle) * r, cy + math.sin(angle) * r, angle))
    # 环形层：沿圆弧铺开的切向丝线段，与辐条交错形成网格
    for ring_r in _SOUL_STRING_RINGS:
        count = max(12, int(2 * math.pi * ring_r / _SOUL_STRING_STRAND_STEP))
        for i in range(count):
            angle = i * math.pi * 2 / count + rot * 0.5
            points.append((cx + math.cos(angle) * ring_r, cy + math.sin(angle) * ring_r,
                           angle + math.pi / 2))
    return points


def _spawn_soul_string_strand(bullet_manager, px, py, angle):
    """结出一根蛛丝线段：从略内侧滑出并停稳在目标位置；绘制期间无判定"""
    brake = 0.10
    slide = 3.0
    v = math.sqrt(2 * brake * slide)
    sx = px - math.cos(angle) * slide
    sy = py - math.sin(angle) * slide
    b = create_bullet_angle(sx, sy, angle, v,
                            Bullet.TYPE_RICE, radius=_SOUL_STRING_STRAND_RADIUS,
                            color=(150, 96, 210))
    b.manager = bullet_manager
    b.brake = brake
    b.angle = angle
    b.harmless = True
    b.lifetime = 600
    bullet_manager.add_enemy_bullet(b)
    return b


def spell_soul_string(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """丝符「Soul String」：结出蜘蛛网（绘制期无判定，成网后激活判定），
    搭配少量自机狙与散的干扰弹幕，织网→成网→收网循环直至符卡结束"""
    state = boss.__dict__.setdefault("_soul_string_state", {})
    if timer == 1:
        state.clear()

    t = timer % _SOUL_STRING_CYCLE
    cycle = timer // _SOUL_STRING_CYCLE

    # --- 织网期：逐点结出蛛网（全程无判定） ---
    if t == 1:
        # ??????Arachne ???????????????????????
        dest_x = random.uniform(150, cfg.BATTLE_AREA_WIDTH - 150)
        boss.move_to(dest_x, boss.y)
        cx = cfg.BATTLE_AREA_WIDTH / 2
        cy = cfg.BATTLE_AREA_HEIGHT / 2
        rot = (cycle % 2) * 0.28 + random.uniform(-0.08, 0.08)
        state["points"] = _build_soul_string_web(cx, cy, rot)
        state["strands"] = []

    if t < _SOUL_STRING_ARM_AT and state.get("points"):
        for _ in range(6):
            if not state["points"]:
                break
            px, py, angle = state["points"].pop(0)
            b = _spawn_soul_string_strand(bullet_manager, px, py, angle)
            state["strands"].append(b)

    # --- 成网：蛛网完成，整张网激活判定 ---
    if t == _SOUL_STRING_ARM_AT:
        for b in state.get("strands", []):
            b.harmless = False
            b.color = cfg.COLOR_GREEN
            # 视觉放大并略微加大判定（还原基础半径→放大→再套视觉缩放）
            base = b.radius / cfg.ENEMY_BULLET_RADIUS_SCALE * 1.25
            b.radius = base * cfg.ENEMY_BULLET_RADIUS_SCALE
            b.collision_radius = base * 0.5

    # --- 收网：蛛网消散，准备下一轮 ---
    if t == _SOUL_STRING_CLEAR_AT:
        for b in state.get("strands", []):
            b.start_cancel()
        state["strands"] = []

    # --- 自机狙（少量，不密集） ---
    if t in (80, 175, 195):
        b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 2.8,
                                Bullet.TYPE_RICE, radius=2.5, color=cfg.COLOR_ORANGE)
        bullet_manager.add_enemy_bullet(b)

    # --- 散的干扰弹幕：随机位置的小扇散弹 ---
    if t % 30 == 15:
        sx = random.uniform(60, cfg.BATTLE_AREA_WIDTH - 60)
        sy = random.uniform(40, 360)
        base = random.uniform(0, math.pi * 2)
        color = random.choice((cfg.COLOR_ORANGE, (255, 96, 160), cfg.COLOR_WHITE))
        for i in range(4):
            angle = base + (i - 1.5) * 0.24
            btype = Bullet.TYPE_CIRCLE if i % 2 == 0 else Bullet.TYPE_KNIFE
            b = create_bullet_angle(sx, sy, angle, random.uniform(1.5, 2.2),
                                    btype, radius=2.5, color=color)
            bullet_manager.add_enemy_bullet(b)


def spell_tarantula_tornado(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """蛛符「Tarantula's Tornado」：蛛足旋风 + 织网飞针"""
    # 蜘蛛女王每隔几秒在当前 x 附近小幅左右移动一次（幅度较小），旋风跟着本体扫场
    if timer % 240 == 0:
        boss.target_x = max(60, min(cfg.BATTLE_AREA_WIDTH - 60,
                                    boss.x + random.uniform(-90, 90)))

    # 蛛足旋风：两股方向相反的刀弹涡流绕Boss公转外扩，到半径上限后沿切线甩出
    if timer % 10 == 0:
        center = (boss.x + math.sin(timer * 0.012) * 45,
                  boss.y + math.cos(timer * 0.009) * 25)
        for arm_angle, color, spin in ((timer * 0.09, cfg.COLOR_ORANGE, 0.10),
                                       (math.pi + timer * 0.07, cfg.COLOR_PURPLE, -0.075)):
            b = create_bullet_angle(boss.x, boss.y, arm_angle, 0.0,
                                    Bullet.TYPE_KNIFE, radius=2.5, color=color)
            b.manager = bullet_manager
            b.orbit_center = center
            b.orbit_radius = 24
            b.orbit_angle = arm_angle
            b.orbit_speed = spin
            b.orbit_grow = 0.55
            b.orbit_break = 130
            b.orbit_break_speed = 2.6
            b.lifetime = 520
            bullet_manager.add_enemy_bullet(b)

    # 织网飞针：箭弹向外飞出后急停，停在“网结点”时朝玩家爆出丝线弹
    # 每根飞针同时再发一根左右（横向）运动方向相反的镜像飞针，织成交叉蛛网
    if timer % 110 == 0:
        base = math.pi / 2 + math.sin(timer * 0.007) * 0.9
        for i in range(7):
            angle = base + (i - 3) * 0.28
            for a, color in ((angle, cfg.COLOR_GREEN), (math.pi - angle, (0, 200, 180))):
                b = create_bullet_angle(boss.x, boss.y, a, 3.3,
                                        Bullet.TYPE_ARROW, radius=3, color=color)
                b.manager = bullet_manager
                b.brake = 0.034
                b.split_spec = {
                    "timer": 100,
                    "aimed": True,
                    "count": 5,
                    "spread": 0.26,
                    "speed": 2.8,
                    "type": Bullet.TYPE_RICE,
                    "radius": 2.5,
                    "color": cfg.COLOR_YELLOW,
                }
                bullet_manager.add_enemy_bullet(b)

def spell_dark_queen_soul(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """魂符「Dark Queen's Soul」：追魂（魂环+追魂大玉）→ 魂飞魄散（分裂刀弹雨+飘魂）"""
    if timer < 360:
        # 阶段1「追魂」：魂环绕体公转外扩；追魂大玉有限转向追踪并逐渐加速
        if timer % 80 == 0:
            for i in range(8):
                angle = i * math.pi * 2 / 8 + timer * 0.03
                b = create_bullet_angle(boss.x, boss.y, angle, 0.0,
                                        Bullet.TYPE_BIG, radius=5,
                                        color=cfg.COLOR_PURPLE if i % 2 == 0 else cfg.COLOR_RED)
                b.manager = bullet_manager
                b.orbit_center = (boss.x, boss.y)
                b.orbit_radius = 30
                b.orbit_angle = angle
                b.orbit_speed = 0.06
                b.orbit_grow = 0.6
                b.orbit_break = 150
                b.orbit_break_speed = 2.0
                b.lifetime = 700
                bullet_manager.add_enemy_bullet(b)
        if timer % 30 == 0:
            b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 1.7,
                                    Bullet.TYPE_BIG, radius=5, color=(150, 60, 230))
            b.manager = bullet_manager
            b.steer_speed = 0.022
            b.accel = 0.009
            b.lifetime = 420
            bullet_manager.add_enemy_bullet(b)
    else:
        # 阶段2「魂飞魄散」：大玉急停后分裂出追身刀弹；白色飘魂游荡全场
        if timer % 80 == 0:
            base = math.atan2(player_y - boss.y, player_x - boss.x)
            for i in range(6):
                angle = base + (i - 2.5) * 0.22
                b = create_bullet_angle(boss.x, boss.y, angle, 2.7,
                                        Bullet.TYPE_BIG, radius=5, color=(150, 60, 230))
                b.manager = bullet_manager
                b.brake = 0.03
                b.split_spec = {
                    "timer": 90,
                    "aimed": True,
                    "count": 6,
                    "spread": 0.32,
                    "speed": 3.1,
                    "type": Bullet.TYPE_KNIFE,
                    "radius": 2.5,
                    "color": cfg.COLOR_WHITE,
                }
                bullet_manager.add_enemy_bullet(b)
        if timer % 9 == 0:
            angle = random.uniform(0, math.pi * 2)
            b = create_bullet_angle(boss.x, boss.y, angle, random.uniform(1.3, 2.0),
                                    Bullet.TYPE_KNIFE, radius=2.0, color=cfg.COLOR_WHITE)
            b.manager = bullet_manager
            b.wobble_amp = 3.0
            b.wobble_freq = 0.18
            b.wobble_phase = random.uniform(0, math.pi * 2)
            b.lifetime = 320
            bullet_manager.add_enemy_bullet(b)
        if timer % 120 == 0:
            for i in range(6):
                angle = i * math.pi * 2 / 6 + timer * 0.04
                b = create_bullet_angle(boss.x, boss.y, angle, 0.0,
                                        Bullet.TYPE_BIG, radius=5, color=(150, 60, 230))
                b.manager = bullet_manager
                b.orbit_center = (boss.x, boss.y)
                b.orbit_radius = 26
                b.orbit_angle = angle
                b.orbit_speed = 0.06
                b.orbit_grow = 0.55
                b.orbit_break = 140
                b.orbit_break_speed = 1.8
                b.lifetime = 600
                bullet_manager.add_enemy_bullet(b)


# --- 第2面道中Boss：末地石守护者 ---
# 石符「Immobile Protector's Wraith」：参考末地素材（末地石 / 末影珍珠 / 召唤之眼 / 紫晶 / 黑曜石柱）
_STONE_COLOR = (198, 186, 142)      # 末地石米黄
_STONE_DIM = (152, 140, 106)        # 暗末地石
_TEAL_COLOR = (86, 206, 200)        # 末影珍珠青
_PURPLE_COLOR = (168, 96, 232)      # 紫晶碎片
_ROSE_COLOR = (226, 104, 168)       # 末地石玫瑰
_PALE_COLOR = (238, 232, 208)       # 怨灵苍白


def _protector_ring_burst(boss, bullet_manager, timer, count=20, speed=1.5, color=_STONE_COLOR):
    """开符/冲击宣告：整圈石弹扩散环"""
    base = timer * 0.03
    for i in range(count):
        b = create_bullet_angle(boss.x, boss.y, base + i * math.tau / count, speed,
                                Bullet.TYPE_RICE, radius=2.4, color=color)
        b.manager = bullet_manager
        b.shock_link = True
        b.lifetime = 400
        bullet_manager.add_enemy_bullet(b)


def _protector_build_barriers(boss):
    """在场地中铺开固定石柱结界：一圈 8 根石柱，位置固定不变（固定弹墙的锚点）"""
    cx = cfg.BATTLE_AREA_WIDTH / 2
    cy = 175
    rx, ry = 216, 156
    for i in range(8):
        a = i * math.tau / 8
        x = max(30, min(cfg.BATTLE_AREA_WIDTH - 30, cx + math.cos(a) * rx))
        y = max(30, min(cfg.BATTLE_AREA_HEIGHT - 30, cy + math.sin(a) * ry))
        boss.protector_barriers.append({
            "x": x, "y": y, "w": 26, "h": 34, "seed": i * 1.7,
        })


def _protector_rock_walls(bullet_manager, boss, timer, phase):
    """固定石质结界：石柱持续吐出排列严密的岩石弹（固定弹墙）"""
    if not boss.protector_barriers:
        _protector_build_barriers(boss)
    if timer % 44 == 0:
        for p in boss.protector_barriers:
            dir_ang = math.atan2(p["y"] - boss.y, p["x"] - boss.x)
            base = dir_ang + math.sin(timer * 0.02 + p["seed"]) * 0.16
            for k in range(2):
                b = create_bullet_angle(p["x"], p["y"], base + (k - 0.5) * 0.30, 1.7,
                                        Bullet.TYPE_RICE, radius=2.3,
                                        color=_STONE_COLOR if k == 0 else _PALE_COLOR)
                b.manager = bullet_manager
                b.shock_link = True
                b.lifetime = 280
                bullet_manager.add_enemy_bullet(b)


def _protector_core_rings(bullet_manager, boss, timer, phase):
    """守护者核心石环：绕核心缓慢旋转的岩石环，随震荡冲击规律性扩散/收缩"""
    if timer % 62 == 0:
        n = 10 + phase
        ring_r = 34 + (timer // 62) % 4 * 12
        base = timer * 0.02
        for i in range(n):
            ang = base + i * math.tau / n
            b = create_bullet_angle(boss.x, boss.y, ang, 0.0,
                                    Bullet.TYPE_BIG, radius=3.4,
                                    color=_STONE_COLOR if i % 2 == 0 else _STONE_DIM)
            b.manager = bullet_manager
            b.orbit_center = (boss.x, boss.y)
            b.orbit_radius = ring_r
            b.orbit_angle = ang
            b.orbit_speed = 0.014
            b.orbit_grow = 0.0
            b.shock_link = True
            b.lifetime = 440
            bullet_manager.add_enemy_bullet(b)


def _protector_giant_rocks(bullet_manager, boss, timer, phase):
    """巨大石块：仅从左右两侧缓慢推进，抵达特定位置碎裂成小型碎石（层层防御阵列）"""
    period = 100
    if timer % period != 0:
        return
    wave = timer // period
    for side in (2, 3):
        for j in range(2):
            slot = (wave + j) % 3
            if side == 2:    # 左边 → 向右推进
                y = 90 + 120 * slot
                x0, y0, ang = -24, y, 0.0
            else:            # 右边 → 向左推进
                y = 90 + 120 * slot
                x0, y0, ang = cfg.BATTLE_AREA_WIDTH + 24, y, math.pi
            spd = 1.0 + (wave % 3) * 0.10
            depth = 130 + slot * 42
            b = create_bullet_angle(x0, y0, ang, spd, Bullet.TYPE_BIG, radius=6,
                                    color=_STONE_DIM)
            b.manager = bullet_manager
            b.split_spec = {"timer": max(40, int(depth / spd)), "ring": True,
                            "count": 6, "speed": 1.8,
                            "type": Bullet.TYPE_RICE, "radius": 2.2,
                            "color": _STONE_COLOR}
            b.lifetime = 720
            bullet_manager.add_enemy_bullet(b)


def _protector_shockwave(boss, bullet_manager, timer, phase):
    """守护者核心震荡：周期性范围冲击，令岩石弹幕规律性扩散与收缩"""
    if phase == 0:
        return
    period = 170 if phase == 1 else 130
    if timer % period != 0:
        return
    boss.protector_shock = {"life": 44, "max_life": 44}
    boss.protector_pulse_dir *= -1
    pull = boss.protector_pulse_dir
    # 冲击波本身也放出一圈石弹
    _protector_ring_burst(boss, bullet_manager, timer, count=14,
                          speed=1.5, color=_PALE_COLOR)
    for eb in bullet_manager.enemy_bullets:
        if not getattr(eb, "shock_link", False):
            continue
        dx = eb.x - boss.x
        dy = eb.y - boss.y
        dist = math.hypot(dx, dy)
        if dist < 1:
            continue
        ux, uy = dx / dist, dy / dist
        if eb.orbit_center is not None:
            if pull > 0:
                eb.orbit_grow = 0.5
            else:
                eb.orbit_grow = -0.45 if eb.orbit_radius > 34 else 0.35
        else:
            eb.vx += ux * (0.9 if pull > 0 else -0.9)
            eb.vy += uy * (0.9 if pull > 0 else -0.9)


def spell_immobile_protector_wraith(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """石符「Immobile Protector's Wraith」：不动守护者之怒

    自身化为坚不可摧的岩石堡垒，在场地中展开固定石质结界，持续向外释放
    排列严密的岩石弹幕；巨大石块弹以缓慢但不可阻挡的轨迹从四周推进，并在
    特定位置碎裂成大量小型碎石，形成层层叠加的防御阵列；随着符卡推进，
    守护者核心释放范围性的震荡冲击，使岩石弹幕产生规律性的扩散与收缩。
    """
    phase = 0 if timer < 260 else (1 if timer < 520 else 2)
    boss.protector_fortress = True

    # 震荡冲击环动画推进
    if boss.protector_shock is not None:
        boss.protector_shock["life"] -= 1
        if boss.protector_shock["life"] <= 0:
            boss.protector_shock = None

    # 不动堡垒：仅轻微浮沉与小幅平移
    boss.target_y = 118 + math.sin(timer * 0.008) * 6
    if timer % 300 == 0:
        boss.target_x = cfg.BATTLE_AREA_WIDTH / 2 + random.uniform(-40, 40)

    # 开符宣告：整圈石弹
    if timer == 1:
        _protector_ring_burst(boss, bullet_manager, timer, count=24, speed=1.6)

    # 固定弹墙：石柱结界持续释放排列严密的岩石弹
    _protector_rock_walls(bullet_manager, boss, timer, phase)

    # 守护者核心石环：绕核心旋转，随震荡扩散/收缩
    _protector_core_rings(bullet_manager, boss, timer, phase)

    # 巨大石块：从四周缓慢推进，碎裂成碎石
    _protector_giant_rocks(bullet_manager, boss, timer, phase)

    # 震荡冲击：令岩石弹幕规律性扩散与收缩（符卡推进后开启）
    _protector_shockwave(boss, bullet_manager, timer, phase)

    # 紫晶追身大玉：缓慢但持续地施压
    if timer % 170 == 0:
        b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 1.6,
                                Bullet.TYPE_BIG, radius=4, color=_PURPLE_COLOR)
        b.manager = bullet_manager
        b.steer_speed = 0.008
        b.lifetime = 600
        bullet_manager.add_enemy_bullet(b)

# --- 二面关底Boss：末影龙 Ender Dragon ---
# 燃符「Fireball Barrage」/ 闪符「Non-Directional Lightning」/ 龙符「One with the Dragons」
# Last Spell：超符「Superiority」（Bomb 禁用、Miss 强制结束不损残机）

_DRAGON_FIRE = (255, 140, 48)        # 龙息火焰
_DRAGON_FIRE_HOT = (255, 92, 28)     # 炽热火焰
_DRAGON_FIRE_PALE = (255, 214, 120)  # 苍白火焰
_LIGHT_WARN = (150, 200, 255)        # 预警淡蓝
_LIGHT_BOLT = (214, 238, 255)        # 闪电白
_LIGHT_CYAN = (140, 206, 255)        # 电弧青
_DRAGON_PURPLE = (176, 108, 240)     # 龙魂紫
_DRAGON_DEEP = (128, 64, 200)        # 深紫
_DRAGON_PALE = (232, 200, 255)       # 龙辉淡紫
_TEAL_DRAGON = (96, 216, 208)        # 末影珍珠青
_SUPER_GOLD = (255, 220, 120)        # 上位龙金
_SUPER_GOLD_DIM = (255, 186, 72)     # 暗金
_SUPER_WHITE = (255, 252, 230)       # 审判白


def _non_spell_dragon_breath(boss, bullet_manager, timer, player_x=0, player_y=0):
    """非符1 龙息：自机狙扇形龙息（加速）+ 周期性龙焰环"""
    # 龙息扇形：三连发自机狙箭弹，带轻微随机散布，命中前加速
    if timer % 22 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for i in range(3):
            offset = (i - 1) * 0.13 + random.uniform(-0.03, 0.03)
            b = create_bullet_angle(boss.x, boss.y, base + offset, 2.2 + i * 0.25,
                                    Bullet.TYPE_ARROW, radius=3, color=_DRAGON_FIRE)
            b.manager = bullet_manager
            b.accel = 0.012
            b.lifetime = 420
            bullet_manager.add_enemy_bullet(b)
    # 龙焰环：交错旋转的米弹环
    if timer % 110 == 0:
        base = timer * 0.02
        for i in range(6):
            angle = base + i * math.tau / 6
            b = create_bullet_angle(boss.x, boss.y, angle, 1.5,
                                    Bullet.TYPE_RICE, radius=2.5,
                                    color=_DRAGON_FIRE_PALE if i % 3 == 0 else _DRAGON_FIRE)
            bullet_manager.add_enemy_bullet(b)
    # 偶尔小幅位移
    if timer % 220 == 0:
        boss.target_x = max(90, min(cfg.BATTLE_AREA_WIDTH - 90,
                                    boss.x + random.uniform(-80, 80)))


def _non_spell_ender_pearl(boss, bullet_manager, timer, player_x=0, player_y=0):
    """非符2 末影珍珠：有限追踪珍珠 + 珍珠环分裂 + 随机闪现位移"""
    # 追踪珍珠：末影珍珠大玉，缓慢转向玩家并加速
    if timer % 40 == 0:
        b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 1.6,
                                Bullet.TYPE_BIG, radius=4.5, color=_TEAL_DRAGON)
        b.manager = bullet_manager
        b.steer_speed = 0.014
        b.accel = 0.006
        b.lifetime = 460
        bullet_manager.add_enemy_bullet(b)
    # 珍珠环：一圈米弹扩散后急停，再朝玩家爆出刀弹
    if timer % 150 == 0:
        base = random.uniform(0, math.tau)
        for i in range(5):
            b = create_bullet_angle(boss.x, boss.y, base + i * math.tau / 5, 2.4,
                                    Bullet.TYPE_RICE, radius=2.5, color=_TEAL_DRAGON)
            b.manager = bullet_manager
            b.brake = 0.02
            b.split_spec = {"timer": 130, "aimed": True, "count": 2, "spread": 0.24,
                            "speed": 3.0, "type": Bullet.TYPE_KNIFE, "radius": 2.5,
                            "color": _LIGHT_CYAN}
            b.lifetime = 460
            bullet_manager.add_enemy_bullet(b)
    # 闪现：Boss 随机瞬移（非符也带「非定向」的味道）
    if timer % 200 == 0:
        boss.target_x = random.uniform(90, cfg.BATTLE_AREA_WIDTH - 90)
        boss.target_y = random.uniform(90, 190)


def spell_fireball_barrage(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """燃符「Fireball Barrage」：空中轰炸——扇形固定火球阵定点爆裂 + 绕场火焰封锁带

    两幕循环（每幕 6 秒，密度随轮次递增）：
    幕1「轰炸阵列」：末影龙在屏幕上方蓄力后，持续向下释放扇形固定火球阵；
        火球沿固定轨迹推进，在指定半径定点爆裂为多方向小火弹，
        形成「第一层躲弹道、第二层预判爆点」的复合弹幕。
    幕2「绕场封锁」：末影龙绕场巡航，移动路径上留下横向/斜向火焰弹幕带，
        周期性封锁空间，迫使玩家寻找安全区域。
    """
    cycle = timer % 720
    phase = cycle // 360
    rounds = timer // 720               # 轮次：随轮次提高压力
    release_gap = max(30, 45 - rounds * 6)

    if phase == 0:
        # ---- 幕1：蓄力轰炸阵列 ----
        if cycle < 50:
            # 蓄力：回到屏幕上方中央
            boss.move_speed = 2.2
            boss.target_x = cfg.BATTLE_AREA_WIDTH / 2
            boss.target_y = 62 + math.sin(cycle * 0.05) * 4
            return
        # 悬停轰炸位
        boss.move_speed = 1.4
        boss.target_x = cfg.BATTLE_AREA_WIDTH / 2
        boss.target_y = 64 + math.sin(timer * 0.05) * 6

        # 主阵列：扇形固定火球阵（不瞄玩家），固定轨迹推进、交错半径定点爆裂
        if (cycle - 50) % release_gap == 0:
            fan_count = 6
            spread = 1.15
            for i in range(fan_count):
                ang = math.pi / 2 + (i - (fan_count - 1) / 2) * (spread / fan_count)
                dist = 120 + (i % 3) * 60      # 近/中/远三组交错爆点，形成错落网格
                speed = random.uniform(2.1, 2.6)
                b = create_bullet_angle(boss.x, boss.y, ang, speed,
                                        Bullet.TYPE_BIG, radius=5,
                                        color=_DRAGON_FIRE)
                b.manager = bullet_manager
                b.split_spec = {
                    "timer": max(20, int(dist / speed)),
                    "base_angle": ang,
                    "count": 5,
                    "spread": math.tau / 8,
                    "speed": 2.3,
                    "type": Bullet.TYPE_RICE,
                    "radius": 2.2,
                    "color": _DRAGON_FIRE_HOT,
                }
                b.lifetime = 520
                bullet_manager.add_enemy_bullet(b)

        # 侧翼骚扰：偶发斜向火球填补阵列缝隙（远距定点爆裂）
        if (cycle - 50) % 60 == 0:
            for offset in (-0.85, 0.85):
                ang = math.pi / 2 + offset
                b = create_bullet_angle(boss.x, boss.y, ang, 2.8,
                                        Bullet.TYPE_BIG, radius=4,
                                        color=_DRAGON_FIRE_PALE)
                b.manager = bullet_manager
                b.split_spec = {
                    "timer": 110,
                    "base_angle": ang,
                    "count": 3,
                    "spread": 0.5,
                    "speed": 2.6,
                    "type": Bullet.TYPE_KNIFE,
                    "radius": 2.2,
                    "color": _DRAGON_FIRE,
                }
                b.lifetime = 480
                bullet_manager.add_enemy_bullet(b)
    else:
        # ---- 幕2：绕场巡航 + 火焰封锁带 ----
        t1 = cycle - 360
        boss.move_speed = 3.4
        # 之字形巡航路径（六段航点，每段 60 帧）
        waypoints = [
            (96, 84),
            (cfg.BATTLE_AREA_WIDTH - 96, 84),
            (cfg.BATTLE_AREA_WIDTH - 120, 200),
            (120, 200),
            (96, 130),
            (cfg.BATTLE_AREA_WIDTH - 96, 130),
        ]
        wp = waypoints[(t1 // 60) % len(waypoints)]
        boss.target_x, boss.target_y = wp

        # 移动路径上留下火焰弹幕带（缓慢漂移，5 秒后消散）
        if t1 % 5 == 0:
            drift = random.uniform(0, math.tau)
            b = create_bullet_angle(boss.x, boss.y, drift, 0.45,
                                    Bullet.TYPE_RICE, radius=2.5,
                                    color=_DRAGON_FIRE if t1 % 10 == 0 else _DRAGON_FIRE_PALE)
            b.manager = bullet_manager
            b.lifetime = 300
            bullet_manager.add_enemy_bullet(b)

        # 横向封锁线：随机高度整排火球缓缓下压，定点爆裂成“火墙”
        if t1 % 100 == 20:
            line_y = random.uniform(120, 260)
            for i in range(7):
                b = create_bullet_angle(30 + i * (cfg.BATTLE_AREA_WIDTH - 60) / 6,
                                        line_y, math.pi / 2, 1.5,
                                        Bullet.TYPE_BIG, radius=4,
                                        color=_DRAGON_FIRE_HOT if i % 2 == 0 else _DRAGON_FIRE)
                b.manager = bullet_manager
                b.split_spec = {
                    "timer": 110,
                    "base_angle": math.pi / 2,
                    "count": 4,
                    "spread": 0.55,
                    "speed": 2.4,
                    "type": Bullet.TYPE_RICE,
                    "radius": 2.0,
                    "color": _DRAGON_FIRE_PALE,
                }
                b.lifetime = 460
                bullet_manager.add_enemy_bullet(b)

def _lightning_wave_positions(rng, count):
    """伪随机生成一拨雷击点：左右均衡 + 上下拉开，围成面积尽量大"""
    sides = [0] * (count // 2) + [1] * (count - count // 2)
    rng.shuffle(sides)
    # 垂直锚点从底部到顶部均匀铺开，让雷击点围成的多边形尽量外扩
    anchors = [640.0 - (640.0 - 170.0) * (i / max(1, count - 1)) for i in range(count)]
    rng.shuffle(anchors)
    pts = []
    for side, ay in zip(sides, anchors):
        if side == 0:
            x = rng.uniform(70, 200)
        else:
            x = rng.uniform(cfg.BATTLE_AREA_WIDTH - 200, cfg.BATTLE_AREA_WIDTH - 70)
        y = ay + rng.uniform(-25, 25)
        pts.append((x, y))
    return pts


def _lightning_node_marker(bullet_manager, x, y, lifetime):
    """雷击点圆形提示：作为电网节点的期间持续显示"""
    b = create_bullet_angle(x, y, 0, 0, Bullet.TYPE_CIRCLE, radius=6, color=_LIGHT_WARN)
    b.manager = bullet_manager
    b.harmless = True
    b.lifetime = lifetime
    bullet_manager.add_enemy_bullet(b)
    b2 = create_bullet_angle(x, y, 0, 0, Bullet.TYPE_CIRCLE, radius=2.5, color=_LIGHT_BOLT)
    b2.manager = bullet_manager
    b2.harmless = True
    b2.lifetime = lifetime
    bullet_manager.add_enemy_bullet(b2)


def _lightning_segment(bullet_manager, x0, y0, x1, y1):
    """两点之间的电流连接线：一条光束线 + 沿线稀疏圆点（判定节点）"""
    dx = x1 - x0
    dy = y1 - y0
    dist = math.hypot(dx, dy)
    if dist < 24:
        return
    ang = math.atan2(dy, dx)
    # 光束线：从起点到终点的一条直线（视觉连接）
    beam = create_bullet_angle(x0, y0, ang, 0.0,
                               Bullet.TYPE_BEAM, radius=3, color=_LIGHT_CYAN)
    beam.manager = bullet_manager
    beam.angle = ang          # 静止弹的 angle 不会由速度初始化，手动指定
    beam.beam_length = dist
    beam.sprite_slot = "s12"  # 雷击射线：etama.png 第一行「射线」图案（浅蓝，白芯保留）
    beam.lifetime = 90    # 电网短暂存续后消散，留出安全间隙
    bullet_manager.add_enemy_bullet(beam)
    # 沿线稀疏圆点：判定点 + 网格节点感
    step = 62
    n = max(1, int(dist / step))
    for i in range(1, n):
        t = i / float(n)
        b = create_bullet_angle(x0 + dx * t, y0 + dy * t, 0.0, 0.0,
                                Bullet.TYPE_CIRCLE, radius=2.5,
                                color=_LIGHT_BOLT)
        b.manager = bullet_manager
        b.lifetime = 90
        bullet_manager.add_enemy_bullet(b)


def spell_non_directional_lightning(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """闪符「Non-Directional Lightning」：预警落雷 + 环形电弧 + 电流网格封锁

    每 120 帧一轮雷击波次（雷击点数量随轮次递增）：
      1) 预警：在场地内标定多个雷击预兆点（大圆标记 + 前摇脉冲闪烁）；
      2) 落雷：预兆点产生双层环形扩散电弧（分裂刀弹更大、更少、更慢）；
      3) 电网：本波所有雷击点两两相连，覆盖大半场地；落点用完即弃、
         不再跨波复用，电网随波次消散留出安全间隙。
    同一轮内「预警标记」与「落雷坐标」由同一随机种子生成，保证预兆与落点一致。
    """
    react_t = max(0, timer - 60)   # 开场 60 帧缓冲：符卡开始后先给反应时间再落雷
    cycle = react_t % 720
    wave = cycle // 120            # 本轮内波次序号
    local = cycle % 120
    wave_no = react_t // 120       # 全局波次（决定雷击密度）

    # 末影龙悬浮游走，释放能量
    boss.target_y = 90 + math.sin(timer * 0.013) * 12
    if timer % 200 == 0:
        boss.target_x = random.uniform(100, cfg.BATTLE_AREA_WIDTH - 100)

    # 本波雷击点（确定性种子：预警与落雷使用同一坐标）
    strike_count = 2 + min(3, wave_no // 2)   # 电球最多 5 个：2、2、3、3、4、4、5、5、5...
    rng = random.Random(7000 + wave_no)
    positions = _lightning_wave_positions(rng, strike_count)

    if local == 12:
        # ---- 预警：标定雷击预兆点（大圆标记 + 前摇闪烁）----
        for (x, y) in positions:
            # 圆形提示点：作为网格节点一直显示到本波电网消散
            _lightning_node_marker(bullet_manager, x, y, 156)
    elif 16 <= local < 72 and local % 8 == 4:
        # ---- 前摇闪烁：落雷前反复脉冲提示 ----
        for (x, y) in positions:
            p = create_bullet_angle(x, y, 0, 0, Bullet.TYPE_CIRCLE, radius=7.5,
                                    color=_LIGHT_WARN)
            p.manager = bullet_manager
            p.harmless = True
            p.lifetime = 6
            bullet_manager.add_enemy_bullet(p)
    elif local == 72:
        # ---- 落雷：落点环形扩散电弧 ----
        for (x, y) in positions:
            # 落点环形电弧：双层固定扩散
            for ring_i, (n, spd, col) in enumerate(((5, 1.9, _LIGHT_BOLT), (3, 2.8, _LIGHT_CYAN))):
                base = rng.uniform(0, math.tau)
                for i in range(n):
                    ang = base + i * math.tau / n
                    b2 = create_bullet_angle(x, y, ang, spd,
                                             Bullet.TYPE_RICE, radius=2.5, color=col)
                    b2.manager = bullet_manager
                    if i % 4 == 0:
                        # 分裂刀弹：更大、更少、更慢，便于反应
                        b2.split_spec = {"timer": 130, "base_angle": ang, "count": 2,
                                         "spread": 0.30, "speed": 1.2,
                                         "type": Bullet.TYPE_KNIFE, "radius": 3.0,
                                         "color": _LIGHT_CYAN if ring_i == 0 else _LIGHT_BOLT}
                    b2.lifetime = 300
                    bullet_manager.add_enemy_bullet(b2)
    elif local == 78:
        # ---- 电网：本波所有雷击点两两相连，落点用完即弃、不再跨波复用 ----
        for i in range(strike_count):
            for j in range(i + 1, strike_count):
                _lightning_segment(bullet_manager, positions[i][0], positions[i][1],
                                   positions[j][0], positions[j][1])

def _dragon_phantom_trajectories(boss, timer, count):
    """幻影龙固定轨迹：偶数序椭圆环绕本体，奇数序正弦横穿场地"""
    w = cfg.BATTLE_AREA_WIDTH
    h = cfg.BATTLE_AREA_HEIGHT
    phantoms = []
    for i in range(count):
        if i % 2 == 0:
            speed = 0.020 + 0.004 * (i // 2)
            phase = i * math.tau / max(2, count)
            rx = 168 + (i % 3) * 28
            ry = 118 + (i % 2) * 32
            ang = timer * speed + phase
            x = boss.x + math.cos(ang) * rx
            y = boss.y + math.sin(ang * 0.85) * ry
            vx = -math.sin(ang) * speed * rx
            vy = math.cos(ang * 0.85) * speed * 0.85 * ry
            move_ang = math.atan2(vy, vx)
        else:
            dir_sign = 1 if (i % 4) == 1 else -1
            progress = (timer * 0.010 + (i // 2) * 0.31) % 1.0
            if dir_sign > 0:
                x = -34 + progress * (w + 68)
            else:
                x = w + 34 - progress * (w + 68)
            base_y = 100 + ((i // 2) % 3) * 58
            y = base_y + math.sin(timer * 0.016 + i * 1.9) * 52
            vx = dir_sign * (w + 68) * 0.010
            vy = math.cos(timer * 0.016 + i * 1.9) * 0.016 * 52
            move_ang = math.atan2(vy, vx)
        phantoms.append({"x": x, "y": y, "angle": move_ang, "flip": math.cos(move_ang) < 0})
    return phantoms


def _phantom_wing_spread(bullet_manager, x, y, timer, color):
    """龙翼状扇形：左右两翼各一簇固定箭弹，呈翼展形"""
    if timer % 95 == 0:
        tilt = math.sin(timer * 0.012) * 0.45
        for side in (-1, 1):
            base = side * (math.pi / 2) + tilt
            for k in range(3):
                ang = base + (k - 1.5) * 0.20
                b = create_bullet_angle(x, y, ang, 1.55 + k * 0.22,
                                        Bullet.TYPE_ARROW, radius=2.6, color=color)
                b.manager = bullet_manager
                b.lifetime = 430
                bullet_manager.add_enemy_bullet(b)


def _phantom_scale_arc(bullet_manager, x, y, timer, color):
    """鳞片状：多层错位短弧米弹，层层叠叠如龙鳞"""
    if timer % 70 == 0:
        for layer in range(2):
            for i in range(4):
                ang = timer * 0.045 + layer * 0.55 + i * math.tau / 4 + (layer % 2) * 0.18
                b = create_bullet_angle(x, y, ang, 1.0 + layer * 0.28,
                                        Bullet.TYPE_RICE, radius=2.2, color=color)
                b.manager = bullet_manager
                b.lifetime = 300
                bullet_manager.add_enemy_bullet(b)


def _phantom_breath(bullet_manager, x, y, player_x, player_y, timer, color):
    """交错龙息：窄幅自机狙连喷，与相邻幻影错开时相"""
    if timer % 55 == 0:
        base = math.atan2(player_y - y, player_x - x)
        for k in range(2):
            b = create_bullet_angle(x, y, base + (k - 0.5) * 0.12, 2.3 + k * 0.12,
                                    Bullet.TYPE_KNIFE, radius=2.4, color=color)
            b.manager = bullet_manager
            b.lifetime = 380
            bullet_manager.add_enemy_bullet(b)


def _dragon_main_ring(bullet_manager, boss, timer, color, speed=1.5, count=14):
    """本体旋转弹环：基角随计时缓慢旋转，逐环封堵"""
    if timer % 165 == 0:
        base = timer * 0.02
        for i in range(count):
            ang = base + i * math.tau / count
            b = create_bullet_angle(boss.x, boss.y, ang, speed,
                                    Bullet.TYPE_RICE, radius=2.4, color=color)
            b.manager = bullet_manager
            b.lifetime = 420
            bullet_manager.add_enemy_bullet(b)


def spell_one_with_the_dragons(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """龙符「One with the Dragons」：万龙共鸣——幻影龙群环绕/穿越 + 多层固定弹阵

    幻影龙数量随战斗推进增加（2 → 5）：偶数序环绕本体、奇数序横穿场地，
    持续释放龙翼扇形 / 鳞片短弧 / 交错龙息；本体与幻影龙同步以旋转弹环和
    大范围扩散弹封锁玩家空间，营造被龙之力量包围的压迫感。
    """
    cycle = timer % 720
    phase = cycle // 240
    count = min(4, 2 + timer // 340)
    phantoms = _dragon_phantom_trajectories(boss, timer, count)
    boss.phantom_dragons = phantoms

    # 本体游走
    boss.target_y = 110 + math.sin(timer * 0.010) * 14
    if timer % 200 == 0:
        boss.target_x = random.uniform(120, cfg.BATTLE_AREA_WIDTH - 120)

    for i, ph in enumerate(phantoms):
        x, y = ph["x"], ph["y"]
        color = _DRAGON_PALE if i % 2 == 0 else _DRAGON_PURPLE
        if phase == 0:
            _phantom_wing_spread(bullet_manager, x, y, timer + i * 13, color)
        elif phase == 1:
            _phantom_scale_arc(bullet_manager, x, y, timer + i * 17, color)
            if (timer // 26 + i) % 2 == 0:
                _phantom_breath(bullet_manager, x, y, player_x, player_y,
                                timer + i * 9, _TEAL_DRAGON)
        else:
            _phantom_scale_arc(bullet_manager, x, y, timer + i * 17, color)
            if (timer // 26 + i) % 2 == 0:
                _phantom_breath(bullet_manager, x, y, player_x, player_y,
                                timer + i * 9, _TEAL_DRAGON)
            if (timer + i * 41) % 150 == 0:
                base = (timer * 0.03) % math.tau
                for k in range(11):
                    ang = base + k * math.tau / 11
                    b = create_bullet_angle(x, y, ang, 1.25,
                                            Bullet.TYPE_CIRCLE, radius=2.6, color=color)
                    b.manager = bullet_manager
                    b.lifetime = 360
                    bullet_manager.add_enemy_bullet(b)

    # 本体攻击：随阶段逐步加密
    if phase == 0:
        _dragon_main_ring(bullet_manager, boss, timer, _DRAGON_DEEP, speed=1.25, count=7)
    elif phase == 1:
        _dragon_main_ring(bullet_manager, boss, timer, _DRAGON_PURPLE, speed=1.4, count=9)
        if cycle % 105 == 0:
            b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 2.0,
                                    Bullet.TYPE_BIG, radius=4, color=_DRAGON_DEEP)
            b.manager = bullet_manager
            b.steer_speed = 0.010
            b.lifetime = 420
            bullet_manager.add_enemy_bullet(b)
    else:
        _dragon_main_ring(bullet_manager, boss, timer, _TEAL_DRAGON, speed=1.55, count=11)
        if cycle % 70 == 0:
            base = cycle * 0.05
            for k in range(7):
                ang = base + k * math.tau / 7
                b = create_bullet_angle(boss.x, boss.y, ang, 1.8,
                                        Bullet.TYPE_ARROW, radius=2.8,
                                        color=_DRAGON_DEEP if k % 2 == 0 else _DRAGON_PALE)
                b.manager = bullet_manager
                b.lifetime = 400
                bullet_manager.add_enemy_bullet(b)



def _superior_core_rings(bullet_manager, boss, timer, phase, wave, cycle_dir):
    """金色龙之核心：环状固定弹——鳞片弹绕核心旋转，随推进换向/变速"""
    if timer % 52 == 0:
        n = min(16, 10 + wave)
        ring_r = 44 + (timer // 44) % 3 * 15
        base = timer * 0.018
        rot_dir = 1.0 if cycle_dir == 0 else -1.0
        # phase 2：旋转方向每隔几环反转，排列错位
        if phase == 2 and (timer // 132) % 2 == 1:
            rot_dir = -rot_dir
        for i in range(n):
            ang = base + i * math.tau / n + (0.5 if phase == 2 and i % 2 else 0.0)
            b = create_bullet_angle(boss.x, boss.y, ang, 0.0,
                                    Bullet.TYPE_RICE, radius=2.6,
                                    color=_SUPER_GOLD if i % 2 == 0 else _SUPER_GOLD_DIM)
            b.manager = bullet_manager
            b.orbit_center = (boss.x, boss.y)
            b.orbit_radius = ring_r
            b.orbit_angle = ang
            b.orbit_speed = 0.012 * rot_dir
            b.lifetime = 460
            bullet_manager.add_enemy_bullet(b)


def _superior_sym_expand(bullet_manager, boss, timer, phase, wave, cycle_dir):
    """对称展开弹：从核心对称外扩的鳞片环，挣脱后沿切线直飞"""
    if timer % 150 == 0:
        n = 8 if phase == 0 else 12
        base = timer * 0.028 * (1.0 if cycle_dir == 0 else -1.0)
        for i in range(n):
            ang = base + i * math.tau / n
            b = create_bullet_angle(boss.x, boss.y, ang, 0.0,
                                    Bullet.TYPE_KNIFE, radius=2.8,
                                    color=_SUPER_WHITE if i % 2 == 0 else _SUPER_GOLD)
            b.manager = bullet_manager
            b.orbit_center = (boss.x, boss.y)
            b.orbit_radius = 22
            b.orbit_angle = ang
            b.orbit_grow = 0.95
            b.orbit_break = 130
            b.orbit_break_speed = 2.1 + min(1.2, wave * 0.06)
            b.lifetime = 460
            bullet_manager.add_enemy_bullet(b)


def _superior_spawn_circles(boss, timer):
    """周期性生成巨大的黄金魔法阵（登记到 boss.superior_circles，由绘制/喷射驱动）"""
    if timer < 240:
        return
    period = 300 if timer < 480 else 230
    if timer % period != 0:
        return
    anchors = [
        (150, 140),
        (cfg.BATTLE_AREA_WIDTH - 150, 140),
        (150, cfg.BATTLE_AREA_HEIGHT - 160),
        (cfg.BATTLE_AREA_WIDTH - 150, cfg.BATTLE_AREA_HEIGHT - 160),
    ]
    available = [p for p in anchors
                 if all(math.hypot(p[0] - c["x"], p[1] - c["y"]) > 260
                        for c in boss.superior_circles)]
    count = 1 if timer < 480 else 2
    for _ in range(count):
        if not available:
            break
        x, y = available.pop(random.randrange(len(available)))
        boss.superior_circles.append({
            "x": x, "y": y,
            "radius": 88 if timer >= 480 else 76,
            "angle": random.uniform(0.0, math.tau),
            "rot": 0.020 if len(boss.superior_circles) % 2 == 0 else -0.020,
            "life": period,
            "max_life": period,
        })


def _superior_circle_spray(bullet_manager, boss, timer, phase):
    """黄金魔法阵：绕阵缘旋转并向外喷射排列整齐的金色鳞片弹"""
    for c in boss.superior_circles[:]:
        c["life"] -= 1
        c["angle"] += c["rot"]
        if c["life"] <= 0:
            boss.superior_circles.remove(c)
            continue
        if c["max_life"] - c["life"] < 30:
            continue   # 成形期
        if timer % 30 == 0:
            for i in range(8):
                ang = c["angle"] + i * math.tau / 10
                x = c["x"] + math.cos(ang) * c["radius"]
                y = c["y"] + math.sin(ang) * c["radius"]
                b = create_bullet_angle(x, y, ang, 2.3,
                                        Bullet.TYPE_RICE, radius=2.4,
                                        color=_SUPER_GOLD if i % 2 == 0 else _SUPER_GOLD_DIM)
                b.manager = bullet_manager
                b.lifetime = 240
                bullet_manager.add_enemy_bullet(b)


def _superior_wing_beams(bullet_manager, boss, timer, phase):
    """龙翼形光束：左右双翼 + 顶角龙角成对展开，将弹幕空间切割成多个区域并缓慢扫掠"""
    if phase == 0:
        return
    period = 150 if phase == 1 else 112
    if timer % period != 0:
        return
    rot = timer * 0.012
    cx, cy = boss.x, boss.y
    beams = []
    # 左右双翼：从核心两侧展开的 V 形光束
    for side in (-1.0, 1.0):
        base = math.pi / 2 + side * 0.52 + rot * 0.25 * side
        for k in (-1.0, 1.0):
            a = base + k * 0.30
            beams.append((cx + side * 42, cy, a, 780))
    # 顶角：向上展开的两条「龙角」光束
    for k in (-1.0, 1.0):
        a = -math.pi / 2 + k * 0.55 + rot * 0.3
        beams.append((cx, cy, a, 620))
    for bx, by, a, ln in beams:
        b = create_bullet_angle(bx, by, a, 0.0, Bullet.TYPE_BEAM, radius=3,
                                color=_SUPER_GOLD)
        b.manager = bullet_manager
        b.angle = a
        b.beam_length = ln
        b.lifetime = period - 18
        # 沿光束垂直方向缓慢平移，像龙翼展开扫过战场
        b.vx = math.cos(a + math.pi / 2) * 0.45
        b.vy = math.sin(a + math.pi / 2) * 0.45
        bullet_manager.add_enemy_bullet(b)


def _superior_scale_storm(bullet_manager, boss, timer, phase, wave):
    """黄金龙鳞风暴（终幕）：全场高密度对称鳞片弹，旋转方向与排列不断变化"""
    if phase < 2:
        return
    if timer % 42 == 0:
        n = 18 + wave % 3 * 2
        dir_sign = 1.0 if (timer // 36) % 2 == 0 else -1.0
        base = timer * 0.05 * dir_sign
        for i in range(n):
            ang = base + i * math.tau / n
            b = create_bullet_angle(boss.x, boss.y, ang, 0.0,
                                    Bullet.TYPE_RICE, radius=2.4,
                                    color=_SUPER_GOLD if i % 3 else _SUPER_WHITE)
            b.manager = bullet_manager
            b.orbit_center = (boss.x, boss.y)
            b.orbit_radius = 16
            b.orbit_angle = ang
            b.orbit_speed = 0.055 * dir_sign
            b.orbit_grow = 1.25
            b.orbit_break = 190
            b.orbit_break_speed = 2.5
            b.lifetime = 480
            bullet_manager.add_enemy_bullet(b)
    # 左右对称的快速鳞片墙：从两侧相向扫过
    if timer % 60 == 0:
        for side in (-1.0, 1.0):
            x0 = cfg.BATTLE_AREA_WIDTH + 40 if side > 0 else -40
            y0 = random.uniform(60, cfg.BATTLE_AREA_HEIGHT - 60)
            b = create_bullet_angle(x0, y0, math.pi if side > 0 else 0.0, 0.0,
                                    Bullet.TYPE_BEAM, radius=3, color=_SUPER_GOLD_DIM)
            b.manager = bullet_manager
            b.angle = math.pi if side > 0 else 0.0
            b.beam_length = 560
            b.vx = -side * 0.9
            b.lifetime = 300
            bullet_manager.add_enemy_bullet(b)


def spell_superiority(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """超符「Superiority」(Last Spell)：黄金领域·龙鳞风暴

    末影龙展开黄金领域，将自身化为金色龙之核心：持续释放以龙鳞为形态的
    环状固定弹；场地周期性生成巨大的黄金魔法阵，沿固定方向旋转并向外喷射
    排列整齐的金色鳞片弹；龙翼形光束从不同方向展开，将弹幕空间切割成多个
    区域。随符卡推进，黄金鳞片阵列不断改变旋转方向与排列方式，最终形成
    覆盖全场的黄金龙鳞风暴。
    """
    phase = 0 if timer < 240 else (1 if timer < 480 else 2)
    wave = timer // 240
    cycle_dir = (timer // 360) % 2   # 每 6 秒反转一次主导旋转方向

    # 金色龙之核心：居中悬浮，仅轻微游走
    boss.target_y = 118 + math.sin(timer * 0.010) * 6
    if timer % 260 == 0:
        boss.target_x = random.uniform(cfg.BATTLE_AREA_WIDTH * 0.40,
                                       cfg.BATTLE_AREA_WIDTH * 0.60)

    # 环状固定弹 + 对称展开弹（核心）
    _superior_core_rings(bullet_manager, boss, timer, phase, wave, cycle_dir)
    _superior_sym_expand(bullet_manager, boss, timer, phase, wave, cycle_dir)

    # 黄金魔法阵：生成 + 旋转 + 喷射鳞片弹
    _superior_spawn_circles(boss, timer)
    _superior_circle_spray(bullet_manager, boss, timer, phase)

    # 龙翼形光束：区域封锁
    _superior_wing_beams(bullet_manager, boss, timer, phase)

    # 终幕：黄金龙鳞风暴
    _superior_scale_storm(bullet_manager, boss, timer, phase, wave)
