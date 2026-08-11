# -*- coding: utf-8 -*-
# 末影龙二面Boss无头测试：符卡流程 / Last Spell 机制 / 符卡背景渲染
import os, sys, time
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())

import pygame
import numpy as np

from src.engine import settings as cfg
from src.entities.bullet import BulletManager

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))

from src.stages.stage2 import Stage2_DragonsNest
from src.engine.spell_bg import SpellBackground, detect_style, STYLES

OUT = r"C:\Users\admin\.codex\visualizations\2026\08\10\019fe930-cabd-7f92-af0d-fbb69529585e"

# ---------- 1. 配置与流程 ----------
stage = Stage2_DragonsNest()
stage.setup_boss()
boss = stage.boss
assert boss is not None and boss.alive
assert len(boss.spell_cards) == 3, "三张通常符"
assert boss.last_spell is not None, "注册 Last Spell"
names = [c.name for c in boss.spell_cards] + [boss.last_spell.name]
print("[1] cards:", names)
assert names[0] == "燃符「Fireball Barrage」"
assert names[1] == "闪符「Non-Directional Lightning」"
assert names[2] == "龙符「One with the Dragons」"
assert names[3] == "超符「Superiority」"
assert boss.non_spell_funcs.keys() == {1, 2}

bm = BulletManager()
boss.entering = False
boss.phase = "non_spell"
boss.combat_enabled = True
px, py = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80

seen = []
frames = 0
while frames < 200000 and boss.alive:
    frames += 1
    boss.update(1 / 60, bm, px, py)
    if boss.phase == "spell" and boss.current_spell:
        if boss.is_last_spell_active():
            tag = "LAST:" + boss.current_spell.name
        else:
            tag = boss.current_spell.name
        if not seen or seen[-1] != tag:
            seen.append(tag)
            print(f"    t={frames:5d} hp={boss.hp:7.0f} -> {tag}")
    boss.take_damage(500)
    if len(bm.enemy_bullets) > 800:
        bm.enemy_bullets = bm.enemy_bullets[:800]

assert not boss.alive, "boss 最终被击破"
print("[2] 流程: " + " -> ".join(seen))
assert seen == [
    "燃符「Fireball Barrage」",
    "闪符「Non-Directional Lightning」",
    "龙符「One with the Dragons」",
    "LAST:超符「Superiority」",
], seen
print("[3] 三张通常符 + Last Spell 顺序正确，Last Spell 在第三符后立即展开")

# ---------- 2. Last Spell 机制 ----------
stage2 = Stage2_DragonsNest()
stage2.setup_boss()
b = stage2.boss
b.entering = False
b.phase = "non_spell"
b.combat_enabled = True
bm2 = BulletManager()
guard = 0
while not b.is_last_spell_active() and guard < 200000 and b.alive:
    b.update(1 / 60, bm2, px, py)
    b.take_damage(500)
    guard += 1
assert b.is_last_spell_active(), "进入 Last Spell"
print(f"[4] Last Spell 展开: {b.current_spell.name}  hp={b.hp:.0f}")
assert b.hp == b.last_spell_hp, (b.hp, b.last_spell_hp)
print(f"      黄金领域血量补充: {b.hp:.0f} OK")

# Miss 强制结束（不扣残机由 menu 处理，这里验证 Boss 状态）
assert b.force_end_last_spell() is True
assert not b.alive and not b.is_last_spell_active()
print("[5] force_end_last_spell OK: boss 击破、Last Spell 状态清除")

# 再次验证：非 Last Spell 时 force_end 返回 False
assert b.force_end_last_spell() is False
print("[6] 非 Last Spell 时 force_end_last_spell()=False OK")

# ---------- 3. 符卡背景渲染 ----------
print("[7] detect_style:")
for n, exp in (("燃符「Fireball Barrage」", "fire"), ("闪符「Non-Directional Lightning」", "lightning"),
               ("龙符「One with the Dragons」", "dragon"), ("超符「Superiority」", "superiority")):
    got = detect_style(n)
    assert got == exp, (n, got, exp)
    print(f"    {n} -> {got}")

results = {}
for style in ("fire", "lightning", "dragon", "superiority"):
    bg = SpellBackground("test", bg_style=style)
    for i in range(40):
        bg.update(1 / 60)
    t0 = time.perf_counter()
    for i in range(60):
        bg.update(1 / 60)
        bg.draw(screen)
    dt = (time.perf_counter() - t0) / 60.0
    bg.draw(screen)
    out = os.path.join(OUT, f"dragon_spellbg_{style}.png")
    pygame.image.save(screen, out)
    arr = pygame.surfarray.array3d(screen).astype(np.float32)
    bright = (arr.mean(axis=2) > 110).mean()
    print(f"    {style}: draw={dt*1000:.2f}ms bright_frac={bright:.4f} -> {out}")
    results[style] = dt * 1000
    assert dt * 1000 < 20, f"{style} 渲染过慢"

# 生命周期淡出
bg = SpellBackground("test", bg_style="superiority")
for i in range(25):
    bg.update(1 / 60)
bg.begin_fade_out()
for i in range(40):
    bg.update(1 / 60)
assert bg.done
print("[8] 符卡背景生命周期淡出 OK")

# ---------- 4. PlayingState：Last Spell 禁 Bomb / Miss 不损残机 ----------
from src.engine.game import Game
from src.ui.menu import PlayingState

game = Game()
game.global_data["stage"] = 1
st = Stage2_DragonsNest()
st.setup_waves()
state = PlayingState(game, st)
state.stage.setup_boss()
state.stage.phase = "boss"
boss = state.stage.boss
boss.entering = False
boss.phase = "non_spell"
boss.combat_enabled = True
state.lives = 3
state.bombs = 3
state.bomb_blocked_timer = 0

# 冲到 Last Spell
guard = 0
while not boss.is_last_spell_active() and guard < 200000 and boss.alive:
    state.stage.boss.update(1 / 60, state.bullet_manager, state.player.x, state.player.y)
    boss.take_damage(500)
    guard += 1
assert boss.is_last_spell_active()
assert not state.bomb_blocked_timer

# 禁 Bomb：按下 X 不应消耗 Bomb
state.game.keys_just_pressed = {pygame.K_x: True}
state.player.want_bomb = True
state.bombs = 3
state.update(1 / 60)
assert state.bombs == 3, "Last Spell 中 Bomb 不应被消耗"
assert state.bomb_blocked_timer > 0, "应显示禁用提示"
print(f"[9] Last Spell 禁 Bomb OK (提示计时器={state.bomb_blocked_timer})")

# Miss 不损残机：放一颗敌弹在玩家身上
state.lives = 3
state.player.invincible = 0
from src.entities.bullet import create_bullet_angle
state.bullet_manager.enemy_bullets.clear()
b = create_bullet_angle(state.player.x, state.player.y, 0, 0, radius=3, color=(255, 255, 255))
state.bullet_manager.add_enemy_bullet(b)
state.update(1 / 60)
assert state.lives == 3, "Last Spell Miss 不应扣残机"
assert not boss.alive, "Last Spell Miss 后 Boss 应被强制击破"
assert state.stage.phase == "cleared" or state.stage.phase == "boss", state.stage.phase
print("[10] Last Spell Miss 不损残机、强制结束 OK")

# ---------- 5. 整场预览截图（符卡宣言横幅） ----------
st3 = Stage2_DragonsNest()
st3.setup_boss()
b3 = st3.boss
b3.entering = False
b3.phase = "non_spell"
b3.combat_enabled = True
bm3 = BulletManager()
for target_name in ("燃符「Fireball Barrage」", "闪符「Non-Directional Lightning」",
                    "龙符「One with the Dragons」", "超符「Superiority」"):
    guard = 0
    while (b3.current_spell is None or b3.current_spell.name != target_name) and guard < 200000 and b3.alive:
        b3.update(1 / 60, bm3, px, py)
        b3.take_damage(500)
        guard += 1
    # 推进到横幅完全显示
    for _ in range(40):
        b3.update(1 / 60, bm3, px, py)
    screen.fill((0, 0, 0))
    st3.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    safe = target_name.replace("「", "").replace("」", "").replace(" ", "_")
    out = os.path.join(OUT, f"dragon_boss_{safe}.png")
    pygame.image.save(screen, out)
    print(f"    banner shot: {out}")

pygame.quit()
print("ALL OK")