# 菜单界面

import os
import math
import random
import pygame
from src.engine import settings as cfg
from src.engine.game import GameState


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
        # 隐藏调试：同时按住 S + K + B 直接进入二面（power=300）
        held = self.game.keys_held
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

        keys = self.game.keys_just_pressed
        if keys.get(pygame.K_UP, False) or keys.get(pygame.K_w, False):
            self.selected = (self.selected - 1) % len(self.options)
        if keys.get(pygame.K_DOWN, False) or keys.get(pygame.K_s, False):
            self.selected = (self.selected + 1) % len(self.options)

        if keys.get(pygame.K_RETURN, False) or keys.get(pygame.K_z, False) or keys.get(pygame.K_SPACE, False):
            self._select()

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
            from src.stages import get_stage_class
            stage = get_stage_class(1)()
            stage.setup_waves()
            self.game.switch_state(PlayingState(self.game, stage))
        elif self.options[self.selected] == "Quit":
            self.game.running = False
        elif self.options[self.selected] == "Settings":
            pass  # TODO
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
        version_text = self.game.font_small.render("v0.1.0 - Codex CLI Project", True, cfg.COLOR_DARK_GRAY)
        screen.blit(version_text, (10, cfg.SCREEN_HEIGHT - 18))


class PlayingState(GameState):
    """游戏主状态"""
    def __init__(self, game, stage, skip_title=False):
        super().__init__(game)
        self.stage = stage
        self.skip_title = skip_title
        from src.entities.bullet import BulletManager
        from src.entities.player import Player
        from src.ui.hud import HUD
        from src.systems.item_system import ItemDropManager, init_default_drop_table
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
        self.skill_manager = SkillManager()
        skills_data = self.game.global_data.get("skills", {})
        if skills_data:
            self.skill_manager.from_dict(skills_data)

        # 掉落弹窗
        self.item_popups = []
        self.power_items = []  # 红色 Power 方块掉落物
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
        self.game.stop_music()

    def update(self, dt):
        keys = self.game.keys_just_pressed
        dialogue_was_active = self.dialogue is not None

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

        # 暂停（对话期间 ESC 用于跳过对话，不触发暂停）
        if not dialogue_was_active and keys.get(pygame.K_ESCAPE, False):
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

        # 通关 处理
        if self.stage_clear:
            self.clear_timer += 1
            if keys.get(pygame.K_RETURN, False) and self.clear_timer > 60:
                from src.stages import get_next_stage_class
                next_cls = get_next_stage_class(self.stage.stage_num)
                if next_cls is not None:
                    stage = next_cls()
                    stage.setup_waves()
                    self.game.switch_state(PlayingState(self.game, stage))
                else:
                    self.game.switch_state(MenuState(self.game))
            return

        # 输入
        self.player.handle_input(self.game.keys, self.game.keys_held, self.game.keys_just_pressed)

        # Bomb（Last Spell 挑战中禁用）
        if self.player.want_bomb and self.bombs > 0 and not self.bomb_active:
            if self.stage.boss is not None and self.stage.boss.is_last_spell_active():
                self.bomb_blocked_timer = 50
            else:
                self._use_bomb()
        if self.bomb_blocked_timer > 0:
            self.bomb_blocked_timer -= 1

        # Bomb 效果
        if self.bomb_active:
            self.bomb_timer -= 1
            if self.bomb_timer <= 0:
                self.bomb_active = False

        # 更新玩家
        self.player.update(dt)

        # 射击
        if self.player.can_shoot():
            self._player_shoot()

        # 更新子弹
        self.bullet_manager.update(dt, self.player.x, self.player.y)

        # 追踪弹自动转向
        self._update_homing_bullets()

        # 掉落物下落与拾取
        self._update_power_items()

        # 更新关卡
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

        # 通关检测
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

        # 更新掉落弹窗
        for popup in self.item_popups[:]:
            popup["timer"] += 1
            if popup["timer"] > 180:
                self.item_popups.remove(popup)

    def _player_shoot(self):
        """玩家射击：按 power 升级弹幕形态（单线->两线->三线）+ 追踪弹"""
        from src.entities import bullet as bm
        power_level = self.power // 100  # 0-4

        # 主射击：单线 -> 两线 -> 三线
        px = self.player.x
        py = self.player.y - 8
        # 侧翼弹道向外倾斜，两弹道夹角 4.5 度（单侧 2.25 度）
        tilt_vx = 0.47
        tilt_vy = -11.96
        if power_level >= 2:
            # 三线：左倾、直射、右倾
            b = bm.create_player_bullet(px - 10, py, -tilt_vx, tilt_vy)
            self.bullet_manager.add_player_bullet(b)
            b = bm.create_player_bullet(px, py)
            self.bullet_manager.add_player_bullet(b)
            b = bm.create_player_bullet(px + 10, py, tilt_vx, tilt_vy)
            self.bullet_manager.add_player_bullet(b)
        elif power_level >= 1:
            # 两线：左右向外倾斜
            b = bm.create_player_bullet(px - 10, py, -tilt_vx, tilt_vy)
            self.bullet_manager.add_player_bullet(b)
            b = bm.create_player_bullet(px + 10, py, tilt_vx, tilt_vy)
            self.bullet_manager.add_player_bullet(b)
        else:
            # 单线：中间一条
            b = bm.create_player_bullet(px, py)
            self.bullet_manager.add_player_bullet(b)

        # 追踪弹：始终只有 1 列；power>=15 开始产生，射速为正常一半；
        # 伤害随 power 从正常 1/3 提升到 2/3
        if self.power >= 15:
            if not self.homing_shot_skip:
                base = cfg.BULLET_PLAYER_DAMAGE
                ratio = 1 / 3 + (1 / 3) * (self.power - 15) / (self.player.max_power - 15)
                hb = bm.create_player_bullet(px, py - 4, homing=True)
                hb.damage = round(base * ratio, 1)
                self.bullet_manager.add_player_bullet(hb)
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
        """击败敌人掉落红色 Power 方块"""
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

    def _reward_enemy_kill(self, enemy):
        """敌人被击破后的奖励结算（分数/技能经验/掉落）"""
        from src.entities.boss import Boss
        self.score += enemy.score
        self.skill_manager.add_xp("COMBAT", enemy.score // 10)
        enemy_type = type(enemy).__name__
        drops = self.item_manager.roll_drops(enemy_type)
        for item in drops:
            self.item_popups.append({"item": item, "timer": 0})
        if isinstance(enemy, Boss):
            boss_drops = self.item_manager.roll_drops("Boss")
            for item in boss_drops:
                self.item_popups.append({"item": item, "timer": 0})
        self._spawn_power_drops(enemy)

    def _use_bomb(self):
        """使用Bomb"""
        self.bombs -= 1
        self.game.global_data["bombs"] = self.bombs
        self.bomb_active = True
        self.bomb_timer = 90

        self.bullet_manager.cancel_all_enemy_bullets()

        from src.entities.boss import Boss
        for enemy in self.stage.get_active_enemies():
            if isinstance(enemy, Boss):
                # Boss 走 take_damage：尊重进场/开符免疫与符卡血量钳制
                if enemy.take_damage(500):
                    self._reward_enemy_kill(enemy)
            else:
                enemy.hp -= 500 * getattr(enemy, "resistance", 1.0)

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

        # 敌弹 vs 玩家（消弹动画中的子弹不造成伤害）
        if self.player.can_be_hit():
            for eb in self.bullet_manager.enemy_bullets[:]:
                if eb.cancel_timer > 0 or eb.harmless:
                    continue
                if eb.hits_player(self.player.x, self.player.y, self.player.hitbox_radius):
                    self._player_die()
                    break

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

        # 重置状态
        self.game_over = False
        self.stage_clear = False
        self.clear_timer = 0
        self.bomb_active = False
        self.bomb_timer = 0
        self.bomb_blocked_timer = 0
        self.item_popups.clear()
        self.power_items.clear()
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

        # 子弹
        self.bullet_manager.draw(screen, ox, oy)

        # Bomb特效（仅战斗区域）
        if self.bomb_active:
            overlay = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT), pygame.SRCALPHA)
            alpha = int(80 * (self.bomb_timer / 90))
            overlay.fill((255, 255, 255, alpha))
            screen.blit(overlay, (ox, oy))

        # 玩家
        self.player.draw(screen, ox, oy)

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