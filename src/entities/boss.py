# Boss 系统
# 符卡战斗、阶段切换、Boss弹幕模式

import math
import random
import os
import pygame
from src.engine import settings as cfg
from src.engine import boss_art
from src.engine.collision import circle_collision
from src.engine import hires
from src.engine.fallback_font import FallbackFont
from src.engine.spell_bg import SpellBackground
from src.entities.bullet import Bullet, create_bullet_aimed, create_bullet_angle

# 模块级字体缓存
_boss_fonts = {}

def _get_font(size, bold=False):
    key = (size, bold)
    if key not in _boss_fonts:
        font_path = os.path.join(cfg.ASSETS_DIR, "fonts", "font1.ttf")
        fallback_path = os.path.join(cfg.ASSETS_DIR, "fonts", "font2.otf")
        _boss_fonts[key] = FallbackFont(font_path, fallback_path, size)
        if bold:
            _boss_fonts[key].set_bold(True)
    return _boss_fonts[key]


# 血条与名字行布局（相对战斗区左上角）
HP_BAR_TOP = 10             # 血条顶部
HP_BAR_HEIGHT = 8           # 血条高度
BOSS_NAME_Y = HP_BAR_TOP + HP_BAR_HEIGHT + 4   # Boss 名 / 符卡名共用行

# 开符站稳：Boss 到达符卡站位（战场宽/2, 120）前不展开符卡弹幕，
# 避免 Boss 边滑行边放弹导致弹幕变形；超时后就位兜底防卡死
SPELL_SETTLE_EPS = 1.0       # 到达站位判定阈值（px）
SPELL_SETTLE_MAX = 240       # 最长等待帧数（超时就位兜底）

# 对话期间 Boss 机体轻微上下漂浮（纯视觉，不影响坐标与判定）
BOSS_DIALOGUE_FLOAT_AMPLITUDE = 8   # 上下浮动幅度（px）
BOSS_DIALOGUE_FLOAT_SPEED = 2.2     # 漂浮角速度（rad/s）

# 阶段血环：Boss 机体周围一圈，表示当前阶段（一个非符 + 紧随其后的符卡）的总血量
RING_THICKNESS = 5             # 环厚度（px）
RING_RADIUS_SPRITE_FIT = 0.95  # 环半径 = 立绘外接矩形长边的一半 x 该系数 + 余量
RING_RADIUS_PAD = 8            # 半径余量（px）
RING_RADIUS_MIN = 34           # 半径下限（无贴图的几何 Boss / 小立绘）
RING_RADIUS_MAX = 92           # 半径上限（大立绘不至于顶到战斗区两侧）
RING_BACK_COLOR = (58, 58, 68) # 底环：阶段总刻度（尚未打掉的部分）
RING_SPELL_DARKEN = 0.62       # 符卡段颜色 = 非符段颜色 x 该系数（略深，作区分）
RING_ARC_STEP = 4.0            # 分段扇形的步进角度（度）
RING_RATIO_REF = 1.5           # 典型「符卡血量 : 非符血量」比值
RING_SPELL_SHARE_REF = 1.0 / 6.0   # 该比值下符卡段占的角度比例（平均 1/6 圈）
RING_SPELL_SHARE_MIN = 0.03    # 符卡段最小角度比例（再薄也留一丝可见）
RING_EARLY_EPS = 0.5           # 判定「非符提前结束」的血量容差


def _ring_spell_share(non_spell_hp, spell_hp):
    """符卡段在环上占的角度比例（压缩后）。

    直接按血量占比（spell / (non + spell)）画，本作的符卡血量普遍是非符的 1~3 倍，
    一圈里大半都是符卡色、非符段反而被挤没。这里按血量比做一次压缩：
    「符卡 : 非符 = RING_RATIO_REF」的典型阶段正好落到 1/6 圈
    （RING_SPELL_SHARE_REF），各阶段的差异仍随血量比单调变化 —— 非符越厚，
    符卡段越窄；本阶段只有符卡（非符没血）时整圈都是符卡色。
    """
    if non_spell_hp <= 0:
        return 1.0
    if spell_hp <= 0:
        return 0.0
    weight = RING_RATIO_REF * (1.0 - RING_SPELL_SHARE_REF) / RING_SPELL_SHARE_REF
    ratio = spell_hp / non_spell_hp
    share = ratio / (ratio + weight)
    return min(1.0, max(RING_SPELL_SHARE_MIN, share))


def _english_only(text):
    """Boss 显示名：只保留 ASCII 英文部分（删除中文），避免名字过长超出战斗区域"""
    return "".join(ch for ch in (text or "") if ord(ch) < 128).strip()


# Boss 贴图缓存：key = (贴图路径, 目标高度)
_boss_sprite_cache = {}
_boss_sprite_attempted = set()


def _get_boss_sprite(path, target_height, sharp=False):
    """加载并缓存 Boss 贴图（按目标高度等比缩放）；失败返回 None（回退几何绘制）

    sharp=True 走高分辨率（符卡宣言的整幅立绘、战斗中出场的本体）：像素乘渲染
    倍率，但度量仍是逻辑尺寸，绘制代码不用改；画到哪里由调用方的贴图层决定
    （立绘走 blit_gpu_top，本体走 hires.blit_entity）。
    碰撞 Mask 一律用默认的 1x 版本，这样判定范围不随画面设置改变。
    """
    factor = hires.scale() if sharp else 1
    key = (path, target_height, factor)
    if key in _boss_sprite_attempted:
        return _boss_sprite_cache.get(key)
    _boss_sprite_attempted.add(key)
    try:
        # 白底立绘在这一步抠掉背景并按内容裁剪（结果缓存，只处理一次）
        img = boss_art.load_sprite(path)
        if img is None:
            raise ValueError("sprite unavailable")
        w, h = img.get_size()
        if h <= 0:
            raise ValueError("invalid sprite height")
        new_w = max(1, round(w * target_height / h))
        if factor > 1:
            _boss_sprite_cache[key] = hires.scaled_image(img, (new_w, target_height),
                                                        factor)
        else:
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
        img = boss_art.load_sprite(path)
        if img is None:
            raise ValueError("sprite unavailable")
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


def _get_sadan_sword_sprite(path, target_height, sharp=False):
    """Loads the diamond sword asset and rotates it to fall vertically.

    The source icon is a square with a diagonal sword, so it is scaled to
    target_height / sqrt(2) and then rotated +45 degrees. The returned surface
    has the sword blade running straight down.

    sharp=True 时按渲染倍率加载与旋转（旋转在倍率像素上做），供实体层直贴。
    """
    key = (path, target_height, bool(sharp))
    if key in _sadan_sword_sprite_cache:
        return _sadan_sword_sprite_cache[key]
    sprite = None
    try:
        side = max(1, int(round(target_height / math.sqrt(2))))
        source = _get_boss_sprite(path, side, sharp=sharp)
        if source is not None:
            sprite = _hi_rotate(source, 45)
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


# --- 战斗区召唤物 / 特效：贴图按倍率旋转、翻转，画到「实体层」---
# 召唤物（幻影龙、亡灵展品、亡灵小队、兵马俑、巨像…）原先与整幅画面一起被放大，
# 与旁边的 Boss 本体、弹幕有清晰度落差。这里统一改走 hires.blit_entity：贴图按
# 渲染倍率加载（_entity_sprite），旋转 / 翻转在倍率像素上做，整体透明度与加法混合
# 都交给显卡（不必每帧抠半透明副本）。


def _hi_rotate(sprite, degrees):
    """旋转一张（可能带倍率的）贴图，并补回倍率标记

    pygame.transform 返回的是普通表面，不带「逻辑尺寸」标记 —— 直接贴会被当成 1x
    图处理（位置按真实像素算，等于错位 + 更糊），所以要重新包一层。
    """
    rotated = pygame.transform.rotate(sprite, degrees)
    factor = getattr(sprite, "hi_scale", 1)
    return rotated if factor <= 1 else hires.wrap(rotated, factor)


def _hi_flip(sprite, flip_x=True, flip_y=False):
    """水平 / 垂直翻转（同样要补回倍率标记，见 _hi_rotate）"""
    flipped = pygame.transform.flip(sprite, flip_x, flip_y)
    factor = getattr(sprite, "hi_scale", 1)
    return flipped if factor <= 1 else hires.wrap(flipped, factor)


def _hi_scale(sprite, logical_size):
    """按逻辑尺寸重新缩放一张（可能带倍率的）贴图，并保持倍率标记"""
    factor = getattr(sprite, "hi_scale", 1)
    size = (max(1, int(round(logical_size[0] * factor))),
            max(1, int(round(logical_size[1] * factor))))
    scaled = pygame.transform.smoothscale(sprite, size)
    return scaled if factor <= 1 else hires.wrap(scaled, factor)


def _entity_sprite(path, height, screen):
    """战斗区召唤物贴图：实体层开着时按渲染倍率加载（关掉开关时仍是 1x 旧观感）"""
    return _get_boss_sprite(path, height, sharp=hires.entity_factor(screen) > 1)


# 符卡宣言文字缓存：key = (符卡名, 颜色) -> (投影, 白字)
_banner_text_cache = {}


def _get_banner_text(name, color):
    """符卡宣言的两张贴图（带色投影 + 白字），按符卡名缓存

    每次开符本来都要 render 两遍、再用 _with_alpha 抠两份半透明副本（copy + fill
    走 BLEND_RGBA_MULT 慢路径，实测 1.3ms/帧）。这里缓存一份「自己的」副本，
    逐帧只调透明度，既省掉渲染与抠副本，也不会污染字体内部的字形缓存表面。
    """
    key = (name, tuple(color))
    got = _banner_text_cache.get(key)
    if got is None:
        font = _get_font(SPELL_BANNER_FONT_SIZE, bold=True)
        shadow = font.render(name, True, color)
        text = font.render(name, True, cfg.COLOR_WHITE)
        if len(_banner_text_cache) > 16:
            _banner_text_cache.clear()
        got = (shadow.copy(), text.copy())
        _banner_text_cache[key] = got
    return got


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
    """生成幻影龙贴图的柔和光晕层（沿剪影向外扩散的淡紫柔光，轻微发光）

    光晕刻意留在 1x：它是「剪影按 1 像素往外糊一圈」出来的柔边，本身没有细节可
    丢 —— 按倍率做反而会把 9 次偏移拉成倍率像素一级的台阶（3x 下就是 3 像素一级
    的硬边）。贴图与法阵走倍率，柔光跟 1x 画布一起放大，观感与旧版一致。
    """
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
SPELL_BANNER_FONT_SIZE = 34       # 符卡名字号（首次使用该字号要解析字体，约 5ms）
PHANTOM_DRAGON_HEIGHT = 52        # 龙符幻影龙贴图展示高度（px）
SPELL_BANNER_DROP = 36            # 淡出时向下平移距离（px）


class SpellCard:
    """符卡（一个攻击阶段）"""
    def __init__(self, name, pattern_func, hp_threshold=None, end_hp_threshold=None,
                 bg_style=None, direct_next=False, time_spell=False,
                 auto_break_frames=None):
        self.name = name
        self.pattern_func = pattern_func
        self.hp_threshold = hp_threshold
        self.end_hp_threshold = end_hp_threshold   # 独立结束阈值（None 时用下一张符的 hp_threshold）
        self.bg_style = bg_style   # 符卡背景风格（None 时按名字自动判断）
        self.direct_next = direct_next   # True 时结束后不进入非符，直接开下一张符卡
        self.time_spell = time_spell     # 时符：无 Boss 血量，攻击不会提前结束符卡
        self.auto_break_frames = auto_break_frames  # 超时自动击破帧数（None=不限时）
        self.timer = 0
        self.active = False
        self.completed = False

    def start(self):
        self.active = True
        self.timer = 0
        self.completed = False

    def update(self, boss, bullet_manager, dt, player_x=0, player_y=0):
        # 默认符卡无时间限制；允许指定帧数后自动击破
        if not self.active:
            return
        self.timer += 1
        self.pattern_func(boss, bullet_manager, self.timer, dt, player_x, player_y)
        if (boss.current_spell is self
                and self.auto_break_frames is not None
                and self.timer >= self.auto_break_frames):
            boss._auto_break_spell()

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
        # 开符站稳：Boss 未到达符卡站位前不展开符卡弹幕
        self._spell_settle = False
        self._spell_settle_frames = 0

        # 阶段血环（Boss 周围一圈：一个非符 + 紧随其后的那张符卡的总血量）
        self._ring_from = None          # 本阶段起始血量（None = 还没铺环）
        self._ring_in_non_spell = False # 环里是否留着尚未结清的非符段
        self._ring_ns_budget = None     # 非符段血量预算（开符时结清）
        self._ring_sp_budget = None     # 符卡段血量预算

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
        self.scarf_active_members = []  # 队符本轮随机激活的两名成员名列表（生命周期由符卡维护）
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
        self.necron_nuclear = None     # 焚符「Nuclear Frenzy」核能领域状态（None=未展开）
        self.kaeman_dominion = None    # 王符「Wither King's Dominion」Wither 王领域状态（None=未展开）
        self.kaeman_relics = None      # 冥符「Five Corrupted Relics」五种 Relic 五边形状态（None=未展开）
        self.kaeman_slash = None       # 裂符「Dimensional Slash」空间裂痕状态（None=未展开）
        self.kaeman_atomize = None     # 王符「Atomizing Ray」原子化扫射射线状态（None=未展开）
        self.kaeman_slumber = None    # 终仪「The Wither King's Final Slumber」吸收/放出状态（None=未展开）
        self.spell_damage_hook = None  # 符卡伤害回调（焚符火力压制领域），由符卡挂接
        self.gagouji_spiral_bullets = []  # 电光「Directional Lightning」旋转麟弹
        self.gagouji_spiral_center = None
        self.gagouji_spin = 0.0
        self.gagouji_spiral_pending = []
        self.gagouji_spiral_complete = False
        self.gagouji_forming_rings = []
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
        # 对话漂浮：相位推进 + 是否处于漂浮状态的标记
        self._float_phase = 0.0
        self._dialogue_float = False

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

    def _spell_settled(self):
        """开符站稳检查：返回 True 表示可展开符卡弹幕。

        Boss 未到达符卡站位（战场宽/2, 120）前不展开弹幕：Boss 继续滑向站位，
        符卡计时同步暂停，避免 Boss 边移动边放弹导致弹幕变形；超时后就位兜底，
        防止站位不可达导致符卡卡死。
        """
        if not self._spell_settle:
            return True
        self._spell_settle_frames += 1
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        if dx * dx + dy * dy <= SPELL_SETTLE_EPS * SPELL_SETTLE_EPS:
            self._spell_settle = False
            return True
        if self._spell_settle_frames >= SPELL_SETTLE_MAX:
            self.x = self.target_x
            self.y = self.target_y
            self._spell_settle = False
            return True
        return False

    def update(self, dt, bullet_manager, player_x, player_y):
        # 符卡背景独立推进：Boss 死亡/结符后的淡出也能继续播放
        if self.spell_bg is not None:
            self.spell_bg.update(dt)
            if self.spell_bg.done:
                self.spell_bg = None
        if not self.alive:
            return
        self._bullet_manager = bullet_manager
        # 默认关闭漂浮；仅“对话待机”分支会开启
        self._dialogue_float = False

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
                self._ring_begin_non_spell()
            self.y += 0.5
            return

        # 尚未开战（对话阶段/登场等待）：只做入场定位移动，不攻击
        if not self.combat_enabled:
            self._move_toward_target(dt)
            # 仅在“对话待机”（无开战延迟）时轻微漂浮，模仿浮空
            if self.combat_delay <= 0:
                self._float_phase += dt * BOSS_DIALOGUE_FLOAT_SPEED
                self._dialogue_float = True
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
            if self.current_spell and self._spell_settled():
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
                    self._ring_begin_non_spell()

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
        self.scarf_active_members = []
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
        self.necron_nuclear = None
        self.kaeman_dominion = None
        self.kaeman_relics = None
        self.kaeman_dragon = None
        self.kaeman_slash = None
        self.kaeman_atomize = None
        self.kaeman_slumber = None
        self.spell_damage_hook = None   # 开符：清空上一符卡的伤害回调
        self.gagouji_spiral_bullets = []
        self.gagouji_spiral_center = None
        self.gagouji_spin = 0.0
        self.gagouji_spiral_pending = []
        self.gagouji_spiral_complete = False
        self.gagouji_forming_rings = []
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
        # 开符站稳：Boss 到达符卡站位前不展开弹幕（避免边移动边放弹导致弹幕变形）
        self._spell_settle = True
        self._spell_settle_frames = 0
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
        # Last Spell 展开：血量已打空，补充黄金领域独立血量
        if self.last_spell_active:
            if getattr(spell, "time_spell", False):
                self.hp = 0
            else:
                self.hp = self.last_spell_hp
        # 阶段血环：从非符打进来的结清非符段，否则本阶段从这张符卡起算
        if self._ring_in_non_spell:
            thresholds = self._ring_thresholds()
            if thresholds is not None:
                self._ring_close_non_spell(*thresholds)
        else:
            self._ring_begin_spell_only()

    def _clear_spell_effects(self):
        """Boss 战败时清除符卡视觉残留（幻影龙/石柱等）"""
        self.phantom_dragons = []
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
        self.scarf_active_members = []
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
        self.necron_nuclear = None
        self.kaeman_dominion = None
        self.kaeman_relics = None
        self.kaeman_dragon = None
        self.kaeman_slash = None
        self.kaeman_atomize = None
        self.kaeman_slumber = None
        self.spell_damage_hook = None   # 战败：清空符卡伤害回调
        self.gagouji_spiral_bullets = []
        self.gagouji_spiral_center = None
        self.gagouji_spin = 0.0
        self.gagouji_spiral_pending = []
        self.gagouji_spiral_complete = False
        self.gagouji_forming_rings = []

    def _auto_break_spell(self):
        """符卡超时自动击破：扣除本符卡剩余 HP 后按正常流程结符。"""
        spell = self.current_spell
        if spell is None:
            return
        threshold = spell.end_hp_threshold
        if threshold is None:
            return
        floor = self.max_hp * threshold
        remaining = max(0.0, self.hp - floor)
        if remaining <= 0:
            self._end_spell()
            return
        resistance = self.resistance
        if resistance > 0:
            self.take_damage(remaining / resistance)
        else:
            self.hp = floor
            self._end_spell()

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
        self.scarf_active_members = []
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
        self.necron_nuclear = None
        self.kaeman_dominion = None
        self.kaeman_relics = None
        self.kaeman_dragon = None
        self.kaeman_slash = None
        self.kaeman_atomize = None
        self.kaeman_slumber = None
        self.spell_damage_hook = None   # 结符：清空符卡伤害回调
        self.gagouji_spiral_bullets = []
        self.gagouji_spiral_center = None
        self.gagouji_spin = 0.0
        self.gagouji_spiral_pending = []
        self.gagouji_spiral_complete = False
        self.gagouji_forming_rings = []
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
            self._ring_begin_non_spell()

    def take_damage(self, damage, source=None):
        if (self.entering or self.invincible or not self.combat_enabled
                or self.phase == "reviving"):
            return False
        if self._is_time_spell_active():
            return False
        self.hp -= damage * self.resistance
        damage_hook = getattr(self, "spell_damage_hook", None)
        if damage_hook is not None:
            damage_hook(damage, source)
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
        # 对话漂浮：仅视觉上下偏移，不影响 Boss 坐标/判定
        if self._dialogue_float:
            py += int(round(math.sin(self._float_phase) *
                            BOSS_DIALOGUE_FLOAT_AMPLITUDE))

        if self.entering and self.entry_timer % 6 < 3:
            return

        # 龙符幻影龙：绘制在 Boss 本体之下
        self._draw_phantom_dragons(screen, offset_x, offset_y)
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
        # 阶段血环：当前阶段（非符 + 符卡）的总血量，画在本体之下
        self._draw_phase_ring(screen, px, py)
        # Boss 本体：配置了贴图时用贴图替换几何绘制（加载失败则回退八角形）
        if self.sprite_path:
            sprite = _get_boss_sprite(self.sprite_path, self.sprite_height, sharp=True)
            if sprite is not None:
                hires.blit_entity(screen, sprite,
                                  (px - sprite.get_width() // 2,
                                   py - sprite.get_height() // 2))
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
        sharp = hires.entity_factor(screen) > 1
        sprite = _entity_sprite(cfg.END_DRAGON_PET_SPRITE, PHANTOM_DRAGON_HEIGHT,
                                screen)
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
                img = _hi_rotate(sprite, -math.degrees(ang))
                if glow_img is not None:
                    glow_img = _hi_rotate(glow_img, -math.degrees(ang))
            if flip:
                img = _hi_flip(img, True, False)
                if glow_img is not None:
                    glow_img = _hi_flip(glow_img, True, False)

            # 柔和光晕：亮度随整体透明度缩放，带轻微呼吸脉动
            if glow_img is not None:
                pulse = 0.72 + 0.28 * math.sin(pygame.time.get_ticks() * 0.004 + i * 1.9)
                glow_alpha = max(0, min(255, int(alpha * 0.55 * pulse)))
                if glow_alpha > 0:
                    hires.blit_entity(screen, glow_img,
                                      (px - glow_img.get_width() // 2,
                                       py - glow_img.get_height() // 2),
                                      alpha=glow_alpha)

            hires.blit_entity(screen, img,
                              (px - img.get_width() // 2,
                               py - img.get_height() // 2),
                              alpha=alpha)

    def _draw_core_aura(self, screen, px, py):
        """金色龙之核心：脉动金环 + 旋转符文环（Last Spell 期间围绕本体）"""
        t = pygame.time.get_ticks() * 0.003
        fx = hires.entity_effect(screen, (px - 59, py - 59), (118, 118))
        for i, (base_r, width, col) in enumerate((
                (34, 2, _SUPER_GOLD_DIM), (44, 1, _SUPER_GOLD), (54, 1, _SUPER_WHITE))):
            rr = int(base_r + math.sin(t + i * 1.4) * 2)
            fx.circle(col, (px, py), rr, width)
        a = t * 0.9
        for k in range(4):
            ang = a + k * math.pi / 2
            x = px + math.cos(ang) * 30
            y = py + math.sin(ang) * 30
            fx.circle(_SUPER_GOLD, (int(x), int(y)), 2, 0)
        fx.commit()

    def _draw_protector_effects(self, screen, offset_x=0, offset_y=0):
        """石符：固定石柱结界 + 堡垒石环 + 震荡冲击环（纯视觉，无判定）"""
        # 固定石柱结界
        for p in self.protector_barriers:
            px = int(p["x"] + offset_x)
            py = int(p["y"] + offset_y)
            w, h = p["w"], p["h"]
            fx = hires.entity_effect(screen, (px - w // 2 - 2, py - h // 2 - 6),
                                     (w + 4, h + 12))
            fx.rect(_STONE_DIM, (px - w // 2, py - h // 2, w, h))
            fx.rect(_STONE_COLOR, (px - w // 2, py - h // 2, w, h), 1)
            fx.rect(_STONE_COLOR, (px - w // 2, py - h // 2 - 4, w, 5))
            fx.commit()
        # 堡垒石环：围绕本体的「岩石堡垒」轮廓
        if self.protector_fortress:
            cx = int(self.x + offset_x)
            cy = int(self.y + offset_y)
            t = pygame.time.get_ticks() * 0.002
            fx = hires.entity_effect(screen, (cx - 44, cy - 44), (88, 88))
            fx.circle(_STONE_DIM, (cx, cy), 30, 2)
            fx.circle(_STONE_COLOR, (cx, cy), 37, 1)
            for k in range(4):
                a = t + k * math.pi / 2
                tx = cx + math.cos(a) * 30
                ty = cy + math.sin(a) * 30
                fx.rect(_STONE_DIM, (int(tx) - 5, int(ty) - 5, 10, 10))
                fx.rect(_STONE_COLOR, (int(tx) - 5, int(ty) - 5, 10, 10), 1)
            fx.commit()
        # 震荡冲击环
        shock = self.protector_shock
        if shock is not None:
            prog = 1.0 - shock["life"] / shock["max_life"]
            r = int(22 + prog * 190)
            col = tuple(int(c * (0.55 + 0.45 * (1.0 - prog))) for c in _STONE_COLOR)
            cx = int(self.x + offset_x)
            cy = int(self.y + offset_y)
            fx = hires.entity_effect(screen, (cx - r - 3, cy - r - 3),
                                     (r * 2 + 6, r * 2 + 6))
            fx.circle(col, (cx, cy), r, 2)
            fx.commit()

    def _draw_watcher_exhibits(self, screen, offset_x=0, offset_y=0):
        """展符亡灵展品：屏幕上方一排亡灵幻影（贴图发光渲染 + 预警光环，纯视觉无判定）"""
        if not self.watcher_exhibits:
            return
        for ex in self.watcher_exhibits:
            height = ex.get("height", 56)
            sprite = _entity_sprite(ex["sprite"], height, screen)
            if sprite is None:
                continue
            px = int(ex["x"] + offset_x)
            py = int(ex["y"] + offset_y)
            # 常驻幽蓝亡灵能量光晕
            glow = _get_watcher_glow(int(height * 0.95),
                                     ex.get("glow_color", (70, 110, 200)))
            if glow is not None:
                hires.blit_entity(screen, glow,
                                  (px - glow.get_width() // 2,
                                   py - glow.get_height() // 2))
            # 预警：幽蓝脉冲光环（符卡点亮 ex["warn"] 期间持续闪烁）
            if ex.get("warn"):
                pulse = (pygame.time.get_ticks() * 0.012) % (math.tau)
                rr = int(height * 0.62) + int(math.sin(pulse) * 6)
                warn_col = ex.get("warn_color", (130, 220, 255))
                fx = hires.entity_effect(screen, (px - rr - 3, py - rr - 3),
                                         (rr * 2 + 6, rr * 2 + 6))
                fx.circle(warn_col, (px, py), rr, 2)
                fx.circle((240, 250, 255), (px, py), max(4, rr - 9), 1)
                fx.commit()
            # 亡灵幻影贴图：加法混合发光渲染（黑色背景不叠加）
            hires.blit_entity(screen, sprite,
                              (px - sprite.get_width() // 2,
                               py - sprite.get_height() // 2),
                              add=True)

    def _draw_revival_circle(self, fx, px, py, prog, color, now):
        """亡灵魔法阵：旋转六芒星紫环 + 内圈亮纹（Undead 召唤/复活共用，纯视觉）

        fx 是一块实体层特效面板（hires.entity_effect）：它按渲染倍率作画，与旁边
        的召唤物贴图同一清晰度；没有显卡层时就是一张 1x 临时表面，观感与旧版一致。
        """
        r = 15 + int(8 * (1.0 - prog))
        rot = now * 0.004
        bright = tuple(min(255, c + 60) for c in color)
        fx.circle(color, (px, py), r, 2)
        fx.circle(bright, (px, py), max(3, r - 5), 1)

        def _triangle(radius, offset):
            pts = [
                (px + math.cos(rot + offset + k * math.tau / 3) * radius,
                 py + math.sin(rot + offset + k * math.tau / 3) * radius)
                for k in range(3)
            ]
            fx.polygon(color, pts, 1)

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
            sprite = _entity_sprite(u["sprite"], height, screen)
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
                hires.blit_entity(screen, glow,
                                  (px - glow.get_width() // 2,
                                   py - glow.get_height() // 2))

            if phase == "summoning":
                # 召唤魔法阵 + 贴图随进度淡入（期间不可命中、不发射）
                prog = min(1.0, timer / max(1, u.get("summon_time", 24)))
                fx = hires.entity_effect(screen, (px - 26, py - 26), (52, 52))
                self._draw_revival_circle(fx, px, py, prog, summon_color, now)
                fx.commit()
                if sprite is not None:
                    hires.blit_entity(screen, sprite,
                                      (px - sprite.get_width() // 2,
                                       py - sprite.get_height() // 2),
                                      alpha=int(255 * prog))
            elif phase == "active":
                # 存活：贴图 + 青绿灵魂火核心
                if sprite is not None:
                    hires.blit_entity(screen, sprite,
                                      (px - sprite.get_width() // 2,
                                       py - sprite.get_height() // 2))
                fx = hires.entity_effect(screen, (px - 7, py - 7), (14, 14))
                fx.circle(soul_color, (px, py), 4, 1)
                fx.commit()
            elif phase == "dying":
                # 灵魂消散：贴图淡出收缩 + 青绿残焰
                prog = 1.0 - min(1.0, timer / max(1, u.get("die_time", 22)))
                if sprite is not None:
                    w = max(1, int(sprite.get_width() * max(0.4, prog)))
                    h = max(1, int(sprite.get_height() * max(0.4, prog)))
                    small = _hi_scale(sprite, (w, h))
                    hires.blit_entity(screen, small, (px - w // 2, py - h // 2),
                                      alpha=int(255 * prog))
                soul_r = max(2, int(8 * prog))
                fx = hires.entity_effect(screen, (px - soul_r - 2, py - soul_r - 2),
                                         (soul_r * 2 + 4, soul_r * 2 + 4))
                fx.circle(soul_color, (px, py), soul_r, 1)
                fx.commit()
            elif phase == "reviving":
                # 亡灵魔法阵重组：紫环旋转 + 青绿灵魂能量朝中心汇聚
                prog = min(1.0, timer / max(1, u.get("revive_time", 90)))
                fx = hires.entity_effect(screen, (px - 26, py - 26), (52, 52))
                self._draw_revival_circle(fx, px, py, prog, summon_color, now)
                fx.commit()
                fx = hires.entity_effect(screen, (px - 36, py - 36), (72, 72))
                for k in range(4):
                    a = now * 0.004 + k * math.pi / 2
                    rr = 6 + (1.0 - prog) * 26
                    gx = px + math.cos(a) * rr
                    gy = py + math.sin(a) * rr
                    fx.circle(soul_color, (int(gx), int(gy)), 2, 0)
                fx.commit()

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
                pulse = 0.5 + 0.5 * math.sin(now * 0.02)
                pulse_r = int(r * (1.15 + pulse * 0.55))
                radius = max(ring_r, pulse_r) + 3
                fx = hires.entity_effect(screen, (px - radius, py - radius),
                                         (radius * 2, radius * 2))
                fx.circle(purple, (px, py), ring_r, 2)
                fx.circle(warn, (px, py), pulse_r, 1)
                fx.commit()
                alpha = int(255 * min(1.0, prog * 1.5))
            elif phase == "despawn":
                prog = min(1.0, timer / max(1, sk.get("despawn_frames", 36)))
                alpha = int(255 * (1.0 - prog))
                scale = 1.0 - 0.4 * prog

            # 喷射闪光：嘴部一亮（纯视觉）
            flash = sk.get("flash", 0)
            if flash > 0:
                fl = min(1.0, flash / 6.0)
                flash_r = int(r * (0.9 + 0.6 * (1.0 - fl))) + 2
                fx = hires.entity_effect(screen, (px - flash_r, py - flash_r),
                                         (flash_r * 2, flash_r * 2))
                fx.circle((215, 245, 255), (px, py), flash_r - 2, 1)
                fx.commit()

            if alpha <= 0:
                continue

            # 骷髅头绘制到实体层特效面板（按渲染倍率作画，支持整体淡入淡出 / 缩小）
            size = int(r * 2.7) + 8
            fx = hires.entity_effect(screen, (px - size // 2, py - size // 2),
                                     (size, size))
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
                fx.polygon(bone, [tip, base_l, base_r])
                fx.polygon(purple, [tip, base_l, base_r], 1)
            # 颅顶圆 + 颧骨/上颌（头骨下半变宽）
            fx.circle(bone, (cx, int(cy - rr * 0.32)), int(rr * 0.78))
            for sx in (-1, 1):
                fx.circle(bone, (cx + sx * int(rr * 0.42), int(cy + rr * 0.10)),
                          int(rr * 0.42))
            # 骨缝线（颅顶细线）
            fx.line(bone_dim, (cx - int(rr * 0.30), int(cy - rr * 0.62)),
                    (cx + int(rr * 0.30), int(cy - rr * 0.62)), 1)

            # 眼窝 + 青色灵魂火
            for sx in (-1, 1):
                ex = cx + sx * int(rr * 0.33)
                ey = int(cy - rr * 0.16)
                fx.circle(socket, (ex, ey), int(rr * 0.24))
                flicker = 0.75 + 0.25 * math.sin(now * 0.02 + sx * 2.1)
                fx.circle(teal, (ex, ey), max(2, int(rr * 0.13 * flicker)))
                fx.circle((205, 255, 235),
                          (ex - int(rr * 0.06), ey - int(rr * 0.06)),
                          max(1, int(rr * 0.04)))
                fx.circle(purple, (ex, ey), int(rr * 0.24), 1)

            # 鼻洞（倒三角）
            nose_top = (cx, int(cy + rr * 0.06))
            nose_l = (cx - int(rr * 0.10), int(cy + rr * 0.22))
            nose_r = (cx + int(rr * 0.10), int(cy + rr * 0.22))
            fx.polygon(socket, [nose_top, nose_l, nose_r])

            # 嘴部：开口高度随 mouth 张合，含上下牙齿与口腔灵魂火
            mouth_top = int(cy + rr * 0.52)
            gap = int(rr * 0.45 * mouth)
            mouth_bottom = mouth_top + gap
            mouth_w = int(rr * 0.66)
            fx.rect(mouth_dark, (cx - mouth_w // 2, mouth_top, mouth_w, max(1, gap)))
            if mouth > 0.02:
                if mouth > 0.3:
                    flame_r = max(2, int(rr * 0.18 * mouth))
                    fx.circle(teal, (cx, mouth_top + gap // 2), flame_r)
                teeth = 5
                for k in range(teeth):
                    tx = cx + (k - (teeth - 1) / 2) * int(rr * 0.15)
                    tw = max(2, int(rr * 0.09))
                    th = max(2, int(rr * 0.13))
                    fx.rect(bone, (tx - tw // 2, mouth_top - th // 2, tw, th))
                    fx.rect(bone, (tx - tw // 2, mouth_bottom - th // 2, tw, th))
                fx.rect(purple, (cx - mouth_w // 2, mouth_top,
                                 mouth_w, max(1, gap)), 1)

            # 下颌骨（随开口下移）
            jaw_cy = int(cy + rr * 0.62 + gap)
            fx.ellipse(bone, (cx - int(rr * 0.55), jaw_cy - int(rr * 0.30),
                              int(rr * 1.10), int(rr * 0.60)))
            fx.ellipse(purple, (cx - int(rr * 0.55), jaw_cy - int(rr * 0.30),
                                int(rr * 1.10), int(rr * 0.60)), 1)

            # 颅骨外轮廓（紫色描边）
            fx.circle(purple, (cx, int(cy - rr * 0.32)), int(rr * 0.78), 1)
            for sx in (-1, 1):
                fx.circle(purple, (cx + sx * int(rr * 0.42), int(cy + rr * 0.10)),
                          int(rr * 0.42), 1)

            # 整体淡入淡出 / 缩放后贴回屏幕
            out = fx
            if scale != 1.0:
                side = max(1, int(size * scale))
                out = _hi_scale(fx, (side, side))
            hires.blit_entity(screen, out,
                              (px - out.get_width() // 2,
                               py - out.get_height() // 2), alpha=alpha)

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
                hires.blit_entity(screen, glow, (px - glow.get_width() // 2,
                                                 py - glow.get_height() // 2))
            # 存活期间缓慢呼吸的紫色外环
            pulse = 0.5 + 0.5 * math.sin(now * 0.006 + mask.get("phase", 0.0))
            ring_r = int(height * 0.58 + pulse * 5)
            fx = hires.entity_effect(screen, (px - ring_r - 3, py - ring_r - 3),
                                     (ring_r * 2 + 6, ring_r * 2 + 6))
            fx.circle(color, (px, py), ring_r, 1)
            fx.commit()
            sprite = _entity_sprite(cfg.STAGE3_BONZO_MASK_SPRITE, height, screen)
            if sprite is None:
                continue
            hires.blit_entity(screen, sprite,
                              (px - sprite.get_width() // 2,
                               py - sprite.get_height() // 2),
                              alpha=alpha, add=True)

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
            fx = hires.entity_effect(screen, (cx - r - 2, cy - r - 2),
                                     (r * 2 + 4, r * 2 + 4))
            fx.circle(bright, (cx, cy), r, 2)
            fx.circle(dim, (cx, cy), int(r * 0.82), 1)
            rot = now * 0.0012
            for i in range(8):
                a = rot + i * math.tau / 8
                x0 = cx + math.cos(a) * r * 0.60
                y0 = cy + math.sin(a) * r * 0.60
                x1 = cx + math.cos(a) * r * (0.90 + pulse * 0.08)
                y1 = cy + math.sin(a) * r * (0.90 + pulse * 0.08)
                fx.line(dim, (x0, y0), (x1, y1), 1)
            fx.circle(bright, (cx, cy), 4, 0)
            fx.commit()

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
                hires.blit_entity(screen, glow,
                                  (px - glow.get_width() // 2,
                                   py - glow.get_height() // 2))

            # 当前主攻成员：脉冲光环 + 高亮小核。
            if active:
                pulse = 0.5 + 0.5 * math.sin(now * 0.008 + idx * 0.9)
                ring_r = int(height * 0.58 + pulse * 7)
                fx = hires.entity_effect(screen, (px - ring_r - 2, py - ring_r - 2),
                                         (ring_r * 2 + 4, ring_r * 2 + 4))
                fx.circle(color, (px, py), ring_r, 2)
                fx.circle((255, 255, 255), (px, py), max(3, ring_r - 6), 1)
                fx.circle((255, 255, 255), (px, py), 3, 0)
                fx.commit()

            sprite = _entity_sprite(member["sprite"], height, screen)
            if sprite is not None:
                hires.blit_entity(screen, sprite,
                                  (px - sprite.get_width() // 2,
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
                fx = hires.entity_effect(screen, (px - 26, py - 26), (52, 52))
                self._draw_revival_circle(fx, px, py, prog, (206, 126, 74), now)
                fx.commit()
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
            pad = width + 2
            fx = hires.entity_effect(screen, (cx - r - pad, cy - r - pad),
                                     (r * 2 + pad * 2, r * 2 + pad * 2))
            fx.circle(color, (cx, cy), max(1, r), width)
            if r > 7:
                fx.circle(color, (cx, cy), max(1, r - 6), 1)
            fx.commit()

        # Telegraph: player can identify the next giant and its fixed spawn slot.
        telegraph = state.get("telegraph")
        if telegraph:
            px = int(telegraph["x"] + offset_x)
            py = int(telegraph["y"] + offset_y)
            pulse = 0.5 + 0.5 * math.sin(now * 0.012 + telegraph.get("phase", 0.0))
            radius = int(telegraph.get("radius", 30) + pulse * 8)
            color = telegraph.get("color", (255, 220, 150))
            fx = hires.entity_effect(screen, (px - radius - 3, py - radius - 3),
                                     (radius * 2 + 6, radius * 2 + 6))
            fx.circle(color, (px, py), radius, 2)
            fx.circle((255, 255, 255), (px, py), max(4, radius - 7), 1)
            fx.circle(color, (px, py), 4, 0)
            fx.commit()
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
            fx = hires.entity_effect(screen, (bx - half - 3, by - half - 3),
                                     (half * 2 + 6, half * 2 + 6))
            fx.rect((120, 205, 255),
                    (bx - half, by - half, half * 2, half * 2), 3)
            fx.rect((230, 245, 255),
                    (bx - half + 3, by - half + 3,
                     half * 2 - 6, half * 2 - 6), 1)
            fx.commit()

        # Diamond Giant's falling sword is visual-only; the landing burst is
        # created by stage4 when its y coordinate reaches land_y.
        sword = state.get("sword")
        if sword:
            sx = int(sword.get("x", cfg.BATTLE_AREA_WIDTH / 2) + offset_x)
            sy = int(sword.get("y", -200) + offset_y)
            sword_sprite = _get_sadan_sword_sprite(
                sword.get("sprite"), int(sword.get("height", 660)),
                sharp=hires.entity_factor(screen) > 1)
            if sword_sprite is not None:
                hires.blit_entity(screen, sword_sprite,
                                  (sx - sword_sprite.get_width() // 2,
                                   sy - sword_sprite.get_height() // 2))
            else:
                half_w = 18
                sword_h = int(sword.get("height", 660))
                fx = hires.entity_effect(
                    screen, (sx - half_w - 2, sy - sword_h - 2),
                    (half_w * 2 + 4, sword_h + 4))
                fx.rect((140, 215, 255),
                        (sx - half_w, sy - sword_h, half_w * 2, sword_h), 3)
                fx.commit()

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
        sprite = _entity_sprite(sprite_path, height, screen) if sprite_path else None

        glow = _get_watcher_glow(int(height * 0.85), color)
        if glow is not None:
            hires.blit_entity(screen, glow,
                              (px - glow.get_width() // 2,
                               py - glow.get_height() // 2), alpha=alpha)

        if sprite is not None:
            hires.blit_entity(screen, sprite,
                              (px - sprite.get_width() // 2,
                               py - sprite.get_height() // 2), alpha=alpha)
        else:
            # Distinct colored silhouette fallback if a sprite is missing.
            hw = max(1, int(height * 0.22))
            hh = max(1, int(height * 0.50))
            fx = hires.entity_effect(screen, (px - hw - 2, py - hh - 2),
                                     (hw * 2 + 4, hh * 2 + 4))
            fx.ellipse(color, (px - hw, py - hh, hw * 2, hh * 2))
            fx.circle(color, (px, py - int(height * 0.36)),
                      max(1, int(height * 0.14)), 0)
            fx.commit(alpha=alpha)

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
            fill_w = int(bar_w * min(1.0, hp / max_hp))
            fx = hires.entity_effect(screen, (bar_x - 1, bar_y - 1),
                                     (bar_w + 2, bar_h + 2))
            fx.rect((24, 26, 36), (bar_x, bar_y, bar_w, bar_h))
            fx.rect(color, (bar_x, bar_y, fill_w, bar_h))
            fx.rect(cfg.COLOR_WHITE, (bar_x, bar_y, bar_w, bar_h), 1)
            fx.commit()

    def _draw_sadan_laser_visual(self, screen, laser, now, offset_x=0, offset_y=0):
        """Draws L.A.S.R.'s warning line and eye source without re-adding collision.

        光束线走 hires.entity_line：长线整条一块面板的话，面板面积是长度平方级
        （一条 900 逻辑像素的斜线在 3x 下就是 20MB 的贴图，每帧重传一次），切成
        若干段后每段一块小面板，总开销只正比于线长，线本身仍按倍率画。
        """
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
            hires.entity_line(screen, bright, (x, y), (ex, ey), 5)
            hires.entity_line(screen, (255, 255, 255), (x, y), (ex, ey), 1)
        elif phase == "active":
            hires.entity_line(screen, color, (x, y), (ex, ey), 8)
            fx = hires.entity_effect(screen, (x - 7, y - 7), (14, 14))
            fx.circle((255, 255, 255), (x, y), 5, 0)
            fx.commit()
        elif phase == "recover":
            hires.entity_line(screen, color, (x, y), (ex, ey), 2)

        if phase in ("warn", "active", "recover"):
            r = 6 if phase == "active" else 5
            fx = hires.entity_effect(screen, (x - r - 2, y - r - 2),
                                     (r * 2 + 4, r * 2 + 4))
            fx.circle(color, (x, y), r, 1)
            fx.commit()

    def _draw_terracotta_soldier(self, screen, px, py, s, now, alpha=255,
                                 attack_active=False):
        """兵马俑贴图渲染；贴图缺失时回退到简单陶土人形。"""
        sprite_path = s.get("sprite", cfg.STAGE4_TERRACOTTA_SPRITE)
        height = s.get("sprite_height", 38)
        sprite = _entity_sprite(sprite_path, height, screen)

        if sprite is not None:
            hires.blit_entity(screen, sprite,
                              (px - sprite.get_width() // 2,
                               py - sprite.get_height() // 2), alpha=alpha)
        else:
            fx = hires.entity_effect(screen, (px - 12, py - 20), (24, 40))
            fx.ellipse((35, 25, 22), (px - 11, py - 12, 22, 26))
            fx.rect((196, 112, 62), (px - 7, py - 6, 14, 18), radius=4)
            fx.circle((196, 112, 62), (px, py - 12), 7)
            fx.commit(alpha=alpha)

        if attack_active and alpha >= 255:
            pulse = 0.5 + 0.5 * math.sin(now * 0.012 + px * 0.03)
            ring = int(14 + pulse * 3)
            fx = hires.entity_effect(screen, (px - ring - 2, py - ring - 2),
                                     (ring * 2 + 4, ring * 2 + 4))
            fx.circle((255, 190, 120), (px, py), ring, 1)
            fx.commit()

    def _draw_terracotta_skull(self, screen, px, py, timer, down_time):
        """被击破后留在原阵位的石质头骨标记，外圈显示复活进度。"""
        base = (122, 102, 88)
        dark = (40, 34, 30)
        light = (188, 146, 106)

        fx = hires.entity_effect(screen, (px - 14, py - 14), (28, 28))
        fx.ellipse((45, 38, 33), (px - 9, py - 8, 18, 18))
        fx.circle(base, (px, py), 9)
        fx.rect(base, (px - 6, py + 1, 12, 7), radius=2)
        fx.circle(dark, (px - 3, py - 2), 2)
        fx.circle(dark, (px + 3, py - 2), 2)
        fx.line(dark, (px - 2, py + 6), (px + 2, py + 6), 1)

        prog = min(1.0, timer / max(1, down_time))
        rect = (px - 12, py - 12, 24, 24)
        start = math.pi / 2
        end = start + math.tau * prog
        fx.arc(light, rect, start, end, 2)
        fx.commit()

    def _draw_boss_body(self, screen, px, py):
        """Boss 本体（八角形 + 魔法阵光环）"""
        r = self.size
        points = []
        for i in range(8):
            angle = i * math.pi / 4
            points.append((px + math.cos(angle) * r, py + math.sin(angle) * r))
        pad = 12
        fx = hires.entity_effect(screen, (px - r - pad, py - r - pad),
                                 (r * 2 + pad * 2, r * 2 + pad * 2))
        fx.polygon(self.color, points, 0)
        fx.polygon(cfg.COLOR_WHITE, points, 2)

        # 魔法阵光环
        glow_r = r + 6 + math.sin(pygame.time.get_ticks() * 0.003) * 3
        fx.circle(self.color, (px, py), int(glow_r), 2)
        fx.commit()

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

        # 立绘与符卡名都贴到「所有图层之上」那一层显卡指令（文字压在立绘之上，
        # 与旧版同序），透明度交给显卡调制：原先每帧把 1728x1728 的立绘与两份
        # 3x 文字贴进 2880x2160 的高分辨率图层，实测 5.3ms/帧 —— 横幅 100 帧
        # 就是 0.3s 的纯卡顿。没有显卡路径时退回画布（表面级 alpha，观感一致）。
        blit_top = getattr(screen, "blit_gpu_top", None)

        def _blit_banner(surface, dest, a):
            if blit_top is not None:
                blit_top(surface, dest, a)
            else:
                surface.set_alpha(None if a >= 255 else a)
                screen.blit(surface, dest)

        # 整幅立绘（等比放大铺满战斗区域中部）
        if self.sprite_path:
            banner_h = _banner_target_height(self.sprite_path)
            sprite = _get_boss_sprite(self.sprite_path, banner_h, sharp=True)
            if sprite is not None:
                _blit_banner(sprite,
                             (cx - sprite.get_width() // 2,
                              cy - sprite.get_height() // 2), alpha)

        # 符卡名（居中，加粗 + 下方投影，无底框）
        if self.spell_banner_name:
            # 投影 + 白字按符卡名缓存一份自己的副本（逐帧只调透明度，
            # 不动字体内部的字形缓存表面）
            shadow, text = _get_banner_text(self.spell_banner_name, self.color)
            text_x = cx - text.get_width() // 2
            text_y = cy + 150 - text.get_height() // 2
            # 投影固定 70% 透明度（alpha=255 时是 178，永远不为 None）
            _blit_banner(shadow, (text_x + 2, text_y + 3), int(alpha * 0.7))
            _blit_banner(text, (text_x, text_y), alpha)

    # --- 阶段血环 ---
    #
    # 环表示当前阶段的总血量：整圈 = 「一个非符 + 紧随其后的那张符卡」的血量之和，
    # 从 12 点钟方向顺时针随掉血缩短；两段按血量比分角度（符卡段做压缩，见
    # _ring_spell_share），符卡段颜色略深作区分。Last Spell 没有非符段，整圈都是
    # 符卡色；时符没有血量，不画环。

    def _ring_card(self):
        """当前阶段对应的符卡：非符阶段是接下来要展开的那张，符卡阶段是正在展开的这张"""
        if self.phase == "spell" and self.current_spell is not None:
            return self.current_spell
        if self.current_spell_idx < len(self.spell_cards):
            return self.spell_cards[self.current_spell_idx]
        return self.last_spell

    def _ring_thresholds(self):
        """当前阶段的两段血量阈值 (开符血量, 符卡结束血量)；无法换算时返回 None"""
        card = self._ring_card()
        if card is None or card.hp_threshold is None:
            # 没有符卡（道中级 Boss）/ 没有血量阈值：整条血都算非符段，打到死为止
            return 0.0, 0.0
        if card is self.last_spell:
            # Last Spell 独立血量：开符时补满一轮，打到 0 为止（没有非符段）
            return self.max_hp * card.hp_threshold, 0.0
        if getattr(card, "time_spell", False):
            # 时符没有血量：环只画到开符那一刻，符卡段不占角度
            return self.max_hp * card.hp_threshold, self.max_hp * card.hp_threshold
        idx = None
        for i, c in enumerate(self.spell_cards):
            if c is card:
                idx = i
                break
        if idx is None:
            return None
        ns_to = self.max_hp * card.hp_threshold
        if card.end_hp_threshold is not None:
            sp_to = self.max_hp * card.end_hp_threshold
        elif idx + 1 < len(self.spell_cards):
            sp_to = self.max_hp * self.spell_cards[idx + 1].hp_threshold
        elif self.last_spell is not None:
            sp_to = self.max_hp * (self.last_spell.hp_threshold or 0.0)
        else:
            sp_to = 0.0
        return ns_to, sp_to

    def _ring_begin_non_spell(self):
        """进入非符阶段：环从当前血量铺满，非符打完（开符）时再结清这一段"""
        self._ring_from = self.hp
        self._ring_in_non_spell = True
        self._ring_ns_budget = None
        self._ring_sp_budget = None

    def _ring_begin_spell_only(self):
        """本阶段直接从符卡开始：复活直接开符 / 连续开符 / Last Spell / 练习单符"""
        self._ring_from = self.hp
        self._ring_in_non_spell = False
        self._ring_ns_budget = None
        self._ring_sp_budget = None

    def _ring_close_non_spell(self, ns_to, sp_to):
        """开符：按实际打掉的血量结清非符段，剩下的圈全归符卡段"""
        self._ring_in_non_spell = False
        if self.hp > ns_to + RING_EARLY_EPS:
            # 非符提前结束（时间触发 / 血量被抬回）：本阶段按「只有符卡」显示
            self._ring_ns_budget = 0.0
            self._ring_sp_budget = max(0.0, self.hp - sp_to)
        else:
            start = self._ring_from if self._ring_from is not None else self.hp
            self._ring_ns_budget = max(0.0, start - ns_to)
            self._ring_sp_budget = max(0.0, ns_to - sp_to)

    def _ring_geometry(self, screen):
        """环的 (半径, 厚度)：跟着立绘大小走，没有贴图时按机体尺寸兜底"""
        half = self.size * 1.6
        if self.sprite_path:
            sprite = _get_boss_sprite(self.sprite_path, self.sprite_height)
            if sprite is not None:
                half = max(sprite.get_size()) * 0.5
        radius = min(RING_RADIUS_MAX,
                     max(RING_RADIUS_MIN, half * RING_RADIUS_SPRITE_FIT + RING_RADIUS_PAD))
        return radius, RING_THICKNESS

    def _ring_state(self, screen):
        """血环绘制参数；None 表示当前不画（未开战 / 战败 / 时符 / 没有符卡）"""
        if not (self.alive and self.combat_enabled):
            return None
        if self.phase not in ("non_spell", "spell"):
            return None
        if self._is_time_spell_active():
            return None
        thresholds = self._ring_thresholds()
        if thresholds is None:
            return None
        ns_to, sp_to = thresholds
        hp = self.hp
        if self._ring_from is None:
            # 兜底：练习模式 / 调试跳转直接落在某个阶段时，环从当前血量铺起
            if self.phase == "non_spell":
                self._ring_begin_non_spell()
            else:
                self._ring_begin_spell_only()

        if self._ring_ns_budget is None or self._ring_sp_budget is None:
            if self._ring_in_non_spell and self.phase == "non_spell":
                self._ring_ns_budget = max(0.0, self._ring_from - ns_to)
                self._ring_sp_budget = max(0.0, ns_to - sp_to)
            else:
                self._ring_close_non_spell(ns_to, sp_to)
        ns_budget = self._ring_ns_budget
        sp_budget = self._ring_sp_budget

        if self._ring_in_non_spell:
            remaining_ns = min(ns_budget, max(0.0, hp - ns_to))
            remaining_sp = sp_budget
        else:
            remaining_ns = 0.0
            remaining_sp = min(sp_budget, max(0.0, hp - sp_to))
        share = _ring_spell_share(ns_budget, sp_budget)
        ns_span = (1.0 - share) * 360.0
        sp_span = share * 360.0
        consumed = 0.0
        if ns_budget > 0:
            consumed += ns_span * (1.0 - remaining_ns / ns_budget)
        else:
            consumed += ns_span
        if sp_budget > 0:
            consumed += sp_span * (1.0 - remaining_sp / sp_budget)
        consumed = min(360.0, max(0.0, consumed))

        # 与非符血条同色系：残血红 -> 黄 -> 白，符卡段整体压深一档
        ratio = max(0.0, hp / self.max_hp) if self.max_hp else 0.0
        if ratio > 0.3:
            base = cfg.COLOR_RED
        elif ratio > 0.15:
            base = cfg.COLOR_YELLOW
        else:
            base = cfg.COLOR_WHITE
        dark = tuple(int(c * RING_SPELL_DARKEN) for c in base)
        radius, thickness = self._ring_geometry(screen)
        return {"radius": radius, "thickness": thickness, "base": base, "dark": dark,
                "ns_span": ns_span, "sp_span": sp_span, "consumed": consumed}

    @staticmethod
    def _ring_point(cx, cy, radius, angle):
        """环上的点：angle 以度计，0 度在 12 点钟方向、顺时针为正"""
        rad = math.radians(angle)
        return (cx + math.sin(rad) * radius, cy - math.cos(rad) * radius)

    def _ring_fill(self, fx, cx, cy, r_in, r_out, a0, a1, color):
        """按小扇形填充一段环：a0 -> a1 顺时针（度）"""
        if a1 - a0 <= 0.01 or r_out <= r_in:
            return
        sectors = max(1, int(math.ceil((a1 - a0) / RING_ARC_STEP)))
        step = (a1 - a0) / sectors
        for i in range(sectors):
            b0 = a0 + step * i
            b1 = b0 + step
            fx.polygon(color, (
                self._ring_point(cx, cy, r_in, b0),
                self._ring_point(cx, cy, r_out, b0),
                self._ring_point(cx, cy, r_out, b1),
                self._ring_point(cx, cy, r_in, b1),
            ))

    def _draw_phase_ring(self, screen, px, py):
        """阶段血环：Boss 机体周围一圈，表示当前阶段（非符 + 符卡）的总血量"""
        state = self._ring_state(screen)
        if state is None:
            return
        radius = state["radius"]
        thickness = state["thickness"]
        outer = radius + thickness * 0.5
        inner = max(2.0, radius - thickness * 0.5)
        fx = hires.entity_effect(screen, (px - outer - 2, py - outer - 2),
                                 (outer * 2 + 4, outer * 2 + 4))
        # 底环：整圈暗色，把阶段总量（= 满圈）标出来
        self._ring_fill(fx, px, py, inner, outer, 0.0, 360.0, RING_BACK_COLOR)
        ns_span = state["ns_span"]
        consumed = state["consumed"]
        if consumed < ns_span:
            self._ring_fill(fx, px, py, inner, outer, consumed, ns_span, state["base"])
        spell_start = max(consumed, ns_span)
        if spell_start < 360.0:
            self._ring_fill(fx, px, py, inner, outer, spell_start, 360.0, state["dark"])
        fx.commit()

    def _draw_hp_bar(self, screen, y, offset_x=0):
        inset = self.hp_bar_inset          # 血条左右边距（默认 30）
        bar_w = cfg.BATTLE_AREA_WIDTH - inset * 2
        bar_h = HP_BAR_HEIGHT
        bar_x = inset + offset_x

        hp_ratio = max(0, self.hp / self.max_hp)

        if hp_ratio > 0.3:
            color = cfg.COLOR_RED
        elif hp_ratio > 0.15:
            color = cfg.COLOR_YELLOW
        else:
            color = cfg.COLOR_WHITE
        fx = hires.entity_effect(screen, (bar_x - 2, y - 3),
                                 (bar_w + 4, bar_h + 7))
        fx.rect(cfg.COLOR_DARK_GRAY, (bar_x, y, bar_w, bar_h))
        fx.rect(color, (bar_x, y, int(bar_w * hp_ratio), bar_h))
        fx.rect(cfg.COLOR_WHITE, (bar_x, y, bar_w, bar_h), 1)

        for i in range(1, 4):
            mx = bar_x + bar_w * i / 4
            fx.line(cfg.COLOR_WHITE, (mx, y - 2), (mx, y + bar_h + 2), 1)
        fx.commit()

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


# --- 魂符「Dark Queen's Soul」：逐颗成型后依次飞出的扇形弹 ---
_DQ_SOUL_FAN_PERIOD = 180
_DQ_SOUL_FAN_COUNT = 11
_DQ_SOUL_FAN_STEP = 0.14
_DQ_SOUL_FAN_RADIUS = 44
_DQ_SOUL_FAN_FORM_INTERVAL = 3
_DQ_SOUL_FAN_LAUNCH_INTERVAL = 1
_DQ_SOUL_FAN_SPEED = 3.0
_DQ_SOUL_FAN_LIFETIME = 420
_DQ_SOUL_RING_COUNT = 24
_DQ_SOUL_RING_RADIUS = 48


def _make_dark_queen_fan_state(base_angle):
    """登记一面待成型扇形弹：先逐颗出现，全部成型后按 1 帧间隔依次飞出。"""
    return {
        "angles": [
            base_angle + (i - (_DQ_SOUL_FAN_COUNT - 1) / 2) * _DQ_SOUL_FAN_STEP
            for i in range(_DQ_SOUL_FAN_COUNT)
        ],
        "index": 0,
        "form_timer": 1,
        "bullets": [],
        "launch_index": 0,
        "launch_timer": 0,
        "launch_interval": _DQ_SOUL_FAN_LAUNCH_INTERVAL,
    }


def _update_dark_queen_fan(boss, bullet_manager):
    """推进所有扇形弹：无判定成型，成型完成后逐枚激活并沿扇角飞出。"""
    states = boss.__dict__.setdefault("_dark_queen_fan_states", [])
    for state in states[:]:
        if state["index"] < len(state["angles"]):
            state["form_timer"] -= 1
            if state["form_timer"] > 0:
                continue
            idx = state["index"]
            ang = state["angles"][idx]
            if idx % 2 == 0:
                ball = create_bullet_angle(
                    boss.x + math.cos(ang) * _DQ_SOUL_FAN_RADIUS,
                    boss.y + math.sin(ang) * _DQ_SOUL_FAN_RADIUS,
                    ang, 0.0,
                    Bullet.TYPE_RICE, radius=2.4, color=cfg.COLOR_PURPLE)
            else:
                ball = create_bullet_angle(
                    boss.x + math.cos(ang) * _DQ_SOUL_FAN_RADIUS,
                    boss.y + math.sin(ang) * _DQ_SOUL_FAN_RADIUS,
                    ang, 0.0,
                    Bullet.TYPE_RICE, radius=2.4, color=(150, 60, 230))
                ball.sprite_slot = "g01_00"
            ball.manager = bullet_manager
            ball.harmless = True
            ball.angle = ang
            ball.lifetime = 9000
            bullet_manager.add_enemy_bullet(ball)
            state["bullets"].append(ball)
            state["index"] += 1
            state["form_timer"] = _DQ_SOUL_FAN_FORM_INTERVAL
        elif state["launch_index"] < len(state["angles"]):
            state["launch_timer"] -= 1
            if state["launch_timer"] > 0:
                continue
            idx = state["launch_index"]
            ball = state["bullets"][idx]
            if ball.alive:
                ang = state["angles"][idx]
                ball.harmless = False
                ball.vx = math.cos(ang) * _DQ_SOUL_FAN_SPEED
                ball.vy = math.sin(ang) * _DQ_SOUL_FAN_SPEED
                ball.angle = ang
                ball.base_speed = _DQ_SOUL_FAN_SPEED
                ball.lifetime = ball.age + _DQ_SOUL_FAN_LIFETIME
            state["launch_index"] += 1
            state["launch_timer"] = state["launch_interval"]
        else:
            states.remove(state)


def spell_dark_queen_soul(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """魂符「Dark Queen's Soul」：直接进入魂飞魄散，附加逐颗成型后依次飞出的扇形弹"""
    fans = boss.__dict__.setdefault("_dark_queen_fan_states", [])
    if timer == 1:
        fans.clear()
    if timer % _DQ_SOUL_FAN_PERIOD == 1:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        fans.append(_make_dark_queen_fan_state(base))
    _update_dark_queen_fan(boss, bullet_manager)

    # 魂飞魄散：24颗紫色大玉绕Boss一圈生成，急停后分裂出紫色米弹；紫色鳞弹飘魂游荡全场
    if timer % 80 == 0:
        for i in range(_DQ_SOUL_RING_COUNT):
            angle = i * math.tau / _DQ_SOUL_RING_COUNT
            b = create_bullet_angle(
                boss.x + math.cos(angle) * _DQ_SOUL_RING_RADIUS,
                boss.y + math.sin(angle) * _DQ_SOUL_RING_RADIUS,
                angle, 2.7,
                Bullet.TYPE_BIG, radius=5, color=(150, 60, 230))
            b.manager = bullet_manager
            b.brake = 0.03
            b.split_spec = {
                "timer": 90,
                "aimed": True,
                "count": 6,
                "spread": 0.32,
                "speed": 3.1,
                "type": Bullet.TYPE_RICE,
                "radius": 2.3,
                "color": cfg.COLOR_PURPLE,
            }
            bullet_manager.add_enemy_bullet(b)
    if timer % 9 == 0:
        angle = random.uniform(0, math.pi * 2)
        b = create_bullet_angle(boss.x, boss.y, angle, random.uniform(1.3, 2.0),
                                Bullet.TYPE_RICE, radius=2.2, color=(150, 60, 230))
        b.sprite_slot = "g01_00"
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
# 燃符「Fireball Barrage」/ 电光「Directional Lightning」/ 龙符「One with the Dragons」
# Last Spell：超符「Superiority」（Bomb 禁用、Miss 强制结束不损残机）

_DRAGON_FIRE = (255, 140, 48)        # 龙息火焰
_DRAGON_FIRE_HOT = (255, 92, 28)     # 炽热火焰
_DRAGON_FIRE_PALE = (255, 214, 120)  # 苍白火焰
_LIGHT_GOLD = (255, 214, 84)         # 麟弹螺旋金
_LIGHT_WARN = (255, 216, 88)         # 关节节点黄
_LIGHT_NODE_FILL = (255, 250, 210)   # 关节节点白芯
_LIGHT_CYAN = (140, 206, 255)        # 末影珍珠青（非符 2 使用）
_DRAGON_PURPLE = (176, 108, 240)     # 龙魂紫
_DRAGON_DEEP = (128, 64, 200)        # 深紫
_DRAGON_PALE = (232, 200, 255)       # 龙辉淡紫
_TEAL_DRAGON = (96, 216, 208)        # 末影珍珠青
_SUPER_GOLD = (255, 220, 120)        # 上位龙金
_SUPER_GOLD_DIM = (255, 186, 72)     # 暗金
_SUPER_WHITE = (255, 252, 230)       # 审判白
_SUPER_SPIRAL_INTERVAL = 6           # 双螺旋每轮发射间隔（帧）
_SUPER_BIG_INTERVAL = _SUPER_SPIRAL_INTERVAL * 2  # 大玉频率减半（总数量减半）
_SUPER_SPIRAL_RATE = 0.085           # 发射角每帧旋转量（弧度/帧）
_SUPER_BIG_SPIRAL_RATE = _SUPER_SPIRAL_RATE * 2  # 大玉发射角旋转量（小弹的 2 倍）
_SUPER_FAST_ARMS = 8                 # 加速小弹臂数
_SUPER_BIG_ARMS = 6                  # 减速大玉臂数
_SUPER_FAST_SPEED = 2.0              # 小弹初速
_SUPER_FAST_ACCEL = 0.010            # 小弹每帧加速度
_SUPER_BIG_SPEED = 6.0               # 大玉初速
_SUPER_BIG_BRAKE = 0.018             # 大玉每帧减速度
_SUPER_BIG_BRAKE_FLOOR = 1.2         # 大玉减速后的保留速度（确保寿命内可抵达底部）
_SUPER_BULLET_RADIUS = 2.6           # 小弹半径
_SUPER_BIG_RADIUS = _SUPER_BULLET_RADIUS * 3.0  # 大玉为小弹的 3 倍（上一版 1.5 倍再翻倍）


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


def _add_gagouji_scale(bullet_manager, x, y, angle, lifetime=9000):
    """在 (x, y) 放置一颗沿 angle 方向的金色麟弹。"""
    bullet = create_bullet_angle(x, y, angle, 0.0,
                                 Bullet.TYPE_RICE, radius=2.5,
                                 color=_LIGHT_GOLD)
    bullet.manager = bullet_manager
    bullet.sprite_slot = "g01_00"
    bullet.angle = angle
    bullet.lifetime = lifetime
    bullet.ignore_offscreen = True
    bullet_manager.add_enemy_bullet(bullet)
    return bullet


def _gagouji_node(bullet_manager, x, y, lifetime=9000, harmless=True):
    """独立黄色圆球：不与鳞弹折线共用坐标，也不作拐点。"""
    node = create_bullet_angle(x, y, 0, 0,
                               Bullet.TYPE_CIRCLE, radius=3.4,
                               color=_LIGHT_WARN)
    node.manager = bullet_manager
    node.fill_color = _LIGHT_NODE_FILL
    node.harmless = harmless
    node.lifetime = lifetime
    bullet_manager.add_enemy_bullet(node)


def _gagouji_ring_state(radius, count, start_angle, color):
    """登记一圈待生成的圆弹：先逐颗出现，整圈完成后才向外发射。"""
    return {
        "radius": radius,
        "count": count,
        "start_angle": start_angle,
        "color": color,
        "angles": [start_angle + i * math.tau / count
                   for i in range(count)],
        "index": 0,
        "bullets": [],
    }


def _update_gagouji_rings(boss, bullet_manager, cx, cy,
                          speed=1.35, lifetime=420):
    """逐帧生成圆弹；一圈全部生成后整圈沿半径方向向外发射。"""
    for state in boss.gagouji_forming_rings[:]:
        if state["index"] < state["count"]:
            idx = state["index"]
            ang = state["angles"][idx]
            ball = create_bullet_angle(
                cx + math.cos(ang) * state["radius"],
                cy + math.sin(ang) * state["radius"],
                ang, 0.0,
                Bullet.TYPE_CIRCLE, radius=3.0, color=state["color"])
            ball.manager = bullet_manager
            ball.harmless = True
            ball.lifetime = 9000
            bullet_manager.add_enemy_bullet(ball)
            state["bullets"].append(ball)
            state["index"] += 1

        if state["index"] >= state["count"]:
            for ball, ang in zip(state["bullets"], state["angles"]):
                if ball.alive:
                    ball.harmless = False
                    ball.vx = math.cos(ang) * speed
                    ball.vy = math.sin(ang) * speed
                    ball.angle = ang
                    ball.lifetime = ball.age + lifetime
            boss.gagouji_forming_rings.remove(state)


def _gagouji_scale_chain(bullet_manager, x0, y0, x1, y1, gap=13.0,
                         rotate_center=None):
    """沿一段直链铺麟弹；返回可整体旋转的麟弹列表。"""
    dx = x1 - x0
    dy = y1 - y0
    dist = math.hypot(dx, dy)
    if dist < 2.0:
        return []
    angle = math.atan2(dy, dx)
    steps = max(3, int(dist / gap))
    bullets = []
    for i in range(1, steps + 1):
        t = i / float(steps)
        b = _add_gagouji_scale(bullet_manager,
                               x0 + dx * t, y0 + dy * t, angle)
        if rotate_center is not None:
            cx, cy = rotate_center
            b.gagouji_base_angle = math.atan2(b.y - cy, b.x - cx)
            b.gagouji_radius = math.hypot(b.x - cx, b.y - cy)
            b.gagouji_sprite_offset = b.angle - b.gagouji_base_angle
            bullets.append(b)
    return bullets


def _gagouji_zigzag_segments(cx, cy, phase):
    """返回一条规律折角臂的每段端点：固定段长、固定转角、方向一致。"""
    ring_rx = 96.0
    ring_ry = 88.0
    px = cx + math.cos(phase) * ring_rx
    py = cy + math.sin(phase) * ring_ry

    side = 1.0
    bend = 0.70
    curl = 0.16
    length = 50.0
    length_growth = 1.10
    steps = 8
    segments = []

    for step in range(steps):
        turn_sign = side if step % 2 == 0 else -side
        direction = phase + turn_sign * bend + curl * step
        nx = px + math.cos(direction) * length
        ny = py + math.sin(direction) * length
        segments.append((px, py, nx, ny))
        px, py = nx, ny
        length *= length_growth
    return segments


def _gagouji_zigzag_arm(bullet_manager, cx, cy, phase, rotate_center=None):
    """生成一条规律折角臂：固定段长、固定转角、方向一致。"""
    bullets = []
    for x0, y0, x1, y1 in _gagouji_zigzag_segments(cx, cy, phase):
        bullets.extend(_gagouji_scale_chain(
            bullet_manager, x0, y0, x1, y1,
            rotate_center=rotate_center))
    return bullets


def spell_gagouji_cyclone(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """电光「Directional Lightning」：规律麟弹折线 + 独立黄球环。

    十五臂全部由 g01_00 麟弹铺成；中心球环与四圈独立圆弹层只按几何
    均匀摆放，不参与任何折线坐标。折线每帧生成一节，全部完成后阵列
    才开始缓慢旋转；圆弹环先逐颗生成，整圈完成后才向外发射。
    """
    cx = cfg.BATTLE_AREA_WIDTH / 2
    cy = 180.0
    boss.target_x = cx
    boss.target_y = 145

    rings = (
        (88.0, 18, 0.00, _LIGHT_WARN),
        (126.0, 24, 0.13, _LIGHT_GOLD),
        (164.0, 30, 0.27, _LIGHT_WARN),
        (202.0, 36, 0.41, _LIGHT_GOLD),
    )

    if timer == 1:
        boss.gagouji_spiral_center = (cx, cy)
        boss.gagouji_spin = 0.0
        boss.gagouji_spiral_bullets = []
        boss.gagouji_spiral_pending = []
        boss.gagouji_spiral_complete = False
        boss.gagouji_forming_rings = []

        ring_rx = 54.0
        ring_ry = 50.0
        for i in range(15):
            ang = i * math.tau / 15
            _gagouji_node(bullet_manager,
                          cx + math.cos(ang) * ring_rx,
                          cy + math.sin(ang) * ring_ry)

        arm_segments = []
        for arm in range(15):
            phase = arm * math.tau / 15
            arm_segments.append(_gagouji_zigzag_segments(cx, cy, phase))
        for step in range(len(arm_segments[0])):
            for segments in arm_segments:
                boss.gagouji_spiral_pending.append(segments[step])

        for radius, count, offset, color in rings:
            boss.gagouji_forming_rings.append(
                _gagouji_ring_state(radius, count, offset, color))
    elif timer % 75 == 0:
        ring_idx = (timer // 75 - 1) % len(rings)
        radius, count, offset, color = rings[ring_idx]
        boss.gagouji_forming_rings.append(
            _gagouji_ring_state(
                radius, count, offset + timer * 0.012, color))

    _update_gagouji_rings(boss, bullet_manager, cx, cy)

    segment_interval = 1  # 原每 3 帧一节，加快 3 倍后每帧生成一节
    if not boss.gagouji_spiral_complete and timer % segment_interval == 0:
        if boss.gagouji_spiral_pending:
            x0, y0, x1, y1 = boss.gagouji_spiral_pending.pop(0)
            boss.gagouji_spiral_bullets.extend(
                _gagouji_scale_chain(
                    bullet_manager, x0, y0, x1, y1,
                    rotate_center=(cx, cy)))
        if not boss.gagouji_spiral_pending:
            boss.gagouji_spiral_complete = True

    if boss.gagouji_spiral_complete:
        spin = boss.gagouji_spin + 0.012 * 0.25 * (2.0 / 3.0)
    else:
        spin = boss.gagouji_spin
    boss.gagouji_spin = spin
    center = boss.gagouji_spiral_center or (cx, cy)
    for bullet in boss.gagouji_spiral_bullets:
        if not bullet.alive:
            continue
        angle = bullet.gagouji_base_angle + spin
        bullet.x = center[0] + math.cos(angle) * bullet.gagouji_radius
        bullet.y = center[1] + math.sin(angle) * bullet.gagouji_radius
        bullet.angle = angle + bullet.gagouji_sprite_offset


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
    """鳞片状：多层错位米弹，先缓慢外扩到位，再快速喷出，层层叠叠如龙鳞"""
    if timer % 70 == 0:
        for layer in range(2):
            for i in range(8):
                ang = timer * 0.045 + layer * 0.55 + i * math.tau / 8 + (layer % 2) * 0.18
                b = create_bullet_angle(x, y, ang, 0.0,
                                        Bullet.TYPE_RICE, radius=2.2, color=color,
                                        lifetime=720)
                b.manager = bullet_manager
                b.orbit_center = (x, y)
                b.orbit_radius = 4
                b.orbit_angle = ang
                b.orbit_speed = 0.0
                b.orbit_grow = 0.7
                b.orbit_break = 36
                b.orbit_break_speed = 2.6
                bullet_manager.add_enemy_bullet(b)


def _dragon_main_ring(bullet_manager, boss, timer, color, speed=1.5, count=14):
    """本体旋转弹环：基角随计时缓慢旋转，逐环封堵"""
    if timer % 165 == 0:
        base = timer * 0.02
        for volley in range(3):
            base_v = base + volley * 0.08
            speed_v = speed + volley * 0.05
            for i in range(count):
                ang = base_v + i * math.tau / count
                b = create_bullet_angle(boss.x, boss.y, ang, speed_v,
                                        Bullet.TYPE_RICE, radius=2.4, color=color)
                b.manager = bullet_manager
                b.lifetime = 720
                bullet_manager.add_enemy_bullet(b)


def spell_one_with_the_dragons(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """龙符「One with the Dragons」：万龙共鸣——幻影龙群环绕/穿越 + 多层固定弹阵

    幻影龙数量随战斗推进增加（2 → 5）：偶数序环绕本体、奇数序横穿场地，
    持续释放龙翼扇形 / 鳞片短弧 / 交错龙息；本体与幻影龙同步以旋转弹环和
    大范围扩散弹封锁玩家空间，营造被龙之力量包围的压迫感。
    """
    cycle = timer % 480
    phase = 1 + cycle // 240
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
        else:
            _phantom_scale_arc(bullet_manager, x, y, timer + i * 17, color)
            if (timer + i * 41) % 150 == 0:
                base = (timer * 0.03) % math.tau
                for volley in range(3):
                    base_v = base + volley * 0.10
                    speed_v = 1.25 + volley * 0.06
                    for k in range(11):
                        ang = base_v + k * math.tau / 11
                        b = create_bullet_angle(x, y, ang, speed_v,
                                                Bullet.TYPE_CIRCLE, radius=2.6, color=color)
                        b.manager = bullet_manager
                        b.lifetime = 720
                        bullet_manager.add_enemy_bullet(b)

    # 本体攻击：随阶段逐步加密
    if phase == 0:
        _dragon_main_ring(bullet_manager, boss, timer, _DRAGON_DEEP, speed=1.25, count=7)
    elif phase == 1:
        _dragon_main_ring(bullet_manager, boss, timer, _DRAGON_PURPLE, speed=1.4, count=9)
    else:
        _dragon_main_ring(bullet_manager, boss, timer, _TEAL_DRAGON, speed=1.55, count=11)
        if cycle % 70 == 0:
            base = cycle * 0.05
            for volley in range(3):
                base_v = base + volley * 0.09
                speed_v = 1.8 + volley * 0.05
                for k in range(7):
                    ang = base_v + k * math.tau / 7
                    b = create_bullet_angle(boss.x, boss.y, ang, speed_v,
                                            Bullet.TYPE_ARROW, radius=2.8,
                                            color=_DRAGON_DEEP if k % 2 == 0 else _DRAGON_PALE)
                    b.manager = bullet_manager
                    b.lifetime = 720
                    bullet_manager.add_enemy_bullet(b)



def spell_superiority(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """超符「Superiority」(Last Spell)：正反双螺旋

    末影龙固定在战场顶部中央不动，以持续旋转的发射角迅速打出两组直线弹幕：
    正向八臂小弹沿固定方向飞行并逐步加速；反向三臂大玉沿相反方向旋转发射，
    每两轮发射一次，数量减半；六臂大玉同样保持直线并逐步减速，尺寸为小弹的 3 倍。
    """
    # 固定在战场顶部中央，不移动
    boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 112)

    if timer % _SUPER_SPIRAL_INTERVAL == 0:
        # 正向螺旋：小弹直线加速
        base = timer * _SUPER_SPIRAL_RATE
        for arm in range(_SUPER_FAST_ARMS):
            angle = base + arm * math.tau / _SUPER_FAST_ARMS
            b = create_bullet_angle(
                boss.x, boss.y, angle, _SUPER_FAST_SPEED,
                Bullet.TYPE_CIRCLE, radius=_SUPER_BULLET_RADIUS,
                color=_SUPER_GOLD if arm % 2 == 0 else _SUPER_GOLD_DIM,
                lifetime=420)
            b.manager = bullet_manager
            b.accel = _SUPER_FAST_ACCEL
            bullet_manager.add_enemy_bullet(b)

    if timer % _SUPER_BIG_INTERVAL == 0:
        # 反向螺旋：大玉直线减速，频率减半
        reverse_base = -timer * _SUPER_BIG_SPIRAL_RATE + math.pi / 4
        for arm in range(_SUPER_BIG_ARMS):
            angle = reverse_base + arm * math.tau / _SUPER_BIG_ARMS
            b = create_bullet_angle(
                boss.x, boss.y, angle, _SUPER_BIG_SPEED,
                Bullet.TYPE_BIG, radius=_SUPER_BIG_RADIUS,
                color=_SUPER_WHITE,
                lifetime=420)
            b.manager = bullet_manager
            b.brake = _SUPER_BIG_BRAKE
            b.brake_floor = _SUPER_BIG_BRAKE_FLOOR
            bullet_manager.add_enemy_bullet(b)
