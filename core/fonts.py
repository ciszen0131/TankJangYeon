import os
import pygame

# fontconfig 가 인식하는 한글 폰트 패밀리 (배포판/OS 무관하게 실제 설치 위치를 찾아줌)
KR_FONT_FAMILIES = "Noto Sans CJK KR,Noto Sans KR,NanumGothic,Nanum Gothic,Malgun Gothic,AppleGothic,Apple SD Gothic Neo"

# fontconfig 로 못 찾을 때를 대비한 직접 경로 후보 (Arch / Debian / macOS / Windows)
KR_FONT_PATHS = [
    # Arch Linux (noto-fonts-cjk / ttf-nanum)
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansKR-Bold.otf",
    "/usr/share/fonts/noto-cjk/NotoSansKR-Regular.otf",
    "/usr/share/fonts/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/nanum/NanumGothic.ttf",
    # Debian / Ubuntu
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    # macOS
    "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    # Windows
    "C:/Windows/Fonts/malgun.ttf",
    "C:/Windows/Fonts/gulim.ttc",
]


def load_font(size: int, bold: bool = False) -> pygame.font.Font:
    """한글 지원 폰트를 fontconfig -> 직접 경로 -> SysFont 순으로 탐색해 반환."""
    # 1) fontconfig 로 실제 설치 경로 조회 (Arch 포함 모든 리눅스에서 가장 확실)
    try:
        matched = pygame.font.match_font(KR_FONT_FAMILIES, bold=bold)
        if matched:
            return pygame.font.Font(matched, size)
    except Exception:
        pass

    # 2) 알려진 절대 경로 후보
    for path in KR_FONT_PATHS:
        try:
            if os.path.exists(path):
                return pygame.font.Font(path, size)
        except Exception:
            pass

    # 3) 이름 기반 SysFont (쉼표로 여러 후보를 한 번에 시도)
    try:
        sysfont = pygame.font.SysFont(KR_FONT_FAMILIES, size, bold=bold)
        if sysfont is not None:
            return sysfont
    except Exception:
        pass

    # 4) 최후의 폴백 (한글 미지원 - 깨져 보일 수 있음)
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