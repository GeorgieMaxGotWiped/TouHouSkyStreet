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
BACKGROUNDS_DIR = os.path.join(ASSETS_DIR, "backgrounds")
SRC_DIR = os.path.join(BASE_DIR, "src")

# --- 用户配置（音量等）：源码运行保存到项目根目录，打包后保存到 exe 同目录 ---
DEFAULT_MUSIC_VOLUME = 0.8

if getattr(sys, 'frozen', False):
    CONFIG_DIR = os.path.dirname(sys.executable)
else:
    CONFIG_DIR = BASE_DIR
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")


def load_user_config():
    """读取用户配置（音量等），文件缺失或损坏时返回默认值"""
    config = {
        "music_volume": DEFAULT_MUSIC_VOLUME,
    }
    try:
        if os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data.get("music_volume"), (int, float)):
                config["music_volume"] = max(0.0, min(1.0, float(data["music_volume"])))
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
STAGE5_FLOOR = STAGE4_FLOOR
STAGE5_WALL = STAGE4_WALL

# --- 关卡标题 ---
TITLES_DIR = os.path.join(ASSETS_DIR, "titles")
STAGE1_TITLE = os.path.join(TITLES_DIR, "stage1.png")
STAGE2_TITLE = os.path.join(TITLES_DIR, "stage2.png")
STAGE3_TITLE = os.path.join(TITLES_DIR, "stage3.png")
STAGE4_TITLE = os.path.join(TITLES_DIR, "stage4.png")
STAGE5_TITLE = os.path.join(TITLES_DIR, "stage5.png")

# 关卡标题显示时长（帧，60FPS）
STAGE_TITLE_DURATION = 180

# 关卡标题投影（偏移量 / 不透明度）
STAGE_TITLE_SHADOW_OFFSET = (6, 8)
STAGE_TITLE_SHADOW_ALPHA = 150

# --- 贴图 ---
SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
ITEMS_DIR = os.path.join(ASSETS_DIR, "items")
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
ARACHNE_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "arachne.png")
SELF_SPRITE = os.path.join(SPRITES_DIR, "self", "self1.png")
PLAYER_SPRITE_IDLE = os.path.join(SPRITES_DIR, "self", "stg1.png")
PLAYER_SPRITE_MOVE = os.path.join(SPRITES_DIR, "self", "stg2.png")
PLAYER_SPRITE_HEIGHT = 70
PLAYER_SPRITE_HITBOX_Y_RATIO = 0.38
PLAYER_HITBOX_DRAW_RADIUS_FACTOR = 3
PLAYER_SPRITE_GLOW_RADIUS = 6
PLAYER_SPRITE_GLOW_ALPHA = 28

# --- 贴图（第2面：末地 / Dragon's Nest） ---
END_DRAGON_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "ender_dragon.png")
END_DRAGON_PET_SPRITE = os.path.join(BACKGROUNDS_DIR, "stage2", "Ender_Dragon_Pet.png")   # 龙符幻影龙贴图
END_STONE_PROTECTOR_SPRITE = os.path.join(SPRITES_DIR, "bosses", "end_stone_protector.png")
ENEMY_SPRITES_DIR_STAGE2 = os.path.join(SPRITES_DIR, "enemies", "stage2")
STAGE2_FAIRY_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE2, "fairy.png")]
STAGE2_SPIRIT_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE2, "spirit.png")]
STAGE2_GUARD_SPRITES = [os.path.join(ENEMY_SPRITES_DIR_STAGE2, "guardian.png")]
# 二面小怪渲染高度（灵体/守卫为竖长型贴图；整体比一面略小）
STAGE2_FAIRY_SPRITE_HEIGHT = 34
STAGE2_SPIRIT_SPRITE_HEIGHT = 96
STAGE2_GUARD_SPRITE_HEIGHT = 110

# --- 贴图（第3面：地下墓穴 / Catacombs Floor 1） ---
WATCHER_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "watcher.png")
BONZO_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "bonzo.png")
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
SCARF_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "scarf.png")
SADAN_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "sadan.png")
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
STAGE5_WATCHER_BOSS_SPRITE = WATCHER_BOSS_SPRITE
STAGE5_PROFESSOR_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "professor.png")
STAGE5_THORN_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "thorn.png")
STAGE5_LIVID_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "livid.png")
STAGE5_MAXOR_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "maxor.png")
STAGE5_STORM_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "storm.png")
STAGE5_GOLDOR_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "goldor.png")
STAGE5_NECRON_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "necron.png")

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


# 音乐（第4面）——当前复用三面音乐文件；后续可替换为四面专属曲
STAGE4_MUSIC_START = STAGE3_MUSIC_START
STAGE4_MUSIC_LOOP = STAGE3_MUSIC_LOOP
STAGE4_MUSIC = STAGE3_MUSIC
STAGE4_BOSS_MUSIC_START = STAGE3_BOSS_MUSIC_START
STAGE4_BOSS_MUSIC_LOOP = STAGE3_BOSS_MUSIC_LOOP

# 曲名（每面开始 / Boss战开始时显示当前播放的音乐名）
STAGE4_MUSIC_NAME = "墓穴深处 ~ The Catacombs"
STAGE4_BOSS_MUSIC_NAME = "死灵王的狂宴 ~ Necromancer's Feast"

# 音乐（第5面）——当前复用四面 Boss 战音乐；后续可替换为五面专属曲
STAGE5_MUSIC_START = STAGE4_BOSS_MUSIC_START
STAGE5_MUSIC_LOOP = STAGE4_BOSS_MUSIC_LOOP
STAGE5_MUSIC = STAGE5_MUSIC_START
STAGE5_BOSS_MUSIC_START = STAGE4_BOSS_MUSIC_START
STAGE5_BOSS_MUSIC_LOOP = STAGE4_BOSS_MUSIC_LOOP

# 曲名（每面开始 / Boss战开始时显示当前播放的音乐名）
STAGE5_MUSIC_NAME = "凋零之厅 ~ Hall of the Wither Lords"
STAGE5_BOSS_MUSIC_NAME = "凋零之厅 ~ Hall of the Wither Lords"

# 曲名横幅显示时长（帧，60FPS）
MUSIC_BANNER_DURATION = 300

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
