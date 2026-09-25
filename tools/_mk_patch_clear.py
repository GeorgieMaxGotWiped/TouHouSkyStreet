# -*- coding: utf-8 -*-
# 临时脚本：生成「击破 / 离场清弹」+「最后一波换编成」的 apply_patch 文本（每个 hunk 一个文件）
import io


def hunk(path, old, new, tag):
    assert old in io.open(path, encoding="utf-8").read(), tag
    txt = ("*** Begin Patch\n*** Update File: %s\n@@\n" % path
           + "".join("-" + ln + "\n" for ln in old.splitlines())
           + "".join("+" + ln + "\n" for ln in new.splitlines())
           + "*** End Patch\n")
    io.open("tools/_patch_%s.txt" % tag, "w", encoding="utf-8", newline="\n").write(txt)
    return tag


# ---------- 1. bullet.py：通用的「爆炸清弹」 ----------
P = "src/entities/bullet.py"
OLD = """    return Bullet(x, y, vx, vy, Bullet.TYPE_RICE, radius=2.0,
                  color=cfg.COLOR_BLUE, damage=cfg.BULLET_PLAYER_DAMAGE,
                  is_player_bullet=True, lifetime=60, homing=homing)


class BulletManager:
"""
NEW = """    return Bullet(x, y, vx, vy, Bullet.TYPE_RICE, radius=2.0,
                  color=cfg.COLOR_BLUE, damage=cfg.BULLET_PLAYER_DAMAGE,
                  is_player_bullet=True, lifetime=60, homing=homing)


def burst_cancel_bullets(bullet_manager, x, y, radius, color=(235, 245, 255)):
    \"\"\"爆炸清弹：把半径内的敌弹推进「变白自爆」动画，并补一圈扩散光效。

    用于「小怪被击破 / 残影离场」这类击破奖励（六面，见 stages/stage6.py）：
    半径由调用方按体型给。光效本身是无害的短命圆弹，所以不参与碰撞与擦弹，
    也不吃难度下的弹幕密度缩减（`add_enemy_bullet` 会放过 harmless 弹）。
    \"\"\"
    for bullet in bullet_manager.enemy_bullets:
        if bullet.harmless or bullet.cancel_timer > 0 or not bullet.alive:
            continue
        if circle_collision(x, y, radius, bullet.x, bullet.y, 0):
            bullet.start_cancel()
    for scale, frames in ((0.62, 7), (0.34, 12)):
        flash = create_bullet_angle(x, y, 0.0, 0.0, Bullet.TYPE_CIRCLE,
                                    radius=radius * scale, color=color)
        flash.manager = bullet_manager
        flash.harmless = True
        flash.lifetime = frames
        bullet_manager.add_enemy_bullet(flash)


class BulletManager:
"""
print(hunk(P, OLD, NEW, "burst"))

# ---------- 2. stage1.py：关卡基类的口径 ----------
P = "src/stages/stage1.py"
OLD = """        elif self.boss and self.boss.alive and self.boss.combat_enabled:
            enemies.append(self.boss)
        return enemies


class Stage1_SkyblockHub(Stage):
"""
NEW = """        elif self.boss and self.boss.alive and self.boss.combat_enabled:
            enemies.append(self.boss)
        return enemies

    def enemy_death_clear_radius(self, enemy):
        \"\"\"小怪被击破时炸掉周围这个半径内的敌弹（0 = 不清弹，基类默认不炸）。

        半径按体型由各面自己给（六面 = 判定半径 × CLEAR_RADIUS_PER_SIZE），
        越大的怪炸得越大；Boss 是否参与也由各面决定。
        \"\"\"
        return 0.0


class Stage1_SkyblockHub(Stage):
"""
print(hunk(P, OLD, NEW, "hook"))

# ---------- 3. menu.py：击破时调用 ----------
P = "src/ui/menu.py"
OLD = """    def _reward_enemy_kill(self, enemy):
        \"\"\"敌人被击破后的奖励结算（分数/技能经验/掉落/击杀计数）\"\"\"
        if self.practice_info:
            return
"""
NEW = """    def _death_clear_bullets(self, enemy):
        \"\"\"击破清弹（各面自定义口径）：把被击破小怪周围一定范围内的敌弹炸掉

        半径由关卡给（`Stage.enemy_death_clear_radius`，基类默认 0 = 不清弹），
        因此「越大的怪炸得越大」是各面自己的事；与奖励结算无关，练习 / Ex 面同样生效。
        \"\"\"
        radius = self.stage.enemy_death_clear_radius(enemy)
        if radius <= 0:
            return
        from src.entities.bullet import burst_cancel_bullets
        burst_cancel_bullets(self.bullet_manager, enemy.x, enemy.y, radius,
                             getattr(enemy, "color", (235, 245, 255)))

    def _reward_enemy_kill(self, enemy):
        \"\"\"敌人被击破后的奖励结算（分数/技能经验/掉落/击杀计数）\"\"\"
        self._death_clear_bullets(enemy)
        if self.practice_info:
            return
"""
print(hunk(P, OLD, NEW, "menu"))

# ---------- 4. stage6.py ----------
P = "src/stages/stage6.py"
print(hunk(P, "from src.entities.bullet import Bullet, create_bullet_aimed, create_bullet_angle\n",
           "from src.entities.bullet import (Bullet, burst_cancel_bullets, create_bullet_aimed,\n"
           "                                create_bullet_angle)\n", "s6imp"))

print(hunk(P, "GHOST_SPELL_FRAMES = 110  # 登场即起手的「告别弹」长度（帧，见 _ghost_spell）\n",
           "GHOST_SPELL_FRAMES = 110  # 登场即起手的「告别弹」长度（帧，见 _ghost_spell）\n"
           "GHOST_CLEAR_RADIUS = 180.0  # 残影离场清弹半径（立绘 190 高，正好炸掉大半个战斗区）\n",
           "s6const1"))

print(hunk(P, "HUSK_FORMATION_STEP = 40.0      # 队形里每往里 / 往下走一档就低这么多\n",
           "HUSK_FORMATION_STEP = 40.0      # 队形里每往里 / 往下走一档就低这么多\n"
           "\n"
           "# 击破清弹：小怪被击破时炸掉周围这个半径内的敌弹，半径按体型给（判定半径 × 3）\n"
           "CLEAR_RADIUS_PER_SIZE = 3.0\n",
           "s6const2"))

OLD = """        for ghost in self.ghosts[:]:
            # 一小段削弱版符卡：登场那一帧就起手（窗口外直接返回）
            _ghost_spell(ghost, bullet_manager, player_x, player_y)
            ghost["age"] += 1
            if ghost["age"] >= ghost["max_age"]:
                self.ghosts.remove(ghost)
                if not self.ghosts and self.ghost_bg is not None:
                    self.ghost_bg.begin_fade_out()
"""
NEW = """        for ghost in self.ghosts[:]:
            # 一小段削弱版符卡：登场那一帧就起手（窗口外直接返回）
            _ghost_spell(ghost, bullet_manager, player_x, player_y)
            ghost["age"] += 1
            if ghost["age"] >= ghost["max_age"]:
                self.ghosts.remove(ghost)
                # 离场清弹：这么大的一位门徒退场，把它周围一圈弹幕一起炸掉
                burst_cancel_bullets(bullet_manager, ghost["x"], ghost["y"],
                                     GHOST_CLEAR_RADIUS, GHOST_GLOWS[ghost["id"]])
                if not self.ghosts and self.ghost_bg is not None:
                    self.ghost_bg.begin_fade_out()

    def enemy_death_clear_radius(self, enemy):
        \"\"\"六面：小怪被击破时炸掉周围的敌弹，半径按体型给（判定半径 × 3）

        凋零游魂 42 / 矿工 48 / 骑士 57 / 守卫与兵马俑 60 / Skeleton Lord 66 /
        巨像 90；Boss（Kaeman）不走这条 —— 击破 Boss 的那一下不清屏。
        \"\"\"
        if isinstance(enemy, Boss):
            return 0.0
        return enemy.size * CLEAR_RADIUS_PER_SIZE
"""
print(hunk(P, OLD, NEW, "s6ghost"))

OLD = """        self.final_wave = EnemyWave([
            WitherColossusEnemy(288, -70, deploy_y=150),
            WitherTerracottaEnemy(110, -40, deploy_y=150),
            WitherTerracottaEnemy(466, -40, deploy_y=150),
            WitherGuardEnemy(150, _top_spawn(-50)),
            WitherGuardEnemy(430, _top_spawn(-50)),
            WitherKnightEnemy(220, -80),
            WitherKnightEnemy(360, -80),
        ], name="Final Defense")
"""
NEW = """        self.final_wave = EnemyWave([
            WitherColossusEnemy(288, -70, deploy_y=94),
            SkeletonLordEnemy(side=-1, y=204), SkeletonLordEnemy(side=1, y=204),
            WitherGuardEnemy(196, _top_spawn(-50)),
            WitherGuardEnemy(380, _top_spawn(-50)),
        ], name="Final Defense")
"""
print(hunk(P, OLD, NEW, "s6final"))
print("patches written")
