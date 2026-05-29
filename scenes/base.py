import pygame
from abc import ABC, abstractmethod


class Scene(ABC):
    """모든 씬이 상속받는 베이스 클래스."""

    def __init__(self, screen: pygame.Surface, fonts: dict, shared: dict):
        self.screen = screen
        self.fonts  = fonts
        self.shared = shared   # 씬 간 공유 상태 (볼륨 등)
        self.next_scene: str | None = None  # 전환할 씬 이름, None 이면 유지

    @abstractmethod
    def handle_event(self, event: pygame.event.Event) -> None:
        """키/마우스 이벤트 처리."""

    @abstractmethod
    def update(self, dt: int) -> None:
        """매 프레임 로직 업데이트. dt = clock.tick() 반환값(ms)."""

    @abstractmethod
    def draw(self, bg_surf: pygame.Surface) -> None:
        """화면 렌더링. bg_surf 에는 이미 배경+파티클이 그려져 있음."""
