# 三面：地下墓穴 ~ The Catacombs Floor 1
# 基于 Hypixel Skyblock 的 The Catacombs Floor 1 区域
# 道中Boss：The Watcher —— 注视之眼，召唤亡灵 + 激光反制
# 关底Boss：Bonzo —— 小丑魔术师，一阶段手持暗之宝珠召唤亡灵、发射凋灵之首，
#           被击破后复活回满血，二阶段展开气球弹幕 Balloon Barrage

import math
import random

from src.engine import settings as cfg
from src.engine.pseudo3d import Pseudo3DFloor
from src.entities.enemy import EnemyWave, FairyEnemy, FairyVolleyEnemy, SpiritEnemy, GuardEnemy, GraveCasterEnemy
from src.entities.boss import Boss, SpellCard
from src.entities.bullet import Bullet, create_bullet_aimed, create_bullet_angle
from src.stages.stage1 import Stage, BOSS_BG_RAMP_TIME, FINAL_BOSS_BG_SPEED_MULT


# 道中Boss The Watcher 总血量
WATCHER_MAX_HP = 5600
# 关底Boss Bonzo 一阶段总血量（两符卡 + 两段非符）
BONZO_MAX_HP = 10000
# Bonzo 被击破后复活回满的血量（二阶段球符）
BONZO_REVIVE_HP = 10000


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
    """The Watcher 专属非符「注视」：
    三连自机狙激光箭 + 周期性激光眼线 + 顶部亡灵雨"""
    # 三连自机狙激光箭
    if timer % 24 == 0:
        for i in range(3):
            b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 3.0 + i * 0.4,
                                    Bullet.TYPE_ARROW, radius=3, color=(120, 220, 235))
            bullet_manager.add_enemy_bullet(b)
    # 激光眼线：从眼瞳两侧射出两道短暂光束（静止线，片刻后消散）
    if timer % 60 == 0:
        base = math.atan2(player_y - boss.y, player_x - boss.x)
        for side in (-0.5, 0.5):
            b = create_bullet_angle(boss.x, boss.y, base + side, 0.0,
                                    Bullet.TYPE_BEAM, radius=3, color=(110, 215, 230))
            b.manager = bullet_manager
            b.angle = base + side
            b.beam_length = 460
            b.lifetime = 30
            b.sprite_slot = "s12"
            bullet_manager.add_enemy_bullet(b)
    # 顶部亡灵雨（暗绿圆弹）
    if timer % 70 == 0:
        for _ in range(2):
            x = random.uniform(50, cfg.BATTLE_AREA_WIDTH - 50)
            b = create_bullet_angle(x, -14, math.pi / 2, random.uniform(1.8, 2.6),
                                    Bullet.TYPE_CIRCLE, radius=2.5, color=(150, 205, 110))
            bullet_manager.add_enemy_bullet(b)


def spell_watcher_gaze(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """眼符「Gaze of the Watcher」：注视之眼
    旋转激光眼线扫场 + 自机狙「眼球」大玉 + 交错扩散环"""
    # 旋转激光眼线：三条光束从眼瞳射出，逐波旋转
    if timer % 90 == 0:
        base = timer * 0.02
        for i in range(3):
            a = base + i * math.pi * 2 / 3
            b = create_bullet_angle(boss.x, boss.y, a, 0.0,
                                    Bullet.TYPE_BEAM, radius=3, color=(110, 220, 235))
            b.manager = bullet_manager
            b.angle = a
            b.beam_length = 500
            b.lifetime = 66
            b.sprite_slot = "s12"
            bullet_manager.add_enemy_bullet(b)
    # 自机狙「眼球」大玉
    if timer % 40 == 0:
        for i in range(2):
            b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 2.6 + i * 0.3,
                                    Bullet.TYPE_BIG, radius=4, color=(130, 225, 235))
            bullet_manager.add_enemy_bullet(b)
    # 交错扩散环（青辉圆弹）
    if timer % 50 == 0:
        n = 12
        base = timer * 0.03
        for i in range(n):
            a = base + i * math.tau / n
            b = create_bullet_angle(boss.x, boss.y, a, 1.6,
                                    Bullet.TYPE_CIRCLE, radius=2.5, color=(90, 195, 225))
            bullet_manager.add_enemy_bullet(b)


# ------------------------- Bonzo（关底Boss） -------------------------

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


def spell_bonzo_undead_legion(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """唤符「Undead Legion」：亡灵军团
    顶部成群落下的亡灵雨 + 左右夹击刀弹 + 自机狙骷髅大玉"""
    # 亡灵雨：顶部随机落下
    if timer % 10 == 0:
        x = random.uniform(40, cfg.BATTLE_AREA_WIDTH - 40)
        b = create_bullet_angle(x, -14, math.pi / 2, random.uniform(1.6, 2.4),
                                Bullet.TYPE_CIRCLE, radius=2.5, color=(140, 200, 110))
        bullet_manager.add_enemy_bullet(b)
    # 左右夹击刀弹（两侧向中间推进）
    if timer % 80 == 0:
        for i in range(3):
            y = 120 + i * 130
            b = create_bullet_angle(cfg.BATTLE_AREA_WIDTH + 20, y, math.pi, 2.2,
                                    Bullet.TYPE_KNIFE, radius=2.5, color=(165, 120, 215))
            bullet_manager.add_enemy_bullet(b)
            b = create_bullet_angle(-20, y, 0.0, 2.2,
                                    Bullet.TYPE_KNIFE, radius=2.5, color=(165, 120, 215))
            bullet_manager.add_enemy_bullet(b)
    # 自机狙骷髅大玉
    if timer % 60 == 0:
        for i in range(3):
            b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 2.2 + i * 0.4,
                                    Bullet.TYPE_BIG, radius=4, color=(185, 150, 215))
            bullet_manager.add_enemy_bullet(b)


def spell_bonzo_wither_skull(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """骸符「Wither Skull Barrage」：凋灵之首齐射
    旋转骷髅扇 + 高速自机狙刀弹 + 圆周凋灵环"""
    # 旋转骷髅扇（大玉）
    if timer % 16 == 0:
        base = timer * 0.06
        for i in range(4):
            a = base + i * math.pi / 2
            b = create_bullet_angle(boss.x, boss.y, a, 1.9,
                                    Bullet.TYPE_BIG, radius=4, color=(200, 160, 230))
            bullet_manager.add_enemy_bullet(b)
    # 高速自机狙刀弹
    if timer % 48 == 0:
        b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 3.6,
                                Bullet.TYPE_KNIFE, radius=2.5, color=(150, 210, 130))
        bullet_manager.add_enemy_bullet(b)
    # 圆周凋灵环
    if timer % 100 == 0:
        n = 14
        base = timer * 0.02
        for i in range(n):
            a = base + i * math.tau / n
            b = create_bullet_angle(boss.x, boss.y, a, 1.4,
                                    Bullet.TYPE_CIRCLE, radius=3, color=(160, 110, 200))
            bullet_manager.add_enemy_bullet(b)


def spell_bonzo_balloon_barrage(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """球符「Balloon Barrage」：气球弹幕
    Bonzo 复活后守在竞技场中央，向四面八方连续射出彩色气球"""
    # 彩色气球弹：全方位扩散（连续多波，色彩轮换）
    if timer % 14 == 0:
        colors = ((235, 90, 130), (90, 200, 220), (235, 200, 90), (150, 230, 120))
        n = 18
        base = timer * 0.05
        wave = timer // 14
        for i in range(n):
            a = base + i * math.tau / n
            col = colors[(i + wave) % len(colors)]
            b = create_bullet_angle(boss.x, boss.y, a, 1.6,
                                    Bullet.TYPE_CIRCLE, radius=3, color=col)
            bullet_manager.add_enemy_bullet(b)
    # 大幅自机狙气球（大玉）
    if timer % 70 == 0:
        b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 2.6,
                                Bullet.TYPE_BIG, radius=4, color=(240, 120, 160))
        bullet_manager.add_enemy_bullet(b)
    # 彩带箭弹环：旋转扩散
    if timer % 200 == 0:
        n = 20
        base = timer * 0.02
        for i in range(n):
            a = base + i * math.tau / n
            b = create_bullet_angle(boss.x, boss.y, a, 2.2,
                                    Bullet.TYPE_ARROW, radius=3, color=(235, 200, 120))
            bullet_manager.add_enemy_bullet(b)


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
        self.mid_boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 115)
        # 符卡：血量到 50% 时打出
        self.mid_boss.add_spell_card(SpellCard(
            "眼符「Gaze of the Watcher」", spell_watcher_gaze,
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
        一阶段「唤符 / 骸符」（召唤亡灵 + 凋灵之首，手持暗之宝珠）；
        被击破后复活回满血，二阶段展开 Last Spell「球符 Balloon Barrage」"""
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
            0: _non_spell_bonzo_orb,
            1: _non_spell_bonzo_skull,
        }
        # 一阶段第一张符：唤符（7200→4600）
        self.boss.add_spell_card(SpellCard(
            "唤符「Undead Legion」", spell_bonzo_undead_legion,
            hp_threshold=0.72, end_hp_threshold=0.46, bg_style="undead"))
        # 一阶段第二张符：骸符（3400→0，击破后「复活」）
        self.boss.add_spell_card(SpellCard(
            "骸符「Wither Skull Barrage」", spell_bonzo_wither_skull,
            hp_threshold=0.34, end_hp_threshold=0.0, bg_style="undead"))
        # 二阶段（复活回满）：球符 Balloon Barrage
        self.boss.last_spell_hp = BONZO_REVIVE_HP
        self.boss.set_last_spell(SpellCard(
            "球符「Balloon Barrage」", spell_bonzo_balloon_barrage,
            hp_threshold=0, bg_style="bonzo"))

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