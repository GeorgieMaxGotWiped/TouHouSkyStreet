# -*- coding: utf-8 -*-
# 一次性补丁：用 Python 精确替换 boss.py 中龙符的整段实现（1441 行起）
p = r"D:\pyz\my thingses\TouHou\src\entities\boss.py"
with open(p, "r", encoding="utf-8") as f:
    text = f.read()

start_marker = "def _dragon_spirit_ring(boss, bullet_manager, cycle):"
end_marker = "def _superior_judgement_ring(boss, bullet_manager, cycle):"
si = text.index(start_marker)
ei = text.index(end_marker)

new_block = '''def _dragon_phantom_trajectories(boss, timer, count):
    """幻影龙固定轨迹：偶数序椭圆环绕本体，奇数序正弦横穿场地"""
    w = cfg.BATTLE_AREA_WIDTH
    h = cfg.BATTLE_AREA_HEIGHT
    phantoms = []
    for i in range(count):
        if i % 2 == 0:
            speed = 0.020 + 0.004 * (i // 2)
            phase = i * math.tau / max(2, count)
            rx = 168 + (i % 3) * 28
            ry = 118 + (i % 2) * 32
            ang = timer * speed + phase
            x = boss.x + math.cos(ang) * rx
            y = boss.y + math.sin(ang * 0.85) * ry
            vx = -math.sin(ang) * speed * rx
            vy = math.cos(ang * 0.85) * speed * 0.85 * ry
            move_ang = math.atan2(vy, vx)
        else:
            dir_sign = 1 if (i % 4) == 1 else -1
            progress = (timer * 0.010 + (i // 2) * 0.31) % 1.0
            if dir_sign > 0:
                x = -34 + progress * (w + 68)
            else:
                x = w + 34 - progress * (w + 68)
            base_y = 100 + ((i // 2) % 3) * 58
            y = base_y + math.sin(timer * 0.016 + i * 1.9) * 52
            vx = dir_sign * (w + 68) * 0.010
            vy = math.cos(timer * 0.016 + i * 1.9) * 0.016 * 52
            move_ang = math.atan2(vy, vx)
        phantoms.append({"x": x, "y": y, "angle": move_ang, "flip": math.cos(move_ang) < 0})
    return phantoms


def _phantom_wing_spread(bullet_manager, x, y, timer, color):
    """龙翼状扇形：左右两翼各一簇固定箭弹，呈翼展形"""
    if timer % 50 == 0:
        tilt = math.sin(timer * 0.012) * 0.45
        for side in (-1, 1):
            base = side * (math.pi / 2) + tilt
            for k in range(4):
                ang = base + (k - 1.5) * 0.20
                b = create_bullet_angle(x, y, ang, 1.8 + k * 0.25,
                                        Bullet.TYPE_ARROW, radius=2.6, color=color)
                b.manager = bullet_manager
                b.lifetime = 430
                bullet_manager.add_enemy_bullet(b)


def _phantom_scale_arc(bullet_manager, x, y, timer, color):
    """鳞片状：多层错位短弧米弹，层层叠叠如龙鳞"""
    if timer % 34 == 0:
        for layer in range(3):
            for i in range(5):
                ang = timer * 0.045 + layer * 0.55 + i * math.tau / 5 + (layer % 2) * 0.18
                b = create_bullet_angle(x, y, ang, 1.1 + layer * 0.34,
                                        Bullet.TYPE_RICE, radius=2.2, color=color)
                b.manager = bullet_manager
                b.lifetime = 300
                bullet_manager.add_enemy_bullet(b)


def _phantom_breath(bullet_manager, x, y, player_x, player_y, timer, color):
    """交错龙息：窄幅自机狙连喷，与相邻幻影错开时相"""
    if timer % 26 == 0:
        base = math.atan2(player_y - y, player_x - x)
        for k in range(3):
            b = create_bullet_angle(x, y, base + (k - 1) * 0.12, 2.6 + k * 0.15,
                                    Bullet.TYPE_KNIFE, radius=2.4, color=color)
            b.manager = bullet_manager
            b.lifetime = 380
            bullet_manager.add_enemy_bullet(b)


def _dragon_main_ring(bullet_manager, boss, timer, color, speed=1.5, count=14):
    """本体旋转弹环：基角随计时缓慢旋转，逐环封堵"""
    if timer % 90 == 0:
        base = timer * 0.02
        for i in range(count):
            ang = base + i * math.tau / count
            b = create_bullet_angle(boss.x, boss.y, ang, speed,
                                    Bullet.TYPE_RICE, radius=2.4, color=color)
            b.manager = bullet_manager
            b.lifetime = 420
            bullet_manager.add_enemy_bullet(b)


def spell_one_with_the_dragons(boss, bullet_manager, timer, dt, player_x=0, player_y=0):
    """龙符「One with the Dragons」：万龙共鸣——幻影龙群环绕/穿越 + 多层固定弹阵

    幻影龙数量随战斗推进增加（2 → 5）：偶数序环绕本体、奇数序横穿场地，
    持续释放龙翼扇形 / 鳞片短弧 / 交错龙息；本体与幻影龙同步以旋转弹环和
    大范围扩散弹封锁玩家空间，营造被龙之力量包围的压迫感。
    """
    cycle = timer % 720
    phase = cycle // 240
    count = min(5, 2 + timer // 240)
    phantoms = _dragon_phantom_trajectories(boss, timer, count)
    boss.phantom_dragons = phantoms

    # 本体游走
    boss.target_y = 110 + math.sin(timer * 0.010) * 14
    if timer % 200 == 0:
        boss.target_x = random.uniform(120, cfg.BATTLE_AREA_WIDTH - 120)

    for i, ph in enumerate(phantoms):
        x, y = ph["x"], ph["y"]
        color = _DRAGON_PALE if i % 2 == 0 else _DRAGON_PURPLE
        if phase == 0:
            _phantom_wing_spread(bullet_manager, x, y, timer + i * 13, color)
        elif phase == 1:
            _phantom_scale_arc(bullet_manager, x, y, timer + i * 17, color)
            if (timer // 26 + i) % 2 == 0:
                _phantom_breath(bullet_manager, x, y, player_x, player_y,
                                timer + i * 9, _TEAL_DRAGON)
        else:
            _phantom_scale_arc(bullet_manager, x, y, timer + i * 17, color)
            if (timer // 26 + i) % 2 == 0:
                _phantom_breath(bullet_manager, x, y, player_x, player_y,
                                timer + i * 9, _TEAL_DRAGON)
            if (timer + i * 41) % 120 == 0:
                base = (timer * 0.03) % math.tau
                for k in range(22):
                    ang = base + k * math.tau / 22
                    b = create_bullet_angle(x, y, ang, 1.4,
                                            Bullet.TYPE_CIRCLE, radius=2.6, color=color)
                    b.manager = bullet_manager
                    b.lifetime = 360
                    bullet_manager.add_enemy_bullet(b)

    # 本体攻击：随阶段逐步加密
    if phase == 0:
        _dragon_main_ring(bullet_manager, boss, timer, _DRAGON_DEEP, speed=1.4, count=12)
    elif phase == 1:
        _dragon_main_ring(bullet_manager, boss, timer, _DRAGON_PURPLE, speed=1.6, count=16)
        if cycle % 60 == 0:
            b = create_bullet_aimed(boss.x, boss.y, player_x, player_y, 2.2,
                                    Bullet.TYPE_BIG, radius=4, color=_DRAGON_DEEP)
            b.manager = bullet_manager
            b.steer_speed = 0.010
            b.lifetime = 420
            bullet_manager.add_enemy_bullet(b)
    else:
        _dragon_main_ring(bullet_manager, boss, timer, _TEAL_DRAGON, speed=1.8, count=20)
        if cycle % 36 == 0:
            base = cycle * 0.05
            for k in range(16):
                ang = base + k * math.tau / 16
                b = create_bullet_angle(boss.x, boss.y, ang, 2.0,
                                        Bullet.TYPE_ARROW, radius=2.8,
                                        color=_DRAGON_DEEP if k % 2 == 0 else _DRAGON_PALE)
                b.manager = bullet_manager
                b.lifetime = 400
                bullet_manager.add_enemy_bullet(b)
'''

text = text[:si] + new_block + "\n\n\n" + text[ei:]
with open(p, "w", encoding="utf-8", newline="") as f:
    f.write(text)
print("patched boss.py spell block OK")