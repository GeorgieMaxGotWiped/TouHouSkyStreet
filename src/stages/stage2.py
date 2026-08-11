# 二面：末地最底层 ~ Dragon's Nest
# 基于 Hypixel Skyblock 的 The End / Dragon's Nest 区域
# 当前为初始化骨架：小怪 / 道中Boss / 关底Boss 均为占位，后续按主题细化

import math
import random

from src.engine import settings as cfg
from src.engine.pseudo3d import Pseudo3DFloor
from src.entities.enemy import EnemyWave, FairyEnemy, FairyVolleyEnemy, SpiritEnemy, GuardEnemy
from src.entities.boss import (
    Boss, SpellCard, spell_immobile_protector_wraith,
    _non_spell_dragon_breath, _non_spell_ender_pearl,
    spell_fireball_barrage, spell_non_directional_lightning,
    spell_one_with_the_dragons, spell_superiority,
)
from src.entities.bullet import Bullet, create_bullet_aimed, create_bullet_angle
from src.stages.stage1 import Stage, BOSS_BG_RAMP_TIME, FINAL_BOSS_BG_SPEED_MULT


# 关底末影龙总血量：= 各阶段/非符血量之和（各段血量保持不变），保证血条全程只降不升
DRAGON_MAX_HP = 13344


def _fairy(x, y, move_pattern="descend"):
    """二面妖精：使用第2面贴图，防御力为原版的1.5倍"""
    fairy = FairyEnemy(x, y, move_pattern,
                       sprite_paths=cfg.STAGE2_FAIRY_SPRITES,
                       sprite_height=cfg.STAGE2_FAIRY_SPRITE_HEIGHT)
    fairy.defense = 1.5
    return fairy


def _fairy_chain(x, count=10, spacing=40, start_y=-16, volley_stagger=8, lead_in=120):
    """一串妖精：同列依次降下，入场后按极短间隔依次开火（数值与普通妖精一致，防御力1.5倍）"""
    chain = [
        FairyVolleyEnemy(x, start_y - i * spacing, volley_index=i,
                         volley_stagger=volley_stagger, lead_in=lead_in,
                         sprite_paths=cfg.STAGE2_FAIRY_SPRITES,
                         sprite_height=cfg.STAGE2_FAIRY_SPRITE_HEIGHT)
        for i in range(count)
    ]
    for fairy in chain:
        fairy.defense = 1.5
    return chain


def _spirit(x, y, move_pattern="strafe"):
    """二面骷髅射手：使用第2面贴图，下降推进 + 水平小幅横移"""
    spirit = SpiritEnemy(x, y, move_pattern,
                         sprite_paths=cfg.STAGE2_SPIRIT_SPRITES,
                         sprite_height=cfg.STAGE2_SPIRIT_SPRITE_HEIGHT)
    spirit.move_speed = 1.1
    spirit.move_amplitude = 2.5
    spirit.defense = 1.5
    return spirit


def _guard(x, y):
    """二面守卫：使用第2面贴图，防御力为一面守卫的2.5倍"""
    guard = GuardEnemy(x, y,
                       sprite_paths=cfg.STAGE2_GUARD_SPRITES,
                       sprite_height=cfg.STAGE2_GUARD_SPRITE_HEIGHT)
    guard.defense = 2.5
    return guard


def _non_spell_stone_protector(boss, bullet_manager, timer, player_x, player_y):
    """末地石守护者专属非符「磐石镇魂」：
    三连自机狙大玉 + 顶部落石雨 + 周期性扩散镇魂环，沉稳但压迫"""
    # 三连自机狙末地石大玉（间隔递进速度，玩家需横向移动）
    if timer % 26 == 0:
        for i in range(3):
            b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 2.1 + i * 0.3,
                                    Bullet.TYPE_BIG, radius=4, color=(198, 186, 142))
            bullet_manager.add_enemy_bullet(b)
    # 顶部随机列坠下的黑曜石箭弹（落石雨）
    if timer % 48 == 0:
        x = random.uniform(50, cfg.BATTLE_AREA_WIDTH - 50)
        b = create_bullet_angle(x, -14, math.pi / 2, random.uniform(2.0, 2.8),
                                Bullet.TYPE_ARROW, radius=3, color=(150, 110, 190))
        bullet_manager.add_enemy_bullet(b)
    # 镇魂环：每 3.5s 向外扩散一圈末影珍珠青圆弹
    if timer % 210 == 0:
        for i in range(14):
            angle = i * math.pi * 2 / 14 + timer * 0.02
            b = create_bullet_angle(boss.x, boss.y, angle, 0.9,
                                    Bullet.TYPE_CIRCLE, radius=2.5, color=(86, 206, 200))
            bullet_manager.add_enemy_bullet(b)
    # 偶尔小幅横移，保持“不动”的压迫感
    if timer % 300 == 0:
        boss.target_x = max(120, min(cfg.BATTLE_AREA_WIDTH - 120,
                                     boss.x + random.uniform(-70, 70)))


class Stage2_DragonsNest(Stage):
    """Stage 2: Dragon's Nest - 末地最底层"""

    def __init__(self):
        super().__init__(2, "末地最底层 ~ Dragon's Nest",
                         bg_color=(12, 6, 22))
        # 伪3D末地地面：地面下移、两侧墙壁外移，视野更开阔；
        # 地面/洞壁贴图沿纵深方向拉伸，避免显得扁
        self.background = Pseudo3DFloor(cfg.STAGE2_FLOOR, cfg.BATTLE_AREA_WIDTH,
                                        cfg.BATTLE_AREA_HEIGHT, bg_color=self.bg_color,
                                        wall_texture_path=cfg.STAGE2_WALL,
                                        horizon_ratio=0.44, tunnel_width=2.2,
                                        far_opening=48,
                                        floor_stretch=3.0, wall_stretch=2.0)
        # 每面资源：二面曲名 / 标题卡（音乐文件未就绪时 play_music 自动跳过）
        self.title_path = cfg.STAGE2_TITLE
        self.music_path = cfg.STAGE2_MUSIC
        self.boss_music_start_path = cfg.STAGE2_BOSS_MUSIC_START
        self.boss_music_loop_path = cfg.STAGE2_BOSS_MUSIC_LOOP
        self.music_name = cfg.STAGE2_MUSIC_NAME
        self.boss_music_name = cfg.STAGE2_BOSS_MUSIC_NAME
        # 道中Boss音乐：2_1.wav
        self.mid_boss_music_path = cfg.STAGE2_MUSIC
        self.background_darkness = 120   # 压暗背景，突出弹幕
        # 战后对话：末影龙 Ender Dragon 被击破后（自机 Mage 在左侧）
        self.defeat_dialogue_lines = [
            ("魔法使 Mage", "最后一缕龙息也消散了……胜负已分。"),
            ("末影龙 Ender Dragon", "虚空……正在接纳我的力量。人类，你确实比我想象中更强。"),
            ("魔法使 Mage", "我可不是什么强者，只是想在龙巢里找点宝物罢了。"),
            ("末影龙 Ender Dragon", "带着你的战利品离开吧。愿末地的虚空……不再记住你的名字。"),
        ]
        self.defeat_dialogue_portraits = {
            "魔法使 Mage": cfg.SELF_SPRITE,
            "末影龙 Ender Dragon": cfg.END_DRAGON_BOSS_SPRITE,
        }
        self.defeat_dialogue_portrait_sides = {
            "魔法使 Mage": "left",
        }

    def setup_waves(self):
        """小怪按时间轴生成（帧）—— 占位波次，后续按末地主题细化"""
        wave1 = EnemyWave([
            _fairy(100, -20, "descend"),
            _fairy(cfg.BATTLE_AREA_WIDTH - 100, -20, "descend"),
        ], name="End Fairies")

        wave2 = EnemyWave([
            _spirit(120, -30, "strafe"),
            _spirit(cfg.BATTLE_AREA_WIDTH - 120, -30, "strafe"),
        ], name="Void Spirits")

        wave3 = EnemyWave([
            _fairy(80, -30, "descend"),
            _fairy(cfg.BATTLE_AREA_WIDTH - 80, -30, "descend"),
            _spirit(cfg.BATTLE_AREA_WIDTH / 2, -20, "strafe"),
        ], name="Ender Patrol")

        # 12s 起：左右交替补充 10 只一组的齐射妖精链（出现次数减半，仅 2 组）
        chain_plan = [
            (12 * 60, cfg.BATTLE_AREA_WIDTH / 4, "End Fairy Chain L"),
            (32 * 60, cfg.BATTLE_AREA_WIDTH * 3 / 4, "End Fairy Chain R"),
        ]
        for chain_time, chain_x, chain_name in chain_plan:
            self.enemy_manager.add_timed_wave(
                chain_time, EnemyWave(_fairy_chain(chain_x), name=chain_name))

        wave4 = EnemyWave([
            _guard(cfg.BATTLE_AREA_WIDTH / 2, 80),
            _fairy(120, -20, "descend"),
            _fairy(cfg.BATTLE_AREA_WIDTH - 120, -20, "descend"),
        ], name="Obsidian Guard")

        wave5 = EnemyWave([
            _fairy(100, -30, "descend"),
            _spirit(cfg.BATTLE_AREA_WIDTH / 2, -40, "strafe"),
            _fairy(cfg.BATTLE_AREA_WIDTH - 100, -30, "descend"),
        ], name="Void Swarm")

        wave6 = EnemyWave([
            _spirit(100, -30, "strafe"),
            _spirit(cfg.BATTLE_AREA_WIDTH - 100, -30, "strafe"),
        ], name="Crystal Spirits")

        wave7 = EnemyWave([
            _fairy(120, -20, "descend"),
            _fairy(cfg.BATTLE_AREA_WIDTH - 120, -20, "descend"),
        ], name="End Wings")

        wave8 = EnemyWave([
            _spirit(80, -30, "strafe"),
            _spirit(cfg.BATTLE_AREA_WIDTH - 80, -30, "strafe"),
        ], name="Last Echoes")

        wave9 = EnemyWave([
            _fairy(120, -20, "descend"),
            _fairy(cfg.BATTLE_AREA_WIDTH - 120, -20, "descend"),
        ], name="Dragon Hatchlings")

        wave10 = EnemyWave([
            _spirit(80, -30, "strafe"),
            _spirit(cfg.BATTLE_AREA_WIDTH - 80, -30, "strafe"),
        ], name="Final Echoes")

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
        """47s 出场的道中Boss：末地石守护者 End Stone Protector（专属非符 + 符卡）"""
        # 非符血量翻倍：总血量 6300，符卡在 1/3 处才打出（非符 4200 / 符卡 2100）
        self.mid_boss = Boss("End Stone Protector", hp=6300,
                             x=cfg.BATTLE_AREA_WIDTH / 2, y=-40,
                             size=26, color=cfg.COLOR_ORANGE,
                             spell_by_hp_only=True, spell_resistance=0.5,
                             non_spell_min_duration=180,
                             non_spell_func=_non_spell_stone_protector,
                             # 血条更宽：左右边距 16，比一面道中更长
                             hp_bar_inset=16,
                             sprite_path=cfg.END_STONE_PROTECTOR_SPRITE,
                             sprite_scale=2.6)
        self.mid_boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 110)
        # 符卡：血量到 1/3 时打出，专属非符阶段同样不简单
        self.mid_boss.add_spell_card(SpellCard(
            "石符「Immobile Protector's Wraith」", spell_immobile_protector_wraith,
            hp_threshold=1.0 / 3.0, bg_style="stone"
        ))

    def _add_post_midboss_waves(self):
        """道中Boss击破后继续生成的小怪（占位）"""
        base = self.mid_boss_defeated_at
        plans = [
            (90, [
                _fairy(80, -20, "descend"),
                _fairy(cfg.BATTLE_AREA_WIDTH / 2, -40, "descend"),
                _fairy(cfg.BATTLE_AREA_WIDTH - 80, -20, "descend"),
            ], "End Scavengers"),
            (180, _fairy_chain(cfg.BATTLE_AREA_WIDTH * 3 / 4), "End Fairy Chain R"),
            (510, _fairy_chain(cfg.BATTLE_AREA_WIDTH * 3 / 4), "End Fairy Chain R2"),
            (240, [
                _spirit(120, -30, "strafe"),
                _spirit(cfg.BATTLE_AREA_WIDTH - 120, -30, "strafe"),
            ], "Void Echoes"),
            (390, [
                _fairy(100, -30, "descend"),
                _spirit(cfg.BATTLE_AREA_WIDTH / 2, -20, "strafe"),
                _fairy(cfg.BATTLE_AREA_WIDTH - 100, -30, "descend"),
            ], "Crystal Veil"),
            (540, [
                _fairy(60, -20, "descend"),
                _fairy(180, -40, "descend"),
                _fairy(cfg.BATTLE_AREA_WIDTH - 180, -40, "descend"),
                _fairy(cfg.BATTLE_AREA_WIDTH - 60, -20, "descend"),
            ], "Dragonlings"),
            (600, [
                _spirit(100, -30, "strafe"),
                _fairy(cfg.BATTLE_AREA_WIDTH / 2, -40, "descend"),
                _spirit(cfg.BATTLE_AREA_WIDTH - 100, -30, "strafe"),
            ], "Final Roar"),
        ]
        for offset, enemies, name in plans:
            wave = EnemyWave(enemies, name=name)
            self.post_waves.append(wave)
            self.enemy_manager.add_timed_wave(base + offset, wave)

    def _on_boss_combat_start(self):
        """末影龙开战：视角逐渐抬升到高位置，俯瞰战场"""
        if self.background is not None:
            self.background.ramp_view_height(140.0, 2.5)

    def setup_boss(self):
        """关底Boss：末影龙 Ender Dragon——三张通常符 + 两张专属非符 + Last Spell「Superiority」"""
        self.boss = Boss("Ender Dragon", hp=DRAGON_MAX_HP,
                         x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
                         size=26, color=cfg.COLOR_PURPLE,
                         spell_by_hp_only=True, spell_resistance=0.5, non_spell_level=2,
                         non_spell_min_duration=240,
                         sprite_path=cfg.END_DRAGON_BOSS_SPRITE,
                         sprite_scale=2.4,
                         bullet_size_scale=2.0, bullet_density=2.0)
        self.boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 100)
        # 每两张符之间各一种专属非符（key = 下一张符卡索引）
        self.boss.non_spell_funcs = {
            1: _non_spell_dragon_breath,   # 燃符 → 闪符：龙息
            2: _non_spell_ender_pearl,     # 闪符 → 龙符：末影珍珠
        }
        self.boss.add_spell_card(SpellCard(
            "燃符「Fireball Barrage」", spell_fireball_barrage,
            # 燃符 2688（9984→7296）
            hp_threshold=9984 / DRAGON_MAX_HP, end_hp_threshold=7296 / DRAGON_MAX_HP, bg_style="fire"))
        self.boss.add_spell_card(SpellCard(
            "闪符「Non-Directional Lightning」", spell_non_directional_lightning,
            # 闪符 2352（6144→3792），其后的末影珍珠非符 672（3792→3120）
            hp_threshold=6144 / DRAGON_MAX_HP, end_hp_threshold=3792 / DRAGON_MAX_HP, bg_style="lightning"))
        self.boss.add_spell_card(SpellCard(
            "龙符「One with the Dragons」", spell_one_with_the_dragons,
            # 龙符 2520（3120→600）
            hp_threshold=3120 / DRAGON_MAX_HP, bg_style="dragon"))
        # Last Spell：超符「Superiority」——Bomb 禁用，Miss 强制结束不损残机
        # Last Spell：血量打空后才展开（黄金领域独立血量由 Boss 补充）
        self.boss.set_last_spell(SpellCard(
            "超符「Superiority」", spell_superiority,
            hp_threshold=0, bg_style="superiority"))

    def _start_dialogue(self):
        """关底对话：自机 Mage 与末影龙 Ender Dragon 战前对峙（自机立绘在左侧）"""
        self.dialogue_lines = [
            ("魔法使 Mage", "这里就是末地的最底层……沉睡在龙巢中的巨龙，终于找到了。"),
            ("末影龙 Ender Dragon", "闯入末地最底层的人类……你们惊醒了沉睡在龙巢中的我。"),
            ("魔法使 Mage", "你就是盘踞在这片虚空最深处的龙吧？抱歉吵醒你，但我不打算空手而归。"),
            ("末影龙 Ender Dragon", "愚蠢。这里没有宝藏，只有无尽的虚空与龙息。"),
            ("魔法使 Mage", "有没有宝藏，要亲眼确认才算数。既然你不肯让路，那就用弹幕说话吧！"),
            ("末影龙 Ender Dragon", "既然你们执意踏进这方寸之地，就用翅膀丈量我的愤怒吧。"),
            ("末影龙 Ender Dragon", "我会让末影珍珠与龙息，将你们彻底驱离这片天地！"),
        ]
        # 说话角色的立绘：自机 Mage 在左侧，末影龙在右侧
        self.dialogue_portraits = {
            "魔法使 Mage": cfg.SELF_SPRITE,
            "末影龙 Ender Dragon": cfg.END_DRAGON_BOSS_SPRITE,
        }
        self.dialogue_portrait_sides = {
            "魔法使 Mage": "left",
        }
        # 对话开始即让Boss入场：在场但不攻击、不显示血条
        self.setup_boss()
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)
        if self.boss:
            self.boss.hold_combat()
        self.dialogue_is_defeat = False
        self.dialogue_active = True
        self.phase = "dialogue"
