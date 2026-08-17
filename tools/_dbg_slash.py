# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.getcwd())
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
import pygame
from src.entities.bullet import BulletManager
from src.engine.spell_bg import SpellBackground
from src.stages.stage6 import Stage6_FinalApproach, spell_kaeman_dimensional_slash

pygame.init()
pygame.display.set_mode((960, 720))
stage = Stage6_FinalApproach()
stage.setup_boss()
boss = stage.boss
stage.phase = "boss"
boss.phase = "spell"
boss.combat_enabled = True
boss.x = boss.target_x = 288.0
boss.y = boss.target_y = 112.0
boss.spell_bg = SpellBackground("x", "kaeman_slash")
bm = BulletManager()
px, py = 288.0, 560.0
t = 0
try:
    for _ in range(60 * 12):
        t += 1
        spell_kaeman_dimensional_slash(boss, bm, t, 1.0 / 60, px, py)
        bm.update(1.0 / 60, px, py)
        sl = getattr(boss, "kaeman_slash", None)
        if sl is not None and sl.get("tentacle") is not None:
            tt = sl["tentacle"].get("teleport_target")
            if tt is not None:
                px, py = tt
                sl["tentacle"]["teleport_target"] = None
except Exception:
    import traceback
    traceback.print_exc()
    for i, b in enumerate(bm.enemy_bullets):
        if isinstance(b.x, tuple) or isinstance(b.y, tuple):
            print("BAD bullet", i, "type", b.bullet_type, "x", b.x, "y", b.y,
                  "vx", b.vx, "vy", b.vy, "lifetime", b.lifetime, "age", b.age)
    print("t", t, "total bullets", len(bm.enemy_bullets))
    raise
print("NO_ERROR t", t, "bullets", len(bm.enemy_bullets))