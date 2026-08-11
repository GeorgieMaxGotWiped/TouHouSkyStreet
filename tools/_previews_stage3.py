# -*- coding: utf-8 -*-
# 三面预览：三套符卡背景 3 帧拼接 + Watcher/Bonzo 符卡战斗截图
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
import pygame
import sys
sys.path.insert(0, os.getcwd())
from src.engine import settings as cfg
from src.entities.bullet import BulletManager

pygame.init()
screen = pygame.display.set_mode((cfg.SCREEN_WIDTH, cfg.SCREEN_HEIGHT))
area = pygame.Surface((cfg.BATTLE_AREA_WIDTH, cfg.BATTLE_AREA_HEIGHT))
outdir = "previews"

from src.engine.spell_bg import SpellBackground
for style in ("watcher", "undead", "bonzo"):
    bg = SpellBackground("test", bg_style=style)
    montage = pygame.Surface((cfg.BATTLE_AREA_WIDTH * 3, cfg.BATTLE_AREA_HEIGHT))
    for i, ft in enumerate((40, 110, 200)):
        while bg.timer < ft:
            bg.update(1 / 60)
        bg.draw(area)
        montage.blit(area, (i * cfg.BATTLE_AREA_WIDTH, 0))
    pygame.image.save(montage, os.path.join(outdir, "spellbg_stage3_%s_3frames.png" % style))
print("spellbg montages saved")

from src.stages.stage3 import Stage3_CatacombsF1, BONZO_REVIVE_HP
PX, PY = cfg.BATTLE_AREA_WIDTH / 2, cfg.BATTLE_AREA_HEIGHT - 80


def run(stage, bm, frames, damage=None, dmg=25, per=4):
    for _ in range(frames):
        stage.update(1 / 60, bm, PX, PY)
        if damage is not None and damage.alive:
            for _ in range(per):
                if damage.take_damage(dmg):
                    break


def shot(stage, name):
    stage.draw(screen, cfg.BATTLE_OFFSET_X, cfg.BATTLE_OFFSET_Y)
    pygame.image.save(screen, name)
    print("saved", name)


# Watcher 符卡战斗
stage = Stage3_CatacombsF1()
stage.setup_waves()
bm = BulletManager()
while stage.phase != "mid_boss":
    stage.update(1 / 60, bm, PX, PY)
run(stage, bm, 150, damage=stage.mid_boss)
mb = stage.mid_boss
# 确保进入符卡
guard = 0
while (mb.alive and mb.phase != "spell" and guard < 600):
    run(stage, bm, 20, damage=mb)
    guard += 20
assert mb.phase == "spell", mb.phase
print("watcher spell:", mb.current_spell.name, "bg:", mb.spell_bg.style if mb.spell_bg else None)
run(stage, bm, 120, damage=mb)   # 让符卡背景淡入完成
shot(stage, "_stage3_preview_watcher_spell.png")

# 打完 Watcher -> 对话 -> Bonzo 一阶段唤符
while stage.phase != "dialogue":
    if stage.phase == "mid_boss" and mb.alive:
        run(stage, bm, 20, damage=mb)
    else:
        stage.update(1 / 60, bm, PX, PY)
stage.on_dialogue_end()
bonzo = stage.boss
guard = 0
while (bonzo.alive and bonzo.current_spell is None and guard < 900):
    run(stage, bm, 20, damage=bonzo)
    guard += 20
assert bonzo.current_spell is not None and "Undead Legion" in bonzo.current_spell.name
print("bonzo spell1:", bonzo.current_spell.name, "bg:", bonzo.spell_bg.style if bonzo.spell_bg else None)
run(stage, bm, 40)                       # 无伤推进，让符卡背景淡入完成
shot(stage, "_stage3_preview_bonzo_undead.png")

# 打到复活（球符）
while bonzo.alive and (bonzo.current_spell is None or "Balloon" not in bonzo.current_spell.name):
    run(stage, bm, 20, damage=bonzo)
    guard += 20
assert bonzo.current_spell is not None and "Balloon" in bonzo.current_spell.name
assert bonzo.hp == BONZO_REVIVE_HP
print("bonzo last spell:", bonzo.current_spell.name, "bg:", bonzo.spell_bg.style if bonzo.spell_bg else None)
run(stage, bm, 40)                       # 无伤推进，让符卡背景淡入完成
shot(stage, "_stage3_preview_bonzo_balloon.png")

pygame.quit()
print("ALL OK")