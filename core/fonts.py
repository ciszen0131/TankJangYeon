import os
import pygame

KR_FONT_PATHS = [
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",   # macOS
    "C:/Windows/Fonts/malgun.ttf",                   # Windows
    "C:/Windows/Fonts/gulim.ttc",
]

def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """한글 지원 폰트를 우선순위 순으로 탐색해 반환."""
    for path in KR_FONT_PATHS:
        try:
            if os.path.exists(path):
                return pygame.font.Font(path, size)
        except Exception:
            pass
    for name in ["malgungothic", "nanumgothic", "notosanscjkkr"]:
        try:
            return pygame.font.SysFont(name, size, bold=bold)
        except Exception:
            pass
    return pygame.font.Font(None, size)


# 전역 폰트 인스턴스 (pygame.init() 이후에 import 할 것)
def init_fonts():
    """폰트 객체 딕셔너리를 생성해 반환."""
    return {
        "title": load_font(52, bold=True),
        "sub":   load_font(22, bold=True),
        "body":  load_font(16),
        "small": load_font(13),
    }
