# 东方天空街 ~ Touhou Sky Street
# 基于 Hypixel Skyblock 的东方Project同人STG
# 游戏全局设置

import os
import sys

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

# --- 关卡标题 ---
TITLES_DIR = os.path.join(ASSETS_DIR, "titles")
STAGE1_TITLE = os.path.join(TITLES_DIR, "stage1.png")
STAGE2_TITLE = os.path.join(TITLES_DIR, "stage2.png")
STAGE3_TITLE = os.path.join(TITLES_DIR, "stage3.png")

# 关卡标题显示时长（帧，60FPS）
STAGE_TITLE_DURATION = 180

# 关卡标题投影（偏移量 / 不透明度）
STAGE_TITLE_SHADOW_OFFSET = (6, 8)
STAGE_TITLE_SHADOW_ALPHA = 150

# --- 贴图 ---
SPRITES_DIR = os.path.join(ASSETS_DIR, "sprites")
PLAYER_BULLET_SPRITE = os.path.join(SPRITES_DIR, "bullets", "Frozen_Scythe_Projectile.png")
PLAYER_BULLET_SPRITE_SIZE = 30   # 玩家子弹贴图显示尺寸（px）
# 敌弹贴图图集：一整张 etama.png（256x256），按格子裁剪使用
ENEMY_BULLET_ATLAS = os.path.join(SPRITES_DIR, "bullets", "etama.png")
# 弹种 → 图集槽位（裁剪区域见 src/entities/bullet_atlas.SLOT_RECTS）
# 第 1 带方块（s0/s1/...）保留给线条渲染；圆形子弹用第 4 带 c0~c7；米弹/箭弹/刀弹用珍珠；大弹用 big0~big7（32x32 大圆）
ENEMY_BULLET_SPRITE_MAP = {
    "circle": "c0",   # 普通圆形子弹：第 4 带圆形（c0~c7 同形异色，可换）
    "rice": "s2",     # 米弹：珍珠
    "arrow": "s3",    # 箭弹：珍珠（第 1 带方块 s0/s1/... 保留给线条渲染，不用作子弹）
    "knife": "s6",    # 刀弹：珍珠
    "big": "big0",    # 大玉：32x32 大圆（big0~big7 同形异色）
}
# 弹幕按 etama.png 原始像素尺寸渲染（小弹 16x16、大弹 64x32），不再随 radius 缩放
# 超过该视觉半径的敌弹（如预警光环 radius 6/7.5 这类大半径敌弹）继续用图元绘制
ENEMY_BULLET_SPRITE_MAX_RADIUS = 9.0
# 判定半径 = 贴图视觉半径（min(宽,高)/2）× 该系数；0.5=判定直径约为贴图一半，1.0=判定与贴图等大
ENEMY_BULLET_HITBOX_FACTOR = 0.5
# 是否按子弹颜色染色（保留弹幕的颜色区分度）
ENEMY_BULLET_SPRITE_TINT = True
ARACHNE_BOSS_SPRITE = os.path.join(SPRITES_DIR, "bosses", "arachne.png")
SELF_SPRITE = os.path.join(SPRITES_DIR, "self", "self1.png")

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
