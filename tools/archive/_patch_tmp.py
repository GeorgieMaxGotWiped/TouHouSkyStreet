# -*- coding: utf-8 -*-

def load(p):
    raw = open(p, 'rb').read()
    if raw.startswith(b'\xef\xbb\xbf'):
        return raw.decode('utf-8-sig'), 'utf-8-sig'
    return raw.decode('utf-8'), 'utf-8'

def save(p, text, enc):
    with open(p, 'wb') as f:
        f.write(text.encode(enc))

# ---------- 1) 关底 Boss 血量 7200 -> 9000 (1.25x)，道中不变 ----------
p = 'src/stages/stage1.py'
text, enc = load(p)
old = 'hp=7200'
assert text.count(old) == 1, 'hp=7200 count != 1'
text = text.replace(old, 'hp=9000')
save(p, text, enc)
print('stage1.py hp ok')

# ---------- 2) Boss 被打空血量时清屏 ----------
p = 'src/entities/boss.py'
text, enc = load(p)
old = '''        if self.hp <= 0:
            self.alive = False
            return True'''
new = '''        if self.hp <= 0:
            self._cancel_screen_bullets()   # 击败/击破符卡时清屏，避免弹幕残留
            self.alive = False
            return True'''
assert text.count(old) == 1, 'take_damage death anchor'
text = text.replace(old, new)
save(p, text, enc)
print('boss.py clear-on-death ok')