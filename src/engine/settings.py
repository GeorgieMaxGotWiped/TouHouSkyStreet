# 东方天空街 ~ Touhou Sky Street
# 基于 Hypixel Skyblock 的东方Project同人STG
# 游戏全局设置

import os
import sys
import json

# --- 路径 ---
# PyInstaller 打包后使用 _MEIPASS 解压目录，源码运行时使用项目根
if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(BASE_DIR, "assets")
SOUNDS_DIR = os.path.join(ASSETS_DIR, "sounds")
MUSIC_DIR = os.path.join(SOUNDS_DIR, "musics")
SFX_DIR = os.path.join(SOUNDS_DIR, "se")
BACKGROUNDS_DIR = os.path.join(ASSETS_DIR, "backgrounds")
SRC_DIR = os.path.join(BASE_DIR, "src")

# --- 用户配置（音量等）：源码运行保存到项目根目录，打包后保存到 exe 同目录 ---
DEFAULT_MUSIC_VOLUME = 0.8
DEFAULT_SFX_VOLUME = 0.7
DEFAULT_GAME_SPEED = 1.0
GAME_SPEED_MIN = 0.25
GAME_SPEED_MAX = 2.0
GAME_SPEED_STEP = 0.25

# --- 显示：输出分辨率 / 缩放模式（实现见 src/engine/display.py）---
# 选项均为内部逻辑分辨率 960x720 的整数倍：窗口模式下窗口取该尺寸，
# 全屏（无边框）时窗口为显示器原生尺寸，由缩放模式决定画面铺多大。
RESOLUTIONS = ((960, 720), (1920, 1440), (2880, 2160), (3840, 2880))
RESOLUTION_LABELS = ("1x", "2x", "3x", "4x")
DEFAULT_RESOLUTION_INDEX = 1
# integer=整数倍（保持 4:3，可能留较大黑边）/ fill=等比填充（黑边最小，允许小数倍）
SCALE_MODES = ("integer", "fill")
SCALE_MODE_LABELS = {"integer": "整数倍", "fill": "填充"}
DEFAULT_SCALE_MODE = "fill"
DEFAULT_FULLSCREEN = False
# 渲染倍率：分辨率无关的图层（伪3D 地面）按此倍率原生绘制，其余图层仍是
# 1x 画布放大。需要 GPU 呈现可用；不可用时自动退回 1x。
RENDER_SCALES = (1, 2, 3)
RENDER_SCALE_LABELS = ("1x", "2x", "3x")
DEFAULT_RENDER_SCALE_INDEX = 2

if getattr(sys, 'frozen', False):
    CONFIG_DIR = os.path.dirname(sys.executable)
else:
    CONFIG_DIR = BASE_DIR
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
# 本地仓库存档（撤离后物资持久化保存，出征前从中挑选携带）
WAREHOUSE_PATH = os.path.join(CONFIG_DIR, "warehouse.json")


def load_user_config():
    """读取用户配置（音量等），文件缺失或损坏时返回默认值"""
    config = {
        "music_volume": DEFAULT_MUSIC_VOLUME,
        "sfx_volume": DEFAULT_SFX_VOLUME,
        "game_speed": DEFAULT_GAME_SPEED,
        "boss_art": BOSS_ART_DEFAULT,
        "resolution_index": DEFAULT_RESOLUTION_INDEX,
        "scale_mode": DEFAULT_SCALE_MODE,
        "fullscreen": DEFAULT_FULLSCREEN,
        "render_scale_index": DEFAULT_RENDER_SCALE_INDEX,
    }
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data.get("music_volume"), (int, float)):
                config["music_volume"] = max(0.0, min(1.0, float(data["music_volume"])))
            if isinstance(data.get("sfx_volume"), (int, float)):
                config["sfx_volume"] = max(0.0, min(1.0, float(data["sfx_volume"])))
            if isinstance(data.get("game_speed"), (int, float)):
                config["game_speed"] = max(GAME_SPEED_MIN, min(GAME_SPEED_MAX,
                                                               float(data["game_speed"])))
            if data.get("boss_art") in BOSS_ART_SETS:
                config["boss_art"] = data["boss_art"]
            index = data.get("resolution_index")
            if isinstance(index, int) and 0 <= index < len(RESOLUTIONS):
                config["resolution_index"] = index
            if data.get("scale_mode") in SCALE_MODES:
                config["scale_mode"] = data["scale_mode"]
            if isinstance(data.get("fullscreen"), bool):
                config["fullscreen"] = data["fullscreen"]
            scale_index = data.get("render_scale_index")
            if isinstance(scale_index, int) and 0 <= scale_index < len(RENDER_SCALES):
                config["render_scale_index"] = scale_index
    except Exception as e:
        print(f"[Config] Failed to load {CONFIG_PATH}: {e}")
    return config


def save_user_config(config):
    """保存用户配置（音量等）到 config.json"""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[Config] Failed to save {CONFIG_PATH}: {e}")


def format_game_speed(speed):
    """把流速显示为简洁的 0.5x / 1x / 1.25x 等形式"""
    text = f"{float(speed):.2f}".rstrip("0").rstrip(".")
    return f"{text}x"


# --- 窗口（宽度固定）---
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 720
FPS = 60
GAME_TITLE = "东方天空街 ~ Touhou Sky Street"

# --- 战斗区域（576x670，距窗口左边 50px）---
BATTLE_OFFSET_X = 50             # 战斗区与窗口左边框的距离
BATTLE_AREA_WIDTH = 576
BATTLE_AREA_HEIGHT = 670
BATTLE_OFFSET_Y = (SCREEN_HEIGHT - BATTLE_AREA_HEIGHT) // 2   # 25，垂直居中

# 右侧信息面板区域（窗口宽度固定，面板占剩余宽度）
PANEL_LEFT = BATTLE_OFFSET_X + BATTLE_AREA_WIDTH              # 626
PANEL_WIDTH = SCREEN_WIDTH - PANEL_LEFT                       # 334

# --- 菜单背景 ---
MENU_BACKGROUND = os.path.join(BACKGROUNDS_DIR, "bg_0.png")
# --- 伪3D背景贴图 ---
STAGE1_FLOOR = os.path.join(BACKGROUNDS_DIR, "stage1", "floor.png")
STAGE1_WALL = os.path.join(BACKGROUNDS_DIR, "stage1", "wall2.png")
# --- 伪3D背景贴图（第2面：末地） ---
STAGE2_FLOOR = os.path.join(BACKGROUNDS_DIR, "stage2", "floor1.png")
STAGE2_WALL = os.path.join(BACKGROUNDS_DIR, "stage2", "wall1.png")
# --- 伪3D背景贴图（第3面：地下墓穴 / Catacombs） ---
STAGE3_FLOOR = os.path.join(BACKGROUNDS_DIR, "stage3", "floor.png")
STAGE3_WALL = os.path.join(BACKGROUNDS_DIR, "stage3", "wall.png")
# --- 伪3D背景贴图（第4面：地下墓穴深处 / The Catacombs） ---
STAGE4_FLOOR = os.path.join(BACKGROUNDS_DIR, "stage4", "floor.png")
STAGE4_WALL = os.path.join(BACKGROUNDS_DIR, "stage4", "wall.png")
# --- 伪3D背景贴图（第5面：凋零之厅 / BOSS RUSH，暂复用四面背景） ---
STAGE5_FLOOR = os.path.join(BACKGROUNDS_DIR, "stage5", "floor.png")
STAGE5_WALL = os.path.join(BACKGROUNDS_DIR, "stage5", "wall.png")

# --- 伪3D背景贴图（第6面：最终进军 / Final Approach，先复用四面墓穴，进入要塞后切换） ---
STAGE6_FLOOR = os.path.join(BACKGROUNDS_DIR, "stage6", "floor.png")
STAGE6_WALL = os.path.join(BACKGROUNDS_DIR, "stage6", "wall.png")
STAGE6_FORTRESS_FLOOR = os.path.join(BACKGROUNDS_DIR, "stage6", "fortress_floor.png")
STAGE6_FORTRESS_WALL = os.path.join(BACKGROUNDS_DIR, "stage6", "fortress_wall.png")

# --- 关卡标题 ---
TITLES_DIR = os.path.join(ASSETS_DIR, "titles")
STAGE1_TITLE = os.path.join(TITLES_DIR, "stage1.png")
STAGE2_TITLE = os.path.join(TITLES_DIR, "stage2.png")
STAGE3_TITLE = os.path.join(TITLES_DIR, "stage3.png")
STAGE4_TITLE = os.path.join(TITLES_DIR, "stage4.png")
STAGE5_TITLE = os.path.join(TITLES_DIR, "stage5.png")
STAGE6_TITLE = os.path.join(TITLES_DIR, "stage6.png")

# 关卡标题显示时长（帧，60FPS）
STAGE_TITLE_DURATION = 180

# 关卡标题投影（偏移量 / 不透明度）
STAGE_TITLE_SHADOW_OFFSET = (6, 8)
STAGE_TITLE_SHADOW_ALPHA = 150

# --- 贴图 ---
SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
ITEMS_DIR = os.path.join(ASSETS_DIR, "items")

# --- Boss 立绘套组（可在设置界面切换，见 set_boss_art） ---
# 立绘放在 assets/sprites/bosses/<套组>/ 下，套组之间仅文件名大小写不同
BOSSES_DIR = os.path.join(SPRITES_DIR, "bosses")
BOSS_ART_SETS = ("new", "another")          # 套组顺序 = 设置界面的切换顺序
BOSS_ART_LABELS = {"new": "新版", "another": "另一版"}
BOSS_ART_DEFAULT = "new"
# Boss 键 → {套组: 文件名}；legacy 仅作为缺图时的兜底，不在设置里出现
BOSS_ART_FILES = {
    "arachne": {"new": "Arachne.png", "another": "Arachne.png",
                "legacy": "arachne.png"},
    "bonzo": {"new": "Bonzo.png", "another": "bonzo.png",
              "legacy": "bonzo.png"},
    "end_stone_protector": {"new": "End_Stone_Protector.png",
                            "another": "end_stone_protector.png",
                            "legacy": "end_stone_protector.png"},
    "ender_dragon": {"new": "Ender_Dragon.png", "another": "ender_dragon.png",
                     "legacy": "ender_dragon.png"},
    "goldor": {"new": "Goldor.png", "another": "Goldor.png",
               "legacy": "goldor.png"},
    "livid": {"new": "Livid.png", "another": "Livid.png",
              "legacy": "livid.png"},
    "maxor": {"new": "Maxor.png", "another": "Maxor.png",
              "legacy": "maxor.png"},
    "necron": {"new": "Necron.png", "another": "Necron.png",
               "legacy": "necron.png"},
    "professor": {"new": "The_Professor.png", "another": "The_Professor.png",
                  "legacy": "professor.png"},
    "sadan": {"new": "Sadan.png", "another": "Sadan.png",
              "legacy": "sadan.png"},
    "scarf": {"new": "Scarf.png", "another": "Scarf.png",
              "legacy": "scarf.png"},
    "storm": {"new": "Storm.png", "another": "storm.png",
              "legacy": "storm.png"},
    "thorn": {"new": "Thorn.png", "another": "thorn.png",
              "legacy": "thorn.png"},
    "watcher": {"new": "The_Watcher.png", "another": "watcher.png",
                "legacy": "watcher.png"},
    "wither_king": {"new": "Wither_King.png", "another": "Wither_King.png",
                    "legacy": "wither_king.png"},
}
# 常量名 → Boss 键：切换套组时统一刷新（含各面的别名常量）
BOSS_SPRITE_ATTRS = {
    "ARACHNE_BOSS_SPRITE": "arachne",
    "END_DRAGON_BOSS_SPRITE": "ender_dragon",
    "END_STONE_PROTECTOR_SPRITE": "end_stone_protector",
    "WATCHER_BOSS_SPRITE": "watcher",
    "BONZO_BOSS_SPRITE": "bonzo",
    "SCARF_BOSS_SPRITE": "scarf",
    "SADAN_BOSS_SPRITE": "sadan",
    "STAGE5_WATCHER_BOSS_SPRITE": "watcher",
    "STAGE5_PROFESSOR_BOSS_SPRITE": "professor",
    "STAGE5_THORN_BOSS_SPRITE": "thorn",
    "STAGE5_LIVID_BOSS_SPRITE": "livid",
    "STAGE5_MAXOR_BOSS_SPRITE": "maxor",
    "STAGE5_STORM_BOSS_SPRITE": "storm",
    "STAGE5_GOLDOR_BOSS_SPRITE": "goldor",
    "STAGE5_NECRON_BOSS_SPRITE": "necron",
    "STAGE6_WITHER_KING_BOSS_SPRITE": "wither_king",
    "STAGE6_KAEMAN_PORTRAIT": "wither_king",
}
# 各面用到的 Boss 立绘：关卡开始时后台预热，避免 Boss 出场瞬间卡顿
STAGE_BOSS_ART = {
    1: ("arachne",),
    2: ("ender_dragon", "end_stone_protector"),
    3: ("watcher", "bonzo"),
    4: ("scarf", "sadan"),
    5: ("watcher", "professor", "thorn", "livid", "maxor", "storm",
        "goldor", "necron"),
    6: ("wither_king",),
}

# 各面会用到的符卡背景风格：关卡载入界面据此预热（开符那一帧原本要现算 12~100ms）
STAGE_SPELL_BG = {
    # 第 1 面两个 Boss 的符卡都没写死 bg_style（按符卡名推断）：
    #   道中 罠符「Luxurious Spool」-> spool
    #   关底 丝符「Soul String」/ 蛛符「Tarantula's Tornado」/ 魂符「Dark Queen's Soul」
    #        -> thread / tornado / soul
    # 漏了这张表的话，第 1 面（含 D+1 这类直接进道中 Boss 的隐藏快捷键：载入时
    # 关底 Boss 还没生成）就等于一条都不预热，开符那帧要现算 12.4+5.4+5.6+5.6ms。
    1: ("spool", "thread", "tornado", "soul"),
    2: ("fire", "lightning", "stone", "dragon", "superiority"),
    3: ("watcher", "bonzo", "undead"),
    4: ("scarf", "sadan", "stone"),
    5: ("watcher", "professor", "thorn", "livid", "maxor", "storm", "stone",
        "goldor", "necron", "soul"),
    6: ("kaeman_dominion", "kaeman_relics", "kaeman_withered_dragon",
        "kaeman_slash", "kaeman_atomize", "kaeman_slumber"),
}


def stage_spell_bg_styles(stage_num):
    """本关要预热的符卡背景风格（第 1 面没有显式 bg_style，按符卡名推断）"""
    try:
        return tuple(STAGE_SPELL_BG.get(int(stage_num), ()))
    except (TypeError, ValueError):
        return ()


_boss_art_set = BOSS_ART_DEFAULT


def boss_art_path(key, art=None):
    """Boss 立绘贴图路径；art 为 None 时使用当前套组。
    当前套组缺少该文件时回退到 legacy 目录，避免换套组后「缺图」。"""
    if art not in BOSS_ART_SETS:
        art = _boss_art_set
    files = BOSS_ART_FILES.get(key) or {}
    path = os.path.join(BOSSES_DIR, art, files.get(art) or files.get(BOSS_ART_DEFAULT, ""))
    if not os.path.exists(path):
        legacy_name = files.get("legacy")
        legacy_path = os.path.join(BOSSES_DIR, "legacy", legacy_name or "")
        if legacy_name and os.path.exists(legacy_path):
            return legacy_path
    return path


def get_boss_art():
    """当前 Boss 立绘套组名"""
    return _boss_art_set


def set_boss_art(name):
    """切换 Boss 立绘套组（new / another），返回实际生效的套组名"""
    global _boss_art_set
    _boss_art_set = name if name in BOSS_ART_SETS else BOSS_ART_DEFAULT
    for attr, key in BOSS_SPRITE_ATTRS.items():
        globals()[attr] = boss_art_path(key)
    return _boss_art_set


def stage_boss_art_paths(stage_num):
    """某一面需要预热的 Boss 立绘路径"""
    return [boss_art_path(key) for key in STAGE_BOSS_ART.get(stage_num, ())]


PLAYER_BULLET_SPRITE = os.path.join(SPRITES_DIR, "bullets", "Frozen_Scythe_Projectile.png")
PLAYER_BULLET_SPRITE_SIZE = 30   # 玩家子弹贴图显示尺寸（px）
# 敌弹贴图图集：一整张 etama.png（256x256），按格子裁剪使用
ENEMY_BULLET_ATLAS = os.path.join(SPRITES_DIR, "bullets", "etama.png")
# 弹种 → 基础图集槽位（完整槽位见 src/entities/bullet_atlas.SLOT_RECTS）
# etama.png 默认行名：
#   第1行 激光、第2行 麟弹、第3行 环玉、第4行 小玉、
#   第5行 米弹、第6行 苦无弹、第7行 针弹、第8行 大玉，再往下 飞刀。
# 实际绘制时会按子弹颜色从同排原图变体中选最接近的槽位，不再染色。
ENEMY_BULLET_SPRITE_MAP = {
    "circle": "g03_00",  # 小玉：第 4 行（16x16）
    "rice": "g04_00",    # 米弹：第 5 行（16x16）
    "arrow": "g06_00",   # 针弹：第 7 行（16x16）
    "knife": "g05_00",   # 苦无弹：第 6 行（16x16）
    "big": "big0",       # 大玉：第 8 行（32x32，big0~big7 同形异色）
}
# 弹幕按 etama.png 原始像素尺寸渲染（小弹 16x16、大弹 32x32），不再随 radius 缩放
# 超过该视觉半径的敌弹（如预警光环 radius 6/7.5 这类大半径敌弹）继续用图元绘制
ENEMY_BULLET_SPRITE_MAX_RADIUS = 9.0
# 判定半径 = 贴图视觉半径（min(宽,高)/2）× 该系数；0.5=判定直径约为贴图一半，1.0=判定与贴图等大
ENEMY_BULLET_HITBOX_FACTOR = 0.5
# 敌弹已改为“原图颜色匹配”，不再染色；此开关保留给开发预览工具使用。
ENEMY_BULLET_SPRITE_TINT = False
ARACHNE_BOSS_SPRITE = boss_art_path("arachne")
SELF_SPRITE = os.path.join(SPRITES_DIR, "self", "self1.png")
PLAYER_SPRITE_IDLE = os.path.join(SPRITES_DIR, "self", "stg1.png")
PLAYER_SPRITE_MOVE = os.path.join(SPRITES_DIR, "self", "stg2.png")
PLAYER_SPRITE_HEIGHT = 70
PLAYER_SPRITE_HITBOX_Y_RATIO = 0.38
PLAYER_HITBOX_DRAW_RADIUS_FACTOR = 3
PLAYER_SPRITE_GLOW_RADIUS = 6
PLAYER_SPRITE_GLOW_ALPHA = 28

# --- 贴图（第2面：末地 / Dragon's Nest） ---
END_DRAGON_BOSS_SPRITE = boss_art_path("ender_dragon")
END_DRAGON_PET_SPRITE = os.path.join(BACKGROUNDS_DIR, "stage2", "Ender_Dragon_Pet.png")   # 龙符幻影龙贴图
END_STONE_PROTECTOR_SPRITE = boss_art_path("end_stone_protector")
ENEMY_SPRITES_DIR_STAGE2 = os.path.join(SPRITES_DIR, "enemies", "stage2")
STAGE2_FAIRY_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE2, "fairy.png")]
STAGE2_SPIRIT_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE2, "spirit.png")]
STAGE2_GUARD_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE2, "guardian.png")]
# 二面小怪渲染高度（灵体/守卫为竖长型贴图；整体比一面略小）
STAGE2_FAIRY_SPRITE_HEIGHT = 34
STAGE2_SPIRIT_SPRITE_HEIGHT = 96
STAGE2_GUARD_SPRITE_HEIGHT = 110

# --- 贴图（第3面：地下墓穴 / Catacombs Floor 1） ---
WATCHER_BOSS_SPRITE = boss_art_path("watcher")
BONZO_BOSS_SPRITE = boss_art_path("bonzo")
ENEMY_SPRITES_DIR_STAGE3 = os.path.join(SPRITES_DIR, "enemies", "stage3")
STAGE3_FAIRY_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE3, "undead.png")]
STAGE3_SPIRIT_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE3, "soul.png")]
STAGE3_GUARD_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE3, "skeleton.png")]
STAGE3_CASTER_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE3, "caster.png")]
# 三面小怪渲染高度（灵魂/骷髅为竖长型贴图）
STAGE3_FAIRY_SPRITE_HEIGHT = 36
STAGE3_SPIRIT_SPRITE_HEIGHT = 80
STAGE3_GUARD_SPRITE_HEIGHT = 96
STAGE3_CASTER_SPRITE_HEIGHT = 88
# 展符「Undead Exhibition」亡灵展品贴图（Watcher 召唤物图标，黑色背景发光渲染）
STAGE3_WATCHER_SUMMONINGS_DIR = os.path.join(BACKGROUNDS_DIR, "stage3", "Watcher_summonings")
STAGE3_WATCHER_SUMMONINGS = [
    os.path.join(STAGE3_WATCHER_SUMMONINGS_DIR, name) for name in (
        "Cannibal.png", "Flamer.png", "Frost.png", "Mute.png", "Ooze.png",
        "Psycho.png", "Putrid.png", "Revoker.png", "Skull.png", "Tear.png",
        "Vader.png", "Walker.png",
    )
]
# 戏符「Grand Illusion」的小丑面具节点（Bonzo 头部面具贴图）
STAGE3_BONZO_MASK_SPRITE = os.path.join(BACKGROUNDS_DIR, "stage3", "Bonzo_Head.png")
# --- 贴图（第4面：地下墓穴深处 / The Catacombs） ---
SCARF_BOSS_SPRITE = boss_art_path("scarf")
SADAN_BOSS_SPRITE = boss_art_path("sadan")
ENEMY_SPRITES_DIR_STAGE4 = os.path.join(SPRITES_DIR, "enemies", "stage4")
STAGE4_FAIRY_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE4, "undead.png")]
STAGE4_SPIRIT_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE4, "soul.png")]
STAGE4_GUARD_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE4, "skeleton.png")]
STAGE4_CASTER_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE4, "caster.png")]
STAGE4_SKELETOR_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE4, "skeletor.png")]
STAGE4_TERRACOTTA_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE4, "terracotta.png")
# Giant sprites for "Precursors' Return" spell card.
STAGE4_BIGFOOT_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE4, "Bigfoot.png")
STAGE4_DIAMOND_GIANT_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE4, "The_Diamond_Giant.png")
STAGE4_LASR_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE4, "L.A.S.R.png")
STAGE4_JOLLY_PINK_GIANT_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE4, "Jolly_Pink_Giant.png")
STAGE4_DIAMOND_SWORD_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE4, "Diamond_Sword.png")
STAGE4_THE_GIANT_ONE_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE4, "TheGiantOne.png")
# 四面小怪渲染高度（贴图比例与三面一致）
STAGE4_FAIRY_SPRITE_HEIGHT = 36
STAGE4_SPIRIT_SPRITE_HEIGHT = 80
STAGE4_GUARD_SPRITE_HEIGHT = 96
STAGE4_CASTER_SPRITE_HEIGHT = 88
STAGE4_SKELETOR_SPRITE_HEIGHT = 96

# --- 五面 Boss 贴图（BOSS RUSH：The Watcher / Wither Lords 与前置 Boss） ---
STAGE5_WATCHER_BOSS_SPRITE = boss_art_path("watcher")
STAGE5_PROFESSOR_BOSS_SPRITE = boss_art_path("professor")
STAGE5_THORN_BOSS_SPRITE = boss_art_path("thorn")
STAGE5_LIVID_BOSS_SPRITE = boss_art_path("livid")
STAGE5_MAXOR_BOSS_SPRITE = boss_art_path("maxor")
STAGE5_STORM_BOSS_SPRITE = boss_art_path("storm")
STAGE5_GOLDOR_BOSS_SPRITE = boss_art_path("goldor")
STAGE5_NECRON_BOSS_SPRITE = boss_art_path("necron")

# --- 六面素材（Final Approach：亡灵军队 / Kaeman 干涉 / 凋零要塞 / Wither King） ---
ENEMY_SPRITES_DIR_STAGE6 = os.path.join(SPRITES_DIR, "enemies", "stage6")
STAGE6_HUSK_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE6, "undead.png")]      # Wither Husk
STAGE6_GUARD_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE6, "skeleton.png")]   # Wither Guard
STAGE6_MINER_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE6, "caster.png")]     # Wither Miner
STAGE6_KNIGHT_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE6, "skeletor.png")]  # Wither Knight
STAGE6_WISP_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE6, "soul.png")]        # 黑能量游魂
STAGE6_TERRACOTTA_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE6, "terracotta.png")
STAGE6_COLOSSUS_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE6, "The_Diamond_Giant.png")
STAGE6_GIANT_ONE_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE6, "TheGiantOne.png")
STAGE6_WITHER_SKULL_SPRITE = os.path.join(BACKGROUNDS_DIR, "stage6", "Wither_Skull.png")
STAGE6_WATCHFUL_EYE_SPRITE = os.path.join(BACKGROUNDS_DIR, "stage6", "watchful_eyes.png")
STAGE6_DARK_ORB_SPRITE = os.path.join(BACKGROUNDS_DIR, "stage6", "Dark_Orb.png")
# 王之门徒残影（复用五面 Wither Lords 立绘）
STAGE6_MAXOR_GHOST_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE6, "maxor_ghost.png")
STAGE6_STORM_GHOST_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE6, "storm_ghost.png")
STAGE6_GOLDOR_GHOST_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE6, "goldor_ghost.png")
STAGE6_NECRON_GHOST_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE6, "necron_ghost.png")
# Wither King（六面最终 Boss，立绘为程序生成占位）
STAGE6_WITHER_KING_BOSS_SPRITE = boss_art_path("wither_king")
STAGE6_KAEMAN_PORTRAIT = boss_art_path("wither_king")
# 对话中 BOSS 头衔表：英文名 -> 中文头衔（对话框右上角显示）
BOSS_TITLES = {
    "Arachne": "巢穴中的妖怪蜘蛛",
    "Ender Dragon": "栖息于末地的龙",
    "Bonzo": "地下城小丑",
    "Sadan": "守卫墓穴的巨人王",
    "The Watcher": "注视深渊之人",
    "Maxor": "爆炸凋零",
    "Necron": "王座之前的死灵",
    "Kaeman": "追逐死亡尽头的大魔法使",
}
# 冥符「Five Corrupted Relics」五种 Relic 贴图（红/橙/绿/蓝/紫，按五边形顶点顺序）
STAGE6_RELIC_SPRITES = (
    os.path.join(ENEMY_SPRITES_DIR_STAGE6, "wither_king_relic", "red.png"),
    os.path.join(ENEMY_SPRITES_DIR_STAGE6, "wither_king_relic", "orange.png"),
    os.path.join(ENEMY_SPRITES_DIR_STAGE6, "wither_king_relic", "green.png"),
    os.path.join(ENEMY_SPRITES_DIR_STAGE6, "wither_king_relic", "blue.png"),
    os.path.join(ENEMY_SPRITES_DIR_STAGE6, "wither_king_relic", "purple.png"),
)
STAGE6_HUSK_SPRITE_HEIGHT = 40
STAGE6_GUARD_SPRITE_HEIGHT = 92
STAGE6_MINER_SPRITE_HEIGHT = 84
STAGE6_KNIGHT_SPRITE_HEIGHT = 96
STAGE6_WISP_SPRITE_HEIGHT = 80

# --- 小怪贴图（第1面） ---
ENEMY_SPRITES_DIR = os.path.join(SPRITES_DIR, "enemies", "stage1")
FAIRY_SPRITE_HEIGHT = 42
SPIRIT_SPRITE_HEIGHT = 47
GUARD_SPRITE_HEIGHT = 57
FAIRY_SPRITES = [os.path.join(ENEMY_SPRITES_DIR, "fairy.png")]
SPIRIT_SPRITES = [os.path.join(ENEMY_SPRITES_DIR, "spirit.png")]
GUARD_SPRITES = [os.path.join(ENEMY_SPRITES_DIR, "guardian.png")]

# --- 颜色 ---
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_RED = (255, 48, 48)
COLOR_BLUE = (48, 192, 255)
COLOR_GREEN = (48, 255, 128)
COLOR_YELLOW = (255, 255, 48)
COLOR_PURPLE = (192, 64, 255)
COLOR_ORANGE = (255, 160, 48)
COLOR_GRAY = (128, 128, 128)
COLOR_DARK_GRAY = (48, 48, 48)
COLOR_PANEL_BG = (10, 14, 26)

# Skyblock 稀有度颜色
RARITY_COLORS = {
    "COMMON": (170, 170, 170),       # 灰
    "UNCOMMON": (85, 255, 85),       # 绿
    "RARE": (85, 85, 255),           # 蓝
    "EPIC": (170, 0, 170),           # 紫
    "LEGENDARY": (255, 170, 0),      # 金
    "MYTHIC": (255, 85, 255),        # 粉
    "DIVINE": (85, 255, 255),        # 青
    "SPECIAL": (255, 85, 85),        # 红
    "VERY_SPECIAL": (255, 85, 85),   # 红
}

# --- 游戏区域（相对战斗区域坐标）---
PLAY_AREA_LEFT = 32
PLAY_AREA_RIGHT = BATTLE_AREA_WIDTH - 32
PLAY_AREA_TOP = 16
PLAY_AREA_BOTTOM = BATTLE_AREA_HEIGHT - 16

# --- 玩家 ---
PLAYER_SPEED_NORMAL = 6.0
PLAYER_SPEED_FOCUSED = 1.6
PLAYER_HITBOX_RADIUS = 2.0
PLAYER_GRAZE_RADIUS = 24    # 擦弹判定半径（px）
PLAYER_START_LIVES = 3
PLAYER_START_BOMBS = 3
PLAYER_MAX_LIVES = 12
PLAYER_MAX_BOMBS = 12
PLAYER_SHOOT_COOLDOWN = 4       # 帧

# --- 子弹 ---
BULLET_PLAYER_SPEED = 12.0
BULLET_PLAYER_DAMAGE = 10
ENEMY_BULLET_RADIUS_SCALE = 1.5   # 敌弹视觉放大倍数（判定不变，仅放大观察）

# --- 敌人 ---
ENEMY_DEFAULT_HP = 100
ENEMY_DEFAULT_SCORE = 1000

# --- 关卡 ---
STAGE_DEFAULT_TIME = 120  # 秒

# --- 音乐 ---
STAGE1_MUSIC = os.path.join(MUSIC_DIR, "1_1.wav")
STAGE1_BOSS_MUSIC_START = os.path.join(MUSIC_DIR, "1_2_start.wav")   # Boss战开场曲（播放一遍）
STAGE1_BOSS_MUSIC_LOOP = os.path.join(MUSIC_DIR, "1_2_loop.wav")     # Boss战循环曲（无限循环）

# 曲名（每面开始 / Boss战开始时显示当前播放的音乐名）
STAGE1_MUSIC_NAME = "巢穴深处 ~ Deep into the Den"
STAGE1_BOSS_MUSIC_NAME = "蛛丝马迹！~ Spider's Fragments"

# 音乐（第2面）——文件未就绪时 play_music 会自动跳过
STAGE2_MUSIC = os.path.join(MUSIC_DIR, "2_1.wav")
STAGE2_BOSS_MUSIC_START = os.path.join(MUSIC_DIR, "2_2_start.wav")
STAGE2_BOSS_MUSIC_LOOP = os.path.join(MUSIC_DIR, "2_2_loop.wav")

# 曲名（每面开始 / Boss战开始时显示当前播放的音乐名）
STAGE2_MUSIC_NAME = "末影之底 ~ Depths of the End"
STAGE2_BOSS_MUSIC_NAME = "龙之怒号 ~ Dragon's Wrath"

# 音乐（第3面）——文件未就绪时 play_music 会自动跳过
STAGE3_MUSIC_START = os.path.join(MUSIC_DIR, "3_1_start.wav")   # 道中开场曲（播放一遍）
STAGE3_MUSIC_LOOP = os.path.join(MUSIC_DIR, "3_1_loop.wav")     # 道中循环曲（无限循环）
STAGE3_MUSIC = os.path.join(MUSIC_DIR, "3_1.wav")
STAGE3_BOSS_MUSIC_START = os.path.join(MUSIC_DIR, "3_2_start.wav")
STAGE3_BOSS_MUSIC_LOOP = os.path.join(MUSIC_DIR, "3_2_loop.wav")

# 曲名（每面开始 / Boss战开始时显示当前播放的音乐名）
STAGE3_MUSIC_NAME = "墓穴回响 ~ Echoes of the Catacombs"
STAGE3_BOSS_MUSIC_NAME = "小丑嘉年华 ~ Bonzo's Carnival"


# 音乐（第4面）——文件未就绪时 play_music 会自动跳过
STAGE4_MUSIC_START = os.path.join(MUSIC_DIR, "4_1_start.wav")   # 道中开场曲（播放一遍）
STAGE4_MUSIC_LOOP = os.path.join(MUSIC_DIR, "4_1_loop.wav")     # 道中循环曲（无限循环）
STAGE4_MUSIC = STAGE4_MUSIC_START
STAGE4_BOSS_MUSIC_START = os.path.join(MUSIC_DIR, "4_2.wav")   # Boss战音乐（单曲，直接循环）
STAGE4_BOSS_MUSIC_LOOP = os.path.join(MUSIC_DIR, "4_2.wav")    # 开场播完后循环同一曲

# 曲名（每面开始 / Boss战开始时显示当前播放的音乐名）
STAGE4_MUSIC_NAME = "墓穴深处 ~ The Catacombs"
STAGE4_BOSS_MUSIC_NAME = "死灵王的狂宴 ~ Necromancer's Feast"

# 音乐（第5面）——文件未就绪时 play_music 会自动跳过
STAGE5_MUSIC_START = os.path.join(MUSIC_DIR, "5_1_start.wav")   # 道中开场曲（播放一遍）
STAGE5_MUSIC_LOOP = os.path.join(MUSIC_DIR, "5_1_loop.wav")     # 道中循环曲（无限循环）
STAGE5_MUSIC = STAGE5_MUSIC_START
STAGE5_BOSS_MUSIC_START = os.path.join(MUSIC_DIR, "5_2_start.wav")   # Boss战音乐（单曲，直接循环）
STAGE5_BOSS_MUSIC_LOOP = os.path.join(MUSIC_DIR, "5_2_start.wav")    # 开场播完后循环同一曲

# 曲名（每面开始 / Boss战开始时显示当前播放的音乐名）
STAGE5_MUSIC_NAME = "凋零之厅 ~ Hall of the Wither Lords"
STAGE5_BOSS_MUSIC_NAME = "凋零之厅 ~ Hall of the Wither Lords"

# --- 六面音乐（Final Approach，暂复用五面/四面 Boss 战曲目） ---
STAGE6_MUSIC_START = STAGE5_MUSIC_START
STAGE6_MUSIC_LOOP = STAGE5_MUSIC_LOOP
STAGE6_MUSIC = STAGE5_MUSIC
STAGE6_BOSS_MUSIC_START = STAGE5_BOSS_MUSIC_START
STAGE6_BOSS_MUSIC_LOOP = STAGE5_BOSS_MUSIC_LOOP
STAGE6_MUSIC_NAME = "最终进军 ~ Final Approach"
STAGE6_BOSS_MUSIC_NAME = "凋零之王的王座 ~ Throne of the Wither King"

# 曲名横幅显示时长（帧，60FPS）
MUSIC_BANNER_DURATION = 300

# --- 音效（游玩/菜单短音效，8-bit 复古风） ---
# 文件名构成约定：assets/sounds/se/<name>.wav
SFX_SHOT = os.path.join(SFX_DIR, "se_shot.mp3")
SFX_ENEP00 = os.path.join(SFX_DIR, "se_enep00.mp3")
SFX_ENEP01 = os.path.join(SFX_DIR, "se_enep01.mp3")
SFX_DAMAGE = os.path.join(SFX_DIR, "se_damage.wav")
SFX_GRAZE = os.path.join(SFX_DIR, "se_graze.wav")
SFX_BOMB = os.path.join(SFX_DIR, "se_bomb.wav")
SFX_CARDGET = os.path.join(SFX_DIR, "se_cardget.wav")
SFX_BONUS = os.path.join(SFX_DIR, "se_bonus.wav")
SFX_POWERUP = os.path.join(SFX_DIR, "se_powerup.wav")
SFX_CURSOR = os.path.join(SFX_DIR, "se_cursor.wav")
SFX_OK = os.path.join(SFX_DIR, "se_ok.wav")
SFX_CANCEL_MENU = os.path.join(SFX_DIR, "se_cancel_menu.wav")

# 音效注册表：逻辑名 -> 文件路径（供 Game.play_sfx 使用）
SFX_PATHS = {
    "shot": SFX_SHOT,
    "enemy_down_small": SFX_ENEP00,
    "enemy_down_boss": SFX_ENEP01,
    "damage": SFX_DAMAGE,
    "graze": SFX_GRAZE,
    "bomb": SFX_BOMB,
    "cardget": SFX_CARDGET,
    "bonus": SFX_BONUS,
    "powerup": SFX_POWERUP,
    "cursor": SFX_CURSOR,
    "ok": SFX_OK,
    "cancel_menu": SFX_CANCEL_MENU,
}


# --- Skyblock 技能 ---
SKILL_XP_TABLE = [0, 50, 125, 200, 300, 500, 750, 1000, 1500, 2000,
                  3500, 5000, 7500, 10000, 15000, 20000, 30000, 50000, 75000, 100000,
                  200000, 300000, 400000, 500000, 600000, 700000, 800000, 900000, 1000000, 1100000,
                  1200000, 1300000, 1400000, 1500000, 1600000, 1700000, 1800000, 1900000, 2000000, 2100000,
                  2200000, 2300000, 2400000, 2500000, 2600000, 2750000, 2900000, 3100000, 3400000, 3700000,
                  4000000]

# --- 物品稀有度权重 ---
DROP_RATES = {
    "COMMON": 0.30,
    "UNCOMMON": 0.25,
    "RARE": 0.20,
    "EPIC": 0.12,
    "LEGENDARY": 0.07,
    "MYTHIC": 0.03,
    "DIVINE": 0.02,
    "SPECIAL": 0.01,
}
