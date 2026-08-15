# -*- coding: utf-8 -*-
import io
path = r"D:\pyz\my thingses\TouHou\src\engine\panorama3d.py"
src = io.open(path, encoding="utf-8").read()
old = """        if junction_v is None:
            junction_v = self._detect_junction_v()
        jv = float(junction_v)
        cy = (self.h - 1) / 2.0"""
new = """        if junction_v is None:
            junction_v = self._detect_junction_v()
        jv = float(junction_v)
        if depth_repeat is None:
            depth_repeat = FLOOR_DEPTH_REPEAT
        cy = (self.h - 1) / 2.0"""
assert src.count(old) == 1, src.count(old)
src = src.replace(old, new)
io.open(path, "w", encoding="utf-8", newline="\n").write(src)
print("patched")
