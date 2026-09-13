# -*- coding: utf-8 -*-
# 字体回退：主字体缺失的字形（如中文字符）自动改用备用字体渲染
#
# 同时负责「高分辨率文字」：按「逻辑字号 x 渲染倍率」渲染，真实像素是逻辑尺寸的
# 倍率倍，但度量接口（get_width / get_size / size / get_height ...）一律回报逻辑
# 尺寸 —— 既有的居中 / 右对齐 / 底板尺寸 / 换行计算因此都不用改。
# 渲染结果按 (文本, 颜色, 底背) 缓存（见 settings 的渲染倍率设置与 hires.version）。

import struct

import pygame

from src.engine import hires

# 文字缓存条数上限：HUD 数字每帧都在变，不设上限会一直涨
_TEXT_CACHE_LIMIT = 400
# 主/备字体选择缓存的条数上限（键是整段文本）
_PICK_CACHE_LIMIT = 1024
# 字体支持的码点集合：与字号无关，按文件路径缓存一次
_COVERED_CACHE = {}


def _covered_codepoints(font_path):
    """解析 TrueType/OpenType 字体的 cmap 表，返回该字体实际支持的码点集合"""
    cached = _COVERED_CACHE.get(font_path)
    if cached is not None:
        return cached
    covered = _parse_covered_codepoints(font_path)
    _COVERED_CACHE[font_path] = covered
    return covered


def _parse_covered_codepoints(font_path):
    try:
        with open(font_path, "rb") as f:
            data = f.read()
    except OSError:
        return set()

    if len(data) < 12:
        return set()

    num_tables = struct.unpack_from(">H", data, 4)[0]
    cmap_offset = None
    for i in range(num_tables):
        rec = 12 + i * 16
        if rec + 16 > len(data):
            break
        if data[rec:rec + 4] == b"cmap":
            cmap_offset = struct.unpack_from(">I", data, rec + 8)[0]
            break
    if cmap_offset is None or cmap_offset + 4 > len(data):
        return set()

    codepoints = set()
    num_subtables = struct.unpack_from(">H", data, cmap_offset + 2)[0]
    for i in range(num_subtables):
        rec = cmap_offset + 4 + i * 8
        if rec + 8 > len(data):
            break
        sub = cmap_offset + struct.unpack_from(">I", data, rec + 4)[0]
        if sub + 2 > len(data):
            continue
        fmt = struct.unpack_from(">H", data, sub)[0]
        if fmt == 4:
            codepoints |= _cmap_format4(data, sub)
        elif fmt == 12:
            codepoints |= _cmap_format12(data, sub)
    return codepoints


def _cmap_format4(data, sub):
    """解析 format 4（BMP）子表"""
    if sub + 16 > len(data):
        return set()
    seg_count_x2 = struct.unpack_from(">H", data, sub + 6)[0]
    seg_count = seg_count_x2 // 2
    end_codes = struct.unpack_from(">%dH" % seg_count, data, sub + 14)
    start_off = sub + 14 + seg_count_x2 + 2
    start_codes = struct.unpack_from(">%dH" % seg_count, data, start_off)
    delta_off = start_off + seg_count_x2
    deltas = struct.unpack_from(">%dh" % seg_count, data, delta_off)
    range_off = delta_off + seg_count_x2
    ranges = struct.unpack_from(">%dH" % seg_count, data, range_off)

    codepoints = set()
    for i in range(seg_count):
        start = start_codes[i]
        end = end_codes[i]
        if start > end:
            continue
        for cp in range(start, end + 1):
            if ranges[i] == 0:
                glyph_id = (cp + deltas[i]) & 0xFFFF
            else:
                addr = range_off + i * 2 + ranges[i] + (cp - start) * 2
                if addr + 2 > len(data):
                    continue
                glyph_id = struct.unpack_from(">H", data, addr)[0]
            if glyph_id != 0:
                codepoints.add(cp)
    return codepoints


def _cmap_format12(data, sub):
    """解析 format 12（全 Unicode）子表"""
    if sub + 16 > len(data):
        return set()
    n_groups = struct.unpack_from(">I", data, sub + 12)[0]
    codepoints = set()
    for i in range(n_groups):
        off = sub + 16 + i * 12
        if off + 12 > len(data):
            break
        start, end, start_glyph = struct.unpack_from(">III", data, off)
        if start_glyph == 0 or end - start > 1000000:
            continue
        codepoints.update(range(start, end + 1))
    return codepoints


class FallbackFont:
    """优先使用主字体；字符串含主字体不支持的字符时整体改用备用字体渲染

    按 hires.scale() 渲染高分辨率文字；倍率变化时自动重建字体与缓存。
    """

    def __init__(self, primary_path, fallback_path, size):
        self.primary_path = primary_path
        self.fallback_path = fallback_path
        self.logical_size = int(size)
        self._covered = _covered_codepoints(primary_path)
        self._scale = 0
        self._bold = False
        self._italic = False
        self._underline = False
        self._build(1)

    # --- 倍率 ---

    def _build(self, factor):
        factor = max(1, int(factor))
        self._scale = factor
        size = self.logical_size * factor
        self.primary = pygame.font.Font(self.primary_path, size)
        self.fallback = pygame.font.Font(self.fallback_path, size)
        for font in (self.primary, self.fallback):
            if self._bold:
                font.set_bold(True)
            if self._italic:
                font.set_italic(True)
            if self._underline:
                font.set_underline(True)
        self._pick_cache = {}
        self._text_cache = {}
        self._cache_order = []

    def sync(self):
        """跟随全局渲染倍率（倍率没变就什么都不做）"""
        factor = hires.scale()
        if factor != self._scale:
            self._build(factor)
        return self._scale

    @property
    def render_scale(self):
        return self._scale

    def _to_logical(self, size):
        if self._scale <= 1:
            return size
        return (int(round(size[0] / float(self._scale))),
                int(round(size[1] / float(self._scale))))

    def _to_logical_scalar(self, value):
        """单个度量值（高 / 行高 / 上伸 / 下伸）按倍率折算回逻辑尺寸"""
        if self._scale <= 1:
            return int(value)
        return int(round(value / float(self._scale)))

    # --- 渲染 ---

    def render(self, text, antialias, color, background=None):
        self.sync()
        key = (text, antialias, tuple(color),
               tuple(background) if background is not None else None)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        font = self._pick(text)
        if background is None:
            raw = font.render(text, antialias, color)
        else:
            raw = font.render(text, antialias, color, background)
        if self._scale > 1:
            surf = hires.HiresSurface(pygame.Surface.get_size(raw), self._scale,
                                      owner=self, key=key)
            pygame.Surface.blit(surf, raw, (0, 0))
        else:
            surf = raw
        if len(self._cache_order) >= _TEXT_CACHE_LIMIT:
            old = self._cache_order.pop(0)
            self._text_cache.pop(old, None)
        self._text_cache[key] = surf
        self._cache_order.append(key)
        return surf

    def size(self, text):
        self.sync()
        return self._to_logical(self._pick(text).size(text))

    def metrics(self, text):
        self.sync()
        return self._pick(text).metrics(text)

    def get_height(self):
        self.sync()
        return self._to_logical_scalar(self.primary.get_height())

    def get_linesize(self):
        self.sync()
        return self._to_logical_scalar(self.primary.get_linesize())

    def get_ascent(self):
        self.sync()
        return self._to_logical_scalar(self.primary.get_ascent())

    def get_descent(self):
        self.sync()
        return self._to_logical_scalar(self.primary.get_descent())

    # --- 主 / 备字体选择 ---

    def _pick(self, text):
        picked = self._pick_cache.get(text)
        if picked is None:
            picked = self.primary
            for ch in text:
                if ord(ch) not in self._covered:
                    picked = self.fallback
                    break
            if len(self._pick_cache) >= _PICK_CACHE_LIMIT:
                self._pick_cache.clear()
            self._pick_cache[text] = picked
        return picked

    # --- 样式（改动会作废已渲染的文字缓存）---

    def set_bold(self, value=True):
        if bool(value) == self._bold:
            return
        self._bold = bool(value)
        self._build(self._scale)

    def set_italic(self, value=True):
        if bool(value) == self._italic:
            return
        self._italic = bool(value)
        self._build(self._scale)

    def set_underline(self, value=True):
        if bool(value) == self._underline:
            return
        self._underline = bool(value)
        self._build(self._scale)
