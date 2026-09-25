# -*- coding: utf-8 -*-
# 阶段血环预览：把一整场 Boss 战按血量取样，拼出「环随掉血缩短」的演变图。
#
# 用法：python tools\_boss_ring_preview.py [名字 ...]
#   名字取自 BOSSES（不传则渲染 DEFAULT）。每张图两行、每行 10 帧，帧下标注
#   当时的阶段 / 血量；输出到 previews/ring_<名字>_<序号>.png。
#
import os
import sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
sys.path.insert(0, os.getcwd())

import pygame

from src.engine import settings as cfg
from src.engine.painter import Painter
from src.entities.bullet import BulletManager

pygame.init()
pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))

TILE = 260                     # 单帧方块边长（逻辑像素）
COLS = 10                      # 每行帧数
OUT = os.environ.get("RING_OUT", "previews")


def _final_boss(stage_cls):
    """关底 Boss：正常建关后取 Boss 作为被试"""
    def build():
        stage = stage_cls()
        stage.setup_boss()
        return stage
    return build


def _mid_boss(stage_cls):
    """道中 Boss：把道中 Boss 摆到 stage.boss 的位置上统一处理"""
    def build():
        stage = stage_cls()
        stage.setup_mid_boss()
        stage.boss = stage.mid_boss
        stage.mid_boss = None
        return stage
    return build


def _stage5(boss_id):
    """五面 BOSS RUSH：单独取出一位 Wither Lord"""
    def build():
        from src.stages.stage5 import Stage5_WitherLords
        stage = Stage5_WitherLords()
        stage.boss = stage._build_boss(boss_id)
        stage.mid_boss = None
        return stage
    return build


def _registry():
    from src.stages.stage1 import Stage1_SkyblockHub
    from src.stages.stage2 import Stage2_DragonsNest
    from src.stages.stage3 import Stage3_CatacombsF1
    from src.stages.stage4 import Stage4_Catacombs
    from src.stages.stage6 import Stage6_FinalApproach
    from src.stages.stage_ex import ExtraStageTheRift

    return {
        "arachne": _final_boss(Stage1_SkyblockHub),
        "spider": _mid_boss(Stage1_SkyblockHub),
        "dragon": _final_boss(Stage2_DragonsNest),
        "bonzo": _final_boss(Stage3_CatacombsF1),
        "watcher_mid": _mid_boss(Stage3_CatacombsF1),
        "scarf": _mid_boss(Stage4_Catacombs),
        "sadan": _final_boss(Stage4_Catacombs),
        "watcher": _stage5("watcher"),
        "professor": _stage5("professor"),
        "thorn": _stage5("thorn"),
        "livid": _stage5("livid"),
        "maxor": _stage5("maxor"),
        "storm": _stage5("storm"),
        "goldor": _stage5("goldor"),
        "necron": _stage5("necron"),
        "kaeman": _final_boss(Stage6_FinalApproach),
        "barry": _final_boss(ExtraStageTheRift),
        "wizardman": _mid_boss(ExtraStageTheRift),
    }


DEFAULT = ["sadan", "dragon", "bonzo", "thorn"]


def build_boss(factory):
    """按真实开战状态摆好一只 Boss（跳过入场 / 对话）"""
    stage = factory()
    boss = stage.boss
    boss.entering = False
    boss.entry_timer = 0
    boss.phase = "non_spell"
    boss.arm_combat(0)
    boss._ring_begin_non_spell()
    return boss


def walk(boss, cols=COLS, guard=6000):
    """整场打一遍，均匀取 cols 帧"""
    bm = BulletManager()
    canvas = Painter.create((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
    shot = []

    def snap(tag):
        canvas.fill((18, 18, 24))
        boss.spell_banner_active = False   # 宣言立绘会盖住血环，预览里先关掉
        px, py = boss.x, boss.y
        boss.draw(canvas, TILE // 2 - px, TILE // 2 - py)
        tile = pygame.Surface((TILE, TILE))
        tile.blit(canvas, (0, 0), (0, 0, TILE, TILE))
        pct = int(round(100.0 * boss.hp / boss.max_hp))
        label = "%s %s hp%d(%d%%)" % (tag, boss.phase[:5], int(boss.hp), pct)
        surf = pygame.Surface((TILE, TILE + 14))
        surf.fill((18, 18, 24))
        surf.blit(tile, (0, 14))
        font = pygame.font.Font(None, 14)
        surf.blit(font.render(label, True, (230, 230, 230)), (3, 1))
        shot.append(surf)

    dmg = boss.max_hp / 260.0
    last_phase = None
    for i in range(guard):
        boss.update(1 / 60, bm, cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80)
        if boss.alive:
            boss.take_damage(dmg)
        tag = "ns" if boss.phase == "non_spell" else ("sp" if boss.phase == "spell"
                                                      else boss.phase[:2])
        if boss.phase != last_phase:
            snap(tag)
            last_phase = boss.phase
        if i % 12 == 0:
            snap(tag)
        if not boss.alive:
            snap("dead")
            break
    step = max(1, len(shot) // cols)
    picked = shot[::step][:cols]
    while len(picked) < cols:
        picked.append(shot[-1])
    return picked


def row(shots):
    out = pygame.Surface((sum(s.get_width() for s in shots),
                          max(s.get_height() for s in shots)))
    out.fill((12, 12, 16))
    x = 0
    for s in shots:
        out.blit(s, (x, 0))
        x += s.get_width()
    return out


def sheet(name, entries, per_sheet=2):
    rows = []
    for label, factory in entries:
        shots = walk(build_boss(factory))
        rows.append(row(shots))
        print("  %s: %d frames" % (label, len(shots)))
    for i in range(0, len(rows), per_sheet):
        chunk = rows[i:i + per_sheet]
        out = pygame.Surface((max(r.get_width() for r in chunk),
                              sum(r.get_height() for r in chunk)))
        out.fill((12, 12, 16))
        y = 0
        for r in chunk:
            out.blit(r, (0, y))
            y += r.get_height()
        path = os.path.join(OUT, "%s_%d.png" % (name, i // per_sheet + 1))
        pygame.image.save(out, path)
        print("saved", path)


def main(argv):
    registry = _registry()
    names = argv or DEFAULT
    unknown = [n for n in names if n not in registry]
    if unknown:
        print("unknown boss: %s" % ", ".join(unknown))
        print("available: %s" % ", ".join(sorted(registry)))
        return 2
    os.makedirs(OUT, exist_ok=True)
    entries = [(n, registry[n]) for n in names]
    sheet("ring_%s" % entries[0][0] if len(entries) == 1 else "ring",
          entries, per_sheet=1 if len(entries) == 1 else 2)
    pygame.quit()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
