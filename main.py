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

# ── pygame 초기화 ────────────────────────────────────────────
pygame.init()
pygame.mixer.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("탱장연 - TANK FRONT")
clock = pygame.time.Clock()

fonts   = init_fonts()
shared  = {}   # 씬 간 공유 상태 (볼륨 등)

# ── 씬 레지스트리 ────────────────────────────────────────────
def build_scenes():
    return {
        SCENE_MAIN:     MainMenuScene(screen, fonts, shared),
        SCENE_SETTINGS: SettingsScene(screen, fonts, shared),
        SCENE_STORY:    StoryScene(screen, fonts, shared),
        SCENE_GAME:     GameScene(screen, fonts, shared),
    }

scenes      = build_scenes()
current_key = SCENE_MAIN

# ── 배경 오브젝트 ─────────────────────────────────────────────
particles    = ParticleSystem(count=80)
scanline_surf = make_scanline_surf()

# ── 메인 루프 ────────────────────────────────────────────────
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
            current_key = scene.next_scene
            # 씬 인스턴스 재생성으로 상태 초기화
            scenes = build_scenes()
            scenes[current_key]  # 새 씬으로 진입
        scene.next_scene = None

    # 업데이트
    scene.update(dt)

    # ── 공통 배경 그리기 ──────────────────────────────────────
    draw_background(screen, scanline_surf)
    particles.update_and_draw(screen)
    draw_title_bar(screen, fonts)

    # ── 씬 고유 UI 그리기 ─────────────────────────────────────
    scene.draw(screen)

    # ── 공통 오버레이 ─────────────────────────────────────────
    draw_corners(screen)

    pygame.display.flip()

pygame.quit()
sys.exit()
