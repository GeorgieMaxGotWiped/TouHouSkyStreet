# -*- coding: utf-8 -*-
# 字体回退：主字体缺失的字形（如中文字符）自动改用备用字体渲染

import struct

import pygame


def _covered_codepoints(font_path):
    """解析 TrueType/OpenType 字体的 cmap 表，返回该字体实际支持的码点集合"""
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
    """优先使用主字体；字符串含主字体不支持的字符时整体改用备用字体"""

    def __init__(self, primary_path, fallback_path, size):
        self.primary = pygame.font.Font(primary_path, size)
        self.fallback = pygame.font.Font(fallback_path, size)
        self._covered = _covered_codepoints(primary_path)
        self._pick_cache = {}

    def _pick(self, text):
        picked = self._pick_cache.get(text)
        if picked is None:
            picked = self.primary
            for ch in text:
                if ord(ch) not in self._covered:
                    picked = self.fallback
                    break
            self._pick_cache[text] = picked
        return picked

    def render(self, text, antialias, color, background=None):
        font = self._pick(text)
        if background is None:
            return font.render(text, antialias, color)
        return font.render(text, antialias, color, background)

    def size(self, text):
        return self._pick(text).size(text)

    def metrics(self, text):
        return self._pick(text).metrics(text)

    def get_height(self):
        return self.primary.get_height()

    def get_linesize(self):
        return self.primary.get_linesize()

    def get_ascent(self):
        return self.primary.get_ascent()

    def get_descent(self):
        return self.primary.get_descent()

    def set_bold(self, value=True):
        self.primary.set_bold(value)
        self.fallback.set_bold(value)

    def set_italic(self, value=True):
        self.primary.set_italic(value)
        self.fallback.set_italic(value)

    def set_underline(self, value=True):
        self.primary.set_underline(value)
        self.fallback.set_underline(value)
