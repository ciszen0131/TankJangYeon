import pygame
import random
from core.constants import WIDTH, HEIGHT, WHITE, CYAN, YELLOW, ORANGE


class Particle:
    def __init__(self):
        self.reset()

    def reset(self):
        self.x       = random.randint(0, WIDTH)
        self.y       = random.randint(0, HEIGHT)
        self.vx      = random.uniform(-0.3, 0.3)
        self.vy      = random.uniform(-0.6, -0.1)
        self.life    = random.randint(80, 200)
        self.maxlife = self.life
        self.size    = random.randint(1, 3)
        self.color   = random.choice([WHITE, CYAN, YELLOW, ORANGE])

    def update(self):
        self.x    += self.vx
        self.y    += self.vy
        self.life -= 1
        if self.life <= 0 or self.y < 0:
            self.reset()

    def draw(self, surf: pygame.Surface):
        alpha = int(255 * (self.life / self.maxlife))
        s = pygame.Surface((self.size * 2, self.size * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, alpha), (self.size, self.size), self.size)
        surf.blit(s, (int(self.x), int(self.y)))


class ParticleSystem:
    def __init__(self, count: int = 80):
        self.particles = [Particle() for _ in range(count)]

    def update_and_draw(self, surf: pygame.Surface):
        for p in self.particles:
            p.update()
            p.draw(surf)


def make_scanline_surf() -> pygame.Surface:
    """스캔라인 오버레이 Surface 생성 (한 번만 호출)."""
    surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    for y in range(0, HEIGHT, 2):
        pygame.draw.line(surf, (0, 0, 0, 40), (0, y), (WIDTH, y))
    return surf
