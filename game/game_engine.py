import pygame
from .player import Player
from .obstacle import Obstacle

# Game Engine

WHITE = (255, 255, 255)
BROWN = (120, 80, 40)
DARK_GREEN = (30, 100, 30)

class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.ground_y = height - 40

        self.player = Player(80, self.ground_y)

        self.speed = 6
        self.speed_increase_per_frame = 0.003
        self.max_speed = 12

        self.spawn_interval = 70  # frames between obstacle spawns
        self._spawn_timer = 0
        self.obstacles = []

        self.distance = 0
        self.score = 0
        self.font = pygame.font.SysFont("Arial", 30)
        self.title_font = pygame.font.SysFont("Arial", 48, bold=True)
        self.game_over = False
        self._game_over_logged = False
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key in (pygame.K_SPACE, pygame.K_UP, pygame.K_w):
            self.player.jump()

    def handle_input(self):
        # Reserved for continuously-held-key input; this runner only
        # needs an edge-triggered jump, handled in handle_event.
        pass

    def update(self):
        if self.game_over:
            return

        self.speed = min(
        self.speed + self.speed_increase_per_frame,
        self.max_speed
        )
        self.player.update()

        self._spawn_timer += 1
        if self._spawn_timer >= self.spawn_interval:
            self._spawn_timer = 0
            self.obstacles.append(Obstacle(self.width, self.ground_y, self.speed))

        previous_positions = {}

        for obstacle in self.obstacles:
            previous_positions[id(obstacle)] = obstacle.x
            obstacle.speed = self.speed
            obstacle.move()

        # NOTE: collision is only checked against each obstacle's rect
        # *after* it has already moved for the frame. There's no check
        # for whether the obstacle's path crossed the player along the
        # way. Since self.speed has no cap, it eventually grows large
        # enough that an obstacle can cover more horizontal distance
        # in one frame than the player's own width - meaning it can be
        # entirely to the right of the player on one frame and entirely
        # to the left on the next, skipping the player's hitbox
        # completely and never registering a hit. See Task 1.
        player_rect = self.player.rect()

        for obstacle in self.obstacles:
            previous_x = previous_positions[id(obstacle)]

            left = min(previous_x, obstacle.x)
            travelled = abs(obstacle.x - previous_x)

            swept_rect = pygame.Rect(
                int(left),
                obstacle.y,
                obstacle.width + int(travelled) + 1,
                obstacle.height
            )

            if swept_rect.colliderect(player_rect):
                self.game_over = True
                return
        for obstacle in self.obstacles:
            if not obstacle.scored and obstacle.x + obstacle.width < self.player.x:
                obstacle.scored = True
                self.score += 1

        self.obstacles = [o for o in self.obstacles if not o.off_screen()]

        self.distance += self.speed
    
    def render(self, screen):
        pygame.draw.line(
            screen, BROWN,
            (0, self.ground_y),
            (self.width, self.ground_y), 4
        )

        pygame.draw.rect(screen, WHITE, self.player.rect())

        for obstacle in self.obstacles:
            pygame.draw.rect(screen, DARK_GREEN, obstacle.rect())

        # Display current score
        score_text = self.font.render(
            f"Score: {self.score}", True, (0, 0, 0)
        )
        screen.blit(score_text, (10, 10))

        # Game Over screen
        if self.game_over:
            # Dark transparent overlay
            overlay = pygame.Surface(
                (self.width, self.height),
                pygame.SRCALPHA
            )
            overlay.fill((0, 0, 0, 170))
            screen.blit(overlay, (0, 0))

            # Game Over title
            title = self.title_font.render(
                "GAME OVER", True, (255, 60, 60)
            )
            title_rect = title.get_rect(
                center=(self.width // 2, self.height // 2 - 50)
            )
            screen.blit(title, title_rect)

            # Final score
            final_score = self.font.render(
                f"Final Score: {self.score}",
                True, (255, 255, 255)
            )
            score_rect = final_score.get_rect(
                center=(self.width // 2, self.height // 2 + 10)
            )
            screen.blit(final_score, score_rect)

            # Exit message
            message = pygame.font.SysFont("Arial", 20).render(
                "Close the window to exit",
                True, (255, 255, 255)
            )
            message_rect = message.get_rect(
                center=(self.width // 2, self.height // 2 + 55)
            )
            screen.blit(message, message_rect)

    