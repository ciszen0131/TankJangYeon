import pygame
from scenes.base import Scene
from core.constants import (
    SCENE_SETTINGS, SCENE_STORY, SCENE_GAME,
    BLACK, WHITE, YELLOW, GRAY, DGRAY, RED, CYAN, WIDTH, HEIGHT
)
from ui.draw import draw_box, draw_text_outline, draw_heart_selector

ITEMS = ["게임 시작", "설정", "스토리", "종료"]


class MainMenuScene(Scene):
    def __init__(self, screen, fonts, shared):
        super().__init__(screen, fonts, shared)
        self.selected = 0
        self.blink    = 0
        self.boot_scroll = 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(ITEMS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(ITEMS)
        elif event.key in (pygame.K_RETURN, pygame.K_z):
            self._confirm()

    def _confirm(self):
        choice = ITEMS[self.selected]
        if choice == "게임 시작":
            self.next_scene = SCENE_GAME
        elif choice == "설정":
            self.next_scene = SCENE_SETTINGS
        elif choice == "스토리":
            self.next_scene = SCENE_STORY
        elif choice == "종료":
            self.next_scene = "quit"

    def update(self, dt: int) -> None:
        self.blink += 1
        self.boot_scroll = (self.boot_scroll + 1) % 162

    def draw(self, surf: pygame.Surface) -> None:
        surf.fill((8, 8, 10))

        for y in range(0, HEIGHT, 24):
            pygame.draw.line(surf, (16, 16, 20), (0, y), (WIDTH, y), 1)

        log_font = self.fonts["small"]
        logs = [
            "SYSTEM BOOT...",
            "PROTO-0 CONNECTED",
            "ZERO HOSTILE SIGNAL DETECTED",
            "CORE STABILITY: MONITORING",
            "AUX POWER ROUTED TO SUIT",
            "REPAIR KIT BUS: READY",
            "TACTICAL LINK: NO RESPONSE",
            "DO NOT LOSE CORE STABILITY",
        ]
        for i, text in enumerate(logs):
            if (self.boot_scroll + i * 18) % 54 < 34:
                surf.blit(log_font.render(text, False, CYAN), (40, 150 + i * 18))

        # 메뉴 박스 또한 기존 170에서 260으로 화면 중앙 부근이 되게 내림
        # 화면 비율(중앙 정렬) 고려
        box_w, box_h = 360, 228
        menu_box = pygame.Rect(WIDTH // 2 - box_w // 2, 285, box_w, box_h)
        pygame.draw.rect(surf, BLACK, menu_box)
        draw_box(surf, menu_box, CYAN, 3)

        title = self.fonts["title"].render("SYSTEM BOOT", False, CYAN)
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, 178))
        sub = self.fonts["small"].render("PROTO-0 / FRONTLINE", False, GRAY)
        surf.blit(sub, (WIDTH // 2 - sub.get_width() // 2, 236))

        for i, item in enumerate(ITEMS):
            iy     = menu_box.y + 22 + i * 48
            is_sel = (i == self.selected)

            if is_sel:
                hl = pygame.Rect(menu_box.x + 4, iy - 6, menu_box.width - 8, 38)
                pygame.draw.rect(surf, DGRAY, hl)
                draw_heart_selector(surf, self.fonts["sub"],
                                    menu_box.x + 22, iy + 12)

            color = YELLOW if is_sel else WHITE
            draw_text_outline(surf, item, self.fonts["sub"],
                              menu_box.x + 50, iy, color=color)

        # 하단 조작 힌트 (겹침 방지로 위치를 더 아래로: 520)
        if self.blink % 60 < 40:
            hint = self.fonts["small"].render("↑↓ 이동   Z/ENTER 선택", False, GRAY)
            surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 540))

        # 버전
        ver = self.fonts["small"].render("v0.1.0  PROTOTYPE", False, GRAY)
        surf.blit(ver, (WIDTH - ver.get_width() - 20, HEIGHT - 24))
