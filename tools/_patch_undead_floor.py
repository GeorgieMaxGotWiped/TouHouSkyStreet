# -*- coding: utf-8 -*-
import io
path = r"D:\pyz\my thingses\TouHou\src\engine\spell_bg.py"
src = io.open(path, encoding="utf-8").read()
old = """        "layers": [
            _Layer(None, panorama=dict(key="stage3_bg1", speed=16.0, fov=60), blend="alpha"),
            _Layer("soul_violet", rot_speed=0.30, scale=2.2, pulse=0.07, freq=0.35),"""
new = """        "layers": [
            _Layer(None, panorama=dict(key="stage3_bg1", speed=16.0, fov=60,
                                        floor=os.path.join(cfg.BACKGROUNDS_DIR,
                                                           "stage3", "bossfloor1.png")),
                   blend="alpha"),
            _Layer("soul_violet", rot_speed=0.30, scale=2.2, pulse=0.07, freq=0.35),"""
assert src.count(old) == 1, "anchor: %d" % src.count(old)
src = src.replace(old, new)
io.open(path, "w", encoding="utf-8", newline="\n").write(src)
print("patched spell_bg.py")
