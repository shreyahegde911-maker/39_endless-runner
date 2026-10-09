
import io
import math
import struct
import wave
import pygame

from .player import Player
from .obstacle import Obstacle


# ---------- COLOURS ----------
BACKGROUND = (189, 235, 255)
GROUND_GREEN = (35, 134, 54)
PLAYER_BLUE = (21, 94, 239)
OBSTACLE_ORANGE = (249, 115, 22)
TEXT_DARK = (25, 40, 65)
WHITE = (255, 255, 255)
RED = (255, 85, 85)
DARK_OVERLAY = (15, 25, 45, 220)


class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.ground_y = height - 40

        # Starting speed and obstacle spawn interval
        self.difficulties = {
            "Easy": (4, 90),
            "Medium": (6, 70),
            "Hard": (8, 50),
        }

        self.difficulty = "Medium"

        self.font = pygame.font.SysFont("Arial", 28, bold=True)
        self.title_font = pygame.font.SysFont(
            "Arial", 46, bold=True
        )
        self.small_font = pygame.font.SysFont("Arial", 21)

        self.init_sounds()

        self.player = Player(80, self.ground_y)

        self.speed = 6
        self.speed_increase_per_frame = 0.003
        self.max_speed = 12

        self.spawn_interval = 70
        self._spawn_timer = 0
        self.obstacles = []

        self.distance = 0
        self.score = 0
        self.game_over = False

    # ---------- SOUND EFFECTS ----------

    def init_sounds(self):
        self.sounds = {}

        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()

            self.sounds["jump"] = self.create_tone(550, 0.10)
            self.sounds["score"] = self.create_tone(850, 0.12)
            self.sounds["game_over"] = self.create_tone(180, 0.30)

        except (pygame.error, OSError):
            # The game remains playable without sound.
            self.sounds = {}

    def create_tone(self, frequency, duration):
        sample_rate = 22050
        amplitude = 9000
        count = int(sample_rate * duration)
        samples = bytearray()

        for i in range(count):
            fade = max(
                0.0,
                min(1.0, i / 300, (count - i) / 500)
            )

            value = int(
                amplitude
                * fade
                * math.sin(
                    2 * math.pi * frequency * i / sample_rate
                )
            )

            samples.extend(struct.pack("<h", value))

        buffer = io.BytesIO()

        with wave.open(buffer, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)
            wav.writeframes(bytes(samples))

        buffer.seek(0)
        return pygame.mixer.Sound(file=buffer)

    def play_sound(self, name):
        sound = self.sounds.get(name)

        if sound is not None:
            try:
                sound.play()
            except pygame.error:
                pass

    # ---------- RESTART GAME ----------

    def reset_game(self, difficulty):
        self.difficulty = difficulty

        self.speed, self.spawn_interval = (
            self.difficulties[difficulty]
        )

        self.player = Player(80, self.ground_y)
        self._spawn_timer = 0
        self.obstacles = []
        self.distance = 0
        self.score = 0
        self.game_over = False

    # ---------- KEYBOARD CONTROLS ----------

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if self.game_over:
            if event.key == pygame.K_1:
                self.reset_game("Easy")
            elif event.key == pygame.K_2:
                self.reset_game("Medium")
            elif event.key == pygame.K_3:
                self.reset_game("Hard")
            elif event.key in (pygame.K_4, pygame.K_ESCAPE):
                pygame.event.post(
                    pygame.event.Event(pygame.QUIT)
                )

            return

        if event.key in (
            pygame.K_SPACE,
            pygame.K_UP,
            pygame.K_w,
        ):
            if self.player.on_ground:
                self.player.jump()
                self.play_sound("jump")

    def handle_input(self):
        pass

    # ---------- UPDATE GAME ----------

    def update(self):
        if self.game_over:
            return

        # Increase speed gradually, with a maximum limit.
        self.speed = min(
            self.speed + self.speed_increase_per_frame,
            self.max_speed,
        )

        self.player.update()

        # Spawn obstacles at regular intervals.
        self._spawn_timer += 1

        if self._spawn_timer >= self.spawn_interval:
            self._spawn_timer = 0
            self.obstacles.append(
                Obstacle(self.width, self.ground_y, self.speed)
            )

        # Save positions before movement for collision checking.
        previous_positions = {}

        for obstacle in self.obstacles:
            previous_positions[id(obstacle)] = obstacle.x
            obstacle.speed = self.speed
            obstacle.move()

        player_rect = self.player.rect()

        # Swept collision detection prevents fast obstacles
        # from skipping over the player between frames.
        for obstacle in self.obstacles:
            previous_x = previous_positions[id(obstacle)]

            left = min(previous_x, obstacle.x)
            travelled = abs(obstacle.x - previous_x)

            swept_rect = pygame.Rect(
                int(left),
                obstacle.y,
                obstacle.width + int(travelled) + 1,
                obstacle.height,
            )

            if swept_rect.colliderect(player_rect):
                self.game_over = True
                self.play_sound("game_over")
                return

        # Award a point for each obstacle passed.
        for obstacle in self.obstacles:
            if (
                not obstacle.scored
                and obstacle.x + obstacle.width < self.player.x
            ):
                obstacle.scored = True
                self.score += 1
                self.play_sound("score")

        self.obstacles = [
            obstacle
            for obstacle in self.obstacles
            if not obstacle.off_screen()
        ]

        self.distance += self.speed

    # ---------- DRAW GAME ----------

    def render(self, screen):
        # Sky background
        screen.fill(BACKGROUND)

        # Ground
        pygame.draw.rect(
            screen,
            GROUND_GREEN,
            (0, self.ground_y, self.width,
             self.height - self.ground_y),
        )

        pygame.draw.line(
            screen,
            (25, 105, 45),
            (0, self.ground_y),
            (self.width, self.ground_y),
            3,
        )

        # Player
        pygame.draw.rect(
            screen,
            PLAYER_BLUE,
            self.player.rect(),
            border_radius=5,
        )

        # Obstacles
        for obstacle in self.obstacles:
            pygame.draw.rect(
                screen,
                OBSTACLE_ORANGE,
                obstacle.rect(),
                border_radius=5,
            )

        # Score panel
        score_panel = pygame.Surface((170, 48), pygame.SRCALPHA)
        score_panel.fill((255, 255, 255, 205))
        screen.blit(score_panel, (10, 10))

        score_text = self.font.render(
            f"Score: {self.score}",
            True,
            TEXT_DARK,
        )
        screen.blit(score_text, (20, 17))

        # Game Over screen and replay menu
        if self.game_over:
            overlay = pygame.Surface(
                (self.width, self.height),
                pygame.SRCALPHA,
            )
            overlay.fill(DARK_OVERLAY)
            screen.blit(overlay, (0, 0))

            title = self.title_font.render(
                "GAME OVER", True, RED
            )
            screen.blit(
                title,
                title.get_rect(
                    center=(
                        self.width // 2,
                        self.height // 2 - 105,
                    )
                ),
            )

            final_score = self.font.render(
                f"Final Score: {self.score}",
                True,
                WHITE,
            )
            screen.blit(
                final_score,
                final_score.get_rect(
                    center=(
                        self.width // 2,
                        self.height // 2 - 50,
                    )
                ),
            )

            message = self.small_font.render(
                "Choose your difficulty",
                True,
                WHITE,
            )
            screen.blit(
                message,
                message.get_rect(
                    center=(
                        self.width // 2,
                        self.height // 2 - 10,
                    )
                ),
            )

            options = [
                ("1  -  EASY", (100, 255, 150)),
                ("2  -  MEDIUM", (120, 200, 255)),
                ("3  -  HARD", (255, 150, 100)),
                ("4  -  EXIT", WHITE),
            ]

            for i, (label, color) in enumerate(options):
                option = self.small_font.render(
                    label, True, color
                )

                screen.blit(
                    option,
                    option.get_rect(
                        center=(
                            self.width // 2,
                            self.height // 2 + 30 + i * 32,
                        )
                    ),
                )
