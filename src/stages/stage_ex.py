# -*- coding: utf-8 -*-
# Ex 面：裂隙 ~ The Rift（主菜单「Extra Stage」直接进入的额外面）
#
# 与 1~6 面的差异（其余流程沿用 Stage 基类）：
#   1) 不经仓库出征：主菜单 → 选自机 → 选难度 → 直接开打；装备物品效果一律不生效，
#      战后也不进休整 / Boss 奖励界面（通关后回主菜单）；
#   2) 道中Boss Wizardman 先对话再开打（覆写基类的 _begin_mid_boss）；
#   3) 关底Boss Barry 暂不配符卡，整场以自定义非符弹幕撑起，战后对话结束即通关。
#
# 资料来自 Hypixel SkyBlock Wiki（Fandom）：
#   - Wizardman：自称多元宇宙的救世主，「Wizardman 不是一个人，而是一份传承」，
#     在 Wizardman Bureau 设下三项试炼（Temporal Race 竞速 / Wizard Brawl 交锋 /
#     Quad Link Legacy 四子连线），试炼奖励碎片可拼出他的护甲。
#   - Barry：SkyBlock Year 223 落选的前市长，如今在 Rift 的 Barry HQ 继续准备
#     「下一届 Rift 选举」，张口就是五级税率与竞选口号，还认为整个宇宙跑在计算机上。
#   - 小怪名字取自 Rift 的真实怪：Globowl / Blobbercyst / Scribe Crux / Riftstalker
#     Bloodfiend（Stillgore Château 的吸血鬼）；Wizardman 的台词里也提过「清剿 vermin」。

import math
import random

from src.engine import settings as cfg
from src.engine.pseudo3d import Pseudo3DFloor
from src.entities.boss import Boss
from src.entities.bullet import Bullet, create_bullet_angle
from src.entities.enemy import Enemy, EnemyWave
from src.stages.stage1 import (
    Stage,
    BOSS_BG_RAMP_TIME,
    BOSS_BG_SPEED_MULT,
    BOSS_COMBAT_DELAY,
    FINAL_BOSS_BG_SPEED_MULT,
)

# 时间轴（帧，60FPS）：道中Boss 45s 出场（先对话），其后小怪清空即进入 Barry 战前对话
MID_BOSS_APPEAR_TIME = 45 * 60
DIALOGUE_TIME = 100 * 60

# Boss 血量（无符卡：整场都是非符阶段，所以血量比同级的符卡 Boss 低一档）
MID_BOSS_HP = 6400
FINAL_BOSS_HP = 16500

TAU = math.tau


def _add(bullet_manager, bullet):
    bullet_manager.add_enemy_bullet(bullet)


# ---------------------------------------------------------------------------
# Ex 面小怪（裂隙生物）
# ---------------------------------------------------------------------------
class RiftVerminEnemy(Enemy):
    """裂隙虫：贴地扑来的小虫，逼近后自机狙。"""
    def __init__(self, x, y, move_pattern="descend"):
        super().__init__(x, y, hp=70, score=650, size=12, color=(190, 120, 220),
                         sprite_paths=cfg.EX_VERMIN_SPRITES,
                         sprite_height=cfg.EX_VERMIN_SPRITE_HEIGHT, anim_speed=12)
        self.move_pattern = move_pattern
        self.move_speed = 1.9
        self.move_amplitude = 2.0
        self.shoot_interval = 92
        self.shoot_pattern = "none"

    def shoot(self, bullet_manager, player_x, player_y):
        base = math.atan2(player_y - self.y, player_x - self.x)
        for offset in (-0.1, 0.1):
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, base + offset, 2.7, Bullet.TYPE_CIRCLE,
                radius=2.5, color=(205, 130, 235)))


class GlobowlEnemy(Enemy):
    """Globowl：竞技场圆枭，横移投出扇形黏弹。"""
    def __init__(self, x, y):
        super().__init__(x, y, hp=180, score=1300, size=16, color=(140, 210, 190),
                         sprite_paths=cfg.EX_GLOBOWL_SPRITES,
                         sprite_height=cfg.EX_GLOBOWL_SPRITE_HEIGHT, anim_speed=18)
        self.move_pattern = "strafe"
        self.move_speed = 0.7
        self.move_amplitude = 2.6
        self.shoot_interval = 104
        self.shoot_pattern = "none"
        self._shots = 0

    def shoot(self, bullet_manager, player_x, player_y):
        self._shots += 1
        base = math.atan2(player_y - self.y, player_x - self.x)
        for i in range(4):
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, base + (i - 1.5) * 0.17, 2.3,
                Bullet.TYPE_CIRCLE, radius=2.5, color=(120, 235, 205)))
        if self._shots % 3 == 0:
            for i in range(10):
                a = i * TAU / 10 + self.age * 0.014
                _add(bullet_manager, create_bullet_angle(
                    self.x, self.y, a, 1.5, Bullet.TYPE_RICE,
                    radius=2.5, color=(90, 190, 175)))


class BlobbercystEnemy(Enemy):
    """Blobbercyst：从裂隙渗出的泡囊，缓缓下沉并散出环弹。"""
    def __init__(self, x, y, deploy_y=180):
        super().__init__(x, y, hp=220, score=1500, size=17, color=(160, 90, 200),
                         sprite_paths=cfg.EX_BLOBBERCYST_SPRITES,
                         sprite_height=cfg.EX_BLOBBERCYST_SPRITE_HEIGHT, anim_speed=20)
        self.move_pattern = "descend"
        self.move_speed = 0.65
        self.shoot_interval = 118
        self.shoot_pattern = "none"
        self.deploy_y = deploy_y

    def _move(self):
        if self.y < self.deploy_y:
            self.y += self.move_speed
        else:
            self.x += math.sin(self.age * 0.02) * 1.4

    def shoot(self, bullet_manager, player_x, player_y):
        for i in range(12):
            a = i * TAU / 12 + self.age * 0.02
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, a, 1.7, Bullet.TYPE_CIRCLE,
                radius=2.5, color=(185, 110, 225)))


class RiftVampireEnemy(Enemy):
    """裂隙吸血鬼（Riftstalker Bloodfiend）：横移接近，三向刀弹压迫。"""
    def __init__(self, x, y):
        super().__init__(x, y, hp=210, score=1900, size=18, color=(200, 70, 110),
                         sprite_paths=cfg.EX_VAMPIRE_SPRITES,
                         sprite_height=cfg.EX_VAMPIRE_SPRITE_HEIGHT, anim_speed=16)
        self.move_pattern = "strafe"
        self.move_speed = 0.9
        self.move_amplitude = 2.2
        self.shoot_interval = 96
        self.shoot_pattern = "none"

    def shoot(self, bullet_manager, player_x, player_y):
        base = math.atan2(player_y - self.y, player_x - self.x)
        for offset in (-0.3, 0.0, 0.3):
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, base + offset, 2.8, Bullet.TYPE_KNIFE,
                radius=2.5, color=(235, 90, 120)))


class ScribeCruxEnemy(Enemy):
    """Crux 刻印者：缓慢逼近的重装刻印者，扇形 + 大玉。"""
    def __init__(self, x, y):
        super().__init__(x, y, hp=300, score=2400, size=20, color=(120, 160, 230),
                         sprite_paths=cfg.EX_CRUX_SPRITES,
                         sprite_height=cfg.EX_CRUX_SPRITE_HEIGHT, anim_speed=22)
        self.move_pattern = "strafe"
        self.move_speed = 0.6
        self.move_amplitude = 1.8
        self.shoot_interval = 112
        self.shoot_pattern = "none"
        self._shots = 0

    def shoot(self, bullet_manager, player_x, player_y):
        self._shots += 1
        base = math.atan2(player_y - self.y, player_x - self.x)
        for i in range(5):
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, base + (i - 2) * 0.13, 2.4,
                Bullet.TYPE_RICE, radius=2.5, color=(130, 170, 245)))
        if self._shots % 2 == 0:
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, math.pi / 2, 1.15, Bullet.TYPE_BIG,
                radius=5, color=(110, 150, 230)))


# ---------------------------------------------------------------------------
# 非符弹幕（两位 Boss 都还没有符卡）
# ---------------------------------------------------------------------------
def _nonspell_wizardman(boss, bullet_manager, timer, player_x, player_y):
    """Wizardman 非符：三场试炼轮番上演（交锋 / 竞速 / 四子连线 / 回退）。"""
    base = math.atan2(player_y - boss.y, player_x - boss.x)

    # Wizard Brawl：正面三向交锋
    if timer % 24 == 0:
        for offset in (-0.22, 0.0, 0.22):
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, base + offset, 2.9, Bullet.TYPE_KNIFE,
                radius=2.5, color=(240, 130, 160)))

    # Temporal Race：两条反向旋转的「赛道」
    if timer % 6 == 0:
        spin = timer * 0.028
        for side in (0.0, math.pi):
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, spin + side, 1.75, Bullet.TYPE_CIRCLE,
                radius=2.5, color=(185, 100, 225)))

    # Quad Link Legacy：七列「连四」弹柱落下
    if timer % 150 == 60:
        span = cfg.BATTLE_AREA_WIDTH - 156
        for i in range(7):
            x = 78 + i * span / 6.0
            _add(bullet_manager, create_bullet_angle(
                x, -12, math.pi / 2, 2.4, Bullet.TYPE_RICE,
                radius=2.5, color=(255, 205, 95)))

    # 回退按钮：隔一段时间换一侧站位，像被按下了倒带
    if timer % 230 == 0:
        boss.move_to(cfg.BATTLE_AREA_WIDTH * random.choice((0.27, 0.73)), 120)


def _nonspell_barry(boss, bullet_manager, timer, player_x, player_y):
    """Barry 非符：竞选纲领（五级税率 / 强调手势 / 翻转世界 / 抗议标语）。"""
    base = math.atan2(player_y - boss.y, player_x - boss.x)

    # 五级税率：每 60 帧放出一级，环越往后越大越密（10% → 50%）
    cycle = timer % 300
    if cycle % 60 == 0:
        bracket = min(4, cycle // 60)
        count = 8 + bracket * 4
        speed = 1.5 + bracket * 0.17
        for i in range(count):
            a = i * TAU / count + timer * 0.004
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, a, speed, Bullet.TYPE_CIRCLE,
                radius=2.5, color=(255, 215, 120 + bracket * 12)))

    # 强调手势：自机狙点射
    if timer % 34 == 0:
        for offset in (-0.12, 0.12):
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, base + offset, 3.0, Bullet.TYPE_RICE,
                radius=2.5, color=(255, 250, 210)))

    # 「把世界翻过来」：自战场底部向上抛起的弹幕
    if timer % 120 == 40:
        span = cfg.BATTLE_AREA_WIDTH - 120
        for i in range(9):
            x = 60 + i * span / 8.0
            _add(bullet_manager, create_bullet_angle(
                x, cfg.BATTLE_AREA_HEIGHT + 10, -math.pi / 2, 2.0,
                Bullet.TYPE_KNIFE, radius=2.5, color=(150, 200, 255)))

    # 抗议标语牌：绕自身旋转的双臂刀弹
    if timer % 8 == 0:
        a = timer * 0.05
        for k in range(2):
            _add(bullet_manager, create_bullet_angle(
                boss.x, boss.y, a + k * math.pi, 2.2, Bullet.TYPE_KNIFE,
                radius=2.5, color=(130, 95, 205)))


class ExtraStageTheRift(Stage):
    """Ex 面：裂隙 ~ The Rift（道中Boss Wizardman / 关底Boss Barry）"""

    def __init__(self):
        super().__init__(cfg.EX_STAGE_NUM, cfg.EX_STAGE_NAME, bg_color=(10, 5, 22))
        # 裂隙隧道：紫黑虚空，远处有裂口透光
        self.background = Pseudo3DFloor(
            cfg.EX_STAGE_FLOOR, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT,
            bg_color=self.bg_color, wall_texture_path=cfg.EX_STAGE_WALL,
            horizon_ratio=0.35, tunnel_width=1.6,
            far_opening=32, floor_stretch=3.2, wall_stretch=1.0,
            wall_align_to_floor=True)
        self.background_darkness = 38

        # 本面资源
        self.title_path = cfg.EX_STAGE_TITLE
        self.music_path = cfg.EX_STAGE_MUSIC_START
        self.music_loop_path = cfg.EX_STAGE_MUSIC_LOOP
        self.boss_music_start_path = cfg.EX_STAGE_BOSS_MUSIC_START
        self.boss_music_loop_path = cfg.EX_STAGE_BOSS_MUSIC_LOOP
        # 道中Boss 有专属曲（与关底曲不同，出场时才切）
        self.mid_boss_music_path = cfg.EX_MID_BOSS_MUSIC
        self.music_name = cfg.EX_STAGE_MUSIC_NAME
        self.boss_music_name = cfg.EX_STAGE_BOSS_MUSIC_NAME

        # Ex 面标记：PlayingState 据此禁用装备物品效果 / 掉落，并改走「通关回主菜单」
        self.items_disabled = True
        # 对话立绘照常套用取景补偿（基类默认开）：Wizardman / Barry 用的是与本作其他 Boss
        # 同规格的高清立绘，两位在 settings.DIALOGUE_PORTRAIT_HEAD_RATIO 里都有登记，
        # 所以不再按「像素立绘原样显示」处理（这条限制随换图一起作废）
        # 载入界面标题（基类默认显示「第 N 面」）
        self.loading_title = "Extra Stage"

        # 对话：道中（Wizardman）与关底（Barry）共用同一套对话机制，
        # dialogue_target 决定对话结束后该让谁开打、该不该切 Boss 战音乐
        self.dialogue_target = "mid"
        self.dialogue_keeps_music = False
        self.mid_boss_dialogue_lines = [
            ("自称救世主 Wizardman", "站住，异世界的来客。"),
            ("自称救世主 Wizardman", "我是 Wizardman。"),
            (cfg.PLAYER_DIALOGUE_NAME, "……Wizardman？"),
            ("自称救世主 Wizardman", "名字不重要。重要的是这个名字背后的东西。"),
            ("自称救世主 Wizardman", "Wizardman 不是一个人，而是一份传承。"),
            ("自称救世主 Wizardman", "我见过无数个「你」，都想要这个称号。"),
            (cfg.PLAYER_DIALOGUE_NAME, "我对别人的称号没有兴趣。"),
            ("自称救世主 Wizardman", "话别说太满。"),
            ("自称救世主 Wizardman", "进到这道裂隙里的人，最后都会想要点什么。"),
            ("自称救世主 Wizardman", "先通过我的试炼吧。"),
            ("自称救世主 Wizardman", "三项：竞速、交锋，还有——四子连线。"),
            (cfg.PLAYER_DIALOGUE_NAME, "……最后那项是什么？"),
            ("自称救世主 Wizardman", "棋逢对手的智慧！"),
            ("自称救世主 Wizardman", "来吧，让我看看你是「又一个回声」，还是「唯一」。"),
        ]
        self.mid_boss_dialogue_portraits = {
            cfg.PLAYER_DIALOGUE_NAME: cfg.SELF_SPRITE,
            "自称救世主 Wizardman": cfg.EX_MID_BOSS_WIZARDMAN_SPRITE,
        }
        self.mid_boss_dialogue_portrait_sides = {cfg.PLAYER_DIALOGUE_NAME: "left"}

        # 关底战前对话（Barry：落选的前市长，在裂隙里张罗下一届选举）
        self.dialogue_lines = [
            ("前市长 Barry", "哎哟。"),
            ("前市长 Barry", "楼上的抗议者又在骂我了。"),
            (cfg.PLAYER_DIALOGUE_NAME, "……楼上？"),
            ("前市长 Barry", "这里没有楼上。这才是重点。"),
            ("前市长 Barry", "最荒唐的是什么，你知道吗？"),
            ("前市长 Barry", "我为这个宇宙做了那么多，结果一届市长都没选上。"),
            (cfg.PLAYER_DIALOGUE_NAME, "所以你把裂隙当成了竞选总部。"),
            ("前市长 Barry", "竞选总部、议会、税务局，全都在这里。"),
            ("前市长 Barry", "等下一届 Rift 选举结束，我们的政府就能永远留在这里。"),
            (cfg.PLAYER_DIALOGUE_NAME, "听起来不像是什么好事。"),
            ("前市长 Barry", "你会明白的。"),
            ("前市长 Barry", "……说实话，我自己也不太明白。"),
            ("前市长 Barry", "总之先打一场吧？反正整个宇宙本来就跑在计算机上。"),
            (cfg.PLAYER_DIALOGUE_NAME, "那就来吧。"),
        ]
        self.dialogue_portraits = {
            cfg.PLAYER_DIALOGUE_NAME: cfg.SELF_SPRITE,
            "前市长 Barry": cfg.EX_FINAL_BOSS_BARRY_SPRITE,
        }
        self.dialogue_portrait_sides = {cfg.PLAYER_DIALOGUE_NAME: "left"}

        # 战后对话（Barry 被击破后、通关结算前）
        self.defeat_dialogue_lines = [
            ("前市长 Barry", "……输了。"),
            ("前市长 Barry", "看来我的竞选纲领还得再改改。"),
            (cfg.PLAYER_DIALOGUE_NAME, "你从一开始就没打算赢吧。"),
            ("前市长 Barry", "谁知道呢。"),
            ("前市长 Barry", "反正税还是要收的。"),
            ("前市长 Barry", "五个税级，最高 50%，一分都不能少。"),
            (cfg.PLAYER_DIALOGUE_NAME, "……我该走了。"),
            ("前市长 Barry", "走好。"),
            ("前市长 Barry", "下次选举，记得投票给我。"),
        ]
        self.defeat_dialogue_portraits = {
            cfg.PLAYER_DIALOGUE_NAME: cfg.SELF_SPRITE,
            "前市长 Barry": cfg.EX_FINAL_BOSS_BARRY_SPRITE,
        }
        self.defeat_dialogue_portrait_sides = {cfg.PLAYER_DIALOGUE_NAME: "left"}

    # ------------------------------------------------------------------
    # 波次
    # ------------------------------------------------------------------
    def setup_waves(self):
        """道中（0 ~ 45s）：裂隙生物按时间轴涌入"""
        em = self.enemy_manager
        waves = (
            (0, EnemyWave([
                RiftVerminEnemy(90, -20), RiftVerminEnemy(288, -40),
                RiftVerminEnemy(486, -20)], name="Rift Vermin")),
            (6 * 60, EnemyWave([
                GlobowlEnemy(120, -30), GlobowlEnemy(456, -30)],
                name="Globowl Pair")),
            (12 * 60, EnemyWave([
                RiftVerminEnemy(70, -24), RiftVerminEnemy(180, -50),
                BlobbercystEnemy(288, -40), RiftVerminEnemy(400, -50),
                RiftVerminEnemy(506, -24)], name="Seeping Swarm")),
            (18 * 60, EnemyWave([
                RiftVampireEnemy(120, -40), ScribeCruxEnemy(456, -40)],
                name="Blood and Sigil")),
            (24 * 60, EnemyWave([
                GlobowlEnemy(90, -30), BlobbercystEnemy(288, -50, deploy_y=170),
                GlobowlEnemy(486, -30)], name="Rift Congregation")),
            (30 * 60, EnemyWave([
                RiftVampireEnemy(160, -40), RiftVampireEnemy(416, -40),
                RiftVerminEnemy(288, -60)], name="Vampire Duet")),
            (36 * 60, EnemyWave([
                ScribeCruxEnemy(140, -40), BlobbercystEnemy(288, -50),
                ScribeCruxEnemy(436, -40)], name="Crux Ward")),
            (41 * 60, EnemyWave([
                RiftVerminEnemy(60, -20), RiftVerminEnemy(170, -40),
                RiftVerminEnemy(288, -60), RiftVerminEnemy(406, -40),
                RiftVerminEnemy(516, -20)], name="Last Vermin")),
        )
        for start, wave in waves:
            em.add_timed_wave(start, wave)

    def setup_mid_boss(self):
        """道中Boss：Wizardman（自封的多元宇宙救世主，先对话再开打）"""
        self.mid_boss = Boss(
            "Wizardman", hp=MID_BOSS_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-40,
            size=22, color=(215, 90, 120),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_level=2, non_spell_min_duration=1,
            non_spell_func=_nonspell_wizardman,
            sprite_path=cfg.EX_MID_BOSS_WIZARDMAN_SPRITE,
            sprite_scale=2.4)
        self.mid_boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 118)
        self.mid_boss.score = 16000

    def _begin_mid_boss(self):
        """道中Boss 出场：先入场站定说话，对话结束才开打（覆写基类的直接开打）"""
        self.setup_mid_boss()
        self._ramp_background_speed(BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)
        if self.mid_boss is not None:
            self.mid_boss.hold_combat()
        self._set_dialogue(self.mid_boss_dialogue_lines,
                           self.mid_boss_dialogue_portraits,
                           self.mid_boss_dialogue_portrait_sides,
                           target="mid", keeps_music=True)
        self.phase = "dialogue"

    def _add_post_midboss_waves(self):
        """道中Boss击破后的小怪（清空后进入 Barry 战前对话）"""
        base = self.mid_boss_defeated_at
        plans = (
            (90, [RiftVerminEnemy(120, -24), RiftVerminEnemy(456, -24)],
             "Scattered Vermin"),
            (220, [GlobowlEnemy(288, -40)], "Drifting Owl"),
            (340, [RiftVampireEnemy(150, -36), RiftVerminEnemy(420, -24)],
             "Thin Blood"),
            (460, [BlobbercystEnemy(200, -40), BlobbercystEnemy(376, -40)],
             "Cyst Bloom"),
        )
        for offset, enemies, name in plans:
            wave = EnemyWave(enemies, name=name)
            self.post_waves.append(wave)
            self.enemy_manager.add_timed_wave(base + offset, wave)

    def setup_boss(self):
        """关底Boss：Barry（暂不配符卡，整场以自定义非符弹幕撑起）"""
        self.boss = Boss(
            "Barry", hp=FINAL_BOSS_HP,
            x=cfg.BATTLE_AREA_WIDTH / 2, y=-60,
            size=30, color=(120, 150, 235),
            spell_by_hp_only=True, spell_resistance=0.5,
            non_spell_level=2, non_spell_min_duration=1,
            non_spell_func=_nonspell_barry,
            sprite_path=cfg.EX_FINAL_BOSS_BARRY_SPRITE,
            sprite_scale=2.6)
        self.boss.move_to(cfg.BATTLE_AREA_WIDTH / 2, 120)
        self.boss.score = 60000
        # 符卡表留空：以后补符卡时直接 boss.add_spell_card(...) 即可

    # ------------------------------------------------------------------
    # 对话
    # ------------------------------------------------------------------
    def _set_dialogue(self, lines, portraits, sides, target, keeps_music):
        self.dialogue_lines = lines
        self.dialogue_portraits = portraits
        self.dialogue_portrait_sides = sides
        self.dialogue_target = target
        # 道中对话期间继续播放道中曲：Boss 战音乐留到关底对话结束时再切
        self.dialogue_keeps_music = keeps_music
        self.dialogue_is_defeat = False
        self.dialogue_active = True

    def _start_dialogue(self):
        """道中小怪清空：Barry 登场对话（对话结束切 Boss 战音乐并开打）"""
        self.setup_boss()
        self._ramp_background_speed(FINAL_BOSS_BG_SPEED_MULT, BOSS_BG_RAMP_TIME)
        if self.boss is not None:
            self.boss.hold_combat()
        self._set_dialogue(self.dialogue_lines, self.dialogue_portraits,
                           self.dialogue_portrait_sides,
                           target="final", keeps_music=False)
        self.phase = "dialogue"

    def on_dialogue_end(self):
        """对话结束：道中对话 → Wizardman 开打；关底对话 → Barry 开打"""
        self.dialogue_active = False
        self.dialogue_keeps_music = False
        if self.dialogue_target == "mid":
            if self.mid_boss is not None:
                self.mid_boss.arm_combat(BOSS_COMBAT_DELAY)
            self.phase = "mid_boss"
            return
        if self.boss is None:
            self.setup_boss()
        if self.boss is not None:
            self.boss.arm_combat(BOSS_COMBAT_DELAY)
        self.phase = "boss"
        self._on_boss_combat_start()

    # ------------------------------------------------------------------
    # 关卡推进
    # ------------------------------------------------------------------
    def update(self, dt, bullet_manager, player_x, player_y):
        """与基类同构，只把「道中Boss 先对话」接进时间轴。"""
        if self.background:
            self.background.update(dt)
        self.timer += 1

        if self.phase == "intro":
            self.enemy_manager.update(dt, bullet_manager, player_x, player_y,
                                      stage_time=self.timer)
            if self.timer >= MID_BOSS_APPEAR_TIME:
                self._begin_mid_boss()

        elif self.phase == "dialogue":
            # 对话期间Boss入场（仅移动，不攻击、不显示血条）
            holder = self.mid_boss if self.dialogue_target == "mid" else self.boss
            if holder is not None and holder.alive:
                holder.update(dt, bullet_manager, player_x, player_y)

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

        elif self.phase == "boss":
            if self.boss:
                self.boss.update(dt, bullet_manager, player_x, player_y)
                if not self.boss.alive:
                    # Boss 被击破：先进行战后对话再通关
                    self._start_defeat_dialogue()

        elif self.phase == "defeat_dialogue":
            if self.boss is not None and self.boss.spell_bg is not None:
                self.boss.update(dt, bullet_manager, player_x, player_y)

        elif self.phase == "cleared":
            if self.boss is not None and self.boss.spell_bg is not None:
                self.boss.update(dt, bullet_manager, player_x, player_y)
