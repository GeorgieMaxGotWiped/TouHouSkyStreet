# -*- coding: utf-8 -*-
import io

p = "tools/_smoke_death_clear.py"
s = io.open(p, encoding="utf-8").read()
i0 = s.index("# ---------- 2.")
i1 = s.index("# ---------- 3.")
new = '''# ---------- 2. 残影离场：大范围清弹 ----------
stage = s6.Stage6_FinalApproach(); stage.setup_waves()
bm2 = BulletManager()
for _ in range(78 * 60 - 3):               # 停在 Storm 登场前几帧：此刻 Maxor 仍在场
    stage.update(1 / 60.0, bm2, 288.0, 560.0); bm2.update(1 / 60.0, 288.0, 560.0)
assert [x["id"] for x in stage.ghosts] == ["maxor"], [x["id"] for x in stage.ghosts]
bm2.enemy_bullets.clear()
near = {}
for gid in ("maxor", "storm"):
    gx, gy = s6.GHOST_POSITIONS[gid]
    seed(bm2, gx, gy, n=14, ring=260.0)
    near[gid] = [b for b in bm2.enemy_bullets if dist(b, gx, gy) <= s6.GHOST_CLEAR_RADIUS]
for _ in range(12):                        # 跨过 78s：Maxor 离场 + Storm 登场
    stage.update(1 / 60.0, bm2, 288.0, 560.0); bm2.update(1 / 60.0, 288.0, 560.0)
assert [x["id"] for x in stage.ghosts] == ["storm"], [x["id"] for x in stage.ghosts]
mx, my = s6.GHOST_POSITIONS["maxor"]
hung = [b for b in bm2.enemy_bullets if b.cancel_timer > 0]
mx_clear = [b for b in hung if dist(b, mx, my) <= s6.GHOST_CLEAR_RADIUS]
print("[2] 残影离场半径 %.0f：Maxor 周围 %d 发里清了 %d 发（离场那一帧）"
      % (s6.GHOST_CLEAR_RADIUS, len(near["maxor"]), len(mx_clear)))
assert len(mx_clear) == len(near["maxor"])

# Storm 离场（86s、Goldor 登场）同样清弹
while stage.timer < 86 * 60 - 3:
    stage.update(1 / 60.0, bm2, 288.0, 560.0); bm2.update(1 / 60.0, 288.0, 560.0)
sx, sy = s6.GHOST_POSITIONS["storm"]
near_st = [b for b in bm2.enemy_bullets if dist(b, sx, sy) <= s6.GHOST_CLEAR_RADIUS]
for _ in range(12):
    stage.update(1 / 60.0, bm2, 288.0, 560.0); bm2.update(1 / 60.0, 288.0, 560.0)
st_clear = [b for b in bm2.enemy_bullets
            if b.cancel_timer > 0 and dist(b, sx, sy) <= s6.GHOST_CLEAR_RADIUS]
print("    Storm 离场时：周围 %d 发里清了 %d 发" % (len(near_st), len(st_clear)))
assert len(st_clear) == len(near_st)

'''
io.open(p, "w", encoding="utf-8", newline="\n").write(s[:i0] + new + s[i1:])
print("rewrote section 2")
