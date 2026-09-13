# 东方天空街 - 游戏主引擎
# 管理游戏主循环、状态切换、场景调度

import gc
import sys
import pygame
import os
from src.engine import display, hires, painter
from src.engine.settings import *
from src.engine import settings as cfg
from src.engine import pseudo3d
from src.engine.fallback_font import FallbackFont

# DPI 感知与 GPU 缩放的 SDL 环境变量必须在 pygame.init() 之前设置
display.configure_environment()


class Game:
    def __init__(self):
        # 先声明 DPI 感知再初始化 SDL：否则高 DPI 缩放下画面会被系统二次拉伸
        display.enable_dpi_awareness()
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)
        # 分代 GC：gen2 扫描一次实测 4~8ms，而这类扫描最容易落在「一帧里分配
        # 最多」的帧上——比如开符那一帧（符卡背景重建）。这里只放宽 gen2 的
        # 触发间隔（gen0/gen1 保持默认，短命循环垃圾照常回收），实测开符帧
        # 从 17~20ms 降回 13ms。
        gc.set_threshold(700, 10, 100)
        # 显示设置（输出分辨率 / 缩放模式 / 全屏）来自 config.json
        self.user_config = load_user_config()
        self.resolution_index = int(self.user_config.get("resolution_index",
                                                         DEFAULT_RESOLUTION_INDEX))
        self.scale_mode = self.user_config.get("scale_mode", DEFAULT_SCALE_MODE)
        self.fullscreen = bool(self.user_config.get("fullscreen", DEFAULT_FULLSCREEN))
        self.render_scale_index = int(self.user_config.get(
            "render_scale_index", DEFAULT_RENDER_SCALE_INDEX))
        self.presenter = None
        self.dst_rect = pygame.Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT)
        self.display_scale = 1.0
        # Windows 下禁用本窗口的输入法(IME)，避免按 Shift 切换输入法后按键被 IME 吞掉
        self._ime_context = None
        self._create_display()
        self.clock = pygame.time.Clock()
        self.running = True
        self.dt = 0.0
        self._speed_accum = 0.0     # 流速子步进累计器（不足 1 步时保留到下一帧）
        self._speed_notice_until = 0 # 流速变化提示的显示截止时间（真实毫秒）

        # 音频初始化（无音频设备时静默降级）
        self.audio_ok = False
        try:
            pygame.mixer.init()
            self.audio_ok = True
        except Exception as e:
            print(f"[Audio] Mixer init failed, audio disabled: {e}")

        # 音量（config.json 已在建立窗口前读取）
        self.music_volume = float(self.user_config.get("music_volume", DEFAULT_MUSIC_VOLUME))
        if self.audio_ok:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except Exception:
                pass

        # 音效（从 config.json 读取音量并预加载，无音频设备时静默降级）
        self.sfx_volume = float(self.user_config.get("sfx_volume", DEFAULT_SFX_VOLUME))
        # 全局游戏流速（0.25x ~ 2.0x，物理/弹幕/关卡时间轴整体缩放）
        self.game_speed = max(GAME_SPEED_MIN, min(GAME_SPEED_MAX,
                                                  float(self.user_config.get("game_speed",
                                                                              DEFAULT_GAME_SPEED))))
        # Boss 立绘套组（new / another，可在设置界面切换）
        cfg.set_boss_art(self.user_config.get("boss_art", BOSS_ART_DEFAULT))
        self.boss_art = cfg.get_boss_art()
        self.sfx_cache = {}
        if self.audio_ok:
            try:
                for _name, _path in SFX_PATHS.items():
                    if os.path.exists(_path):
                        _sfx = pygame.mixer.Sound(_path)
                        _sfx.set_volume(self.sfx_volume)
                        self.sfx_cache[_name] = _sfx
            except Exception as e:
                print(f"[Audio] SFX load failed, audio disabled: {e}")

        # 音乐自然播放结束的事件（用于Boss战开场曲播完后切换循环曲）
        self.music_end_event = pygame.USEREVENT + 1

        # 加载字体
        # 加载字体（font1 缺中文字形时自动回退到 font2）
        font_path = os.path.join(ASSETS_DIR, "fonts", "font1.ttf")
        fallback_path = os.path.join(ASSETS_DIR, "fonts", "font2.otf")
        self.font_small = FallbackFont(font_path, fallback_path, 16)
        self.font_medium = FallbackFont(font_path, fallback_path, 24)
        self.font_large = FallbackFont(font_path, fallback_path, 36)
        self.font_huge = FallbackFont(font_path, fallback_path, 48)

        # 输入
        self.keys = {}
        self.keys_just_pressed = {}
        self.keys_held = {}
        # 鼠标输入（终端破解 GUI 等用）
        self.mouse_pos = (0, 0)
        self.mouse_buttons_just_pressed = {}
        self.mouse_buttons_held = {}

        # 游戏状态栈
        self.states = []
        self.current_state = None

        # 当前播放的音乐路径（用于判断是否需要切换，避免同一曲目重头播放）
        self.current_music_path = None

        # 全局数据（跨场景共享）
        self.global_data = {
            "score": 0,
            "lives": PLAYER_START_LIVES,
            "bombs": PLAYER_START_BOMBS,
            "power": 0,
            "graze": 0,
            "stage": 1,
            "difficulty": "EASY",
            # Skyblock 数据
            "skills": {
                "COMBAT": {"xp": 0, "level": 0},
                "MINING": {"xp": 0, "level": 0},
                "FARMING": {"xp": 0, "level": 0},
                "FORAGING": {"xp": 0, "level": 0},
                "FISHING": {"xp": 0, "level": 0},
                "ENCHANTING": {"xp": 0, "level": 0},
                "ALCHEMY": {"xp": 0, "level": 0},
            },
            "coins": 0,
            "inventory": [],
            "equipment": {},
            "reforges": {},
            "active_effects": [],
        }

    # --- 输入法(IME)处理 ---

    def _disable_ime(self):
        """禁用本窗口的输入法(IME)，防止 Shift 切换输入法后按键失效"""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = pygame.display.get_wm_info().get("window")
            if not hwnd:
                return
            imm32 = ctypes.windll.imm32
            imm32.ImmAssociateContext.argtypes = [wintypes.HWND, wintypes.HANDLE]
            imm32.ImmAssociateContext.restype = wintypes.HANDLE
            # 将窗口的输入法关联设为 NULL，游戏窗口内不再使用输入法
            self._ime_context = imm32.ImmAssociateContext(hwnd, None)
        except Exception as e:
            print(f"[IME] Failed to disable IME: {e}")

    def _restore_ime(self):
        """退出前恢复输入法上下文，避免影响系统其它窗口"""
        if sys.platform != "win32" or self._ime_context is None:
            return
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = pygame.display.get_wm_info().get("window")
            if not hwnd:
                return
            imm32 = ctypes.windll.imm32
            imm32.ImmAssociateContext.argtypes = [wintypes.HWND, wintypes.HANDLE]
            imm32.ImmAssociateContext.restype = wintypes.HANDLE
            imm32.ImmAssociateContext(hwnd, self._ime_context)
        except Exception as e:
            print(f"[IME] Failed to restore IME: {e}")

    # --- 音乐控制 ---

    def play_music(self, music_path, loops=-1):
        """播放背景音乐，默认无限循环"""
        if not self.audio_ok:
            return False
        try:
            if not os.path.exists(music_path):
                print(f"[Audio] Music file not found: {music_path}")
                return False
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.set_endevent(self.music_end_event)
            pygame.mixer.music.play(loops)
            self.current_music_path = music_path
            return True
        except Exception as e:
            print(f"[Audio] Failed to play music {music_path}: {e}")
            return False

    def stop_music(self):
        """停止背景音乐"""
        self.current_music_path = None
        if self.audio_ok:
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass

    def music_busy(self):
        """背景音乐是否正在播放"""
        if not self.audio_ok:
            return False
        try:
            return bool(pygame.mixer.music.get_busy())
        except Exception:
            return False

    def set_music_volume(self, volume):
        """设置背景音乐音量（0.0 ~ 1.0）并保存配置"""
        self.music_volume = max(0.0, min(1.0, float(volume)))
        self.user_config["music_volume"] = self.music_volume
        save_user_config(self.user_config)
        if self.audio_ok:
            try:
                pygame.mixer.music.set_volume(self.music_volume)
            except Exception:
                pass

    # --- 音效控制 ---

    def play_sfx(self, name, volume=None):
        """播放一个预加载音效；volume 为 None 时使用全局 sfx_volume"""
        if not self.audio_ok:
            return False
        sfx = self.sfx_cache.get(name)
        if sfx is None:
            return False
        try:
            if volume is None:
                sfx.set_volume(self.sfx_volume)
            else:
                sfx.set_volume(max(0.0, min(1.0, float(volume))))
            sfx.play()
            return True
        except Exception as e:
            print(f"[Audio] Failed to play sfx {name}: {e}")
            return False

    def set_sfx_volume(self, volume):
        """设置音效音量（0.0 ~ 1.0）并保存配置"""
        self.sfx_volume = max(0.0, min(1.0, float(volume)))
        self.user_config["sfx_volume"] = self.sfx_volume
        save_user_config(self.user_config)
        if self.audio_ok:
            try:
                for sfx in self.sfx_cache.values():
                    sfx.set_volume(self.sfx_volume)
            except Exception:
                pass

    # --- 全局游戏流速 ---

    def set_game_speed(self, speed):
        """设置全局游戏流速（0.25x ~ 2.0x）并保存配置"""
        speed = round(max(GAME_SPEED_MIN, min(GAME_SPEED_MAX, float(speed))), 2)
        if abs(speed - self.game_speed) < 1e-9:
            return
        self.game_speed = speed
        self.user_config["game_speed"] = speed
        save_user_config(self.user_config)
        self._speed_notice_until = pygame.time.get_ticks() + 1500

    def adjust_game_speed(self, delta):
        """按步长调节全局游戏流速"""
        self.set_game_speed(self.game_speed + delta)

    def reset_game_speed(self):
        """恢复默认 1.0x 流速"""
        self.set_game_speed(DEFAULT_GAME_SPEED)

    # --- Boss 立绘套组 ---

    def set_boss_art(self, name):
        """切换 Boss 立绘套组（new / another）并保存配置"""
        cfg.set_boss_art(name)
        self.boss_art = cfg.get_boss_art()
        self.user_config["boss_art"] = self.boss_art
        save_user_config(self.user_config)
        return self.boss_art

    def _position_window(self, fullscreen):
        """Place the borderless fullscreen window correctly on Windows."""
        if sys.platform != "win32":
            return
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = pygame.display.get_wm_info().get("window")
            if not hwnd:
                return
            user32 = ctypes.windll.user32
            user32.SetWindowPos.argtypes = [
                wintypes.HWND, wintypes.HWND,
                ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_uint,
            ]
            user32.SetWindowPos.restype = wintypes.BOOL
            if fullscreen:
                user32.SetWindowPos(hwnd, -1, 0, 0, 0, 0, 0x0001 | 0x0010)
                return
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            outer = wintypes.RECT()
            client = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(outer))
            user32.GetClientRect(hwnd, ctypes.byref(client))
            client_w = client.right - client.left
            client_h = client.bottom - client.top
            border_x = client.left - outer.left
            border_y = client.top - outer.top
            x = (screen_w - client_w) // 2 - border_x
            y = (screen_h - client_h) // 2 - border_y
            user32.SetWindowPos(hwnd, -2, x, y, 0, 0, 0x0001 | 0x0010)
        except Exception:
            pass

    # --- 显示：输出分辨率 / 缩放模式 / 全屏 ---

    def _window_size(self):
        """窗口模式下的窗口尺寸（物理像素）：取设置的分辨率并限制在桌面范围内"""
        want_w, want_h = RESOLUTIONS[self.resolution_index]
        desk_w, desk_h = display.get_desktop_size()
        if desk_w > 0 and desk_h > 0:
            want_w = min(want_w, desk_w)
            want_h = min(want_h, desk_h)
        return max(SCREEN_WIDTH, want_w), max(SCREEN_HEIGHT, want_h)

    def _create_display(self):
        """建立窗口与逻辑画布，并尝试启用 GPU 呈现（失败则回退 CPU 缩放）"""
        # 先释放旧窗口的呈现资源再重建窗口：等下面重新赋值时才回收的话，
        # 旧 texture/renderer 的析构会发生在 SDL 销毁窗口之后，可能误伤
        # 新窗口刚创建、恰好复用同一地址的渲染器（表现为 present 时报 texture 无效）
        self.presenter = None
        flags = pygame.SCALED | (pygame.FULLSCREEN if self.fullscreen else 0)
        try:
            self.window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        except pygame.error as e:
            # 个别后端不支持 SCALED：退回普通窗口
            print(f"[Display] SCALED window failed, fallback to plain window: {e}")
            self.window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        # 游戏始终绘制到 960x720 逻辑画布，缩放只发生在呈现阶段。
        # 画布带 alpha：走 GPU 地面时，战斗区要在这一层上抠空让显卡画的地面透出来
        # 画布另外挂一张「渲染倍率倍」的高分辨率图层，承接文字/立绘/面板（见 hires.py）
        # 画布即统一绘制入口 Painter：既有 screen.blit / pygame.draw 照旧可用，
        # 新增的 fill_gpu / blit_gpu 在有显卡时改由显卡按渲染倍率原生绘制
        self.screen = painter.Painter.create((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.presenter = display.GpuPresenter((SCREEN_WIDTH, SCREEN_HEIGHT))
        if not self.presenter.ok:
            # CPU 缩放路径需要窗口本身就是目标尺寸（与旧版全屏做法一致）
            self.presenter = None
            self.window = pygame.display.set_mode(self._window_size())
        if not self.fullscreen:
            self._apply_window_size()
            self._position_window(False)
        self._update_present_rect()
        self._init_floor_scale()
        self._disable_ime()

    def _apply_window_size(self):
        """窗口模式：把窗口调整到设置的分辨率（物理像素）"""
        if self.fullscreen or self.presenter is None:
            return
        try:
            from pygame._sdl2 import video as video_module
            video_module.Window.from_display_module().size = self._window_size()
        except Exception as e:
            print(f"[Display] Resize window failed: {e}")

    def _update_present_rect(self):
        """重新计算画面在窗口中的目标矩形与缩放倍数"""
        try:
            win_size = pygame.display.get_window_size()
        except Exception:
            win_size = self.window.get_size()
        self.dst_rect, self.display_scale = display.present_rect(
            win_size, (SCREEN_WIDTH, SCREEN_HEIGHT), self.scale_mode)

    # --- 渲染倍率（分辨率无关图层：伪3D 地面）---

    @property
    def render_scale(self):
        """当前生效的地面渲染倍率（无 GPU 呈现时退回 1x）"""
        if self.presenter is None:
            return 1
        return RENDER_SCALES[self.render_scale_index]

    def _init_floor_scale(self):
        """把渲染倍率交给伪3D 地面与高分辨率图层。

        GPU 呈现不可用时退回 1x——CPU 只能在 1x 画布上绘制，倍率提高反而看不清。
        """
        gpu = self.presenter is not None
        pseudo3d.Pseudo3DFloor.gpu_active = gpu
        pseudo3d.Pseudo3DFloor.default_scale = self.render_scale
        # 文字/立绘/面板的高分辨率图层（同一倍率；无 GPU 时被压回 1x）
        hires.set_scale(self.render_scale)
        self.screen.set_hires_factor(hires.scale())

    def apply_render_scale(self, stage):
        """把当前渲染倍率应用到关卡里已有的伪3D 地面（改设置时用）"""
        if stage is None or not hasattr(stage, "iter_floors"):
            return
        scale = self.render_scale
        for floor in stage.iter_floors():
            floor.set_scale(scale)

    def set_render_scale(self, index):
        """设置渲染倍率（RENDER_SCALES 下标）：即时应用到所有在跑的关卡"""
        index = max(0, min(len(RENDER_SCALES) - 1, int(index)))
        if index == self.render_scale_index:
            return
        self.render_scale_index = index
        self.user_config["render_scale_index"] = index
        save_user_config(self.user_config)
        self._init_floor_scale()
        for state in [self.current_state] + list(self.states):
            self.apply_render_scale(getattr(state, "stage", None))

    def _battle_dst_rect(self):
        """战斗区在窗口中的目标矩形（按呈现倍数换算），供 GPU 直绘地面使用"""
        scale = self.display_scale
        return pygame.Rect(
            int(round(self.dst_rect.x + BATTLE_OFFSET_X * scale)),
            int(round(self.dst_rect.y + BATTLE_OFFSET_Y * scale)),
            max(1, int(round(BATTLE_AREA_WIDTH * scale))),
            max(1, int(round(BATTLE_AREA_HEIGHT * scale))))

    def display_status_text(self):
        """设置界面用：当前生效的输出尺寸与缩放倍数"""
        try:
            win_w, win_h = pygame.display.get_window_size()
        except Exception:
            win_w, win_h = self.window.get_size()
        mode = SCALE_MODE_LABELS.get(self.scale_mode, self.scale_mode)
        floor = RENDER_SCALE_LABELS[self.render_scale_index] if self.presenter else "1x(无GPU)"
        return (f"输出 {win_w}×{win_h}    画面 {self.dst_rect.width}×{self.dst_rect.height}"
                f"（{self.display_scale:.2f}×，{mode}）    地面 {floor}")

    def set_resolution(self, index):
        """设置输出分辨率（RESOLUTIONS 下标），窗口模式下立即生效"""
        index = max(0, min(len(RESOLUTIONS) - 1, int(index)))
        if index == self.resolution_index:
            return
        self.resolution_index = index
        self.user_config["resolution_index"] = index
        save_user_config(self.user_config)
        self._apply_window_size()
        self._update_present_rect()

    def set_scale_mode(self, mode):
        """设置缩放模式：integer=整数倍 / fill=等比填充"""
        if mode not in SCALE_MODES or mode == self.scale_mode:
            return
        self.scale_mode = mode
        self.user_config["scale_mode"] = mode
        save_user_config(self.user_config)
        self._update_present_rect()

    def set_fullscreen(self, on):
        """切换窗口 / 无边框全屏（保持分辨率与缩放模式）"""
        on = bool(on)
        if on != self.fullscreen:
            self.toggle_fullscreen()

    def toggle_fullscreen(self):
        """F11：窗口 / 无边框全屏（保持分辨率与缩放模式）"""
        self.fullscreen = not self.fullscreen
        self.user_config["fullscreen"] = self.fullscreen
        save_user_config(self.user_config)
        self._create_display()

    def _cpu_present(self):
        """回退路径：CPU 缩放后居中贴到窗口（仅 GPU 呈现不可用时使用）"""
        win_w, win_h = self.window.get_size()
        if (win_w, win_h) == (SCREEN_WIDTH, SCREEN_HEIGHT):
            self.window.blit(self.screen, (0, 0))
            return
        if self.scale_mode == "integer":
            scaled = pygame.transform.scale(self.screen, self.dst_rect.size)
        else:
            scaled = pygame.transform.smoothscale(self.screen, self.dst_rect.size)
        self.window.fill((0, 0, 0))
        self.window.blit(scaled, self.dst_rect.topleft)

    def run(self):
        """主循环"""
        while self.running:
            self.dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update()
            self._draw()
            if self.presenter is None:
                # GPU 呈现路径已在 presenter.present() 内部提交画面
                pygame.display.flip()

        self.quit()

    def _unscale_mouse(self, pos):
        """把窗口坐标换算回 960x720 逻辑坐标（画面居中且可能带黑边）"""
        mx, my = pos
        scale = self.display_scale or 1.0
        if scale == 1.0:
            return (mx - self.dst_rect.x, my - self.dst_rect.y)
        return ((mx - self.dst_rect.x) / scale, (my - self.dst_rect.y) / scale)
    def _handle_events(self):
        """处理输入事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.keys_just_pressed[event.key] = True
                self.keys_held[event.key] = True
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
                elif event.key == pygame.K_F8:
                    self.adjust_game_speed(-GAME_SPEED_STEP)
                elif event.key == pygame.K_F9:
                    self.adjust_game_speed(GAME_SPEED_STEP)
                elif event.key == pygame.K_F10:
                    self.reset_game_speed()
            elif event.type == pygame.KEYUP:
                self.keys_held[event.key] = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_buttons_just_pressed[event.button] = True
                self.mouse_buttons_held[event.button] = True
            elif event.type == pygame.MOUSEBUTTONUP:
                self.mouse_buttons_held[event.button] = False
            elif event.type == self.music_end_event:
                # 背景音乐自然播放结束（无限循环曲不会触发）
                if self.current_state:
                    self.current_state.on_music_end()

        self.keys = pygame.key.get_pressed()
        self.mouse_pos = self._unscale_mouse(pygame.mouse.get_pos())

    def mouse_hover(self, rect):
        """鼠标是否悬停在 pygame.Rect 上（供各界面鼠标交互使用）"""
        try:
            return rect.collidepoint(self.mouse_pos)
        except AttributeError:
            return False

    def mouse_clicked(self, button=1):
        """鼠标按键是否刚刚按下（默认左键 1）"""
        return bool(self.mouse_buttons_just_pressed.get(button))

    def wheel_direction(self):
        """返回鼠标滚轮方向：上= -1，下= +1，无滚动= 0"""
        up = bool(self.mouse_buttons_just_pressed.get(4))
        down = bool(self.mouse_buttons_just_pressed.get(5))
        return -1 if up else (1 if down else 0)

    def _update(self):
        """按 game_speed 累计执行逻辑子步；一次性输入只在首个子步生效"""
        if not self.current_state:
            self.keys_just_pressed = {}
            self.mouse_buttons_just_pressed = {}
            return

        self._speed_accum += self.game_speed
        steps = int(self._speed_accum)
        if steps <= 0:
            return
        self._speed_accum -= steps

        # 单帧最多追赶 4 个逻辑步，避免偶发卡顿后无限追帧
        if steps > 4:
            steps = 4
            self._speed_accum = min(self._speed_accum, 1.0)

        for i in range(steps):
            state = self.current_state
            state.update(self.dt)
            if self.current_state is not state:
                # 逻辑步内发生状态切换后立即停止剩余子步，
                # 避免新状态在同一渲染帧被额外更新
                self._speed_accum = 0.0
                break
            if i < steps - 1:
                # 高速子步之间清除一次性输入，避免炸弹/技能等重复触发
                self.keys_just_pressed = {}
                self.mouse_buttons_just_pressed = {}

        self.keys_just_pressed = {}
        self.mouse_buttons_just_pressed = {}

    def _draw(self):
        # 帧首清掉上一帧高分辨率图层占用的区域（脏矩形）
        self.screen.begin_frame()
        # 帧首重置本帧的显卡绘制指令（无 GPU 呈现时不收集）
        self.screen.begin_gpu_frame(self.render_scale, self.presenter is not None)
        if self.current_state:
            self.current_state.draw(self.screen)
        # 流速变化提示（真实时间，短暂显示）
        if pygame.time.get_ticks() < self._speed_notice_until:
            text = f"游戏速度 {format_game_speed(self.game_speed)}"
            surf = self.font_small.render(text, True, COLOR_YELLOW)
            x, y = 30, SCREEN_HEIGHT - 52
            bg = pygame.Surface((surf.get_width() + 16, surf.get_height() + 8),
                                pygame.SRCALPHA)
            bg.fill((0, 0, 0, 170))
            self.screen.blit(bg, (x - 8, y - 4))
            self.screen.blit(surf, (x, y))
        # 本帧要由显卡原生绘制的地面（关卡绘制时登记，战斗区已在帧上抠空）
        floor = pseudo3d.take_gpu_floor()
        # 本帧高分辨率图层需要上传的区域（只画了很小一块时省掉整幅上传）
        ui_area = self.screen.end_frame()
        if self.presenter is not None:
            # GPU 缩放呈现（含黑边），renderer 内部已完成 present
            self.presenter.present(self.screen, self.dst_rect, floor,
                                   self._battle_dst_rect() if floor is not None else None,
                                   ui=self.screen.hi, ui_area=ui_area,
                                   gpu_ops=self.screen.gpu_ops(),
                                   layer_size=self.screen.hires_size())
        else:
            self._cpu_present()

    def push_state(self, state):
        """压入新状态"""
        if self.current_state:
            self.current_state.pause()
            self.states.append(self.current_state)
        self.current_state = state
        state.enter(self)

    def pop_state(self):
        """弹出当前状态"""
        if self.current_state:
            self.current_state.exit()
        if self.states:
            self.current_state = self.states.pop()
            self.current_state.resume()
        else:
            self.current_state = None

    def switch_state(self, state):
        """切换状态（替换当前）"""
        if self.current_state:
            self.current_state.exit()
        self.current_state = state
        state.enter(self)

    def quit(self):
        self._restore_ime()
        pygame.quit()
        sys.exit()

class GameState:
    """游戏状态基类"""
    def __init__(self, game):
        self.game = game

    def on_music_end(self):
        """背景音乐自然播放结束回调（子类可覆写）"""
        pass

    def enter(self, game):
        pass

    def exit(self):
        pass

    def pause(self):
        pass

    def resume(self):
        pass

    def update(self, dt):
        pass

    def draw(self, screen):
        pass
