# -*- coding: utf-8 -*-
import io

def rd(p):
    return io.open(p, "r", encoding="utf-8", newline="").read().split("\n")

def hunk(lines, i0, i1, new, ctx=3):
    out = []
    for j in range(i0 - ctx, i0):
        out.append(" " + lines[j])
    for j in range(i0, i1):
        out.append("-" + lines[j])
    for ln in new:
        out.append("+" + ln)
    for j in range(i1, i1 + ctx):
        out.append(" " + lines[j])
    return out

g = rd("src/stages/stage6.py")

def close_of(start):
    for i in range(start, len(g)):
        if g[i] == "        )":
            return i + 1
    raise SystemExit("no close")

hunks = []

# A) 新增 _top_spawn 助手 + Husk 速度注释（插在 class WitherHuskEnemy 之前）
i = g.index("class WitherHuskEnemy(Enemy):")
hunks.append(hunk(g, i, i + 1, [
    "# 「直接出现在画面里」的两种小怪（凋零守卫 / 凋零矿工）：不再从区域外落下，",
    "# 而是直接出现在战斗区上部。原来的「区外高度」按 _top_spawn 换算成画面内落点，",
    "# 并且保持原来的先后关系 —— 原来 y 越负（越高）的，落点也越高。",
    "TOP_SPAWN_LOWEST_Y = 220.0    # 落点最低的一档（对应原来最靠画面上缘的 -24）",
    "TOP_SPAWN_SPREAD = 2.4        # 原高度每高 1px，落点就高 2.4px",
    "",
    "",
    "def _top_spawn(y_above):",
    '    """把原来的「区域外高度」换算成画面内的落点（越高的原高度 -> 越高的落点）。"""',
    "    return int(round(TOP_SPAWN_LOWEST_Y + (y_above + 24) * TOP_SPAWN_SPREAD))",
    "",
    "",
    "class WitherHuskEnemy(Enemy):",
]))

# B) Husk 速度 1.5 -> 3.0
i = g.index("        self.move_speed = 1.5")
hunks.append(hunk(g, i, i + 1, ["        self.move_speed = 3.0       # 全道中最快的一档（原 1.5）"]))

# C) march_waves 整块替换
i = g.index("        # 前半段：亡灵军队防线（0 ~ 42s，逐渐加强）")
j = close_of(g.index("        march_waves = ("))
new_march = """        # 前半段：亡灵军队防线（0 ~ 42s，逐渐加强）
        # 凋零守卫 / 凋零矿工直接在画面内上部出现（_top_spawn 换算落点，见其定义）；
        # 凋零游魂仍从区域外落下，速度 3.0，每波数量为原来的两倍。
        march_waves = (
            # 第一梯队：左右两位 Skeleton Lord 同时横向切入（左右对称入场）
            (4 * 60, EnemyWave([
                SkeletonLordEnemy(side=-1), SkeletonLordEnemy(side=1)],
                name="Skeleton Lords")),
            (9 * 60, EnemyWave([
                WitherGuardEnemy(140, _top_spawn(-30)), WitherGuardEnemy(430, _top_spawn(-30)),
                WitherHuskEnemy(200, -60), WitherHuskEnemy(150, -88),
                WitherHuskEnemy(380, -60), WitherHuskEnemy(430, -88)],
                name="Undead Line")),
            (14 * 60, EnemyWave([
                WitherMinerEnemy(80, _top_spawn(-24)), WitherMinerEnemy(288, _top_spawn(-56)),
                WitherMinerEnemy(492, _top_spawn(-24)), WitherHuskEnemy(160, -70),
                WitherHuskEnemy(105, -98), WitherHuskEnemy(420, -70),
                WitherHuskEnemy(475, -98)], name="Miner Phalanx")),
            (19 * 60, EnemyWave([
                WitherGuardEnemy(110, _top_spawn(-40)), WitherGuardEnemy(460, _top_spawn(-40)),
                WitherMinerEnemy(200, _top_spawn(-60)), WitherMinerEnemy(380, _top_spawn(-60)),
                WitherHuskEnemy(288, -80), WitherHuskEnemy(232, -108),
                WitherHuskEnemy(344, -108)], name="Fortress Gate")),
            (24 * 60, EnemyWave([
                WitherMinerEnemy(90, _top_spawn(-24)), WitherMinerEnemy(250, _top_spawn(-56)),
                WitherMinerEnemy(400, _top_spawn(-24)), WitherMinerEnemy(500, _top_spawn(-56)),
                WitherGuardEnemy(288, _top_spawn(-70))], name="Wither Labor")),
            (29 * 60, EnemyWave([
                WitherGuardEnemy(130, _top_spawn(-40)), WitherGuardEnemy(320, _top_spawn(-70)),
                WitherGuardEnemy(450, _top_spawn(-40)), WitherHuskEnemy(80, -80),
                WitherHuskEnemy(150, -108), WitherHuskEnemy(230, -90),
                WitherHuskEnemy(300, -118), WitherHuskEnemy(420, -90),
                WitherHuskEnemy(490, -118)], name="Guard Wall")),
            (34 * 60, EnemyWave([
                WitherHuskEnemy(70, -24), WitherHuskEnemy(180, -56),
                WitherHuskEnemy(288, -80), WitherHuskEnemy(400, -56),
                WitherHuskEnemy(500, -24), WitherHuskEnemy(40, -42),
                WitherHuskEnemy(150, -74), WitherHuskEnemy(288, -108),
                WitherHuskEnemy(430, -74), WitherHuskEnemy(540, -42),
                WitherMinerEnemy(240, _top_spawn(-90)),
                WitherMinerEnemy(350, _top_spawn(-90))], name="Last March")),
        )""".split("\n")
hunks.append(hunk(g, i, j, new_march))

# D) fortress_waves 整块替换
i = g.index("        fortress_waves = (")
j = close_of(i)
new_fort = """        fortress_waves = (
            (68 * 60, EnemyWave([
                WitherGuardEnemy(130, _top_spawn(-40)), WitherGuardEnemy(430, _top_spawn(-40)),
                WitherKnightEnemy(288, -70)], name="Fortress Wall")),
            (75 * 60, EnemyWave([
                WitherMinerEnemy(110, _top_spawn(-40)), WitherMinerEnemy(360, _top_spawn(-40)),
                WitherKnightEnemy(210, -70)], name="Siege Detail")),
            (82 * 60, EnemyWave([
                WitherKnightEnemy(110, -50), WitherKnightEnemy(280, -50),
                WitherKnightEnemy(460, -50), WitherGuardEnemy(200, _top_spawn(-80)),
                WitherGuardEnemy(380, _top_spawn(-80))], name="Knight Order")),
            (90 * 60, EnemyWave([
                WitherTerracottaEnemy(160, -40, deploy_y=150),
                WitherTerracottaEnemy(420, -40, deploy_y=150),
                WitherGuardEnemy(288, _top_spawn(-60))], name="Golem Ward")),
        )""".split("\n")
hunks.append(hunk(g, i, j, new_fort))

# E) 最后防线的两位守卫
i = g.index("            WitherGuardEnemy(150, -50),")
hunks.append(hunk(g, i, i + 2, [
    "            WitherGuardEnemy(150, _top_spawn(-50)),",
    "            WitherGuardEnemy(430, _top_spawn(-50)),",
]))

patch = ["*** Begin Patch", "*** Update File: src/stages/stage6.py"]
for h in hunks:
    patch += ["@@"] + h
patch += ["*** End Patch"]
io.open("tools/_patch_topspawn.txt", "w", encoding="utf-8", newline="\n").write("\n".join(patch))
print("hunks:", len(hunks))
