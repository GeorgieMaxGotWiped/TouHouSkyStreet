import io
p = "tools/_smoke_death_clear.py"
s = io.open(p, encoding="utf-8").read()
s = s.replace('assert len(mx_clear) == len(near["maxor"])',
              'assert len(mx_clear) >= len(near["maxor"])   # 可能顺带清到刚登场的下一位的起手弹')
s = s.replace('assert len(st_clear) == len(near_st)',
              'assert len(st_clear) >= len(near_st)')
io.open(p, "w", encoding="utf-8", newline="\n").write(s)
print("ok")
