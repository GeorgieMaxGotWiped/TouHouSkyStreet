# -*- coding: utf-8 -*-
import os, subprocess, sys, time
env = dict(os.environ)
env["SDL_VIDEODRIVER"] = "dummy"
py = r"C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
log = open(r"D:\pyz\my thingses\TouHou\tools\_boot_out.txt", "w", encoding="utf-8", errors="replace")
p = subprocess.Popen([py, r"D:\pyz\my thingses\TouHou\main.py"],
                     cwd=r"D:\pyz\my thingses\TouHou", env=env,
                     stdout=log, stderr=subprocess.STDOUT)
try:
    rc = p.wait(timeout=8)
    print("exited early, code=", rc)
except subprocess.TimeoutExpired:
    p.kill()
    print("still running after 8s (boot OK, killed)")
log.close()
print("---- log tail ----")
with open(r"D:\pyz\my thingses\TouHou\tools\_boot_out.txt", encoding="utf-8", errors="replace") as f:
    txt = f.read()
print(txt[-1500:] if txt else "(empty)")
