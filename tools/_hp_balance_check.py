# -*- coding: utf-8 -*-
import os, sys
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())
import pygame
from src.engine import settings as cfg
from src.entities.bullet import BulletManager
pygame.init()
pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
from src.stages.stage2 import Stage2_DragonsNest, DRAGON_MAX_HP

st = Stage2_DragonsNest()
st.setup_boss()
b = st.boss
b.entering = False
b.phase = "non_spell"
b.combat_enabled = True
bm = BulletManager()

events = []
min_hp = {}
prev = (b.current_spell.name if b.current_spell else None, b.phase)
for i in range(3000):
    b.update(1/60, bm, cfg.BATTLE_AREA_WIDTH/2, cfg.BATTLE_AREA_HEIGHT-80)
    b.take_damage(500)
    name = b.current_spell.name if b.current_spell else None
    if name:
        min_hp[name] = min(min_hp.get(name, b.hp), b.hp)
    key = (name, b.phase)
    if key != prev:
        events.append((key[0], key[1], b.hp))
        prev = key
    if not b.alive:
        break

names = [e[0] for e in events]
# 闪符：入口 -> 其后首个非符血量
i_light = names.index("闪符「Non-Directional Lightning」")
light_start = events[i_light][2]
ns_hp = next(events[j][2] for j in range(i_light+1, len(events)) if events[j][1] == "non_spell")
# 龙符：入口 -> 符内最低血量（血量打空才转入超符）
i_dragon = names.index("龙符「One with the Dragons」")
dragon_start = events[i_dragon][2]
dragon_min = min_hp["龙符「One with the Dragons」"]
dragon_floor = int(b.last_spell.hp_threshold * DRAGON_MAX_HP)   # 超符触发阈值 = 打空
dragon_hp = dragon_start - dragon_floor
light_hp = light_start - ns_hp
print(f"闪符: {light_start:.0f} -> {ns_hp:.0f} = {light_hp:.0f} HP (期望 2352)")
print(f"龙符: {dragon_start:.0f} -> {dragon_min:.0f} (下限 {dragon_floor}) = {dragon_hp:.0f} HP (期望 3120，打空后展开超符)")
assert light_hp == 2352, light_hp
assert dragon_hp == 3120, dragon_hp
assert dragon_min <= 250, dragon_min   # 血量确实被打到接近打空后才转入超符
print("RESULT: PASS")
pygame.quit()