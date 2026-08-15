# 三面：地下墓穴 ~ The Catacombs Floor 1
# 基于 Hypixel Skyblock 的 The Catacombs Floor 1 区域
# 道中Boss：The Watcher —— 注视之眼，召唤亡灵 + 激光反制
# 关底Boss：Bonzo —— 小丑魔术师，一阶段依次使用死符、骸符、戏符，
#           被击破后原地复活回满血，二阶段使用气符与秘仪。

import math
import random

from src.engine import settings as cfg
from src.engine.pseudo3d import Pseudo3DFloor
from src.engine.collision import circle_collision
from src.entities.enemy import EnemyWave, FairyEnemy, FairyVolleyEnemy, SpiritEnemy, GuardEnemy, GraveCasterEnemy
from src.entities.boss import Boss, SpellCard
from src.entities.bullet import Bullet, create_bullet_aimed, create_bullet_angle
from src.stages.stage1 import Stage, BOSS_BG_RAMP_TIME, FINAL_BOSS_BG_SPEED_MULT


# 道中Boss The Watcher 总血量
WATCHER_MAX_HP = 5600
# 关底Boss Bonzo 一阶段总血量：按当前段落血量倍率重算后为 19080
BONZO_MAX_HP = 21480
# Bonzo 被击破后复活回满的血量（二阶段气符 / 秘仪，保持原值不变）
BONZO_REVIVE_HP = 10000
# 二阶段重新计算血条阈值使用的 max_hp（与复活血量一致，二阶段总长度保持不变）
BONZO_REVIVE_MAX_HP = 10000


def _undead(x, y, move_pattern="descend"):
    """三面亡灵僵尸：使用第3面贴图，防御力为一面妖精的2倍"""
    fairy = FairyEnemy(x, y, move_pattern,
                       sprite_paths=cfg.STAGE3_FAIRY_SPRITES,
                       sprite_height=cfg.STAGE3_FAIRY_SPRITE_HEIGHT)
    fairy.defense = 2.0
    return fairy


def _undead_chain(x, count=10, spacing=40, start_y=-16, volley_stagger=8, lead_in=120):
    """一串亡灵：同列依次降下，入场后按极短间隔依次开火（血量削弱为当前 2/3，其余数值与普通亡灵一致）"""
    chain = [
        FairyVolleyEnemy(x, start_y - i * spacing, volley_index=i,
                         volley_stagger=volley_stagger, lead_in=lead_in,
                         sprite_paths=cfg.STAGE3_FAIRY_SPRITES,
                         sprite_height=cfg.STAGE3_FAIRY_SPRITE_HEIGHT)
        for i in range(count)
    ]
    for fairy in chain:
        fairy.defense = 2.0
        fairy.hp = fairy.max_hp = round(fairy.hp * 2 / 3)
    return chain


def _soul(x, y, move_pattern="strafe"):
    """三面墓穴幽魂：使用第3面贴图，下降推进 + 水平小幅横移"""
    spirit = SpiritEnemy(x, y, move_pattern,
                         sprite_paths=cfg.STAGE3_SPIRIT_SPRITES,
                         sprite_height=cfg.STAGE3_SPIRIT_SPRITE_HEIGHT)
    spirit.move_speed = 1.1
    spirit.move_amplitude = 2.5
    spirit.defense = 2.0
    return spirit


def _skeleton(x, y):
    """三面骷髅守卫：使用第3面贴图，防御力为一面守卫的3倍"""
    guard = GuardEnemy(x, y,
                       sprite_paths=cfg.STAGE3_GUARD_SPRITES,
                       sprite_height=cfg.STAGE3_GUARD_SPRITE_HEIGHT)
    guard.defense = 3.0
    return guard


def _caster(x, y, deploy_y=165):
    """三面墓穴唤魂者：快速下坠到部署位后缓慢下落，5 连环形弹幕齐射（弹速随存在时间递减）"""
    caster = GraveCasterEnemy(x, y, deploy_y=deploy_y,
                              sprite_paths=cfg.STAGE3_CASTER_SPRITES,
                              sprite_height=cfg.STAGE3_CASTER_SPRITE_HEIGHT)
    caster.defense = 2.0
    return caster


# ------------------------- The Watcher（道中Boss） -------------------------

def _non_spell_watcher_gaze(boss, bullet_manager, timer, player_x, player_y):
    """The Watcher non-spell: rotating lens fans, double eye rings, scanning beams, and drifting souls."""
    # Gentle floating motion keeps the eye feeling alive.
    boss.target_y = 112 + math.sin(timer * 0.012) * 5

    # Three rotating lens fans: cyan arrows with a violet rice echo.
    if timer % 26 == 0:
        base = timer * 0.055
        for arm in range(3):
            a = base + arm * math.tau / 3
            for j in range(2):
                ang = a + (j - 0.5) * 0.18
                if j == 0:
                    b = create_bullet_angle(boss.x, boss.y, ang, 2.50,
                                            Bullet.TYPE_ARROW, radius=2.6,
                                            color=(120, 220, 235))
                else:
                    b = create_bullet_angle(boss.x, boss.y, ang, 2.05,
                                            Bullet.TYPE_RICE, radius=2.2,
                                            color=(155, 95, 220))
                bullet_manager.add_enemy_bullet(b)

    # Two interleaved slow eye rings with a soft wobble.
    if timer % 150 == 0:
        base = timer * 0.02
        for ring in range(2):
            for i in range(13):
                a = base + ring * math.pi / 13 + i * math.tau / 13
                b = create_bullet_angle(boss.x, boss.y, a, 1.70,
                                        Bullet.TYPE_CIRCLE, radius=2.4,
                                        color=(96, 216, 208) if ring == 0 else (150, 116, 188))
                b.wobble_amp = 8
                b.wobble_freq = 0.04
                bullet_manager.add_enemy_bullet(b)

    # Rotating scanning eye beams, symmetric rather than aimed.
    if timer % 72 == 0:
        base = timer * 0.035
        for side in (0.0, math.pi):
            a = base + side
            b = create_bullet_angle(boss.x, boss.y, a, 0.0,
                                    Bullet.TYPE_BEAM, radius=3, color=(110, 215, 230))
            b.manager = bullet_manager
            b.angle = a
            b.beam_length = 430
            b.lifetime = 26
            b.sprite_slot = "s12"
            bullet_manager.add_enemy_bullet(b)

    # Drifting undead soul drops, loosely spread below the eye.
    if timer % 60 == 0:
        center_x = max(70, min(cfg.BATTLE_AREA_WIDTH - 70,
                               boss.x + random.uniform(-75, 75)))
        for k in range(2):
            b = create_bullet_angle(center_x + k * 22, -14, math.pi / 2,
                                    random.uniform(1.9, 2.6),
                                    Bullet.TYPE_CIRCLE, radius=2.3,
                                    color=(150, 205, 110))
            b.wobble_amp = 16
            b.wobble_freq = 0.03
            bullet_manager.add_enemy_bullet(b)
# ------------------------- The Watcher：展符「Undead Exhibition」 -------------------------
# 展符参数集中区（方便后续调整难度）：所有可调项集中在 _WATCHER_EXHIBITION
_WATCHER_EXHIBITION = {
    # —— 符卡总览（帧，60FPS）——
    "spell_duration": 3600,      # 符卡设计时长（实际以血量结束，约 60s）

    # —— 亡灵展品：屏幕上方固定一排亡灵幻影（x 中心坐标, 贴图, 显示高度）——
    "exhibit_y": 38,             # 展品基准 y（战场坐标，两侧按下方 y 偏移成微弧形）
    "exhibits": [
        (96, cfg.STAGE3_WATCHER_SUMMONINGS[0], 56, 8),    # Cannibal（外侧下移，微弧形）
        (192, cfg.STAGE3_WATCHER_SUMMONINGS[8], 56, 4),   # Skull
        (288, cfg.STAGE3_WATCHER_SUMMONINGS[2], 56, 0),   # Frost
        (384, cfg.STAGE3_WATCHER_SUMMONINGS[6], 56, 4),   # Putrid
        (480, cfg.STAGE3_WATCHER_SUMMONINGS[11], 56, 8),  # Walker（外侧下移，微弧形）
    ],

    # —— 密集扇形骨弹：每具亡灵以正下方为中心 ±fan_half_angle 的扇形齐射 ——
    # 单具亡灵在屏幕底部铺成一条竖直弹柱；相邻亡灵弹柱重叠 → 中间封锁，
    # 弹柱之外的两侧保留贴边通道，到屏幕最下方中间无法穿过。
    "fan_half_angle": math.radians(5),   # 扇形半角（弧度）；越大弹柱越宽、两侧通道越窄
    "fan_curve": 0.0012,                 # 扇形弯曲度：离中心越远的骨弹越向外弯（弧度/帧·弧度偏角）
    "fan_gap_chance": 0.4,               # 扇形随机留出可穿过小缝隙的概率（部分扇形有缺口）
    "fan_gap_size": (3, 5),              # 缺口连续抽掉的发数（越往下缺口越宽，底部约 25~40px）
    "fan_big_chance": 1 / 3,             # 扇形被替换为“两颗大玉、中间空当”的概率
    "fan_big_angle": math.radians(4),    # 两颗大玉相对正下方的偏角（中间留出可穿空当）
    "fan_big_radius": 4,                 # 大玉半径（判定按图集，深紫亡灵能量）

    # —— 缝隙大玉：带缺口扇形在缺口正中放一颗可被玩家子弹击破的大玉 ——
    "fan_orb_radius": 4,                 # 缝隙大玉半径（图集渲染，深紫亡灵能量）
    "fan_orb_hp": 10,                    # 生命值（玩家弹单发伤害 10，1 发击破）
    "fan_orb_explode_radius": 80,        # 击破后爆炸清弹半径（px），范围内玩家也受伤

    # —— The Watcher 本体环形弹：自身发出的深紫亡灵能量环（少量、固定弹、不追踪） ——
    "boss_ring_start": 90,            # 第一环出现的帧（开符 1.5s 后）
    "boss_ring_step": 170,            # 每环间隔（帧，约 2.8s 一环，少量）
    "boss_ring_count": 14,            # 每环弹数（下一环整体旋转半个弹距，交错互补）
    "boss_ring_speed": 1.7,           # 弹速（px/帧，偏慢）
    "boss_ring_radius": 3,            # 弹半径
    "boss_ring_color": (150, 70, 210),  # 深紫亡灵能量

    # —— 三阶段节奏（帧）：阶段1 单体 → 阶段2 双体 → 阶段3 全员持续五射 ——
    "phase1_end": 250,           # 阶段1结束帧：单体随机激活（每 25 帧随机一具）
    "phase2_end": 550,           # 阶段2结束帧：双体随机激活（每 30 帧随机两具，其后进入全员五射）
    "p3_cycle": 180,             # 阶段3：全员轮番齐射的周期（帧），每轮 5 具随机顺序错发，直到击破

    # —— 阶段1：单体随机激活，单具亡灵一面密集扇 ——
    "p1_step": 25,               # 每轮间隔（帧，250/25=10 轮，随机单体，频率翻倍）
    "p1_warn": 12,               # 预警提前量（帧）
    "p1_count": 20,              # 扇形骨弹数（单具亡灵弹柱内铺满）
    "p1_speed": 1.9,             # 弹速（px/帧，偏慢）

    # —— 循环2：两具同时激活，相位互补形成更密的交错扇墙 ——
    "p2_step": 30,               # 每轮间隔（帧，300/30=10 轮，频率翻倍）
    "p2_warn": 14,               # 预警提前量（帧）
    "p2_active": 2,              # 每轮同时激活的亡灵数（随机两具）
    "p2_count": 22,              # 每具亡灵扇形骨弹数（相位互补后弹柱内双倍加密）
    "p2_speed": 2.1,

    # —— 循环3：全员轮番齐射，5 具亡灵按固定间隔错开发射，不成无缝整墙 ——
    "p3_warn": 40,               # 首位亡灵齐射前预警（帧）
    "p3_stagger": 26,            # 各亡灵发射间隔（帧，5 具约 1.7s 轮番压完）
    "p3_count": 20,              # 每具亡灵扇形骨弹数（相位互补加密单柱）
    "p3_speed": 2.3,

    # —— 弹幕视觉 ——
    "bone_color": (250, 246, 235),   # 白色骨弹
    "bone_radius": 3,
    "soul_color": (120, 205, 255),   # 幽蓝灵魂火
    "soul_purple": (150, 70, 210),   # 深紫亡灵能量
    "warn_color": (130, 220, 255),   # 幽蓝预警
    "glow_color": (70, 120, 220),    # 展品常驻亡灵能量光晕
    "flash_color": (210, 240, 255),  # 发射光效
}


def _watcher_fire_flash(bullet_manager, x, y):
    """发射瞬间的短暂光效：白芯青光一闪"""
    f = create_bullet_angle(x, y, 0.0, 0.0, Bullet.TYPE_CIRCLE,
                            radius=11, color=_WATCHER_EXHIBITION["flash_color"])
    f.manager = bullet_manager
    f.harmless = True
    f.lifetime = 7
    bullet_manager.add_enemy_bullet(f)


def _watcher_warning(bullet_manager, ex, warn_frames):
    """激活预警：幽蓝光束指向发射方向 + 点亮展品（Boss 绘制脉冲光环）"""
    ex["warn"] = True
    beam = create_bullet_angle(ex["x"], ex["y"], math.pi / 2, 0.0,
                               Bullet.TYPE_BEAM, radius=3,
                               color=_WATCHER_EXHIBITION["warn_color"])
    beam.manager = bullet_manager
    beam.angle = math.pi / 2
    beam.beam_length = 96
    beam.sprite_slot = "s12"
    beam.harmless = True
    beam.lifetime = warn_frames
    bullet_manager.add_enemy_bullet(beam)
    # 预警光点：展品核心持续亮起的幽蓝光
    p = create_bullet_angle(ex["x"], ex["y"], 0.0, 0.0, Bullet.TYPE_CIRCLE,
                            radius=10, color=_WATCHER_EXHIBITION["warn_color"])
    p.manager = bullet_manager
    p.harmless = True
    p.lifetime = warn_frames
    bullet_manager.add_enemy_bullet(p)


def _watcher_clear_warn(ex):
    """预警结束：熄灭展品高亮"""
    ex["warn"] = False


def _watcher_soul_burst(bullet_manager, x, y, count=6):
    """展品出现时的灵魂粒子：向四周飘散的幽蓝/深紫光点"""
    for i in range(count):
        ang = i * math.tau / count + random.uniform(-0.35, 0.35)
        speed = random.uniform(0.8, 1.7)
        color = random.choice((_WATCHER_EXHIBITION["soul_color"],
                               _WATCHER_EXHIBITION["soul_purple"]))
        b = create_bullet_angle(x, y, ang, speed, Bullet.TYPE_CIRCLE,
                                radius=2, color=color)
        b.manager = bullet_manager
        b.harmless = True
        b.lifetime = random.randint(26, 44)
        bullet_manager.add_enemy_bullet(b)


def _watcher_lane_fan(bullet_manager, x, y, count, speed, phase=0.0):
    """密集扇形骨弹：以正下方为中心 ±fan_half_angle 的扇形齐射。

    单具亡灵在屏幕底部铺成一条竖直弹柱，弹道略微外弯呈弧扇形；相邻亡灵
    弹柱重叠 → 中间封锁，弹柱之外保留贴边通道。部分扇形会随机抽掉连续几发
    留出可穿过的小缝隙（越往下越宽），缝隙正中放一颗可被玩家子弹击破的大玉，
    击破后爆炸清掉周围弹幕（玩家在爆炸范围内也会受伤）；另有概率整面扇形被
    替换为两颗中间有空当的大玉。多具亡灵以不同 phase 错位互补。
    """
    P = _WATCHER_EXHIBITION
    # 概率替换：两颗中间有空当的大玉（深紫亡灵能量）
    if P["fan_big_chance"] > 0 and random.random() < P["fan_big_chance"]:
        off = P["fan_big_angle"]
        for side in (-1, 1):
            a = math.pi / 2 + side * off
            b = create_bullet_angle(x, y, a, speed, Bullet.TYPE_BIG,
                                    radius=P["fan_big_radius"], color=P["soul_purple"])
            if P["fan_curve"]:
                b.turn_rate = P["fan_curve"] * (a - math.pi / 2)
            b.manager = bullet_manager
            bullet_manager.add_enemy_bullet(b)
        _watcher_fire_flash(bullet_manager, x, y)
        return

    half = P["fan_half_angle"]
    if count < 2:
        return
    step = (2 * half) / (count - 1)
    # 部分扇形随机留出可穿过的小缝隙：随机抽掉连续几发（不贴边）
    gap_start = gap_end = -1
    if P["fan_gap_chance"] > 0 and random.random() < P["fan_gap_chance"] and count >= 6:
        gap_size = random.randint(*P["fan_gap_size"])
        gap_start = random.randint(1, count - gap_size - 1)
        gap_end = gap_start + gap_size
    for i in range(count):
        if gap_start <= i < gap_end:
            continue
        a = math.pi / 2 - half + (i + phase) * step
        b = create_bullet_angle(x, y, a, speed, Bullet.TYPE_KNIFE,
                                radius=P["bone_radius"], color=P["bone_color"])
        if P["fan_curve"]:
            b.turn_rate = P["fan_curve"] * (a - math.pi / 2)
        b.manager = bullet_manager
        bullet_manager.add_enemy_bullet(b)
    # 缺口正中放一颗可被玩家子弹击破的大玉：击破后爆炸清弹（范围内玩家也受伤）
    if gap_start >= 0:
        gap_center = gap_start + (gap_end - gap_start) / 2.0
        a = math.pi / 2 - half + (gap_center + phase) * step
        orb = create_bullet_angle(x, y, a, speed, Bullet.TYPE_BIG,
                                  radius=P["fan_orb_radius"], color=P["soul_purple"])
        if P["fan_curve"]:
            orb.turn_rate = P["fan_curve"] * (a - math.pi / 2)
        orb.manager = bullet_manager
        orb.shootable = True
        orb.hp = P["fan_orb_hp"]
        orb.explode_radius = P["fan_orb_explode_radius"]
        bullet_manager.add_enemy_bullet(orb)
    _watcher_fire_flash(bullet_manager, x, y)


def _watcher_boss_ring(boss, bullet_manager, timer):
    """The Watcher 本体环形弹：从自身向四周放出的深紫亡灵能量环。
    每环均匀分布、不追踪玩家；下一环整体旋转半个弹距，缓慢交错成环网。"""
    P = _WATCHER_EXHIBITION
    if timer < P["boss_ring_start"]:
        return
    if (timer - P["boss_ring_start"]) % P["boss_ring_step"] != 0:
        return
    n = P["boss_ring_count"]
    ring_idx = (timer - P["boss_ring_start"]) // P["boss_ring_step"]
    base = ring_idx * (math.pi / n)   # 每环旋转半个弹距，交错互补
    for i in range(n):
        a = base + i * math.tau / n
        b = create_bullet_angle(boss.x, boss.y, a, P["boss_ring_speed"],
                                Bullet.TYPE_CIRCLE, radius=P["boss_ring_radius"],
                                color=P["boss_ring_color"])
        b.manager = bullet_manager
        bullet_manager.add_enemy_bullet(b)
    _watcher_fire_flash(bullet_manager, boss.x, boss.y)


def _watcher_phase_solo(boss, bullet_manager, t):
    """阶段1：单体随机激活——随机一具亡灵向正下方放一面密集扇形骨弹"""
    P = _WATCHER_EXHIBITION
    step = P["p1_step"]
    local = t % step
    if local == step - P["p1_warn"]:
        idx = random.randrange(len(boss.watcher_exhibits))
        boss.watcher_solo_idx = idx
        ex = boss.watcher_exhibits[idx]
        _watcher_warning(bullet_manager, ex, P["p1_warn"])
    elif local == step - 1:
        ex = boss.watcher_exhibits[boss.watcher_solo_idx]
        _watcher_clear_warn(ex)
        _watcher_lane_fan(bullet_manager, ex["x"], ex["y"],
                          P["p1_count"], P["p1_speed"])


def _watcher_phase_cross(boss, bullet_manager, t):
    """阶段2：双体随机激活——随机两具亡灵向正下方相位互补，交错成更密的扇墙"""
    P = _WATCHER_EXHIBITION
    step = P["p2_step"]
    local = t % step
    if local == step - P["p2_warn"]:
        boss.watcher_cross_active = random.sample(
            range(len(boss.watcher_exhibits)), P["p2_active"])
        for ex_idx in boss.watcher_cross_active:
            ex = boss.watcher_exhibits[ex_idx]
            _watcher_warning(bullet_manager, ex, P["p2_warn"])
    elif local == step - 1:
        for k, ex_idx in enumerate(boss.watcher_cross_active):
            ex = boss.watcher_exhibits[ex_idx]
            _watcher_clear_warn(ex)
            # 相位互补：第二具亡灵的弹位填进第一具的空隙
            _watcher_lane_fan(bullet_manager, ex["x"], ex["y"],
                              P["p2_count"], P["p2_speed"],
                              phase=k / P["p2_active"])


def _watcher_phase_climax(boss, bullet_manager, lt):
    """阶段3：全员轮番齐射并持续——每 p3_cycle 帧一轮，5 具亡灵随机顺序错发，直到符卡被击破"""
    P = _WATCHER_EXHIBITION
    n = len(boss.watcher_exhibits)
    local = lt % P["p3_cycle"]
    if local == 0:
        boss.watcher_climax_order = random.sample(range(n), n)
        for ex in boss.watcher_exhibits:
            _watcher_warning(bullet_manager, ex,
                             P["p3_warn"] + (n - 1) * P["p3_stagger"])
    for k in range(n):
        fire_t = P["p3_warn"] + k * P["p3_stagger"]
        if local == fire_t:
            ex = boss.watcher_exhibits[boss.watcher_climax_order[k]]
            _watcher_clear_warn(ex)
            _watcher_lane_fan(bullet_manager, ex["x"], ex["y"],
                              P["p3_count"], P["p3_speed"], phase=k / n)


def spell_watcher_undead_exhibition(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """展符「Undead Exhibition」：亡灵展览馆
    The Watcher 在屏幕上方召唤一排固定的亡灵幻影作为展品。每隔固定时间亡灵亮起
    幽蓝预警，随后向正下方释放极其密集的扇形骨弹——每具亡灵的弹柱在屏幕底部
    重叠封锁中间区域，越往下越密，到屏幕最下方中间完全无法穿过，只能从两侧贴边绕过：
      阶段1：单体随机激活，单具亡灵一面密集扇；
      阶段2：两具亡灵随机组合同时激活，相位互补交错成更密的扇墙；
      阶段3：全员轮番齐射并持续，5 具亡灵随机顺序错开发射、弹柱依次压下，
             到达后不再回到单体阶段，直到符卡被击破。
    带缺口的扇形会在缺口正中放一颗可被玩家子弹击破的大玉，击破后爆炸清弹
    （玩家在爆炸范围内也会受伤）。The Watcher 本体还会周期性地向四周放出
    缓慢旋转交错的深紫亡灵能量环（少量，不追踪玩家）。全程无自机狙、无随机乱射。
    """
    P = _WATCHER_EXHIBITION

    # 开符：召唤一排亡灵展品并绽放灵魂粒子
    if timer == 1:
        boss.watcher_exhibits = []
        boss.watcher_solo_idx = 0
        boss.watcher_cross_active = [0, 2]
        boss.watcher_climax_order = list(range(len(P["exhibits"])))
        for x, sprite, height, y_off in P["exhibits"]:
            boss.watcher_exhibits.append({
                "x": x, "y": P["exhibit_y"] + y_off, "sprite": sprite, "height": height,
                "warn": False,
                "glow_color": P["glow_color"], "warn_color": P["warn_color"],
            })
        for ex in boss.watcher_exhibits:
            _watcher_soul_burst(bullet_manager, ex["x"], ex["y"])
        return

    # The Watcher 悬浮观察：轻微上下浮动，不主动走位
    boss.target_y = 118 + math.sin(timer * 0.011) * 6

    t = timer
    _watcher_boss_ring(boss, bullet_manager, t)
    if t < P["phase1_end"]:
        _watcher_phase_solo(boss, bullet_manager, t)
    elif t < P["phase2_end"]:
        # 阶段2 使用相对阶段起点的局部时间
        _watcher_phase_cross(boss, bullet_manager, t - P["phase1_end"])
    else:
        # 阶段3 持续五射，直到符卡被击破，不再回到单体阶段
        _watcher_phase_climax(boss, bullet_manager, t - P["phase2_end"])


# ------------------------- Bonzo（关底Boss） -------------------------

def _non_spell_bonzo_carnival(boss, bullet_manager, timer, player_x, player_y):
    """Opening non-spell: twin rice pinwheels + two-color offset rings.

    Fixed-angle choreography, no persistent big-orb aimed barrages.
    """
    # Rotating twin pinwheels: two mirrored 4-shot fans of rice bullets.
    if timer % 22 == 0:
        base = timer * 0.043
        for arm in range(2):
            a = base + arm * math.pi
            for i in range(4):
                ang = a + (i - 1.5) * 0.20
                b = create_bullet_angle(boss.x, boss.y, ang, 2.55,
                                        Bullet.TYPE_RICE, radius=2.4,
                                        color=(245, 175, 95) if arm == 0 else (125, 215, 235))
                bullet_manager.add_enemy_bullet(b)

    # Two interleaved slow rings, offset by half a bullet gap.
    if timer % 96 == 0:
        base = timer * 0.016
        for ring in range(2):
            for i in range(11):
                ang = base + ring * math.pi / 11 + i * math.tau / 11
                b = create_bullet_angle(boss.x, boss.y, ang, 1.95,
                                        Bullet.TYPE_CIRCLE, radius=2.1,
                                        color=(250, 215, 130) if ring == 0 else (200, 130, 245))
                bullet_manager.add_enemy_bullet(b)

    # Harmless carnival sparkle ring for stage presence.
    if timer % 160 == 0:
        base = timer * 0.03
        for i in range(12):
            b = create_bullet_angle(boss.x, boss.y, base + i * math.tau / 12, 1.45,
                                    Bullet.TYPE_CIRCLE, radius=2.0, color=(255, 240, 185))
            b.harmless = True
            b.lifetime = 48
            bullet_manager.add_enemy_bullet(b)


def _non_spell_bonzo_bone_carnival(boss, bullet_manager, timer, player_x, player_y):
    """Post-dreadlord non-spell: turning bone-knife fans + delayed split flowers.

    Same fixed-choreography philosophy as the opening non-spell, with a
    colder bone-and-soul palette and denser short bursts.
    """
    # Two slowly turning 3-shot fans of knife bullets.
    if timer % 34 == 0:
        base = timer * 0.055
        for arm in range(2):
            a = base + arm * math.pi
            for i in range(3):
                b = create_bullet_angle(boss.x, boss.y, a + (i - 1) * 0.17,
                                        2.70, Bullet.TYPE_KNIFE, radius=2.2,
                                        color=(235, 235, 250) if arm == 0 else (165, 205, 255))
                b.turn_rate = 0.011 if arm == 0 else -0.011
                bullet_manager.add_enemy_bullet(b)

    # Delayed split flowers: harmless seeds bloom into non-aimed rice fans.
    if timer % 78 == 0:
        base = timer * 0.012
        for i in range(4):
            seed_angle = base + i * math.tau / 4
            seed = create_bullet_angle(boss.x, boss.y, seed_angle, 1.05,
                                       Bullet.TYPE_CIRCLE, radius=2.4,
                                       color=(215, 185, 255))
            seed.harmless = True
            seed.manager = bullet_manager
            seed.lifetime = 90
            seed.split_spec = {
                "timer": 30,
                "count": 5,
                "spread": 0.30,
                "speed": 2.25,
                "type": Bullet.TYPE_RICE,
                "radius": 2.2,
                "color": (235, 205, 255),
                "aimed": False,
                "base_angle": seed_angle,
            }
            bullet_manager.add_enemy_bullet(seed)

    # Slow wobbling bone ring.
    if timer % 135 == 0:
        base = timer * 0.02
        for i in range(14):
            b = create_bullet_angle(boss.x, boss.y, base + i * math.tau / 14, 2.05,
                                    Bullet.TYPE_KNIFE, radius=1.9,
                                    color=(205, 220, 245))
            b.wobble_amp = 10
            b.wobble_freq = 0.05
            bullet_manager.add_enemy_bullet(b)


def _non_spell_bonzo_orb(boss, bullet_manager, timer, player_x, player_y):
    """Bonzo 一阶段非符「暗之宝珠」：
    环绕暗紫大玉（公转外扩）+ 自机狙凋灵之首"""
    # 环绕暗球：公转逐渐外扩，半径超限后沿切线飞出
    if timer % 130 == 0:
        for i in range(3):
            b = create_bullet_angle(boss.x, boss.y, i * math.tau / 3, 0.0,
                                    Bullet.TYPE_BIG, radius=4, color=(150, 70, 200))
            b.orbit_center = (boss.x, boss.y)
            b.orbit_radius = 66
            b.orbit_angle = i * math.tau / 3
            b.orbit_speed = 0.028
            b.orbit_grow = 0.24
            b.orbit_break = 128
            b.orbit_break_speed = 2.4
            b.lifetime = 420
            bullet_manager.add_enemy_bullet(b)
    # 自机狙凋灵之首（大玉三连）
    if timer % 50 == 0:
        for i in range(3):
            b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 2.4 + i * 0.3,
                                    Bullet.TYPE_BIG, radius=4, color=(185, 140, 215))
            bullet_manager.add_enemy_bullet(b)


def _non_spell_bonzo_skull(boss, bullet_manager, timer, player_x, player_y):
    """Bonzo 一阶段第二非符「骷髅法术」：
    扇形凋灵之首 + 亡灵圆环"""
    # 扇形凋灵之首
    if timer % 36 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for i in range(5):
            off = (i - 2) * 0.14
            b = create_bullet_angle(boss.x, boss.y, base + off, 2.8,
                                    Bullet.TYPE_BIG, radius=4, color=(190, 150, 220))
            bullet_manager.add_enemy_bullet(b)
    # 亡灵圆环
    if timer % 90 == 0:
        n = 10
        base = timer * 0.02
        for i in range(n):
            a = base + i * math.tau / n
            b = create_bullet_angle(boss.x, boss.y, a, 1.5,
                                    Bullet.TYPE_CIRCLE, radius=2.5, color=(150, 210, 120))
            bullet_manager.add_enemy_bullet(b)


# ------------------------- Bonzo：第一符卡「死符 Undead Revival」 -------------------------
# 符卡参数集中区（方便调整难度）：所有可调项集中在 _BONZO_REVIVAL
_BONZO_REVIVAL = {
    # —— Undead 数量与生成节奏（帧，60FPS）——
    "initial_undead": 6,        # 开符时同时存在的 Undead 数量（初始翻倍：6）
    "max_undead": 10,           # 最大同时存在 Undead 数量（翻倍：10，复活只补位、不新增）
    "spawn_interval": 90,       # 补充召唤间隔（帧，约 1.5s 一具；数量翻倍后保持同样的补满节奏）

    # —— Undead 本体 ——
    "undead_hp": 60,            # 单个 Undead 生命（玩家弹单发 10，需 6 发击破）
    "undead_height": 46,        # 贴图渲染高度（px）
    "hit_radius": 15,           # 玩家弹判定半径（px）
    "summon_time": 24,          # 召唤魔法阵动画时长（帧，期间不可命中、不发射）
    "die_time": 22,             # 灵魂消散时长（帧，消散后进入复活等待）
    "revive_time": 90,          # 复活等待（帧，约 1.5s，期间展示亡灵魔法阵重组）

    # —— 固定轨迹移动（不追踪玩家）——
    "move_speed": 0.9,          # 横向/斜向轨迹速度（px/帧，较慢）
    "patrol_speed": 0.02,       # 巡逻轨迹角速度（弧度/帧）
    "patrol_amp_x": 54,         # 巡逻区域横向幅度（px）
    "patrol_amp_y": 30,         # 巡逻区域纵向幅度（px）
    "move_bounds": (44, cfg.BATTLE_AREA_WIDTH - 44, 52, cfg.BATTLE_AREA_HEIGHT // 2 - 5),
    "spawn_y_max": 300,         # 生成/复活位置最大 y（Boss 下方带，整体保持在屏幕上半）

    # —— 骨弹散射（固定方向，不自机狙）——
    "fire_interval": 58,        # 发射间隔（帧，约 0.97s，频率翻倍）
    "fire_interval_min": 20,    # 复活频率加成后的最小间隔（帧，安全下限）
    "revive_boost": 0.25,       # 每次复活：攻击频率与骨弹速度增加初始值的 25%
    "fire_stagger": 12,         # 各 Undead 首轮发射错开帧数（数量翻倍后保持总错开时长一致）
    "bone_count": 8,            # 骨弹数量（固定 8 方向散射）
    "bone_speed": 1.8,          # 骨弹速度（px/帧，较慢、弹间有空隙）
    "bone_radius": 2.6,         # 骨弹半径
    "bone_lifetime": 380,       # 骨弹存活帧数
    "bone_offset_step": math.pi / 8,  # 相邻 Undead 的散射角度错位（多体交叉成网）
    "bone_offset_jitter": 0.05,       # 每具 Undead 固定的微小随机偏角（弧度）

    # —— 复活圆弹：Undead 复活瞬间以新位置为圆心发一圈圆弹（不自机狙）——
    "revive_ring_count": 14,      # 圆弹数量
    "revive_ring_speed": 2.2,     # 圆弹速度（px/帧）
    "revive_ring_radius": 2.6,    # 圆弹半径
    "revive_ring_color": (160, 80, 220),  # 紫色亡灵能量
    "revive_ring_lifetime": 360,  # 圆弹存活帧数

    # —— 视觉 ——
    "bone_color": (250, 246, 235),     # 白色骨弹
    "soul_teal": (100, 225, 190),      # 青绿色灵魂火
    "soul_purple": (160, 80, 220),     # 紫色亡灵能量
    "summon_color": (180, 95, 235),    # 召唤/复活魔法阵主色（紫）
}


def _revival_pick_spawn(boss, player_x, player_y, P):
    """选取 Undead 生成位置：约八成在 Bonzo 下方的全宽均匀带（x 横向铺开、
    不聚在正下方），约两成来自屏幕上方；全部保持在屏幕上半（y <= spawn_y_max），
    玩家下方的下半屏始终留空。拒绝采样保证不贴脸。"""
    W, H = cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT
    y_top = P["spawn_y_max"]
    for _ in range(40):
        if random.random() < 0.8:
            # 下方均匀带：x 全宽均匀分布，y 在 Boss 下方到上半屏下限之间均匀分布
            x = random.uniform(60, W - 60)
            y = random.uniform(boss.y + 55, y_top)
        else:
            # 少量屏幕上方（保留召唤来源的多样性）
            x = random.uniform(56, W - 56)
            y = random.uniform(60, 110)
        if (math.hypot(x - player_x, y - player_y) >= 120
                and 40 < x < W - 40 and 40 < y < H - 40):
            return x, y
    # 兜底：下方均匀带内
    return random.uniform(60, W - 60), min(y_top, boss.y + 70)


def _revival_new_route(u, P):
    """为 Undead 分配固定轨迹（巡逻 / 横向 / 缓慢斜向），不追踪玩家。"""
    u["route"] = random.choice(("patrol", "horizontal", "diagonal"))
    speed = P["move_speed"]
    if u["route"] == "horizontal":
        u["vx"] = random.choice((-1, 1)) * speed
        u["vy"] = 0.0
    elif u["route"] == "diagonal":
        ang = random.uniform(-0.55, 0.55)
        d = random.choice((-1, 1))
        u["vx"] = math.cos(ang) * speed * d
        u["vy"] = math.sin(ang) * speed * d
    else:
        u["vx"] = u["vy"] = 0.0


def _revival_make_undead(index, spawn_pos, P):
    """创建一具 Undead。

    Undead 生命周期状态机：
      summoning（召唤魔法阵） -> active（移动+发射，可被击破）
      -> dying（灵魂消散） -> reviving（亡灵魔法阵重组等待）
      -> summoning -> active ...（复活后换位、攻击频率与弹速各提升初始 25%，并发出圆弹环）
    """
    x, y = spawn_pos
    u = {
        "sprite": random.choice(cfg.STAGE3_WATCHER_SUMMONINGS),
        "height": P["undead_height"],
        "x": x, "y": y,
        "phase": "summoning",
        "timer": 0,
        "hp": P["undead_hp"],
        "max_hp": P["undead_hp"],
        "revives": 0,
        "fire_interval": P["fire_interval"],
        "bone_speed": P["bone_speed"],   # 当前骨弹速度（复活后按 revive_boost 逐次提升）
        # 首轮发射错开：避免全屏 Undead 同时齐射，便于观察与预判
        "fire_timer": P["fire_interval"] + index * P["fire_stagger"],
        # 固定散射偏置：多具 Undead 弹道错开、交叉成网（复活后保持不变，保持可预测）
        "angle_offset": index * P["bone_offset_step"]
                        + random.uniform(-P["bone_offset_jitter"], P["bone_offset_jitter"]),
        "home": (x, y),
        "summon_time": P["summon_time"],
        "die_time": P["die_time"],
        "revive_time": P["revive_time"],
        "glow_color": P["soul_purple"],
        "summon_color": P["summon_color"],
        "soul_color": P["soul_teal"],
    }
    _revival_new_route(u, P)
    return u


def _revival_move_undead(u, P):
    """固定轨迹移动：巡逻绕固定区域 / 横向 / 缓慢斜向，撞边界反弹（不追踪玩家）。"""
    x0, x1, y0, y1 = P["move_bounds"]
    if u["route"] == "patrol":
        t = u["timer"] * P["patrol_speed"]
        hx, hy = u["home"]
        u["x"] = hx + math.sin(t) * P["patrol_amp_x"]
        u["y"] = hy + math.cos(t * 0.6) * P["patrol_amp_y"]
        return
    u["x"] += u["vx"]
    u["y"] += u["vy"]
    if u["x"] <= x0:
        u["x"] = x0
        u["vx"] = abs(u["vx"])
    elif u["x"] >= x1:
        u["x"] = x1
        u["vx"] = -abs(u["vx"])
    if u["y"] <= y0:
        u["y"] = y0
        u["vy"] = abs(u["vy"])
    elif u["y"] >= y1:
        u["y"] = y1
        u["vy"] = -abs(u["vy"])


def _revival_fire_flash(bullet_manager, x, y, P):
    """发射瞬间的青绿灵魂火一闪（纯视觉）"""
    f = create_bullet_angle(x, y, 0.0, 0.0, Bullet.TYPE_CIRCLE,
                            radius=9, color=P["soul_teal"])
    f.manager = bullet_manager
    f.harmless = True
    f.lifetime = 6
    bullet_manager.add_enemy_bullet(f)


def _revival_soul_burst(bullet_manager, x, y, P, count=6):
    """灵魂粒子：青绿/紫色光点向四周飘散（出现/消散/复活用，纯视觉）"""
    for i in range(count):
        ang = i * math.tau / count + random.uniform(-0.4, 0.4)
        speed = random.uniform(0.7, 1.6)
        color = random.choice((P["soul_teal"], P["soul_purple"]))
        b = create_bullet_angle(x, y, ang, speed, Bullet.TYPE_CIRCLE,
                                radius=2, color=color)
        b.manager = bullet_manager
        b.harmless = True
        b.lifetime = random.randint(24, 42)
        bullet_manager.add_enemy_bullet(b)


def _revival_boss_cast_flash(bullet_manager, boss, P):
    """Bonzo 施法光效：紫色能量波动（提示“是 Bonzo 在召唤”）"""
    f = create_bullet_angle(boss.x, boss.y, 0.0, 0.0, Bullet.TYPE_CIRCLE,
                            radius=16, color=P["soul_purple"])
    f.manager = bullet_manager
    f.harmless = True
    f.lifetime = 8
    bullet_manager.add_enemy_bullet(f)


def _revival_fire_volley(bullet_manager, u, P):
    """骨弹散射：向固定 8 方向发射白色骨弹（不自机狙）。

    每具 Undead 拥有固定的角度偏置 angle_offset —— 多具同时在场时
    弹道错开、彼此交叉成网；玩家观察 Undead 位置即可预判走位。
    """
    base = u["angle_offset"]
    for i in range(P["bone_count"]):
        a = base + i * math.tau / P["bone_count"]
        b = create_bullet_angle(u["x"], u["y"], a, u["bone_speed"],
                                Bullet.TYPE_KNIFE, radius=P["bone_radius"],
                                color=P["bone_color"], lifetime=P["bone_lifetime"])
        b.manager = bullet_manager
        bullet_manager.add_enemy_bullet(b)
    _revival_fire_flash(bullet_manager, u["x"], u["y"], P)


def _revival_kill(u, bullet_manager, P):
    """Undead 被玩家击破：进入灵魂消散（不立即删除），随后进入复活流程"""
    u["phase"] = "dying"
    u["timer"] = 0
    _revival_soul_burst(bullet_manager, u["x"], u["y"], P, count=10)


def _revival_revive_ring(bullet_manager, u, P):
    """复活瞬间发出的圆弹环：以 Undead 新位置为圆心向固定方向扩散一圈紫色圆弹。
    不自机狙；每复活一次整体旋转半个弹距，避免与上一次圆弹完全重叠。"""
    n = P["revive_ring_count"]
    base = u["revives"] * (math.pi / n)
    for i in range(n):
        a = base + i * math.tau / n
        b = create_bullet_angle(u["x"], u["y"], a, P["revive_ring_speed"],
                                Bullet.TYPE_CIRCLE, radius=P["revive_ring_radius"],
                                color=P["revive_ring_color"],
                                lifetime=P["revive_ring_lifetime"])
        b.manager = bullet_manager
        bullet_manager.add_enemy_bullet(b)


def _revival_resurrect(u, boss, bullet_manager, player_x, player_y, P):
    """复活：换一个生成位置、重新分配固定轨迹、发出圆弹环。
    每次复活攻击频率与骨弹速度各增加初始值的 revive_boost（25%），
    频率有下限 fire_interval_min，弹速不设上限。"""
    u["x"], u["y"] = _revival_pick_spawn(boss, player_x, player_y, P)
    u["home"] = (u["x"], u["y"])
    _revival_new_route(u, P)
    u["revives"] += 1
    u["hp"] = u["max_hp"]
    # 攻击频率：间隔 = 初始间隔 / (1 + 0.25 * 复活次数)，不低于下限
    u["fire_interval"] = max(P["fire_interval_min"],
                             round(P["fire_interval"] / (1 + P["revive_boost"] * u["revives"])))
    u["fire_timer"] = u["fire_interval"]
    # 骨弹速度：初始速度 * (1 + 0.25 * 复活次数)
    u["bone_speed"] = P["bone_speed"] * (1 + P["revive_boost"] * u["revives"])
    # 复活瞬间：以新位置发出一圈圆弹
    _revival_revive_ring(bullet_manager, u, P)


def _revival_update_undead(u, boss, bullet_manager, player_x, player_y, P):
    """单具 Undead 生命周期推进（召唤 -> 活跃 -> 消散 -> 复活等待 -> 复活）"""
    u["timer"] += 1
    phase = u["phase"]
    if phase == "summoning":
        # 召唤魔法阵动画结束 -> 进入活跃（移动 + 发射 + 可被击破）
        if u["timer"] >= P["summon_time"]:
            u["phase"] = "active"
            u["timer"] = 0
    elif phase == "active":
        _revival_move_undead(u, P)
        # 固定间隔发射骨弹散射
        u["fire_timer"] -= 1
        if u["fire_timer"] <= 0:
            _revival_fire_volley(bullet_manager, u, P)
            u["fire_timer"] = u["fire_interval"]
    elif phase == "dying":
        # 灵魂消散结束 -> 亡灵魔法阵重组等待
        if u["timer"] >= P["die_time"]:
            u["phase"] = "reviving"
            u["timer"] = 0
            _revival_soul_burst(bullet_manager, u["x"], u["y"], P, count=4)
    elif phase == "reviving":
        # 等待结束 -> 原地满血复活（重新召唤动画，换位 + 频率加成）
        if u["timer"] >= P["revive_time"]:
            _revival_resurrect(u, boss, bullet_manager, player_x, player_y, P)
            u["phase"] = "summoning"
            u["timer"] = 0


def _revival_check_hits(undeads, bullet_manager, P):
    """玩家弹 vs 活跃 Undead：命中扣血并消耗玩家弹，击破进入复活流程"""
    for u in undeads:
        if u["phase"] != "active":
            continue
        for pb in bullet_manager.player_bullets[:]:
            if not pb.alive or pb.cancel_timer > 0:
                continue
            if circle_collision(u["x"], u["y"], P["hit_radius"],
                                pb.x, pb.y, pb.collision_radius):
                pb.alive = False
                u["hp"] -= pb.damage
                if u["hp"] <= 0:
                    _revival_kill(u, bullet_manager, P)
                    break


def spell_bonzo_undead_revival(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """死符「Undead Revival」：亡灵复活秀

    Bonzo 本人不亲自攻击，只在中场缓慢漂浮施法，周期性召唤 Undead：
      1. Undead 从 Boss 周围 / 屏幕上方 / 屏幕边缘出现（召唤魔法阵，不贴脸）；
      2. 沿固定轨迹移动（巡逻 / 横向 / 缓慢斜向，不追踪玩家）；
      3. 向固定 8 方向散射白色骨弹（不自机狙），多具之间角度错开交叉成网；
      4. 被玩家击破后不立即删除：灵魂消散 -> 亡灵魔法阵重组等待（约 1.5s）
         -> 换位复活：攻击频率与骨弹速度各提升初始的 25%（频率有下限），
         复活瞬间还以新位置发出一圈紫色圆弹。
    Undead 数量封顶（max_undead），随时间逐渐补满，符合三面终 Boss 第一符卡定位。
    """
    P = _BONZO_REVIVAL

    # 开符：立即召唤初始一批 Undead
    if timer == 1:
        boss.bonzo_undeads = []
        for i in range(P["initial_undead"]):
            spawn = _revival_pick_spawn(boss, player_x, player_y, P)
            boss.bonzo_undeads.append(_revival_make_undead(i, spawn, P))
            _revival_soul_burst(bullet_manager, spawn[0], spawn[1], P, count=5)
            _revival_boss_cast_flash(bullet_manager, boss, P)
        return

    # Bonzo 本体：不亲自攻击，仅缓慢漂浮施法
    boss.target_x = cfg.BATTLE_AREA_WIDTH / 2 + math.sin(timer * 0.008) * 44
    boss.target_y = 116 + math.sin(timer * 0.011) * 7

    # 周期性补充召唤：随时间逐渐增加到最大数量（到达上限后只复活、不新增）
    cap = min(P["max_undead"], P["initial_undead"] + timer // P["spawn_interval"])
    if timer % P["spawn_interval"] == 0 and len(boss.bonzo_undeads) < cap:
        index = len(boss.bonzo_undeads)
        spawn = _revival_pick_spawn(boss, player_x, player_y, P)
        boss.bonzo_undeads.append(_revival_make_undead(index, spawn, P))
        _revival_soul_burst(bullet_manager, spawn[0], spawn[1], P, count=5)
        _revival_boss_cast_flash(bullet_manager, boss, P)

    # Undead 生命周期推进
    for u in boss.bonzo_undeads:
        _revival_update_undead(u, boss, bullet_manager, player_x, player_y, P)

    # 玩家弹 vs Undead 碰撞
    _revival_check_hits(boss.bonzo_undeads, bullet_manager, P)


# ------------------------- Bonzo：第二符卡「骸符 Skull Dreadlord」 -------------------------
# 符卡参数集中区（方便调整难度）：所有可调项集中在 _BONZO_DREADLORD
_BONZO_DREADLORD = {
    # —— 循环节奏（帧，60FPS）——
    "spell_duration": 4200,        # 符卡设计时长（实际以血量结束，约 70s）
    "rebuild_delay": 8,            # 全部骷髅消散后、重建新阵列前的停顿（帧）
    "warn_frames": 30,             # 骷髅头出现预警动画时长（帧）
    "despawn_frames": 36,          # 骷髅头喷完弹幕即消散的动画时长（帧）

    # —— 骷髅阵列 ——
    "skull_count": 5,              # 骷髅头数量（固定弧列）
    "array_radius": 118,           # 弧列半径（px，围绕 Bonzo 的下半弧）
    "array_span": math.radians(130),  # 弧列覆盖角度（以正下方为中心左右对称）
    "skull_radius": 17,            # 骷髅头绘制半径（px）

    # —— 交替攻击节奏 ——
    "attack_stagger": 28,          # 相邻骷髅头张嘴开火错开帧数（交替攻击）
    "open_frames": 14,             # 张嘴时长（嘴张到最大时开始喷射）
    "hold_frames": 22,             # 嘴保持张开帧数（连喷窗口）
    "close_frames": 12,            # 闭嘴时长

    # —— V 形骨扇（骨雨/骨墙，正中留出可穿空隙）——
    "burst_count": 2,              # 张嘴期间喷出的波数（快/慢两层）
    "burst_interval": 10,          # 两波喷射间隔（帧）
    "fan_count": 6,                # 每波 V 形骨弹数量（左右各半，正中留空）
    "fan_angle": math.radians(60), # V 形总张角
    "bone_speed": 2.6,             # 主层骨弹速度（px/帧）
    "bone_speed_2": 2.0,           # 次层骨弹速度（慢层，随速度差拉出流动骨帘）
    "bone_radius": 2.6,            # 骨弹半径
    "bone_lifetime": 430,          # 骨弹存活帧数
    "bone_wobble": 6,              # 骨弹蛇形摆动幅度（px，骨帘流动感）
    "bone_wobble_freq": 0.05,      # 摆动频率（弧度/帧）
    "bone_color_2": (215, 240, 235),  # 次层骨弹（青白，增加层次）
    "fan_tilt": math.radians(3),   # 相邻骷髅头扇形左右对称偏角（对称交错）
    "focal_depth": 130,            # 收敛焦点位于屏幕底缘下方（px，全固定方向）

    # —— 灵魂火环（张嘴瞬间向四周扩散，观赏 + 可躲）——
    "ring_count": 8,               # 灵魂火环弹数
    "ring_speed": 1.0,             # 环弹速度（px/帧，慢速扩散）
    "ring_radius": 2.2,            # 环弹半径
    "ring_color": (110, 235, 210), # 青色灵魂火
    "ring_lifetime": 300,          # 环弹存活帧数

    # —— 骨刺直线弹 ——
    "spike_speed": 3.0,            # 骨刺速度（px/帧，竖直下刺）
    "spike_radius": 3.6,           # 骨刺半径（大玉）
    "spike_color": (175, 110, 235),  # 紫色亡灵能量

    # —— 可击破骷髅魂玉（少量随机，打爆后爆炸清弹）——
    "orb_count_range": (1, 2),     # 每轮阵列随机生成的大玉数量
    "orb_hp": 30,                  # 生命值（玩家弹单发 10，约 3 发击破）
    "orb_explode_radius": 90,      # 击破后爆炸清弹半径（px），范围内玩家也受伤
    "orb_speed": 0.7,              # 缓慢飘落速度（px/帧）
    "orb_radius": 4.5,             # 大玉半径
    "orb_color": (240, 150, 255),  # 品紫亡灵能量（醒目区别于骨弹/灵魂火）
    "orb_lifetime": 600,           # 存活帧数（10s）
    "orb_spawn_y": (100, 260),     # 生成高度范围（px，随机）

    # —— 视觉 ——
    "bone_color": (250, 246, 235),   # 白色骨骼
    "soul_teal": (110, 235, 210),    # 青色灵魂火
    "soul_purple": (170, 95, 235),   # 紫色亡灵能量
    "warn_color": (150, 220, 255),   # 预警青白光
    "flash_color": (215, 245, 255),  # 喷射瞬间闪光
}


def _dreadlord_array_positions(boss, P):
    """骷髅弧列：以 Bonzo 为中心、正下方为对称轴的固定下半弧阵列。
    位置在生成时一次定死（固定弹，不自机狙），Bonzo 缓慢漂浮只影响下一轮阵列。"""
    cx, cy = boss.x, boss.y + 6
    r = P["array_radius"]
    n = P["skull_count"]
    start = math.pi / 2 - P["array_span"] / 2
    step = P["array_span"] / max(1, n - 1)
    return [(cx + math.cos(start + i * step) * r,
             cy + math.sin(start + i * step) * r) for i in range(n)]


def _dreadlord_make_skull(index, pos, P, wave, focal):
    """创建一颗骷髅头（临时弹幕发射器）。

    生命周期状态机：warn（预警浮现）-> attack（张嘴连喷）-> despawn（喷完即消散）
    -> 全部消散后重建新阵列。
    弹道基准角朝固定焦点（屏幕底缘下方）收敛，全部为固定方向；相邻骷髅按序号
    左右对称倾斜（偶数左倾 / 奇数右倾），形成对称交错弹。"""
    x, y = pos
    fx, fy = focal
    base = math.atan2(fy - y, fx - x)
    base += P["fan_tilt"] if index % 2 == 0 else -P["fan_tilt"]
    return {
        "x": x, "y": y,
        "index": index,
        "phase": "warn",
        "timer": 0,
        "alive": True,             # 存活标志：喷完消散后置 False
        "attack_delay": index * P["attack_stagger"],   # 交替攻击错开帧数
        "mouth": 0.0,          # 嘴部开合 0..1（绘制用）
        "base_angle": base,
        "burst_index": 0,      # 已喷出的波数（快/慢两层）
        "spike": (index + wave) % 2 == 0,  # 骨刺隔波交替（保持左右对称）
        "spike_fired": False,  # 竖直骨刺是否已发射
        "ring_fired": False,   # 灵魂火环是否已扩散
        "flash": 0,            # 喷射闪光剩余帧数（绘制用）
        # 绘制所需节奏参数复制到每个骷髅，绘制层不依赖符卡配置
        "warn_frames": P["warn_frames"],
        "open_frames": P["open_frames"],
        "hold_frames": P["hold_frames"],
        "close_frames": P["close_frames"],
        "despawn_frames": P["despawn_frames"],
        "radius": P["skull_radius"],
        "bone_color": P["bone_color"],
        "soul_teal": P["soul_teal"],
        "soul_purple": P["soul_purple"],
        "warn_color": P["warn_color"],
    }


def _dreadlord_fire_burst(bullet_manager, skull, burst, P):
    """V 形骨扇：以骷髅嘴部为圆心朝焦点方向喷射两侧骨刃，正中留出可穿空隙。

    主层快（白色）、次层慢（青白），两层同角对齐，随速度差拉开成流动骨帘；
    每根骨刃带蛇形摆动（骨帘流动感）；全部为固定方向（不自机狙）。"""
    base = skull["base_angle"]
    spacing = P["fan_angle"] / max(1, P["fan_count"] - 1)
    speed = P["bone_speed"] if burst % 2 == 0 else P["bone_speed_2"]
    color = P["bone_color"] if burst % 2 == 0 else P["bone_color_2"]
    half = P["fan_count"] // 2
    for i in range(1, half + 1):
        for side in (-1, 1):
            off = (i - 0.5) * spacing * side
            b = create_bullet_angle(skull["x"], skull["y"], base + off, speed,
                                    Bullet.TYPE_KNIFE, radius=P["bone_radius"],
                                    color=color, lifetime=P["bone_lifetime"])
            b.manager = bullet_manager
            b.wobble_amp = P["bone_wobble"]
            b.wobble_freq = P["bone_wobble_freq"]
            b.wobble_phase = (skull["index"] * 2.7 + i * 1.9 + burst * 3.1) % (math.tau)
            bullet_manager.add_enemy_bullet(b)


def _dreadlord_fire_ring(bullet_manager, skull, P):
    """灵魂火环：嘴张到最大时向四周扩散一圈青色灵魂火弹（慢速固定方向）"""
    n = P["ring_count"]
    base = skull["index"] * 0.24
    for i in range(n):
        a = base + i * math.tau / n
        b = create_bullet_angle(skull["x"], skull["y"], a, P["ring_speed"],
                                Bullet.TYPE_CIRCLE, radius=P["ring_radius"],
                                color=P["ring_color"], lifetime=P["ring_lifetime"])
        b.manager = bullet_manager
        bullet_manager.add_enemy_bullet(b)


def _dreadlord_fire_spike(bullet_manager, skull, P):
    """骨刺直线弹：从骷髅头正下方竖直下刺的紫色大玉（更快，压迫走位）"""
    b = create_bullet_angle(skull["x"], skull["y"], math.pi / 2, P["spike_speed"],
                            Bullet.TYPE_BIG, radius=P["spike_radius"],
                            color=P["spike_color"], lifetime=P["bone_lifetime"])
    b.manager = bullet_manager
    bullet_manager.add_enemy_bullet(b)


def _dreadlord_spawn_orb(bullet_manager, P):
    """随机生成一颗可击破骷髅魂玉：品紫大玉缓慢飘落，醒目可区分。

    被玩家子弹打爆后由通用碰撞层触发爆炸（_explode_shootable_orb）：
    清掉周围敌弹；玩家在爆炸范围内也会受伤。少量随机，作为固定骨弹
    之外的互动奖励目标，不构成弹幕洪流。"""
    x = random.uniform(cfg.BATTLE_AREA_WIDTH * 0.15, cfg.BATTLE_AREA_WIDTH * 0.85)
    y = random.uniform(*P["orb_spawn_y"])
    orb = create_bullet_angle(x, y, math.pi / 2, P["orb_speed"], Bullet.TYPE_BIG,
                              radius=P["orb_radius"], color=P["orb_color"],
                              lifetime=P["orb_lifetime"])
    orb.manager = bullet_manager
    orb.shootable = True
    orb.hp = P["orb_hp"]
    orb.explode_radius = P["orb_explode_radius"]
    bullet_manager.add_enemy_bullet(orb)
    # 高亮光圈：提示玩家这是一颗可击破目标（纯视觉）
    halo = create_bullet_angle(x, y, 0.0, 0.0, Bullet.TYPE_CIRCLE,
                               radius=P["orb_explode_radius"] * 0.22,
                               color=P["orb_color"])
    halo.manager = bullet_manager
    halo.harmless = True
    halo.lifetime = 30
    bullet_manager.add_enemy_bullet(halo)
    _dreadlord_soul_burst(bullet_manager, x, y, P, count=4)


def _dreadlord_glow_flash(bullet_manager, x, y, color, radius):
    """施法/喷射瞬间的短闪光（纯视觉）"""
    f = create_bullet_angle(x, y, 0.0, 0.0, Bullet.TYPE_CIRCLE,
                            radius=radius, color=color)
    f.manager = bullet_manager
    f.harmless = True
    f.lifetime = 6
    bullet_manager.add_enemy_bullet(f)


def _dreadlord_soul_burst(bullet_manager, x, y, P, count=6):
    """灵魂粒子：青/紫光点向四周飘散（骷髅出现/消散用，纯视觉）"""
    for i in range(count):
        ang = i * math.tau / count + random.uniform(-0.4, 0.4)
        speed = random.uniform(0.6, 1.5)
        color = random.choice((P["soul_teal"], P["soul_purple"]))
        b = create_bullet_angle(x, y, ang, speed, Bullet.TYPE_CIRCLE,
                                radius=2, color=color)
        b.manager = bullet_manager
        b.harmless = True
        b.lifetime = random.randint(22, 40)
        bullet_manager.add_enemy_bullet(b)


def _dreadlord_update_skull(skull, bullet_manager, P):
    """单颗骷髅头生命周期推进（warn -> attack -> despawn）。

    骷髅头喷完弹幕（连喷 + 骨刺收尾、嘴部闭合）后立即消散，不再原地待命；
    全部骷髅消散后由符卡主循环重建新阵列。"""
    if not skull.get("alive", True):
        return
    skull["timer"] += 1
    if skull["flash"] > 0:
        skull["flash"] -= 1
    phase = skull["phase"]
    if phase == "warn":
        skull["mouth"] = 0.0
        if skull["timer"] >= skull["warn_frames"] + skull.get("attack_delay", 0):
            skull["phase"] = "attack"
            skull["timer"] = 0
    elif phase == "attack":
        t = skull["timer"]
        open_t = skull["open_frames"]
        hold_t = skull["hold_frames"]
        close_t = skull["close_frames"]
        # 嘴部开合动画
        if t <= open_t:
            skull["mouth"] = min(1.0, t / max(1, open_t))
        elif t <= open_t + hold_t:
            skull["mouth"] = 1.0
        elif t <= open_t + hold_t + close_t:
            skull["mouth"] = max(0.0, 1.0 - (t - open_t - hold_t) / max(1, close_t))
        else:
            # 喷完弹幕：立即进入消散（灵魂粒子 + 淡出）
            skull["phase"] = "despawn"
            skull["timer"] = 0
            skull["mouth"] = 0.0
            _dreadlord_soul_burst(bullet_manager, skull["x"], skull["y"], P, count=6)
            return
        # 嘴张到最大：扩散一圈灵魂火环（观赏 + 可躲）
        if t == open_t and not skull["ring_fired"]:
            _dreadlord_fire_ring(bullet_manager, skull, P)
            skull["ring_fired"] = True
        # 嘴张到最大后按固定间隔连喷两层骨扇
        if (t > open_t and (t - open_t) % P["burst_interval"] == 0
                and skull["burst_index"] < P["burst_count"]):
            _dreadlord_fire_burst(bullet_manager, skull, skull["burst_index"], P)
            skull["burst_index"] += 1
            skull["flash"] = 6
        # 最后一波后补一根竖直骨刺（隔波交替，不占满每一列）
        if skull["burst_index"] >= P["burst_count"] and not skull["spike_fired"]:
            if skull.get("spike", True):
                _dreadlord_fire_spike(bullet_manager, skull, P)
            skull["spike_fired"] = True
    elif phase == "despawn":
        skull["mouth"] = 0.0
        if skull["timer"] >= skull["despawn_frames"]:
            skull["alive"] = False


def _dreadlord_spawn_array(boss, bullet_manager, P):
    """生成一轮骷髅阵列：弧列位置与收敛焦点一次定死，附带灵魂粒子与施法闪光"""
    positions = _dreadlord_array_positions(boss, P)
    focal = (boss.x, cfg.BATTLE_AREA_HEIGHT + P["focal_depth"])
    wave = boss.bonzo_dreadlord_wave
    boss.bonzo_dreadlord_skulls = [
        _dreadlord_make_skull(i, positions[i], P, wave, focal)
        for i in range(P["skull_count"])
    ]
    boss.bonzo_dreadlord_wave += 1
    for pos in positions:
        _dreadlord_soul_burst(bullet_manager, pos[0], pos[1], P, count=5)
    _dreadlord_glow_flash(bullet_manager, boss.x, boss.y, P["soul_purple"], 16)
    # 少量随机可击破魂玉：打爆后爆炸清掉周围弹幕（玩家在范围内也受伤）
    for _ in range(random.randint(*P["orb_count_range"])):
        _dreadlord_spawn_orb(bullet_manager, P)


def spell_bonzo_skull_dreadlord(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """骸符「Skull Dreadlord」：骸骨领主

    骷髅王威压：Bonzo 周围周期性生成巨大的骷髅头印记阵列，单循环弹幕（无多阶段）：
      1. 预警：骷髅头带紫色召唤环 + 脉冲光环浮现，张嘴前不可发射；
      2. 交替攻击：骷髅头按固定顺序逐颗张嘴，嘴张到最大后连喷多波固定扇形骨弹，
         最后一波后补一根竖直下刺的紫色骨刺；
      3. 对称交错：相邻骷髅头 V 形骨扇左右对称倾斜，快慢两层同角对齐、
         随速度差拉开成流动骨帘，正中与层间均留有可穿空隙；
         灵魂火环与交替骨刺点缀其间，全部为固定弹、不使用自机狙；
      4. 少量随机魂玉：每轮阵列额外生成 1~2 颗醒目的品紫可击破大玉，
         缓慢飘落；被玩家子弹打爆后爆炸清掉周围弹幕，玩家在爆炸
         范围内也会受伤；
      5. 立即消散：每颗骷髅喷完弹幕即淡出消散，不再原地待命；
      6. 重建：全部骷髅消散后短暂停顿，随即重新生成新的骷髅阵列。
    """
    P = _BONZO_DREADLORD

    # 开符：生成第一轮骷髅阵列
    if timer == 1:
        boss.bonzo_dreadlord_rebuild = 0
        _dreadlord_spawn_array(boss, bullet_manager, P)

    # Bonzo 本体：骸骨领主漂浮施法，不亲自攻击
    boss.target_x = cfg.BATTLE_AREA_WIDTH / 2 + math.sin(timer * 0.007) * 30
    boss.target_y = 112 + math.sin(timer * 0.010) * 6

    # 骷髅头生命周期推进（喷完弹幕即进入消散）
    for skull in boss.bonzo_dreadlord_skulls:
        _dreadlord_update_skull(skull, bullet_manager, P)

    # 全部骷髅消散后：短暂停顿，随后重建新阵列
    skulls = boss.bonzo_dreadlord_skulls
    if skulls and all(not sk.get("alive", True) for sk in skulls):
        boss.bonzo_dreadlord_rebuild += 1
        if boss.bonzo_dreadlord_rebuild >= P["rebuild_delay"]:
            boss.bonzo_dreadlord_rebuild = 0
            _dreadlord_spawn_array(boss, bullet_manager, P)


# ------------------------- Bonzo：第三符卡「戏符 Grand Illusion」 -------------------------
_BONZO_ILLUSION = {
    "mask_count": 6,            # 小丑面具幻象节点数量
    "orbit_rx": 124,            # 旋转轨道横向半径（px）
    "orbit_ry": 74,             # 旋转轨道纵向半径（px，压扁成环绕 Boss 的椭圆）
    "orbit_speed": 0.011,       # 轨道角速度（弧度/帧，缓慢旋转）
    "mask_height": 52,          # 面具贴图渲染高度（px）

    "sweep_interval": 8,        # 每个面具扫射的发射间隔（帧）
    "sweep_burst": 2,           # 每次扫射发射的子弹数量
    "sweep_spread": 0.06,       # 每次扫射内子弹间的散布角（弧度）
    "sweep_speed": 2.05,        # 扫射子弹速度（px/帧）
    "sweep_span": 0.72,         # 扫射方向左右摆动的最大角度（弧度）
    "sweep_step": 0.052,        # 每帧扫射角变化量（弧度/帧）

    "cycle_interval": 230,      # 阵型重组间隔（帧）
    "respawn_delay": 40,        # 面具消失后到新位置重生的间隔（帧）
    "reshuffle_count": 2,       # 每次重组消失/重生的面具数量
}

_ILLUSION_COLORS = (
    (245, 105, 175), (110, 215, 225), (245, 205, 95),
    (150, 235, 120), (205, 130, 250), (245, 150, 105),
)


def _illusion_make_mask(index, P):
    """创建一个小丑面具幻象节点，初始均匀分布在椭圆轨道上。"""
    return {
        "index": index,
        "angle": index * math.tau / P["mask_count"],
        "phase": index * 0.9,
        "x": 0.0,
        "y": 0.0,
        "alive": True,
        "alpha": 255,
        "respawn_timer": 0,
        "next_angle": 0.0,
        "next_phase": 0.0,
        "fire_offset": index * 4,
        "sweep_angle": 0.0,
        "sweep_dir": 1 if index % 2 == 0 else -1,
        "color": _ILLUSION_COLORS[index % len(_ILLUSION_COLORS)],
    }


def _illusion_update_position(boss, mask, P):
    """把面具放到当前椭圆轨道角度对应的世界坐标上。"""
    mask["x"] = boss.x + math.cos(mask["angle"]) * P["orbit_rx"]
    mask["y"] = boss.y + math.sin(mask["angle"]) * P["orbit_ry"]


def _illusion_emit_sweep(bullet_manager, mask, P):
    """从面具当前位置射出一小簇扫射弹，方向随 sweep_angle 左右摆动。"""
    base = mask["angle"] + mask["sweep_angle"]
    count = P["sweep_burst"]
    spread = P["sweep_spread"]
    for i in range(count):
        offset = 0.0 if count == 1 else (i - (count - 1) / 2) * spread
        b = create_bullet_angle(mask["x"], mask["y"], base + offset,
                                P["sweep_speed"], Bullet.TYPE_RICE,
                                radius=2.4, color=mask["color"])
        bullet_manager.add_enemy_bullet(b)


def _illusion_reshuffle(boss, P):
    """攻击循环节点：随机让部分面具消失，并在计时结束后于新位置重生。"""
    masks = boss.bonzo_masks
    alive_idx = [i for i, m in enumerate(masks) if m["alive"]]
    count = min(P["reshuffle_count"], len(alive_idx))
    for idx in random.sample(alive_idx, count):
        mask = masks[idx]
        mask["alive"] = False
        mask["alpha"] = 0
        mask["respawn_timer"] = P["respawn_delay"]
        mask["next_angle"] = random.uniform(0.0, math.tau)
        mask["next_phase"] = random.uniform(0.0, math.tau)
        mask["fire_offset"] = random.randrange(P["sweep_interval"])


def spell_bonzo_grand_illusion(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """戏符「Grand Illusion」：小丑魔术

    Bonzo 自身周围生成多个小丑面具幻象节点，面具沿固定椭圆轨道缓慢旋转，
    并持续朝左右摆动方向扫射弹幕。攻击循环中会随机让部分面具消失，
    稍后在新的轨道角度重新出现，从而改变整个弹幕阵列的形状。
    """
    P = _BONZO_ILLUSION

    if timer == 1:
        boss.bonzo_masks = [_illusion_make_mask(i, P) for i in range(P["mask_count"])]
        for mask in boss.bonzo_masks:
            _illusion_update_position(boss, mask, P)
        return

    # Bonzo 本体：居中施法，仅做轻微漂浮
    boss.target_x = cfg.BATTLE_AREA_WIDTH / 2 + math.sin(timer * 0.007) * 26
    boss.target_y = 116 + math.sin(timer * 0.010) * 6

    # 阵型重组：部分面具消失，计时结束后在其他位置重生
    if timer > 1 and timer % P["cycle_interval"] == 0:
        _illusion_reshuffle(boss, P)

    # 更新每个面具的位置 / 状态，并发射弹幕
    for mask in boss.bonzo_masks:
        if mask["alive"]:
            mask["angle"] = (mask["angle"] + P["orbit_speed"]) % math.tau
            mask["phase"] += P["orbit_speed"]
            _illusion_update_position(boss, mask, P)

            # 扫射方向左右摆动，到边界后反向
            mask["sweep_angle"] += mask["sweep_dir"] * P["sweep_step"]
            if abs(mask["sweep_angle"]) >= P["sweep_span"]:
                mask["sweep_angle"] = math.copysign(P["sweep_span"], mask["sweep_angle"])
                mask["sweep_dir"] *= -1
            if (timer + mask["fire_offset"]) % P["sweep_interval"] == 0:
                _illusion_emit_sweep(bullet_manager, mask, P)
        else:
            mask["respawn_timer"] -= 1
            if mask["respawn_timer"] <= 0:
                mask["alive"] = True
                mask["alpha"] = 255
                mask["angle"] = mask["next_angle"]
                mask["phase"] = mask["next_phase"]
                _illusion_update_position(boss, mask, P)


_BONZO_SHOWTIME = {
    # Finale: high-frequency 8-way bursts centered on Bonzo.
    "fire_interval": 2,          # frames between ring volleys
    "ring_count": 8,             # bullets per ring
    "bullet_speed": 1.75,
    "bullet_radius": 2.5,
    "bullet_lifetime": 420,

    # Periodic three-orb volley: aimed larger showtime orbs.
    "big_orb_interval": 120,     # frames between volleys
    "big_orb_count": 3,          # orbs per volley
    "big_orb_speed_factor": 1.4, # bullet_speed * 2.0 * 0.7
    "big_orb_radius": 5.0,
    "big_orb_lifetime": 480,

    # Rotation speed changes on a fixed schedule, then loops.
    # Each item is (duration_frames, angular_speed_radians_per_frame).
    "rotation_schedule": (
        (150, 0.06),
        (120, 0.16),
        (150, 0.03),
        (110, 0.22),
        (130, 0.09),
    ),

    "bob_amplitude": 6,
}


def _showtime_spin_state(timer):
    """Return continuous (angle, current_spin_speed) for the schedule."""
    schedule = _BONZO_SHOWTIME["rotation_schedule"]
    cycle = sum(duration for duration, _ in schedule)
    cycle_angle = sum(spin * duration for duration, spin in schedule)
    cycles, local = divmod(timer, cycle)

    angle = cycles * cycle_angle
    speed = schedule[-1][1]

    for duration, spin in schedule:
        if local < duration:
            angle += spin * local
            speed = spin
            break
        angle += spin * duration
        local -= duration

    return angle, speed


def spell_bonzo_showtime(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """Secret rite "Showtime": Bonzo centers himself and fires rapid 8-way rings.

    The firing angle rotates continuously. Its rotation speed changes several
    times over a fixed schedule, creating accelerating/decelerating wheel waves.
    """
    P = _BONZO_SHOWTIME

    boss.target_x = cfg.BATTLE_AREA_WIDTH / 2
    boss.target_y = 112 + math.sin(timer * 0.012) * P["bob_amplitude"]

    if timer % P["big_orb_interval"] == 0:
        orb_speed = P["bullet_speed"] * P["big_orb_speed_factor"]
        for _ in range(P["big_orb_count"]):
            orb = create_bullet_aimed(
                boss.x, boss.y, player_x, player_y, orb_speed,
                Bullet.TYPE_BIG, radius=P["big_orb_radius"],
                color=(255, 245, 170), lifetime=P["big_orb_lifetime"])
            bullet_manager.add_enemy_bullet(orb)

    if timer % P["fire_interval"] != 0:
        return

    base_angle, _ = _showtime_spin_state(timer)

    palette = (
        (255, 90, 120),
        (90, 210, 235),
        (255, 205, 90),
        (150, 235, 125),
        (190, 135, 245),
        (250, 160, 75),
        (235, 120, 205),
        (125, 225, 190),
    )

    for i in range(P["ring_count"]):
        angle = base_angle + i * math.tau / P["ring_count"]
        b = create_bullet_angle(
            boss.x, boss.y, angle, P["bullet_speed"],
            Bullet.TYPE_CIRCLE, radius=P["bullet_radius"],
            color=palette[i % len(palette)])
        bullet_manager.add_enemy_bullet(b)


_BONZO_BALLOON = {
    # Wave choreography: fixed angles, no random scatter, no aimed spam.
    "wave_interval": 128,        # frames between balloon waves
    "balloon_count": 12,         # balloons per wave, evenly spaced around Bonzo
    "angle_step": math.tau / 24, # global wave rotation

    # Balloon motion: launch outward, decelerate, then hover.
    "balloon_speed": 1.35,
    "balloon_brake": 0.022,
    "balloon_radius": 5.0,
    "balloon_lifetime": 360,
    "stay_time": 48,             # frames stationary before bursting

    # Burst: multi-arm rotating groups of kunai, straight outward only.
    "burst_duration": 42,        # frames each burst core keeps firing
    "burst_interval": 3,         # frames between spiral shots
    "burst_arms": 4,             # angular arms per shot, evenly spaced
    "burst_group_count": 3,      # kunai per arm
    "group_spread": 0.45,        # angular width of each kunai fan
    "spiral_angle_step": 0.22,   # arm rotation per shot
    "spiral_accel": 0.022,       # outward acceleration; no return-to-center path
    "explosion_speed": 1.75,
    "explosion_radius": 2.3,     # kunai visual radius
    "explosion_lifetime": 600,   # long enough to leave the screen, then removed
}


def spell_bonzo_balloon_barrage(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """Air sign "Balloon Barrage": outward-spiraling kunai bursts from balloons.

    Each balloon launches, decelerates to a hover, then emits rotating arms of
    kunai. Every kunai travels straight outward and accelerates, so it only
    expands away from the burst point and is removed after leaving the field.
    """
    P = _BONZO_BALLOON

    boss.target_x = cfg.BATTLE_AREA_WIDTH / 2
    boss.target_y = 112

    if timer % P["wave_interval"] != 0:
        return

    wave = timer // P["wave_interval"]
    wave_angle = wave * P["angle_step"]
    explode_timer = int(P["balloon_speed"] / P["balloon_brake"]) + P["stay_time"]

    palette = (
        (235, 90, 130),
        (90, 200, 220),
        (235, 200, 90),
        (150, 230, 120),
        (180, 140, 235),
        (245, 165, 70),
    )

    for i in range(P["balloon_count"]):
        angle = wave_angle + i * math.tau / P["balloon_count"]
        color = palette[i % len(palette)]

        balloon = create_bullet_angle(
            boss.x, boss.y, angle, P["balloon_speed"],
            Bullet.TYPE_BIG, radius=P["balloon_radius"], color=color)

        balloon.brake = P["balloon_brake"]
        balloon.brake_floor = 0.0
        balloon.manager = bullet_manager
        balloon.split_spec = {
            "timer": explode_timer,
            "stream": True,
            "duration": P["burst_duration"],
            "interval": P["burst_interval"],
            "count": P["burst_arms"],
            "angle_step": P["spiral_angle_step"],
            "group_count": P["burst_group_count"],
            "group_spread": P["group_spread"],
            "base_angle": wave_angle,
            "speed": P["explosion_speed"],
            "type": Bullet.TYPE_KNIFE,
            "radius": P["explosion_radius"],
            "color": color,
            "child_accel": P["spiral_accel"],
            "child_lifetime": P["explosion_lifetime"],
            "core_radius": 6,
            "core_color": (255, 250, 220),
        }
        balloon.lifetime = P["balloon_lifetime"]
        bullet_manager.add_enemy_bullet(balloon)


class Stage3_CatacombsF1(Stage):
    """Stage 3: The Catacombs Floor 1 - 地下墓穴"""

    def __init__(self):
        super().__init__(3, "地下墓穴 ~ The Catacombs Floor 1",
                         bg_color=(8, 9, 12))
        # 伪3D墓穴甬道：低地平线 + 较窄通道，营造幽深地下感
        self.background = Pseudo3DFloor(cfg.STAGE3_FLOOR, cfg.BATTLE_AREA_WIDTH,
                                        cfg.BATTLE_AREA_HEIGHT, bg_color=self.bg_color,
                                        wall_texture_path=cfg.STAGE3_WALL,
                                        horizon_ratio=0.42, tunnel_width=2.0,
                                        far_opening=40,
                                        floor_stretch=3.0, wall_stretch=1.0,
                                        wall_align_to_floor=True)
        # 每面资源：三面曲名 / 标题卡（音乐文件未就绪时 play_music 自动跳过）
        self.title_path = cfg.STAGE3_TITLE
        self.music_path = cfg.STAGE3_MUSIC_START
        self.music_loop_path = cfg.STAGE3_MUSIC_LOOP
        self.boss_music_start_path = cfg.STAGE3_BOSS_MUSIC_START
        self.boss_music_loop_path = cfg.STAGE3_BOSS_MUSIC_LOOP
        self.music_name = cfg.STAGE3_MUSIC_NAME
        self.boss_music_name = cfg.STAGE3_BOSS_MUSIC_NAME
        self.mid_boss_music_path = None
        self.background_darkness = 130
        # 战后对话：Bonzo 被击破后（自机 Mage 在左侧）
        self.defeat_dialogue_lines = [
            ("魔法使 Mage", "气球全都被戳破了，你的把戏也该收场了吧。"),
            ("Bonzo", "Pfft—fine, fine! You popped my best balloons... I guess you win this floor."),
            ("魔法使 Mage", "地下墓穴的宝物，我就笑纳了。下次别再拿气球挡路了。"),
            ("Bonzo", "Hehehe... the Catacombs never forget their jester. Enjoy the loot, Mage!"),
        ]
        self.defeat_dialogue_portraits = {
            "魔法使 Mage": cfg.SELF_SPRITE,
            "Bonzo": cfg.BONZO_BOSS_SPRITE,
        }
        self.defeat_dialogue_portrait_sides = {
            "魔法使 Mage": "left",
        }   # 压暗背景，突出弹幕

    def setup_waves(self):
        """小怪按时间轴生成（帧）—— 亡灵主题"""
        wave1 = EnemyWave([
            _undead(100, -20, "descend"),
            _undead(cfg.BATTLE_AREA_WIDTH - 100, -20, "descend"),
        ], name="Grave Fairies")

        wave2 = EnemyWave([
            _soul(120, -30, "strafe"),
            _soul(cfg.BATTLE_AREA_WIDTH - 120, -30, "strafe"),
        ], name="Wandering Souls")

        wave3 = EnemyWave([
            _undead(80, -30, "descend"),
            _undead(cfg.BATTLE_AREA_WIDTH - 80, -30, "descend"),
            _soul(cfg.BATTLE_AREA_WIDTH / 2, -20, "strafe"),
        ], name="Tomb Patrol")

        # 12s 起：补充 10 只一组的齐射亡灵链
        chain_plan = [
            (12 * 60, cfg.BATTLE_AREA_WIDTH / 4, "Undead Chain L"),
        ]
        for chain_time, chain_x, chain_name in chain_plan:
            self.enemy_manager.add_timed_wave(
                chain_time, EnemyWave(_undead_chain(chain_x), name=chain_name))

        wave4 = EnemyWave([
            _skeleton(cfg.BATTLE_AREA_WIDTH / 2, 80),
            _undead(120, -20, "descend"),
            _undead(cfg.BATTLE_AREA_WIDTH - 120, -20, "descend"),
        ], name="Skeleton Guard")

        wave5 = EnemyWave([
            _undead(100, -30, "descend"),
            _soul(cfg.BATTLE_AREA_WIDTH / 2, -40, "strafe"),
            _undead(cfg.BATTLE_AREA_WIDTH - 100, -30, "descend"),
            _caster(cfg.BATTLE_AREA_WIDTH * 3 / 4, -30, deploy_y=165),
        ], name="Corpse Swarm")

        wave6 = EnemyWave([
            _soul(100, -30, "strafe"),
            _soul(cfg.BATTLE_AREA_WIDTH - 100, -30, "strafe"),
        ], name="Crypt Souls")

        wave7 = EnemyWave([
            _undead(120, -20, "descend"),
            _undead(cfg.BATTLE_AREA_WIDTH - 120, -20, "descend"),
        ], name="Rotting Arms")

        wave8 = EnemyWave([
            _soul(80, -30, "strafe"),
            _soul(cfg.BATTLE_AREA_WIDTH - 80, -30, "strafe"),
            _caster(100, -30, deploy_y=160),
            _caster(cfg.BATTLE_AREA_WIDTH - 100, -30, deploy_y=170),
        ], name="Last Whispers")

        wave9 = EnemyWave([
            _undead(120, -20, "descend"),
            _undead(cfg.BATTLE_AREA_WIDTH - 120, -20, "descend"),
        ], name="Hungry Corpses")

        wave10 = EnemyWave([
            _caster(cfg.BATTLE_AREA_WIDTH / 2, -40, deploy_y=165),
        ], name="Final Vigil")

        self.enemy_manager.add_timed_wave(0, wave1)
        self.enemy_manager.add_timed_wave(5 * 60, wave2)
        self.enemy_manager.add_timed_wave(10 * 60, wave3)
        self.enemy_manager.add_timed_wave(15 * 60, wave4)
        self.enemy_manager.add_timed_wave(20 * 60, wave5)
        self.enemy_manager.add_timed_wave(25 * 60, wave6)
        self.enemy_manager.add_timed_wave(30 * 60, wave7)
        self.enemy_manager.add_timed_wave(35 * 60, wave8)
        self.enemy_manager.add_timed_wave(40 * 60, wave9)
        self.enemy_manager.add_timed_wave(44 * 60, wave10)

    def setup_mid_boss(self):
        """47s 出场的道中Boss：The Watcher（注视之眼）——专属非符 + 一张符卡"""
        self.mid_boss = Boss("The Watcher", hp=WATCHER_MAX_HP,
                             x=cfg.BATTLE_AREA_WIDTH / 2, y=-40,
                             size=26, color=(90, 220, 230),
                             spell_by_hp_only=True, spell_resistance=0.5,
                             non_spell_min_duration=180,
                             non_spell_func=_non_spell_watcher_gaze,
                             hp_bar_inset=16,
                             sprite_path=cfg.WATCHER_BOSS_SPRITE,
                             sprite_scale=2.4)
        self.mid_boss.bonus_drops = ["overflux_power_orb", "revive_stone"]
        self.mid_boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 115)
        # 符卡：血量到 50% 时打出
        self.mid_boss.add_spell_card(SpellCard(
            "展符「Undead Exhibition」", spell_watcher_undead_exhibition,
            hp_threshold=0.5, bg_style="watcher"))

    def _add_post_midboss_waves(self):
        """道中Boss击破后继续生成的小怪（全部可退场，确保1分22秒左右能清空）"""
        base = self.mid_boss_defeated_at
        plans = [
            (90, [
                _undead(80, -20, "descend"),
                _undead(cfg.BATTLE_AREA_WIDTH / 2, -40, "descend"),
                _undead(cfg.BATTLE_AREA_WIDTH - 80, -20, "descend"),
            ], "Grave Scavengers"),
            (180, _undead_chain(cfg.BATTLE_AREA_WIDTH * 3 / 4), "Undead Chain R2"),
            (510, _undead_chain(cfg.BATTLE_AREA_WIDTH * 3 / 4), "Undead Chain R3"),
            (240, [
                _soul(120, -30, "strafe"),
                _soul(cfg.BATTLE_AREA_WIDTH - 120, -30, "strafe"),
                _caster(cfg.BATTLE_AREA_WIDTH * 3 / 4, -30, deploy_y=168),
            ], "Crypt Echoes"),
            (390, [
                _undead(100, -30, "descend"),
                _soul(cfg.BATTLE_AREA_WIDTH / 2, -20, "strafe"),
                _undead(cfg.BATTLE_AREA_WIDTH - 100, -30, "descend"),
            ], "Bone Veil"),
            (540, [
                _undead(60, -20, "descend"),
                _undead(180, -40, "descend"),
                _undead(cfg.BATTLE_AREA_WIDTH - 180, -40, "descend"),
                _undead(cfg.BATTLE_AREA_WIDTH - 60, -20, "descend"),
            ], "Risen Mass"),
            (600, [
                _soul(100, -30, "strafe"),
                _undead(cfg.BATTLE_AREA_WIDTH / 2, -40, "descend"),
                _soul(cfg.BATTLE_AREA_WIDTH - 100, -30, "strafe"),
                _caster(120, -30, deploy_y=165),
                _caster(cfg.BATTLE_AREA_WIDTH - 120, -30, deploy_y=170),
            ], "Final March"),
        ]
        for offset, enemies, name in plans:
            wave = EnemyWave(enemies, name=name)
            self.post_waves.append(wave)
            self.enemy_manager.add_timed_wave(base + offset, wave)

    def _on_boss_combat_start(self):
        """Bonzo 开战：视角逐渐抬升，俯瞰墓穴大厅"""
        if self.background is not None:
            self.background.ramp_view_height(120.0, 2.5)

    def setup_boss(self):
        """关底Boss：Bonzo 小丑魔术师——两阶段：
        一阶段「死符 / 骸符 / 戏符」（召唤亡灵、骸骨法术、小丑魔术）；
        被击破后原地复活回满血，二阶段「气符 / 秘仪」。
        未制作的戏符与秘仪先使用简单框架，不填充弹幕。"""
        self.boss = Boss("Bonzo", hp=BONZO_MAX_HP,
                         x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
                         size=24, color=cfg.COLOR_ORANGE,
                         spell_by_hp_only=True, spell_resistance=0.5, non_spell_level=2,
                         non_spell_min_duration=240,
                         sprite_path=cfg.BONZO_BOSS_SPRITE,
                         sprite_scale=2.6)
        self.boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 110)
        # 每两张符之间各一种专属非符（key = 下一张符卡索引）
        self.boss.non_spell_funcs = {
            0: _non_spell_bonzo_carnival,
            1: _non_spell_bonzo_skull,
            2: _non_spell_bonzo_bone_carnival,
        }
        # ??????????????????????
        self.boss.revive_skips_non_spell = True
        # 一阶段血量分段：按当前段落血量分别乘 4 / 3.5 / 1.8 / 1.5 / 1.2
        hp_after_opening = BONZO_MAX_HP - 4000
        hp_after_card1 = hp_after_opening - 3400
        hp_after_card2 = hp_after_card1 - 1600 * 1.8
        hp_after_mid = hp_after_card2 - 4000

        # 一阶段第一张符：死符（结束后直接衔接骸符，不进入非符）
        self.boss.add_spell_card(SpellCard(
            "死符「Undead Revival」", spell_bonzo_undead_revival,
            hp_threshold=hp_after_opening / BONZO_MAX_HP,
            end_hp_threshold=hp_after_card1 / BONZO_MAX_HP,
            bg_style="undead", direct_next=True))
        # 一阶段第二张符：骸符
        self.boss.add_spell_card(SpellCard(
            "骸符「Skull Dreadlord」", spell_bonzo_skull_dreadlord,
            hp_threshold=hp_after_card1 / BONZO_MAX_HP,
            end_hp_threshold=hp_after_card2 / BONZO_MAX_HP,
            bg_style="undead"))
        # 一阶段第三张符：戏符（击破后 Bonzo 死亡并原地复活）
        self.boss.add_spell_card(SpellCard(
            "戏符「Grand Illusion」", spell_bonzo_grand_illusion,
            hp_threshold=hp_after_mid / BONZO_MAX_HP,
            end_hp_threshold=0.0, bg_style="bonzo"))
        # 二阶段第一张符：气符（复活血量 10000 起手，结束阈值 0.70 →
        # 气符血量 3000，为原 6000 的一半；秘仪 Showtime 仍用独立血量）
        self.boss.add_spell_card(SpellCard(
            "气符「Balloon Barrage」", spell_bonzo_balloon_barrage,
            hp_threshold=0.80, end_hp_threshold=0.70, bg_style="bonzo"))
        # 二阶段第二张符：秘仪（最终表演）
        # Last Spell: Showtime (Bomb disabled, miss ends the spell).
        self.boss.last_spell_hp = 4000
        self.boss.set_last_spell(SpellCard(
            "\u79d8\u4eea\u300cShowtime\u300d", spell_bonzo_showtime,
            hp_threshold=0, bg_style="bonzo"))
        # 戏符结束后进入复活演出，回满血进入二阶段
        self.boss.revive_after_spell_idx = 3
        self.boss.revive_hp = BONZO_REVIVE_HP
        self.boss.revive_max_hp = BONZO_REVIVE_MAX_HP
        self.boss.revive_duration = 180

    def _start_dialogue(self):
        """关底对话：自机 Mage 与 Bonzo 战前对峙（自机立绘在左侧）"""
        self.dialogue_lines = [
            ("魔法使 Mage", "这里就是地下墓穴的深处……好浓的腐臭与笑声。"),
            ("Bonzo", "Gratz for making it this far, but I'm basically unbeatable!"),
            ("魔法使 Mage", "你就是守在这一层的小丑？看起来只是会玩气球而已。"),
            ("Bonzo", "I can summon lots of Undead. Check this out!"),
            ("魔法使 Mage", "亡灵吗……在这种地方倒是很应景。"),
            ("Bonzo", "Do you want a balloon? Everyone loves balloons!"),
            ("Bonzo", "Run, run, run, RUN! Ahahaha!"),
            ("魔法使 Mage", "我会把你那些把戏连气球一起戳破的！"),
        ]
        # 说话角色的立绘：自机 Mage 在左侧，Bonzo 在右侧
        self.dialogue_portraits = {
            "魔法使 Mage": cfg.SELF_SPRITE,
            "Bonzo": cfg.BONZO_BOSS_SPRITE,
        }
        self.dialogue_portrait_sides = {
            "魔法使 Mage": "left",
        }
        # 对话开始即让Boss入场：在场但不攻击、不显示血条
        self.setup_boss()
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)
        if self.boss:
            self.boss.hold_combat()
        self.dialogue_active = True
        self.phase = "dialogue"

    def skip_to_revival(self):
        """G key during Bonzo pre-battle dialogue: jump straight to revived phase 2."""
        if self.phase != "dialogue" or self.dialogue_is_defeat:
            return False
        self.on_dialogue_end()
        boss = self.boss
        if boss is None or len(boss.spell_cards) < 4:
            return False

        balloon_spell = boss.spell_cards[3]
        boss.arm_combat(0)
        boss.entering = False
        boss.current_spell_idx = 3
        boss.max_hp = BONZO_REVIVE_MAX_HP
        boss.hp = BONZO_REVIVE_HP
        boss._start_spell(balloon_spell)
        return True
