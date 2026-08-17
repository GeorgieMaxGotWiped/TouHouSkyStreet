# Player spell card / Bomb implementation.
# Bomb is treated as a player-side spell card: portrait + name banner, then three
# Hyperion strikes. It intentionally does not open a spell domain or a boss phase.
import math
import os
import pygame

from src.engine import settings as cfg
from src.engine.collision import point_segment_distance
from src.entities.boss import Boss


SPELL_NAME = "神剑「Wither Impact」"

# Normal Bomb timings. The whole sequence is 130 frames (~2.17s at 60 FPS).
BANNER_DURATION = 30       # Portrait + spell-name banner at the start.
STRIKE_OFFSET = 0          # First Hyperion starts immediately on bomb use.
STRIKE_COUNT = 3
STRIKE_DURATION = 40       # Each Hyperion: aim -> teleport -> explosion.
AIM_FRAMES = 12            # Frames spent locking on before teleporting.
EXPLOSION_FRAMES = 26      # Visible explosion duration.
FINAL_FRAMES = 10          # Short fade after the final explosion.
TOTAL_FRAMES = STRIKE_OFFSET + STRIKE_COUNT * STRIKE_DURATION + FINAL_FRAMES

# Death Bomb timings: 5 swords, shorter gaps, still under 4 seconds.
DEATH_STRIKE_COUNT = 5
DEATH_STRIKE_DURATION = 32
DEATH_AIM_FRAMES = 10
DEATH_EXPLOSION_FRAMES = 20
DEATH_FINAL_FRAMES = 8
DEATH_TOTAL_FRAMES = (STRIKE_OFFSET + DEATH_STRIKE_COUNT * DEATH_STRIKE_DURATION
                      + DEATH_FINAL_FRAMES)

DAMAGE_PER_STRIKE = 2400
PATH_HIT_RADIUS = 88       # How close an enemy must be to the strike path.
PORTRAIT_HEIGHT = 560
HYPERION_HEIGHT = 88

HYPERION_PATH = os.path.join(cfg.ASSETS_DIR, "sprites", "self", "Hyperion.png")
PORTRAIT_PATH = os.path.join(cfg.ASSETS_DIR, "sprites", "self", "self1.png")


_image_cache = {}


def _load_image(path, target_height, max_width=None):
    """Load and cache an image scaled to target_height (or width-capped)."""
    key = (path, target_height, max_width)
    if key in _image_cache:
        return _image_cache[key]
    _image_cache[key] = None
    try:
        img = pygame.image.load(path)
        try:
            img = img.convert_alpha()
        except Exception:
            pass
        w, h = img.get_size()
        if h <= 0:
            raise ValueError("invalid image height")
        new_h = int(target_height)
        new_w = max(1, int(round(w * new_h / h)))
        if max_width is not None and new_w > max_width:
            new_w = max_width
            new_h = max(1, int(round(h * new_w / w)))
        _image_cache[key] = pygame.transform.smoothscale(img, (new_w, new_h))
    except Exception as exc:
        print(f"[PlayerSpell] Failed to load image {path}: {exc}")
    return _image_cache[key]


def _with_alpha(surf, alpha):
    """Return a copy with the requested overall alpha (0-255)."""
    if surf is None or alpha >= 255:
        return surf
    result = surf.copy()
    result.fill((255, 255, 255, max(0, min(255, alpha))),
                special_flags=pygame.BLEND_RGBA_MULT)
    return result


class PlayerSpellCard:
    """Player-side spell card: Wither Impact.

    The card shows a portrait/name banner, grants the player invulnerability, and
    summons three Hyperion images. Each Hyperion locks on to the nearest
    attackable enemy, teleports to it, and explodes along the travel path.
    """

    name = SPELL_NAME

    def __init__(self, player, bullet_manager, stage, game, on_enemy_killed=None,
                 deathbomb=False, damage_mult=1.0):
        self.player = player
        self.bullet_manager = bullet_manager
        self.stage = stage
        self.game = game
        self.on_enemy_killed = on_enemy_killed
        self.damage_mult = float(damage_mult or 1.0)

        if deathbomb:
            self.strike_count = DEATH_STRIKE_COUNT
            self.strike_duration = DEATH_STRIKE_DURATION
            self.aim_frames = DEATH_AIM_FRAMES
            self.explosion_frames = DEATH_EXPLOSION_FRAMES
            self.final_frames = DEATH_FINAL_FRAMES
        else:
            self.strike_count = STRIKE_COUNT
            self.strike_duration = STRIKE_DURATION
            self.aim_frames = AIM_FRAMES
            self.explosion_frames = EXPLOSION_FRAMES
            self.final_frames = FINAL_FRAMES
        self.strike_offset = STRIKE_OFFSET
        self.total_frames = (self.strike_offset
                             + self.strike_count * self.strike_duration
                             + self.final_frames)

        self.timer = 0
        self.done = False
        self.strikes = []
        self.hyperion_sprite = _load_image(HYPERION_PATH, HYPERION_HEIGHT)
        self.portrait = _load_image(
            PORTRAIT_PATH, PORTRAIT_HEIGHT, max_width=cfg.BATTLE_AREA_WIDTH - 80)

    def update(self, dt):
        """Advance the card state machine. Frame-based to match the rest of the game."""
        if self.done:
            return

        self.timer += 1
        if self.timer >= self.total_frames:
            self.done = True
            return

        if self.timer <= self.strike_offset:
            return

        combat_t = self.timer - self.strike_offset
        if combat_t <= self.strike_count * self.strike_duration:
            index = (combat_t - 1) // self.strike_duration
            local = (combat_t - 1) % self.strike_duration
            if local == 0:
                self._start_strike(index)
            elif local == self.aim_frames:
                self._trigger_strike(index)

    # ------------------------------------------------------------------
    # Internal state helpers
    # ------------------------------------------------------------------
    def _front_position(self, index):
        """Return where the index-th Hyperion waits in front of the player."""
        spacing = 38
        centered_index = index - (self.strike_count - 1) / 2.0
        x = max(28.0, min(cfg.BATTLE_AREA_WIDTH - 28.0,
                          self.player.x + centered_index * spacing))
        y = max(46.0, self.player.y - 62.0)
        return (x, y)

    def _attackable_enemies(self):
        """Enemies that can currently be damaged."""
        result = []
        for enemy in self.stage.get_active_enemies():
            if not getattr(enemy, "alive", True):
                continue
            if isinstance(enemy, Boss):
                if not getattr(enemy, "combat_enabled", True):
                    continue
                if getattr(enemy, "invincible", False) or getattr(enemy, "entering", False):
                    continue
                if getattr(enemy, "phase", "") in ("entry", "reviving"):
                    continue
            result.append(enemy)
        return result

    def _choose_target(self):
        """Pick the nearest attackable enemy; fall back to nearest active enemy."""
        candidates = self._attackable_enemies()
        if not candidates:
            candidates = self.stage.get_active_enemies()
        if candidates:
            target = min(
                candidates,
                key=lambda e: (e.x - self.player.x) ** 2 + (e.y - self.player.y) ** 2)
            return (target.x, target.y)

        # No enemies: fire upward so the card still has a coherent visual.
        x = max(30.0, min(cfg.BATTLE_AREA_WIDTH - 30.0, self.player.x))
        y = max(60.0, self.player.y - 300.0)
        return (x, y)

    def _start_strike(self, index):
        """Create the strike state: choose target and record launch position/angle."""
        while len(self.strikes) <= index:
            self.strikes.append(None)

        start = self._front_position(index)
        target = self._choose_target()
        angle = math.atan2(target[1] - start[1], target[0] - start[0])
        self.strikes[index] = {
            "start": start,
            "target": target,
            "angle": angle,
            "triggered": False,
            "triggered_at": 0,
        }

    def _trigger_strike(self, index):
        """Teleport the Hyperion to its target and explode along the path."""
        if index >= len(self.strikes):
            return
        strike = self.strikes[index]
        if strike is None or strike.get("triggered"):
            return

        strike["triggered"] = True
        strike["triggered_at"] = self.timer
        self._damage_path(strike["start"], strike["target"])
        self._cancel_bullets_along(strike["start"], strike["target"])

    def _damage_path(self, start, target):
        """Damage every enemy close to the travel segment."""
        sx, sy = start
        tx, ty = target
        for enemy in self.stage.get_active_enemies():
            if not getattr(enemy, "alive", True):
                continue
            ex, ey = getattr(enemy, "x", 0.0), getattr(enemy, "y", 0.0)
            body_radius = max(10.0, getattr(enemy, "size", 12.0) * 0.85)
            if point_segment_distance(ex, ey, sx, sy, tx, ty) <= PATH_HIT_RADIUS + body_radius:
                strike_damage = int(round(DAMAGE_PER_STRIKE * self.damage_mult))
                killed = enemy.take_damage(strike_damage)
                if killed and self.on_enemy_killed is not None:
                    self.on_enemy_killed(enemy)

    def _cancel_bullets_along(self, start, target):
        """Clear enemy bullets near the explosion path (bomb-style screen clear)."""
        sx, sy = start
        tx, ty = target
        for bullet in self.bullet_manager.enemy_bullets:
            if not getattr(bullet, "alive", True) or getattr(bullet, "cancel_timer", 0) > 0:
                continue
            if getattr(bullet, "harmless", False):
                continue
            radius = getattr(bullet, "collision_radius", 2.0)
            if point_segment_distance(bullet.x, bullet.y, sx, sy, tx, ty) <= PATH_HIT_RADIUS + radius:
                bullet.start_cancel()

    def _combat_progress(self):
        """Return (active_strike_index, local_frame) or (None, None) outside strikes."""
        if self.timer <= self.strike_offset:
            return None, None
        combat_t = self.timer - self.strike_offset
        if combat_t > self.strike_count * self.strike_duration:
            return None, None
        index = min(self.strike_count - 1, (combat_t - 1) // self.strike_duration)
        local = (combat_t - 1) % self.strike_duration
        return index, local

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------
    def draw(self, screen, offset_x=0, offset_y=0):
        if self.timer <= 0 or self.timer > self.total_frames:
            return

        # Explosions are drawn underneath the Hyperions.
        for strike in self.strikes:
            if not strike or not strike.get("triggered"):
                continue
            age = self.timer - strike.get("triggered_at", 0)
            if 0 <= age <= self.explosion_frames:
                self._draw_explosion(
                    screen, strike["start"], strike["target"], age, offset_x, offset_y)

        if self.timer > self.strike_offset:
            self._draw_hyperions(screen, offset_x, offset_y)

        if self.timer <= BANNER_DURATION:
            self._draw_banner(screen, offset_x, offset_y)

    def _draw_hyperions(self, screen, offset_x=0, offset_y=0):
        active_index, local = self._combat_progress()
        combat_end = self.strike_offset + self.strike_count * self.strike_duration
        final_t = max(0, self.timer - combat_end)

        for i in range(self.strike_count):
            strike = self.strikes[i] if i < len(self.strikes) else None

            # Fired Hyperion: stay at the impact point, then fade after all strikes.
            if strike and strike.get("triggered"):
                age = self.timer - strike.get("triggered_at", 0)
                alpha = 140 if age <= self.explosion_frames else 120
                if final_t > 0:
                    alpha = max(0, 140 - final_t * 14)
                self._draw_hyperion(screen, strike["target"], strike["angle"],
                                    offset_x, offset_y, alpha=alpha)
                continue

            # Current Hyperion: aim, then teleport.
            if i == active_index and strike:
                if local < self.aim_frames:
                    self._draw_aiming_hyperion(
                        screen, strike, local, offset_x, offset_y)
                else:
                    self._draw_hyperion(screen, strike["target"], strike["angle"],
                                        offset_x, offset_y)
                continue

            # After all strikes, do not spawn replacement Hyperions.
            if final_t > 0:
                continue

            # Waiting Hyperions hover in front of the player, facing upward.
            wait_pos = self._front_position(i)
            self._draw_hyperion(screen, wait_pos, -math.pi / 2,
                                offset_x, offset_y, alpha=225)

    def _draw_aiming_hyperion(self, screen, strike, local, offset_x=0, offset_y=0):
        start = strike["start"]
        target = strike["target"]
        angle = strike["angle"]
        self._draw_hyperion(screen, start, angle, offset_x, offset_y)

        progress = min(1.0, (local + 1) / self.aim_frames)
        sx = offset_x + start[0]
        sy = offset_y + start[1]
        tx = offset_x + start[0] + (target[0] - start[0]) * progress
        ty = offset_y + start[1] + (target[1] - start[1]) * progress
        pygame.draw.line(screen, cfg.COLOR_WHITE, (int(sx), int(sy)),
                         (int(tx), int(ty)), 2)
        pygame.draw.line(screen, (180, 235, 255), (int(sx), int(sy)),
                         (int(tx), int(ty)), 1)

    def _draw_hyperion(self, screen, pos, angle, offset_x=0, offset_y=0, alpha=255):
        sprite = self.hyperion_sprite
        if sprite is None:
            # Fallback: simple sword-like diamond/line.
            px, py = int(pos[0] + offset_x), int(pos[1] + offset_y)
            pygame.draw.circle(screen, (120, 200, 255), (px, py), 10, 2)
            return

        # The source sprite points upward. Pygame rotation is CCW-positive,
        # so this mapping points it toward ``angle`` (screen coordinates).
        rotated = pygame.transform.rotate(sprite, -math.degrees(angle) - 90)
        if alpha < 255:
            rotated = _with_alpha(rotated, alpha)
        px = int(pos[0] + offset_x - rotated.get_width() // 2)
        py = int(pos[1] + offset_y - rotated.get_height() // 2)
        screen.blit(rotated, (px, py))

    def _draw_explosion(self, screen, start, target, age, offset_x=0, offset_y=0):
        sx, sy = start
        tx, ty = target
        length = math.hypot(tx - sx, ty - sy)
        if length <= 0.001:
            return

        # Expansion at the beginning, fade near the end.
        attack = min(1.0, age / max(1, self.explosion_frames * 0.35))
        fade = max(0.0, 1.0 - (age - self.explosion_frames * 0.62) /
                   max(1, self.explosion_frames * 0.38))
        intensity = attack * fade
        if intensity <= 0.0:
            return

        max_radius = max(20.0, min(82.0, 22.0 + length * 0.16))
        base_radius = max(6.0, max_radius * intensity)
        steps = max(10, min(30, int(length // 12) + 1))

        # Radius is largest at both endpoints and smallest in the middle.
        for k in range(steps + 1):
            s = k / steps
            edge_factor = abs(s - 0.5) * 2.0  # 1 at ends, 0 at center.
            radius = max(3.0, base_radius * (0.26 + 0.74 * edge_factor))
            px = int(offset_x + sx + (tx - sx) * s)
            py = int(offset_y + sy + (ty - sy) * s)
            if radius < 1:
                continue
            pygame.draw.circle(screen, cfg.COLOR_WHITE, (px, py), int(radius), 0)
            pygame.draw.circle(screen, cfg.COLOR_WHITE, (px, py),
                               max(1, int(radius * 0.62)), 0)
            pygame.draw.circle(screen, cfg.COLOR_WHITE, (px, py),
                               max(1, int(radius * 0.22)), 0)

        # Central white beam.
        pygame.draw.line(
            screen, (255, 255, 255),
            (int(offset_x + sx), int(offset_y + sy)),
            (int(offset_x + tx), int(offset_y + ty)),
            max(2, int(3 * intensity)))

    def _draw_banner(self, screen, offset_x=0, offset_y=0):
        t = self.timer / BANNER_DURATION
        fade_in = 8 / BANNER_DURATION
        fade_out = 10 / BANNER_DURATION
        if t < fade_in:
            alpha = int(255 * t / fade_in)
        elif t > 1.0 - fade_out:
            alpha = int(255 * (1.0 - t) / fade_out)
        else:
            alpha = 255
        alpha = max(0, min(255, alpha))

        cx = offset_x + cfg.BATTLE_AREA_WIDTH // 2
        cy = offset_y + cfg.BATTLE_AREA_HEIGHT // 2 + int(t * 24)

        if self.portrait is not None:
            portrait = _with_alpha(self.portrait, alpha)
            screen.blit(portrait, (cx - portrait.get_width() // 2,
                                   cy - portrait.get_height() // 2))

        # Spell name box, matching the boss declaration style.
        font = self.game.font_large
        text = font.render(self.name, True, cfg.COLOR_WHITE)
        text = _with_alpha(text, alpha)
        pad_x, pad_y = 18, 8
        box = pygame.Surface((text.get_width() + pad_x * 2,
                              text.get_height() + pad_y * 2), pygame.SRCALPHA)
        box.fill((10, 14, 26, int(alpha * 0.62)))
        pygame.draw.rect(box, (255, 255, 255, int(alpha * 0.85)),
                         box.get_rect(), 2, border_radius=6)
        box.blit(text, (pad_x, pad_y))
        screen.blit(box, (cx - box.get_width() // 2,
                          cy + 165 - box.get_height() // 2))
