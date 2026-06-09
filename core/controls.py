import pygame


DEFAULT_CONTROLS = {
    "move_up": pygame.K_UP,
    "move_down": pygame.K_DOWN,
    "move_left": pygame.K_LEFT,
    "move_right": pygame.K_RIGHT,
    "slot_change": pygame.K_x,
    "use_item": pygame.K_z,
}


SPECIAL_KEY_LABELS = {
    pygame.K_UP: "↑",
    pygame.K_DOWN: "↓",
    pygame.K_LEFT: "←",
    pygame.K_RIGHT: "→",
    pygame.K_RETURN: "ENTER",
    pygame.K_ESCAPE: "ESC",
    pygame.K_SPACE: "SPACE",
    pygame.K_TAB: "TAB",
    pygame.K_BACKSPACE: "BACKSPACE",
    pygame.K_LSHIFT: "LSHIFT",
    pygame.K_RSHIFT: "RSHIFT",
    pygame.K_LCTRL: "LCTRL",
    pygame.K_RCTRL: "RCTRL",
    pygame.K_LALT: "LALT",
    pygame.K_RALT: "RALT",
}


def get_controls(shared: dict) -> dict:
    controls = shared.setdefault("controls", dict(DEFAULT_CONTROLS))

    for action, key in DEFAULT_CONTROLS.items():
        controls.setdefault(action, key)

    return controls


def set_control_key(shared: dict, action: str, key: int) -> None:
    controls = get_controls(shared)

    if action in controls:
        controls[action] = key


def key_label(key: int) -> str:
    if key in SPECIAL_KEY_LABELS:
        return SPECIAL_KEY_LABELS[key]

    name = pygame.key.name(key)

    if not name:
        return str(key)

    return name.upper()