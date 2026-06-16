import pygame

from scenes.base import Scene
from core.constants import SCENE_MAIN, BLACK, WHITE, YELLOW, GRAY, DGRAY, CYAN, WIDTH
from ui.draw import draw_box, draw_heart_selector


SECTIONS = [
    {
        "title": "세계관",
        "accent": CYAN,
        "lines": [
            "산업도시 강철구의 지하에는 오래된 자동 방어 시스템이 잠들어 있었다.",
            "그 이름은 수호자 ZERO.",
            "",
            "본래 도시를 지키기 위해 만들어졌지만, 정체불명의 침입 이후 ZERO는 도시 전체를 침입 구역으로 판정하기 시작한다.",
            "",
            "견습 정비공 PROTO-0은 미완성 수호 슈트를 걸친 채 중앙 통제실로 내려가 ZERO를 직접 정지시키려 한다.",
        ],
    },
    {
        "title": "PROTO-0",
        "accent": (80, 255, 210),
        "lines": [
            "너무 큰 정비복 위에 미완성 수호 슈트를 임시로 끼워 입은 견습생.",
            "반쯤 깨진 바이저와 민트색 코어가 유일하게 살아 있는 신호다.",
            "",
            "ZERO의 공격을 회피하며, 가지고 있는 레이저 블레스터로 ZERO를 멈추기 위해 움직인다.",
            "",
        ],
    },
    {
        "title": "수호자 ZERO",
        "accent": (255, 120, 230),
        "lines": [
            "다섯 모듈의 설정을 한 몸에 압축한 통합 운영 인격.",
            "송전탑 무기, 포대, 작살 케이블, 치료 코어의 잔해가 하나의 거대한 기계 몸체에 붙어 있다.",
            "",
            "ZERO의 바이저는 PROTO-0과 같은 민트색으로 빛난다.",
            "둘은 같은 설계 계통에서 만들어진 형제 모델이라는 암시다.",
            "",
            "하지만 ZERO는 더 이상 사람을 구분하지 못한다.",
            "도시를 지키기 위해, 도시를 멈추려 한다.",
        ],
    },
]

VISIBLE_LINES = 10
BODY_PADDING_X = 18


def wrap_text(font: pygame.font.Font, text: str, max_width: int) -> list[str]:
    if not text:
        return [""]

    wrapped: list[str] = []
    current = ""

    for char in text:
        test = current + char
        if current and font.size(test)[0] > max_width:
            wrapped.append(current.rstrip())
            current = char.lstrip()
        else:
            current = test

    if current:
        wrapped.append(current.rstrip())

    return wrapped


class StoryScene(Scene):
    def __init__(self, screen, fonts, shared):
        super().__init__(screen, fonts, shared)
        self.selected = 0
        self.scroll = 0
        self.blink = 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_z):
            self.next_scene = SCENE_MAIN
        elif event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(SECTIONS)
            self.scroll = 0
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(SECTIONS)
            self.scroll = 0
        elif event.key in (pygame.K_LEFT, pygame.K_a):
            self.scroll = max(0, self.scroll - 1)
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.scroll = min(self.max_scroll, self.scroll + 1)

    @property
    def current_section(self) -> dict:
        return SECTIONS[self.selected]

    @property
    def max_scroll(self) -> int:
        return max(0, len(self._wrapped_lines()) - VISIBLE_LINES)

    def _wrapped_lines(self) -> list[str]:
        max_width = 430 - BODY_PADDING_X * 2
        lines: list[str] = []
        for line in self.current_section["lines"]:
            lines.extend(wrap_text(self.fonts["small"], line, max_width))
        return lines

    def update(self, dt: int) -> None:
        self.blink += 1

    def draw(self, surf: pygame.Surface) -> None:
        box = pygame.Rect(70, 155, 660, 345)
        pygame.draw.rect(surf, BLACK, box)
        draw_box(surf, box, WHITE, 3)

        title = self.fonts["sub"].render("[ STORY ARCHIVE ]", False, CYAN)
        surf.blit(title, (WIDTH // 2 - title.get_width() // 2, box.y + 12))
        pygame.draw.line(surf, WHITE, (box.x + 16, box.y + 44), (box.right - 16, box.y + 44), 2)

        nav_rect = pygame.Rect(box.x + 18, box.y + 62, 160, 230)
        body_rect = pygame.Rect(box.x + 200, box.y + 62, 430, 230)
        pygame.draw.rect(surf, DGRAY, nav_rect)
        pygame.draw.rect(surf, BLACK, body_rect)
        draw_box(surf, nav_rect, GRAY, 2)
        draw_box(surf, body_rect, GRAY, 2)

        self._draw_nav(surf, nav_rect)
        self._draw_body(surf, body_rect)

        if self.blink % 60 < 42:
            hint = self.fonts["small"].render("UP/DOWN 항목  LEFT/RIGHT 스크롤  ENTER/ESC 돌아가기", False, GRAY)
            hint_x = max(20, WIDTH // 2 - hint.get_width() // 2)
            surf.blit(hint, (hint_x, box.bottom + 12))

    def _draw_nav(self, surf: pygame.Surface, rect: pygame.Rect) -> None:
        for i, section in enumerate(SECTIONS):
            y = rect.y + 18 + i * 44
            is_selected = i == self.selected
            color = YELLOW if is_selected else WHITE

            if is_selected:
                pygame.draw.rect(surf, BLACK, (rect.x + 4, y - 7, rect.width - 8, 32))
                draw_heart_selector(surf, self.fonts["body"], rect.x + 20, y + 8)

            label = self.fonts["body"].render(section["title"], False, color)
            surf.blit(label, (rect.x + 40, y))

    def _draw_body(self, surf: pygame.Surface, rect: pygame.Rect) -> None:
        section = self.current_section
        accent = section["accent"]

        header = self.fonts["sub"].render(section["title"], False, accent)
        surf.blit(header, (rect.x + BODY_PADDING_X, rect.y + 12))
        pygame.draw.line(
            surf,
            accent,
            (rect.x + BODY_PADDING_X, rect.y + 42),
            (rect.right - BODY_PADDING_X, rect.y + 42),
            2,
        )

        wrapped = self._wrapped_lines()
        visible = wrapped[self.scroll:self.scroll + VISIBLE_LINES]
        for li, line in enumerate(visible):
            y = rect.y + 56 + li * 18
            color = GRAY if not line else WHITE
            text = self.fonts["small"].render(line, False, color)
            surf.blit(text, (rect.x + BODY_PADDING_X, y))

        if self.max_scroll > 0:
            marker = f"{self.scroll + 1}/{self.max_scroll + 1}"
            page = self.fonts["small"].render(marker, False, GRAY)
            surf.blit(page, (rect.right - page.get_width() - 14, rect.bottom - 20))
