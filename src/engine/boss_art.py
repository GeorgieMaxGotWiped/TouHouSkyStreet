# 东方天空街 ~ Touhou Sky Street
# Boss 立绘载入：转显示格式 + 缓存
#
# assets/sprites/bosses 下的立绘按套组分子目录存放（new / another / legacy），
# 统一都是「透明背景 PNG」，所以这里只负责载入、转显示格式与缓存，不再有
# 抠白底 / 按内容裁剪那套处理。
#
# 如果手头的立绘是白底（或边缘带半透明白框）的不透明图，先用离线脚本处理成
# 透明背景 PNG 再放进 assets——那是制作流程的一步，不该让运行时去猜。
#
# 缓存按贴图路径，同一张图每个进程只解码一次；关卡载入时会用后台线程预热
# （见 preload），避免 Boss 出场瞬间卡顿。

import threading

import pygame

_sprite_cache = {}
_failed_paths = set()
_cache_lock = threading.Lock()


def load_sprite(path):
    """载入 Boss 立绘（透明背景 PNG），失败返回 None。

    结果按路径缓存，同一贴图重复调用不会重复解码；失败不写入缓存，
    下一次调用仍会重试（调用方各自有「只试一次」的兜底缓存）。
    """
    if not path:
        return None
    with _cache_lock:
        if path in _sprite_cache:
            return _sprite_cache[path]
    try:
        surface = pygame.image.load(path)
    except Exception as exc:
        with _cache_lock:
            first_failure = path not in _failed_paths
            _failed_paths.add(path)
        if first_failure:
            print(f"[BossArt] Failed to load sprite {path}: {exc}")
        return None
    try:
        surface = surface.convert_alpha()
    except Exception:
        pass
    with _cache_lock:
        _sprite_cache[path] = surface
    return surface


def preload(paths):
    """后台线程预热立绘，避免 Boss 出场瞬间因解码卡顿（已缓存的跳过）"""
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
