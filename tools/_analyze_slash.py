# -*- coding: utf-8 -*-
import os, glob
from PIL import Image

d = r"D:\pyz\my thingses\TouHou\previews\kaeman_slash"
OX, OY = 50, 25
W, H = 576, 670

def count_colors(path):
    im = Image.open(path).convert("RGB")
    px = im.load()
    bright_red = 0
    dark_red = 0
    white_core = 0
    for y in range(OY, OY + H, 2):
        for x in range(OX, OX + W, 2):
            r, g, b = px[x, y]
            if r > 150 and g < 110 and b < 120:
                bright_red += 1
            if 70 <= r <= 200 and g < 80 and b < 90:
                dark_red += 1
            if r > 220 and g > 190 and b > 190:
                white_core += 1
    return bright_red, dark_red, white_core

for p in sorted(glob.glob(os.path.join(d, "*.png"))):
    name = os.path.basename(p)
    if name.startswith("small"):
        continue
    br, dr, wc = count_colors(p)
    print("%-26s bright_red=%5d dark_red=%5d white_core=%5d" % (name, br, dr, wc))