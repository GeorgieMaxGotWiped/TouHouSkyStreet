# 关卡/阶段基类

import pygame
import random
from src.engine import settings as cfg
from src.engine.pseudo3d import Pseudo3DFloor
from src.entities.enemy import EnemyManager, EnemyWave, FairyEnemy, SpiritEnemy, GuardEnemy
from src.entities.boss import Boss, SpellCard
from src.entities.boss import (
    spell_luxurious_spool,
    spell_soul_string, spell_tarantula_tornado, spell_dark_queen_soul,
)


# 时间轴常量（帧，60FPS）
MID_BOSS_APPEAR_TIME = 47 * 60    # 47s：道中Boss出场
DIALOGUE_TIME = 82 * 60           # 1分22秒：小怪清空后进入对话
BOSS_COMBAT_DELAY = int(0.6 * cfg.FPS)   # 对话结束后等待 0.6s 再开战

# Boss出场时背景滚动加速
BOSS_BG_SPEED_MULT = 2.0        # 速度倍率
BOSS_BG_RAMP_TIME = 2.0         # 平滑过渡时长（秒）
FINAL_BOSS_BG_SPEED_MULT = 3.5    # 关底Boss速度倍率


class Stage:
    """关卡基类"""
    def __init__(self, stage_num, name, bg_color=None):
        self.stage_num = stage_num
        self.name = name
        self.bg_color = bg_color or (8, 8, 24)
        self.background = None          # 伪3D背景渲染器（可空）
        self.background_darkness = 0    # 背景压暗（0-255，越大越暗，让弹幕更清晰）
        self.enemy_manager = EnemyManager()
        self.mid_boss = None          # 道中Boss（47s出场）
        self.boss = None              # 1面Boss（对话后登场，暂未接入）
        self.timer = 0                # 关卡计时器（帧）
        self.phase = "intro"          # intro / mid_boss / post_midboss / dialogue / boss / cleared

        # 对话
        self.dialogue_lines = []
        self.dialogue_portraits = {}   # {角色名: 立绘贴图路径}
        self.dialogue_portrait_sides = {}   # {角色名: "left"/"right"}，默认右侧
        self.dialogue_active = False
        # 战后对话（Boss 被击破后、通关结算前）：Boss 留在场上完成对话
        self.dialogue_is_defeat = False
        self.defeat_dialogue_lines = []
        self.defeat_dialogue_portraits = {}
        self.defeat_dialogue_portrait_sides = {}
        self.post_waves = []          # 道中Boss击破后的小怪（全部清空后进入对话）
        self.mid_boss_defeated_at = None
        self.post_waves_added = False

        # 曲名（PlayingState 在面开始 / Boss战开始时显示）
        self.music_name = ""
        self.boss_music_name = ""

        # 每面资源（音乐 / 标题卡）：基类默认一面，子类可覆写
        self.title_path = cfg.STAGE1_TITLE
        self.music_path = cfg.STAGE1_MUSIC
        self.boss_music_start_path = cfg.STAGE1_BOSS_MUSIC_START
        self.boss_music_loop_path = cfg.STAGE1_BOSS_MUSIC_LOOP
        # 道中Boss音乐：None 表示继续播放道中曲，不额外切换
        self.mid_boss_music_path = None

    def setup_waves(self):
        """子类重写：按时间轴设置小怪波次"""
        raise NotImplementedError

    def setup_mid_boss(self):
        """子类重写：设置道中Boss"""
        raise NotImplementedError

    def setup_boss(self):
        """子类重写：设置1面Boss（对话后登场）"""
        raise NotImplementedError

    def _add_post_midboss_waves(self):
        """子类重写：道中Boss击破后追加的小怪波次"""
        pass

    def _ramp_background_speed(self, multiplier, duration):
        # Boss出场时让背景滚动速度平滑加速（无背景渲染器时忽略）
        if self.background is not None and hasattr(self.background, "ramp_speed"):
            self.background.ramp_speed(multiplier, duration)

    def update(self, dt, bullet_manager, player_x, player_y):
        if self.background:
            self.background.update(dt)
        self.timer += 1

        if self.phase == "intro":
            self.enemy_manager.update(dt, bullet_manager, player_x, player_y,
                                      stage_time=self.timer)
            if self.timer >= MID_BOSS_APPEAR_TIME:
                self.setup_mid_boss()
                self._ramp_background_speed(BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)
                self.phase = "mid_boss"

        elif self.phase == "mid_boss":
            self.enemy_manager.update(dt, bullet_manager, player_x, player_y,
                                      stage_time=self.timer)
            if self.mid_boss and self.mid_boss.alive:
                self.mid_boss.update(dt, bullet_manager, player_x, player_y)
            elif self.mid_boss:
                self.mid_boss_defeated_at = self.timer
                self._ramp_background_speed(1.0, BOSS_BG_RAMP_TIME)
                self.phase = "post_midboss"

        elif self.phase == "post_midboss":
            # 道中Boss符卡背景淡出期间继续推进
            if self.mid_boss is not None and self.mid_boss.spell_bg is not None:
                self.mid_boss.update(dt, bullet_manager, player_x, player_y)
            if not self.post_waves_added:
                self._add_post_midboss_waves()
                self.post_waves_added = True
            self.enemy_manager.update(dt, bullet_manager, player_x, player_y,
                                      stage_time=self.timer)
            if (self.timer >= DIALOGUE_TIME
                    and self.post_waves
                    and all(w.all_dead for w in self.post_waves)):
                self._start_dialogue()

        elif self.phase == "dialogue":
            # 对话期间Boss入场（仅移动，不攻击、不显示血条）
            if self.boss and self.boss.alive:
                self.boss.update(dt, bullet_manager, player_x, player_y)

        elif self.phase == "boss":
            if self.boss:
                # 死亡/结符后仍推进，让符卡背景淡出播完
                self.boss.update(dt, bullet_manager, player_x, player_y)
                if not self.boss.alive:
                    # Boss 被击破：不立即消失，先进行战后对话
                    self._start_defeat_dialogue()

        elif self.phase == "defeat_dialogue":
            # 战后对话：Boss 已击破但留在场上，仅推进符卡背景淡出
            if self.boss is not None and self.boss.spell_bg is not None:
                self.boss.update(dt, bullet_manager, player_x, player_y)

        elif self.phase == "cleared":
            # 结符淡出未播完时继续推进（Boss 已死亡，只更新符卡背景）
            if self.boss is not None and self.boss.spell_bg is not None:
                self.boss.update(dt, bullet_manager, player_x, player_y)

    def _start_dialogue(self):
        self.dialogue_lines = [
            ("蜘蛛女王 Arachne", "你们竟敢召唤黑暗女王？胆敢挑战我的存在..."),
            ("蜘蛛女王 Arachne", "嘎哈哈哈哈！真是令人厌烦……不过，看来并非只有你们准备了后手！"),
            ("蜘蛛女王 Arachne", "蜘蛛巢穴之中，蛛群已至……你能数清十只吗？"),
            ("蜘蛛女王 Arachne", "就让你们先品尝一丝吧——那即将降临这个世界的无尽蛛潮！"),
        ]
        # Arachne 说话时在对话框旁显示立绘
        self.dialogue_portraits = {
            "蜘蛛女王 Arachne": cfg.ARACHNE_BOSS_SPRITE,
        }
        # 对话开始即让Boss入场：在场但不攻击、不显示血条
        self.setup_boss()
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)
        if self.boss:
            self.boss.hold_combat()
        self.dialogue_is_defeat = False
        self.dialogue_active = True
        self.phase = "dialogue"

    def on_dialogue_end(self):
        """对话结束（PlayingState 已切换Boss战音乐）：等待 0.6s 后Boss开战"""
        self.dialogue_active = False
        if self.boss is None:
            self.setup_boss()
        if self.boss:
            self.boss.arm_combat(BOSS_COMBAT_DELAY)
        self.phase = "boss"
        self._on_boss_combat_start()

    def _start_defeat_dialogue(self):
        """Boss 被击破后：留在场上进行战后对话，对话结束后进入通关结算"""
        if not self.defeat_dialogue_lines:
            # 未配置战后对话：直接进入通关结算，避免卡在对话阶段
            self.dialogue_is_defeat = False
            self.dialogue_active = False
            self.phase = "cleared"
            self._ramp_background_speed(1.0, BOSS_BG_RAMP_TIME)
            return
        self.dialogue_lines = self.defeat_dialogue_lines
        self.dialogue_portraits = self.defeat_dialogue_portraits
        self.dialogue_portrait_sides = self.defeat_dialogue_portrait_sides
        self.dialogue_is_defeat = True
        self.dialogue_active = True
        self.phase = "defeat_dialogue"
        self._ramp_background_speed(1.0, BOSS_BG_RAMP_TIME)

    def on_defeat_dialogue_end(self):
        """战后对话结束：进入通关结算"""
        self.dialogue_active = False
        self.phase = "cleared"
        self._ramp_background_speed(1.0, BOSS_BG_RAMP_TIME)

    def _on_boss_combat_start(self):
        """子类可覆写：关底Boss开战时触发（如背景视角变化）"""
        pass

    def draw(self, screen, offset_x=0, offset_y=0):
        # 背景（仅战斗区域）
        pygame.draw.rect(screen, self.bg_color,
                         (offset_x, offset_y, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT))
        # 符卡背景已完全覆盖时跳过伪3D背景绘制（省性能）
        hide_floor = any(
            b is not None and b.spell_bg is not None and not b.spell_bg.done and b.spell_bg.is_opaque
            for b in (self.mid_boss, self.boss))
        if self.background and not hide_floor:
            self.background.draw(screen, offset_x, offset_y)
            if self.background_darkness:
                dark = pygame.Surface(
                    (cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT), pygame.SRCALPHA)
                dark.fill((0, 0, 0, self.background_darkness))
                screen.blit(dark, (offset_x, offset_y))

        # 符卡特殊背景（Boss 展开符卡时覆盖在关卡背景之上、弹幕之下）
        for boss_ref in (self.mid_boss, self.boss):
            if boss_ref is not None and boss_ref.spell_bg is not None and not boss_ref.spell_bg.done:
                boss_ref.spell_bg.draw(screen, offset_x, offset_y)

        # 小怪
        if self.phase in ("intro", "mid_boss", "post_midboss", "dialogue"):
            self.enemy_manager.draw(screen, offset_x, offset_y)

        # 道中Boss
        if self.mid_boss and self.mid_boss.alive:
            self.mid_boss.draw(screen, offset_x, offset_y)

        # 关底Boss：战后对话期间 Boss 留在场上
        if self.boss and (self.boss.alive or self.phase == "defeat_dialogue"):
            self.boss.draw(screen, offset_x, offset_y)

    def draw_foreground(self, screen, offset_x=0, offset_y=0):
        """子弹与自机之后的战斗区前景层，供关卡/符卡绘制覆盖特效。"""
        pass

    def is_cleared(self):
        return self.phase == "cleared"

    def get_active_enemies(self):
        enemies = []
        if self.phase in ("intro", "mid_boss", "post_midboss"):
            enemies.extend(self.enemy_manager.get_active_enemies())
        if self.phase == "mid_boss" and self.mid_boss and self.mid_boss.alive:
            enemies.append(self.mid_boss)
        elif self.boss and self.boss.alive and self.boss.combat_enabled:
            enemies.append(self.boss)
        return enemies


class Stage1_SkyblockHub(Stage):
    """Stage 1: Spider's Den - 蜘蛛的巢穴"""

    def __init__(self):
        super().__init__(1, "蜘蛛的巢穴 ~ Spider's Den",
                         bg_color=(8, 12, 32))
        # 伪3D洞穴地面
        self.background = Pseudo3DFloor(cfg.STAGE1_FLOOR, cfg.BATTLE_AREA_WIDTH,
                                        cfg.BATTLE_AREA_HEIGHT, bg_color=self.bg_color,
                                        wall_texture_path=cfg.STAGE1_WALL)
        # 本面道中 / Boss战音乐名
        self.music_name = cfg.STAGE1_MUSIC_NAME
        self.boss_music_name = cfg.STAGE1_BOSS_MUSIC_NAME
        # 战后对话：蜘蛛女王 Arachne 被击破后（自机 Mage 在左侧）
        self.defeat_dialogue_lines = [
            ("魔法使 Mage", "呼……蛛丝终于全部斩断了。蜘蛛女王，看来也不过如此嘛。"),
            ("蜘蛛女王 Arachne", "嘎……竟敢击碎我的暗之女王之魂……你们究竟是什么来头？"),
            ("魔法使 Mage", "只是路过的魔法使罢了。这片巢穴里的宝物，我就收下了。"),
            ("蜘蛛女王 Arachne", "哼……拿去吧。只要蜘蛛之巢尚存，我终有一日会重新织起这张网……"),
        ]
        self.defeat_dialogue_portraits = {
            "魔法使 Mage": cfg.SELF_SPRITE,
            "蜘蛛女王 Arachne": cfg.ARACHNE_BOSS_SPRITE,
        }
        self.defeat_dialogue_portrait_sides = {
            "魔法使 Mage": "left",
        }

    def setup_waves(self):
        """小怪按时间轴生成（帧）"""
        # 0s: 三只妖精从左右入场
        wave1 = EnemyWave([
            FairyEnemy(100, -20, "descend"),
            FairyEnemy(cfg.BATTLE_AREA_WIDTH / 2, -40, "descend"),
            FairyEnemy(cfg.BATTLE_AREA_WIDTH - 100, -20, "descend"),
        ], name="Forest Fairies")

        # 5s: 左右各两只
        wave2 = EnemyWave([
            FairyEnemy(60, -20, "descend"),
            FairyEnemy(140, -50, "descend"),
            FairyEnemy(cfg.BATTLE_AREA_WIDTH - 60, -20, "descend"),
            FairyEnemy(cfg.BATTLE_AREA_WIDTH - 140, -50, "descend"),
        ], name="Fairy Squad")

        # 10s: 灵体
        wave3 = EnemyWave([
            SpiritEnemy(120, -30, "sin"),
            SpiritEnemy(cfg.BATTLE_AREA_WIDTH - 120, -30, "sin"),
        ], name="Wandering Spirits")

        # 15s: 混合
        wave4 = EnemyWave([
            FairyEnemy(80, -30, "descend"),
            FairyEnemy(cfg.BATTLE_AREA_WIDTH - 80, -30, "descend"),
            SpiritEnemy(cfg.BATTLE_AREA_WIDTH / 2, -20, "sin"),
        ], name="Mixed Assault")

        # 20s: 守卫
        wave5 = EnemyWave([
            GuardEnemy(cfg.BATTLE_AREA_WIDTH / 2, 80),
            FairyEnemy(120, -20, "descend"),
            FairyEnemy(cfg.BATTLE_AREA_WIDTH - 120, -20, "descend"),
        ], name="Guardian Appears")

        # 25s: 补位小怪
        wave6 = EnemyWave([
            FairyEnemy(80, -20, "descend"),
            SpiritEnemy(cfg.BATTLE_AREA_WIDTH / 2, -20, "sin"),
            FairyEnemy(cfg.BATTLE_AREA_WIDTH - 80, -20, "descend"),
        ], name="Silk Drift")

        # 30s: 妖精小队
        wave7 = EnemyWave([
            FairyEnemy(100, -30, "descend"),
            FairyEnemy(cfg.BATTLE_AREA_WIDTH / 2, -40, "descend"),
            FairyEnemy(cfg.BATTLE_AREA_WIDTH - 100, -30, "descend"),
        ], name="Swarming Fairies")

        # 35s: 灵体
        wave8 = EnemyWave([
            SpiritEnemy(100, -30, "sin"),
            SpiritEnemy(cfg.BATTLE_AREA_WIDTH - 100, -30, "sin"),
        ], name="Nest Spirits")

        # 40s: 妖精
        wave9 = EnemyWave([
            FairyEnemy(120, -20, "descend"),
            FairyEnemy(cfg.BATTLE_AREA_WIDTH - 120, -20, "descend"),
        ], name="Web Threads")

        # 44s: 收尾灵体（Arachne 出场前清场）
        wave10 = EnemyWave([
            SpiritEnemy(80, -30, "sin"),
            SpiritEnemy(cfg.BATTLE_AREA_WIDTH - 80, -30, "sin"),
        ], name="Last Threads")

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
        """47s 出场的道中Boss：蜘蛛女王 Arachne（仅一张符卡）"""
        self.mid_boss = Boss("Arachne", hp=2400,
                             x=cfg.BATTLE_AREA_WIDTH / 2, y=-40,
                             size=22, color=cfg.COLOR_PURPLE,
                             spell_by_hp_only=True, spell_resistance=0.5, non_spell_level=1,
                             sprite_path=cfg.ARACHNE_BOSS_SPRITE,
                             sprite_scale=2.2)
        self.mid_boss.bonus_drops = ["overflux_power_orb"]
        self.mid_boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 110)
        # 符卡：血量到 50% 时才打出，开符后受伤变为 50%
        self.mid_boss.add_spell_card(SpellCard(
            "罠符「Luxurious Spool」", spell_luxurious_spool,
            hp_threshold=1.0 / 3.0
        ))

    def _add_post_midboss_waves(self):
        """道中Boss击破后继续生成的小怪（全部可退场，确保1分22秒左右能清空）"""
        base = self.mid_boss_defeated_at
        plans = [
            (90, [
                FairyEnemy(80, -20, "descend"),
                FairyEnemy(cfg.BATTLE_AREA_WIDTH / 2, -40, "descend"),
                FairyEnemy(cfg.BATTLE_AREA_WIDTH - 80, -20, "descend"),
            ], "Silk Skirmish"),
            (240, [
                SpiritEnemy(120, -30, "sin"),
                SpiritEnemy(cfg.BATTLE_AREA_WIDTH - 120, -30, "sin"),
            ], "Weaving Spirits"),
            (390, [
                FairyEnemy(100, -30, "descend"),
                SpiritEnemy(cfg.BATTLE_AREA_WIDTH / 2, -20, "sin"),
                FairyEnemy(cfg.BATTLE_AREA_WIDTH - 100, -30, "descend"),
            ], "Thread Barrier"),
            (540, [
                FairyEnemy(60, -20, "descend"),
                FairyEnemy(180, -40, "descend"),
                FairyEnemy(cfg.BATTLE_AREA_WIDTH - 180, -40, "descend"),
                FairyEnemy(cfg.BATTLE_AREA_WIDTH - 60, -20, "descend"),
            ], "Spiderlings"),
            (660, [
                SpiritEnemy(100, -30, "sin"),
                FairyEnemy(cfg.BATTLE_AREA_WIDTH / 2, -40, "descend"),
                SpiritEnemy(cfg.BATTLE_AREA_WIDTH - 100, -30, "sin"),
            ], "Final Web"),
        ]
        for offset, enemies, name in plans:
            wave = EnemyWave(enemies, name=name)
            self.post_waves.append(wave)
            self.enemy_manager.add_timed_wave(base + offset, wave)

    def setup_boss(self):
        """1面Boss：蜘蛛女王 Arachne（三张符卡，首符前与符卡间均为非符阶段）"""
        self.boss = Boss("Arachne", hp=9000,
                         x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
                         size=22, color=cfg.COLOR_PURPLE,
                         spell_by_hp_only=True, spell_resistance=0.5, non_spell_level=2,
                         non_spell_min_duration=240,
                         sprite_path=cfg.ARACHNE_BOSS_SPRITE,
                         sprite_scale=2.2)
        self.boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 100)

        # 符卡：仅按血量触发，符卡间自动回到非符阶段
        self.boss.add_spell_card(SpellCard(
            "丝符「Soul String」", spell_soul_string,
            hp_threshold=0.75
        ))
        self.boss.add_spell_card(SpellCard(
            "蛛符「Tarantula's Tornado」", spell_tarantula_tornado,
            hp_threshold=0.45
        ))
        self.boss.add_spell_card(SpellCard(
            "魂符「Dark Queen's Soul」", spell_dark_queen_soul,
            hp_threshold=0.12
        ))
