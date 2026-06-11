import math
import random

import pygame

from scenes.base import Scene
from core.controls import get_controls
from core.constants import (
    SCENE_MAIN,
    BLACK,
    WHITE,
    YELLOW,
    GRAY,
    DGRAY,
    RED,
    CYAN,
    ORANGE,
    WIDTH,
    HEIGHT,
)
from ui.draw import draw_box, draw_text_outline


PLAYFIELD = pygame.Rect(74, 150, 652, 390)
UI_TOP = 548

PLAYFIELD_CENTER = pygame.Vector2(PLAYFIELD.centerx, PLAYFIELD.centery)
PHASE_NAMES = [
    "BOOT / SYSTEM ONLINE",
    "PHASE 1 / SHOCK LINE",
    "PHASE 2 / GRAPPLE NET",
    "PHASE 3 / STUN FIELD",
    "PHASE 4 / KNOCKBACK SWEEP",
]

PLAYER_COLORS = {
    "body": (72, 72, 80),
    "visor": CYAN,
    "trim": (120, 120, 130),
    "glow": (88, 255, 220),
}

ITEM_DEFS = [
    {"name": "회복", "kind": "heal", "color": (90, 220, 120), "desc": "체력 +1"},
    {"name": "방어막", "kind": "shield", "color": (120, 180, 255), "desc": "잠시 무적"},
    {"name": "폭탄", "kind": "bomb", "color": ORANGE, "desc": "탄막 정리"},
]


class GameScene(Scene):
    def __init__(self, screen, fonts, shared):
        super().__init__(screen, fonts, shared)
        self.controls = get_controls(shared)
        self.boot_timer = 2.0

        self.player_pos = pygame.Vector2(PLAYFIELD.centerx, PLAYFIELD.bottom - 56)
        self.player_speed = 280.0
        self.player_focus_speed = 170.0
        self.player_hit_radius = 7
        self.player_hp = 6
        self.player_invuln = 0.0
        self.fire_timer = 0.0

        self.boss_pos = pygame.Vector2(PLAYFIELD.centerx, PLAYFIELD.y + 76)
        self.boss_rect = pygame.Rect(0, 0, 74, 74)
        self.boss_rect.center = (int(self.boss_pos.x), int(self.boss_pos.y))
        self.phase_level = 0
        self.boss_hp_max = 80
        self.boss_hp = self.boss_hp_max
        self.boss_dir = 1
        self.boss_speed = 90.0
        self.enemy_timer = 0.0
        self.attack_index = 0
        self.attack_windup = 0.0
        self.pending_pattern = None
        self.pending_attack_name = "BOOT / SYSTEM ONLINE"
        self.phase_index = 0
        self.control_lock = 0.0
        self.knockback_velocity = pygame.Vector2(0, 0)
        self.grapple_timer = 0.0
        self.grapple_origin = None
        self.grapple_hit_flash = 0.0
        self.stun_timer = 0.0
        self.push_timer = 0.0
        self.boss_side = -1

        self.player_bullets: list[dict] = []
        self.enemy_bullets: list[dict] = []
        self.field_walls: list[dict] = []
        self.grapple_lines: list[dict] = []
        self.pickups: list[dict] = self._build_pickups()

        self.inventory = [
            {"name": "회복", "kind": "heal", "count": 1, "color": (90, 220, 120), "desc": "코어 회복"},
            {"name": "방어막", "kind": "shield", "count": 1, "color": (120, 180, 255), "desc": "방어 메트릭스"},
            {"name": "충격탄", "kind": "bomb", "count": 1, "color": ORANGE, "desc": "탄막 정리"},
        ]
        self.active_slot = 0

        self.stars = [
            [random.randrange(WIDTH), random.randrange(HEIGHT), random.randint(1, 3)]
            for _ in range(80)
        ]

        self.star_scroll = 0.0
        self.blink = 0
        self.result = None
        self.phase_banner_timer = 0.0
        self.phase_banner_text = PHASE_NAMES[0]
        self.boss_base_pos = pygame.Vector2(PLAYFIELD.centerx, PLAYFIELD.y + 76)
        self.boss_move_timer = 0.0
        self.boss_move_mode = 0
        self.boss_target = pygame.Vector2(self.boss_base_pos.x, self.boss_base_pos.y)

    def _build_pickups(self) -> list[dict]:
        return [
            {"rect": pygame.Rect(148, 362, 28, 28), "kind": "heal", "color": (90, 220, 120)},
            {"rect": pygame.Rect(372, 422, 28, 28), "kind": "shield", "color": (120, 180, 255)},
            {"rect": pygame.Rect(610, 360, 28, 28), "kind": "bomb", "color": ORANGE},
        ]

    def _current_item(self) -> dict:
        if not self.inventory:
            return {"name": "없음", "kind": None, "count": 0, "color": GRAY, "desc": ""}
        return self.inventory[self.active_slot % len(self.inventory)]

    def _cycle_slot(self) -> None:
        if self.inventory:
            for step in range(1, len(self.inventory) + 1):
                next_slot = (self.active_slot + step) % len(self.inventory)
                if self.inventory[next_slot]["count"] > 0:
                    self.active_slot = next_slot
                    return
            self.active_slot = (self.active_slot + 1) % len(self.inventory)

    def _use_item(self) -> None:
        item = self._current_item()
        if item["count"] <= 0:
            return

        if item["kind"] == "heal":
            self.player_hp = min(6, self.player_hp + 2)
        elif item["kind"] == "shield":
            self.player_invuln = 2.5
        elif item["kind"] == "bomb":
            self.enemy_bullets.clear()
            self.field_walls.clear()
            self.grapple_lines.clear()
            self.boss_hp = max(0, self.boss_hp - 10)

        item["count"] -= 1

    def _spawn_player_bullet(self) -> None:
        self.player_bullets.append(
            {
                "pos": pygame.Vector2(self.player_pos.x, self.player_pos.y - 12),
                "vel": pygame.Vector2(0, -480),
                "radius": 4,
                "color": (80, 255, 220),
            }
        )

    def _spawn_enemy_bullet(self, angle: float, speed: float, color, radius: int = 5, origin=None) -> None:
        if origin is None:
            origin = pygame.Vector2(self.boss_pos.x, self.boss_pos.y + 30)
        self.enemy_bullets.append(
            {
                "pos": pygame.Vector2(origin.x, origin.y),
                "vel": pygame.Vector2(math.cos(angle) * speed, math.sin(angle) * speed),
                "radius": radius,
                "color": color,
            }
        )

    def _phase_scale(self) -> tuple[float, float]:
        speed_scale = 1.0 + self.phase_level * 0.18
        timer_scale = max(0.58, 1.0 - self.phase_level * 0.10)
        return speed_scale, timer_scale

    def _advance_phase(self) -> None:
        self.phase_level += 1
        self.boss_hp_max = min(160, 80 + self.phase_level * 30)
        self.boss_hp = self.boss_hp_max
        self.attack_index = 0
        self.phase_index = 0
        self.enemy_timer = 0.0
        self.attack_windup = 0.65
        self.pending_pattern = None
        self.phase_banner_text = f"PHASE {self.phase_level} / SYSTEM ESCALATION"
        self.phase_banner_timer = 1.5
        self.enemy_bullets.clear()
        self.field_walls.clear()
        self.grapple_origin = None
        self.grapple_timer = 0.0
        self.grapple_hit_flash = 0.0
        self.stun_timer = 0.0
        self.push_timer = 0.0
        self.control_lock = 0.35
        self.knockback_velocity = pygame.Vector2(0, 0)
        self.boss_move_timer = 0.0
        self.boss_move_mode = 0

    def _update_boss_behavior(self, dt_sec: float) -> None:
        self.boss_move_timer += dt_sec

        if self.boot_timer > 0.0:
            self.boss_target = pygame.Vector2(self.boss_base_pos.x, self.boss_base_pos.y)
        elif self.phase_level == 0:
            x = self.boss_base_pos.x + math.sin(self.boss_move_timer * 1.8) * 62
            y = self.boss_base_pos.y + math.sin(self.boss_move_timer * 3.2) * 8
            self.boss_target = pygame.Vector2(x, y)
        elif self.phase_level == 1:
            if self.boss_move_timer >= 1.1:
                self.boss_move_timer = 0.0
                self.boss_move_mode = 1 - self.boss_move_mode
            x = PLAYFIELD.left + 170 if self.boss_move_mode == 0 else PLAYFIELD.right - 170
            y = self.boss_base_pos.y + 6
            self.boss_target = pygame.Vector2(x, y)
        elif self.phase_level == 2:
            orbit_angle = self.boss_move_timer * 1.4
            x = self.boss_base_pos.x + math.cos(orbit_angle) * 72
            y = self.boss_base_pos.y + math.sin(orbit_angle * 1.8) * 16
            self.boss_target = pygame.Vector2(x, y)
        else:
            if self.boss_move_timer >= 0.85:
                self.boss_move_timer = 0.0
                self.boss_move_mode = (self.boss_move_mode + 1) % 3
            if self.boss_move_mode == 0:
                self.boss_target = pygame.Vector2(self.boss_base_pos.x, self.boss_base_pos.y)
            elif self.boss_move_mode == 1:
                self.boss_target = pygame.Vector2(self.boss_base_pos.x - 80, self.boss_base_pos.y + 8)
            else:
                self.boss_target = pygame.Vector2(self.boss_base_pos.x + 80, self.boss_base_pos.y + 8)

        self.boss_target.x = max(PLAYFIELD.left + 120, min(PLAYFIELD.right - 120, self.boss_target.x))
        self.boss_target.y = max(PLAYFIELD.top + 54, min(PLAYFIELD.top + 128, self.boss_target.y))
        self.boss_pos += (self.boss_target - self.boss_pos) * min(1.0, 5.0 * dt_sec)
        self.boss_rect.center = (int(self.boss_pos.x), int(self.boss_pos.y))

    def _sync_boss_position(self, dt_sec: float) -> None:
        self._update_boss_behavior(dt_sec)

    def _maybe_advance_phase(self) -> None:
        if self.boss_hp <= 0 and self.result is None:
            if self.phase_level >= 3:
                self.result = "clear"
            else:
                self._advance_phase()

    def _spawn_wall_squeeze(self) -> None:
        left_wall = pygame.Rect(PLAYFIELD.left + 4, PLAYFIELD.top + 4, 20, PLAYFIELD.height - 8)
        right_wall = pygame.Rect(PLAYFIELD.right - 24, PLAYFIELD.top + 4, 20, PLAYFIELD.height - 8)
        _, timer_scale = self._phase_scale()
        self.field_walls.extend([
            {"rect": left_wall, "vx": 38 + self.phase_level * 8, "life": 2.4 * timer_scale, "color": (255, 140, 120)},
            {"rect": right_wall, "vx": -38 - self.phase_level * 8, "life": 2.4 * timer_scale, "color": (255, 140, 120)},
        ])

    def _spawn_grapple(self) -> None:
        self.grapple_origin = pygame.Vector2(self.boss_pos.x, self.boss_pos.y + 24)
        _, timer_scale = self._phase_scale()
        self.grapple_timer = 1.0 * timer_scale
        self.grapple_hit_flash = 0.25

    def _spawn_stun_field(self) -> None:
        _, timer_scale = self._phase_scale()
        self.stun_timer = 0.9 * timer_scale

    def _spawn_knockback_sweep(self) -> None:
        _, timer_scale = self._phase_scale()
        self.push_timer = 1.0 * timer_scale
        self.control_lock = 0.4

    def _spawn_shock_line(self) -> None:
        aim = pygame.Vector2(self.player_pos.x - self.boss_pos.x, self.player_pos.y - self.boss_pos.y)
        if aim.length_squared() == 0:
            aim = pygame.Vector2(0, 1)
        base_angle = math.atan2(aim.y, aim.x)
        speed_scale, _ = self._phase_scale()
        offsets = (-0.12, 0.0, 0.12)
        if self.phase_level >= 2:
            offsets = (-0.22, -0.12, 0.0, 0.12, 0.22)
        for offset in offsets:
            self._spawn_enemy_bullet(base_angle + offset, 165 * speed_scale, (255, 130, 130), radius=5)

    def _spawn_aimed_fan(self) -> None:
        aim = pygame.Vector2(self.player_pos.x - self.boss_pos.x, self.player_pos.y - self.boss_pos.y)
        if aim.length_squared() == 0:
            aim = pygame.Vector2(0, 1)
        base_angle = math.atan2(aim.y, aim.x)
        speed_scale, _ = self._phase_scale()
        if self.phase_level >= 2:
            fan_offsets = (-0.34, -0.20, -0.08, 0.0, 0.08, 0.20, 0.34, 0.48, -0.48)
            speeds = (140, 152, 164, 168, 164, 152, 140, 160, 160)
            colors = ((255, 96, 132), (255, 160, 92), (255, 96, 132), (255, 210, 90), (255, 96, 132), (255, 160, 92), (255, 96, 132), (255, 210, 90), (255, 210, 90))
            limit = min(len(fan_offsets), 5 + self.phase_level)
            for offset, speed, color in zip(fan_offsets[:limit], speeds[:limit], colors[:limit]):
                self._spawn_enemy_bullet(base_angle + offset, speed * speed_scale, color, radius=5)
            return

        fan_offsets = (-0.30, -0.14, 0.0, 0.14, 0.30, 0.42, -0.42)
        speeds = (135, 150, 160, 150, 135, 165, 165)
        colors = ((255, 96, 132), (255, 160, 92), (255, 96, 132), (255, 160, 92), (255, 96, 132), (255, 210, 90), (255, 210, 90))
        limit = min(len(fan_offsets), 5 + self.phase_level)
        for offset, speed, color in zip(fan_offsets[:limit], speeds[:limit], colors[:limit]):
            self._spawn_enemy_bullet(base_angle + offset, speed * speed_scale, color, radius=5)

    def _spawn_ring(self) -> None:
        speed_scale, _ = self._phase_scale()
        ring_count = 10 + self.phase_level * 2
        base_angle = (self.attack_index * 0.18) % math.tau
        for i in range(ring_count):
            angle = base_angle + (math.tau * i / ring_count)
            speed = (82 + (i % 2) * 8) * speed_scale
            color = (120, 190, 255) if i % 2 == 0 else (120, 255, 210)
            self._spawn_enemy_bullet(angle, speed, color, radius=4)

    def _spawn_stream(self) -> None:
        aim = pygame.Vector2(self.player_pos.x - self.boss_pos.x, self.player_pos.y - self.boss_pos.y)
        if aim.length_squared() == 0:
            aim = pygame.Vector2(0, 1)
        base_angle = math.atan2(aim.y, aim.x)
        speed_scale, _ = self._phase_scale()

        offsets = (-0.08, 0.0, 0.08)
        if self.phase_level >= 3:
            offsets = (-0.14, -0.08, 0.0, 0.08, 0.14)
        for offset in offsets:
            self._spawn_enemy_bullet(base_angle + offset, 160 * speed_scale, (255, 70, 70), radius=5)

    def _spawn_spiral(self) -> None:
        speed_scale, _ = self._phase_scale()
        base_angle = (self.attack_index * 0.45) % math.tau
        for i in range(6 + self.phase_level * 2):
            angle = base_angle + i * 0.24
            self._spawn_enemy_bullet(angle, 95 * speed_scale, (170, 120, 255), radius=4)

    def _spawn_cross(self) -> None:
        aim = pygame.Vector2(self.player_pos.x - self.boss_pos.x, self.player_pos.y - self.boss_pos.y)
        if aim.length_squared() == 0:
            aim = pygame.Vector2(0, 1)
        base_angle = math.atan2(aim.y, aim.x)
        speed_scale, _ = self._phase_scale()
        for offset in (-0.36, 0.0, 0.36):
            self._spawn_enemy_bullet(base_angle + offset, 135 * speed_scale, (255, 210, 90), radius=5)

    def _spawn_spray(self) -> None:
        speed_scale, _ = self._phase_scale()
        for offset in (-0.55, -0.32, 0.0, 0.32, 0.55):
            angle = math.pi / 2 + offset + random.uniform(-0.05, 0.05)
            self._spawn_enemy_bullet(angle, 100 * speed_scale, (110, 240, 220), radius=4)

    def _spawn_side_pressure(self) -> None:
        side = -1 if (self.phase_level + self.attack_index) % 2 == 0 else 1
        side_y = PLAYFIELD.top + 44 if side < 0 else PLAYFIELD.bottom - 44
        origin = pygame.Vector2(PLAYFIELD.left + 24, side_y)
        speed_scale, _ = self._phase_scale()
        for step in range(7):
            speed = (155 + step * 8) * speed_scale
            self._spawn_enemy_bullet(0.0 if side < 0 else math.pi, speed, (255, 90, 200), radius=5, origin=origin)

    def _spawn_grapple_shot(self) -> None:
        base = math.atan2(self.player_pos.y - self.boss_pos.y, self.player_pos.x - self.boss_pos.x)
        speed_scale, _ = self._phase_scale()
        for offset in (-0.05, 0.0, 0.05):
            self._spawn_enemy_bullet(base + offset, 175 * speed_scale, (160, 220, 255), radius=4)

    def _spawn_pattern(self) -> None:
        pattern = self.phase_index % 6
        if pattern == 0:
            self._spawn_aimed_fan()
        elif pattern == 1:
            self._spawn_ring()
        else:
            if pattern == 2:
                self._spawn_stream()
                self._spawn_grapple_shot()
            elif pattern == 3:
                self._spawn_spiral()
                self._spawn_wall_squeeze()
            elif pattern == 4:
                self._spawn_cross()
                self._spawn_stun_field()
            else:
                self._spawn_spray()
                self._spawn_side_pressure()
        self.attack_index += 1
        self.phase_index = (self.phase_index + 1) % 6
        self.phase_banner_text = f"PHASE {self.phase_level + 1} / SYSTEM ESCALATION"
        self.phase_banner_timer = 1.0

    def _update_walls(self, dt_sec: float) -> None:
        new_walls: list[dict] = []
        for wall in self.field_walls:
            wall["life"] -= dt_sec
            wall["rect"].x += int(wall["vx"] * dt_sec)
            if wall["life"] > 0:
                new_walls.append(wall)
        self.field_walls = new_walls

    def _apply_wall_collisions(self) -> None:
        for wall in self.field_walls:
            if wall["rect"].collidepoint(self.player_pos.x, self.player_pos.y):
                if wall["vx"] > 0:
                    self.player_pos.x = wall["rect"].right + 8
                else:
                    self.player_pos.x = wall["rect"].left - 8

    def _apply_grapple(self, dt_sec: float) -> None:
        if self.grapple_timer <= 0.0 or self.grapple_origin is None:
            return
        to_origin = pygame.Vector2(self.grapple_origin.x - self.player_pos.x, self.grapple_origin.y - self.player_pos.y)
        if to_origin.length_squared() > 1:
            pull = to_origin.normalize() * 210 * dt_sec
            self.player_pos += pull
        self.grapple_timer = max(0.0, self.grapple_timer - dt_sec)

    def _apply_stun(self, dt_sec: float) -> None:
        if self.stun_timer <= 0.0:
            return
        self.stun_timer = max(0.0, self.stun_timer - dt_sec)
        if self.stun_timer > 0.2:
            self.control_lock = max(self.control_lock, 0.1)

    def _apply_knockback(self, dt_sec: float) -> None:
        if self.push_timer <= 0.0:
            return
        self.push_timer = max(0.0, self.push_timer - dt_sec)
        if self.push_timer > 0.0:
            self.player_pos += self.knockback_velocity * dt_sec

    def _update_stars(self, dt: float) -> None:
        for star in self.stars:
            star[1] += star[2] * 28 * dt
            if star[1] > HEIGHT:
                star[0] = random.randrange(WIDTH)
                star[1] = -4
                star[2] = random.randint(1, 3)

    def _draw_starfield(self, surf: pygame.Surface) -> None:
        for x, y, size in self.stars:
            color = (120, 120, 150) if size == 1 else (170, 170, 200) if size == 2 else (220, 220, 255)
            pygame.draw.rect(surf, color, (int(x), int(y), size, size))

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        controls = self.controls

        if event.key == pygame.K_ESCAPE:
            self.next_scene = SCENE_MAIN
        elif event.key == controls["slot_change"]:
            self._cycle_slot()
        elif event.key == controls["use_item"]:
            self._use_item()

    def update(self, dt: int) -> None:
        dt_sec = dt / 1000.0
        self.blink += 1
        self.star_scroll += 70 * dt_sec

        if self.phase_banner_timer > 0.0:
            self.phase_banner_timer = max(0.0, self.phase_banner_timer - dt_sec)

        if self.result is not None:
            return

        if self.boot_timer > 0.0:
            self.boot_timer = max(0.0, self.boot_timer - dt_sec)

        self.controls = get_controls(self.shared)
        pressed = pygame.key.get_pressed()
        focus = pressed[pygame.K_LSHIFT] or pressed[pygame.K_RSHIFT]

        move_x = 0.0
        move_y = 0.0
        if pressed[self.controls["move_left"]]:
            move_x -= 1.0
        if pressed[self.controls["move_right"]]:
            move_x += 1.0
        if pressed[self.controls["move_up"]]:
            move_y -= 1.0
        if pressed[self.controls["move_down"]]:
            move_y += 1.0

        if self.boot_timer <= 0.0 and self.control_lock <= 0.0:
            move = pygame.Vector2(move_x, move_y)
            if move.length_squared() > 0:
                speed = self.player_focus_speed if focus else self.player_speed
                move = move.normalize() * speed * dt_sec
                self.player_pos += move
        else:
            self.control_lock = max(0.0, self.control_lock - dt_sec)

        self.player_pos.x = max(PLAYFIELD.left + 20, min(PLAYFIELD.right - 20, self.player_pos.x))
        self.player_pos.y = max(PLAYFIELD.top + 22, min(PLAYFIELD.bottom - 20, self.player_pos.y))

        self._apply_wall_collisions()
        self._apply_grapple(dt_sec)
        self._apply_stun(dt_sec)
        self._apply_knockback(dt_sec)

        if self.boot_timer <= 0.0:
            self.fire_timer += dt_sec
            if self.fire_timer >= 0.2:
                self.fire_timer = 0.0
                self._spawn_player_bullet()

        if self.attack_windup > 0.0:
            self.attack_windup = max(0.0, self.attack_windup - dt_sec)
            if self.attack_windup == 0.0 and self.pending_pattern is not None:
                self.pending_pattern()
                self.pending_pattern = None

        if self.boot_timer <= 0.0:
            self.enemy_timer += dt_sec
            if self.enemy_timer >= 1.15:
                self.enemy_timer = 0.0
                self.attack_windup = 0.45
                self.pending_pattern = self._spawn_pattern

        self._sync_boss_position(dt_sec)

        self._update_walls(dt_sec)

        for bullet in self.player_bullets:
            bullet["pos"] += bullet["vel"] * dt_sec
        self.player_bullets = [
            bullet for bullet in self.player_bullets if PLAYFIELD.collidepoint(int(bullet["pos"].x), int(bullet["pos"].y))
        ]

        for bullet in self.enemy_bullets:
            bullet["pos"] += bullet["vel"] * dt_sec
        self.enemy_bullets = [
            bullet for bullet in self.enemy_bullets if PLAYFIELD.collidepoint(int(bullet["pos"].x), int(bullet["pos"].y))
        ]

        if self.grapple_hit_flash > 0.0:
            self.grapple_hit_flash = max(0.0, self.grapple_hit_flash - dt_sec)
            if self.grapple_hit_flash > 0.0 and random.random() < 0.08:
                self.enemy_bullets.append(
                    {
                        "pos": pygame.Vector2(self.player_pos.x, self.player_pos.y),
                        "vel": pygame.Vector2(random.uniform(-40, 40), random.uniform(-40, 40)),
                        "radius": 2,
                        "color": YELLOW,
                    }
                )

        for pickup in self.pickups:
            if pickup.get("used"):
                continue
            if pickup["rect"].collidepoint(self.player_pos.x, self.player_pos.y):
                for item in self.inventory:
                    if item["kind"] == pickup["kind"]:
                        item["count"] += 1
                        break
                pickup["used"] = True

        self.player_invuln = max(0.0, self.player_invuln - dt_sec)

        player_hit = pygame.Vector2(self.player_pos.x, self.player_pos.y)
        if self.player_invuln <= 0.0:
            hit_radius = 4 if focus else self.player_hit_radius
            for bullet in self.enemy_bullets:
                if player_hit.distance_to(bullet["pos"]) <= hit_radius + bullet["radius"]:
                    self.player_hp -= 1
                    self.player_invuln = 1.2
                    bullet["pos"].x = -9999
                    break

        if self.phase_level % 2 == 1 and self.player_invuln <= 0.0:
            for wall in self.field_walls:
                if wall["rect"].collidepoint(player_hit.x, player_hit.y):
                    self.player_hp -= 1
                    self.player_invuln = 1.0
                    self.knockback_velocity = pygame.Vector2(220 if wall["vx"] < 0 else -220, 0)
                    break

        new_player_bullets: list[dict] = []
        for bullet in self.player_bullets:
            if bullet["pos"].distance_to(self.boss_pos) <= bullet["radius"] + 34:
                self.boss_hp = max(0, self.boss_hp - 1)
            else:
                new_player_bullets.append(bullet)
        self.player_bullets = new_player_bullets

        self._maybe_advance_phase()

        if self.player_hp <= 0:
            self.result = "fail"

    def draw(self, surf: pygame.Surface) -> None:
        self._draw_starfield(surf)

        pygame.draw.rect(surf, (8, 12, 22), PLAYFIELD)
        draw_box(surf, PLAYFIELD, WHITE, 3)

        for wall in self.field_walls:
            pygame.draw.rect(surf, wall["color"], wall["rect"])
            draw_box(surf, wall["rect"], WHITE, 2)

        if self.grapple_origin is not None and self.grapple_timer > 0.0:
            start = (int(self.grapple_origin.x), int(self.grapple_origin.y))
            end = (int(self.player_pos.x), int(self.player_pos.y))
            pygame.draw.line(surf, CYAN, start, end, 3)
            hook = pygame.Rect(0, 0, 14, 14)
            hook.center = start
            pygame.draw.rect(surf, CYAN, hook, 2)

        for pickup in self.pickups:
            if pickup.get("used"):
                continue
            pygame.draw.rect(surf, pickup["color"], pickup["rect"])
            draw_box(surf, pickup["rect"], WHITE, 2)
            icon = self.fonts["small"].render(pickup["kind"][0].upper(), False, BLACK)
            surf.blit(icon, (pickup["rect"].x + 8, pickup["rect"].y + 3))

        self._draw_boss(surf)
        self._draw_player(surf)
        self._draw_bullets(surf)
        self._draw_ui(surf)

        if self.boot_timer > 0.0:
            self._draw_boot_overlay(surf)

        if self.result == "clear":
            self._draw_center_banner(surf, "STAGE CLEAR", CYAN)
        elif self.result == "fail":
            self._draw_center_banner(surf, "MISSION FAILED", RED)

    def _draw_boss(self, surf: pygame.Surface) -> None:
        pygame.draw.rect(surf, RED, self.boss_rect)
        draw_box(surf, self.boss_rect, WHITE, 2)
        label = self.fonts["small"].render("ZERO", False, WHITE)
        surf.blit(label, (self.boss_rect.centerx - label.get_width() // 2, self.boss_rect.y - 18))

        hp_ratio = self.boss_hp / max(1, self.boss_hp_max)
        hp_bar = pygame.Rect(PLAYFIELD.left + 90, PLAYFIELD.top + 18, PLAYFIELD.width - 180, 8)
        pygame.draw.rect(surf, DGRAY, hp_bar)
        pygame.draw.rect(surf, RED, (hp_bar.x, hp_bar.y, int(hp_bar.width * hp_ratio), hp_bar.height))
        pygame.draw.rect(surf, WHITE, hp_bar, 1)

    def _draw_player(self, surf: pygame.Surface) -> None:
        invuln_flash = self.player_invuln > 0 and (self.blink // 4) % 2 == 0
        body_color = (200, 220, 255) if invuln_flash else PLAYER_COLORS["body"]
        glow_color = (255, 255, 255) if invuln_flash else PLAYER_COLORS["glow"]

        center = (int(self.player_pos.x), int(self.player_pos.y))
        body_rect = pygame.Rect(0, 0, 26, 32)
        body_rect.center = center
        helmet_rect = pygame.Rect(0, 0, 32, 26)
        helmet_rect.midbottom = (center[0], center[1] - 6)

        pygame.draw.circle(surf, glow_color, center, 16)
        pygame.draw.rect(surf, body_color, body_rect)
        pygame.draw.rect(surf, PLAYER_COLORS["trim"], body_rect, 2)
        pygame.draw.rect(surf, (55, 55, 62), helmet_rect)
        pygame.draw.rect(surf, PLAYER_COLORS["trim"], helmet_rect, 2)
        visor = pygame.Rect(0, 0, 14, 8)
        visor.center = (center[0] + 2, center[1] - 8)
        pygame.draw.rect(surf, PLAYER_COLORS["visor"], visor)
        pygame.draw.circle(surf, glow_color, (center[0], center[1] + 1), 4)

    def _draw_bullets(self, surf: pygame.Surface) -> None:
        for bullet in self.player_bullets:
            pygame.draw.circle(surf, bullet["color"], (int(bullet["pos"].x), int(bullet["pos"].y)), bullet["radius"])
        for bullet in self.enemy_bullets:
            pygame.draw.circle(surf, bullet["color"], (int(bullet["pos"].x), int(bullet["pos"].y)), bullet["radius"])

        if self.attack_windup > 0.0:
            telegraph = pygame.Rect(PLAYFIELD.left + 16, PLAYFIELD.top + 52, PLAYFIELD.width - 32, 8)
            pygame.draw.rect(surf, DGRAY, telegraph)
            fill = int(telegraph.width * (1.0 - self.attack_windup / 0.32))
            pygame.draw.rect(surf, YELLOW, (telegraph.x, telegraph.y, fill, telegraph.height))
            pygame.draw.rect(surf, WHITE, telegraph, 1)

    def _draw_ui(self, surf: pygame.Surface) -> None:
        ui_box = pygame.Rect(72, UI_TOP, 656, 44)
        pygame.draw.rect(surf, BLACK, ui_box)
        draw_box(surf, ui_box, WHITE, 2)

        hp_label = self.fonts["small"].render("코어 안정도", False, YELLOW)
        surf.blit(hp_label, (ui_box.x + 10, ui_box.y + 10))

        hp_bar = pygame.Rect(ui_box.x + 90, ui_box.y + 12, 110, 14)
        pygame.draw.rect(surf, DGRAY, hp_bar)
        draw_box(surf, hp_bar, WHITE, 1)
        segment_gap = 2
        segment_width = (hp_bar.width - segment_gap * 5) // 6
        for index in range(6):
            segment = pygame.Rect(
                hp_bar.x + index * (segment_width + segment_gap),
                hp_bar.y,
                segment_width,
                hp_bar.height,
            )
            filled = index < self.player_hp
            pygame.draw.rect(surf, RED if filled else (50, 50, 58), segment)
            pygame.draw.rect(surf, WHITE if filled else DGRAY, segment, 1)

        controls_text = self.fonts["small"].render("X:다음 아이템  Z:사용  SHIFT:포커스", False, GRAY)
        surf.blit(controls_text, (ui_box.right - controls_text.get_width() - 10, ui_box.y + 10))

        inv_box = pygame.Rect(74, 500, 424, 40)
        use_box = pygame.Rect(510, 500, 216, 40)
        pygame.draw.rect(surf, BLACK, inv_box)
        pygame.draw.rect(surf, BLACK, use_box)
        draw_box(surf, inv_box, WHITE, 2)
        draw_box(surf, use_box, WHITE, 2)

        inv_label = self.fonts["small"].render("정비 칸", False, CYAN)
        use_label = self.fonts["small"].render("사용 슬롯", False, CYAN)
        surf.blit(inv_label, (inv_box.x + 8, inv_box.y - 18))
        surf.blit(use_label, (use_box.x + 8, use_box.y - 18))

        slot_w = 128
        for i, item in enumerate(self.inventory):
            slot = pygame.Rect(inv_box.x + 8 + i * 138, inv_box.y + 6, slot_w, 28)
            is_active = i == self.active_slot
            pygame.draw.rect(surf, DGRAY if is_active else (25, 25, 28), slot)
            draw_box(surf, slot, item["color"] if is_active else GRAY, 2)
            name = f'{item["name"]} x{item["count"]}'
            text = self.fonts["small"].render(name, False, WHITE if item["count"] > 0 else GRAY)
            surf.blit(text, (slot.x + 8, slot.y + 6))
            if is_active:
                pivot = self.fonts["small"].render("▼", False, YELLOW)
                surf.blit(pivot, (slot.centerx - pivot.get_width() // 2, slot.y - 10))
                pivot_line_y = slot.y + slot.height + 2
                pygame.draw.line(surf, YELLOW, (slot.centerx, pivot_line_y), (slot.centerx, pivot_line_y + 8), 2)

        current = self._current_item()
        pygame.draw.rect(surf, DGRAY, (use_box.x + 8, use_box.y + 6, use_box.width - 16, 28))
        draw_box(surf, pygame.Rect(use_box.x + 8, use_box.y + 6, use_box.width - 16, 28), current["color"], 2)
        text = self.fonts["small"].render(f'{current["name"]} - {current["desc"]}', False, WHITE)
        surf.blit(text, (use_box.x + 14, use_box.y + 12))

        x_hint = self.fonts["small"].render("원형큐처럼 다음 정비 장비로 회전", False, GRAY)
        surf.blit(x_hint, (use_box.right - x_hint.get_width() - 10, use_box.y - 18))

        if self.blink % 60 < 40:
            hint = self.fonts["small"].render("SHIFT:포커스  ESC:메인 메뉴", False, GRAY)
            surf.blit(hint, (PLAYFIELD.right - hint.get_width() - 8, PLAYFIELD.bottom + 8))

        if self.phase_banner_timer > 0.0:
            banner = self.fonts["small"].render(self.phase_banner_text, False, CYAN)
            surf.blit(banner, (WIDTH // 2 - banner.get_width() // 2, PLAYFIELD.top - 24))

    def _draw_boot_overlay(self, surf: pygame.Surface) -> None:
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surf.blit(overlay, (0, 0))

        box = pygame.Rect(150, 220, 500, 118)
        pygame.draw.rect(surf, BLACK, box)
        draw_box(surf, box, CYAN, 3)
        title = self.fonts["title"].render("SYSTEM BOOT", False, CYAN)
        surf.blit(title, (box.centerx - title.get_width() // 2, box.y + 18))
        sub = self.fonts["small"].render("PROTO-0 CONNECTED  //  ZERO HOSTILE SIGNAL DETECTED", False, GRAY)
        surf.blit(sub, (box.centerx - sub.get_width() // 2, box.y + 66))
        tip = self.fonts["small"].render("INSERT COIN... 아니고, 살아남아라.", False, YELLOW)
        surf.blit(tip, (box.centerx - tip.get_width() // 2, box.y + 88))

    def _draw_center_banner(self, surf: pygame.Surface, text: str, color) -> None:
        box = pygame.Rect(200, 260, 400, 76)
        pygame.draw.rect(surf, BLACK, box)
        draw_box(surf, box, color, 3)
        banner = self.fonts["title"].render(text, False, color)
        surf.blit(banner, (box.centerx - banner.get_width() // 2, box.y + 18))
        sub = self.fonts["small"].render("ENTER 또는 ESC 로 돌아가기", False, GRAY)
        surf.blit(sub, (box.centerx - sub.get_width() // 2, box.bottom - 24))