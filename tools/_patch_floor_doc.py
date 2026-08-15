# -*- coding: utf-8 -*-
import io
path = r"D:\pyz\my thingses\TouHou\src\engine\panorama3d.py"
src = io.open(path, encoding="utf-8").read()
old1 = "        行映射表在初始化时预计算并缓存；渲染时只对静态贴图按表重采样，\n        写入复用的帧表面后逐列 blit（不逐帧新建贴图）。"
new1 = "        行映射表在初始化时预计算并缓存；渲染时只对静态贴图按表重采样，\n        与墙体一致按 col_step 分组后写入复用的帧表面并逐组 blit（不逐帧新建贴图）。"
old2 = "        每列行映射表在初始化时预计算（v=K/((cy-y)*cos(phi))，与墙体同曲率），\n        结果写入复用的帧表面后逐列 blit 到该列交界线下方。"
new2 = "        行映射表在初始化时预计算（v=K/((cy-y)*cos(phi))，与墙体同曲率），\n        按 col_step 分组采样，结果写入复用的帧表面后逐组 blit 到交界线下方。"
assert src.count(old1) == 1, src.count(old1)
assert src.count(old2) == 1, src.count(old2)
src = src.replace(old1, new1).replace(old2, new2)
io.open(path, "w", encoding="utf-8", newline="\n").write(src)
print("docstrings updated")
