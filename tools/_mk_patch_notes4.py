# -*- coding: utf-8 -*-
import io
p = "RELEASE_NOTES.md"
t = io.open(p, encoding="utf-8").read()
lines = t.split("\n")
for i in (126, 136, 137, 138, 139, 140):
    print(i + 1, repr(lines[i][:80]))
i = 137
patch = ["*** Begin Patch", "*** Update File: RELEASE_NOTES.md", "@@"]
patch.append(" " + lines[i])
patch.append(" " + lines[i + 1])
patch.append("+" + (
    " - 六面小怪被击破 / 门徒残影离场时会炸掉周围一圈敌弹（`src/entities/bullet.py`、"
    "`src/stages/stage1.py`、`src/stages/stage6.py`、`src/ui/menu.py`）：新增 `burst_cancel_bullets()` —— "
    "把半径内的敌弹推进游戏里原有的「变白自爆」动画（不是瞬间消失），另补两圈无害白光展现爆炸范围"
    "（光效是 `harmless` 弹，不参与碰撞与擦弹，也不吃难度下的密度缩减）；清弹半径按体型给"
    "（`CLEAR_RADIUS_PER_SIZE = 3.0`，即判定半径 × 3）：凋零游魂 42 / 矿工 48 / 骑士 57 / "
    "守卫与兵马俑 60 / Skeleton Lord 66 / 巨像 90，四位残影固定 180（立绘 190 高，约炸掉大半个战斗区，"
    "白光取各自残影的主色）"))
patch.append("+" + (
    "   - 挂点：`Stage` 新增钩子 `enemy_death_clear_radius(enemy)`（基类返回 0 = 不清弹，其余各面画面不变），"
    "六面覆写它；击破奖励这一条走 `PlayingState._death_clear_bullets()`（在 `_reward_enemy_kill` 开头调用，"
    "符卡练习与 Ex 面同样生效），残影离场则在 `_update_ghosts` 里直接调用"))
patch.append("+" + (
    "   - Kaeman 不走这条：击破 Boss 的那一下不清屏（`enemy_death_clear_radius` 见到 `Boss` 返回 0）"))
patch.append("+")
patch.append("+" + (
    " - 六面王座前的最后防线（100s）换编成（`src/stages/stage6.py`）：原来这一波是 12 只小怪的混编，"
    "现在只有 5 只 —— 左右两位 Skeleton Lord（从画面左右外侧 x=±622 横向切入、停在 x=150 / 426）＋"
    "上方一位 Wither Colossus（x=288，从 y=-70 下降到 y=94 悬停）＋两位 Wither Guard"
    "（直接出现在画面内 y=118，x=196 / 380，随后照旧缓缓下落）"))
patch.append("+" + (
    "   - 上面「实测在场」那条里的 100s Final Defense 数字随之更新：12 只 → 7 只（含开场未被击破的两位 Lord，"
    "实战打完是 5 只）、同屏敌弹 246 → 192 发；29s Guard Wall 20 只 / 34s Last March 28 只 的敌机数不变，"
    "同屏敌弹因 Skeleton Lord 加密而由 289 / 322 涨到 312 / 358 发"))
patch.append(" " + lines[i + 2])
patch.append(" " + lines[i + 3])
patch.append("*** End Patch")
io.open("tools/_patch_notes4.txt", "w", encoding="utf-8").write("\n".join(patch) + "\n")
print("written", len(patch))
