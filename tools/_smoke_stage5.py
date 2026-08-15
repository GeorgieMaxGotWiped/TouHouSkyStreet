# -*- coding: utf-8 -*-
# 五面冒烟测试：BOSS RUSH 状态机 / 十张符卡顺序 / 最终通关结算。
import math
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame

pygame.init()
screen = pygame.display.set_mode((960, 720))
sys.path.insert(0, os.getcwd())

from src.engine import settings as cfg
from src.entities.bullet import BulletManager
from src.stages import get_stage_class, get_next_stage_class
from src.stages.stage5 import Stage5_WitherLords

def _solve_goldor_terminal(stage, bm, px, py, limit=4000):
    """机械符「Terminal Pursuit」是时符：伤害无法推进，需按玩法破解 5 个终端并进入中央。"""
    from src.stages import goldor_terminal as gt

    def tick(px, py, click=None, keys=None):
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

    guard = 0
    while guard < limit:
        st = getattr(stage.boss, "goldor_terminal", None)
        boss = stage.boss
        if st is None or st.get("spell_done") or boss.current_spell is None:
            return px, py
        if st.get("entering_center"):
            px, py = tick(px, py)
            guard += 1
            continue
        if st["hacking"] is not None:
            puzzle = st["puzzle"]
            if puzzle.kind == "order":
                dir_keys = (pygame.K_UP, pygame.K_RIGHT, pygame.K_DOWN, pygame.K_LEFT)
                for d in puzzle.sequence:
                    px, py = tick(px, py, keys={dir_keys[d]: True})
                    if stage.boss.goldor_terminal is None:
                        break
                for _ in range(4):
                    if stage.boss.goldor_terminal is None:
                        break
                    px, py = tick(px, py)
                continue
            clicks = []
            if puzzle.kind == "color":
                for i in range(puzzle.slot_count()):
                    if puzzle.items[i] == puzzle.target_idx:
                        r = puzzle.slot_rect(i)
                        clicks.append((r.centerx, r.centery))
            elif puzzle.kind == "panes":
                for i in range(15):
                    if puzzle.red[i]:
                        r = puzzle.slot_rect(i)
                        clicks.append((r.centerx, r.centery))
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
                            rect = puzzle.slot_rect(r * puzzle.cols + c)
                            for _ in range(need):
                                clicks.append((rect.centerx, rect.centery))
                            break
            for click in clicks:
                px, py = tick(px, py, click=click)
                if stage.boss.current_spell is None or stage.boss.goldor_terminal is None:
                    break
            for _ in range(4):
                if stage.boss.goldor_terminal is None:
                    break
                px, py = tick(px, py)
            continue
        if stage.player_input_locked:
            px, py = tick(px, py)
            guard += 1
            continue
        target = next((t for t in st["terminals"] if not t["solved"]), None)
        if target is None:
            s_cur = gt._gt_project_s(px, py)
            entry_s = gt._gt_project_s(gt.GT_IL - 20,
                                       (gt.GT_ENTRANCE_Y0 + gt.GT_ENTRANCE_Y1) / 2)
            dist = gt._gt_path_dist(s_cur, entry_s)
            if dist > 6.0:
                s_new = (s_cur + min(5.0, dist)) % gt.GT_LOOP_LEN
                tx, ty = gt._gt_path_point(s_new)
                px, py = move_toward(px, py, tx, ty, speed=5.0)
            else:
                px, py = move_toward(px, py, gt.GT_IL + 80,
                                     (gt.GT_ENTRANCE_Y0 + gt.GT_ENTRANCE_Y1) / 2,
                                     speed=5.0)
            px, py = tick(px, py)
            guard += 1
            continue
        s_cur = gt._gt_project_s(px, py)
        dist = gt._gt_path_dist(s_cur, target["s"])
        if dist < 8.0:
            px, py = move_toward(px, py, target["x"], target["y"], speed=5.0)
        else:
            s_new = (s_cur + min(5.0, dist)) % gt.GT_LOOP_LEN
            tx, ty = gt._gt_path_point(s_new)
            px, py = move_toward(px, py, tx, ty, speed=5.0)
        px, py = tick(px, py)
        guard += 1
    raise AssertionError("机械符「Terminal Pursuit」未能自动通关")

def main():
    assert get_stage_class(5) is Stage5_WitherLords, "stage5 registered"
    assert get_next_stage_class(4) is Stage5_WitherLords, "stage4 -> stage5"
    assert get_next_stage_class(5) is None, "stage5 -> menu"
    print("[1] registry OK")

    stage = Stage5_WitherLords()
    stage.setup_waves()
    bm = BulletManager()
    px, py = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80

    stage.update(1 / 60, bm, px, py)
    assert stage.phase == "dialogue" and stage.dialogue_active
    assert stage.boss is not None and stage.boss.name == "The Watcher"
    stage.on_dialogue_end()
    assert stage.phase == "boss" and stage.boss.current_spell is not None
    print("[2] The Watcher opening spell OK")

    seen = []
    guard = 0
    while stage.phase not in ("cleared", "defeat_dialogue") and guard < 60000:
        stage.update(1 / 60, bm, px, py)
        if stage.phase == "dialogue" and not stage.dialogue_is_defeat:
            stage.on_dialogue_end()
            guard += 1
            continue
        boss = stage.boss
        if (boss is not None and boss.alive and boss.combat_enabled
                and stage.phase == "boss"
                and boss.current_spell is not None
                and boss.current_spell.name == "机械符「Terminal Pursuit」"):
            px, py = _solve_goldor_terminal(stage, bm, px, py)
        elif boss is not None and boss.alive and boss.combat_enabled and stage.phase == "boss":
            for _ in range(4):
                boss.take_damage(60)
        if boss is not None and boss.current_spell is not None:
            name = boss.current_spell.name
            if not seen or seen[-1] != name:
                seen.append(name)
        guard += 1

    if stage.phase == "defeat_dialogue":
        stage.on_defeat_dialogue_end()
    assert stage.phase == "cleared", f"cleared, got {stage.phase}"
    assert "Undead Exhibition" in seen[0]
    assert "Apocalypse" in seen[-1]
    assert any("Giga Lightning" in n for n in seen), "Storm Phase2 spell present"
    assert any("Terminal Pursuit" in n for n in seen), "Goldor 机械符在符卡序列中"
    assert any("Infinite Rage" in n for n in seen), "Goldor Phase3 符卡在符卡序列中"

    assert len(seen) == 10, f"10 spells, got {len(seen)}: {seen}"
    print(f"[3] BOSS RUSH cleared, spells={len(seen)}")

    stage.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    os.makedirs("previews", exist_ok=True)
    pygame.image.save(screen, os.path.join("previews", "_stage5_preview_cleared.png"))
    print("ALL OK")

if __name__ == "__main__":
    main()
