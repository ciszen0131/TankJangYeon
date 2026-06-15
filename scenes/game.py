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
    INTRO_LINES,
    INTRO_DURATION,
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
        self.boot_timer = INTRO_DURATION

        self.player_pos = pygame.Vector2(PLAYFIELD.centerx, PLAYFIELD.bottom - 56)
        self.player_speed = 280.0
        self.player_focus_speed = 170.0
        self.player_hit_radius = 7
        self.player_hp = 100
        self.player_hp_max = 100
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
        self.heavy_cast_timer = 0.0
        self.heavy_cast_shot_timer = 0.0
        self.heavy_safe_lane = pygame.Rect(0, 0, 0, 0)
        self.heavy_safe_zones: list[pygame.Rect] = []
        self.heavy_danger_zones: list[pygame.Rect] = []
        self.heavy_hit_applied = False
        self.heavy_reward_dropped = False
        self.stun_wave_cast_timer = 0.0
        self.center_flame_cast_timer = 0.0
        self.center_flame_safe_zones: list[pygame.Rect] = []
        self.center_flame_danger_zone = pygame.Rect(0, 0, 0, 0)
        self.center_flames: list[dict] = []
        self.center_flame_hit_applied = False
        self.boss_kill_cheat_down = False
        self.boss_kill_cheat_sequence = []
        self.boss_kill_cheat_timer = 0.0
        self.boss_side = -1

        self.player_bullets: list[dict] = []
        self.enemy_bullets: list[dict] = []
        self.field_walls: list[dict] = []
        self.heavy_lasers: list[dict] = []
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
            self.player_hp = min(self.player_hp_max, self.player_hp + 20)
        elif item["kind"] == "shield":
            self.player_invuln = 2.5
        elif item["kind"] == "bomb":
            self.enemy_bullets.clear()
            self.field_walls.clear()
            self.heavy_lasers.clear()
            self.center_flames.clear()
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

    def _spawn_enemy_bullet(
        self,
        angle: float,
        speed: float,
        color,
        radius: int = 5,
        origin=None,
        damage: int = 5,
    ) -> None:
        if origin is None:
            origin = pygame.Vector2(self.boss_pos.x, self.boss_pos.y + 30)
        self.enemy_bullets.append(
            {
                "pos": pygame.Vector2(origin.x, origin.y),
                "vel": pygame.Vector2(math.cos(angle) * speed, math.sin(angle) * speed),
                "radius": radius,
                "color": (255, 70, 70),
                "damage": damage,
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
        self.heavy_lasers.clear()
        self.heavy_safe_zones.clear()
        self.heavy_danger_zones.clear()
        self.heavy_hit_applied = False
        self.heavy_reward_dropped = False
        self.stun_wave_cast_timer = 0.0
        self.center_flame_cast_timer = 0.0
        self.center_flame_safe_zones.clear()
        self.center_flame_danger_zone = pygame.Rect(0, 0, 0, 0)
        self.center_flames.clear()
        self.center_flame_hit_applied = False
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
        speed_scale, _ = self._phase_scale()
        center_y = PLAYFIELD.centery + math.sin(self.attack_index * 0.8) * 54
        for step in range(7):
            offset_y = (step - 3) * 18
            y = max(PLAYFIELD.top + 30, min(PLAYFIELD.bottom - 30, center_y + offset_y))
            speed = (155 + step * 8) * speed_scale
            left_origin = pygame.Vector2(PLAYFIELD.left + 18, y)
            right_origin = pygame.Vector2(PLAYFIELD.right - 18, y)
            self._spawn_enemy_bullet(0.0, speed, (255, 90, 200), radius=5, origin=left_origin)
            self._spawn_enemy_bullet(math.pi, speed, (255, 90, 200), radius=5, origin=right_origin)

    def _start_heavy_survival_pattern(self) -> None:
        self.heavy_cast_timer = 2.0
        self.heavy_lasers.clear()
        self.field_walls.clear()
        self.enemy_bullets.clear()
        self.heavy_hit_applied = False
        self.heavy_reward_dropped = False

        safe_width = 96
        safe_x = PLAYFIELD.centerx - safe_width // 2
        self.heavy_safe_zones = [
            pygame.Rect(safe_x, PLAYFIELD.top + 8, safe_width, PLAYFIELD.height - 16),
        ]
        self.heavy_safe_lane = self.heavy_safe_zones[0]

        strip_width = 34
        left_start = PLAYFIELD.left + 26
        right_start = PLAYFIELD.right - 26 - strip_width
        self.heavy_danger_zones = [
            pygame.Rect(left_start, PLAYFIELD.top + 8, strip_width, PLAYFIELD.height - 16),
            pygame.Rect(left_start + 88, PLAYFIELD.top + 8, strip_width, PLAYFIELD.height - 16),
            pygame.Rect(right_start - 88, PLAYFIELD.top + 8, strip_width, PLAYFIELD.height - 16),
            pygame.Rect(right_start, PLAYFIELD.top + 8, strip_width, PLAYFIELD.height - 16),
        ]
        self.phase_banner_text = "HEAVY CAST / SURVIVE"
        self.phase_banner_timer = 1.2

    def _spawn_heavy_lasers(self) -> None:
        self.heavy_lasers.clear()
        if not self.heavy_danger_zones:
            return
        for rect in self.heavy_danger_zones:
            self.heavy_lasers.append(
                {
                    "rect": rect.copy(),
                    "life": 1.3,
                    "color": (255, 70, 70),
                    "damage": 30,
                    "boss_heal": int(self.boss_hp_max * 0.7),
                }
            )

    def _drop_shock_bomb_pickup(self) -> None:
        rect = pygame.Rect(0, 0, 28, 28)
        rect.center = (
            int(max(PLAYFIELD.left + 24, min(PLAYFIELD.right - 24, self.player_pos.x))),
            int(max(PLAYFIELD.top + 24, min(PLAYFIELD.bottom - 24, self.player_pos.y))),
        )
        self.pickups.append({"rect": rect, "kind": "bomb", "color": ORANGE})

    def _start_stun_flame_pattern(self) -> None:
        self.stun_wave_cast_timer = 2.0
        self.center_flame_cast_timer = 0.0
        self.center_flames.clear()
        self.center_flame_hit_applied = False
        self.heavy_lasers.clear()
        self.field_walls.clear()
        self.enemy_bullets.clear()

        side_width = 118
        self.center_flame_safe_zones = [
            pygame.Rect(PLAYFIELD.left + 8, PLAYFIELD.top + 8, side_width, PLAYFIELD.height - 16),
            pygame.Rect(PLAYFIELD.right - side_width - 8, PLAYFIELD.top + 8, side_width, PLAYFIELD.height - 16),
        ]
        self.center_flame_danger_zone = pygame.Rect(
            PLAYFIELD.left + side_width + 22,
            PLAYFIELD.top + 8,
            PLAYFIELD.width - (side_width + 22) * 2,
            PLAYFIELD.height - 16,
        )
        self.phase_banner_text = "STUN WAVE / CENTER FLAME"
        self.phase_banner_timer = 1.2

    def _spawn_center_flame(self) -> None:
        if self.center_flame_danger_zone.width <= 0:
            return
        self.center_flames = [
            {
                "rect": self.center_flame_danger_zone.copy(),
                "life": 1.2,
                "color": (255, 70, 35),
                "damage": 35,
            }
        ]

    def _spawn_grapple_shot(self) -> None:
        base = math.atan2(self.player_pos.y - self.boss_pos.y, self.player_pos.x - self.boss_pos.x)
        speed_scale, _ = self._phase_scale()
        for offset in (-0.05, 0.0, 0.05):
            self._spawn_enemy_bullet(base + offset, 175 * speed_scale, (160, 220, 255), radius=4)

    def _spawn_pattern(self) -> None:
        if self.phase_level == 0:
            pattern_count = 4
            pattern = self.phase_index % pattern_count
            if pattern == 0:
                self._spawn_aimed_fan()
            elif pattern == 1:
                self._spawn_ring()
            elif pattern == 2:
                self._spawn_stream()
            else:
                self._spawn_spray()
                self._spawn_side_pressure()
        elif self.phase_level == 1:
            pattern_count = 5
            pattern = self.phase_index % pattern_count
            if pattern == 0:
                self._spawn_aimed_fan()
            elif pattern == 1:
                self._spawn_ring()
            elif pattern == 2:
                self._spawn_stream()
            elif pattern == 3:
                self._spawn_spray()
                self._spawn_side_pressure()
            else:
                self._start_heavy_survival_pattern()
        else:
            pattern_count = 8
            pattern = self.phase_index % pattern_count
            if pattern == 0:
                self._spawn_aimed_fan()
            elif pattern == 1:
                self._spawn_ring()
            elif pattern == 2:
                self._spawn_stream()
                self._spawn_grapple_shot()
            elif pattern == 3:
                self._spawn_spiral()
                self._spawn_wall_squeeze()
            elif pattern == 4:
                self._spawn_cross()
                self._spawn_stun_field()
            elif pattern == 5:
                self._spawn_spray()
                self._spawn_side_pressure()
            elif pattern == 6:
                self._start_heavy_survival_pattern()
            else:
                self._start_stun_flame_pattern()
        self.attack_index += 1
        self.phase_index = (self.phase_index + 1) % pattern_count
        special_casting = (
            self.heavy_cast_timer > 0.0
            or self.stun_wave_cast_timer > 0.0
            or self.center_flame_cast_timer > 0.0
        )
        if not special_casting:
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

        had_heavy_lasers = bool(self.heavy_lasers)
        new_lasers: list[dict] = []
        for laser in self.heavy_lasers:
            laser["life"] -= dt_sec
            if laser["life"] > 0:
                new_lasers.append(laser)
        self.heavy_lasers = new_lasers
        if had_heavy_lasers and not self.heavy_lasers and not self.heavy_hit_applied and not self.heavy_reward_dropped:
            self._drop_shock_bomb_pickup()
            self.heavy_reward_dropped = True
            self.phase_banner_text = "DODGE BONUS / SHOCK BOMB"
            self.phase_banner_timer = 1.0

        new_flames: list[dict] = []
        for flame in self.center_flames:
            flame["life"] -= dt_sec
            if flame["life"] > 0:
                new_flames.append(flame)
        self.center_flames = new_flames

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

    def _trigger_boss_kill_cheat(self) -> None:
        self.boss_hp = 0
        self.phase_banner_text = "DEBUG / BOSS HP ZERO"
        self.phase_banner_timer = 0.8

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        controls = self.controls
        cheat_keys = (pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t, pygame.K_y)

        if event.key in cheat_keys:
            expected_key = cheat_keys[len(self.boss_kill_cheat_sequence)]
            if event.key == expected_key:
                self.boss_kill_cheat_sequence.append(event.key)
            else:
                self.boss_kill_cheat_sequence = [event.key] if event.key == cheat_keys[0] else []
            self.boss_kill_cheat_timer = 1.4
            if len(self.boss_kill_cheat_sequence) == len(cheat_keys):
                self._trigger_boss_kill_cheat()
                self.boss_kill_cheat_sequence.clear()

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
        if self.boss_kill_cheat_timer > 0.0:
            self.boss_kill_cheat_timer = max(0.0, self.boss_kill_cheat_timer - dt_sec)
            if self.boss_kill_cheat_timer == 0.0:
                self.boss_kill_cheat_sequence.clear()

        if self.result is not None:
            return

        if self.boot_timer > 0.0:
            self.boot_timer = max(0.0, self.boot_timer - dt_sec)

        self.controls = get_controls(self.shared)
        pressed = pygame.key.get_pressed()
        focus = pressed[pygame.K_LSHIFT] or pressed[pygame.K_RSHIFT]
        boss_kill_cheat_down = all(
            pressed[key]
            for key in (pygame.K_q, pygame.K_w, pygame.K_e, pygame.K_r, pygame.K_t, pygame.K_y)
        )
        if boss_kill_cheat_down and not self.boss_kill_cheat_down:
            self._trigger_boss_kill_cheat()
        self.boss_kill_cheat_down = boss_kill_cheat_down

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

        if self.heavy_cast_timer > 0.0:
            self.heavy_cast_timer = max(0.0, self.heavy_cast_timer - dt_sec)
            if self.heavy_cast_timer == 0.0:
                self._spawn_heavy_lasers()

        if self.stun_wave_cast_timer > 0.0:
            self.stun_wave_cast_timer = max(0.0, self.stun_wave_cast_timer - dt_sec)
            if self.stun_wave_cast_timer == 0.0:
                self.stun_timer = max(self.stun_timer, 1.25)
                self.control_lock = max(self.control_lock, 1.25)
                self.center_flame_cast_timer = 0.65
                self.phase_banner_text = "CENTER FLAME / SIDE SAFE"
                self.phase_banner_timer = 1.0

        if self.center_flame_cast_timer > 0.0:
            self.center_flame_cast_timer = max(0.0, self.center_flame_cast_timer - dt_sec)
            if self.center_flame_cast_timer == 0.0:
                self._spawn_center_flame()

        heavy_active = self.heavy_cast_timer > 0.0 or bool(self.heavy_lasers)
        stun_flame_active = (
            self.stun_wave_cast_timer > 0.0
            or self.center_flame_cast_timer > 0.0
            or bool(self.center_flames)
        )
        special_active = heavy_active or stun_flame_active
        if self.boot_timer <= 0.0 and not special_active:
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

        if self.grapple_hit_flash > 0.0 and not special_active:
            self.grapple_hit_flash = max(0.0, self.grapple_hit_flash - dt_sec)
            if self.grapple_hit_flash > 0.0 and random.random() < 0.08:
                self.enemy_bullets.append(
                    {
                        "pos": pygame.Vector2(self.player_pos.x, self.player_pos.y),
                        "vel": pygame.Vector2(random.uniform(-40, 40), random.uniform(-40, 40)),
                        "radius": 2,
                        "color": (255, 70, 70),
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
                    self.player_hp -= bullet.get("damage", 5)
                    self.player_invuln = 1.2
                    bullet["pos"].x = -9999
                    break

        if self.phase_level % 2 == 1 and self.player_invuln <= 0.0:
            for wall in self.field_walls:
                if wall["rect"].collidepoint(player_hit.x, player_hit.y):
                    self.player_hp -= 5
                    self.player_invuln = 1.0
                    self.knockback_velocity = pygame.Vector2(220 if wall["vx"] < 0 else -220, 0)
                    break

        if self.player_invuln <= 0.0 and not self.heavy_hit_applied:
            for laser in self.heavy_lasers:
                if laser["rect"].collidepoint(player_hit.x, player_hit.y):
                    self.player_hp -= laser.get("damage", self.player_hp_max // 2)
                    self.boss_hp = min(self.boss_hp_max, self.boss_hp + laser.get("boss_heal", int(self.boss_hp_max * 0.7)))
                    self.heavy_hit_applied = True
                    self.player_invuln = 1.2
                    break

        if self.player_invuln <= 0.0 and not self.center_flame_hit_applied:
            for flame in self.center_flames:
                if flame["rect"].collidepoint(player_hit.x, player_hit.y):
                    self.player_hp -= flame.get("damage", 35)
                    self.center_flame_hit_applied = True
                    self.player_invuln = 1.2
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

        if self.stun_wave_cast_timer > 0.0:
            stun_overlay = pygame.Surface((PLAYFIELD.width, PLAYFIELD.height), pygame.SRCALPHA)
            stun_overlay.fill((70, 125, 255, 95))
            surf.blit(stun_overlay, PLAYFIELD.topleft)
            draw_box(surf, PLAYFIELD.inflate(-12, -12), CYAN, 3)
            cast_text = self.fonts["small"].render("STUN WAVE 2.0s - NO DAMAGE", False, WHITE)
            surf.blit(cast_text, (PLAYFIELD.left + 14, PLAYFIELD.top + 10))

        if self.center_flame_cast_timer > 0.0:
            cast_overlay = pygame.Surface((PLAYFIELD.width, PLAYFIELD.height), pygame.SRCALPHA)
            cast_overlay.fill((20, 20, 28, 40))
            surf.blit(cast_overlay, PLAYFIELD.topleft)
            if self.center_flame_danger_zone.width > 0:
                danger_overlay = pygame.Surface(
                    (self.center_flame_danger_zone.width, self.center_flame_danger_zone.height),
                    pygame.SRCALPHA,
                )
                danger_overlay.fill((255, 40, 40, 105))
                surf.blit(danger_overlay, self.center_flame_danger_zone.topleft)
                draw_box(surf, self.center_flame_danger_zone, RED, 2)
            for safe_zone in self.center_flame_safe_zones:
                safe_overlay = pygame.Surface((safe_zone.width, safe_zone.height), pygame.SRCALPHA)
                safe_overlay.fill((70, 125, 255, 125))
                surf.blit(safe_overlay, safe_zone.topleft)
                draw_box(surf, safe_zone, CYAN, 2)
            cast_text = self.fonts["small"].render("CENTER FLAME - BLUE SIDES SAFE", False, WHITE)
            surf.blit(cast_text, (PLAYFIELD.left + 14, PLAYFIELD.top + 10))

        if self.heavy_cast_timer > 0.0:
            cast_overlay = pygame.Surface((PLAYFIELD.width, PLAYFIELD.height), pygame.SRCALPHA)
            cast_overlay.fill((20, 20, 28, 40))
            surf.blit(cast_overlay, PLAYFIELD.topleft)
            cast_progress = 1.0 - self.heavy_cast_timer / 2.0
            pressure_width = int(34 + cast_progress * 82)
            left_pressure = pygame.Rect(PLAYFIELD.left + 8, PLAYFIELD.top + 8, pressure_width, PLAYFIELD.height - 16)
            right_pressure = pygame.Rect(PLAYFIELD.right - 8 - pressure_width, PLAYFIELD.top + 8, pressure_width, PLAYFIELD.height - 16)
            for pressure_zone in (left_pressure, right_pressure):
                pressure_overlay = pygame.Surface((pressure_zone.width, pressure_zone.height), pygame.SRCALPHA)
                pressure_overlay.fill((255, 35, 35, 55))
                surf.blit(pressure_overlay, pressure_zone.topleft)
                draw_box(surf, pressure_zone, RED, 1)
            for danger_zone in self.heavy_danger_zones:
                danger_overlay = pygame.Surface((danger_zone.width, danger_zone.height), pygame.SRCALPHA)
                danger_overlay.fill((255, 40, 40, 95))
                surf.blit(danger_overlay, danger_zone.topleft)
                draw_box(surf, danger_zone, RED, 2)
            for safe_zone in self.heavy_safe_zones:
                safe_overlay = pygame.Surface((safe_zone.width, safe_zone.height), pygame.SRCALPHA)
                safe_overlay.fill((70, 125, 255, 125))
                surf.blit(safe_overlay, safe_zone.topleft)
                draw_box(surf, safe_zone, CYAN, 2)
            cast_text = self.fonts["small"].render("HEAVY CAST 2.0s - BLUE SAFE ZONES", False, WHITE)
            surf.blit(cast_text, (PLAYFIELD.left + 14, PLAYFIELD.top + 10))

        for laser in self.heavy_lasers:
            pygame.draw.rect(surf, laser["color"], laser["rect"])
            draw_box(surf, laser["rect"], WHITE, 2)

        for flame in self.center_flames:
            pygame.draw.rect(surf, flame["color"], flame["rect"])
            draw_box(surf, flame["rect"], WHITE, 2)

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
        glow_color = PLAYER_COLORS["glow"] # 민트색
        armor_color = (45, 45, 50)
        accent_color = (80, 80, 85)
        
        centerx, centery = self.boss_rect.centerx, self.boss_rect.centery

        # 후면 케이블 실루엣 (작살 케이블 잔해)
        for idx in range(3):
            angle = self.boss_move_timer * 2 + idx * (math.pi * 0.6)
            offset_x = math.cos(angle) * 35
            offset_y = math.sin(angle) * 20
            pygame.draw.line(surf, (30, 30, 30), (centerx, centery), (centerx + offset_x, centery - 20 + offset_y), 4)

        # 1. 메인 섀시 (조금 더 각진 다각형 구조)
        main_poly = [
            (centerx - 30, centery - 35),
            (centerx + 30, centery - 35),
            (centerx + 40, centery),
            (centerx + 35, centery + 35),
            (centerx - 35, centery + 35),
            (centerx - 40, centery)
        ]
        pygame.draw.polygon(surf, armor_color, main_poly)
        pygame.draw.polygon(surf, accent_color, main_poly, 3)
        
        # 2. ZERO의 광학 바이저 (크게 가로지르는 형태)
        visor_rect = pygame.Rect(centerx - 28, centery - 15, 56, 12)
        pygame.draw.rect(surf, (15, 15, 15), visor_rect, border_radius=4)
        
        # 바이저 발광 효과 (맥박치듯)
        glow_width = int(50 + math.sin(self.boss_move_timer * 5) * 4)
        glow_rect = pygame.Rect(0, 0, glow_width, 8)
        glow_rect.center = visor_rect.center
        pygame.draw.rect(surf, glow_color, glow_rect, border_radius=2)
        
        # 3. 송전탑 파츠 (상부)
        pygame.draw.polygon(surf, (60, 60, 70), [
            (centerx - 12, centery - 35),
            (centerx + 12, centery - 35),
            (centerx, centery - 55)
        ])
        if int(self.boss_move_timer * 10) % 3 == 0:
            # 방전 이펙트
            pygame.draw.circle(surf, (200, 255, 255), (centerx, centery - 55), 5)
            pygame.draw.line(surf, (150, 255, 255), (centerx, centery - 55), (centerx - 8, centery - 65), 2)
            pygame.draw.line(surf, (150, 255, 255), (centerx, centery - 55), (centerx + 6, centery - 60), 2)

        # 4. 치료 코어 및 포대 잔해 (좌/우 어깨)
        # 좌측: 치료 코어 파이프 느낌
        pygame.draw.rect(surf, (30, 70, 50), (centerx - 45, centery - 5, 15, 25), border_radius=3)
        pygame.draw.circle(surf, (90, 255, 120), (centerx - 37, centery + 5), 4)

        # 우측: 중화기 포대 장갑
        pygame.draw.rect(surf, (70, 30, 30), (centerx + 30, centery - 10, 20, 30), border_radius=4)
        pygame.draw.rect(surf, DGRAY, (centerx + 50, centery + 5, 14, 6))

        # 이름표
        label = self.fonts["small"].render("ZERO", False, glow_color)
        surf.blit(label, (centerx - label.get_width() // 2, centery - 75))

        # 체력 바
        hp_ratio = self.boss_hp / max(1, self.boss_hp_max)
        hp_bar = pygame.Rect(PLAYFIELD.left + 90, PLAYFIELD.top + 18, PLAYFIELD.width - 180, 8)
        pygame.draw.rect(surf, DGRAY, hp_bar)
        pygame.draw.rect(surf, RED, (hp_bar.x, hp_bar.y, int(hp_bar.width * hp_ratio), hp_bar.height))
        pygame.draw.rect(surf, WHITE, hp_bar, 1)

    def _draw_player(self, surf: pygame.Surface) -> None:
        invuln_flash = self.player_invuln > 0 and (self.blink // 4) % 2 == 0
        suit_base = (200, 220, 255) if invuln_flash else (130, 95, 45)  # 낡고 큰 정비복
        suit_shadow = (100, 70, 30)
        armor_color = (255, 255, 255) if invuln_flash else (85, 95, 105) # 장갑
        glow_color = (255, 255, 255) if invuln_flash else PLAYER_COLORS["glow"]

        centerx, centery = int(self.player_pos.x), int(self.player_pos.y)
        
        # 1. 헐렁한 정비복 (바디) + 약간의 애니메이션(호흡)
        breath = math.sin(self.boss_move_timer * 8) * 1.5
        suit_rect = pygame.Rect(0, 0, 32, 36)
        suit_rect.center = (centerx, centery + 4 + int(breath))
        
        # 옷 주름과 명암 표현
        pygame.draw.rect(surf, suit_shadow, (suit_rect.x, suit_rect.y + 4, suit_rect.width, suit_rect.height), border_radius=8)
        pygame.draw.rect(surf, suit_base, suit_rect, border_radius=8)

        # 2. 미완성 수호 슈트 흉갑 (Chest Armor)
        chest_points = [
            (centerx - 14, centery - 8),
            (centerx + 14, centery - 8),
            (centerx + 8, centery + 4),
            (centerx - 8, centery + 4)
        ]
        pygame.draw.polygon(surf, armor_color, chest_points)
        pygame.draw.polygon(surf, PLAYER_COLORS["trim"], chest_points, 2)
        
        # 흉갑 정중앙의 민트색 동력 코어
        pygame.draw.circle(surf, glow_color, (centerx, centery - 2), 5)
        pygame.draw.circle(surf, WHITE, (centerx, centery - 2), 2) # 코어 하이라이트

        # 3. 반쯤 깨진 헬멧
        helmet_rect = pygame.Rect(0, 0, 28, 26)
        helmet_rect.midbottom = (centerx, centery - 6)
        pygame.draw.rect(surf, (40, 40, 45), helmet_rect, border_radius=10)
        
        # 바이저 백그라운드
        dark_visor = pygame.Rect(0, 0, 20, 10)
        dark_visor.center = (centerx, helmet_rect.centery + 2)
        pygame.draw.rect(surf, (10, 10, 10), dark_visor)
        
        # 반파된 광학 바이저 (지그재그 패턴)
        broken_points = [
            (dark_visor.left, dark_visor.top),
            (dark_visor.left + 12, dark_visor.top),
            (dark_visor.left + 8, dark_visor.centery),
            (dark_visor.left + 14, dark_visor.bottom),
            (dark_visor.left, dark_visor.bottom)
        ]
        pygame.draw.polygon(surf, glow_color, broken_points)
        pygame.draw.polygon(surf, (150, 255, 230), broken_points, 1) # 테두리 하이라이트

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

        hp_bar = pygame.Rect(ui_box.x + 90, ui_box.y + 12, 150, 14)
        pygame.draw.rect(surf, DGRAY, hp_bar)
        draw_box(surf, hp_bar, WHITE, 1)
        hp_ratio = max(0.0, min(1.0, self.player_hp / max(1, self.player_hp_max)))
        pygame.draw.rect(surf, RED, (hp_bar.x, hp_bar.y, int(hp_bar.width * hp_ratio), hp_bar.height))
        hp_text = self.fonts["small"].render(f"{max(0, int(self.player_hp))} / {self.player_hp_max}", False, WHITE)
        surf.blit(hp_text, (hp_bar.right + 8, ui_box.y + 10))

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

        # 상수 리스트(INTRO_LINES)의 내용 수에 맞춰 박스 높이 계산
        box_h = 60 + len(INTRO_LINES) * 24
        box = pygame.Rect(WIDTH // 2 - 250, HEIGHT // 2 - box_h // 2, 500, box_h)
        pygame.draw.rect(surf, BLACK, box)
        draw_box(surf, box, CYAN, 3)
        
        title = self.fonts["title"].render("OPERATION START", False, CYAN)
        surf.blit(title, (box.centerx - title.get_width() // 2, box.y + 18))
        
        # 인트로 텍스트 그리기
        for i, line in enumerate(INTRO_LINES):
            text_surf = self.fonts["small"].render(line, False, GRAY)
            surf.blit(text_surf, (box.centerx - text_surf.get_width() // 2, box.y + 60 + i * 24))

    def _draw_center_banner(self, surf: pygame.Surface, text: str, color) -> None:
        box = pygame.Rect(200, 260, 400, 76)
        pygame.draw.rect(surf, BLACK, box)
        draw_box(surf, box, color, 3)
        banner = self.fonts["title"].render(text, False, color)
        surf.blit(banner, (box.centerx - banner.get_width() // 2, box.y + 18))
        sub = self.fonts["small"].render("ENTER 또는 ESC 로 돌아가기", False, GRAY)
        surf.blit(sub, (box.centerx - sub.get_width() // 2, box.bottom - 24))
