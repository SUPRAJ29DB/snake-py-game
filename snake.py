import random
import sys

import pygame

CELL_SIZE = 20
GRID_WIDTH = 40
GRID_HEIGHT = 30

WIDTH = GRID_WIDTH * CELL_SIZE
HEIGHT = GRID_HEIGHT * CELL_SIZE

FPS = 60
INITIAL_SPEED = 8
SPEED_INCREASE = 1
MAX_SPEED = 20

BACKGROUND = (18, 24, 32)
GRID_COLOR = (29, 38, 48)
SNAKE_COLOR = (65, 220, 120)
SNAKE_HEAD_COLOR = (120, 255, 160)
FOOD_COLOR = (255, 85, 85)
TEXT_COLOR = (240, 245, 250)
OVERLAY_COLOR = (8, 12, 18)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Python Snake")
clock = pygame.time.Clock()

font = pygame.font.Font(None, 30)
large_font = pygame.font.Font(None, 58)
small_font = pygame.font.Font(None, 24)


def random_food(snake):
    """Choose a free grid cell for the food."""
    free_cells = [
        (x, y)
        for x in range(GRID_WIDTH)
        for y in range(GRID_HEIGHT)
        if (x, y) not in snake
    ]

    return random.choice(free_cells) if free_cells else None


def new_game():
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
        "food": random_food(snake),
        "score": 0,
        "state": "playing",
        "move_timer": 0,
    }


def draw_cell(color, position, inset=2):
    """Draw one grid cell."""
    x, y = position
    rect = pygame.Rect(
        x * CELL_SIZE + inset,
        y * CELL_SIZE + inset,
        CELL_SIZE - inset * 2,
        CELL_SIZE - inset * 2,
    )
    pygame.draw.rect(screen, color, rect, border_radius=5)


def draw_text(text, font_obj, color, center):
    surface = font_obj.render(text, True, color)
    rect = surface.get_rect(center=center)
    screen.blit(surface, rect)


def draw_game(game):
    screen.fill(BACKGROUND)

    for x in range(0, WIDTH, CELL_SIZE):
        pygame.draw.line(
            screen, GRID_COLOR, (x, 0), (x, HEIGHT)
        )

    for y in range(0, HEIGHT, CELL_SIZE):
        pygame.draw.line(
            screen, GRID_COLOR, (0, y), (WIDTH, y)
        )

    # Food
    if game["food"] is not None:
        draw_cell(FOOD_COLOR, game["food"], inset=3)

    for index, segment in enumerate(game["snake"]):
        color = SNAKE_HEAD_COLOR if index == 0 else SNAKE_COLOR
        draw_cell(color, segment)

    speed = min(
        INITIAL_SPEED + game["score"] // 5 * SPEED_INCREASE,
        MAX_SPEED,
    )

    score_surface = font.render(
        f"Score: {game['score']}", True, TEXT_COLOR
    )
    screen.blit(score_surface, (12, 10))

    speed_surface = small_font.render(
        f"Speed: {speed}", True, TEXT_COLOR
    )
    speed_rect = speed_surface.get_rect(topright=(WIDTH - 12, 14))
    screen.blit(speed_surface, speed_rect)

    if game["state"] in ("game_over", "won"):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((*OVERLAY_COLOR, 210))
        screen.blit(overlay, (0, 0))

        if game["state"] == "won":
            title = "YOU WIN!"
        else:
            title = "GAME OVER"

        draw_text(
            title,
            large_font,
            FOOD_COLOR if game["state"] == "game_over"
            else SNAKE_HEAD_COLOR,
            (WIDTH // 2, HEIGHT // 2 - 65),
        )

        draw_text(
            f"Final score: {game['score']}",
            font,
            TEXT_COLOR,
            (WIDTH // 2, HEIGHT // 2 - 15),
        )

        draw_text(
            "Press R to restart",
            font,
            TEXT_COLOR,
            (WIDTH // 2, HEIGHT // 2 + 35),
        )

        draw_text(
            "Press ESC to quit",
            small_font,
            TEXT_COLOR,
            (WIDTH // 2, HEIGHT // 2 + 75),
        )

    pygame.display.flip()


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

    if key not in directions:
        return

    new_direction = directions[key]
    current_direction = game["direction"]
    if (
        new_direction[0] + current_direction[0] == 0
        and new_direction[1] + current_direction[1] == 0
    ):
        return

    game["next_direction"] = new_direction


def update_game(game):
    """Advance the snake by one grid cell."""
    snake = game["snake"]
    dx, dy = game["next_direction"]

    game["direction"] = game["next_direction"]

    head_x, head_y = snake[0]
    new_head = (head_x + dx, head_y + dy)

    if not (
        0 <= new_head[0] < GRID_WIDTH
        and 0 <= new_head[1] < GRID_HEIGHT
    ):
        game["state"] = "game_over"
        return

    eating = new_head == game["food"]

    body_to_check = snake if eating else snake[:-1]

    if new_head in body_to_check:
        game["state"] = "game_over"
        return

    snake.insert(0, new_head)

    if eating:
        game["score"] += 1
        game["food"] = random_food(snake)

        if game["food"] is None:
            game["state"] = "won"
    else:
        snake.pop()


def main():
    game = new_game()
    running = True

    while running:

        elapsed_ms = clock.tick(FPS)
        game["move_timer"] += elapsed_ms

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                elif event.key == pygame.K_r:
                    if game["state"] != "playing":
                        game = new_game()

                elif game["state"] == "playing":
                    handle_direction(game, event.key)

        if game["state"] == "playing":
            speed = min(
                INITIAL_SPEED
                + game["score"] // 5 * SPEED_INCREASE,
                MAX_SPEED,
            )
            move_interval = 1000 / speed

            if game["move_timer"] >= move_interval:
                game["move_timer"] %= move_interval
                update_game(game)

        draw_game(game)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
