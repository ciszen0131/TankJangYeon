import pygame
from core.constants import WHITE, BLACK, YELLOW, GRAY, DGRAY, RED, CYAN, WIDTH, HEIGHT


def draw_box(surf: pygame.Surface, rect: pygame.Rect,
             color=WHITE, thickness: int = 3) -> None:
    """언더테일 스타일 테두리 박스."""
    pygame.draw.rect(surf, color, rect, thickness)


def draw_text_outline(surf: pygame.Surface, text: str,
                      font: pygame.font.Font,
                      x: int, y: int,
                      color=WHITE, outline=BLACK,
                      cx: bool = False) -> None:
    """외곽선 포함 텍스트 렌더링. cx=True 이면 x 기준 가운데 정렬."""
    render   = font.render(text, False, color)
    outline_r = font.render(text, False, outline)
    if cx:
        x = x - render.get_width() // 2
    for dx in (-2, 2):
        for dy in (-2, 2):
            surf.blit(outline_r, (x + dx, y + dy))
    surf.blit(render, (x, y))


def draw_volume_bar(surf: pygame.Surface, fonts: dict,
                    x: int, y: int, w: int, h: int,
                    value: int, max_val: int = 10,
                    active: bool = False) -> None:
    """볼륨 게이지 바."""
    color = YELLOW if active else GRAY
    pygame.draw.rect(surf, DGRAY, (x, y, w, h))
    fill = int(w * value / max_val)
    pygame.draw.rect(surf, color, (x, y, fill, h))
    pygame.draw.rect(surf, WHITE, (x, y, w, h), 2)
    val_surf = fonts["body"].render(str(value), False, WHITE)
    surf.blit(val_surf, (x + w + 8, y))


def draw_heart_selector(surf: pygame.Surface, font: pygame.font.Font,
                        x: int, y: int) -> None:
    """♥ 셀렉터 아이콘."""
    heart = font.render("♥", False, RED)
    surf.blit(heart, (x - heart.get_width() // 2, y - heart.get_height() // 2))


def draw_title_bar(surf: pygame.Surface, fonts: dict,
                   blink_timer: int = 0) -> None:
    """모든 화면 공통 상단 타이틀 박스."""
    from core.constants import DIM
    title_box = pygame.Rect(60, 30, WIDTH - 120, 110)
    pygame.draw.rect(surf, BLACK, title_box)
    draw_box(surf, title_box, WHITE, 3)

    # 점선 장식
    for dx in range(8, title_box.width - 8, 12):
        pygame.draw.rect(surf, (30, 30, 30), (title_box.x + dx, title_box.y + 4, 6, 3))
        pygame.draw.rect(surf, (30, 30, 30), (title_box.x + dx, title_box.bottom - 7, 6, 3))

    draw_text_outline(surf, "FRONTLINE", fonts["title"], WIDTH // 2, 45, cx=True)
    draw_text_outline(surf, "탱 장 연",    fonts["sub"],   WIDTH // 2, 95, color=YELLOW, cx=True)


def draw_background(surf: pygame.Surface, scanline_surf: pygame.Surface) -> None:
    """그리드 + 스캔라인 배경."""
    from core.constants import DIM
    surf.fill(DIM)
    grid_color = (20, 20, 30)
    for gx in range(0, WIDTH, 32):
        pygame.draw.line(surf, grid_color, (gx, 0), (gx, HEIGHT))
    for gy in range(0, HEIGHT, 32):
        pygame.draw.line(surf, grid_color, (0, gy), (WIDTH, gy))
    surf.blit(scanline_surf, (0, 0))


def draw_corners(surf: pygame.Surface) -> None:
    """코너 픽셀 장식 + 상하 마킹 라인."""
    size = 12
    for cx, cy in [(0, 0), (WIDTH - size, 0),
                   (0, HEIGHT - size), (WIDTH - size, HEIGHT - size)]:
        pygame.draw.rect(surf, WHITE, (cx, cy, size, size))
        pygame.draw.rect(surf, BLACK, (cx + 2, cy + 2, size - 4, size - 4))
    pygame.draw.line(surf, GRAY, (size, 3),          (WIDTH - size, 3),          1)
    pygame.draw.line(surf, GRAY, (size, HEIGHT - 4), (WIDTH - size, HEIGHT - 4), 1)
