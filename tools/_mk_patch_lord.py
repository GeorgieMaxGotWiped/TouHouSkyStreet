# -*- coding: utf-8 -*-
# 临时脚本：生成 Skeleton Lord 黄绿交替 + 频率/转角翻倍的 apply_patch 文本
import io

path = "src/stages/stage6.py"
txt = io.open(path, encoding="utf-8").read()

H1_OLD = """    别的机制，弹速与弹密是该兵种的全部压迫感来源。
    \"\"\"
    ENTRY_SPEED = 7.0        # 横向切入速度（px/帧），约 0.2s 从边框切到停驻位
    ANCHOR_INSET = 150.0     # 停驻点到同侧边框的距离
    SETTLE_FRAMES = 6        # 到位后停顿多少帧再开火（0.1s，几乎紧接着就起手）
    VOLLEY_FRAMES = 12       # 螺旋每轮间隔（帧）
    VOLLEY_BULLETS = 5       # 每轮弹数（同轮等分一圈，5 发 + 每轮偏转 = 螺旋）
    SPIN_STEP = 0.55         # 每轮螺旋的偏转角（弧度）
    BULLET_SPEED = 4.2       # 鳞弹弹速（px/帧），比道中其它小怪的 1.5~2.6 快得多
"""
H1_NEW = """    别的机制，弹速与弹密是该兵种的全部压迫感来源；弹色每轮在黄 / 绿之间交替。
    \"\"\"
    ENTRY_SPEED = 7.0        # 横向切入速度（px/帧），约 0.2s 从边框切到停驻位
    ANCHOR_INSET = 150.0     # 停驻点到同侧边框的距离
    SETTLE_FRAMES = 6        # 到位后停顿多少帧再开火（0.1s，几乎紧接着就起手）
    VOLLEY_FRAMES = 6        # 螺旋每轮间隔（帧），比初版快一倍
    VOLLEY_BULLETS = 5       # 每轮弹数（同轮等分一圈，5 发 + 每轮偏转 = 螺旋）
    SPIN_STEP = 1.10         # 每轮螺旋的偏转角（弧度），比初版大一倍
    BULLET_SPEED = 4.2       # 鳞弹弹速（px/帧），比道中其它小怪的 1.5~2.6 快得多
    COLOR_YELLOW = (225, 190, 30)   # 黄鳞弹（图集里落在 g01_13）
    COLOR_GREEN = (60, 205, 70)     # 绿鳞弹（图集里落在 g01_10）
"""

H2_OLD = """        self.spin = 0.0             # 当前螺旋偏转角
"""
H2_NEW = """        self.spin = 0.0             # 当前螺旋偏转角
        self.volley = 0             # 已发射轮数：偶数轮黄、奇数轮绿
"""

H3_OLD = """    def shoot(self, bullet_manager, player_x, player_y):
        for i in range(self.VOLLEY_BULLETS):
            angle = self.spin + i * math.tau / self.VOLLEY_BULLETS
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, angle, self.BULLET_SPEED, Bullet.TYPE_SCALE,
                radius=5, color=(178, 128, 236)))
        self.spin += self.SPIN_STEP * (1 if self.side < 0 else -1)
"""
H3_NEW = """    def shoot(self, bullet_manager, player_x, player_y):
        color = self.COLOR_YELLOW if self.volley % 2 == 0 else self.COLOR_GREEN
        for i in range(self.VOLLEY_BULLETS):
            angle = self.spin + i * math.tau / self.VOLLEY_BULLETS
            _add(bullet_manager, create_bullet_angle(
                self.x, self.y, angle, self.BULLET_SPEED, Bullet.TYPE_SCALE,
                radius=5, color=color))
        self.spin += self.SPIN_STEP * (1 if self.side < 0 else -1)
        self.volley += 1
"""

hunks = []
for old, new in ((H1_OLD, H1_NEW), (H2_OLD, H2_NEW), (H3_OLD, H3_NEW)):
    assert txt.count(old) == 1, "anchor not unique: %r" % old[:60]
    hunks.append("@@\n" + "".join("-" + ln + "\n" for ln in old.splitlines())
                 + "".join("+" + ln + "\n" for ln in new.splitlines()))

patch = "*** Begin Patch\n*** Update File: %s\n" % path + "".join(hunks) + "*** End Patch\n"
io.open("tools/_patch_lord.txt", "w", encoding="utf-8", newline="\n").write(patch)
print("patch written, %d hunks" % len(hunks))
