import math
import random
import pygame
from pathlib import Path
from collections import deque

# THE LAST EXPEDITION
# Controls: WASD or arrow keys to move; R to restart after a game ends; ESC to quit.

pygame.init()

# Optional audio assets live in a folder named "sounds" beside main.py.
# Missing files are safely ignored, so the game still runs without audio.
SOUND_DIR = Path(__file__).resolve().parent / "sounds"
SOUND_FILES = {
    "music": SOUND_DIR / "background_music.ogg",
    "collect": SOUND_DIR / "collect.wav",
    "warning": SOUND_DIR / "warning.wav",
    "victory": SOUND_DIR / "victory.wav",
    "defeat": SOUND_DIR / "defeat.wav",
}
AUDIO_AVAILABLE = False
SOUND_ENABLED = True
sounds = {}
try:
    pygame.mixer.init()
    AUDIO_AVAILABLE = True
    for sound_name in ("collect", "warning", "victory", "defeat"):
        sound_path = SOUND_FILES[sound_name]
        if sound_path.exists():
            try:
                sounds[sound_name] = pygame.mixer.Sound(str(sound_path))
            except pygame.error:
                pass
    if SOUND_FILES["music"].exists():
        try:
            pygame.mixer.music.load(str(SOUND_FILES["music"]))
            pygame.mixer.music.set_volume(0.35)
            pygame.mixer.music.play(-1)
        except pygame.error:
            pass
except pygame.error:
    AUDIO_AVAILABLE = False


def play_sound(name):
    if SOUND_ENABLED and AUDIO_AVAILABLE and name in sounds:
        try:
            sounds[name].play()
        except pygame.error:
            pass


def set_sound_enabled(enabled):
    global SOUND_ENABLED
    SOUND_ENABLED = enabled
    if not AUDIO_AVAILABLE:
        return
    try:
        if SOUND_ENABLED:
            if SOUND_FILES["music"].exists() and not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)
        else:
            pygame.mixer.music.pause()
    except pygame.error:
        pass

WIDTH, HEIGHT = 800, 600
TILE = 40
COLS, ROWS = WIDTH // TILE, HEIGHT // TILE
PLAYER_SPEED = 4
PLAYER_SIZE = 26
WIN_RESOURCES = 6
RESOURCE_COUNT = 10
GAME_TIME = 120
SAFE_ZONE_START_RADIUS = 440
SAFE_ZONE_MIN_RADIUS = 90
SAFE_ZONE_SHRINK_SECONDS = 90
OUTSIDE_DAMAGE_PER_SECOND = 18

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("The Last Expedition")
clock = pygame.time.Clock()
font = pygame.font.Font(None, 28)
small_font = pygame.font.Font(None, 20)
big_font = pygame.font.Font(None, 48)

BACKGROUND = (20, 30, 50)
GRID_COLOR = (35, 47, 67)
WALL_COLOR = (100, 115, 135)
WHITE = (255, 255, 255)
BLUE = (0, 190, 255)
GREEN = (50, 220, 120)
GOLD = (255, 200, 50)
RED = (255, 90, 100)
ORANGE = (255, 150, 60)
PURPLE = (190, 120, 255)
SAFE_COLOR = (60, 220, 160)

START = (1, 1)
EXIT_CELL = (18, 13)
wall_rects = [
    pygame.Rect(160, 40, 40, 240),
    pygame.Rect(280, 160, 40, 240),
    pygame.Rect(400, 40, 40, 240),
    pygame.Rect(520, 200, 40, 240),
    pygame.Rect(640, 40, 40, 240),
    pygame.Rect(160, 360, 120, 40),
    pygame.Rect(360, 440, 120, 40),
]


def cell_center(cell):
    return (cell[0] * TILE + TILE // 2, cell[1] * TILE + TILE // 2)


def cell_rect(cell):
    return pygame.Rect(cell[0] * TILE, cell[1] * TILE, TILE, TILE)


def build_wall_cells():
    blocked = set()
    for wall in wall_rects:
        left = wall.left // TILE
        right = (wall.right - 1) // TILE
        top = wall.top // TILE
        bottom = (wall.bottom - 1) // TILE
        for x in range(left, right + 1):
            for y in range(top, bottom + 1):
                blocked.add((x, y))
    return blocked


WALLS = build_wall_cells()


def neighbors(cell):
    x, y = cell
    for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
        if 0 <= nxt[0] < COLS and 0 <= nxt[1] < ROWS and nxt not in WALLS:
            yield nxt


def bfs_path(start, goal):
    if start in WALLS or goal in WALLS:
        return []
    queue = deque([start])
    previous = {start: None}
    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for nxt in neighbors(current):
            if nxt not in previous:
                previous[nxt] = current
                queue.append(nxt)
    if goal not in previous:
        return []
    path = []
    current = goal
    while current is not None:
        path.append(current)
        current = previous[current]
    return list(reversed(path))


class Explorer:
    def __init__(self, name, cell, color, role):
        self.name = name
        self.x, self.y = cell_center(cell)
        self.color = color
        self.role = role
        self.resources = 0
        self.move_timer = 0.0

    def rect(self):
        return pygame.Rect(int(self.x - 12), int(self.y - 12), 24, 24)

    def cell(self):
        return (int(self.x // TILE), int(self.y // TILE))


def reset_game():
    global player, rivals, resources, state, player_supplies
    global health, time_left, game_start_time, outside_time, warning_played

    player = pygame.Rect(65, 65, PLAYER_SIZE, PLAYER_SIZE)
    rivals = [
        Explorer("Collector", (18, 1), ORANGE, "collector"),
        Explorer("Cautious", (1, 13), PURPLE, "cautious"),
    ]
    resources = set()
    occupied = set(WALLS) | {START, EXIT_CELL}
    occupied.update(rival.cell() for rival in rivals)
    while len(resources) < RESOURCE_COUNT:
        cell = (random.randrange(1, COLS - 1), random.randrange(1, ROWS - 1))
        if cell not in occupied:
            resources.add(cell)
            occupied.add(cell)
    player_supplies = 0
    health = 100.0
    time_left = float(GAME_TIME)
    game_start_time = pygame.time.get_ticks() / 1000.0
    outside_time = 0.0
    warning_played = False
    state = "playing"


def player_cell():
    return (int(player.centerx // TILE), int(player.centery // TILE))


def move_player(dx, dy):
    # Separate axis movement prevents walking through walls.
    player.x += dx
    for wall in wall_rects:
        if player.colliderect(wall):
            if dx > 0:
                player.right = wall.left
            elif dx < 0:
                player.left = wall.right
    player.y += dy
    for wall in wall_rects:
        if player.colliderect(wall):
            if dy > 0:
                player.bottom = wall.top
            elif dy < 0:
                player.top = wall.bottom
    player.clamp_ip(screen.get_rect())


def update_rivals(dt):
    for rival in rivals:
        rival.move_timer += dt
        if rival.move_timer < 0.38:  # slower rival movement for fairer gameplay
            continue
        rival.move_timer = 0.0
        start = rival.cell()
        if resources:
            if rival.role == "collector":
                choices = [(len(bfs_path(start, target)), target) for target in resources]
                choices = [item for item in choices if item[0] > 1]
                target = min(choices)[1] if choices else EXIT_CELL
            else:
                pc = player_cell()
                target = max(resources, key=lambda c: abs(c[0] - pc[0]) + abs(c[1] - pc[1]))
        else:
            target = EXIT_CELL
        path = bfs_path(start, target)
        if len(path) > 1:
            next_cell = path[1]
            rival.x, rival.y = cell_center(next_cell)
            if next_cell in resources:
                resources.remove(next_cell)
                rival.resources += 1


def collect_player_resources():
    global player_supplies
    cell = player_cell()
    if cell in resources:
        resources.remove(cell)
        player_supplies += 1
        play_sound("collect")


def safe_zone_radius(elapsed):
    progress = min(1.0, max(0.0, elapsed / SAFE_ZONE_SHRINK_SECONDS))
    return SAFE_ZONE_START_RADIUS - progress * (SAFE_ZONE_START_RADIUS - SAFE_ZONE_MIN_RADIUS)


def update_survival(dt):
    global health, time_left, state, outside_time, warning_played
    elapsed = pygame.time.get_ticks() / 1000.0 - game_start_time
    time_left = max(0.0, GAME_TIME - elapsed)
    radius = safe_zone_radius(elapsed)
    safe_center = (WIDTH // 2, HEIGHT // 2)
    distance = math.hypot(player.centerx - safe_center[0], player.centery - safe_center[1])
    if distance > radius:
        outside_time += dt
        health -= OUTSIDE_DAMAGE_PER_SECOND * dt
    else:
        outside_time = max(0.0, outside_time - dt * 2)
    health = max(0.0, health)
    if health <= 30 and not warning_played:
        play_sound("warning")
        warning_played = True
    if health > 35:
        warning_played = False
    if health <= 0 or time_left <= 0:
        state = "lost"


def draw_bar(x, y, width, height, value, max_value, color):
    pygame.draw.rect(screen, (60, 65, 80), (x, y, width, height), border_radius=4)
    fill_width = int(width * max(0.0, min(1.0, value / max_value)))
    if fill_width > 0:
        pygame.draw.rect(screen, color, (x, y, fill_width, height), border_radius=4)
    pygame.draw.rect(screen, WHITE, (x, y, width, height), 1, border_radius=4)


def draw():
    elapsed = pygame.time.get_ticks() / 1000.0 - game_start_time
    radius = safe_zone_radius(elapsed)
    safe_center = (WIDTH // 2, HEIGHT // 2)
    screen.fill(BACKGROUND)

    for x in range(0, WIDTH, TILE):
        pygame.draw.line(screen, GRID_COLOR, (x, 0), (x, HEIGHT))
    for y in range(0, HEIGHT, TILE):
        pygame.draw.line(screen, GRID_COLOR, (0, y), (WIDTH, y))

    # Safe zone ring
    pygame.draw.circle(screen, SAFE_COLOR, safe_center, int(radius), 2)

    for wall in wall_rects:
        pygame.draw.rect(screen, WALL_COLOR, wall, border_radius=4)
        pygame.draw.rect(screen, WHITE, wall, 1, border_radius=4)

    for cell in resources:
        pygame.draw.rect(screen, GOLD, cell_rect(cell).inflate(-14, -14), border_radius=5)

    exit_rect = cell_rect(EXIT_CELL).inflate(-3, -3)
    pygame.draw.rect(screen, GREEN, exit_rect, border_radius=5)
    exit_label = small_font.render("EXIT", True, (10, 40, 20))
    screen.blit(exit_label, exit_label.get_rect(center=exit_rect.center))

    for rival in rivals:
        pygame.draw.rect(screen, rival.color, rival.rect(), border_radius=5)
        label = small_font.render(rival.name, True, WHITE)
        screen.blit(label, (int(rival.x - label.get_width() / 2), int(rival.y - 25)))

    pygame.draw.rect(screen, BLUE, player, border_radius=5)

    # HUD panel
    pygame.draw.rect(screen, (12, 20, 38), (0, 0, WIDTH, 58))
    screen.blit(font.render("THE LAST EXPEDITION", True, WHITE), (10, 5))
    screen.blit(small_font.render(f"Supplies: {player_supplies}/{WIN_RESOURCES}", True, GOLD), (10, 34))
    screen.blit(small_font.render(f"Time: {int(time_left):03d}s", True, WHITE), (205, 35))
    screen.blit(small_font.render("Health", True, WHITE), (315, 35))
    draw_bar(370, 36, 120, 16, health, 100, GREEN if health > 35 else RED)
    screen.blit(small_font.render(f"Zone: {int(radius)}", True, SAFE_COLOR), (510, 35))
    sound_label = "ON" if SOUND_ENABLED else "OFF"
    screen.blit(small_font.render(f"Sound: {sound_label} (V)", True, WHITE), (10, HEIGHT - 44))
    screen.blit(small_font.render("WASD/arrows: move | ESC: quit", True, WHITE), (10, HEIGHT - 24))
    rival_status = "  ".join(f"{r.name}: {r.resources}" for r in rivals)
    screen.blit(small_font.render(rival_status, True, WHITE), (400, HEIGHT - 24))

    if state in ("won", "lost"):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))
        title = "EXPEDITION COMPLETE!" if state == "won" else "EXPEDITION FAILED"
        color = GREEN if state == "won" else RED
        title_img = big_font.render(title, True, color)
        screen.blit(title_img, title_img.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 30)))
        if state == "lost":
            reason = "Your health ran out or time expired."
            reason_img = small_font.render(reason, True, WHITE)
            screen.blit(reason_img, reason_img.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 5)))
        hint = font.render("R: restart   M: title menu   ESC: quit", True, WHITE)
        screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 35)))

    pygame.display.flip()


# Title screen state and menu buttons
state = "menu"
MENU_START_RECT = pygame.Rect(WIDTH // 2 - 120, 330, 240, 56)
MENU_HELP_RECT = pygame.Rect(WIDTH // 2 - 120, 400, 240, 48)
show_controls = False
warning_played = False

# Decorative stars are generated once so they stay still on the title screen.
random.seed()
stars = [(random.randrange(30, WIDTH - 30), random.randrange(30, HEIGHT - 30),
          random.choice((1, 1, 2))) for _ in range(70)]

def draw_title_screen():
    screen.fill((8, 16, 32))

    # Subtle night-sky stars.
    for sx, sy, size in stars:
        pygame.draw.circle(screen, (95, 125, 160), (sx, sy), size)

    # Distant mountain silhouettes and a dark foreground.
    pygame.draw.polygon(screen, (19, 38, 57), [(0, 270), (130, 145), (235, 260),
                         (355, 125), (500, 265), (635, 160), (800, 275), (800, 600), (0, 600)])
    pygame.draw.polygon(screen, (12, 27, 43), [(0, 370), (155, 280), (290, 380),
                         (455, 295), (610, 385), (735, 300), (800, 345), (800, 600), (0, 600)])

    # Expedition emblem.
    emblem_center = (WIDTH // 2, 170)
    pygame.draw.circle(screen, (38, 76, 92), emblem_center, 48, 3)
    pygame.draw.circle(screen, SAFE_COLOR, emblem_center, 35, 2)
    pygame.draw.polygon(screen, GOLD, [(emblem_center[0], 137), (emblem_center[0] - 12, 181),
                         (emblem_center[0], 172), (emblem_center[0] + 12, 181)])

    title_font = pygame.font.Font(None, 58)
    subtitle_font = pygame.font.Font(None, 25)
    title = title_font.render("THE LAST EXPEDITION", True, WHITE)
    screen.blit(title, title.get_rect(center=(WIDTH // 2, 235)))
    subtitle = subtitle_font.render("SCAVENGE. SURVIVE. EXTRACT.", True, SAFE_COLOR)
    screen.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 275)))

    mouse_pos = pygame.mouse.get_pos()
    start_hover = MENU_START_RECT.collidepoint(mouse_pos)
    start_color = (57, 175, 132) if start_hover else (35, 125, 104)
    pygame.draw.rect(screen, start_color, MENU_START_RECT, border_radius=10)
    pygame.draw.rect(screen, (130, 245, 195), MENU_START_RECT, 2, border_radius=10)
    start_text = font.render("START EXPEDITION", True, WHITE)
    screen.blit(start_text, start_text.get_rect(center=MENU_START_RECT.center))

    help_hover = MENU_HELP_RECT.collidepoint(mouse_pos)
    help_color = (49, 68, 91) if help_hover else (30, 45, 65)
    pygame.draw.rect(screen, help_color, MENU_HELP_RECT, border_radius=9)
    pygame.draw.rect(screen, (100, 130, 160), MENU_HELP_RECT, 1, border_radius=9)
    help_text = small_font.render("HOW TO PLAY", True, WHITE)
    screen.blit(help_text, help_text.get_rect(center=MENU_HELP_RECT.center))

    if show_controls:
        panel = pygame.Rect(WIDTH // 2 - 230, 465, 460, 85)
        pygame.draw.rect(screen, (7, 16, 29), panel, border_radius=8)
        pygame.draw.rect(screen, (70, 110, 130), panel, 1, border_radius=8)
        lines = ["Move: WASD or arrow keys", "Collect 6 supplies, then reach the green EXIT.",
                 "Stay inside the shrinking ring; outside it drains health."]
        for i, line in enumerate(lines):
            img = small_font.render(line, True, WHITE)
            screen.blit(img, img.get_rect(center=(WIDTH // 2, 480 + i * 22)))

    footer = small_font.render(f"A survival adventure  |  Sound: {'ON' if SOUND_ENABLED else 'OFF'} (V to toggle)", True, (140, 160, 185))
    screen.blit(footer, footer.get_rect(center=(WIDTH // 2, HEIGHT - 20)))
    pygame.display.flip()

running = True
while running:
    dt = clock.tick(60) / 1000.0
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                if state == "menu":
                    running = False
                else:
                    running = False
            elif event.key == pygame.K_v:
                set_sound_enabled(not SOUND_ENABLED)
            elif state == "menu" and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                reset_game()
            elif state == "menu" and event.key == pygame.K_h:
                show_controls = not show_controls
            elif event.key == pygame.K_r and state in ("won", "lost"):
                reset_game()
            elif event.key == pygame.K_m and state in ("won", "lost"):
                state = "menu"
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1 and state == "menu":
            if MENU_START_RECT.collidepoint(event.pos):
                reset_game()
            elif MENU_HELP_RECT.collidepoint(event.pos):
                show_controls = not show_controls

    if state == "menu":
        draw_title_screen()
        continue

    if state == "playing":
        keys = pygame.key.get_pressed()
        dx = int(bool(keys[pygame.K_RIGHT] or keys[pygame.K_d])) - int(bool(keys[pygame.K_LEFT] or keys[pygame.K_a]))
        dy = int(bool(keys[pygame.K_DOWN] or keys[pygame.K_s])) - int(bool(keys[pygame.K_UP] or keys[pygame.K_w]))
        # Normalize diagonal movement so it isn't faster.
        if dx and dy:
            scale = 0.7071
        else:
            scale = 1.0
        move_player(int(dx * PLAYER_SPEED * scale), int(dy * PLAYER_SPEED * scale))
        collect_player_resources()
        update_rivals(dt)
        update_survival(dt)
        if player_supplies >= WIN_RESOURCES and player.colliderect(cell_rect(EXIT_CELL)):
            state = "won"
            play_sound("victory")
        elif state == "lost":
            play_sound("defeat")

    draw()

if AUDIO_AVAILABLE:
    try:
        pygame.mixer.music.stop()
        pygame.mixer.quit()
    except pygame.error:
        pass
pygame.quit()
