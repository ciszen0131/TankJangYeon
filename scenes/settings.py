import pygame
from scenes.base import Scene
from core.constants import (
    SCENE_MAIN, BLACK, WHITE, YELLOW, GRAY, DGRAY, RED, CYAN, WIDTH
)
from ui.draw import draw_box, draw_volume_bar, draw_heart_selector

LABELS   = ["마스터 볼륨", "음악 볼륨", "효과음 볼륨"]
VOL_KEYS = ["volume_master", "volume_music", "volume_sfx"]
ITEMS    = LABELS + ["← 돌아가기"]


class SettingsScene(Scene):
    def __init__(self, screen, fonts, shared):
        super().__init__(screen, fonts, shared)
        self.selected = 0
        # 볼륨값은 shared 에서 읽고 씀
        self.shared.setdefault("volume_master", 8)
        self.shared.setdefault("volume_music",  6)
        self.shared.setdefault("volume_sfx",    8)

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_UP, pygame.K_w):
            self.selected = (self.selected - 1) % len(ITEMS)
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.selected = (self.selected + 1) % len(ITEMS)

        elif event.key in (pygame.K_LEFT, pygame.K_a):
            if self.selected < 3:
                key = VOL_KEYS[self.selected]
                self.shared[key] = max(0, self.shared[key] - 1)

        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            if self.selected < 3:
                key = VOL_KEYS[self.selected]
                self.shared[key] = min(10, self.shared[key] + 1)

        elif event.key in (pygame.K_RETURN, pygame.K_z, pygame.K_ESCAPE):
            if self.selected == 3 or event.key == pygame.K_ESCAPE:
                self.next_scene = SCENE_MAIN

    def update(self, dt: int) -> None:
        pass

    def draw(self, surf: pygame.Surface) -> None:
        cfg_box = pygame.Rect(160, 165, 480, 260)
        pygame.draw.rect(surf, BLACK, cfg_box)
        draw_box(surf, cfg_box, WHITE, 3)

        # 타이틀
        t = self.fonts["sub"].render("[ 설  정 ]", False, CYAN)
        surf.blit(t, (WIDTH // 2 - t.get_width() // 2, cfg_box.y + 12))

        # 볼륨 항목
        for i, (label, key) in enumerate(zip(LABELS, VOL_KEYS)):
            iy     = cfg_box.y + 55 + i * 56
            is_sel = (i == self.selected)
            color  = YELLOW if is_sel else WHITE

            if is_sel:
                draw_heart_selector(surf, self.fonts["sub"], cfg_box.x + 22, iy + 12)

            lbl = self.fonts["body"].render(label, False, color)
            surf.blit(lbl, (cfg_box.x + 48, iy))

            draw_volume_bar(surf, self.fonts,
                            cfg_box.x + 200, iy + 2, 180, 18,
                            self.shared[key], active=is_sel)

            if is_sel:
                hint = self.fonts["small"].render("← → 조절", False, GRAY)
                surf.blit(hint, (cfg_box.x + 48, iy + 22))

        # 돌아가기
        back_y  = cfg_box.y + 220
        is_back = (self.selected == 3)
        if is_back:
            draw_heart_selector(surf, self.fonts["sub"], cfg_box.x + 22, back_y + 12)
        bc = YELLOW if is_back else WHITE
        back_txt = self.fonts["sub"].render("← 돌아가기", False, bc)
        surf.blit(back_txt, (cfg_box.x + 48, back_y))

        esc_hint = self.fonts["small"].render("ESC 로 돌아가기", False, GRAY)
        surf.blit(esc_hint, (WIDTH // 2 - esc_hint.get_width() // 2, cfg_box.bottom + 12))
