# -*- coding: utf-8 -*-
import io
path = "src/stages/stage6.py"
txt = io.open(path, encoding="utf-8").read()
g0 = txt.index("def _ghost_spell_maxor(")
g1 = txt.index("def _ghost_spell(ghost, bullet_manager, player_x, player_y):")
OLD = txt[g0:g1]
patch = "*** Begin Patch\n*** Update File: %s\n@@\n" % path
patch += "".join("-" + ln + "\n" for ln in OLD.splitlines())
patch += "*** End Patch\n"
io.open("tools/_patch_b_only.txt", "w", encoding="utf-8", newline="\n").write(patch)
print("B-only patch: %d chars, %d lines" % (len(patch), len(OLD.splitlines())))
