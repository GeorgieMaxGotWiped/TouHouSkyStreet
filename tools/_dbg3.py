
import os, sys, traceback
os.environ["SDL_VIDEODRIVER"] = "dummy"
import pygame
import numpy as np
sys.path.insert(0, os.getcwd())
from src.engine import settings as cfg

pygame.init()
screen = pygame.display.set_mode((576, 670))

def mk_rgba(rgb, alpha):
    surf = pygame.Surface((rgb.shape[1], rgb.shape[0]), pygame.SRCALPHA)
    pygame.surfarray.blit_array(surf, np.ascontiguousarray(rgb, dtype=np.uint8))
    pa = pygame.surfarray.pixels_alpha(surf)
    pa[:, :] = np.ascontiguousarray(alpha, dtype=np.uint8)
    del pa
    return surf

def step(name, fn):
    try:
        r = fn()
        print("  OK", name, "->", r if not hasattr(r, 'get_size') else ('surf ' + str(r.get_size())))
        return r
    except Exception:
        print("  FAIL", name)
        traceback.print_exc()
        return None

for f in ["Luxurious_Spool.png", "Arachne's_Fang.png", "Arack.png"]:
    print("====", f)
    path = os.path.join(cfg.ASSETS_DIR, "backgrounds", "stage1", f)
    img = step("load", lambda: pygame.image.load(path))
    if img is None: continue
    w, h = img.get_size()
    rgb = step("array3d", lambda: pygame.surfarray.array3d(img).astype(np.float32))
    if rgb is None: continue
    lum = rgb.mean(axis=2)
    alpha = np.clip((lum - 6.0) / 24.0, 0.0, 1.0)
    print("  mask any:", bool((alpha > 0.05).any()))
    ys, xs = np.nonzero(alpha > 0.05)
    if not len(ys): continue
    pad = 8
    y0, y1 = max(0, int(ys.min()) - pad), min(h - 1, int(ys.max()) + pad)
    x0, x1 = max(0, int(xs.min()) - pad), min(w - 1, int(xs.max()) + pad)
    crop_rgb = rgb[y0:y1 + 1, x0:x1 + 1]
    crop_a = alpha[y0:y1 + 1, x0:x1 + 1]
    tmp = step("make_rgba", lambda: mk_rgba(crop_rgb, crop_a * 255.0))
    if tmp is None: continue
    target_h = 100
    s = target_h / float(tmp.get_height())
    nw = max(1, int(tmp.get_width() * s))
    icon = step("smoothscale", lambda: pygame.transform.smoothscale(tmp, (nw, target_h)))
    if icon is None:
        icon = step("scale_fallback", lambda: pygame.transform.scale(tmp, (nw, target_h)))
    if icon is None: continue
    arr = step("array3d2", lambda: pygame.surfarray.array3d(icon).astype(np.float32))
    if arr is None: continue
    a_arr = step("array_alpha", lambda: pygame.surfarray.array_alpha(icon).astype(np.float32))
    if a_arr is None: continue
    step("make_rgba2", lambda: mk_rgba(arr, a_arr))
pygame.quit()
