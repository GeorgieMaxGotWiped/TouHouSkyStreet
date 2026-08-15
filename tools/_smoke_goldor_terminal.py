# -*- coding: utf-8 -*-
# 机械符「Terminal Pursuit」冒烟测试：
# 强开 Goldor 第一张符卡 -> 环路约束 -> 依次破解 5 个终端 ->
# 进入中央 -> 符卡结束并直接进入 Aegis；期间渲染预览图。
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import sys
sys.path.insert(0, os.getcwd())
import math
import pygame

from src.engine import settings as cfg
from src.entities.bullet import BulletManager

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
os.makedirs("previews", exist_ok=True)

from src.stages.stage5 import Stage5_WitherLords
from src.stages import goldor_terminal as gt


def make_stage():
    stage = Stage5_WitherLords()
    boss = stage._make_goldor()
    stage.boss = boss
    stage.phase = "boss"
    boss.arm_combat(0)
    boss.entering = False
    boss.entry_timer = 0
    boss._start_spell(boss.spell_cards[0])
    assert boss.current_spell.name == "机械符「Terminal Pursuit」", boss.current_spell.name
    return stage, boss


def tick(stage, bm, px, py, click=None, keys=None):
    stage.mouse_pos = (cfg.BATTLE_OFFSET_X + (click[0] if click else px),
                       cfg.BATTLE_OFFSET_Y + (click[1] if click else py))
    stage.mouse_buttons_just_pressed = {1: True} if click else {}
    stage.mouse_buttons_held = {1: bool(click)}
    stage.keys_just_pressed = keys or {}
    tp = getattr(stage, "player_teleport_target", None)
    if tp is not None:
        px, py = tp
        stage.player_teleport_target = None
    px, py = stage.constrain_player(px, py)
    stage.update(1 / 60, bm, px, py)
    return px, py


def move_toward(px, py, tx, ty, speed=5.0):
    d = math.hypot(tx - px, ty - py)
    if d < speed:
        return tx, ty
    return px + (tx - px) / d * speed, py + (ty - py) / d * speed


def render(name):
    screen.fill((0, 0, 0))
    pygame.draw.rect(screen, cfg.COLOR_PANEL_BG,
                     (cfg.PANEL_LEFT, 0, cfg.PANEL_WIDTH, cfg.SCREEN_HEIGHT))
    stage.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    stage.draw_foreground(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    pygame.image.save(screen, os.path.join("previews", name))


def _keyboard_steps(puzzle, target):
    """返回把光标从当前位置移动到 target 的方向键序列（行内折返）。"""
    cols = puzzle.cols
    cr, cc = divmod(puzzle.cursor, cols)
    tr, tc = divmod(target, cols)
    steps = []
    if tc != cc:
        fwd = (tc - cc) % cols
        if fwd <= cols - fwd:
            steps += [pygame.K_RIGHT] * fwd
        else:
            steps += [pygame.K_LEFT] * (cols - fwd)
    if tr != cr:
        steps += [pygame.K_DOWN if tr > cr else pygame.K_UP] * abs(tr - cr)
    return steps


def solve_current_puzzle(stage, bm, px, py):
    """用键盘自动破解当前终端（方向序列直接按方向键，其余移动光标+Z）。"""
    state = stage.boss.goldor_terminal
    puzzle = state["puzzle"]
    render(f"_gt_terminal_puzzle_{puzzle.kind}.png")
    dir_keys = (pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT)
    if puzzle.kind == "order":
        # 方向序列：按显示顺序直接输入方向键
        for d in puzzle.sequence:
            state = stage.boss.goldor_terminal
            puzzle = state["puzzle"]
            if puzzle is None or puzzle.complete:
                break
            px, py = tick(stage, bm, px, py, keys={dir_keys[d]: True})
    else:
        targets = []
        if puzzle.kind == "color":
            targets = [i for i in range(puzzle.slot_count())
                       if puzzle.items[i] == puzzle.target_idx]
        elif puzzle.kind == "panes":
            targets = [i for i in range(15) if puzzle.red[i]]
        elif puzzle.kind == "device":
            # 蛇形路径 绿(0,0)->红(n-1,n-1)：把路径格旋转到指向下一格
            n = puzzle.rows
            path = []
            for r in range(n):
                cseq = range(n) if r % 2 == 0 else range(n - 1, -1, -1)
                for c in cseq:
                    path.append((r, c))
            dir_vecs = ((-1, 0), (0, 1), (1, 0), (0, -1))   # 上 右 下 左
            for i in range(len(path) - 1):
                r, c = path[i]
                nr, nc = path[i + 1]
                for di, (dr, dc) in enumerate(dir_vecs):
                    if (nr - r, nc - c) == (dr, dc):
                        need = (di - puzzle.current[r][c]) % 4
                        targets += [r * puzzle.cols + c] * need
                        break
        assert targets, f"puzzle {puzzle.kind} 没有可操作项"
        for target in targets:
            state = stage.boss.goldor_terminal
            puzzle = state["puzzle"]
            if puzzle is None or puzzle.complete:
                return px, py
            for k in _keyboard_steps(puzzle, target):
                px, py = tick(stage, bm, px, py, keys={k: True})
            px, py = tick(stage, bm, px, py, keys={pygame.K_z: True})
    # 结算帧
    for _ in range(4):
        px, py = tick(stage, bm, px, py)
    state = stage.boss.goldor_terminal
    pz = state["puzzle"]
    assert pz is None or pz.complete, "破解后应已结算"
    return px, py


def approach_and_solve(stage, bm, px, py, terminal_idx):
    """沿环路顺时针移动到终端 -> 等待破解开始 -> 自动解决。"""
    state = stage.boss.goldor_terminal
    t = state["terminals"][terminal_idx]
    guard = 0
    while guard < 900:
        state = stage.boss.goldor_terminal
        if state["hacking"] is not None:
            return solve_current_puzzle(stage, bm, px, py)
        if stage.player_input_locked:
            px, py = tick(stage, bm, px, py)
            guard += 1
            continue
        s_cur = gt._gt_project_s(px, py)
        dist = gt._gt_path_dist(s_cur, t["s"])
        if dist < 8.0:
            px, py = move_toward(px, py, t["x"], t["y"], speed=5.0)
        else:
            s_new = (s_cur + min(5.0, dist)) % gt.GT_LOOP_LEN
            tx, ty = gt._gt_path_point(s_new)
            px, py = move_toward(px, py, tx, ty, speed=5.0)
        px, py = tick(stage, bm, px, py)
        guard += 1
    raise AssertionError(f"终端 {terminal_idx} 未触发破解")


# --- 1. 开符与传送 ---
stage, boss = make_stage()
bm = BulletManager()
px, py = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80
for _ in range(10):
    px, py = tick(stage, bm, px, py)
state = boss.goldor_terminal
assert state is not None
# 玩家应已传送到左下角附近
assert math.hypot(px - gt.GT_BL[0], py - gt.GT_BL[1]) < 3, (px, py, gt.GT_BL)
print(f"[1] 开符 OK：玩家已传送至左下角 {px:.0f},{py:.0f}")

# --- 2. 环路约束：随机点被 _gt_clamp_player 拉回走廊；并通过真实 tick 验证接线 ---
rng = __import__("random").Random(7)
for _ in range(12):
    px, py = tick(stage, bm, px, py)
state = boss.goldor_terminal
for _ in range(300):
    x = rng.uniform(0, cfg.BATTLE_AREA_WIDTH)
    y = rng.uniform(0, cfg.BATTLE_AREA_HEIGHT)
    cx, cy = gt._gt_clamp_player(x, y, state)
    assert not (gt.GT_IL < cx < gt.GT_IR and gt.GT_IT < cy < gt.GT_IB), (cx, cy)
    assert gt.GT_OUTER <= cx <= gt.GT_OUTER_RIGHT, (cx, cy)
    assert gt.GT_OUTER <= cy <= gt.GT_OUTER_BOTTOM, (cx, cy)
assert stage.constrain_player(px, py) is not None
print(f"[2] 走廊约束 OK：玩家位于环路内 {px:.0f},{py:.0f}")
render("_gt_terminal_corridor.png")

# --- 3. 依次破解 5 个终端 ---
for idx, tdef in enumerate(gt.GT_TERMINAL_DEFS):
    # 若当前不在目标终端附近，先把玩家送回左下角再走
    px, py = tick(stage, bm, px, py)
    state = boss.goldor_terminal
    if state["hacking"] is None:
        px, py = tick(stage, bm, px, py)
    px, py = approach_and_solve(stage, bm, px, py, idx)
    state = boss.goldor_terminal
    assert state["terminals"][idx]["solved"], f"终端 {idx} 未解决"
    print(f"[3.{idx + 1}] {tdef['kind'].upper()} 终端破解 OK（已解决 {state['solved_count']}）")

# --- 4. 最终 DEVICE 破解后中央入口开启 ---
state = boss.goldor_terminal
assert state["center_open"], "DEVICE 破解后中央入口未开启"
assert all(t["solved"] for t in state["terminals"]), "全部终端应已解决"
render("_gt_terminal_center_open.png")
print("[4] 中央入口已开启 OK")

# --- 5. 进入中央 -> 符卡结束 -> 直接进入 Aegis ---
guard = 0
while boss.current_spell is not None and boss.current_spell.name == "机械符「Terminal Pursuit」" and guard < 900:
    state = boss.goldor_terminal
    if state is None or state.get("spell_done"):
        break
    if state.get("entering_center"):
        px, py = tick(stage, bm, px, py)
        guard += 1
        continue
    # 沿环路移动到左墙入口带，再进入中央
    s_cur = gt._gt_project_s(px, py)
    entry_s = gt._gt_project_s(gt.GT_IL - 20, (gt.GT_ENTRANCE_Y0 + gt.GT_ENTRANCE_Y1) / 2)
    dist = gt._gt_path_dist(s_cur, entry_s)
    if dist > 6.0:
        s_new = (s_cur + min(5.0, dist)) % gt.GT_LOOP_LEN
        tx, ty = gt._gt_path_point(s_new)
        px, py = move_toward(px, py, tx, ty, speed=5.0)
    else:
        # 直接穿过左墙缺口进入中央
        px, py = move_toward(px, py, gt.GT_IL + 80,
                             (gt.GT_ENTRANCE_Y0 + gt.GT_ENTRANCE_Y1) / 2, speed=5.0)
    px, py = tick(stage, bm, px, py)
    guard += 1
assert boss.current_spell is not None and "Aegis" in boss.current_spell.name, (
    f"应进入 Aegis，实际 {boss.current_spell.name if boss.current_spell else None}")
print("[5] 进入中央后符卡结束，直接进入下一张：", boss.current_spell.name)

render("_gt_terminal_aegis_start.png")
print("[SMOKE] 机械符「Terminal Pursuit」全流程 OK")
