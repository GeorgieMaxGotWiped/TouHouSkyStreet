import io
p = 'tools/_preview_clear_final.py'
t = io.open(p, encoding='utf-8').read()
old = r'admin\.cache\codex\visualizations'
new = r'admin\.codex\visualizations'
n = t.count(old)
assert n == 1, n
io.open(p, 'w', encoding='utf-8').write(t.replace(old, new))
print('patched', n)
