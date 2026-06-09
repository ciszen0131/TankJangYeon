import pygame

from scenes.base import Scene

from core.constants import (
    SCENE_MAIN,
    BLACK,
    WHITE,
    YELLOW,
    GRAY,
    DGRAY,
    CYAN,
    WIDTH,
)

from core.controls import (
    get_controls,
    key_label,
    set_control_key,
)

from ui.draw import (
    draw_box,
    draw_volume_bar,
    draw_heart_selector,
    draw_text_outline,
)

VOLUME_ITEMS = [
    ("마스터 볼륨", "volume_master"),
    ("음악 볼륨", "volume_music"),
    ("효과음 볼륨", "volume_sfx"),
]

KEY_ITEMS = [
    ("위로 가기", "move_up"),
    ("아래로 가기", "move_down"),
    ("왼쪽으로 가기", "move_left"),
    ("오른쪽으로 가기", "move_right"),
    ("아이템 슬롯 변경", "slot_change"),
    ("아이템 사용", "use_item"),
]

BG_COLOR = (96, 96, 96)


class SettingsScene(Scene):

    def __init__(self, screen, fonts, shared):

        super().__init__(screen, fonts, shared)

        self.selected = 0

        self.binding_action: str | None = None

        # 키 설정 스크롤
        self.key_scroll = 0
        self.key_row_height = 46
        self.visible_key_rows = 4

        self.shared.setdefault("volume_master", 8)
        self.shared.setdefault("volume_music", 6)
        self.shared.setdefault("volume_sfx", 8)

        get_controls(self.shared)

    def handle_event(self, event: pygame.event.Event) -> None:

        if event.type != pygame.KEYDOWN:
            return

        controls = get_controls(self.shared)

        volume_count = len(VOLUME_ITEMS)
        key_count = len(KEY_ITEMS)

        total_count = volume_count + key_count + 1

        # =========================
        # 키 변경 중
        # =========================

        if self.binding_action is not None:

            if event.key == pygame.K_ESCAPE:

                self.binding_action = None

            else:

                set_control_key(
                    self.shared,
                    self.binding_action,
                    event.key
                )

                self.binding_action = None

            return

        # =========================
        # 위 이동
        # =========================

        if event.key == controls["move_up"]:

            self.selected = (
                self.selected - 1
            ) % total_count

        # =========================
        # 아래 이동
        # =========================

        elif event.key == controls["move_down"]:

            self.selected = (
                self.selected + 1
            ) % total_count

        # =========================
        # 볼륨 감소
        # =========================

        elif event.key == controls["move_left"]:

            if self.selected < volume_count:

                key = VOLUME_ITEMS[self.selected][1]

                self.shared[key] = max(
                    0,
                    self.shared[key] - 1
                )

        # =========================
        # 볼륨 증가
        # =========================

        elif event.key == controls["move_right"]:

            if self.selected < volume_count:

                key = VOLUME_ITEMS[self.selected][1]

                self.shared[key] = min(
                    10,
                    self.shared[key] + 1
                )

        # =========================
        # 확인
        # =========================

        elif event.key in (
            pygame.K_RETURN,
            pygame.K_z
        ):

            # 키 설정 선택
            if (
                volume_count
                <= self.selected
                < volume_count + key_count
            ):

                self.binding_action = (
                    KEY_ITEMS[
                        self.selected - volume_count
                    ][1]
                )

            # 돌아가기
            elif (
                self.selected
                == volume_count + key_count
            ):

                self.next_scene = SCENE_MAIN

        # =========================
        # ESC
        # =========================

        elif event.key == pygame.K_ESCAPE:

            self.next_scene = SCENE_MAIN

        # =========================
        # 자동 스크롤
        # =========================

        if (
            volume_count
            <= self.selected
            < volume_count + key_count
        ):

            current_index = (
                self.selected - volume_count
            )

            visible_top = (
                self.key_scroll
                // self.key_row_height
            )

            visible_bottom = (
                visible_top
                + self.visible_key_rows
                - 1
            )

            # 아래로 내려감
            if current_index >= visible_bottom:

                self.key_scroll = (
                    (
                        current_index
                        - self.visible_key_rows
                        + 2
                    )
                    * self.key_row_height
                )

            # 위로 올라감
            elif current_index < visible_top:

                self.key_scroll = (
                    current_index
                    * self.key_row_height
                )

            self.key_scroll = max(
                0,
                self.key_scroll
            )

    def update(self, dt: int) -> None:
        pass

    def draw(self, surf: pygame.Surface) -> None:

        surf.fill(BG_COLOR)

        cfg_box = pygame.Rect(
            72,
            84,
            656,
            444
        )

        pygame.draw.rect(
            surf,
            DGRAY,
            cfg_box
        )

        draw_box(
            surf,
            cfg_box,
            WHITE,
            3
        )

        # =========================
        # 제목
        # =========================

        draw_text_outline(
            surf,
            "[ 설  정 ]",
            self.fonts["sub"],
            WIDTH // 2,
            cfg_box.y + 12,
            color=CYAN,
            cx=True
        )

        # =========================
        # 돌아가기 버튼
        # =========================

        back_index = (
            len(VOLUME_ITEMS)
            + len(KEY_ITEMS)
        )

        is_back = (
            self.selected == back_index
        )

        back_color = (
            YELLOW if is_back else WHITE
        )

        back_y = cfg_box.y + 14

        if is_back:

            draw_heart_selector(
                surf,
                self.fonts["sub"],
                cfg_box.x + 18,
                back_y + 8
            )

        back_txt = self.fonts["body"].render(
            "돌아가기",
            False,
            back_color
        )

        surf.blit(
            back_txt,
            (
                cfg_box.x + 42,
                back_y
            )
        )

        # =========================
        # 카테고리 제목
        # =========================

        volume_title = self.fonts["small"].render(
            "볼륨",
            False,
            GRAY
        )

        key_title = self.fonts["small"].render(
            "키 설정",
            False,
            GRAY
        )

        surf.blit(
            volume_title,
            (
                cfg_box.x + 28,
                cfg_box.y + 56
            )
        )

        surf.blit(
            key_title,
            (
                cfg_box.x + 28,
                cfg_box.y + 230
            )
        )

        # =========================
        # 볼륨 설정
        # =========================

        volume_row_y = cfg_box.y + 90

        for i, (label, key) in enumerate(
            VOLUME_ITEMS
        ):

            iy = volume_row_y + i * 52

            is_sel = (
                i == self.selected
            )

            color = (
                YELLOW
                if is_sel
                else WHITE
            )

            if is_sel:

                draw_heart_selector(
                    surf,
                    self.fonts["sub"],
                    cfg_box.x + 22,
                    iy + 12
                )

            lbl = self.fonts["body"].render(
                label,
                False,
                color
            )

            surf.blit(
                lbl,
                (
                    cfg_box.x + 48,
                    iy
                )
            )

            draw_volume_bar(
                surf,
                self.fonts,
                cfg_box.x + 160,
                iy + 2,
                180,
                18,
                self.shared[key],
                active=is_sel
            )

            if is_sel:

                hint = self.fonts["small"].render(
                    "← → 조절",
                    False,
                    GRAY
                )

                surf.blit(
                    hint,
                    (
                        cfg_box.x + 48,
                        iy + 20
                    )
                )

        # =========================
        # 키 설정
        # =========================

        key_row_y = cfg_box.y + 264

        for i, (label, action) in enumerate(
            KEY_ITEMS
        ):

            item_index = (
                len(VOLUME_ITEMS)
                + i
            )

            iy = (
                key_row_y
                + i * self.key_row_height
                - self.key_scroll
            )

            # 화면 밖 숨김
            if (
                iy < cfg_box.y + 250
                or iy > cfg_box.bottom - 70
            ):
                continue

            is_sel = (
                item_index == self.selected
            )

            color = (
                YELLOW
                if is_sel
                else WHITE
            )

            if is_sel:

                draw_heart_selector(
                    surf,
                    self.fonts["sub"],
                    cfg_box.x + 22,
                    iy + 12
                )

            lbl = self.fonts["body"].render(
                label,
                False,
                color
            )

            surf.blit(
                lbl,
                (
                    cfg_box.x + 48,
                    iy
                )
            )

            current = key_label(
                self.shared["controls"][action]
            )

            key_surf = self.fonts["body"].render(
                current,
                False,
                CYAN if is_sel else GRAY
            )

            surf.blit(
                key_surf,
                (
                    cfg_box.right
                    - key_surf.get_width()
                    - 34,
                    iy
                )
            )

            if is_sel:

                hint_text = (
                    "ENTER 로 변경"
                    if self.binding_action is None
                    else "원하는 키를 누르세요"
                )

                hint = self.fonts["small"].render(
                    hint_text,
                    False,
                    GRAY
                )

                surf.blit(
                    hint,
                    (
                        cfg_box.x + 48,
                        iy + 22
                    )
                )

        # =========================
        # 키 변경 팝업
        # =========================

        if self.binding_action is not None:

            overlay = pygame.Rect(
                cfg_box.x + 116,
                cfg_box.y + 154,
                424,
                96
            )

            pygame.draw.rect(
                surf,
                BLACK,
                overlay
            )

            draw_box(
                surf,
                overlay,
                WHITE,
                2
            )

            msg = self.fonts["sub"].render(
                "키를 눌러 변경",
                False,
                YELLOW
            )

            sub = self.fonts["small"].render(
                "ESC 로 취소",
                False,
                GRAY
            )

            surf.blit(
                msg,
                (
                    overlay.centerx
                    - msg.get_width() // 2,
                    overlay.y + 18
                )
            )

            surf.blit(
                sub,
                (
                    overlay.centerx
                    - sub.get_width() // 2,
                    overlay.y + 56
                )
            )

        # =========================
        # 하단 ESC 안내
        # =========================

        esc_hint = self.fonts["small"].render(
            "ESC 로 돌아가기",
            False,
            GRAY
        )

        surf.blit(
            esc_hint,
            (
                WIDTH // 2
                - esc_hint.get_width() // 2,
                cfg_box.bottom + 10
            )
        )