# 菜单界面

import os
import math
import random
import pygame
from src.engine import settings as cfg
from src.engine.collision import circle_collision, point_segment_distance
from src.engine.game import GameState
from src.entities.player_spell import PlayerSpellCard
from src.systems.item_system import BOSS_REWARD_POOLS, C_SKILLS
from src.systems.item_effects import aggregate_effects

WITHER_BOSS_NAMES = {"Maxor", "Storm", "Goldor", "Necron", "Kaeman"}

DEATHBOMB_WINDOW_FRAMES = 24


def load_background(path, size):
    """加载背景图并缩放到指定尺寸，失败返回 None"""
    try:
        if os.path.exists(path):
            img = pygame.image.load(path)
            return pygame.transform.smoothscale(img, size)
    except Exception as e:
        print(f"[Background] Failed to load {path}: {e}")
    return None


class MenuState(GameState):
    """主菜单"""
    def __init__(self, game):
        super().__init__(game)
        self.options = ["Start Game", "Practice", "Settings", "Quit"]
        self.selected = 0
        # 背景图
        self.background = load_background(cfg.MENU_BACKGROUND,
                                          (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))

    def enter(self, game):
        self.selected = 0
        self.game.stop_music()

    def update(self, dt):
        # 隐藏调试：同时按住 D + 对应数字，直接跳到该面道中Boss战（满power）
        held = self.game.keys_held
        if held.get(pygame.K_d, False):
            stage_key_map = {
                1: (pygame.K_1, pygame.K_KP1),
                2: (pygame.K_2, pygame.K_KP2),
                3: (pygame.K_3, pygame.K_KP3),
                4: (pygame.K_4, pygame.K_KP4),
            }
            for stage_num, number_keys in stage_key_map.items():
                if any(held.get(key, False) for key in number_keys):
                    self._debug_start_midboss(stage_num)
                    return

        # 隐藏调试：同时按住 S + K + B 直接进入二面（power=300）
        if (held.get(pygame.K_s, False) and held.get(pygame.K_k, False)
                and held.get(pygame.K_b, False)):
            self._debug_start_stage2()
            return
        # 隐藏调试：同时按住 2 + M 直接进入二面关底Boss战前对话（满power）
        if ((held.get(pygame.K_2, False) or held.get(pygame.K_KP2, False))
                and held.get(pygame.K_m, False)):
            self._debug_stage2_boss_dialogue()
            return
        # 隐藏调试：同时按住 S + K + C 直接进入三面（power=300）
        if (held.get(pygame.K_s, False) and held.get(pygame.K_k, False)
                and held.get(pygame.K_c, False)):
            self._debug_start_stage3()
            return
        # 隐藏调试：同时按住 3 + M 直接进入三面关底Boss战前对话（满power）
        if ((held.get(pygame.K_3, False) or held.get(pygame.K_KP3, False))
                and held.get(pygame.K_m, False)):
            self._debug_stage3_boss_dialogue()
            return
        # 隐藏调试：同时按住 S + K + 4 直接进入四面（power=300）
        if (held.get(pygame.K_s, False) and held.get(pygame.K_k, False)
                and (held.get(pygame.K_4, False) or held.get(pygame.K_KP4, False))):
            self._debug_start_stage4()
            return
        # 隐藏调试：同时按住 4 + M 直接进入四面关底Boss战前对话（满power）
        if ((held.get(pygame.K_4, False) or held.get(pygame.K_KP4, False))
                and held.get(pygame.K_m, False)):
            self._debug_stage4_boss_dialogue()
            return
        # 隐藏调试：同时按住 S + K + 5 直接进入五面 BOSS RUSH（power=400）
        if (held.get(pygame.K_s, False) and held.get(pygame.K_k, False)
                and (held.get(pygame.K_5, False) or held.get(pygame.K_KP5, False))):
            self._debug_start_stage5()
            return
        # 隐藏调试：同时按住 5 + M 直接进入五面 Maxor 战前对话（满power）
        if ((held.get(pygame.K_5, False) or held.get(pygame.K_KP5, False))
                and held.get(pygame.K_m, False)):
            self._debug_stage5_maxor_dialogue()
            return
        # 隐藏调试：同时按住 S + K + 6 直接进入六面 Final Approach（power=400）
        if (held.get(pygame.K_s, False) and held.get(pygame.K_k, False)
                and (held.get(pygame.K_6, False) or held.get(pygame.K_KP6, False))):
            self._debug_start_stage6()
            return
        # 隐藏调试：同时按住 6 + M 直接进入六面 Kaeman 战前对话（满power）
        if ((held.get(pygame.K_6, False) or held.get(pygame.K_KP6, False))
                and held.get(pygame.K_m, False)):
            self._debug_stage6_boss_dialogue()
            return

        keys = self.game.keys_just_pressed
        if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
            self.selected = (self.selected - 1) % len(self.options)
        if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
            self.selected = (self.selected + 1) % len(self.options)

        if keys.get(pygame.K_RETURN, False) or keys.get(pygame.K_z, False) or keys.get(pygame.K_SPACE, False):
            self._select()

    def _debug_start_midboss(self, stage_num):
        """隐藏调试：直接进入指定关卡的战斗中Boss战，power 设为满值（400）。"""
        from src.stages import get_stage_class
        stage_cls = get_stage_class(stage_num)
        if stage_cls is None:
            return

        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 400
        self.game.global_data["graze"] = 0

        stage = stage_cls()
        # 不调用 setup_waves：直接跳过道中前半段小怪，只保留道中Boss战与其后的推进。
        stage.setup_mid_boss()
        stage.phase = "mid_boss"
        stage.timer = 0
        self.game.switch_state(PlayingState(self.game, stage))

    def _debug_start_stage2(self):
        """隐藏调试：直接进入二面，power 设为 300"""
        from src.stages.stage2 import Stage2_DragonsNest
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 300
        self.game.global_data["graze"] = 0
        stage = Stage2_DragonsNest()
        stage.setup_waves()
        self.game.switch_state(PlayingState(self.game, stage))

    def _debug_start_stage3(self):
        """隐藏调试：直接进入三面，power 设为 300"""
        from src.stages.stage3 import Stage3_CatacombsF1
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 300
        self.game.global_data["graze"] = 0
        stage = Stage3_CatacombsF1()
        stage.setup_waves()
        self.game.switch_state(PlayingState(self.game, stage))

    def _debug_stage3_boss_dialogue(self):
        """隐藏调试：直接进入三面关底Boss战前对话，power 满（400）"""
        from src.stages.stage3 import Stage3_CatacombsF1
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 400
        self.game.global_data["graze"] = 0
        stage = Stage3_CatacombsF1()
        # 直接进入关底对话：Boss 入场但不攻击、不显示血条，跳过小怪与道中Boss
        stage._start_dialogue()
        self.game.switch_state(PlayingState(self.game, stage, skip_title=True))

    def _debug_start_stage4(self):
        """隐藏调试：直接进入四面，power 设为 300"""
        from src.stages.stage4 import Stage4_Catacombs
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 400
        self.game.global_data["graze"] = 0
        stage = Stage4_Catacombs()
        stage.setup_waves()
        self.game.switch_state(PlayingState(self.game, stage))

    def _debug_stage4_boss_dialogue(self):
        """隐藏调试：直接进入四面关底Boss战前对话，power 满（400）"""
        from src.stages.stage4 import Stage4_Catacombs
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 400
        self.game.global_data["graze"] = 0
        stage = Stage4_Catacombs()
        stage._start_dialogue()
        self.game.switch_state(PlayingState(self.game, stage, skip_title=True))

    def _debug_start_stage5(self):
        """隐藏调试：直接进入五面 BOSS RUSH，power 设为满值（400）。"""
        from src.stages.stage5 import Stage5_WitherLords
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 400
        self.game.global_data["graze"] = 0
        stage = Stage5_WitherLords()
        stage.setup_waves()
        self.game.switch_state(PlayingState(self.game, stage))

    def _debug_stage5_maxor_dialogue(self):
        """隐藏调试：直接进入五面 Maxor 战前对话，power 满（400）。"""
        from src.stages.stage5 import Stage5_WitherLords
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 400
        self.game.global_data["graze"] = 0
        stage = Stage5_WitherLords()
        stage._start_maxor_dialogue()
        self.game.switch_state(PlayingState(self.game, stage, skip_title=True))

    def _debug_start_stage6(self):
        """隐藏调试：直接进入六面最终进军，power 设为满值（400）。"""
        from src.stages.stage6 import Stage6_FinalApproach
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 400
        self.game.global_data["graze"] = 0
        stage = Stage6_FinalApproach()
        stage.setup_waves()
        self.game.switch_state(PlayingState(self.game, stage))

    def _debug_stage6_boss_dialogue(self):
        """隐藏调试：直接进入六面 Kaeman（The Wither King）战前对话，power 满（400）。"""
        from src.stages.stage6 import Stage6_FinalApproach
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 400
        self.game.global_data["graze"] = 0
        stage = Stage6_FinalApproach()
        # 直接进入关底对话：Kaeman 入场但不攻击、不显示血条，跳过进军全流程
        stage._start_final_dialogue()
        self.game.switch_state(PlayingState(self.game, stage, skip_title=True))

    def _debug_stage2_boss_dialogue(self):
        """隐藏调试：直接进入二面关底Boss战前对话，power 满（400）"""
        from src.stages.stage2 import Stage2_DragonsNest
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 400
        self.game.global_data["graze"] = 0
        stage = Stage2_DragonsNest()
        # 直接进入关底对话：Boss 入场但不攻击、不显示血条，跳过小怪与道中Boss
        stage._start_dialogue()
        self.game.switch_state(PlayingState(self.game, stage, skip_title=True))

    def _select(self):
        if self.options[self.selected] == "Start Game":
            # 新游戏：先进仓库出征准备，选择携带物品与金币
            from src.ui.loadout import LoadoutState
            self.game.switch_state(LoadoutState(self.game))
        elif self.options[self.selected] == "Quit":
            self.game.running = False
        elif self.options[self.selected] == "Settings":
            self.game.push_state(SettingsState(self.game))
        elif self.options[self.selected] == "Practice":
            from src.ui.practice import PracticeSelectState
            self.game.push_state(PracticeSelectState(self.game))

    def draw(self, screen):
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((4, 4, 16))

        # 菜单选项（首项定位于离左上角 x560 y380）
        start_x = 560
        start_y = 380
        for i, option in enumerate(self.options):
            color = cfg.COLOR_YELLOW if i == self.selected else cfg.COLOR_WHITE
            text = self.game.font_medium.render(option, True, color)

            x = start_x
            y = start_y + i * 44

            if i == self.selected:
                indicator = "> "
                ind_text = self.game.font_medium.render(indicator, True, cfg.COLOR_YELLOW)
                screen.blit(ind_text, (x - 22, y))
                pulse = math.sin(pygame.time.get_ticks() * 0.004) * 0.3 + 0.7
                glow_color = tuple(int(c * pulse) for c in cfg.COLOR_YELLOW)
                glow = self.game.font_medium.render(option, True, glow_color)
                screen.blit(glow, (x, y))

            screen.blit(text, (x, y))

        # 底部版本
        version_text = self.game.font_small.render("v1.4.2 - Codex CLI Project", True, cfg.COLOR_DARK_GRAY)
        screen.blit(version_text, (10, cfg.SCREEN_HEIGHT - 18))

        # 撤离 / 操作提示（一次性通知）
        notice = getattr(self.game, "notice", None)
        if notice:
            notice_text = self.game.font_small.render(notice, True, cfg.COLOR_GREEN)
            screen.blit(notice_text, ((cfg.SCREEN_WIDTH - notice_text.get_width()) // 2,
                                      cfg.SCREEN_HEIGHT - 64))



class SettingsState(GameState):
    """设置界面：音乐音量调节"""

    def __init__(self, game):
        super().__init__(game)
        self.background = load_background(cfg.MENU_BACKGROUND,
                                          (cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
        self.selected = 0          # 0=音量行，1=返回行
        self.volume_step = 0.1     # 每次按键调节的音量幅度
        self._repeat_timer = 0     # 按住方向键时连续调节的间隔计时

    def enter(self, game):
        self.selected = 0
        self._repeat_timer = 0
        # 进入设置时播放一段背景音乐，方便即时听到音量变化
        self.game.play_music(cfg.STAGE1_MUSIC)

    def exit(self):
        self.game.stop_music()

    def update(self, dt):
        keys = self.game.keys_just_pressed
        if keys.get(pygame.K_ESCAPE, False) or keys.get(pygame.K_x, False):
            self.game.pop_state()
            return

        if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
            self.selected = (self.selected - 1) % 2
        if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
            self.selected = (self.selected + 1) % 2

        if self.selected == 0:
            # 音量行：左/右方向键调节（支持按住连续调节）
            held = self.game.keys_held
            left = held.get(pygame.K_LEFT, False) or held.get(pygame.K_a, False)
            right = held.get(pygame.K_RIGHT, False) or held.get(pygame.K_d, False)
            if left or right:
                self._repeat_timer -= 1
                if self._repeat_timer <= 0:
                    self._change_volume(-self.volume_step if left else self.volume_step)
                    self._repeat_timer = 5
            else:
                self._repeat_timer = 0
        else:
            # 返回行：确认返回主菜单
            if (keys.get(pygame.K_RETURN, False) or keys.get(pygame.K_z, False)
                    or keys.get(pygame.K_SPACE, False)):
                self.game.pop_state()

    def _change_volume(self, delta):
        volume = round(max(0.0, min(1.0, self.game.music_volume + delta)), 2)
        self.game.set_music_volume(volume)

    def draw(self, screen):
        if self.background:
            screen.blit(self.background, (0, 0))
        else:
            screen.fill((4, 4, 16))

        # 标题
        title = self.game.font_large.render("设置", True, cfg.COLOR_YELLOW)
        screen.blit(title, ((cfg.SCREEN_WIDTH - title.get_width()) // 2, 110))

        # 音量行
        volume = self.game.music_volume
        selected = self.selected == 0
        color = cfg.COLOR_YELLOW if selected else cfg.COLOR_WHITE
        label = self.game.font_medium.render("音乐音量", True, color)
        percent = self.game.font_medium.render(f"{int(round(volume * 100))}%", True, color)
        screen.blit(label, (300, 280))
        screen.blit(percent, (640, 280))

        # 音量条
        bar_x, bar_y, bar_w, bar_h = 430, 288, 180, 12
        pygame.draw.rect(screen, cfg.COLOR_DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
        if volume > 0:
            fill_w = max(4, int(bar_w * volume))
            pygame.draw.rect(screen, cfg.COLOR_GREEN if selected else cfg.COLOR_GRAY,
                             (bar_x, bar_y, fill_w, bar_h))
        pygame.draw.rect(screen, color, (bar_x, bar_y, bar_w, bar_h), 1)

        # 操作提示
        hint = self.game.font_small.render("< / > 调节音量    Esc 返回", True, cfg.COLOR_GRAY)
        screen.blit(hint, ((cfg.SCREEN_WIDTH - hint.get_width()) // 2, 330))

        # 返回行
        back_color = cfg.COLOR_YELLOW if self.selected == 1 else cfg.COLOR_WHITE
        back = self.game.font_medium.render("返回", True, back_color)
        back_x = (cfg.SCREEN_WIDTH - back.get_width()) // 2
        if self.selected == 1:
            ind = self.game.font_medium.render("> ", True, cfg.COLOR_YELLOW)
            screen.blit(ind, (back_x - 26, 430))
        screen.blit(back, (back_x, 430))


class PlayingState(GameState):
    """游戏主状态"""
    def __init__(self, game, stage, skip_title=False, practice_info=None):
        super().__init__(game)
        self.stage = stage
        self.skip_title = skip_title
        # 练习模式信息（None 表示正常通关流程）
        self.practice_info = practice_info
        self.practice_done = False
        self.practice_done_timer = 0
        from src.entities.bullet import BulletManager
        from src.entities.player import Player
        from src.ui.hud import HUD
        from src.systems.item_system import (
            ItemDropManager,
            ItemInventory,
            init_default_drop_table,
            init_stage_drop_table,
        )
        from src.systems.skill_system import SkillManager

        self.bullet_manager = BulletManager()
        self.player = Player(cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80)
        self.hud = HUD(game)

        # 战斗区域偏移（绘制时使用）
        self.offset_x = cfg.BATTLE_OFFSET_X
        self.offset_y = cfg.BATTLE_OFFSET_Y

        # 分数与资源（从全局数据继承）
        self.score = self.game.global_data.get("score", 0)
        self.lives = self.game.global_data.get("lives", cfg.PLAYER_START_LIVES)
        self.bombs = self.game.global_data.get("bombs", cfg.PLAYER_START_BOMBS)
        self.power = self.game.global_data.get("power", 0)
        self.graze = self.game.global_data.get("graze", 0)

        # Skyblock 系统
        self.item_manager = ItemDropManager()
        init_default_drop_table(self.item_manager)
        init_stage_drop_table(self.item_manager, self.stage.stage_num)
        self.item_inventory = ItemInventory.from_global_data(self.game.global_data)
        self.equipment_stats = self.item_inventory.get_equipped_stats()
        self.pending_boss_reward_pool = None

        # 物品被动效果聚合（装备在休整期间才会变化，本关内保持不变）
        self.item_effects = aggregate_effects(self.item_inventory, self.stage.stage_num)
        self.c_skill_id = self.item_inventory.get_c_skill_equipped_id()
        self.c_uses = {}
        self.c_skill_message = ""
        self.c_skill_message_timer = 0
        self.bad_health_timer = 0
        self.arack_timer = 0
        self.spider_timer = 0
        self.spirit_bow_timer = 0
        self.end_stone_timer = 0
        self.precursor_timer = 0
        self.lives_lost_this_stage = 0
        self.kill_counter = 0
        self.shadow_damage = 0.0
        self.wither_shields = []
        self.bonzo_balloons = []
        self.fot_roses = []
        self.overflux_orbs = []
        self.summoned_minions = []
        # 判定点缩放（Maxor's Boots）
        self.player.hitbox_radius = cfg.PLAYER_HITBOX_RADIUS * self.item_effects["hitbox_scale"]
        self._apply_stage_start_bonuses()
        self.skill_manager = SkillManager()
        skills_data = self.game.global_data.get("skills", {})
        if skills_data:
            self.skill_manager.from_dict(skills_data)

        # 掉落弹窗
        self.item_popups = []
        self.power_items = []  # 红色 Power 方块掉落物
        self.bonus_items = []  # Boss reward drops (+Bomb / +Life)
        self.homing_shot_skip = False  # 追踪弹射速为正常一半（零替发射）

        # 状态
        self.paused = False
        self.game_over = False
        self.stage_clear = False
        self.clear_timer = 0
        self.dialogue = None  # 对话框（非 None 时显示，玩法继续推进）
        self.boss_music_intro = False  # Boss战开场曲播放中（播完后切循环曲）
        self.stage_music_intro = False  # 道中开场曲播放中（播完后切循环曲）
        self.mid_boss_music_started = False  # 道中Boss音乐是否已切换（出场时只切一次）

        # 曲名横幅（每面开始 / Boss战开始时显示当前音乐名）
        self.music_banner_name = None  # 当前显示的曲名
        self.music_banner_timer = 0    # 曲名横幅剩余显示帧数

        # 关卡标题（面开始时覆盖在战斗界面上，随后淡出消失）
        self.stage_title_image = None   # 当前关卡标题贴图
        self.stage_title_shadow = None  # 关卡标题投影
        self.stage_title_timer = 0      # 关卡标题剩余显示帧数

        # Bomb 效果
        self.bomb_active = False
        self.bomb_timer = 0
        self.player_spell = None
        self.death_window = 0
        # Last Spell 中禁用 Bomb 的提示计时器
        self.bomb_blocked_timer = 0

    def enter(self, game):
        # 练习模式：直接播放 Boss 战音乐，不显示关卡标题
        if self.practice_info:
            self._enter_practice()
            return
        # 道中Boss音乐标记复位（重进本面时重新生效）
        self.mid_boss_music_started = False
        # 播放本面道中曲
        self._play_stage_music()
        # 面开始时显示当前播放的音乐名
        self._show_music_name(self.stage.music_name)
        # 面开始时显示关卡标题（覆盖战斗界面）
        if not self.skip_title:
            self._show_stage_title(self.stage.title_path)
        # 记录当前关卡号
        self.game.global_data["stage"] = self.stage.stage_num

    def on_music_end(self):
        """Boss战开场曲播完后无缝切到循环曲"""
        # 仅在开场曲确实自然播完时切换（stop_music 等触发的假结束事件会被忽略）
        if self.boss_music_intro and not self.game.music_busy():
            self.boss_music_intro = False
            self.game.play_music(self.stage.boss_music_loop_path)
        elif self.stage_music_intro and not self.game.music_busy():
            self.stage_music_intro = False
            self.game.play_music(self.stage.music_loop_path)

    def _play_stage_music(self):
        """播放本面道中曲：配置了 music_loop_path 时先播一遍开场曲，再无缝切到循环曲。"""
        self.stage_music_intro = False
        loop_path = getattr(self.stage, "music_loop_path", None)
        if loop_path:
            self.stage_music_intro = True
            self.game.play_music(self.stage.music_path, loops=0)
        else:
            self.game.play_music(self.stage.music_path)

    def _show_music_name(self, name):
        """显示曲名横幅（每面开始 / Boss战开始时）"""
        self.music_banner_name = name
        self.music_banner_timer = cfg.MUSIC_BANNER_DURATION

    def _draw_music_banner(self, screen):
        """在战斗区右上角绘制当前曲名（淡入淡出）"""
        if not self.music_banner_name or self.music_banner_timer <= 0:
            return
        total = cfg.MUSIC_BANNER_DURATION
        remaining = self.music_banner_timer
        if remaining >= total - 15:
            alpha = int(255 * (total - remaining) / 15)   # 淡入
        elif remaining <= 40:
            alpha = int(255 * remaining / 40)             # 淡出
        else:
            alpha = 255

        text = self.game.font_medium.render(self.music_banner_name, True, cfg.COLOR_WHITE)
        text.set_alpha(alpha)
        right = cfg.BATTLE_OFFSET_X + cfg.BATTLE_AREA_WIDTH - 12  # 战斗区右上角（右对齐）
        y = cfg.BATTLE_OFFSET_Y + 12

        band = pygame.Surface((text.get_width() + 32, text.get_height() + 12), pygame.SRCALPHA)
        band.fill((0, 0, 0, int(alpha * 0.5)))
        screen.blit(band, (right - band.get_width(), y - 6))
        screen.blit(text, (right - text.get_width(), y))

    def _show_stage_title(self, path):
        """面开始时显示关卡标题（覆盖战斗界面，随后淡出消失）"""
        self.stage_title_image = None
        self.stage_title_shadow = None
        self.stage_title_timer = 0
        try:
            if os.path.exists(path):
                img = pygame.image.load(path)
                if (img.get_width() != cfg.BATTLE_AREA_WIDTH
                        or img.get_height() != cfg.BATTLE_AREA_HEIGHT):
                    img = pygame.transform.smoothscale(
                        img, (cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT))
                if img.get_alpha() is not None:
                    img = img.convert_alpha()
                else:
                    img = img.convert()
                self.stage_title_image = img
                if img.get_alpha() is not None:
                    self.stage_title_shadow = self._make_title_shadow(img)
                self.stage_title_timer = cfg.STAGE_TITLE_DURATION
        except Exception as e:
            print(f"[StageTitle] Failed to load {path}: {e}")

    def _make_title_shadow(self, img):
        """根据标题图透明通道生成柔化投影（黑色 + 降采样模糊）"""
        shadow = img.copy()
        shadow.fill((0, 0, 0, 255), special_flags=pygame.BLEND_RGBA_MULT)
        w, h = shadow.get_size()
        small = pygame.transform.smoothscale(
            shadow, (max(1, w // 6), max(1, h // 6)))
        return pygame.transform.smoothscale(small, (w, h))

    def _draw_stage_title(self, screen):
        """在战斗区域绘制关卡标题（带投影，最后 30 帧淡出）"""
        if not self.stage_title_image or self.stage_title_timer <= 0:
            return
        fade_frames = 30
        if self.stage_title_timer <= fade_frames:
            alpha = int(255 * self.stage_title_timer / fade_frames)
        else:
            alpha = 255
        if self.stage_title_shadow:
            self.stage_title_shadow.set_alpha(
                int(cfg.STAGE_TITLE_SHADOW_ALPHA * alpha / 255))
            dx, dy = cfg.STAGE_TITLE_SHADOW_OFFSET
            screen.blit(self.stage_title_shadow,
                        (self.offset_x + dx, self.offset_y + dy))
        self.stage_title_image.set_alpha(alpha)
        screen.blit(self.stage_title_image, (self.offset_x, self.offset_y))

    # ================= 符卡练习模式 =================

    def _enter_practice(self):
        """练习模式进入：直接播放 Boss 战音乐并显示曲名。"""
        self.mid_boss_music_started = True
        self.stage_music_intro = False
        self.boss_music_intro = True
        self.game.play_music(self.stage.boss_music_start_path, loops=0)
        self._show_music_name(self.stage.boss_music_name)

    def _update_practice(self, dt, keys):
        """练习模式更新：单符卡循环 + 击破结算 / 重试 / 下一张 / 返回。"""
        # 击破结算
        if self.practice_done:
            self.practice_done_timer += 1
            if (keys.get(pygame.K_r, False) or keys.get(pygame.K_z, False)
                    or keys.get(pygame.K_SPACE, False)):
                self._practice_restart()
            elif keys.get(pygame.K_n, False):
                self._practice_next_card()
            elif (keys.get(pygame.K_ESCAPE, False)
                  or keys.get(pygame.K_BACKSPACE, False)):
                self._practice_back_to_select()
            return

        # 中途退出
        if (keys.get(pygame.K_ESCAPE, False)
                or keys.get(pygame.K_BACKSPACE, False)):
            self._practice_back_to_select()
            return

        # 玩家输入（机械符等中央演出期间锁定）
        if not getattr(self.stage, "player_input_locked", False):
            self.player.handle_input(self.game.keys, self.game.keys_held,
                                     self.game.keys_just_pressed)
        else:
            self.player.want_bomb = False
            self.player.vx = 0.0
            self.player.vy = 0.0
            self.player.shooting = False

        # 移动速度修正与限制
        self._apply_speed_effects()
        if self.end_stone_timer > 0:
            self.player.vx = 0.0
            self.player.vy = 0.0

        # Bomb（Last Spell 挑战中禁用）
        if (self.player.want_bomb and self.bombs > 0
                and not self.bomb_active and self.player_spell is None):
            if self.stage.boss is not None and self.stage.boss.is_last_spell_active():
                self.bomb_blocked_timer = 50
            else:
                self._use_bomb()
        if self.bomb_blocked_timer > 0:
            self.bomb_blocked_timer -= 1

        # 决死Bomb窗口
        if self.death_window > 0:
            self.death_window -= 1
            if self.death_window <= 0:
                self._player_die()
            return

        # Bomb/自机符卡效果
        if self.player_spell is not None:
            self.player_spell.update(dt)
            if self.player_spell.done:
                self.player_spell = None
                self.bomb_active = False
                self.bomb_timer = 0
                self.player.spell_invincible = False

        # 更新玩家
        self.player.update(dt)
        tp = getattr(self.stage, "player_teleport_target", None)
        if tp is not None:
            self.player.x, self.player.y = tp
            self.stage.player_teleport_target = None
        constrain = getattr(self.stage, "constrain_player", None)
        if constrain is not None:
            self.player.x, self.player.y = constrain(self.player.x, self.player.y)

        # 射击 / 弹幕
        if self.player.can_shoot():
            self._player_shoot()
        self.bullet_manager.update(dt, self.player.x, self.player.y)
        self._update_homing_bullets()
        self._update_c_skills()
        self._update_power_items()
        self._update_bonus_items()

        # 更新练习舞台（转发鼠标/按键供机械符等使用）
        self.stage.mouse_pos = self.game.mouse_pos
        self.stage.mouse_buttons_just_pressed = self.game.mouse_buttons_just_pressed
        self.stage.mouse_buttons_held = self.game.mouse_buttons_held
        self.stage.keys_just_pressed = self.game.keys_just_pressed
        self.stage.keys_held = self.game.keys_held
        self.stage.update(dt, self.bullet_manager, self.player.x, self.player.y)

        # 碰撞检测
        self._check_collisions()

        # 符卡击破：显示结算并清屏
        boss = getattr(self.stage, "boss", None)
        if boss is not None and not boss.alive and not self.practice_done:
            self.practice_done = True
            self.practice_done_timer = 0
            self.bullet_manager.clear_all()
            self.player_spell = None
            self.bomb_active = False
            self.bomb_timer = 0
            self.player.spell_invincible = False
            self.game.stop_music()

        # 曲名横幅递减
        if self.music_banner_timer > 0:
            self.music_banner_timer -= 1

        # 掉落弹窗
        for popup in self.item_popups[:]:
            popup["timer"] += 1
            if popup["timer"] > 180:
                self.item_popups.remove(popup)

    def _practice_restart(self):
        """重试当前符卡：重建练习舞台与自机状态。"""
        from src.entities.bullet import BulletManager
        from src.entities.player import Player
        from src.ui.practice import build_practice_boss, PracticeStage
        entry = self.practice_info["entry"]
        card_index = self.practice_info["card_index"]
        stage, boss = build_practice_boss(entry, card_index)
        self.stage = PracticeStage(stage, boss)

        self.bullet_manager = BulletManager()
        self.player = Player(cfg.BATTLE_AREA_WIDTH / 2,
                             cfg.BATTLE_AREA_HEIGHT - 80)
        self.player.hitbox_radius = (cfg.PLAYER_HITBOX_RADIUS
                                     * self.item_effects["hitbox_scale"])

        # 练习模式固定满火力 3 残机 3 雷
        self.score = 0
        self.lives = cfg.PLAYER_START_LIVES
        self.bombs = cfg.PLAYER_START_BOMBS
        self.power = 400
        self.graze = 0

        # 重置状态
        self.practice_done = False
        self.practice_done_timer = 0
        self.bomb_active = False
        self.bomb_timer = 0
        self.player_spell = None
        self.player.spell_invincible = False
        self.death_window = 0
        self.bomb_blocked_timer = 0
        self.item_popups.clear()
        self.power_items.clear()
        self.bonus_items.clear()
        self.homing_shot_skip = False
        self.dialogue = None
        self.c_skill_message = ""
        self.c_skill_message_timer = 0

        # 重播 Boss 战音乐
        self.game.stop_music()
        pygame.event.clear(self.game.music_end_event)
        self.boss_music_intro = True
        self.stage_music_intro = False
        self.game.play_music(self.stage.boss_music_start_path, loops=0)
        self._show_music_name(self.stage.boss_music_name)

    def _practice_next_card(self):
        """切到下一张符卡（同一 Boss，最后一张后回到第一张）。"""
        entry = self.practice_info["entry"]
        n = len(entry["cards"])
        self.practice_info["card_index"] = (
            self.practice_info["card_index"] + 1) % n
        self.practice_info["card_name"] = (
            entry["cards"][self.practice_info["card_index"]]["name"])
        self._practice_restart()

    def _practice_back_to_select(self):
        """返回符卡练习选择界面。"""
        from src.ui.practice import PracticeSelectState
        self.game.switch_state(PracticeSelectState(self.game))

    def _draw_practice_overlay(self, screen):
        """练习模式 HUD 提示与符卡击破结算。"""
        # 战斗中提示退出方式（战斗区左上角）
        if not self.practice_done:
            hint = self.game.font_small.render(
                "符卡练习  Esc 返回选择", True, cfg.COLOR_GRAY)
            screen.blit(hint, (self.offset_x + 10,
                               self.offset_y + cfg.BATTLE_AREA_HEIGHT - 20))
            return
        # 击破结算
        overlay = pygame.Surface((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT),
                                 pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))
        title = self.game.font_large.render("符卡击破！", True, cfg.COLOR_GREEN)
        card_name = self.practice_info["card_name"]
        last_tag = "（Last Spell）" if self.practice_info.get("last") else ""
        card = self.game.font_medium.render(
            card_name + last_tag, True, cfg.COLOR_YELLOW)
        screen.blit(title, ((cfg.SCREEN_WIDTH - title.get_width()) // 2, 240))
        screen.blit(card, ((cfg.SCREEN_WIDTH - card.get_width()) // 2, 320))
        hint = self.game.font_small.render(
            "[R] 重试    [N] 下一张    [Esc] 返回选择", True, cfg.COLOR_WHITE)
        screen.blit(hint, ((cfg.SCREEN_WIDTH - hint.get_width()) // 2, 384))

    def exit(self):
        # 练习模式不写回存档数据，避免污染主线进度
        if self.practice_info:
            self.game.stop_music()
            return
        # 保存状态到全局数据
        self.game.global_data["score"] = self.score
        self.game.global_data["lives"] = self.lives
        self.game.global_data["bombs"] = self.bombs
        self.game.global_data["power"] = self.power
        self.game.global_data["graze"] = self.graze
        self.game.global_data["skills"] = self.skill_manager.to_dict()
        self._save_item_inventory()
        self.game.stop_music()

    def update(self, dt):
        keys = self.game.keys_just_pressed
        # 练习模式：单符卡循环与击破/重试/返回结算
        if self.practice_info:
            self._update_practice(dt, keys)
            return
        dialogue_was_active = self.dialogue is not None

        # Stage3 debug skip: G during Bonzo pre-battle dialogue -> revived phase 2.
        if (self.dialogue is not None
                and not getattr(self.stage, "dialogue_is_defeat", False)
                and keys.get(pygame.K_g, False)
                and getattr(self.stage, "skip_to_revival", None) is not None
                and self.stage.skip_to_revival()):
            self.dialogue = None
            self.game.stop_music()
            pygame.event.clear(self.game.music_end_event)
            self.boss_music_intro = True
            self.stage_music_intro = False
            self.game.play_music(self.stage.boss_music_start_path, loops=0)
            self._show_music_name(self.stage.boss_music_name)

        # Stage4 debug skip: G during Sadan's pre-battle dialogue -> Precursors' Return.
        if (self.dialogue is not None
                and not getattr(self.stage, "dialogue_is_defeat", False)
                and keys.get(pygame.K_g, False)
                and getattr(self.stage, "skip_to_precursors_return", None) is not None
                and self.stage.skip_to_precursors_return()):
            self.dialogue = None
            self.game.stop_music()
            pygame.event.clear(self.game.music_end_event)
            self.boss_music_intro = True
            self.stage_music_intro = False
            self.game.play_music(self.stage.boss_music_start_path, loops=0)
            self._show_music_name(self.stage.boss_music_name)

        # Stage5 debug skip: 1 -> Professor; 2/3/4/5/6 -> spell cards.
        stage5_skip_done = False
        if (self.dialogue is not None
                and not getattr(self.stage, "dialogue_is_defeat", False)
                and getattr(self.stage, "skip_to_opening_boss", None) is not None):
            if keys.get(pygame.K_1, False) and self.stage.skip_to_opening_boss("professor"):
                stage5_skip_done = True
        if not stage5_skip_done and (self.dialogue is not None
                and not getattr(self.stage, "dialogue_is_defeat", False)
                and getattr(self.stage, "skip_to_spell_card", None) is not None):
            for key, boss_id, spell_idx in ((pygame.K_2, "storm", 0),
                                            (pygame.K_3, "goldor", 0),
                                            (pygame.K_4, "goldor", 1),
                                            (pygame.K_5, "necron", 0),
                                            (pygame.K_6, "necron", 1)):
                if keys.get(key, False) and self.stage.skip_to_spell_card(boss_id, spell_idx):
                    stage5_skip_done = True
                    break
        if stage5_skip_done:
            self.dialogue = None
            self.game.stop_music()
            pygame.event.clear(self.game.music_end_event)
            self.boss_music_intro = True
            self.stage_music_intro = False
            self.game.play_music(self.stage.boss_music_start_path, loops=0)
            self._show_music_name(self.stage.boss_music_name)

        # Stage6 debug skip: 1~6 during Kaeman pre-battle dialogue -> spell cards 1~6.
        stage6_skip_done = False
        if (self.dialogue is not None
                and not getattr(self.stage, "dialogue_is_defeat", False)
                and getattr(self.stage, "skip_to_kaeman_spell", None) is not None):
            for key, idx in ((pygame.K_1, 1), (pygame.K_2, 2), (pygame.K_3, 3),
                             (pygame.K_4, 4), (pygame.K_5, 5), (pygame.K_6, 6)):
                if keys.get(key, False) and self.stage.skip_to_kaeman_spell(idx):
                    stage6_skip_done = True
                    break
        if stage6_skip_done:
            self.dialogue = None
            self.game.stop_music()
            pygame.event.clear(self.game.music_end_event)
            self.boss_music_intro = True
            self.stage_music_intro = False
            self.game.play_music(self.stage.boss_music_start_path, loops=0)
            self._show_music_name(self.stage.boss_music_name)

        # Stage4 debug skip: H during Sadan's pre-battle dialogue -> Bridge Between Worlds.
        if (self.dialogue is not None
                and not getattr(self.stage, "dialogue_is_defeat", False)
                and keys.get(pygame.K_h, False)
                and getattr(self.stage, "skip_to_bridge_between_worlds", None) is not None
                and self.stage.skip_to_bridge_between_worlds()):
            self.dialogue = None
            self.game.stop_music()
            pygame.event.clear(self.game.music_end_event)
            self.boss_music_intro = True
            self.stage_music_intro = False
            self.game.play_music(self.stage.boss_music_start_path, loops=0)
            self._show_music_name(self.stage.boss_music_name)
        # 对话：不冻结玩法，弹幕与玩家的运动/攻击继续推进
        if self.dialogue:
            self.dialogue.update(dt)
            if self.dialogue.finished:
                self.dialogue = None
                if getattr(self.stage, "dialogue_is_defeat", False):
                    # 战后对话结束：不重新开战，直接进入通关结算
                    self.stage.on_defeat_dialogue_end()
                else:
                    # 对话结束：停止道中曲，先播放一遍Boss战开场曲，再让Boss进场
                    self.game.stop_music()
                    # stop_music 也会触发一次音乐结束事件（pygame 行为），
                    # 若不清理，下一帧会误判开场曲播完而立即切到循环曲
                    pygame.event.clear(self.game.music_end_event)
                    self.boss_music_intro = True
                    self.stage_music_intro = False
                    self.game.play_music(self.stage.boss_music_start_path, loops=0)
                    # Boss战开始：显示Boss战音乐名
                    self._show_music_name(self.stage.boss_music_name)
                    self.stage.on_dialogue_end()

        # 暂停（对话期间 ESC 用于跳过对话，不触发暂停；终端破解时 ESC 用于退出破解）
        if (not dialogue_was_active
                and not getattr(self.stage, "player_input_locked", False)
                and keys.get(pygame.K_ESCAPE, False)):
            self.paused = not self.paused
            # 暂停时同步暂停/恢复背景音乐
            if self.game.audio_ok:
                try:
                    if self.paused:
                        pygame.mixer.music.pause()
                    else:
                        pygame.mixer.music.unpause()
                except Exception:
                    pass
        if self.paused:
            return

        # 曲名横幅剩余时间递减
        if self.music_banner_timer > 0:
            self.music_banner_timer -= 1

        # 关卡标题剩余时间递减
        if self.stage_title_timer > 0:
            self.stage_title_timer -= 1

        # 游戏结束 处理
        if self.game_over:
            if keys.get(pygame.K_r, False):
                self._restart()
            elif keys.get(pygame.K_ESCAPE, False):
                self.game.switch_state(MenuState(self.game))
            return



        # P key: simulate clearing the whole stage and open the boss reward screen.
        if (keys.get(pygame.K_p, False)
                and self.pending_boss_reward_pool is None
                and self.stage.stage_num in BOSS_REWARD_POOLS):
            self._simulate_full_clear()
            return

        # 输入（终端破解 / 中央演出期间锁定，只保留结算与按键提示）
        if not getattr(self.stage, "player_input_locked", False):
            self.player.handle_input(self.game.keys, self.game.keys_held,
                                     self.game.keys_just_pressed)
        else:
            self.player.want_bomb = False
            self.player.vx = 0.0
            self.player.vy = 0.0
            self.player.shooting = False

        # C 技能（按 C 释放装备的 C 技能物品）
        if (not getattr(self.stage, "player_input_locked", False)
                and self.death_window <= 0 and not self.game_over
                and keys.get(pygame.K_c, False)):
            self._use_c_skill()

        # 移动速度修正（装备效果：Heavy Armor 减速 / Maxor's Boots 加速等）
        self._apply_speed_effects()
        # End Stone Sword：C 技能期间无法移动（仍可射击）
        if self.end_stone_timer > 0:
            self.player.vx = 0.0
            self.player.vy = 0.0

        # Bomb（Last Spell 挑战中禁用）；中弹后短暂窗口内触发决死Bomb。
        if self.death_window > 0:
            if self.player.want_bomb and self.bombs > 0:
                self._use_bomb(deathbomb=True)
        elif (self.player.want_bomb and self.bombs > 0
                and not self.bomb_active and self.player_spell is None):
            if self.stage.boss is not None and self.stage.boss.is_last_spell_active():
                self.bomb_blocked_timer = 50
            else:
                self._use_bomb()
        if self.bomb_blocked_timer > 0:
            self.bomb_blocked_timer -= 1

        # 决死Bomb窗口：类似子弹时间，冻结弹幕与动作，只保留Bomb输入和倒计时。
        if self.death_window > 0:
            self.death_window -= 1
            if self.death_window <= 0:
                self._player_die()
            return

        # Bomb/自机符卡效果
        if self.player_spell is not None:
            self.player_spell.update(dt)
            if self.player_spell.done:
                self.player_spell = None
                self.bomb_active = False
                self.bomb_timer = 0
                self.player.spell_invincible = False

        # 更新玩家
        self.player.update(dt)

        # 符卡/关卡对自机的直接操控：传送 + 走廊约束
        tp = getattr(self.stage, "player_teleport_target", None)
        if tp is not None:
            self.player.x, self.player.y = tp
            self.stage.player_teleport_target = None
        constrain = getattr(self.stage, "constrain_player", None)
        if constrain is not None:
            self.player.x, self.player.y = constrain(self.player.x, self.player.y)

        # 射击
        if (not getattr(self.stage, "player_input_locked", False)
                and self.player.can_shoot()):
            self._player_shoot()

        # 更新子弹
        self.bullet_manager.update(dt, self.player.x, self.player.y)

        # 追踪弹自动转向
        self._update_homing_bullets()

        # C 技能实体与计时器更新
        self._update_c_skills()

        # 掉落物下落与拾取
        self._update_power_items()
        self._update_bonus_items()

        # 更新关卡（先转发鼠标/按键，供终端破解 GUI 使用）
        self.stage.mouse_pos = self.game.mouse_pos
        self.stage.mouse_buttons_just_pressed = self.game.mouse_buttons_just_pressed
        self.stage.mouse_buttons_held = self.game.mouse_buttons_held
        self.stage.keys_just_pressed = self.game.keys_just_pressed
        self.stage.keys_held = self.game.keys_held
        self.stage.update(dt, self.bullet_manager, self.player.x, self.player.y)

        # 为 Sadan 兵马俑（兵符小怪）挂接掉落回调（新 Boss 实例只挂一次）
        cur_boss = self.stage.boss
        if cur_boss is not None and getattr(cur_boss, "terracotta_drop_callback", None) is None:
            cur_boss.terracotta_drop_callback = self._roll_terracotta_drops

        # 道中Boss出场：切换到该面配置的道中Boss音乐（与当前曲相同则不重启，避免重头播放）
        if self.stage.phase == "mid_boss" and not self.mid_boss_music_started:
            self.mid_boss_music_started = True
            mid_music = getattr(self.stage, "mid_boss_music_path", None)
            if mid_music and mid_music != self.game.current_music_path:
                self.game.play_music(mid_music)

        # 触发对话
        if self.stage.dialogue_active and self.dialogue is None:
            from src.ui.dialogue import DialogueBox
            self.dialogue = DialogueBox(self.game, self.stage.dialogue_lines,
                                        portraits=self.stage.dialogue_portraits,
                                        portrait_sides=getattr(self.stage, "dialogue_portrait_sides", {}),
                                        portrait_scales=getattr(self.stage, "dialogue_portrait_scales", {}),
                                        portrait_offsets=getattr(self.stage, "dialogue_portrait_offsets", {}))

        # 碰撞检测
        self._check_collisions()

        # 关底 Boss 可能经由 Last Spell 超时结束 / Miss 强退等非伤害路径死亡，
        # 这些路径不会调用 _reward_enemy_kill，需要在这里补登记 4 选 1 奖励。
        self._register_boss_reward()

        # 通关检测：保存数据并切入关卡间休整界面
        if self.stage.is_cleared() and not self.stage_clear:
            self.stage_clear = True
            self.clear_timer = 0
            self.game.stop_music()   # Boss已击破：停止Boss战音乐
            # 保存全部数据到全局
            self.game.global_data["score"] = self.score
            self.game.global_data["lives"] = self.lives
            self.game.global_data["bombs"] = self.bombs
            self.game.global_data["power"] = self.power
            self.game.global_data["graze"] = self.graze
            self.game.global_data["skills"] = self.skill_manager.to_dict()
            # Necromancer Lord Leggings：关卡结束未失残机 -> +1残机 +1BOMB
            eff = self.item_effects
            if self.lives_lost_this_stage <= 0 and (eff["end_no_hit_lives"] or eff["end_no_hit_bombs"]):
                self.lives = min(cfg.PLAYER_MAX_LIVES, self.lives + int(eff["end_no_hit_lives"]))
                self.bombs = min(cfg.PLAYER_MAX_BOMBS, self.bombs + int(eff["end_no_hit_bombs"]))
                self.game.global_data["lives"] = self.lives
                self.game.global_data["bombs"] = self.bombs
            # Tarantula Helmet：关卡结束时若失去残机>1，获得1BOMB
            if self.lives_lost_this_stage > 1 and eff["end_lost_over1_bombs"]:
                self.bombs = min(cfg.PLAYER_MAX_BOMBS, self.bombs + int(eff["end_lost_over1_bombs"]))
                self.game.global_data["bombs"] = self.bombs
            self._save_item_inventory()
            if self.pending_boss_reward_pool:
                # 关底 Boss 已击破：先进入 4 选 1 奖励，再进入休整
                from src.ui.boss_reward import BossRewardState
                self.game.switch_state(BossRewardState(
                    self.game, self.stage.stage_num, self.pending_boss_reward_pool))
            else:
                from src.ui.intermission import IntermissionState
                self.game.switch_state(IntermissionState(self.game, self.stage.stage_num))
            return

        # 更新掉落弹窗
        for popup in self.item_popups[:]:
            popup["timer"] += 1
            if popup["timer"] > 180:
                self.item_popups.remove(popup)

    def _player_shoot(self):
        """玩家射击：按 power 升级弹幕形态（单线->两线->三线）+ 追踪弹

        装备效果影响：散射夹角（Terminator）、固定/追踪弹道数（Loving）、
        追踪领域（Spirit Bow）、追踪/非追踪弹伤害加成。
        """
        from src.entities import bullet as bm
        power_level = self.power // 100  # 0-4
        eff = self.item_effects
        spirit_active = self.spirit_bow_timer > 0

        # 主射击：单线 -> 两线 -> 三线（Loving 减少1条固定弹）
        px = self.player.x
        py = self.player.y - 8
        lines = max(1, min(3, power_level + 1 + int(eff["fixed_bullet_add"])))
        # 侧翼弹道向外倾斜（Terminator 修改夹角）
        if eff["terminator"]:
            per_side_deg = 4.5 if not self.player.focused else 0.5
        else:
            per_side_deg = 2.25
        tilt_vx = math.tan(math.radians(per_side_deg)) * 12.0
        tilt_vy = -11.96
        if lines >= 3:
            # 三线：左倾、直射、右倾
            b = bm.create_player_bullet(px - 10, py, -tilt_vx, tilt_vy)
            b.damage = self._bullet_damage(homing=spirit_active)
            b.homing = spirit_active
            self.bullet_manager.add_player_bullet(b)
            b = bm.create_player_bullet(px, py)
            b.damage = self._bullet_damage(homing=spirit_active)
            b.homing = spirit_active
            self.bullet_manager.add_player_bullet(b)
            b = bm.create_player_bullet(px + 10, py, tilt_vx, tilt_vy)
            b.damage = self._bullet_damage(homing=spirit_active)
            b.homing = spirit_active
            self.bullet_manager.add_player_bullet(b)
        elif lines == 2:
            # 两线：左右向外倾斜
            b = bm.create_player_bullet(px - 10, py, -tilt_vx, tilt_vy)
            b.damage = self._bullet_damage(homing=spirit_active)
            b.homing = spirit_active
            self.bullet_manager.add_player_bullet(b)
            b = bm.create_player_bullet(px + 10, py, tilt_vx, tilt_vy)
            b.damage = self._bullet_damage(homing=spirit_active)
            b.homing = spirit_active
            self.bullet_manager.add_player_bullet(b)
        else:
            # 单线：中间一条
            b = bm.create_player_bullet(px, py)
            b.damage = self._bullet_damage(homing=spirit_active)
            b.homing = spirit_active
            self.bullet_manager.add_player_bullet(b)

        # 追踪弹：power>=15 开始产生，射速为正常一半（Loving 增加1条追踪弹）；
        # 伤害随 power 从正常 1/3 提升到 2/3；power 满（400）时射速恢复正常（每帧发射）
        track_count = 1 + int(eff["tracking_bullet_add"])
        if self.power >= 15:
            full_power = self.power >= self.player.max_power
            if full_power or not self.homing_shot_skip:
                base = self._bullet_damage(homing=True)
                ratio = 1 / 3 + (1 / 3) * (self.power - 15) / (self.player.max_power - 15)
                offsets = (-4, 4) if track_count >= 2 else (0,)
                for off in offsets:
                    hb = bm.create_player_bullet(px + off, py - 4, homing=True)
                    hb.damage = round(base * ratio, 1)
                    self.bullet_manager.add_player_bullet(hb)
            if not full_power:
                self.homing_shot_skip = not self.homing_shot_skip

    def _bullet_damage(self, homing):
        """单发子弹伤害（含追踪/非追踪弹伤害加成）。"""
        base = self._weapon_damage()
        eff = self.item_effects
        if homing:
            mult = 1.0 + eff["tracking_damage_pct"] / 100.0
            if not self.player.focused:
                mult += eff["tracking_high_speed_damage_pct"] / 100.0
        else:
            mult = 1.0 + eff["non_tracking_damage_pct"] / 100.0
        return base * mult

    def _update_homing_bullets(self):
        """追踪弹自动瞄准最近的敌人"""
        enemies = self.stage.get_active_enemies()
        if not enemies:
            return
        for pb in self.bullet_manager.player_bullets:
            if not pb.homing:
                continue
            target = min(enemies, key=lambda e: (e.x - pb.x) ** 2 + (e.y - pb.y) ** 2)
            dx = target.x - pb.x
            dy = target.y - pb.y
            dist = math.hypot(dx, dy)
            if dist < 1:
                continue
            speed = math.hypot(pb.vx, pb.vy)
            if speed < 0.01:
                speed = cfg.BULLET_PLAYER_SPEED
            # 按角度转向，转向时保持速度恒定，避免向下追踪时减速
            desired_angle = math.atan2(dy, dx)
            current_angle = math.atan2(pb.vy, pb.vx)
            diff = (desired_angle - current_angle + math.pi) % (2 * math.pi) - math.pi
            max_turn = 0.15
            if abs(diff) <= max_turn:
                new_angle = desired_angle
            else:
                new_angle = current_angle + math.copysign(max_turn, diff)
            pb.vx = math.cos(new_angle) * speed
            pb.vy = math.sin(new_angle) * speed
            pb.angle = new_angle

    def _spawn_power_drops(self, enemy):
        """击败敌人掉落红色 Power 方块（power 已满时不掉落）"""
        if self.power >= self.player.max_power:
            return
        from src.entities.pickup import PowerPickup
        from src.entities.boss import Boss
        count = 10 if isinstance(enemy, Boss) else 2
        for _ in range(count):
            item = PowerPickup(
                enemy.x + random.uniform(-14, 14),
                enemy.y,
            )
            self.power_items.append(item)

    def _update_power_items(self):
        """红色 Power 方块下落与拾取"""
        # power 已满：清除场上所有 Power 方块
        if self.power >= self.player.max_power:
            if self.power_items:
                self.power_items.clear()
            return
        # 顶部25%区域 + 低速：吸收全屏 power 方块（每个方块 power 减半）
        suction_active = (
            self.player.focused
            and self.player.y <= cfg.BATTLE_AREA_HEIGHT * 0.25
        )
        # 任意位置吸收耗时相同：0.2 秒（60fps 下 12 帧）
        suck_frames = int(cfg.FPS * 0.2)
        for item in self.power_items[:]:
            if suction_active:
                item.start_suck(suck_frames)
                item.suck_toward(self.player.x, self.player.y)
            else:
                item.update(0)
                item.end_suck()
            if not item.alive:
                self.power_items.remove(item)
                continue
            if item.sucking:
                continue  # 吸收中：未满 0.2s 不提前拾取
            dist_sq = (item.x - self.player.x) ** 2 + (item.y - self.player.y) ** 2
            if dist_sq < item.PICKUP_RADIUS ** 2:
                item.alive = False
                self.power_items.remove(item)
                gain = item.value // 2 if suction_active else item.value
                self.power = min(self.player.max_power, self.power + gain)
                self.game.global_data["power"] = self.power

    def _spawn_bonus_drops(self, enemy):
        """Spawn boss reward drops (+Bomb / +Life) configured on this enemy."""
        bonus_drops = getattr(enemy, "bonus_drops", None)
        if not bonus_drops:
            return
        from src.entities.pickup import (
            DROP_OVERFLUX_POWER_ORB,
            DROP_REVIVE_STONE,
            OverfluxPowerOrbPickup,
            ReviveStonePickup,
        )
        for drop_type in bonus_drops:
            x = enemy.x + random.uniform(-10, 10)
            y = enemy.y
            if drop_type == DROP_OVERFLUX_POWER_ORB:
                item = OverfluxPowerOrbPickup(x, y)
            elif drop_type == DROP_REVIVE_STONE:
                item = ReviveStonePickup(x, y)
            else:
                continue
            self.bonus_items.append(item)

    def _update_bonus_items(self):
        """Update boss reward pickups. They are not cleared at max power."""
        suction_active = (
            self.player.focused
            and self.player.y <= cfg.BATTLE_AREA_HEIGHT * 0.25
        )
        suck_frames = int(cfg.FPS * 0.2)
        for item in self.bonus_items[:]:
            if suction_active:
                item.start_suck(suck_frames)
                item.suck_toward(self.player.x, self.player.y)
            else:
                item.update(0)
                item.end_suck()
            if not item.alive:
                self.bonus_items.remove(item)
                continue
            if item.sucking:
                continue
            dist_sq = (item.x - self.player.x) ** 2 + (item.y - self.player.y) ** 2
            if dist_sq < item.PICKUP_RADIUS ** 2:
                item.alive = False
                self.bonus_items.remove(item)
                self._collect_bonus_item(item)

    def _collect_bonus_item(self, item):
        from src.entities.pickup import OverfluxPowerOrbPickup, ReviveStonePickup
        if isinstance(item, ReviveStonePickup):
            self.lives = min(cfg.PLAYER_MAX_LIVES, self.lives + 1)
            self.game.global_data["lives"] = self.lives
        elif isinstance(item, OverfluxPowerOrbPickup):
            self.bombs = min(cfg.PLAYER_MAX_BOMBS, self.bombs + 1)
            self.game.global_data["bombs"] = self.bombs

    def _save_item_inventory(self):
        """把背包、装备、金币写回全局数据，供跨关和休整界面读取。"""
        self.item_inventory.save_to_global_data(self.game.global_data)
        self.equipment_stats = self.item_inventory.get_equipped_stats()

    def _gain_item(self, item):
        """将掉落物品计入背包；SkyBlock Coin 直接转换为金币（+1M，受Coin掉落加成）。"""
        if item.id == "skyblock_coin":
            base = 1000000
            amount = int(base * (1.0 + self.item_effects["coin_drop_pct"] / 100.0))
            self.item_inventory.add_coins(amount)
        else:
            self.item_inventory.add_item(item.id)
        self._save_item_inventory()

    def _weapon_damage(self):
        """当前玩家弹幕基础伤害（含伤害%加算与触发性加成）。"""
        eff = self.item_effects
        pct = eff["damage_pct"] + self.shadow_damage
        if self.bad_health_timer > 0:
            pct += 200.0
        if self.arack_timer > 0:
            pct += eff["arack_pct"]
        return cfg.BULLET_PLAYER_DAMAGE * (1.0 + pct / 100.0)

    def _reward_enemy_kill(self, enemy):
        """敌人被击破后的奖励结算（分数/技能经验/掉落/击杀计数）"""
        if self.practice_info:
            return
        from src.entities.boss import Boss
        self.score += enemy.score
        self.skill_manager.add_xp("COMBAT", enemy.score // 10)
        eff = self.item_effects
        is_boss = isinstance(enemy, Boss)

        # 击杀计数与效果（Maddox Batphone / Baby Yeti Pet / Shadow Assassin / Lapis）
        self.kill_counter += 1
        if eff["kill50_bombs"] and self.kill_counter % 50 == 0:
            self.bombs = min(cfg.PLAYER_MAX_BOMBS, self.bombs + 1)
            self.game.global_data["bombs"] = self.bombs
        if eff["kill50_lives"] and self.kill_counter % 50 == 0:
            self.lives = min(cfg.PLAYER_MAX_LIVES, self.lives + 1)
            self.game.global_data["lives"] = self.lives
        if is_boss:
            self.shadow_damage += eff["kill_boss_damage_pct"]
            if eff["kill_boss_coins"]:
                self.item_inventory.add_coins(int(eff["kill_boss_coins"]))
        else:
            self.shadow_damage += eff["kill_small_damage_pct"]
            if eff["kill_small_coins"]:
                self.item_inventory.add_coins(int(eff["kill_small_coins"]))

        chance_mult = eff["drop_rate_mult"]
        epic_mult = eff["epic_drop_rate_mult"]
        dropped_ids = set()
        drops = []
        for key in self._enemy_drop_keys(enemy):
            for item in self.item_manager.roll_drops(key, chance_mult, epic_mult):
                if item.id not in dropped_ids:
                    dropped_ids.add(item.id)
                    drops.append(item)
        if is_boss:
            # 关底最终 Boss 被真正击破时登记 3 选 1 奖励池（防复活/重复触发；
            # 五面 Boss Rush 只有 Necron 计入，避免中途弹出奖励/误掷最终掉落）
            if (enemy is self.stage.boss and self.pending_boss_reward_pool is None
                    and self.stage.stage_num in BOSS_REWARD_POOLS
                    and self._is_final_stage_boss(enemy)):
                self.pending_boss_reward_pool = BOSS_REWARD_POOLS[self.stage.stage_num]
            for item in self.item_manager.roll_drops("Boss", chance_mult, epic_mult):
                if item.id not in dropped_ids:
                    dropped_ids.add(item.id)
                    drops.append(item)
        for item in drops:
            self.item_popups.append({"item": item, "timer": 0})
            self._gain_item(item)
        self._spawn_power_drops(enemy)
        self._spawn_bonus_drops(enemy)

    def _is_final_stage_boss(self, boss):
        """该 Boss 是否为关底最终 Boss（只有它被击破才发放三选一奖励）。

        五面是连续 Boss Rush：每个 Boss 都会短暂成为 stage.boss，
        只有最后一个 Necron 计入；其余关卡 stage.boss 即最终 Boss。
        """
        stage = self.stage
        bid = getattr(stage, "current_boss_id", None)
        if stage.stage_num == 5 and bid:
            return bid == "necron"
        return boss is stage.boss

    def _register_boss_reward(self):
        """兜底登记关底 Boss 的 4 选 1 奖励。

        伤害击杀时 _reward_enemy_kill 已经登记（pending_boss_reward_pool 非空），
        这里只处理 Last Spell 超时 / Miss 强退等未经过 _reward_enemy_kill 的死亡路径，
        并顺带补发该 Boss 专属掉落表与 Boss 通用掉落的掉落。
        """
        if self.practice_info:
            return
        if self.pending_boss_reward_pool is not None:
            return
        boss = getattr(self.stage, "boss", None)
        if boss is None or boss.alive:
            return
        if not self._is_final_stage_boss(boss):
            return
        stage_num = self.stage.stage_num
        if stage_num not in BOSS_REWARD_POOLS:
            return
        self.pending_boss_reward_pool = BOSS_REWARD_POOLS[stage_num]
        granted = set()
        chance_mult = self.item_effects["drop_rate_mult"]
        epic_mult = self.item_effects["epic_drop_rate_mult"]
        for key in (f"stage{stage_num}_final_boss", "Boss"):
            for item in self.item_manager.roll_drops(key, chance_mult, epic_mult):
                if item.id in granted:
                    continue
                granted.add(item.id)
                self.item_popups.append({"item": item, "timer": 0})
                self._gain_item(item)

    def _simulate_full_clear(self):
        """P-key shortcut: simulate killing every enemy in this stage.

        Each enemy rolls its own drop table(s) through _enemy_drop_keys, exactly
        like a real kill. bonus_drops configured on bosses/mid-bosses are
        converted directly into +Bomb / +Life. Then the stage's 3-choice boss
        reward pool is registered and the player is taken straight to the
        reward screen.
        """
        stage = self.stage
        stage_num = stage.stage_num

        # Build bosses / post-midboss waves that have not appeared yet so the
        # whole stage's loot is included in the simulation.
        if getattr(stage, "mid_boss", None) is None and hasattr(stage, "setup_mid_boss"):
            try:
                stage.setup_mid_boss()
            except Exception:
                pass
        if (getattr(stage, "mid_boss", None) is not None
                and not getattr(stage, "post_waves_added", False)):
            if getattr(stage, "mid_boss_defeated_at", None) is None:
                stage.mid_boss_defeated_at = stage.timer
            try:
                stage._add_post_midboss_waves()
                stage.post_waves_added = True
            except Exception:
                pass
        if getattr(stage, "boss", None) is None and hasattr(stage, "setup_boss"):
            try:
                stage.setup_boss()
            except Exception:
                pass

        # Collect every enemy once (waves, timed waves, post-midboss waves,
        # mid boss and final boss).
        enemies = []
        seen = set()

        def add_enemy(enemy):
            if enemy is not None and id(enemy) not in seen:
                seen.add(id(enemy))
                enemies.append(enemy)

        manager = stage.enemy_manager
        for wave in list(getattr(manager, "waves", []) or []):
            for enemy in getattr(wave, "enemies", []) or []:
                add_enemy(enemy)
        for _, wave in list(getattr(manager, "timed_waves", []) or []):
            for enemy in getattr(wave, "enemies", []) or []:
                add_enemy(enemy)
        for wave in list(getattr(stage, "post_waves", []) or []):
            for enemy in getattr(wave, "enemies", []) or []:
                add_enemy(enemy)
        add_enemy(getattr(stage, "mid_boss", None))
        add_enemy(getattr(stage, "boss", None))

        from src.entities.pickup import DROP_OVERFLUX_POWER_ORB, DROP_REVIVE_STONE
        for enemy in enemies:
            # Roll drop tables for this enemy, de-duplicated per enemy exactly
            # like _reward_enemy_kill does.
            rolled = set()
            chance_mult = self.item_effects["drop_rate_mult"]
            epic_mult = self.item_effects["epic_drop_rate_mult"]
            for key in self._enemy_drop_keys(enemy):
                for item in self.item_manager.roll_drops(key, chance_mult, epic_mult):
                    if item.id in rolled:
                        continue
                    rolled.add(item.id)
                    self._gain_item(item)
                    self.item_popups.append({"item": item, "timer": 0})
            # Convert configured bonus drops straight into +Bomb / +Life.
            for drop_type in getattr(enemy, "bonus_drops", None) or []:
                if drop_type == DROP_OVERFLUX_POWER_ORB:
                    self.bombs = min(cfg.PLAYER_MAX_BOMBS, self.bombs + 1)
                    self.game.global_data["bombs"] = self.bombs
                elif drop_type == DROP_REVIVE_STONE:
                    self.lives = min(cfg.PLAYER_MAX_LIVES, self.lives + 1)
                    self.game.global_data["lives"] = self.lives

        # Keep only the last few popups in case they ever get drawn.
        if len(self.item_popups) > 12:
            self.item_popups = self.item_popups[-12:]

        # Register the 3-choice reward pool, persist run data and switch.
        self.pending_boss_reward_pool = BOSS_REWARD_POOLS[stage_num]
        self.game.global_data["score"] = self.score
        self.game.global_data["lives"] = self.lives
        self.game.global_data["bombs"] = self.bombs
        self.game.global_data["power"] = self.power
        self.game.global_data["graze"] = self.graze
        self.game.global_data["skills"] = self.skill_manager.to_dict()
        self._save_item_inventory()
        self.game.stop_music()
        from src.ui.boss_reward import BossRewardState
        self.game.switch_state(BossRewardState(
            self.game, stage_num, self.pending_boss_reward_pool))

    def _enemy_drop_keys(self, enemy):
        """推导掉落表 key：
        - 敌人实例配置 drop_group 时按该分组掷（五面按 Boss 身份分组）；
        - 否则按身份推 stage{N}_final_boss / midboss / minion；
        - 所有敌人额外掷 stage{N}_any（该面任意敌人通用表）；
        - 最后回退到类型名与基类名，保证子类小怪也能吃到掉落。"""
        from src.entities.boss import Boss
        keys = []
        stage_num = self.stage.stage_num
        group = getattr(enemy, "drop_group", None)
        if group:
            groups = group if isinstance(group, (list, tuple)) else [group]
            for g in groups:
                if g and g not in keys:
                    keys.append(g)
        elif isinstance(enemy, Boss):
            if enemy is self.stage.boss:
                keys.append(f"stage{stage_num}_final_boss")
            elif enemy is self.stage.mid_boss:
                keys.append(f"stage{stage_num}_midboss")
        else:
            keys.append(f"stage{stage_num}_minion")
        keys.append(f"stage{stage_num}_any")
        if isinstance(enemy, Boss) and enemy is self.stage.mid_boss:
            keys.append("MidBoss")
        keys.append(type(enemy).__name__)
        for klass in type(enemy).__mro__[1:]:
            keys.append(klass.__name__)
        return keys

    def _use_bomb(self, deathbomb=False):
        """使用Bomb；deathbomb=True 时按决死Bomb规则消耗资源。"""
        if deathbomb:
            cost = 2 if self.bombs >= 2 else 1
        else:
            cost = 1
        self.bombs -= cost
        # Hyperion：使用决死Bomb并消耗2B时回复1B
        if deathbomb and cost == 2 and int(self.item_effects["deathbomb_refund"]) > 0:
            self.bombs = min(cfg.PLAYER_MAX_BOMBS, self.bombs + 1)
        self.game.global_data["bombs"] = self.bombs
        self.bomb_active = True
        self.bomb_timer = 0
        self.death_window = 0

        # Bomb 本身也是符卡：开场立即清屏，展开自机符卡而不进入Boss符卡阶段。
        self.bullet_manager.cancel_all_enemy_bullets()
        self.player.spell_invincible = True
        bomb_mult = 1.0 + self.item_effects["bomb_damage_pct"] / 100.0
        self.player_spell = PlayerSpellCard(
            self.player,
            self.bullet_manager,
            self.stage,
            self.game,
            on_enemy_killed=self._reward_enemy_kill,
            deathbomb=deathbomb,
            damage_mult=bomb_mult,
        )

    def _check_collisions(self):
        from src.entities.boss import Boss

        # 玩家弹 vs 敌人
        for pb in self.bullet_manager.player_bullets[:]:
            for enemy in self.stage.get_active_enemies():
                if not enemy.alive:
                    continue
                if enemy.collides_with_bullet(pb.x, pb.y, pb.collision_radius):
                    pb.alive = False
                    # 目标类型伤害加成：小怪（Undead Sword）/ 道中Boss（Catacombs）/
                    # 凋零（Wither Relic）
                    dmg = pb.damage * self._target_damage_mult(enemy)
                    # 命中来源标记：焚符等“持续输出”类机制据此判定压制力，
                    # 追踪弹自动命中不应能无脑维持压制。
                    if isinstance(enemy, Boss):
                        killed = enemy.take_damage(
                            dmg, source="homing" if pb.homing else "main")
                    else:
                        killed = enemy.take_damage(dmg)
                    if killed:
                        self._reward_enemy_kill(enemy)
                    break

        # 召唤小怪弹幕：可以抵消敌弹
        for pb in self.bullet_manager.player_bullets[:]:
            if not getattr(pb, "cancels_bullets", False) or not pb.alive:
                continue
            for eb in self.bullet_manager.enemy_bullets[:]:
                if not eb.alive or eb.cancel_timer > 0:
                    continue
                if circle_collision(pb.x, pb.y, max(4.0, pb.collision_radius),
                                    eb.x, eb.y, eb.collision_radius):
                    eb.start_cancel()
                    pb.alive = False
                    break

        # 凋零护盾：碰到敌弹将其抵消并失去该护盾
        if self.wither_shields:
            for shield in self.wither_shields[:]:
                if not shield.alive:
                    continue
                for eb in self.bullet_manager.enemy_bullets[:]:
                    if not eb.alive or eb.cancel_timer > 0:
                        continue
                    if circle_collision(shield.x, shield.y, shield.size + 2,
                                        eb.x, eb.y, eb.collision_radius):
                        eb.start_cancel()
                        shield.alive = False
                        break
            self.wither_shields = [s for s in self.wither_shields if s.alive]

        # Bonzo 气球：碰到敌弹爆炸（清掉爆炸范围内的敌弹）
        if self.bonzo_balloons:
            for bal in self.bonzo_balloons[:]:
                if not bal.alive:
                    continue
                for eb in self.bullet_manager.enemy_bullets[:]:
                    if not eb.alive or eb.cancel_timer > 0:
                        continue
                    if circle_collision(bal.x, bal.y, bal.radius,
                                        eb.x, eb.y, eb.collision_radius):
                        bal.explode(self.bullet_manager)
                        break
            self.bonzo_balloons = [b for b in self.bonzo_balloons if b.alive]

        # 可击破大玉（展符缺口玉） vs 玩家弹：击破后爆炸清弹（范围内玩家也受伤）
        for eb in self.bullet_manager.enemy_bullets[:]:
            if not eb.shootable or not eb.alive or eb.cancel_timer > 0:
                continue
            for pb in self.bullet_manager.player_bullets[:]:
                if not pb.alive:
                    continue
                if circle_collision(eb.x, eb.y, eb.collision_radius,
                                    pb.x, pb.y, pb.collision_radius):
                    pb.alive = False
                    eb.hp -= pb.damage
                    if eb.hp <= 0:
                        self._explode_shootable_orb(eb)
                        break

        # 敌弹 vs 玩家（消弹动画中的子弹不造成伤害）
        if self.player.can_be_hit():
            for eb in self.bullet_manager.enemy_bullets[:]:
                if eb.cancel_timer > 0 or eb.harmless:
                    continue
                if eb.hits_player(self.player.x, self.player.y, self.player.hitbox_radius):
                    self._on_player_hit()
                    break

        # Storm 符卡「Giga Lightning」：全屏毁灭性雷击——不在仍然有效的避雷柱安全区内即中弹
        giga = getattr(getattr(self.stage, "boss", None), "storm_giga", None)
        if (giga is not None and giga.get("strike_active")
                and not giga.get("strike_checked") and self.player.can_be_hit()):
            giga["strike_checked"] = True
            safe_r = giga.get("safe_radius", 34)
            safe = any(
                p["alive"] and math.hypot(self.player.x - p["x"],
                                          self.player.y - p["y"]) <= safe_r
                for p in giga.get("pillars", []))
            if not safe:
                self._on_player_hit()

        # 机械符「Terminal Pursuit」：被 Goldor 追上 -> 中弹
        goldor_t = getattr(getattr(self.stage, "boss", None), "goldor_terminal", None)
        if (goldor_t is not None and goldor_t.get("caught_active")
                and self.player.can_be_hit()):
            goldor_t["caught_active"] = False
            self._on_player_hit()

        # 裂符「Dimensional Slash」：被触手拖到 Kaeman 怀中 -> 中弹
        slash_st = getattr(getattr(self.stage, "boss", None), "kaeman_slash", None)
        if (slash_st is not None and slash_st.get("grab_hit_active")
                and self.player.can_be_hit()):
            slash_st["grab_hit_active"] = False
            self._on_player_hit()

        # 王符「Atomizing Ray」：旋转扫射光束扫中 -> 中弹
        atom_st = getattr(getattr(self.stage, "boss", None), "kaeman_atomize", None)
        if (atom_st is not None and atom_st.get("beam_active")
                and self.player.can_be_hit()):
            ax = atom_st.get("bx", 0.0)
            ay = atom_st.get("by", 0.0)
            al = atom_st.get("length", 0.0)
            angles = atom_st.get("angles")
            if not angles:
                angles = (atom_st.get("angle", 0.0),)
            for aa in angles:
                ex = ax + math.cos(aa) * al
                ey = ay + math.sin(aa) * al
                if point_segment_distance(self.player.x, self.player.y,
                                          ax, ay, ex, ey) <= (atom_st.get("hit_radius", 8.0)
                                                               + self.player.hitbox_radius):
                    self._on_player_hit()
                    break

        # 焚符「Nuclear Frenzy」：核能爆炸领域内即中弹（持续输出才能压制范围）
        nuke = getattr(getattr(self.stage, "boss", None), "necron_nuclear", None)
        if (nuke is not None and self.player.can_be_hit()
                and math.hypot(self.player.x - nuke.get("cx", 0),
                               self.player.y - nuke.get("cy", 0))
                <= nuke.get("radius", 0) + self.player.hitbox_radius):
            self._on_player_hit()

        # 擦弹判定
        if self.player.focused:
            for eb in self.bullet_manager.enemy_bullets[:]:
                if eb.grazed or eb.cancel_timer > 0 or eb.harmless:
                    continue
                dist_sq = (eb.x - self.player.x)**2 + (eb.y - self.player.y)**2
                if dist_sq < (self.player.graze_radius + eb.collision_radius)**2 and dist_sq > (self.player.hitbox_radius + eb.collision_radius)**2:
                    eb.grazed = True
                    self.graze += 1
                    self.score += 100

    def _explode_shootable_orb(self, eb):
        """可击破大玉被击破：爆炸清掉周围敌弹，范围内玩家也受伤"""
        # 大玉自身变白自爆（期间不参与碰撞与擦弹）
        eb.start_cancel()
        eb.harmless = True
        # 爆炸清弹：半径内敌弹进入消弹动画
        for b in self.bullet_manager.enemy_bullets[:]:
            if b is eb or b.harmless or b.cancel_timer > 0 or not b.alive:
                continue
            if circle_collision(eb.x, eb.y, eb.explode_radius, b.x, b.y, 0):
                b.start_cancel()
        # 爆炸光效：白紫双圈扩散
        from src.entities.bullet import create_bullet_angle, Bullet
        for radius, color, frames in (
                (eb.explode_radius * 0.5, (210, 240, 255), 6),
                (eb.explode_radius * 0.3, (150, 70, 210), 10)):
            f = create_bullet_angle(eb.x, eb.y, 0.0, 0.0, Bullet.TYPE_CIRCLE,
                                    radius=radius, color=color)
            f.manager = self.bullet_manager
            f.harmless = True
            f.lifetime = frames
            self.bullet_manager.add_enemy_bullet(f)
        # 范围内玩家也受伤
        if self.player.can_be_hit() and circle_collision(
                eb.x, eb.y, eb.explode_radius,
                self.player.x, self.player.y, self.player.hitbox_radius):
            self._on_player_hit()

    def _on_player_hit(self):
        """玩家中弹：重甲抵消 / 蜘蛛护符自动决死 / Last Spell直接结算，否则进入决死Bomb窗口。"""
        eff = self.item_effects
        # Heavy Armor：概率抵消被弹
        if eff["hit_cancel_chance"] > 0 and random.random() * 100.0 < eff["hit_cancel_chance"]:
            return
        # Spider Artifact：失去残机后10s内再次失机 -> 改为失去1B并放出决死Bomb
        if eff["spider_artifact"] and self.spider_timer > 0 and self.bombs >= 1:
            self.spider_timer = 0
            self.bombs -= 1
            self.game.global_data["bombs"] = self.bombs
            self._use_bomb()
            return
        if (self.stage.boss is not None
                and self.stage.boss.is_last_spell_active()):
            self._player_die()
            return
        self._start_death_window()

    def _start_death_window(self):
        """开启约12帧的红色收缩结界，等待玩家按下Bomb触发决死Bomb。"""
        if self.death_window > 0:
            return
        self.death_window = DEATHBOMB_WINDOW_FRAMES
        self.player.invincible = max(self.player.invincible,
                                     self.death_window + 1)

    def _draw_death_window(self, screen, offset_x=0, offset_y=0):
        """绘制中弹后的红色收缩结界。"""
        if self.death_window <= 0:
            return
        t = 1.0 - self.death_window / float(DEATHBOMB_WINDOW_FRAMES)
        radius = max(12, int(58 * (1.0 - t) + 12))
        px = int(self.player.x + offset_x)
        py = int(self.player.y + offset_y)

        diameter = radius * 2 + 8
        barrier = pygame.Surface((diameter, diameter), pygame.SRCALPHA)
        center = diameter // 2
        pygame.draw.circle(barrier, (255, 48, 48, 48), (center, center), radius, 0)
        pygame.draw.circle(barrier, (255, 64, 64, 235), (center, center), radius, 3)
        pygame.draw.circle(barrier, (255, 150, 150, 170), (center, center),
                           max(6, radius - 7), 1)
        screen.blit(barrier, (px - center, py - center))

    def _player_die(self):
        """玩家死亡"""
        # 练习模式：Miss 即重试当前符卡，不消耗残机、不触发游戏结束
        if self.practice_info:
            self._practice_restart()
            return
        # Last Spell 挑战：Miss 不损残机，直接强制结束（彩蛋性质）
        if (self.stage.boss is not None
                and self.stage.boss.is_last_spell_active()):
            self.stage.boss.force_end_last_spell()
            self.player.hit()
            return
        self.lives -= 1
        self.lives_lost_this_stage += 1
        # Arack / Spider Artifact：失去残机后的10秒触发窗口
        self.arack_timer = int(cfg.FPS * 10)
        self.spider_timer = int(cfg.FPS * 10)
        self.game.global_data["lives"] = self.lives
        if self.lives <= 0:
            self.game_over = True
            self.dialogue = None   # 对话中死亡：立即结束对话
        else:
            self.player.hit()
            gt = None
            if self.stage.boss is not None:
                gt = getattr(self.stage.boss, "goldor_terminal", None)
            if not (gt is not None and not gt.get("spell_done")):
                self.player.reset_position()
            self.bullet_manager.clear_all()
            self.bullet_manager.cancel_all_enemy_bullets()
            # 裂符「Dimensional Slash」：死亡复活时取消触手拉拽，避免重生后再被拖
            slash_st = getattr(getattr(self.stage, "boss", None), "kaeman_slash", None)
            if slash_st is not None:
                slash_st["tentacle"] = None
                slash_st["grab_hit_active"] = False

    def _restart(self):
        """重新开始"""
        # 重置当前关卡（同一关重开）
        stage = type(self.stage)()
        stage.setup_waves()
        self.stage = stage

        # 重置子管理器
        from src.entities.bullet import BulletManager
        from src.entities.player import Player
        self.bullet_manager = BulletManager()
        self.player = Player(cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80)

        # 重置数值
        self.score = 0
        self.lives = cfg.PLAYER_START_LIVES
        self.bombs = cfg.PLAYER_START_BOMBS
        self.power = 0
        self.graze = 0
        # 同步全局数据
        self.game.global_data["score"] = 0
        self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
        self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
        self.game.global_data["power"] = 0
        self.game.global_data["graze"] = 0

        # 重置 Skyblock 物品数据
        from src.systems.item_system import ItemInventory
        self.item_inventory = ItemInventory()
        self.item_inventory.save_to_global_data(self.game.global_data)
        self.equipment_stats = {}

        # 重置状态
        self.game_over = False
        self.stage_clear = False
        self.clear_timer = 0
        self.bomb_active = False
        self.bomb_timer = 0
        self.player_spell = None
        self.player.spell_invincible = False
        self.death_window = 0
        self.bomb_blocked_timer = 0
        self.item_popups.clear()
        self.power_items.clear()
        self.bonus_items.clear()
        self.homing_shot_skip = False

        # 重置物品效果与 C 技能状态（重开后背包已清空）
        self.item_effects = aggregate_effects(self.item_inventory, self.stage.stage_num)
        self.c_skill_id = self.item_inventory.get_c_skill_equipped_id()
        self.c_uses = {}
        self.c_skill_message = ""
        self.c_skill_message_timer = 0
        self.bad_health_timer = 0
        self.arack_timer = 0
        self.spider_timer = 0
        self.spirit_bow_timer = 0
        self.end_stone_timer = 0
        self.precursor_timer = 0
        self.lives_lost_this_stage = 0
        self.kill_counter = 0
        self.shadow_damage = 0.0
        self.wither_shields = []
        self.bonzo_balloons = []
        self.fot_roses = []
        self.overflux_orbs = []
        self.summoned_minions = []
        self.player.hitbox_radius = cfg.PLAYER_HITBOX_RADIUS * self.item_effects["hitbox_scale"]
        self._apply_stage_start_bonuses()
        self.dialogue = None
        self.boss_music_intro = False
        self.mid_boss_music_started = False
        self.stage_music_intro = False

        # 重播音乐
        self._play_stage_music()
        # 重开后同样显示道中曲名
        self._show_music_name(self.stage.music_name)
        # 重开后同样显示关卡标题
        self._show_stage_title(self.stage.title_path)

    # ================= C 技能与物品被动效果 =================

    def _set_c_message(self, text, frames=80):
        self.c_skill_message = text
        self.c_skill_message_timer = frames

    def _apply_stage_start_bonuses(self):
        """关卡开始时应用 Goldor's Helmet / Storm's Leggings 等效果并重置本关计数。"""
        eff = self.item_effects
        if int(eff["start_lives"]) > 0:
            self.lives = min(cfg.PLAYER_MAX_LIVES, self.lives + int(eff["start_lives"]))
        if int(eff["start_bombs"]) > 0:
            self.bombs = min(cfg.PLAYER_MAX_BOMBS, self.bombs + int(eff["start_bombs"]))
        self.game.global_data["lives"] = self.lives
        self.game.global_data["bombs"] = self.bombs
        self.lives_lost_this_stage = 0
        self.kill_counter = 0
        self.shadow_damage = 0.0
        self.c_uses = {}
        if self.c_skill_id:
            self.c_uses[self.c_skill_id] = 0
        self.wither_shields = []
        self.bonzo_balloons = []
        self.fot_roses = []
        self.overflux_orbs = []
        self.summoned_minions = []
        self.spirit_bow_timer = 0
        self.end_stone_timer = 0
        self.precursor_timer = 0

    def _enemy_bullet_near_graze(self):
        """是否有敌弹位于擦弹范围内（Tarantula Pet 加速判断）。"""
        px, py = self.player.x, self.player.y
        r = self.player.graze_radius + 8
        for b in self.bullet_manager.enemy_bullets:
            if not b.alive or b.cancel_timer > 0 or b.harmless:
                continue
            if (b.x - px) ** 2 + (b.y - py) ** 2 <= r * r:
                return True
        return False

    def _apply_speed_effects(self):
        """根据装备效果修正玩家移动速度（在 handle_input 之后调用）。"""
        eff = self.item_effects
        mult = 1.0 + eff["speed_pct"] / 100.0
        if not self.player.focused:
            mult += eff["high_speed_pct"] / 100.0
        if eff["graze_speed_pct"] > 0 and self._enemy_bullet_near_graze():
            mult += eff["graze_speed_pct"] / 100.0
        self.player.speed = max(0.15, self.player.speed * mult)

    def _apply_graze_slow(self):
        """低速状态擦弹范围内敌弹减速（Scarf's Studies）；离开范围后恢复原速。"""
        eff = self.item_effects
        slow = 1.0 - eff["graze_slow_pct"] / 100.0
        px, py = self.player.x, self.player.y
        r = self.player.graze_radius
        for b in self.bullet_manager.enemy_bullets:
            if not b.alive or b.cancel_timer > 0 or b.harmless:
                continue
            base = getattr(b, "base_speed", 0.0)
            if base <= 0:
                continue
            in_range = self.player.focused and (b.x - px) ** 2 + (b.y - py) ** 2 <= r * r
            cur = math.hypot(b.vx, b.vy)
            if cur <= 0.01:
                continue
            if in_range:
                target = base * slow
                if cur > target:
                    k = target / cur
                    b.vx *= k
                    b.vy *= k
            else:
                if cur < base * 0.99:
                    k = min(1.0, (base / cur) ** 0.12)
                    b.vx *= k
                    b.vy *= k

    # ---- C 技能 ----

    def _use_c_skill(self):
        """按 C 释放当前装备的 C 技能。"""
        item_id = self.c_skill_id
        if not item_id:
            self._set_c_message("未装备 C 技能物品")
            return
        info = C_SKILLS.get(item_id)
        if not info:
            return
        used = self.c_uses.get(item_id, 0)
        if used >= info["per_stage"]:
            self._set_c_message(f"C技能「{info['name']}」：本面已用完（{info['per_stage']}次）")
            return
        handler = getattr(self, f"_c_{item_id}", None)
        if handler is None:
            return
        if not handler():
            return
        self.c_uses[item_id] = used + 1
        remain = info["per_stage"] - used - 1
        self._set_c_message(f"C技能「{info['name']}」已释放（本面剩余{remain}次）")

    def _c_sword_of_bad_health(self):
        """消耗1残机，10秒内友方伤害+200%。"""
        if self.lives <= 1:
            self._set_c_message("残机不足，无法使用嗜血爆发")
            return False
        self.lives -= 1
        self.lives_lost_this_stage += 1
        self.game.global_data["lives"] = self.lives
        self.bad_health_timer = int(cfg.FPS * 10)
        return True

    def _c_bonzos_staff(self):
        """放出3个随机方向有后坐力的气球。"""
        from src.systems.c_skill_entities import BonzoBalloon
        for _ in range(3):
            self.bonzo_balloons.append(BonzoBalloon(self.player.x, self.player.y - 10))
        for bal in self.bonzo_balloons[-3:]:
            self.player.x = max(cfg.PLAY_AREA_LEFT, min(cfg.PLAY_AREA_RIGHT,
                                                        self.player.x - bal.vx * 6))
            self.player.y = max(cfg.PLAY_AREA_TOP, min(cfg.PLAY_AREA_BOTTOM,
                                                        self.player.y - bal.vy * 6))
        return True

    def _c_golem_sword(self):
        """钢铁之击：炸掉擦弹范围内所有弹幕。"""
        px, py = self.player.x, self.player.y
        r = self.player.graze_radius
        for b in self.bullet_manager.enemy_bullets[:]:
            if not b.alive or b.cancel_timer > 0:
                continue
            if circle_collision(px, py, r, b.x, b.y, b.collision_radius):
                b.start_cancel()
        return True

    def _c_aspect_of_the_end(self):
        self._teleport_player()
        return True

    def _c_enderman_pet_epic(self):
        self._teleport_player()
        return True

    def _c_tarantula_boots(self):
        """蛛影突袭：清除当前移动方向上最近的1个弹幕并快速移动至其位置。"""
        dx, dy = self.player.vx, self.player.vy
        if dx == 0 and dy == 0:
            dy = -1.0
        length = math.hypot(dx, dy) or 1.0
        ux, uy = dx / length, dy / length
        px, py = self.player.x, self.player.y
        best = None
        best_dist2 = None
        for b in self.bullet_manager.enemy_bullets:
            if not b.alive or b.cancel_timer > 0 or b.harmless:
                continue
            rx, ry = b.x - px, b.y - py
            if rx * ux + ry * uy <= 0:
                continue
            d2 = rx * rx + ry * ry
            if best_dist2 is None or d2 < best_dist2:
                best_dist2 = d2
                best = b
        if best is None:
            self._set_c_message("当前移动方向前方没有可清除的弹幕")
            return False
        best.start_cancel()
        self.player.x = max(cfg.PLAY_AREA_LEFT, min(cfg.PLAY_AREA_RIGHT, best.x))
        self.player.y = max(cfg.PLAY_AREA_TOP, min(cfg.PLAY_AREA_BOTTOM, best.y))
        return True

    def _teleport_player(self):
        """向当前移动方向瞬移一段距离。"""
        dx, dy = self.player.vx, self.player.vy
        if dx == 0 and dy == 0:
            dy = -1.0
        length = math.hypot(dx, dy) or 1.0
        dist = 150
        self.player.x = max(cfg.PLAY_AREA_LEFT, min(cfg.PLAY_AREA_RIGHT,
                                                    self.player.x + dx / length * dist))
        self.player.y = max(cfg.PLAY_AREA_TOP, min(cfg.PLAY_AREA_BOTTOM,
                                                    self.player.y + dy / length * dist))

    def _c_end_stone_sword(self):
        """2秒内无法移动且无法受伤。"""
        self.end_stone_timer = int(cfg.FPS * 2)
        self.player.invincible = max(self.player.invincible, int(cfg.FPS * 2) + 1)
        return True

    def _c_wither_cloak_sword(self):
        """召唤6个护盾围绕自机，持续10秒。"""
        from src.systems.c_skill_entities import WitherShield
        if self.wither_shields:
            self._set_c_message("凋零护盾已在场")
            return False
        self.wither_shields = [WitherShield(self.player, i, 6) for i in range(6)]
        return True

    def _c_spirit_bow(self):
        """10秒内所有自机子弹变为追踪弹。"""
        self.spirit_bow_timer = int(cfg.FPS * 10)
        for pb in self.bullet_manager.player_bullets:
            pb.homing = True
        return True

    def _c_aspect_of_the_dragons(self):
        """龙怒：炸掉上方弹幕并对BOSS造成4800伤害。"""
        limit_y = self.player.y + 30
        for b in self.bullet_manager.enemy_bullets[:]:
            if not b.alive or b.cancel_timer > 0:
                continue
            if b.y < limit_y:
                b.start_cancel()
        boss = self.stage.boss
        if boss is not None and boss.alive and getattr(boss, "combat_enabled", True):
            self._apply_boss_damage(boss, 4800)
        return True

    def _c_flower_of_truth(self):
        """放出玫瑰：追踪消灭最近3个弹幕后飞向BOSS造成1200伤害。"""
        from src.systems.c_skill_entities import FlowerRose
        if self.fot_roses:
            self._set_c_message("玫瑰已在场")
            return False
        self.fot_roses.append(FlowerRose(self.player.x, self.player.y - 12))
        return True

    def _c_giants_sword(self):
        """清除全场弹幕并对BOSS造成当前阶段50%的伤害。"""
        self.bullet_manager.cancel_all_enemy_bullets()
        boss = self.stage.boss
        if boss is not None and boss.alive and getattr(boss, "combat_enabled", True):
            self._apply_boss_damage(boss, boss.hp * 0.5)
        return True

    def _c_precursor_eye(self):
        """向上射出1道持续3秒的红色激光（帧伤20）。"""
        self.precursor_timer = int(cfg.FPS * 3)
        return True

    def _c_overflux_power_orb(self):
        """Boss战中召唤Orb，持续处于范围内10秒获得1残机。"""
        from src.systems.c_skill_entities import OverfluxOrb
        boss = self.stage.boss
        if boss is None or not boss.alive or not getattr(boss, "combat_enabled", True):
            self._set_c_message("能量核心只能在Boss战中使用")
            return False
        if self.overflux_orbs:
            self._set_c_message("能量核心已在场")
            return False
        self.overflux_orbs.append(OverfluxOrb(self.player.x, self.player.y))
        return True

    def _c_summoning_ring(self):
        """随机召唤2只归属于你的小怪。"""
        from src.systems.c_skill_entities import SummonedMinion
        for off in (-22, 22):
            self.summoned_minions.append(SummonedMinion(self.player.x + off, self.player.y + 8))
        return True

    def _apply_boss_damage(self, boss, damage):
        """对 Boss 造成 C 技能伤害；若击破则补发击杀奖励。"""
        if boss is None or not boss.alive:
            return False
        killed = boss.take_damage(damage, source="main")
        if killed:
            self._reward_enemy_kill(boss)
        return killed

    # ---- 目标类型伤害倍率 ----

    def _target_damage_mult(self, enemy):
        from src.entities.boss import Boss
        eff = self.item_effects
        mult = 1.0
        if isinstance(enemy, Boss):
            if self._is_midboss_target(enemy):
                mult *= 1.0 + eff["midboss_damage_pct"] / 100.0
            if self._is_wither_target(enemy):
                mult *= 1.0 + eff["wither_damage_pct"] / 100.0
        else:
            mult *= 1.0 + eff["minion_damage_pct"] / 100.0
        return mult

    def _is_midboss_target(self, enemy):
        if enemy is self.stage.mid_boss:
            return True
        group = getattr(enemy, "drop_group", None)
        if group:
            groups = group if isinstance(group, (list, tuple)) else [group]
            return "MidBoss" in groups
        return False

    def _is_wither_target(self, enemy):
        return getattr(enemy, "is_wither", False) or getattr(enemy, "name", "") in WITHER_BOSS_NAMES

    # ---- 每帧 C 技能更新 ----

    def _update_c_skills(self):
        eff = self.item_effects
        if self.bad_health_timer > 0:
            self.bad_health_timer -= 1
        if self.arack_timer > 0:
            self.arack_timer -= 1
        if self.spider_timer > 0:
            self.spider_timer -= 1
        if self.spirit_bow_timer > 0:
            self.spirit_bow_timer -= 1
        if self.precursor_timer > 0:
            self.precursor_timer -= 1
            self._precursor_laser_damage()
        if self.c_skill_message_timer > 0:
            self.c_skill_message_timer -= 1
            if self.c_skill_message_timer <= 0:
                self.c_skill_message = ""

        for shield in self.wither_shields[:]:
            shield.update(self.player)
        self.wither_shields = [s for s in self.wither_shields if s.alive]

        for bal in self.bonzo_balloons[:]:
            bal.update()
        self.bonzo_balloons = [b for b in self.bonzo_balloons if b.alive]

        for rose in self.fot_roses[:]:
            rose.update(self.bullet_manager, self.stage.boss)
        self.fot_roses = [r for r in self.fot_roses if r.alive]

        for orb in self.overflux_orbs[:]:
            gained = orb.update(self.player)
            if gained:
                self.lives = min(cfg.PLAYER_MAX_LIVES, self.lives + 1)
                self.game.global_data["lives"] = self.lives
                self._set_c_message("能量核心充能完成：+1残机")
                orb.alive = False
        self.overflux_orbs = [o for o in self.overflux_orbs if o.alive]

        for m in self.summoned_minions[:]:
            m.update(self.bullet_manager, self.stage.boss)
        self.summoned_minions = [m for m in self.summoned_minions if m.alive]

        # 擦弹减速（Scarf's Studies）
        if eff["graze_slow_pct"] > 0:
            self._apply_graze_slow()

    def _precursor_laser_damage(self):
        """先驱激光每帧对光束范围内的 Boss 造成20点伤害。"""
        boss = self.stage.boss
        if boss is None or not boss.alive or not getattr(boss, "combat_enabled", True):
            return
        if abs(boss.x - self.player.x) <= 22 and boss.y < self.player.y:
            self._apply_boss_damage(boss, 20)

    def _draw_precursor_laser(self, screen, ox=0, oy=0):
        if self.precursor_timer <= 0:
            return
        px = int(self.player.x + ox)
        py = int(self.player.y + oy)
        top = int(oy)
        height = max(1, py - top)
        surf = pygame.Surface((40, height), pygame.SRCALPHA)
        surf.fill((255, 40, 40, 90))
        screen.blit(surf, (px - 20, top))
        pygame.draw.line(screen, (255, 120, 120), (px, top), (px, py), 2)
        pygame.draw.line(screen, (255, 255, 255), (px, py), (px, py - 12), 2)

    def _draw_c_skill_entities(self, screen, ox=0, oy=0):
        for shield in self.wither_shields:
            shield.draw(screen, ox, oy)
        for bal in self.bonzo_balloons:
            bal.draw(screen, ox, oy)
        for rose in self.fot_roses:
            rose.draw(screen, ox, oy)
        for orb in self.overflux_orbs:
            orb.draw(screen, ox, oy)
        for m in self.summoned_minions:
            m.draw(screen, ox, oy)
        self._draw_precursor_laser(screen, ox, oy)

    def _draw_c_skill_indicator(self, screen):
        """战斗区左上角显示当前 C 技能与剩余次数。"""
        if not self.c_skill_id:
            return
        info = C_SKILLS.get(self.c_skill_id)
        if not info:
            return
        used = self.c_uses.get(self.c_skill_id, 0)
        remain = max(0, info["per_stage"] - used)
        x = self.offset_x + 10
        y = self.offset_y + 10
        text = self.game.font_small.render(
            f"C：{info['name']}（本面{remain}/{info['per_stage']}）", True, cfg.COLOR_YELLOW)
        band = pygame.Surface((text.get_width() + 12, text.get_height() + 6), pygame.SRCALPHA)
        band.fill((0, 0, 0, 120))
        screen.blit(band, (x - 6, y - 3))
        screen.blit(text, (x, y))
        if self.c_skill_message:
            msg = self.game.font_small.render(self.c_skill_message, True, cfg.COLOR_GREEN)
            band2 = pygame.Surface((msg.get_width() + 12, msg.get_height() + 6), pygame.SRCALPHA)
            band2.fill((0, 0, 0, 120))
            screen.blit(band2, (x - 6, y + text.get_height() + 2))
            screen.blit(msg, (x, y + text.get_height() + 5))

    def _roll_terracotta_drops(self, soldier):
        """Sadan 兵符「Terracotta Army」的兵马俑被击破时的掉落。"""
        if self.practice_info:
            return
        chance_mult = self.item_effects["drop_rate_mult"]
        epic_mult = self.item_effects["epic_drop_rate_mult"]
        for item in self.item_manager.roll_drops("stage4_terracotta", chance_mult, epic_mult):
            self.item_popups.append({"item": item, "timer": 0})
            self._gain_item(item)

    def draw(self, screen):
        ox, oy = self.offset_x, self.offset_y

        # 清除整屏，避免新边距区域留下上一帧残影
        screen.fill(cfg.COLOR_BLACK)

        # 右侧面板背景（先画，防止战斗区绘制覆盖面板）
        pygame.draw.rect(screen, cfg.COLOR_PANEL_BG,
                         (cfg.PANEL_LEFT, 0, cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT))

        # 关卡绘制（战斗区域）
        # 裁剪到战斗框内：进场前的敌机/子弹等不会在框外（上下黑边）露出来
        battle_rect = pygame.Rect(ox, oy, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT)
        screen.set_clip(battle_rect)

        self.stage.draw(screen, ox, oy)

        # 掉落物（红色 Power 方块）
        for item in self.power_items:
            item.draw(screen, ox, oy)
        for item in self.bonus_items:
            item.draw(screen, ox, oy)

        # Player sprite is decorative and drawn below all bullets
        self.player.draw_sprite(screen, ox, oy)

        # Bullets
        self.bullet_manager.draw(screen, ox, oy)

        # Hitbox stays above bullet layers
        self.player.draw_hitbox(screen, ox, oy)

        # C 技能实体（护盾/气球/玫瑰/Orb/召唤小怪/激光）
        self._draw_c_skill_entities(screen, ox, oy)

        # 决死Bomb判定窗口：红色结界快速收缩
        if self.death_window > 0:
            self._draw_death_window(screen, ox, oy)

        # 自机符卡/Bomb特效（仅战斗区域，含立绘横幅、Hyperion与爆炸）
        if self.player_spell is not None:
            self.player_spell.draw(screen, ox, oy)

        # 符卡/关卡前景遮罩：绘制在子弹与自机之上（例如终符的黑暗吞噬）
        self.stage.draw_foreground(screen, ox, oy)
        # 恢复全屏绘制（边框、HUD、对话、横幅等照常绘制）

        screen.set_clip(None)

        # 战斗区域边框
        pygame.draw.rect(screen, cfg.COLOR_DARK_GRAY,
                         (ox, oy, cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT), 2)

        # 右侧 HUD
        active_boss = None
        if self.stage.boss and self.stage.boss.alive and self.stage.boss.combat_enabled:
            active_boss = self.stage.boss
        elif self.stage.mid_boss and self.stage.mid_boss.alive:
            active_boss = self.stage.mid_boss
        self.hud.draw(screen, self.player, self.score, self.lives,
                      self.bombs, self.power, self.graze,
                      stage_name=self.stage.name, boss=active_boss)

        # C 技能指示器（物品名 / 剩余次数 / 提示）
        self._draw_c_skill_indicator(screen)

        # Last Spell 中禁用 Bomb 的提示
        if self.bomb_blocked_timer > 0:
            hint = self.game.font_small.render(
                "LAST SPELL 中无法使用 Bomb！", True, cfg.COLOR_YELLOW)
            hx = self.player.x + self.offset_x - hint.get_width() // 2
            hy = self.player.y + self.offset_y - 46
            hx = max(self.offset_x + 8,
                     min(self.offset_x + cfg.BATTLE_AREA_WIDTH - hint.get_width() - 8, hx))
            screen.blit(hint, (hx, hy))

        # 掉落弹窗
        for popup in self.item_popups:
            self.hud.draw_item_popup(screen, popup["item"], popup["timer"])

        # 对话
        if self.dialogue:
            self.dialogue.draw(screen)

        # 关卡标题（面开始时覆盖在战斗界面上，随后淡出消失）
        self._draw_stage_title(screen)

        # 曲名横幅（面开始 / Boss战开始时显示当前音乐名）
        self._draw_music_banner(screen)

        # 暂停
        if self.paused:
            self.hud.draw_pause(screen)

        # 游戏结束
        if self.game_over:
            self.hud.draw_game_over(screen, self.score)

        # 通关
        if self.stage_clear:
            self.hud.draw_stage_clear(screen, self.score, self.stage.name)

        # 练习模式：右上角提示 + 击破结算
        if self.practice_info:
            self._draw_practice_overlay(screen)
