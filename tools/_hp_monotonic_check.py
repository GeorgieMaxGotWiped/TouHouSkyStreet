# -*- coding: utf-8 -*-
# 验证：总血量 13344 下，血条全程严格递减，且各阶段/非符血量保持当前值
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager
pygame.init()
pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
from src.stages import stage2

st = stage2.Stage2_DragonsNest()
st.setup_boss()
b = st.boss
b.entering = False
b.phase = "non_spell"
b.combat_enabled = True
bm = BulletManager()

events = []  # (阶段标签, hp)
prev = (b.current_spell.name if b.current_spell else None, b.phase)
last_hp = b.hp
for i in range(4000):
    b.update(1/60, bm, cfg.BATTLE_AREA_WIDTH/2, cfg.BATTLE_AREA_HEIGHT-80)
    b.take_damage(500)
    key = (b.current_spell.name if b.current_spell else None, b.phase)
    if key != prev:
        events.append((key[0], key[1], b.hp))
        prev = key
    if not b.alive:
        break

print(f"max_hp = {b.max_hp}  (期望 13344)")
assert b.max_hp == 13344, b.max_hp
for e in events:
    print(f"  {e[1]:10s} {e[0] if e[0] else '(非符)'}: hp={e[2]:.0f}")

# 按顺序收集所有边界血量
hps = [b.max_hp] + [e[2] for e in events]
hps.append(0.0)
print("边界序列:", [round(h, 1) for h in hps])
assert all(hps[i] > hps[i+1] for i in range(len(hps)-1)), "血量未严格递减!"
print("血条严格递减: PASS")

# 各段血量 = 相邻边界差（按阶段顺序）
expected = [("开场非符", 3360), ("燃符", 2688), ("龙息非符", 1152), ("闪符", 2352),
            ("末影珍珠非符", 672), ("龙符", 2520), ("超符", 600)]
seg_hps = [round(hps[i] - hps[i+1]) for i in range(len(expected))]
print("各段血量:", list(zip([e[0] for e in expected], seg_hps)))
assert seg_hps == [e[1] for e in expected], seg_hps
print("各段血量保持当前值: PASS")
print("RESULT: PASS")
pygame.quit()