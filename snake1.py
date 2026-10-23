import asyncio
import json
import math
import random
import struct
from array import array
from pathlib import Path

import pygame

CELL_SIZE = 20
GRID_WIDTH = 40
GRID_HEIGHT = 30

WIDTH = GRID_WIDTH * CELL_SIZE
HEIGHT = GRID_HEIGHT * CELL_SIZE

FPS = 60

INITIAL_SPEED = 8
SPEED_INCREASE = 1
POINTS_PER_LEVEL = 5
MAX_SPEED = 22

HIGH_SCORE_FILE = Path("snake_high_score.json")

BACKGROUND = (18, 24, 32)
GRID_COLOR = (29, 38, 48)
GRID_HIGHLIGHT = (42, 53, 65)

SNAKE_COLOR = (65, 220, 120)
SNAKE_HEAD_COLOR = (120, 255, 160)

FOOD_COLOR = (255, 85, 85)
FOOD_HIGHLIGHT = (255, 190, 190)

TEXT_COLOR = (240, 245, 250)
MUTED_TEXT_COLOR = (160, 175, 190)

OVERLAY_COLOR = (8, 12, 18)
ACCENT_COLOR = (90, 180, 255)
PAUSE_COLOR = (255, 210, 90)

SHADOW_COLOR = (5, 9, 13)

pygame.init()

try:
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
except pygame.error:
    AUDIO_AVAILABLE = False

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Python Snake 3D")
clock = pygame.time.Clock()

title_font = pygame.font.Font(None, 78)
large_font = pygame.font.Font(None, 64)
font = pygame.font.Font(None, 30)
small_font = pygame.font.Font(None, 24)
tiny_font = pygame.font.Font(None, 20)

ALL_CELLS = {
    (x, y)
    for x in range(GRID_WIDTH)
    for y in range(GRID_HEIGHT)
}

def lighten(color, amount=25):
    """Return a brighter version of an RGB color."""
    return tuple(min(255, value + amount) for value in color)


def darken(color, amount=35):
    """Return a darker version of an RGB color."""
    return tuple(max(0, value - amount) for value in color)


def current_level(score):
    """Calculate the current level from the score."""
    return 1 + score // POINTS_PER_LEVEL


def current_speed(score):
    """Calculate movement speed from the current score."""
    level = current_level(score)

    return min(
        INITIAL_SPEED + (level - 1) * SPEED_INCREASE,
        MAX_SPEED,
    )


def create_tone(frequency, duration_ms, volume=0.25):
    """Create a short sound procedurally without external files."""
    if not AUDIO_AVAILABLE:
        return None

    sample_rate = 44100
    sample_count = int(sample_rate * duration_ms / 1000)
    amplitude = int(32767 * volume)

    samples = array("h")

    for index in range(sample_count):
        time_value = index / sample_rate

        # Fade out to avoid a clicking sound.
        fade = max(0.0, 1.0 - index / sample_count)

        value = math.sin(2 * math.pi * frequency * time_value)
        samples.append(int(amplitude * value * fade))

    raw_samples = samples.tobytes()

    wav_header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + len(raw_samples),
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        len(raw_samples),
    )

    return pygame.mixer.Sound(buffer=wav_header + raw_samples)


if AUDIO_AVAILABLE:
    eat_sound = create_tone(720, 90, 0.22)
    level_sound = create_tone(980, 160, 0.25)
    game_over_sound = create_tone(150, 280, 0.25)
    click_sound = create_tone(420, 60, 0.15)
else:
    eat_sound = None
    level_sound = None
    game_over_sound = None
    click_sound = None


def play_sound(sound, enabled=True):
    """Play a sound safely."""
    if not enabled or sound is None:
        return

    try:
        sound.play()
    except pygame.error:
        pass


def load_high_score():
    """Load the high score safely."""
    try:
        data = json.loads(
            HIGH_SCORE_FILE.read_text(encoding="utf-8")
        )

        return max(0, int(data.get("high_score", 0)))

    except (
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ):
        return 0


def save_high_score(high_score):
    """Save the high score as JSON."""
    try:
        HIGH_SCORE_FILE.write_text(
            json.dumps(
                {"high_score": int(high_score)},
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError:
        # Some browser environments may not allow file writes.
        pass


def random_food(snake):
    """
    Select a free cell efficiently.

    `snake` should be a set of occupied positions.
    """
    free_cells = list(ALL_CELLS.difference(snake))

    if not free_cells:
        return None

    return random.choice(free_cells)


def new_game(high_score):
    """Create a fresh game state."""
    center_x = GRID_WIDTH // 2
    center_y = GRID_HEIGHT // 2

    snake = [
        (center_x, center_y),
        (center_x - 1, center_y),
        (center_x - 2, center_y),
    ]

    return {
        "snake": snake,
        "direction": (1, 0),
        "next_direction": (1, 0),
        "food": random_food(set(snake)),
        "score": 0,
        "high_score": high_score,
        "state": "start",
        "move_timer": 0.0,
        "sound_enabled": AUDIO_AVAILABLE,
    }


def restart_game(game):
    """Restart the game while preserving the high score."""
    high_score = game["high_score"]
    restarted = new_game(high_score)
    restarted["state"] = "playing"
    return restarted


def draw_3d_cell(color, position, inset=2, is_head=False):

    x, y = position

    rect = pygame.Rect(
        x * CELL_SIZE + inset,
        y * CELL_SIZE + inset,
        CELL_SIZE - inset * 2,
        CELL_SIZE - inset * 2,
    )

    shadow_rect = rect.move(2, 3)

    pygame.draw.rect(
        screen,
        SHADOW_COLOR,
        shadow_rect,
        border_radius=6,
    )

    # Main body.
    pygame.draw.rect(
        screen,
        color,
        rect,
        border_radius=6,
    )

    highlight = lighten(color, 35)

    pygame.draw.line(
        screen,
        highlight,
        rect.topleft,
        rect.topright,
        2,
    )

    pygame.draw.line(
        screen,
        highlight,
        rect.topleft,
        rect.bottomleft,
        2,
    )

    shadow = darken(color, 45)

    pygame.draw.line(
        screen,
        shadow,
        rect.bottomleft,
        rect.bottomright,
        3,
    )

    pygame.draw.line(
        screen,
        shadow,
        rect.topright,
        rect.bottomright,
        3,
    )

    shine_rect = pygame.Rect(
        rect.left + 4,
        rect.top + 3,
        max(3, rect.width // 3),
        3,
    )

    pygame.draw.rect(
        screen,
        lighten(color, 90),
        shine_rect,
        border_radius=2,
    )

    if is_head:
        draw_head_eyes(rect)


def draw_head_eyes(rect):
    """Draw simple eyes on the snake's head."""
    eye_color = (10, 35, 20)

    direction = game_direction_for_drawing

    if direction == (1, 0):
        eyes = [
            (rect.right - 5, rect.top + 6),
            (rect.right - 5, rect.bottom - 6),
        ]
    elif direction == (-1, 0):
        eyes = [
            (rect.left + 5, rect.top + 6),
            (rect.left + 5, rect.bottom - 6),
        ]
    elif direction == (0, -1):
        eyes = [
            (rect.left + 6, rect.top + 5),
            (rect.right - 6, rect.top + 5),
        ]
    else:
        eyes = [
            (rect.left + 6, rect.bottom - 5),
            (rect.right - 6, rect.bottom - 5),
        ]

    for eye in eyes:
        pygame.draw.circle(screen, eye_color, eye, 2)


def draw_3d_food(position):
    """Draw the food as a glowing pseudo-3D sphere."""
    x, y = position

    center = (
        x * CELL_SIZE + CELL_SIZE // 2,
        y * CELL_SIZE + CELL_SIZE // 2,
    )

    pygame.draw.circle(
        screen,
        (75, 25, 30),
        center,
        11,
    )

    pygame.draw.circle(
        screen,
        (135, 35, 42),
        (center[0] + 1, center[1] + 2),
        9,
    )

    pygame.draw.circle(
        screen,
        FOOD_COLOR,
        center,
        7,
    )

    pygame.draw.circle(
        screen,
        FOOD_HIGHLIGHT,
        (center[0] - 2, center[1] - 3),
        2,
    )

    pygame.draw.arc(
        screen,
        (110, 25, 30),
        pygame.Rect(
            center[0] - 7,
            center[1] - 7,
            14,
            14,
        ),
        0.15,
        math.pi - 0.15,
        2,
    )


def draw_board_frame():
    """Draw a raised frame around the board."""
    outer_rect = pygame.Rect(
        2,
        2,
        WIDTH - 4,
        HEIGHT - 4,
    )

    pygame.draw.rect(
        screen,
        (5, 8, 12),
        outer_rect,
        width=4,
    )

    pygame.draw.line(
        screen,
        (70, 90, 105),
        outer_rect.topleft,
        outer_rect.topright,
        3,
    )

    pygame.draw.line(
        screen,
        (70, 90, 105),
        outer_rect.topleft,
        outer_rect.bottomleft,
        3,
    )

    # Dark bottom and right edges.
    pygame.draw.line(
        screen,
        (3, 5, 8),
        outer_rect.bottomleft,
        outer_rect.bottomright,
        3,
    )

    pygame.draw.line(
        screen,
        (3, 5, 8),
        outer_rect.topright,
        outer_rect.bottomright,
        3,
    )


def draw_background():
    """Draw the background and grid."""
    screen.fill(BACKGROUND)

    for y in range(0, HEIGHT + 1, CELL_SIZE):
        pygame.draw.line(
            screen,
            GRID_COLOR,
            (0, y),
            (WIDTH, y),
        )

    for x in range(0, WIDTH + 1, CELL_SIZE):
        pygame.draw.line(
            screen,
            GRID_COLOR,
            (x, 0),
            (x, HEIGHT),
        )

    for x in range(CELL_SIZE, WIDTH, CELL_SIZE):
        pygame.draw.line(
            screen,
            GRID_HIGHLIGHT,
            (x + 1, 0),
            (x + 1, HEIGHT),
        )

    for y in range(CELL_SIZE, HEIGHT, CELL_SIZE):
        pygame.draw.line(
            screen,
            GRID_HIGHLIGHT,
            (0, y + 1),
            (WIDTH, y + 1),
        )

    draw_board_frame()


def draw_text(text, font_obj, color, center):
    """Draw centered text."""
    surface = font_obj.render(str(text), True, color)
    rect = surface.get_rect(center=center)
    screen.blit(surface, rect)


def draw_hud(game):
    """Draw score, level, speed, and high score."""
    score_surface = font.render(
        f"Score: {game['score']}",
        True,
        TEXT_COLOR,
    )

    screen.blit(score_surface, (12, 10))

    level_surface = small_font.render(
        f"Level: {current_level(game['score'])}",
        True,
        ACCENT_COLOR,
    )

    level_rect = level_surface.get_rect(
        center=(WIDTH // 2, 24)
    )

    screen.blit(level_surface, level_rect)

    high_surface = small_font.render(
        f"Best: {game['high_score']}",
        True,
        TEXT_COLOR,
    )

    high_rect = high_surface.get_rect(
        topright=(WIDTH - 12, 14)
    )

    screen.blit(high_surface, high_rect)

    speed_surface = tiny_font.render(
        f"Speed: {current_speed(game['score'])}",
        True,
        MUTED_TEXT_COLOR,
    )

    speed_rect = speed_surface.get_rect(
        bottomleft=(12, HEIGHT - 8)
    )

    screen.blit(speed_surface, speed_rect)

    sound_label = "Sound: ON" if game["sound_enabled"] else "Sound: OFF"

    sound_surface = tiny_font.render(
        sound_label,
        True,
        MUTED_TEXT_COLOR,
    )

    sound_rect = sound_surface.get_rect(
        bottomright=(WIDTH - 12, HEIGHT - 8)
    )

    screen.blit(sound_surface, sound_rect)


def draw_overlay():
    """Draw a transparent dark overlay."""
    overlay = pygame.Surface(
        (WIDTH, HEIGHT),
        pygame.SRCALPHA,
    )

    overlay.fill((*OVERLAY_COLOR, 220))
    screen.blit(overlay, (0, 0))


def draw_start_overlay():
    """Draw the start screen."""
    draw_overlay()

    draw_text(
        "PYTHON SNAKE",
        title_font,
        SNAKE_HEAD_COLOR,
        (WIDTH // 2, HEIGHT // 2 - 110),
    )

    draw_text(
        "3D Edition",
        font,
        ACCENT_COLOR,
        (WIDTH // 2, HEIGHT // 2 - 58),
    )

    draw_text(
        "Eat food, grow longer, and beat your high score.",
        small_font,
        TEXT_COLOR,
        (WIDTH // 2, HEIGHT // 2 - 12),
    )

    draw_text(
        "Press ENTER or SPACE to start",
        font,
        ACCENT_COLOR,
        (WIDTH // 2, HEIGHT // 2 + 42),
    )

    draw_text(
        "Arrow keys / WASD: move    P: pause    M: sound",
        small_font,
        MUTED_TEXT_COLOR,
        (WIDTH // 2, HEIGHT // 2 + 91),
    )


def draw_pause_overlay():
    """Draw the pause screen."""
    draw_overlay()

    draw_text(
        "PAUSED",
        large_font,
        PAUSE_COLOR,
        (WIDTH // 2, HEIGHT // 2 - 35),
    )

    draw_text(
        "Press P to resume",
        font,
        TEXT_COLOR,
        (WIDTH // 2, HEIGHT // 2 + 30),
    )


def draw_end_overlay(game):
    """Draw the game-over or win screen."""
    draw_overlay()

    if game["state"] == "won":
        title = "YOU WIN!"
        title_color = SNAKE_HEAD_COLOR
    else:
        title = "GAME OVER"
        title_color = FOOD_COLOR

    draw_text(
        title,
        large_font,
        title_color,
        (WIDTH // 2, HEIGHT // 2 - 90),
    )

    draw_text(
        f"Final score: {game['score']}",
        font,
        TEXT_COLOR,
        (WIDTH // 2, HEIGHT // 2 - 30),
    )

    draw_text(
        f"High score: {game['high_score']}",
        font,
        ACCENT_COLOR,
        (WIDTH // 2, HEIGHT // 2 + 10),
    )

    draw_text(
        "Press R, ENTER, or SPACE to restart",
        font,
        TEXT_COLOR,
        (WIDTH // 2, HEIGHT // 2 + 62),
    )

    draw_text(
        "Press ESC to quit",
        small_font,
        MUTED_TEXT_COLOR,
        (WIDTH // 2, HEIGHT // 2 + 105),
    )


def draw_game(game):
    """Render the complete game."""
    global game_direction_for_drawing

    draw_background()

    if game["food"] is not None:
        draw_3d_food(game["food"])

    game_direction_for_drawing = game["direction"]

    for index, segment in enumerate(game["snake"]):
        color = (
            SNAKE_HEAD_COLOR
            if index == 0
            else SNAKE_COLOR
        )

        draw_3d_cell(
            color,
            segment,
            inset=2,
            is_head=index == 0,
        )

    draw_hud(game)

    if game["state"] == "start":
        draw_start_overlay()

    elif game["state"] == "paused":
        draw_pause_overlay()

    elif game["state"] in ("game_over", "won"):
        draw_end_overlay(game)

    pygame.display.flip()


# ============================================================
# Input
# ============================================================

def handle_direction(game, key):
    """Change direction without allowing a 180-degree turn."""
    directions = {
        pygame.K_UP: (0, -1),
        pygame.K_w: (0, -1),

        pygame.K_DOWN: (0, 1),
        pygame.K_s: (0, 1),

        pygame.K_LEFT: (-1, 0),
        pygame.K_a: (-1, 0),

        pygame.K_RIGHT: (1, 0),
        pygame.K_d: (1, 0),
    }

    new_direction = directions.get(key)

    if new_direction is None:
        return

    current_direction = game["direction"]

    # Reject a direct 180-degree turn.
    if (
        new_direction[0] == -current_direction[0]
        and new_direction[1] == -current_direction[1]
    ):
        return

    game["next_direction"] = new_direction


def toggle_pause(game):
    """Toggle between playing and paused states."""
    if game["state"] == "playing":
        game["state"] = "paused"

    elif game["state"] == "paused":
        game["state"] = "playing"


def update_game(game):
    """Advance the snake by one grid cell."""
    snake = game["snake"]

    game["direction"] = game["next_direction"]

    dx, dy = game["direction"]

    head_x, head_y = snake[0]
    new_head = (
        head_x + dx,
        head_y + dy,
    )

    if not (
        0 <= new_head[0] < GRID_WIDTH
        and 0 <= new_head[1] < GRID_HEIGHT
    ):
        game["state"] = "game_over"
        play_sound(
            game_over_sound,
            game["sound_enabled"],
        )
        return

    eating = new_head == game["food"]

    body_to_check = snake if eating else snake[:-1]

    if new_head in body_to_check:
        game["state"] = "game_over"
        play_sound(
            game_over_sound,
            game["sound_enabled"],
        )
        return

    old_level = current_level(game["score"])

    snake.insert(0, new_head)

    if eating:
        game["score"] += 1

        if game["score"] > game["high_score"]:
            game["high_score"] = game["score"]
            save_high_score(game["high_score"])

        game["food"] = random_food(set(snake))

        play_sound(
            eat_sound,
            game["sound_enabled"],
        )

        new_level = current_level(game["score"])

        if new_level > old_level:
            play_sound(
                level_sound,
                game["sound_enabled"],
            )

        if game["food"] is None:
            game["state"] = "won"

    else:
        snake.pop()


def process_movement(game, elapsed_seconds):

    game["move_timer"] += elapsed_seconds

    speed = current_speed(game["score"])
    move_interval = 1.0 / speed

    updates = 0
    max_updates_per_frame = 5

    while (
        game["move_timer"] >= move_interval
        and game["state"] == "playing"
        and updates < max_updates_per_frame
    ):
        game["move_timer"] -= move_interval
        update_game(game)
        updates += 1

    if updates == max_updates_per_frame:
        game["move_timer"] = 0.0


async def main():
    """Run the game."""
    high_score = load_high_score()
    game = new_game(high_score)

    running = True

    while running:
        elapsed_seconds = min(
            clock.tick(FPS) / 1000.0,
            0.1,
        )

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key in (
                    pygame.K_RETURN,
                    pygame.K_SPACE,
                ):
                    if game["state"] == "start":
                        game["state"] = "playing"
                        play_sound(
                            click_sound,
                            game["sound_enabled"],
                        )

                    elif game["state"] in (
                        "game_over",
                        "won",
                    ):
                        game = restart_game(game)
                        play_sound(
                            click_sound,
                            game["sound_enabled"],
                        )

                elif event.key == pygame.K_r:
                    if game["state"] in (
                        "game_over",
                        "won",
                    ):
                        game = restart_game(game)
                        play_sound(
                            click_sound,
                            game["sound_enabled"],
                        )

                elif event.key == pygame.K_p:
                    if game["state"] in (
                        "playing",
                        "paused",
                    ):
                        toggle_pause(game)
                        play_sound(
                            click_sound,
                            game["sound_enabled"],
                        )

                elif event.key == pygame.K_m:
                    game["sound_enabled"] = not game["sound_enabled"]

                    if not game["sound_enabled"]:
                        if AUDIO_AVAILABLE:
                            pygame.mixer.stop()

                    else:
                        play_sound(
                            click_sound,
                            True,
                        )

                elif game["state"] == "playing":
                    handle_direction(game, event.key)

        if game["state"] == "playing":
            process_movement(
                game,
                elapsed_seconds,
            )

        draw_game(game)

        await asyncio.sleep(0)

    pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
