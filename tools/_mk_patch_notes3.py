# -*- coding: utf-8 -*-
# 临时脚本：代码首段注释 + RELEASE_NOTES 追加
import io

# ---- 1) stage6.py 文件头注释 ----
path = "src/stages/stage6.py"
txt = io.open(path, encoding="utf-8").read()
OLD_C = "#   - 后半段「要塞」：推进到凋零要塞，敌人减少而弹幕更宏大，曾败北的\n"
NEW_C = "#   - 后半段「要塞」：推进到凋零要塞后不再生成小怪，曾败北的\n"
assert txt.count(OLD_C) == 1
io.open("tools/_patch_hdr.txt", "w", encoding="utf-8", newline="\n").write(
    "*** Begin Patch\n*** Update File: %s\n@@\n-%s+%s*** End Patch\n" % (path, OLD_C, NEW_C))

# ---- 2) RELEASE_NOTES ----
npath = "RELEASE_NOTES.md"
ntxt = io.open(npath, encoding="utf-8").read()
ANCHOR = "  - 各波队形：Undead Line / Miner Phalanx 各是左右两个斜臂（左 `\\` + 右 `/`，合起来是一个 V）、Fortress Gate 3 只排 V（档高 44）、Guard Wall 6 只排 V（档高 34）、Last March 10 只是上下两层 V（各 5 只，档高 40，第二层整体再高 48px）\n"
assert ntxt.count(ANCHOR) == 1, "锚点没找到"
ADD = """
- 六面残影段不再生成小怪，四位门徒的弹幕加强（`src/stages/stage6.py`）：原来要塞段还排着四波小怪（68s Fortress Wall / 75s Siege Detail / 82s Knight Order / 90s Golem Ward），它们与 70s 起登场的门徒残影挤在同一段里；现在这四波全部取消，70~97s 只剩残影接力（每位登场那一帧即起手的一段弹幕），段内小怪为零，残影收场后照旧进入 100s 的王座前最后防线（`setup_waves` 里这一段只剩注释）
  - 四位残影的「告别弹」在原来的削弱版基础上整体加强到约 2.3 倍弹量，片段长度由 80 帧延长到 110 帧（`GHOST_SPELL_FRAMES`）：Maxor 骷髅排三排各 3 发 → 四排各 5 发、末尾自机狙大玉一对 → 两轮各 3 发（片段发弹 11 → 26）；Storm 八向环每 20 帧 6 发 → 每 18 帧 8 发、自机狙双刀每 40 → 36 帧、旋转箭环 8 发一圈 → 12 发两圈、随机大玉 3 → 4 发（39 → 92）；Goldor 金环 8 → 10 发并来两圈、反向白环 6 → 8 发并来两圈、米弹三臂每 12 帧 4 圈 → 四臂每 10 帧 5 圈（26 → 56）；Necron 螺旋六臂每 15 帧 4 圈 → 八臂每 10 帧 7 圈、末尾大玉环 10 发一圈 → 12 发两圈（34 → 80）
  - 仍然一个机制都不带（没有无敌与破防、没有结晶 / 终端 / 避雷柱、没有判定窗口与全屏雷击、没有 TNT 与地狱火），弹速也仍低于原版；实测（首波两位 Lord 已在真实战斗中被击破）71 / 79 / 87 / 95s 四帧的同屏敌弹是 47 / 70 / 57 / 80 发
"""
io.open("tools/_patch_notes3.txt", "w", encoding="utf-8", newline="\n").write(
    "*** Begin Patch\n*** Update File: %s\n@@\n" % npath
    + "".join(" " + ln + "\n" for ln in ANCHOR.splitlines())
    + "".join("+" + ln + "\n" for ln in ADD.splitlines())
    + "*** End Patch\n")
print("ok")
