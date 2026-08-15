# 菜单界面

import os
import math
import random
import pygame
from src.engine import settings as cfg
from src.engine.collision import circle_collision
from src.engine.game import GameState
from src.entities.player_spell import PlayerSpellCard
from src.systems.item_system import BOSS_REWARD_POOLS

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
            # 新游戏：重置全局数据
            self.game.global_data["score"] = 0
            self.game.global_data["lives"] = cfg.PLAYER_START_LIVES
            self.game.global_data["bombs"] = cfg.PLAYER_START_BOMBS
            self.game.global_data["power"] = 0
            self.game.global_data["graze"] = 0
            from src.systems.item_system import ItemInventory
            empty_inventory = ItemInventory()
            empty_inventory.save_to_global_data(self.game.global_data)
            from src.stages import get_stage_class
            stage = get_stage_class(1)()
            stage.setup_waves()
            self.game.switch_state(PlayingState(self.game, stage))
        elif self.options[self.selected] == "Quit":
            self.game.running = False
        elif self.options[self.selected] == "Settings":
            self.game.push_state(SettingsState(self.game))
        elif self.options[self.selected] == "Practice":
            pass  # TODO

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
        version_text = self.game.font_small.render("v1.1.0 - Codex CLI Project", True, cfg.COLOR_DARK_GRAY)
        screen.blit(version_text, (10, cfg.SCREEN_HEIGHT - 18))



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
    def __init__(self, game, stage, skip_title=False):
        super().__init__(game)
        self.stage = stage
        self.skip_title = skip_title
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

    def exit(self):
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
                                        portrait_sides=getattr(self.stage, "dialogue_portrait_sides", {}))

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
        """玩家射击：按 power 升级弹幕形态（单线->两线->三线）+ 追踪弹"""
        from src.entities import bullet as bm
        power_level = self.power // 100  # 0-4
        weapon_damage = self._weapon_damage()

        # 主射击：单线 -> 两线 -> 三线
        px = self.player.x
        py = self.player.y - 8
        # 侧翼弹道向外倾斜，两弹道夹角 4.5 度（单侧 2.25 度）
        tilt_vx = 0.47
        tilt_vy = -11.96
        if power_level >= 2:
            # 三线：左倾、直射、右倾
            b = bm.create_player_bullet(px - 10, py, -tilt_vx, tilt_vy)
            b.damage = weapon_damage
            self.bullet_manager.add_player_bullet(b)
            b = bm.create_player_bullet(px, py)
            b.damage = weapon_damage
            self.bullet_manager.add_player_bullet(b)
            b = bm.create_player_bullet(px + 10, py, tilt_vx, tilt_vy)
            b.damage = weapon_damage
            self.bullet_manager.add_player_bullet(b)
        elif power_level >= 1:
            # 两线：左右向外倾斜
            b = bm.create_player_bullet(px - 10, py, -tilt_vx, tilt_vy)
            b.damage = weapon_damage
            self.bullet_manager.add_player_bullet(b)
            b = bm.create_player_bullet(px + 10, py, tilt_vx, tilt_vy)
            b.damage = weapon_damage
            self.bullet_manager.add_player_bullet(b)
        else:
            # 单线：中间一条
            b = bm.create_player_bullet(px, py)
            b.damage = weapon_damage
            self.bullet_manager.add_player_bullet(b)

        # 追踪弹：始终只有 1 列；power>=15 开始产生，射速为正常一半；
        # 伤害随 power 从正常 1/3 提升到 2/3；power 满（400）时射速恢复正常（每帧发射）
        if self.power >= 15:
            full_power = self.power >= self.player.max_power
            if full_power or not self.homing_shot_skip:
                base = weapon_damage
                ratio = 1 / 3 + (1 / 3) * (self.power - 15) / (self.player.max_power - 15)
                hb = bm.create_player_bullet(px, py - 4, homing=True)
                hb.damage = round(base * ratio, 1)
                self.bullet_manager.add_player_bullet(hb)
            if not full_power:
                self.homing_shot_skip = not self.homing_shot_skip

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
        """将掉落物品计入背包；SkyBlock Coin 直接转换为金币。"""
        if item.id == "skyblock_coin":
            self.item_inventory.add_coins(100)
        else:
            self.item_inventory.add_item(item.id)
        self._save_item_inventory()

    def _weapon_damage(self):
        """当前玩家弹幕基础伤害。

        暂时禁用所有物品词条对战斗的影响（后续重做物品效果时再接入）。
        """

        return cfg.BULLET_PLAYER_DAMAGE

    def _reward_enemy_kill(self, enemy):
        """敌人被击破后的奖励结算（分数/技能经验/掉落）"""
        from src.entities.boss import Boss
        self.score += enemy.score
        self.skill_manager.add_xp("COMBAT", enemy.score // 10)
        dropped_ids = set()
        drops = []
        for key in self._enemy_drop_keys(enemy):
            for item in self.item_manager.roll_drops(key):
                if item.id not in dropped_ids:
                    dropped_ids.add(item.id)
                    drops.append(item)
        if isinstance(enemy, Boss):
            # 关底 Boss 被真正击破时登记 4 选 1 奖励池（防复活/重复触发）
            if (enemy is self.stage.boss and self.pending_boss_reward_pool is None
                    and self.stage.stage_num in BOSS_REWARD_POOLS):
                self.pending_boss_reward_pool = BOSS_REWARD_POOLS[self.stage.stage_num]
            for item in self.item_manager.roll_drops("Boss"):
                if item.id not in dropped_ids:
                    dropped_ids.add(item.id)
                    drops.append(item)
        for item in drops:
            self.item_popups.append({"item": item, "timer": 0})
            self._gain_item(item)
        self._spawn_power_drops(enemy)
        self._spawn_bonus_drops(enemy)

    def _register_boss_reward(self):
        """兜底登记关底 Boss 的 4 选 1 奖励。

        伤害击杀时 _reward_enemy_kill 已经登记（pending_boss_reward_pool 非空），
        这里只处理 Last Spell 超时 / Miss 强退等未经过 _reward_enemy_kill 的死亡路径，
        并顺带补发该 Boss 专属掉落表与 Boss 通用掉落的掉落。
        """
        if self.pending_boss_reward_pool is not None:
            return
        boss = getattr(self.stage, "boss", None)
        if boss is None or boss.alive:
            return
        stage_num = self.stage.stage_num
        if stage_num not in BOSS_REWARD_POOLS:
            return
        self.pending_boss_reward_pool = BOSS_REWARD_POOLS[stage_num]
        granted = set()
        for key in (f"stage{stage_num}_final_boss", "Boss"):
            for item in self.item_manager.roll_drops(key):
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
            for key in self._enemy_drop_keys(enemy):
                for item in self.item_manager.roll_drops(key):
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
        优先敌人实例上的 drop_group；其次按身份（关底/道中Boss/小怪）推
        stage{N}_xxx；最后回退到类型名与基类名，保证子类小怪也能吃到掉落。"""
        from src.entities.boss import Boss
        keys = []
        group = getattr(enemy, "drop_group", None)
        if group:
            keys.append(group)
        stage_num = self.stage.stage_num
        if isinstance(enemy, Boss):
            if enemy is self.stage.boss:
                keys.append(f"stage{stage_num}_final_boss")
            elif enemy is self.stage.mid_boss:
                keys.append(f"stage{stage_num}_midboss")
        else:
            keys.append(f"stage{stage_num}_minion")
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
        self.game.global_data["bombs"] = self.bombs
        self.bomb_active = True
        self.bomb_timer = 0
        self.death_window = 0

        # Bomb 本身也是符卡：开场立即清屏，展开自机符卡而不进入Boss符卡阶段。
        self.bullet_manager.cancel_all_enemy_bullets()
        self.player.spell_invincible = True
        self.player_spell = PlayerSpellCard(
            self.player,
            self.bullet_manager,
            self.stage,
            self.game,
            on_enemy_killed=self._reward_enemy_kill,
            deathbomb=deathbomb,
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
                    killed = enemy.take_damage(pb.damage)
                    if killed:
                        self._reward_enemy_kill(enemy)
                    break

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
        """玩家中弹：Last Spell直接结算，否则进入决死Bomb窗口。"""
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
        # Last Spell 挑战：Miss 不损残机，直接强制结束（彩蛋性质）
        if (self.stage.boss is not None
                and self.stage.boss.is_last_spell_active()):
            self.stage.boss.force_end_last_spell()
            self.player.hit()
            return
        self.lives -= 1
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
