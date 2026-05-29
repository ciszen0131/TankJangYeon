import pygame
from scenes.base import Scene
from core.constants import SCENE_MAIN, BLACK, WHITE, YELLOW, GRAY, CYAN, WIDTH
from ui.draw import draw_box

STORY_LINES = [
    "20XX년. 도심 한복판에",
    "탱크들이 모여들었다.",
    "",
    "그들은 스스로를 '탱장연'이라 불렀다.",
    "거대한 철갑 위에 올라선 자들과",
    "그것을 막으려는 하나의 방패.",
    "",
    "싸움이 시작된다.",
    "",
    "[ ENTER 또는 ESC 로 돌아가기 ]",
]
VISIBLE_LINES = 9


class StoryScene(Scene):
    def __init__(self, screen, fonts, shared):
        super().__init__(screen, fonts, shared)
        self.scroll = 0
        self.blink  = 0

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_z):
            self.next_scene = SCENE_MAIN
        elif event.key == pygame.K_DOWN:
            self.scroll = min(self.scroll + 1,
                              max(0, len(STORY_LINES) - VISIBLE_LINES))
        elif event.key == pygame.K_UP:
            self.scroll = max(0, self.scroll - 1)

    def update(self, dt: int) -> None:
        self.blink += 1

    def draw(self, surf: pygame.Surface) -> None:
        box = pygame.Rect(100, 160, 600, 310)
        pygame.draw.rect(surf, BLACK, box)
        draw_box(surf, box, WHITE, 3)

        # 타이틀
        t = self.fonts["sub"].render("[ 배  경 ]", False, CYAN)
        surf.blit(t, (WIDTH // 2 - t.get_width() // 2, box.y + 10))

        # 구분선
        pygame.draw.line(surf, WHITE,
                         (box.x + 16,    box.y + 40),
                         (box.right - 16, box.y + 40), 2)

        # 텍스트
        visible = STORY_LINES[self.scroll: self.scroll + VISIBLE_LINES]
        for li, line in enumerate(visible):
            ty    = box.y + 52 + li * 26
            color = WHITE
            if "ENTER" in line or "ESC" in line:
                color = YELLOW if self.blink % 60 < 40 else GRAY
            t_surf = self.fonts["body"].render(line, False, color)
            surf.blit(t_surf, (box.x + 24, ty))

        hint = self.fonts["small"].render("ESC 또는 ENTER 로 돌아가기", False, GRAY)
        surf.blit(hint, (WIDTH // 2 - hint.get_width() // 2, box.bottom + 12))
