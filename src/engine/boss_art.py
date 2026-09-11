# 东方天空街 ~ Touhou Sky Street
# Boss 立绘载入：白底抠除 + 内容裁剪 + 缓存
#
# assets/sprites/bosses 下的立绘按套组分子目录存放（new / another / legacy），
# 其中部分套组是「白底不透明 PNG」。游戏需要透明背景立绘，因此这里在载入时
# 做一次「白底抠除」（从四边洪水填充，避免误伤角色身上的白色区域）再按内容
# 包围盒裁剪，使新立绘在游戏内的可视大小与旧立绘基本一致。
# 处理结果按贴图路径缓存，同一张图每个进程只处理一次。

import threading

import numpy as np
import pygame

# 单通道最小值 ≥ 该值视为「白色背景」候选
WHITE_CHANNEL_MIN = 238
# 洪水填充先在 1/COARSE_BLOCK 的粗网格上连通，再回到像素级补齐边缘
COARSE_BLOCK = 4
# 边缘羽化：白度过渡的灰度跨度（越小边缘越硬）
FEATHER_SPAN = 45
# 裁剪包围盒时视为「有内容」的透明度阈值
ALPHA_CUTOFF = 8
# 抠图处理的目标分辨率区间（游戏内立绘最大展示高度为 648px，留一倍余量）
MIN_SOURCE_DIM = 1024
MAX_SOURCE_DIM = 1536
# 四边采样中「不透明纯白」占比超过该值时，认为贴图带白底
WHITE_BORDER_RATIO = 0.5

_sprite_cache = {}
_failed_paths = set()
_cache_lock = threading.Lock()

# pygame 2.1 起 tostring/fromstring 更名为 tobytes/frombytes，这里做兼容
_image_to_bytes = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
_image_from_bytes = getattr(pygame.image, "frombytes", None) or pygame.image.frombuffer


def _dilate(mask):
    """四邻域膨胀（返回新数组，不修改入参）"""
    out = mask.copy()
    out[1:, :] |= mask[:-1, :]
    out[:-1, :] |= mask[1:, :]
    out[:, 1:] |= mask[:, :-1]
    out[:, :-1] |= mask[:, 1:]
    return out


def _downscale(rgb, factor):
    """整数倍面积平均缩小（factor <= 1 时原样返回）"""
    if factor <= 1:
        return rgb
    height, width = rgb.shape[:2]
    height2, width2 = (height // factor) * factor, (width // factor) * factor
    if height2 == 0 or width2 == 0:
        return rgb
    blocks = rgb[:height2, :width2].astype(np.uint16)
    blocks = blocks.reshape(height2 // factor, factor, width2 // factor, factor, rgb.shape[2])
    return (blocks.sum(axis=(1, 3)) // (factor * factor)).astype(np.uint8)


def _work_factor(width, height):
    """按原图尺寸选择处理倍率，使处理结果的最长边不低于 MIN_SOURCE_DIM"""
    longest = max(width, height)
    factor = 1
    while factor < 4 and longest // (factor * 2) >= MIN_SOURCE_DIM:
        factor *= 2
    return factor


def remove_white_background(rgb, threshold=WHITE_CHANNEL_MIN, block=COARSE_BLOCK):
    """把白色背景抠成透明，返回 RGBA 数组（背景 α=0，边缘按白度羽化）。

    只处理「与图像四边相连」的白色区域，因此角色身上的白色（白发、白袍、
    高光）不会被误删。
    """
    height, width = rgb.shape[:2]
    min_channel = rgb.min(axis=2)
    candidate = min_channel >= threshold

    # 1) 粗网格：整块全白才算背景候选（保守），连通填充开销降到 1/block²
    rows = (height + block - 1) // block
    cols = (width + block - 1) // block
    padded = np.zeros((rows * block, cols * block), dtype=bool)
    padded[:height, :width] = candidate
    coarse = padded.reshape(rows, block, cols, block).all(axis=(1, 3))

    # 2) 从图像四边向内洪水填充（白底必定与边框相连）
    background = np.zeros_like(coarse)
    background[0, :] = coarse[0, :]
    background[-1, :] = coarse[-1, :]
    background[:, 0] = coarse[:, 0]
    background[:, -1] = coarse[:, -1]
    while True:
        grown = _dilate(background) & coarse
        if grown.sum() == background.sum():
            break
        background = grown

    # 3) 回到像素级：补齐粗网格漏掉的边缘（块内混有内容时整块被保留过）
    filled = np.repeat(np.repeat(background, block, 0), block, 1)[:height, :width] & candidate
    for _ in range(block + 3):
        grown = _dilate(filled) & candidate
        if grown.sum() == filled.sum():
            break
        filled = grown

    # 4) α 通道：背景全透明，紧贴背景的一圈按白度羽化
    alpha = np.full((height, width), 255, dtype=np.int16)
    alpha[filled] = 0
    edge = _dilate(filled) & ~filled
    if edge.any():
        whiteness = (threshold - min_channel[edge]).astype(np.float32)
        alpha[edge] = np.clip(whiteness * (255.0 / FEATHER_SPAN), 0, 255).astype(np.int16)

    rgba = np.dstack([rgb, alpha.astype(np.uint8)])
    # 羽化边缘的像素是「角色色 + 白底」的混合，反解出原色避免白边
    blend = edge & (alpha > ALPHA_CUTOFF) & (alpha < 250)
    if blend.any():
        ratio = (alpha[blend].astype(np.float32) / 255.0)[:, None]
        rgb_mix = (rgb[blend].astype(np.float32) - (1.0 - ratio) * 255.0) / ratio
        rgba[blend, :3] = np.clip(rgb_mix, 0, 255).astype(np.uint8)
    return rgba


def crop_to_content(rgba, cutoff=ALPHA_CUTOFF, pad=1):
    """按不透明内容裁掉四周空白（保留 pad 像素边距）"""
    height, width = rgba.shape[:2]
    rows = np.where((rgba[:, :, 3] > cutoff).any(axis=1))[0]
    cols = np.where((rgba[:, :, 3] > cutoff).any(axis=0))[0]
    if len(rows) == 0 or len(cols) == 0:
        return rgba
    top = max(0, int(rows[0]) - pad)
    bottom = min(height, int(rows[-1]) + 1 + pad)
    left = max(0, int(cols[0]) - pad)
    right = min(width, int(cols[-1]) + 1 + pad)
    if (top, bottom, left, right) == (0, height, 0, width):
        return rgba
    return rgba[top:bottom, left:right]


def _white_border_ratio(rgb, alpha):
    """四边采样中「不透明且接近纯白」的像素占比（判断贴图是否带白底）"""
    height, width = alpha.shape[:2]
    band = max(1, min(height, width) // 100)
    parts_rgb = (rgb[:band].reshape(-1, 3), rgb[-band:].reshape(-1, 3),
                 rgb[:, :band].reshape(-1, 3), rgb[:, -band:].reshape(-1, 3))
    parts_alpha = (alpha[:band].reshape(-1), alpha[-band:].reshape(-1),
                   alpha[:, :band].reshape(-1), alpha[:, -band:].reshape(-1))
    border_rgb = np.concatenate(parts_rgb)
    border_alpha = np.concatenate(parts_alpha)
    white = (border_rgb.min(axis=1) >= WHITE_CHANNEL_MIN) & (border_alpha >= 250)
    return float(white.mean())


def _surface_from_rgba(rgba):
    """RGBA 数组 → pygame Surface（转显示格式失败时返回原表面）"""
    height, width = rgba.shape[:2]
    surface = _image_from_bytes(rgba.tobytes(), (width, height), "RGBA")
    try:
        surface = surface.convert_alpha()
    except Exception:
        pass
    return surface


def _build_sprite(path):
    """载入贴图：带白底时抠除并按内容裁剪，否则原样返回"""
    image = pygame.image.load(path)
    width, height = image.get_size()
    raw = _image_to_bytes(image, "RGBA")
    pixels = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4)
    if _white_border_ratio(pixels[:, :, :3], pixels[:, :, 3]) <= WHITE_BORDER_RATIO:
        # 已是透明背景立绘：保持原样（含边距），与旧套组表现一致
        try:
            return image.convert_alpha()
        except Exception:
            return image

    rgb = _downscale(pixels[:, :, :3], _work_factor(width, height))
    surface = _surface_from_rgba(crop_to_content(remove_white_background(rgb)))
    longest = max(surface.get_size())
    if longest > MAX_SOURCE_DIM:
        scale = MAX_SOURCE_DIM / float(longest)
        surface = pygame.transform.smoothscale(
            surface, (max(1, int(round(surface.get_width() * scale))),
                      max(1, int(round(surface.get_height() * scale)))))
    return surface


def load_sprite(path):
    """载入 Boss 立绘（白底自动抠除、按内容裁剪），失败返回 None。

    结果按路径缓存，同一贴图重复调用不会重复处理；失败不写入缓存，
    下一次调用仍会重试（调用方各自有「只试一次」的兜底缓存）。
    """
    if not path:
        return None
    with _cache_lock:
        if path in _sprite_cache:
            return _sprite_cache[path]
    try:
        surface = _build_sprite(path)
    except Exception as exc:
        with _cache_lock:
            first_failure = path not in _failed_paths
            _failed_paths.add(path)
        if first_failure:
            print(f"[BossArt] Failed to load sprite {path}: {exc}")
        return None
    with _cache_lock:
        _sprite_cache[path] = surface
    return surface


def preload(paths):
    """后台线程预热立绘，避免 Boss 出场瞬间因抠图卡顿（已缓存的跳过）"""
    with _cache_lock:
        pending = [p for p in dict.fromkeys(paths or ())
                   if p and p not in _sprite_cache and p not in _failed_paths]
    if not pending:
        return None

    def worker():
        for path in pending:
            load_sprite(path)

    thread = threading.Thread(target=worker, name="boss-art-preload", daemon=True)
    thread.start()
    return thread
