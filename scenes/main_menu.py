import pygame
from scenes.base import Scene
from core.constants import (
    SCENE_SETTINGS, SCENE_STORY, SCENE_GAME,
    BLACK, WHITE, YELLOW, GRAY, DGRAY, RED, WIDTH, HEIGHT
)
from ui.draw import draw_box, draw_text_outline, draw_heart_selector

ITEMS = ["게임 시작", "설정", "스토리", "종료"]


class MainMenuScene(Scene):
    def __init__(self, screen, fonts, shared):
        super().__init__(screen, fonts, shared)
        self.selected = 0
        self.blink    = 0

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

    def draw(self, surf: pygame.Surface) -> None:
        menu_box = pygame.Rect(220, 175, 360, 220)
        pygame.draw.rect(surf, BLACK, menu_box)
        draw_box(surf, menu_box, WHITE, 3)

        for i, item in enumerate(ITEMS):
            iy     = menu_box.y + 18 + i * 48
            is_sel = (i == self.selected)

            if is_sel:
                hl = pygame.Rect(menu_box.x + 4, iy - 6, menu_box.width - 8, 38)
                pygame.draw.rect(surf, DGRAY, hl)
                draw_heart_selector(surf, self.fonts["sub"],
                                    menu_box.x + 22, iy + 12)

            color = YELLOW if is_sel else WHITE
            draw_text_outline(surf, item, self.fonts["sub"],
                              menu_box.x + 50, iy, color=color)

        # 하단 조작 힌트
        if self.blink % 60 < 40:
            hint = self.fonts["small"].render("↑↓ 이동   Z/ENTER 선택", False, GRAY)
            surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, 415))

        # 버전
        ver = self.fonts["small"].render("v0.1.0  PROTOTYPE", False, GRAY)
        surf.blit(ver, (WIDTH - ver.get_width() - 20, HEIGHT - 24))
