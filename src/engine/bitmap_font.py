# 自定义位图字体渲染器
# 加载 .bin 格式的 raw bitmap font (256x256, 16x16 chars)
# 用于替换默认 pygame 字体

import pygame
import os
from src.engine import settings as cfg


class BitmapFont:
    """位图字体 - 从 raw .bin 文件加载 256x256 字符表"""
    
    CHAR_COLS = 16  # 每行16个字符
    CHAR_ROWS = 16  # 每列16个字符
    CHAR_W = 16     # 每个字符宽16像素
    CHAR_H = 16     # 每个字符高16像素
    ATLAS_SIZE = 256
    
    def __init__(self, font_path=None):
        self.atlas = None
        self.char_surfaces = {}  # 缓存渲染后的字符
        
        if font_path and os.path.exists(font_path):
            self._load_font(font_path)
        else:
            self._create_default()
    
    def _load_font(self, path):
        """加载 raw bitmap font"""
        try:
            with open(path, 'rb') as f:
                raw_data = f.read()
            
            if len(raw_data) < self.ATLAS_SIZE * self.ATLAS_SIZE:
                raise ValueError(f"Font file too small: {len(raw_data)} bytes")
            
            # 创建灰度 Surface
            self.atlas = pygame.Surface((self.ATLAS_SIZE, self.ATLAS_SIZE), depth=8)
            
            # 填充像素数据
            for y in range(self.ATLAS_SIZE):
                for x in range(self.ATLAS_SIZE):
                    idx = y * self.ATLAS_SIZE + x
                    if idx < len(raw_data):
                        brightness = raw_data[idx]
                        self.atlas.set_at((x, y), (brightness, brightness, brightness))
            
            print(f"Bitmap font loaded: {path} ({len(raw_data)} bytes)")
        except Exception as e:
            print(f"Failed to load font: {e}, using default")
            self._create_default()
    
    def _create_default(self):
        """创建默认字体（简单的8x8等宽）"""
        self.atlas = pygame.Surface((self.ATLAS_SIZE, self.ATLAS_SIZE))
        self.atlas.fill((0, 0, 0))
        # 使用 pygame 默认字体生成字符表
        default_font = pygame.font.Font(None, 14)
        for i in range(256):
            col = i % self.CHAR_COLS
            row = i // self.CHAR_COLS
            char = chr(i) if 32 <= i < 127 else ' '
            char_surf = default_font.render(char, True, (255, 255, 255))
            cx = col * self.CHAR_W + (self.CHAR_W - char_surf.get_width()) // 2
            cy = row * self.CHAR_H + (self.CHAR_H - char_surf.get_height()) // 2
            self.atlas.blit(char_surf, (cx, cy))
    
    def get_char_rect(self, char_code):
        """获取字符在atlas中的矩形区域"""
        col = char_code % self.CHAR_COLS
        row = char_code // self.CHAR_ROWS
        return pygame.Rect(col * self.CHAR_W, row * self.CHAR_H, self.CHAR_W, self.CHAR_H)
    
    def render_char(self, char, color, scale=1):
        """渲染单个字符"""
        char_code = ord(char)
        if char_code > 255:
            char_code = 63  # '?' fallback
        
        cache_key = (char_code, color, scale)
        if cache_key in self.char_surfaces:
            return self.char_surfaces[cache_key]
        
        src_rect = self.get_char_rect(char_code)
        
        if scale == 1:
            char_surf = pygame.Surface((self.CHAR_W, self.CHAR_H), pygame.SRCALPHA)
        else:
            char_surf = pygame.Surface((self.CHAR_W * scale, self.CHAR_H * scale), pygame.SRCALPHA)
        
        # 提取字符像素
        for y in range(self.CHAR_H):
            for x in range(self.CHAR_W):
                pixel_color = self.atlas.get_at((src_rect.x + x, src_rect.y + y))
                brightness = pixel_color[0]  # 灰度值
                if brightness > 20:  # 阈值过滤
                    alpha = brightness
                    r = min(255, int(color[0] * brightness / 255))
                    g = min(255, int(color[1] * brightness / 255))
                    b = min(255, int(color[2] * brightness / 255))
                    
                    if scale == 1:
                        char_surf.set_at((x, y), (r, g, b, alpha))
                    else:
                        sx = x * scale
                        sy = y * scale
                        for dy in range(scale):
                            for dx in range(scale):
                                char_surf.set_at((sx + dx, sy + dy), (r, g, b, alpha))
        
        self.char_surfaces[cache_key] = char_surf
        return char_surf
    
    def render(self, text, color, size=16):
        """渲染文本，返回 Surface。
        size: 目标字符像素大小，用于计算缩放"""
        if not text:
            return pygame.Surface((0, 0), pygame.SRCALPHA)
        
        scale = max(1, size // self.CHAR_H)
        
        lines = text.split('\n')
        line_height = self.CHAR_H * scale
        total_width = max(sum(self._char_width(ord(c), scale) for c in line) for line in lines)
        total_height = line_height * len(lines)
        
        if total_width == 0 or total_height == 0:
            return pygame.Surface((1, 1), pygame.SRCALPHA)
        
        surf = pygame.Surface((total_width, total_height), pygame.SRCALPHA)
        
        y_offset = 0
        for line in lines:
            x_offset = 0
            for char in line:
                char_surf = self.render_char(char, color, scale)
                surf.blit(char_surf, (x_offset, y_offset))
                x_offset += self._char_width(ord(char), scale)
            y_offset += line_height
        
        return surf
    
    def _char_width(self, char_code, scale):
        """计算字符宽度（自动裁剪空白边）"""
        return self.CHAR_W * scale  # 等宽字体
    
    def size(self, text, size=16):
        """返回渲染后的文本尺寸"""
        surf = self.render(text, (255, 255, 255), size)
        return (surf.get_width(), surf.get_height())
    
    def clear_cache(self):
        self.char_surfaces.clear()
