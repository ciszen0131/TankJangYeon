import sys
import pygame

from core.constants import WIDTH, HEIGHT, SCENE_MAIN, SCENE_SETTINGS, SCENE_STORY, SCENE_GAME
from core.fonts     import init_fonts
from ui.particles   import ParticleSystem, make_scanline_surf
from ui.draw        import draw_background, draw_title_bar, draw_corners

from scenes.main_menu import MainMenuScene
from scenes.settings  import SettingsScene
from scenes.story     import StoryScene
from scenes.game      import GameScene

# ── pygame 초기화 ────────────────────────────────
pygame.init()
pygame.mixer.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("탱장연 - FRONTLINE")
clock = pygame.time.Clock()

fonts   = init_fonts()
shared  = {}   # 씬 간 공유 상태 (볼륨 등)

# ── BGM 재생 함수 ───────────────────────────────
from core.constants import BGM_VOLUME

def play_bgm(filepath: str):
    import os

    base, _ = os.path.splitext(filepath)
    candidates = list(dict.fromkeys(
        [filepath] + [base + ext for ext in (".ogg", ".mp3", ".wav", ".flac")]
    ))

    for path in candidates:
        if not os.path.exists(path):
            continue
        # 실제 오디오는 보통 1KB 이상 - 더미/플레이스홀더 파일 거르기
        if os.path.getsize(path) < 1024:
            print(f"[알림] BGM 이 플레이스홀더(더미) 파일이라 건너뜁니다: {path}")
            continue
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(BGM_VOLUME)
            pygame.mixer.music.play(-1)
            return
        except Exception as e:
            print(f"[경고] BGM 재생 실패 ({path}): {e}")

    print(f"[알림] 재생할 수 있는 BGM 이 없습니다: {filepath}")
    print("        assets/audio/ 에 실제 .ogg/.mp3/.wav 음원을 넣어주세요.")

# 시작 BGM
play_bgm("assets/audio/bgm_menu.ogg")

# ── 씬 레지스트리 ────────────────────────────────
def build_scenes():
    return {
        SCENE_MAIN:     MainMenuScene(screen, fonts, shared),
        SCENE_SETTINGS: SettingsScene(screen, fonts, shared),
        SCENE_STORY:    StoryScene(screen, fonts, shared),
        SCENE_GAME:     GameScene(screen, fonts, shared),
    }

scenes      = build_scenes()
current_key = SCENE_MAIN

# ── 배경 오브젝트 ───────────────────────────────
particles    = ParticleSystem(count=80)
scanline_surf = make_scanline_surf()

# ── 메인 루프 ──────────────────────────────────
running = True
while running:
    dt = clock.tick(60)

    scene = scenes[current_key]

    # 이벤트
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        scene.handle_event(event)

    # 씬 전환 처리
    if scene.next_scene:
        if scene.next_scene == "quit":
            running = False
        else:
            prev_key = current_key
            current_key = scene.next_scene
            
            # 음악 전환 (메뉴 <-> 인게임)
            if current_key == SCENE_GAME and prev_key != SCENE_GAME:
                pygame.mixer.music.fadeout(500)
                play_bgm("assets/audio/bgm_ingame.ogg")
            elif current_key == SCENE_MAIN and prev_key == SCENE_GAME:
                pygame.mixer.music.fadeout(500)
                play_bgm("assets/audio/bgm_menu.ogg")

            # 씬 인스턴스 재생성으로 상태 초기화
            scenes = build_scenes()
            scenes[current_key]  # 새 씬으로 진입
        scene.next_scene = None

    # 업데이트
    scene.update(dt)

    # ── 공통 배경 그리기 ─────────────────────────
    draw_background(screen, scanline_surf)
    particles.update_and_draw(screen)
    draw_title_bar(screen, fonts)

    # ── 씬 고유 UI 그리기 ─────────────────────────
    scene.draw(screen)

    # ── 공통 오버레이 ─────────────────────────────
    draw_corners(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
