# 东方天空街 - 游戏主引擎
# 管理游戏主循环、状态切换、场景调度

import sys
import pygame
import os
from src.engine.settings import *
from src.engine.fallback_font import FallbackFont


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(GAME_TITLE)
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.window = self.screen  # ??????????????????
        # Windows 下禁用本窗口的输入法(IME)，避免按 Shift 切换输入法后按键被 IME 吞掉
        self._ime_context = None
        self._disable_ime()
        self.fullscreen = False  # F11 切换全屏
        self.clock = pygame.time.Clock()
        self.running = True
        self.dt = 0.0

        # 音频初始化（无音频设备时静默降级）
        self.audio_ok = False
        try:
            pygame.mixer.init()
            self.audio_ok = True
        except Exception as e:
            print(f"[Audio] Mixer init failed, audio disabled: {e}")

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
            "difficulty": "NORMAL",
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
            "inventory": [],
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

    def toggle_fullscreen(self):
        """F11????? / ????"""
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            # ??????????????????????? 960x720 ?????
            # ?? SCALED ???????????????????
            try:
                self.window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                # ????????? 960x720??????? _draw ??????
                self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            except pygame.error as e:
                print(f"[Display] Fullscreen failed, stay windowed: {e}")
                self.fullscreen = False
                self.window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
                self.screen = self.window
        else:
            self.window = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            self.screen = self.window

        # ??????????????
        self._disable_ime()
    def run(self):
        """主循环"""
        while self.running:
            self.dt = self.clock.tick(FPS) / 1000.0
            self._handle_events()
            self._update()
            self._draw()
            pygame.display.flip()

        self.quit()

    def _handle_events(self):
        """处理输入事件"""
        self.keys_just_pressed = {}
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.keys_just_pressed[event.key] = True
                self.keys_held[event.key] = True
                if event.key == pygame.K_F11:
                    self.toggle_fullscreen()
            elif event.type == pygame.KEYUP:
                self.keys_held[event.key] = False
            elif event.type == self.music_end_event:
                # 背景音乐自然播放结束（无限循环曲不会触发）
                if self.current_state:
                    self.current_state.on_music_end()

        self.keys = pygame.key.get_pressed()

    def _update(self):
        if self.current_state:
            self.current_state.update(self.dt)

    def _draw(self):
        if self.current_state:
            self.current_state.draw(self.screen)
        if self.screen is not self.window:
            # ?????????????????????????????
            win_w, win_h = self.window.get_size()
            scale = min(win_w / SCREEN_WIDTH, win_h / SCREEN_HEIGHT)
            new_w = max(1, round(SCREEN_WIDTH * scale))
            new_h = max(1, round(SCREEN_HEIGHT * scale))
            scaled = pygame.transform.smoothscale(self.screen, (new_w, new_h))
            self.window.fill((0, 0, 0))
            self.window.blit(scaled, ((win_w - new_w) // 2, (win_h - new_h) // 2))
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

