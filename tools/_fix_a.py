import io
p = 'tools/_probe_final_wave.py'
t = io.open(p, encoding='utf-8').read()
t = t.replace('import pygame\nfrom src.entities.bullet', 'import pygame\npygame.init()\npygame.display.set_mode((960, 720))\nfrom src.entities.bullet', 1)
io.open(p, 'w', encoding='utf-8').write(t)
print('ok')
