import io
p = "RELEASE_NOTES.md"
t = io.open(p, encoding="utf-8").read()
old = " 涨到 312 / 358 发\n### 后续计划"
assert t.count(old) == 1, t.count(old)
io.open(p, "w", encoding="utf-8").write(t.replace(old, " 涨到 312 / 358 发\n\n### 后续计划"))
print("ok")
