# 东方天空街 ~ Touhou Sky Street
# 基于 Hypixel Skyblock 的东方Project同人STG
# 游戏全局设置

import os
import math
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
GUI_DIR = os.path.join(ASSETS_DIR, "gui")
# 窗口 / 任务栏 / EXE 图标：打包脚本（build_exe.bat、TouHouSkyStreet.spec）用的是同一个
# 文件，换图标只需替换 assets/gui/icon.png
GAME_ICON_PATH = os.path.join(GUI_DIR, "icon.png")
# 原图 1254x1254，交给系统前缩到这个边长（任务栏取不到这么大，缩小也省内存）
GAME_ICON_SIZE = 256
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
        "player_character": PLAYER_CHARACTER_DEFAULT,
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
            if data.get("player_character") in PLAYER_CHARACTER_KEYS:
                config["player_character"] = data["player_character"]
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

# --- 界面切换过渡（黑场淡出 / 淡入）与进场动效 ---
# 过渡：先把画面压到全黑，在最黑的那一帧才真正换界面，再淡回来。按真实时间走，
# 不受 game_speed 影响（实现在 src/engine/game.py 的 ScreenTransition）。
SCREEN_FADE_OUT = 0.10
SCREEN_FADE_IN = 0.16
SCREEN_FADE_COLOR = (0, 0, 0)
# 进场动效：新界面的标题 / 面板 / 选项按次序错位淡入，并轻微上移（src/ui/anim.py）
UI_INTRO_DURATION = 0.22
UI_INTRO_STAGGER = 0.055
UI_INTRO_DELAY = 0.05
UI_INTRO_RISE = 12

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

# --- 伪3D背景贴图（第6面：最终进军 / Final Approach，复用四面墓穴，道中全程一套） ---
STAGE6_FLOOR = os.path.join(BACKGROUNDS_DIR, "stage6", "floor.png")
STAGE6_WALL = os.path.join(BACKGROUNDS_DIR, "stage6", "wall.png")

# --- 伪3D背景贴图（Ex 面：裂隙 / The Rift，从主菜单直接进入的额外面） ---
EX_STAGE_FLOOR = os.path.join(BACKGROUNDS_DIR, "stage_ex", "floor.png")
EX_STAGE_WALL = os.path.join(BACKGROUNDS_DIR, "stage_ex", "wall.png")

# --- 关卡标题 ---
TITLES_DIR = os.path.join(ASSETS_DIR, "titles")
STAGE1_TITLE = os.path.join(TITLES_DIR, "stage1.png")
STAGE2_TITLE = os.path.join(TITLES_DIR, "stage2.png")
STAGE3_TITLE = os.path.join(TITLES_DIR, "stage3.png")
STAGE4_TITLE = os.path.join(TITLES_DIR, "stage4.png")
STAGE5_TITLE = os.path.join(TITLES_DIR, "stage5.png")
STAGE6_TITLE = os.path.join(TITLES_DIR, "stage6.png")
EX_STAGE_TITLE = os.path.join(TITLES_DIR, "stage_ex.png")

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
# 文件名大小写必须与 assets/sprites/bosses/<套组>/ 里的实际文件一致（Windows 上大小写
# 不敏感，但仓库到 Linux / macOS 上就是两个文件，写错会直接找不到图）
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
    "wizardman": {"new": "Wizardman.png", "another": "Wizardman.png",
                  "legacy": "wizardman.png"},
    "barry": {"new": "barry.png", "another": "barry.png",
              "legacy": "barry.png"},
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
    "EX_MID_BOSS_WIZARDMAN_SPRITE": "wizardman",
    "EX_FINAL_BOSS_BARRY_SPRITE": "barry",
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
    7: ("wizardman", "barry"),
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
        "kaeman_slash", "kaeman_atomize", "kaeman_slumber",
        # 道中四段残影各自的背景（maxor / storm / goldor 复用五面的整幅贴图，
        # necron 用六面自己的 NecronP.png）：残影出场时现建 SpellBackground，
        # 那几张 4.8~5.2MB 的源图解码 70~100ms，必须在这里先热好
        "maxor", "storm", "goldor", "necron_p"),
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


# 弹幕贴图目录：自机弹贴图与敌弹图集都放这里
BULLETS_DIR = os.path.join(SPRITES_DIR, "bullets")
# 默认自机弹贴图（寒霜镰刀飞刃）：没登记专属子弹的自机都用它
PLAYER_BULLET_SPRITE_DEFAULT = os.path.join(BULLETS_DIR, "Frozen_Scythe_Projectile.png")
PLAYER_BULLET_SPRITE_SIZE = 30   # 玩家子弹贴图显示尺寸（px）
# 敌弹贴图图集：一整张 etama.png（256x256），按格子裁剪使用
ENEMY_BULLET_ATLAS = os.path.join(BULLETS_DIR, "etama.png")
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
    "scale": "g01_00",   # 鳞弹：第 2 行（16x16）
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

# --- 自机（玩家）形象（切换见 set_player_character） ---
# 贴图放在 assets/sprites/self/<角色目录>/ 下，一个角色一个目录，目录内按用途放图：
#   portrait 立绘（对话 / Bomb 卡）、idle 站立、move 移动
# 角色目录里缺某张图时，会先在本角色内换别的用途顶上，再退回默认自机，不至于因为
# 少一张图整个自机都画不出来。后续增加可选自机：把图放进新目录，在下面几张表里各
# 登记一行即可，绘制代码不用动；形象还没备齐的角色只登记 FILES，先不加进
# PLAYER_CHARACTER_SELECTABLE。
PLAYER_CHARACTERS_DIR = os.path.join(SPRITES_DIR, "self")
PLAYER_CHARACTER_DEFAULT = "mage"
# 登记顺序 = 后续自机选择界面的排列顺序
PLAYER_CHARACTER_KEYS = ("mage", "archer", "tank", "frozen_blaze")
PLAYER_CHARACTER_LABELS = {
    "mage": "魔法使 Mage",
    "archer": "弓手 Archer",
    "tank": "重装 Tank",
    "frozen_blaze": "冰焰 Frozen Blaze",
}
# 角色键 → {用途: 文件名}；dir 是角色目录名（大小写与磁盘一致），
# height / hitbox_y_ratio 可选，写该角色自己的渲染高度与判定点比例；
# bullet / bullet_angle 可选，写该角色专属的自机弹贴图（assets/sprites/bullets/
# 下的文件名，或绝对路径）与它的旋转角（度，逆时针为正）—— 不写就用默认自机弹、
# 不旋转；少 idle / move 的角色由 player_character_path 退回本角色的立绘
PLAYER_CHARACTER_FILES = {
    "mage": {"dir": "Mage", "portrait": "self1.png", "idle": "stg1.png",
             "move": "stg2.png"},
    # 弓箭原图指向斜上方，转 45 度后弹道朝上（与冰焰的冰箭同一个口径）；
    # 中间那条的爆炸箭在弹幕差分表里单独换（见 PLAYER_CHARACTER_SHOTS）
    "archer": {"dir": "Archer", "portrait": "Archer.png", "idle": "stg1.png",
               "move": "stg2.png", "bullet": "Iron_Arrow.png",
               "bullet_angle": 45},
    "tank": {"dir": "Tank", "portrait": "Tank.png", "idle": "stg1.png",
             "move": "stg2.png"},
    # 冰箭原图指向斜上方，转 45 度后弹道朝上（与其余自机弹一致）
    "frozen_blaze": {"dir": "FB", "portrait": "FB.png", "idle": "stg1.png",
                     "move": "stg2.png", "bullet": "Icy_Arrow.png",
                     "bullet_angle": 45},
}
# 已定稿、可以摆上选择界面的自机（登记的素材都齐了，所以等于全部登记角色）
PLAYER_CHARACTER_SELECTABLE = PLAYER_CHARACTER_KEYS
# 自机选择界面的副标题与介绍（介绍按行给，一行一句，字号 16，一行约 22 字以内）
PLAYER_CHARACTER_TITLES = {
    "mage": "Mage · 魔法使",
    "archer": "Archer · 弓手",
    "tank": "Tank · 重装",
    "frozen_blaze": "Frozen Blaze · 冰焰",
}
PLAYER_CHARACTER_INTROS = {
    "mage": (
        "以寒霜镰刀与魔导之力贯穿弹幕的魔法使。",
        "指尖凝霜成刃，Hyperion 一出鞘，",
        "整条地下城走廊都会安静下来。",
    ),
    "archer": (
        "眼里只有一条弹道的弓手。",
        "拉满弓弦的那一瞬，敌机的位置、",
        "弹幕的缝隙、风的走向，全在计算之内。",
    ),
    "tank": (
        "把像素方块当铠甲披在身上的重装。",
        "慢，但不会被推走：",
        "她站在哪里，哪里就是安全线。",
    ),
    "frozen_blaze": (
        "把地下城走廊冻成一条冰面的自机。",
        "冰箭离弦即结霜，弹幕再密，",
        "也挡不住其中那条笔直的白线。",
    ),
}
# 角色代表色（取自立绘配色，用于选择界面的名字与高亮）
PLAYER_CHARACTER_COLORS = {
    "mage": (80, 200, 255),
    "archer": (192, 96, 255),
    "tank": (208, 208, 216),
    "frozen_blaze": (144, 184, 255),
}

# --- 自机弹幕（各机体的射击差分） ---
# 固定弹与追踪弹按机体登记在下表，射击逻辑（ui/menu.py 的 _player_shoot）只读这张
# 表，不再把「1/2/3 条扇形 + 追踪弹」写死：
#   line_base / line_step / line_max
#              固定弹条数 = 起始条数 + 每级火力 × 步长，再按上限截断：旧版就是
#              「1 + 1 × 火力等级，上限 3」（火力 0/1/2/3/4 -> 1/2/3/3/3）；
#              Mage / Archer 写「1 + 2 × 火力等级，上限 5」-> 1/3/5/5/5
#   tilt_step  相邻弹条之间的夹角步长（度）：向外第 n 条倾斜 n × 步长，
#              0 = 全部笔直向上；低速（focus）时再乘 focus_tilt_mult
#   pierce     固定弹是否穿透（命中敌人不消失，可打穿多个目标）
#   tracking   是否发射追踪弹（与旧版一致：power >= 15 起、射速为正常一半）
#   layouts    可选：指定条数下的 (横向落点, 倾角倍率) —— 不写就按 PLAYER_SHOT_X_STEP
#              等距排开、倾角倍率取 0, ±1, ±2 …
#   converge   可选：写 True 时所有弹条从同一点出发（弓手的「弓箭起始点收束」），
#              只靠倾角散开
#   center     可选：中间那条（倾角最接近 0）换专属弹，见 player_shot_center_spec
# 固定弹道数增减（Loving）加在「截断之前」，与旧版一致：满火力下那一 -1 条被上限
# 吃掉（旧版也没有生效），不会因为换了机体就变成另一套算法。
PLAYER_SHOT_X_STEP = 10.0        # 相邻弹条的横向间距（px）
PLAYER_SHOT_TILT_STEP = 2.25     # 基准夹角步长（度，单侧）
PLAYER_SHOT_TILT_VY = -11.96     # 倾斜弹的垂直速度（旧版数值，保持不变）
# 爆炸箭（弓手中间那条）命中敌人时炸掉的敌弹半径（px）：比击破小怪的清弹
# （各面 42~90）小一圈，是「一发弹的小范围」而不是一次清屏
PLAYER_SHOT_EXPLOSIVE_CLEAR_RADIUS = 34.0
# 爆炸箭的发射节奏（帧）：每这么多帧才轮到一根，其余时候中间那条也是普通箭
PLAYER_SHOT_EXPLOSIVE_INTERVAL = 240
PLAYER_CHARACTER_SHOTS = {
    # 冰焰：与旧版完全一致（1/2/3 条、±10 落点、含追踪弹），旧版数值逐条写死
    "frozen_blaze": {
        "line_base": 1,
        "line_step": 1,
        "line_max": 3,
        "tilt_step": PLAYER_SHOT_TILT_STEP,
        "focus_tilt_mult": 1.0,
        "pierce": False,
        "tracking": True,
        "layouts": {
            1: ((0.0,), (0.0,)),
            2: ((-10.0, 10.0), (-1.0, 1.0)),
            3: ((-10.0, 0.0, 10.0), (-1.0, 0.0, 1.0)),
        },
    },
    # 魔法使：1/3/5 条、扩散两倍、穿透，但没有追踪弹
    "mage": {
        "line_base": 1,
        "line_step": 2,
        "line_max": 5,
        "tilt_step": PLAYER_SHOT_TILT_STEP * 2,
        "focus_tilt_mult": 1.0,
        "pierce": True,
        "tracking": False,
    },
    # 弓手：条数与扇形同 Mage（扩散两倍）、低速扩散减半，但不穿透；所有箭从同一
    # 点射出（起始点收束，只靠倾角散开）；中间那条每 240 帧有一根是爆炸箭，
    # 其余时候中间也是普通箭
    "archer": {
        "line_base": 1,
        "line_step": 2,
        "line_max": 5,
        "tilt_step": PLAYER_SHOT_TILT_STEP * 2,
        "focus_tilt_mult": 0.5,
        "pierce": False,
        "tracking": False,
        "converge": True,
        "center": {"sprite": "Explosive_Arrow.png", "angle": 45,
                   "clear_radius": PLAYER_SHOT_EXPLOSIVE_CLEAR_RADIUS,
                   "interval": PLAYER_SHOT_EXPLOSIVE_INTERVAL},
    },
    # 重装：1/2/3 条笔直向上（不扩散）+ 与旧版一样的追踪弹
    "tank": {
        "line_base": 1,
        "line_step": 1,
        "line_max": 3,
        "tilt_step": 0.0,
        "focus_tilt_mult": 1.0,
        "pierce": False,
        "tracking": True,
    },
}
# 未登记的机体沿用这张表：即旧版自机弹
PLAYER_SHOT_LEGACY = PLAYER_CHARACTER_SHOTS["frozen_blaze"]

# 常量名 → 用途：切换自机时统一刷新
PLAYER_SPRITE_ATTRS = {
    "SELF_SPRITE": "portrait",
    "PLAYER_SPRITE_IDLE": "idle",
    "PLAYER_SPRITE_MOVE": "move",
}

# 自机贴图渲染高度（px）与「判定点位于贴图上的高度比例」
PLAYER_SPRITE_HEIGHT_DEFAULT = 70
PLAYER_SPRITE_HITBOX_Y_RATIO_DEFAULT = 0.38
PLAYER_HITBOX_DRAW_RADIUS_FACTOR = 3
PLAYER_SPRITE_GLOW_RADIUS = 6
PLAYER_SPRITE_GLOW_ALPHA = 28
# 自机弹贴图的旋转角（度，逆时针为正）：贴图原图不朝上时用它转正
PLAYER_BULLET_SPRITE_ANGLE_DEFAULT = 0

_player_character_key = PLAYER_CHARACTER_DEFAULT


def _player_character_file_path(key, field):
    """角色目录里该用途的文件路径（文件不一定存在）"""
    spec = PLAYER_CHARACTER_FILES.get(key) or {}
    name = spec.get(field)
    if not name:
        return ""
    return os.path.join(PLAYER_CHARACTERS_DIR, spec.get("dir") or key, name)


def normalize_player_character(key=None):
    """规范化角色键：None 取当前自机，未登记的键回退默认自机"""
    if key is None:
        return _player_character_key
    return key if key in PLAYER_CHARACTER_FILES else PLAYER_CHARACTER_DEFAULT


def player_character_path(field, key=None):
    """自机贴图路径：field 为 portrait / idle / move。

    该角色缺这张图时先在本角色内换别的用途顶上，再退回默认自机 —— 登记了新角色
    却少一张图时，不至于整个自机都画不出来。
    """
    key = normalize_player_character(key)
    path = _player_character_file_path(key, field)
    if os.path.exists(path):
        return path
    for other in ("move", "idle", "portrait"):
        if other == field:
            continue
        fallback = _player_character_file_path(key, other)
        if fallback and os.path.exists(fallback):
            return fallback
    if key != PLAYER_CHARACTER_DEFAULT:
        return player_character_path(field, PLAYER_CHARACTER_DEFAULT)
    return path


def player_character_dialogue_name(key=None):
    """剧情对话里自机的说话名（＝自机选择界面那块名牌上的显示名）

    剧情文本一律引用常量 PLAYER_DIALOGUE_NAME，不再写死「魔法使 Mage」：写死的话
    选弓手 / 重装 / 冰焰出征，Boss 与旁白照样管你叫 Mage，可立绘已经是本人了。
    """
    return PLAYER_CHARACTER_LABELS.get(
        normalize_player_character(key),
        PLAYER_CHARACTER_LABELS[PLAYER_CHARACTER_DEFAULT])


def player_character_options():
    """可选自机 [(角色键, 显示名), ...]，给后续的自机选择界面用"""
    return [(key, PLAYER_CHARACTER_LABELS.get(key, key))
            for key in PLAYER_CHARACTER_SELECTABLE if key in PLAYER_CHARACTER_FILES]


def player_character_bullet_path(key=None):
    """自机弹贴图：角色登记的专属子弹，没登记 / 文件缺失时用默认自机弹。

    贴图按「assets/sprites/bullets/<文件名>」找（也接受绝对路径）；与立绘不同，
    这里的兜底是默认自机弹而不是本角色别的用途的图 —— 少一张弹图不该让自机弹
    变成立绘。
    """
    key = normalize_player_character(key)
    name = (PLAYER_CHARACTER_FILES.get(key) or {}).get("bullet")
    if name:
        path = name if os.path.isabs(name) else os.path.join(BULLETS_DIR, name)
        if os.path.exists(path):
            return path
    return PLAYER_BULLET_SPRITE_DEFAULT


def player_character_shot_spec(key=None):
    """当前（或指定）自机的弹幕参数（见 PLAYER_CHARACTER_SHOTS）

    未登记的机体（新加角色还没写自己的射击参数）退回旧版自机弹。
    """
    return PLAYER_CHARACTER_SHOTS.get(normalize_player_character(key),
                                      PLAYER_SHOT_LEGACY)


def player_shot_lines(spec, count, focused=False):
    """按弹条数算出每条的 (横向落点, 倾角)（度），返回 [(dx, deg), ...]

    默认向两侧等距排开、倾角倍率取 0, ±1, ±2 …（乘 spec 的 tilt_step）；spec 里
    写了 layouts 的条数（旧版机体的 2 条弹是 ±10 落点、±1 倍倾角）按表走。
    """
    layout = (spec.get("layouts") or {}).get(count)
    if layout is not None:
        offsets, tilts = layout
    elif spec.get("converge"):
        # 收束：所有弹条从同一点出发，只有倾角把它们分开
        offsets = (0.0,) * count
        tilts = tuple(i - (count - 1) / 2.0 for i in range(count))
    else:
        mid = (count - 1) / 2.0
        offsets = tuple((i - mid) * PLAYER_SHOT_X_STEP for i in range(count))
        tilts = tuple(i - mid for i in range(count))
    step = float(spec.get("tilt_step", PLAYER_SHOT_TILT_STEP))
    if focused:
        step *= float(spec.get("focus_tilt_mult", 1.0))
    return [(float(dx), tilt * step) for dx, tilt in zip(offsets, tilts)]


def player_shot_count(spec, power_level, extra=0):
    """固定弹条数：起始条数 + 每级火力 × 步长（Loving 的增减加在截断之前）"""
    base = float(spec.get("line_base", 1))
    step = float(spec.get("line_step", 1))
    top = float(spec.get("line_max", 3))
    return int(max(1, min(top, base + step * power_level + extra)))


def player_shot_velocity(tilt_deg):
    """某条弹条的 (vx, vy)：倾角 0 = 笔直向上，否则按旧版数值倾斜

    发射与「预热哪些方向的贴图」共用这一份公式（见 player_shot_headings），
    免得两边各写一遍、改了一处另一处跟不上。
    """
    if abs(tilt_deg) < 1e-6:
        return 0.0, -BULLET_PLAYER_SPEED
    return math.tan(math.radians(tilt_deg)) * 12.0, PLAYER_SHOT_TILT_VY


def player_shot_center_spec(spec):
    """中间那条弹的专属弹（弓手的爆炸箭）：返回 {'path', 'angle', 'clear_radius'} 或 None

    spec 里写 center：{"sprite": "Explosive_Arrow.png", "angle": 45,
    "clear_radius": 34, "interval": 240} —— sprite 是 assets/sprites/bullets/ 下的
    文件名（也接受绝对路径），angle 是贴图原图不朝上时的转正角（口径同
    PLAYER_BULLET_SPRITE_ANGLE），clear_radius 是命中敌人时炸掉的敌弹半径，
    interval 是发射节奏（帧，0 = 每发都是它）。贴图缺失时返回 None：这条弹退回
    机体自己的贴图，不因为少一张图就把整个自机弹画崩。
    """
    center = (spec or {}).get("center")
    if not center or not center.get("sprite"):
        return None
    name = center["sprite"]
    path = name if os.path.isabs(name) else os.path.join(BULLETS_DIR, name)
    if not os.path.exists(path):
        return None
    return {"path": path,
            "angle": float(center.get("angle", PLAYER_BULLET_SPRITE_ANGLE_DEFAULT)),
            "clear_radius": float(center.get("clear_radius", 0.0)),
            "interval": int(center.get("interval", 0))}


def player_shot_center_index(spec, count, focused=False):
    """中间那条弹的下标（换专属弹用）：倾角最接近 0 的那条

    偶数条（Loving 把弓手变成 2 / 4 条时没有正中间）取靠左的那条。
    """
    lines = player_shot_lines(spec, count, focused)
    return min(range(len(lines)), key=lambda i: (abs(lines[i][1]), i))


def player_shot_extra_sprites(key=None):
    """该自机除默认弹贴图外还要预热的贴图 [{'path', 'angle'}, ...]（载入界面用）"""
    center = player_shot_center_spec(player_character_shot_spec(key))
    return [center] if center else []


def player_shot_headings(key=None):
    """该自机的固定弹会飞出的方向（弧度，载入界面预热旋转贴图用）

    自机弹贴图按运动方向转正（见 bullet._draw_player_sprite），所以每个方向都是
    一张单独的旋转贴图；发射前把本机体用得到的几个方向先烤好，第一发就不会现转。
    逐条弹条按 player_shot_velocity 算，与 _player_shoot 同一份公式。
    """
    spec = player_character_shot_spec(key)
    top = int(max(1.0, float(spec.get("line_max", 3))))
    headings = set()
    for count in range(1, top + 1):
        for focused in (False, True):
            for _, tilt in player_shot_lines(spec, count, focused):
                vx, vy = player_shot_velocity(tilt)
                headings.add(round(math.atan2(vy, vx), 6))
    return sorted(headings)


def player_character_color(key=None):
    """角色代表色（未登记时退回白色）"""
    return PLAYER_CHARACTER_COLORS.get(normalize_player_character(key), COLOR_WHITE)


def get_player_character():
    """当前自机角色键"""
    return _player_character_key


def set_player_character(key):
    """切换自机，返回实际生效的角色键。

    切换后刷新 SELF_SPRITE / PLAYER_SPRITE_IDLE / PLAYER_SPRITE_MOVE /
    PLAYER_DIALOGUE_NAME / PLAYER_BULLET_SPRITE（+ 角度）与角色自己的渲染高度、
    判定点比例：绘制侧（player / bullet / dialogue / player_spell / 关卡载入）与
    剧情文本（各面 stages）照旧读这些常量，不必知道「角色」这回事。
    """
    global _player_character_key
    _player_character_key = normalize_player_character(key)
    spec = PLAYER_CHARACTER_FILES.get(_player_character_key) or {}
    for attr, field in PLAYER_SPRITE_ATTRS.items():
        globals()[attr] = player_character_path(field)
    globals()["PLAYER_DIALOGUE_NAME"] = player_character_dialogue_name()
    globals()["PLAYER_BULLET_SPRITE"] = player_character_bullet_path()
    globals()["PLAYER_BULLET_SPRITE_ANGLE"] = float(
        spec.get("bullet_angle", PLAYER_BULLET_SPRITE_ANGLE_DEFAULT))
    globals()["PLAYER_SPRITE_HEIGHT"] = int(
        spec.get("height", PLAYER_SPRITE_HEIGHT_DEFAULT))
    globals()["PLAYER_SPRITE_HITBOX_Y_RATIO"] = float(
        spec.get("hitbox_y_ratio", PLAYER_SPRITE_HITBOX_Y_RATIO_DEFAULT))
    return _player_character_key


# 这些常量是绘制侧与剧情文本的入口，取默认自机的贴图 / 名字；切换自机会刷新它们
SELF_SPRITE = player_character_path("portrait")
PLAYER_SPRITE_IDLE = player_character_path("idle")
PLAYER_SPRITE_MOVE = player_character_path("move")
PLAYER_DIALOGUE_NAME = player_character_dialogue_name()
PLAYER_BULLET_SPRITE = player_character_bullet_path()
PLAYER_BULLET_SPRITE_ANGLE = PLAYER_BULLET_SPRITE_ANGLE_DEFAULT
PLAYER_SPRITE_HEIGHT = PLAYER_SPRITE_HEIGHT_DEFAULT
PLAYER_SPRITE_HITBOX_Y_RATIO = PLAYER_SPRITE_HITBOX_Y_RATIO_DEFAULT

# --- 对话立绘取景（同屏人物的相对大小） ---
# 对话框里的立绘按「内容高度」统一缩放，可立绘各自的取景差得很远（全身像 vs 半身特写），
# 于是同屏就一大一小 —— 换上一张取景更近的立绘（例如新的末影龙）时尤其明显。
# 下表登记每张立绘的「头高 ÷ 内容高」，运行时据此换算补偿倍率，让所有人物看起来一样近。
#
# 度量方式：跑 tools\_portrait_head_ruler.py 生成标尺图（内容顶部 40% 放大到 400px，
# 5% 一条线），读「头顶（含头发 / 帽子）到下颚」占内容高的百分比。换图 / 加图后照图
# 重读一遍再填回来；表里没有的立绘不补偿（倍率 1.0），漏填只会退回旧行为。
# 每个套组都要登记：两套用的是各自的图，同名 Boss 的头高可以不一样。
DIALOGUE_PORTRAIT_HEAD_RATIO = {
    "another": {
        "arachne": 0.20,
        "bonzo": 0.16,
        "end_stone_protector": 0.16,
        "ender_dragon": 0.24,
        "goldor": 0.21,
        "livid": 0.18,
        "maxor": 0.14,
        "necron": 0.13,
        "professor": 0.19,
        "sadan": 0.21,
        "scarf": 0.16,
        "storm": 0.15,
        "thorn": 0.16,
        "watcher": 0.22,
        "wither_king": 0.26,
        "wizardman": 0.23,
        "barry": 0.16,
    },
    "new": {
        "arachne": 0.15,
        "bonzo": 0.14,
        "end_stone_protector": 0.13,
        "ender_dragon": 0.24,
        "goldor": 0.23,
        "livid": 0.17,
        "maxor": 0.14,
        "necron": 0.17,
        "professor": 0.22,
        "sadan": 0.20,
        "scarf": 0.18,
        "storm": 0.17,
        "thorn": 0.17,
        "watcher": 0.17,
        "wither_king": 0.18,
        "wizardman": 0.23,
        "barry": 0.16,
    },
}
# 自机立绘（不分套组）：自机是全部对话的基准，所以目标头高就取这一档附近
DIALOGUE_PORTRAIT_SELF_HEAD_RATIO = {
    "mage": 0.20,
    "archer": 0.18,
    "tank": 0.20,
    "frozen_blaze": 0.19,
}
# 目标头高（同样是「头高 ÷ 内容高」）与补偿倍率的上下限：上限 1.45 是给取景最远的
# 远景全身像（Necron / Maxor，头只占内容高 13%）留的余量，下限 0.70 防止把半身特写压得太小
DIALOGUE_PORTRAIT_HEAD_TARGET = 0.19
DIALOGUE_PORTRAIT_FACTOR_RANGE = (0.70, 1.45)
# 统一放大：取景对齐过的人物整体再做大 10%（裂隙面不参与放大，见 ui/dialogue.py 的 harmonize）
DIALOGUE_PORTRAIT_SCALE = 1.10
# 立绘放大后允许达到的最大宽度（逻辑像素；战斗区可视宽 552，同屏两张各占一边）。
# 只约束放大方向：会超出这个宽度时补偿就停手（缩小方向不受限）。接近正方形取景的
# 半身立绘（Bonzo / Watcher / Thorn）原尺寸就顶到这个预算，所以它们只会缩、不再放大 ——
# 否则五面「Watcher + 召唤的 Boss」这类同屏两张会糊在一起
DIALOGUE_PORTRAIT_MAX_WIDTH = int(round(380 * DIALOGUE_PORTRAIT_SCALE))


def dialogue_portrait_head_ratio(path):
    """立绘的「头高 ÷ 内容高」；没登记返回 None，表示不补偿"""
    if not path:
        return None
    for key in PLAYER_CHARACTER_FILES:
        if player_character_path("portrait", key) == path:
            ratio = DIALOGUE_PORTRAIT_SELF_HEAD_RATIO.get(key)
            return float(ratio) if ratio else None
    for key in BOSS_ART_FILES:
        if boss_art_path(key) == path:
            ratio = (DIALOGUE_PORTRAIT_HEAD_RATIO.get(_boss_art_set) or {}).get(key)
            return float(ratio) if ratio else None
    return None


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
# Skeleton Lord：由 skeletor.png 染成凋零紫（见 tools/_gen_skeleton_lord.py），与凋零骑士区分开
STAGE6_LORD_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE6, "skeleton_lord.png")]
STAGE6_WISP_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE6, "soul.png")]        # 黑能量游魂
STAGE6_TERRACOTTA_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE6, "terracotta.png")
STAGE6_COLOSSUS_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE6, "The_Diamond_Giant.png")
STAGE6_GIANT_ONE_SPRITE = os.path.join(ENEMY_SPRITES_DIR_STAGE6, "TheGiantOne.png")
STAGE6_WITHER_SKULL_SPRITE = os.path.join(BACKGROUNDS_DIR, "stage6", "Wither_Skull.png")
STAGE6_WATCHFUL_EYE_SPRITE = os.path.join(BACKGROUNDS_DIR, "stage6", "watchful_eyes.png")
STAGE6_DARK_ORB_SPRITE = os.path.join(BACKGROUNDS_DIR, "stage6", "Dark_Orb.png")
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
    "Wizardman": "自称多元宇宙的救世主",
    "Barry": "落选之后仍在竞选的前市长",
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
STAGE6_LORD_SPRITE_HEIGHT = 108
STAGE6_WISP_SPRITE_HEIGHT = 80

# --- Ex 面素材（The Rift：裂隙） ---
# 小怪走程序生成的裂隙生物贴图（tools/_gen_stage_ex_assets.py）
ENEMY_SPRITES_DIR_STAGE_EX = os.path.join(SPRITES_DIR, "enemies", "stage_ex")
EX_VERMIN_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE_EX, "vermin.png")]        # 裂隙虫
EX_GLOBOWL_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE_EX, "globowl.png")]      # Globowl 圆枭
EX_BLOBBERCYST_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE_EX, "blobbercyst.png")]  # Blobbercyst 泡囊
EX_VAMPIRE_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE_EX, "vampire.png")]      # 裂隙吸血鬼
EX_CRUX_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE_EX, "crux.png")]            # Crux 刻印者
EX_VERMIN_SPRITE_HEIGHT = 34
EX_GLOBOWL_SPRITE_HEIGHT = 44
EX_BLOBBERCYST_SPRITE_HEIGHT = 46
EX_VAMPIRE_SPRITE_HEIGHT = 88
EX_CRUX_SPRITE_HEIGHT = 92
# 道中Boss Wizardman / 关底Boss Barry（立绘来自 Hypixel SkyBlock Wiki 的 NPC 全身像）
EX_MID_BOSS_WIZARDMAN_SPRITE = boss_art_path("wizardman")
EX_FINAL_BOSS_BARRY_SPRITE = boss_art_path("barry")
# Ex 面不经仓库出征：固定满火力开局，装备物品效果一律不生效
EX_STAGE_START_POWER = 400
EX_STAGE_NUM = 7
EX_STAGE_NAME = "裂隙 ~ The Rift"

# 只在符卡演出里才会现读的贴图：这些图第一次用是在符卡展开后的头几帧，正是最
# 不能掉帧的地方（实测第 4 面「王符 The Giant One」的巨人解码 10.7ms、石像兵
# 6.2ms，第 3 面亡灵展品 2.9ms）。载入界面按这张表提前解码，开符帧就只剩缩放。
# 队符「Necrotic Squad」的四名亡灵成员贴图（Boss 立绘同款，由 Boss 绘制）
STAGE4_SCARF_SQUAD_SPRITES = (
    os.path.join(BACKGROUNDS_DIR, "stage4", "Undead_Warrior.png"),
    os.path.join(BACKGROUNDS_DIR, "stage4", "Undead_Archer.png"),
    os.path.join(BACKGROUNDS_DIR, "stage4", "Undead_Mage.gif"),
    os.path.join(BACKGROUNDS_DIR, "stage4", "Undead_Priest.png"),
)

STAGE_SPELL_SPRITES = {
    2: (END_DRAGON_PET_SPRITE,),
    3: tuple(STAGE3_WATCHER_SUMMONINGS) + (STAGE3_BONZO_MASK_SPRITE,),
    4: (STAGE4_TERRACOTTA_SPRITE, STAGE4_BIGFOOT_SPRITE, STAGE4_DIAMOND_GIANT_SPRITE,
        STAGE4_LASR_SPRITE, STAGE4_JOLLY_PINK_GIANT_SPRITE,
        STAGE4_DIAMOND_SWORD_SPRITE, STAGE4_THE_GIANT_ONE_SPRITE)
       + STAGE4_SCARF_SQUAD_SPRITES,
    6: (STAGE6_TERRACOTTA_SPRITE, STAGE6_COLOSSUS_SPRITE, STAGE6_GIANT_ONE_SPRITE,
        STAGE6_WITHER_SKULL_SPRITE, STAGE6_WATCHFUL_EYE_SPRITE, STAGE6_DARK_ORB_SPRITE)
       + tuple(STAGE6_RELIC_SPRITES),
}

# 道中残影立绘：六面要塞段那四位王之门徒残影直接借「Boss 立绘套组」里这四位的
# 立绘，会随设置里的 new / another 套组换图，所以这里只记 Boss 键，路径等到预热
# 时才解析（写死路径的话换套组后还是旧图）。
STAGE_GHOST_ART = {
    6: ("maxor", "storm", "goldor", "necron"),
}


def stage_ghost_art_paths(stage_num):
    """某面道中残影立绘路径（按当前 Boss 立绘套组解析）"""
    try:
        keys = STAGE_GHOST_ART.get(int(stage_num), ())
    except (TypeError, ValueError):
        return []
    return [boss_art_path(key) for key in keys]


def stage_spell_sprites(stage_num):
    """某一面「开打后才会第一次现读」的贴图路径（载入界面预热用）

    含符卡演出贴图与道中残影立绘：后者是套组立绘，路径在调用时才解析。
    """
    try:
        num = int(stage_num)
    except (TypeError, ValueError):
        return ()
    return (tuple(STAGE_SPELL_SPRITES.get(num, ()))
            + tuple(stage_ghost_art_paths(num)))


# 符卡演出会把 Boss 立绘临时换成这些贴图（第 4 面「王符 The Giant One」＝ Sadan 变身
# 巨人）：换图那一帧要按「符卡宣言横幅高度」把整幅立绘重缩一次（3x 实测 5.7ms），
# 正好落在开符后几帧，所以连战斗中的高度一起登记、载入界面一并预热。
# 表项：(贴图路径, 战斗中高度)
STAGE_BOSS_ART_SWAPS = {
    4: ((STAGE4_THE_GIANT_ONE_SPRITE, 320),),
}


def stage_boss_art_swaps(stage_num):
    """某面符卡演出会临时换上的 Boss 立绘：(路径, 战斗中高度)"""
    try:
        return tuple(STAGE_BOSS_ART_SWAPS.get(int(stage_num), ()))
    except (TypeError, ValueError):
        return ()


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

# --- 六面音乐（Final Approach） ---
STAGE6_MUSIC_START = os.path.join(MUSIC_DIR, "6_1_start.wav")   # 道中曲（播放一遍）
STAGE6_MUSIC_LOOP = STAGE6_MUSIC_START                          # 无独立循环文件，开场播完后循环同一曲
STAGE6_MUSIC = STAGE6_MUSIC_START
STAGE6_BOSS_MUSIC_START = STAGE5_BOSS_MUSIC_START               # Boss战曲目暂复用五面
STAGE6_BOSS_MUSIC_LOOP = STAGE5_BOSS_MUSIC_LOOP
STAGE6_MUSIC_NAME = "最终进军 ~ Final Approach"
STAGE6_BOSS_MUSIC_NAME = "凋零之王的王座 ~ Throne of the Wither King"

# --- Ex 面音乐（The Rift，暂复用三面 / 四面的曲目） ---
EX_STAGE_MUSIC_START = STAGE3_MUSIC_START          # 道中开场曲（播放一遍）
EX_STAGE_MUSIC_LOOP = STAGE3_MUSIC_LOOP            # 道中循环曲（无限循环）
EX_STAGE_MUSIC = EX_STAGE_MUSIC_START
EX_MID_BOSS_MUSIC = STAGE3_BOSS_MUSIC_LOOP         # 道中Boss Wizardman（循环）
EX_STAGE_BOSS_MUSIC_START = STAGE4_BOSS_MUSIC_START
EX_STAGE_BOSS_MUSIC_LOOP = STAGE4_BOSS_MUSIC_LOOP
EX_STAGE_MUSIC_NAME = "裂隙彼端 ~ Beyond the Rift"
EX_STAGE_BOSS_MUSIC_NAME = "竞选者的狂想 ~ The Candidate's Fantasy"

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
