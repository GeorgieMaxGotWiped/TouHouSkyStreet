import io
p = "tools/_smoke_death_clear.py"
s = io.open(p, encoding="utf-8").read()
old = 'assert len(st_clear) >= len(near_st)'
new = ('miss = [b for b in near_st if b.alive and b.cancel_timer <= 0\n'
       '        and dist(b, sx, sy) <= s6.GHOST_CLEAR_RADIUS]\n'
       'assert not miss, len(miss)      # 半径内还「活着且没被清」的应为 0')
assert s.count(old) == 1
io.open(p, "w", encoding="utf-8", newline="\n").write(s.replace(old, new))
print("ok")
