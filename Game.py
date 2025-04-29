# -*- coding: utf-8 -*-
#Created on Tue Apr 29 2025


# Import
import pygame
import random
import time
import os
import math
from enum import Enum

# Initialize pygame and mixer
try:
    pygame.init()
    pygame.mixer.init()
except pygame.error as e:
    print(f"Pygame initialization failed: {e}")
    exit(1)

# Game window setup
WIDTH = 800
HEIGHT = 600
try:
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Simple Game")
except pygame.error as e:
    print(f"Failed to set up display: {e}")
    exit(1)

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (70, 248, 160)
GRAY = (210, 210, 210)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
BROWN = (139, 69, 19)

# Configuration constants
CONFIG = {
    'ROAD_WIDTH': 350,
    'ROAD_X': (WIDTH - 350) // 2,
    'MARKER_WIDTH': 10,
    'MARKER_HEIGHT': 50,
    'CAR_WIDTH': 40,
    'CAR_HEIGHT': 100,
    'MAX_SPEED': 15,
    'ACCELERATION': 0.20,
    'DECELERATION': 0.05,
    'TURN_SPEED': 0.3,
    'TREE_WIDTH': 80,
    'TREE_HEIGHT': 80,
    'FLAG_WIDTH': 40,
    'FLAG_HEIGHT': 80,
    'BARRIER_WIDTH': 80,
    'BARRIER_HEIGHT': 50,
    'PERSON_WIDTH': 30,
    'PERSON_HEIGHT': 90,
    'FPS': 60,
    'OPPONENT_MIN_INTERVAL': 1,
    'OPPONENT_MAX_INTERVAL': 2.0,
}

# Game clock
clock = pygame.time.Clock()

# Object types
class ObjectType(Enum):
    TREE = "tree"
    FLAG = "flag"
    BARRIER = "barrier"
    PERSON = "person"

def load_image(name, size, angle=0, colorkey=None):
    """Load image with placeholder fallback."""
    try:
        image = pygame.image.load(name).convert_alpha()
        image = pygame.transform.scale(image, size)
        if colorkey is not None:
            image.set_colorkey(colorkey)
        return image if angle == 0 else pygame.transform.rotate(image, angle)
    except pygame.error as e:
        print(f"Failed to load image {name}: {e}")
        surf = pygame.Surface(size, pygame.SRCALPHA)
        if "tree" in name:
            pygame.draw.rect(surf, BROWN, (size[0]//3, size[1]//2, size[0]//3, size[1]//2))
            pygame.draw.polygon(surf, GREEN, [(0, size[1]//2), (size[0], size[1]//2), (size[0]//2, 0)])
        elif "flag" in name:
            pygame.draw.rect(surf, BROWN, (size[0]//2-2, 0, 4, size[1]))
            pygame.draw.polygon(surf, RED, [(size[0]//2, 10), (size[0], 25), (size[0]//2, 40)])
        elif "barrier" in name:
            pygame.draw.rect(surf, YELLOW, (0, 0, size[0], size[1]))
            pygame.draw.rect(surf, BLACK, (0, 0, size[0], size[1]), 2)
        elif "person" in name:
            pygame.draw.ellipse(surf, (200, 150, 150), (0, 0, size[0], size[0]))
            pygame.draw.rect(surf, BLUE, (size[0]//4, size[0], size[0]//2, size[1]-size[0]))
        elif "car1" in name:
            surf.fill(BLUE)
        else:
            surf.fill(RED)
        return surf if angle == 0 else pygame.transform.rotate(surf, angle)

def load_sound(name):
    """Load sound with silent fallback."""
    try:
        return pygame.mixer.Sound(name)
    except pygame.error as e:
        print(f"Failed to load sound {name}: {e}")
        return pygame.mixer.Sound(buffer=bytearray(0))

# Load assets with error handling
try:
    player_car_img = load_image("car.png", (CONFIG['CAR_WIDTH'], CONFIG['CAR_HEIGHT']))
    opponent_car_img = load_image("car1.png", (CONFIG['CAR_WIDTH'], CONFIG['CAR_HEIGHT']), 180)
    tree_img = load_image("tree.png", (CONFIG['TREE_WIDTH'], CONFIG['TREE_HEIGHT']))
    flag_img = load_image("flag.png", (CONFIG['FLAG_WIDTH'], CONFIG['FLAG_HEIGHT']))
    barrier_img = load_image("barrier.png", (CONFIG['BARRIER_WIDTH'], CONFIG['BARRIER_HEIGHT']))
    person_img = load_image("person.png", (CONFIG['PERSON_WIDTH'], CONFIG['PERSON_HEIGHT']))
except Exception as e:
    print(f"Failed to load one or more images: {e}")
    exit(1)

# Load sounds
engine_sound = load_sound("engine.mp3")
crash_sound = load_sound("crash.mp3")
score_sound = load_sound("score.mp3")

# Configure audio
engine_sound.set_volume(0.3)
crash_sound.set_volume(0.7)
score_sound.set_volume(0.5)

class Car:
    def __init__(self, x, y, img, max_speed, is_player=False):
        self.x = x
        self.y = y
        self.img = img
        self.max_speed = maxFuel = max_speed
        self.speed = 0
        self.angle = 0
        self.target_angle = 0
        self.is_player = is_player
        self.width = img.get_width()
        self.height = img.get_height()
        self.current_img = img
        self._image_cache = {}

    def draw(self, surface):
        angle = round(self.angle, 1)
        if angle not in self._image_cache:
            self._image_cache[angle] = pygame.transform.rotate(self.img, angle) if abs(angle) > 1 else self.img
        self.current_img = self._image_cache[angle]
        rect = self.current_img.get_rect(center=(self.x + self.width//2, self.y + self.height//2))
        surface.blit(self.current_img, rect.topleft)

    def move(self, direction=None):
        if self.is_player:
            if direction == "left":
                self.target_angle = 15
                self.x -= self.speed * CONFIG['TURN_SPEED']
            elif direction == "right":
                self.target_angle = -15
                self.x += self.speed * CONFIG['TURN_SPEED']
            else:
                self.target_angle = 0

            self.angle += (self.target_angle - self.angle) * 0.2
            self.x = max(CONFIG['ROAD_X'] + 20, min(CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - self.width - 20, self.x))

            if direction in ("left", "right"):
                self.speed = min(self.speed + CONFIG['ACCELERATION'], self.max_speed)
            else:
                self.speed = max(self.speed - CONFIG['DECELERATION'], 0)
        else:
            self.y += self.speed
            return self.y > HEIGHT

class EnvironmentObject:
    def __init__(self, x, y, img, obj_type):
        self.x = x
        self.y = y
        self.img = img
        self.type = obj_type
        self.width = img.get_width()
        self.height = img.get_height()

    def draw(self, surface):
        surface.blit(self.img, (self.x, self.y))

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)

class Game:
    def __init__(self):
        self.player = Car(WIDTH // 2 - CONFIG['CAR_WIDTH'] // 2, HEIGHT - 150, player_car_img, CONFIG['MAX_SPEED'], True)
        self.opponents = []
        self.environment = []
        self.score = 0
        self.game_over = False
        self.last_opponent_time = time.time()
        self.opponent_interval = CONFIG['OPPONENT_MAX_INTERVAL']
        self.start_time = time.time()
        self.engine_sound_played = False
        self.setup_environment()

    def check_overlap(self, new_obj, existing_objs, max_retries=50):
        """Check if new object overlaps with existing objects, with retry limit."""
        new_rect = pygame.Rect(new_obj.x, new_obj.y, new_obj.width, new_obj.height)
        for obj in existing_objs:
            if new_rect.colliderect(obj.get_rect()):
                return True
        return False

    def setup_environment(self):
        # Place trees and flags without overlap
        side_objects = []
        for _ in range(8):
            retries = 0
            while retries < 50:
                y = random.randint(-HEIGHT, HEIGHT * 2)
                side = random.choice(["left", "right"])
                x = (CONFIG['ROAD_X'] - CONFIG['TREE_WIDTH'] - random.randint(10, 50)) if side == "left" else \
                    (CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] + random.randint(10, 50))
                tree = EnvironmentObject(x, y, tree_img, ObjectType.TREE)
                if not self.check_overlap(tree, side_objects):
                    side_objects.append(tree)
                    self.environment.append(tree)
                    break
                retries += 1
            if retries >= 50:
                print("Warning: Could not place tree without overlap")

        for _ in range(6):
            retries = 0
            while retries < 50:
                y = random.randint(-HEIGHT, HEIGHT * 2)
                side = random.choice(["left", "right"])
                x = (CONFIG['ROAD_X'] - CONFIG['FLAG_WIDTH'] - random.randint(5, 30)) if side == "left" else \
                    (CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] + random.randint(5, 30))
                flag = EnvironmentObject(x, y, flag_img, ObjectType.FLAG)
                if not self.check_overlap(flag, side_objects):
                    side_objects.append(flag)
                    self.environment.append(flag)
                    break
                retries += 1
            if retries >= 50:
                print("Warning: Could not place flag without overlap")

        # Place barriers (rarer)
        for _ in range(4):
            x = random.randint(CONFIG['ROAD_X'] + 20, CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - CONFIG['BARRIER_WIDTH'] - 20)
            y = random.randint(-HEIGHT, HEIGHT * 2)
            self.environment.append(EnvironmentObject(x, y, barrier_img, ObjectType.BARRIER))

        # Place people
        for _ in range(4):
            if random.random() > 0.5:
                x = random.randint(CONFIG['ROAD_X'] + 20, CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - CONFIG['PERSON_WIDTH'] - 20)
                y = random.randint(-HEIGHT, HEIGHT * 2)
                self.environment.append(EnvironmentObject(x, y, person_img, ObjectType.PERSON))

    def draw_road(self):
        screen.fill(GREEN)
        pygame.draw.rect(screen, GRAY, (CONFIG['ROAD_X'], 0, CONFIG['ROAD_WIDTH'], HEIGHT))
        marker_y = (self.player.speed * 10) % (CONFIG['MARKER_HEIGHT'] * 2)
        while marker_y < HEIGHT:
            pygame.draw.rect(screen, WHITE, (WIDTH // 2 - CONFIG['MARKER_WIDTH'] // 2, marker_y, CONFIG['MARKER_WIDTH'], CONFIG['MARKER_HEIGHT']))
            marker_y += CONFIG['MARKER_HEIGHT'] * 2

    def add_opponent(self):
        current_time = time.time()
        if current_time - self.last_opponent_time > self.opponent_interval:
            x = random.randint(CONFIG['ROAD_X'] + 50, CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - CONFIG['CAR_WIDTH'] - 50)
            speed = random.uniform(2, 5) + self.score / 300
            self.opponents.append(Car(x, -CONFIG['CAR_HEIGHT'], opponent_car_img, speed))
            self.last_opponent_time = current_time
            self.opponent_interval = max(CONFIG['OPPONENT_MIN_INTERVAL'], CONFIG['OPPONENT_MAX_INTERVAL'] - self.score / 300)

    def check_collisions(self):
        player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)

        for opponent in self.opponents:
            if player_rect.colliderect(pygame.Rect(opponent.x, opponent.y, opponent.width, opponent.height)):
                self.game_over = True
                return

        for obj in self.environment:
            if player_rect.colliderect(obj.get_rect()):
                if obj.type == ObjectType.BARRIER:
                    self.score += 100
                    score_sound.play()
                    obj.y = -HEIGHT - obj.height
                elif obj.type == ObjectType.PERSON:
                    crash_sound.play()
                    self.game_over = True
                    return

    def update(self):
        if not self.game_over:
            if not self.engine_sound_played and time.time() - self.start_time >= 5:
                try:
                    engine_sound.play(-1)
                    self.engine_sound_played = True
                except pygame.error as e:
                    print(f"Failed to play engine sound: {e}")

            self.add_opponent()
            self.opponents = [opponent for opponent in self.opponents if not opponent.move()]

            for obj in self.environment:
                obj.y += self.player.speed * 0.5
                if obj.y > HEIGHT:
                    if obj.type == ObjectType.TREE:
                        retries = 0
                        while retries < 50:
                            side = random.choice(["left", "right"])
                            x = (CONFIG['ROAD_X'] - CONFIG['TREE_WIDTH'] - random.randint(10, 50)) if side == "left" else \
                                (CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] + random.randint(10, 50))
                            obj.x = x
                            obj.y = -obj.height - random.randint(0, 100)
                            if not self.check_overlap(obj, [o for o in self.environment if o.type in [ObjectType.TREE, ObjectType.FLAG]]):
                                break
                            retries += 1
                        if retries >= 50:
                            obj.y = -obj.height - random.randint(0, 100)  # Fallback placement
                    elif obj.type == ObjectType.FLAG:
                        retries = 0
                        while retries < 50:
                            side = random.choice(["left", "right"])
                            x = (CONFIG['ROAD_X'] - CONFIG['FLAG_WIDTH'] - random.randint(5, 30)) if side == "left" else \
                                (CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] + random.randint(5, 30))
                            obj.x = x
                            obj.y = -obj.height - random.randint(0, 100)
                            if not self.check_overlap(obj, [o for o in self.environment if o.type in [ObjectType.TREE, ObjectType.FLAG]]):
                                break
                            retries += 1
                        if retries >= 50:
                            obj.y = -obj.height - random.randint(0, 100)  # Fallback placement
                    elif obj.type == ObjectType.BARRIER:
                        obj.x = random.randint(CONFIG['ROAD_X'] + 20, CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - CONFIG['BARRIER_WIDTH'] - 20)
                        obj.y = -obj.height - random.randint(0, 100)
                    elif obj.type == ObjectType.PERSON:
                        obj.x = random.randint(CONFIG['ROAD_X'] + 20, CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - CONFIG['PERSON_WIDTH'] - 20)
                        obj.y = -obj.height - random.randint(0, 100)

            self.check_collisions()

    def draw(self):
        self.draw_road()
        for obj in self.environment:
            obj.draw(screen)
        for opponent in self.opponents:
            opponent.draw(screen)
        self.player.draw(screen)

        font = pygame.font.SysFont(None, 36)
        score_text = font.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        speed_text = font.render(f"Speed: {int(self.player.speed * 10)}", True, WHITE)
        screen.blit(speed_text, (10, 50))

        if self.game_over:
            try:
                engine_sound.stop()
            except pygame.error as e:
                print(f"Failed to stop engine sound: {e}")
            font = pygame.font.SysFont(None, 100)
            game_over_text = font.render("GAME OVER", True, RED)
            screen.blit(game_over_text, (WIDTH // 2 - 150, HEIGHT // 5 - 50))
            restart_text = font.render("R-Restart/Q-Quit", True, RED)
            screen.blit(restart_text, (WIDTH // 2 - 220, HEIGHT // 2 + 50))

def main():
    game = Game()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if game.game_over:
                    if event.key == pygame.K_r:
                        game = Game()
                    elif event.key == pygame.K_q:
                        running = False
                elif event.key == pygame.K_m:
                    try:
                        engine_sound.set_volume(0 if engine_sound.get_volume() > 0 else 0.3)
                    except pygame.error as e:
                        print(f"Failed to toggle mute: {e}")

        if not game.game_over:
            keys = pygame.key.get_pressed()
            direction = None
            if keys[pygame.K_LEFT]:
                direction = "left"
            elif keys[pygame.K_RIGHT]:
                direction = "right"
            game.player.move(direction)

        game.update()
        game.draw()
        pygame.display.flip()
        clock.tick(CONFIG['FPS'])

    try:
        pygame.quit()
    except pygame.error as e:
        print(f"Failed to quit Pygame: {e}")

if __name__ == "__main__":
    main()

    def setup_environment(self):
        # Place trees and flags without overlap
        side_objects = []
        for _ in range(8):
            retries = 0
            while retries < 50:
                y = random.randint(-HEIGHT, HEIGHT * 2)
                side = random.choice(["left", "right"])
                x = (CONFIG['ROAD_X'] - CONFIG['TREE_WIDTH'] - random.randint(10, 50)) if side == "left" else \
                    (CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] + random.randint(10, 50))
                tree = EnvironmentObject(x, y, tree_img, ObjectType.TREE)
                if not self.check_overlap(tree, side_objects):
                    side_objects.append(tree)
                    self.environment.append(tree)
                    break
                retries += 1
            if retries >= 50:
                print("Warning: Could not place tree without overlap")

        for _ in range(6):
            retries = 0
            while retries < 50:
                y = random.randint(-HEIGHT, HEIGHT * 2)
                side = random.choice(["left", "right"])
                x = (CONFIG['ROAD_X'] - CONFIG['FLAG_WIDTH'] - random.randint(5, 30)) if side == "left" else \
                    (CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] + random.randint(5, 30))
                flag = EnvironmentObject(x, y, flag_img, ObjectType.FLAG)
                if not self.check_overlap(flag, side_objects):
                    side_objects.append(flag)
                    self.environment.append(flag)
                    break
                retries += 1
            if retries >= 50:
                print("Warning: Could not place flag without overlap")

        # Place barriers (rarer)
        for _ in range(4):
            x = random.randint(CONFIG['ROAD_X'] + 20, CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - CONFIG['BARRIER_WIDTH'] - 20)
            y = random.randint(-HEIGHT, HEIGHT * 2)
            self.environment.append(EnvironmentObject(x, y, barrier_img, ObjectType.BARRIER))

        # Place people
        for _ in range(4):
            if random.random() > 0.5:
                x = random.randint(CONFIG['ROAD_X'] + 20, CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - CONFIG['PERSON_WIDTH'] - 20)
                y = random.randint(-HEIGHT, HEIGHT * 2)
                self.environment.append(EnvironmentObject(x, y, person_img, ObjectType.PERSON))

    def draw_road(self):
        screen.fill(GREEN)
        pygame.draw.rect(screen, GRAY, (CONFIG['ROAD_X'], 0, CONFIG['ROAD_WIDTH'], HEIGHT))
        marker_y = (self.player.speed * 10) % (CONFIG['MARKER_HEIGHT'] * 2)
        while marker_y < HEIGHT:
            pygame.draw.rect(screen, WHITE, (WIDTH // 2 - CONFIG['MARKER_WIDTH'] // 2, marker_y, CONFIG['MARKER_WIDTH'], CONFIG['MARKER_HEIGHT']))
            marker_y += CONFIG['MARKER_HEIGHT'] * 2

    def add_opponent(self):
        current_time = time.time()
        if current_time - self.last_opponent_time > self.opponent_interval:
            x = random.randint(CONFIG['ROAD_X'] + 50, CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - CONFIG['CAR_WIDTH'] - 50)
            speed = random.uniform(2, 5) + self.score / 300
            self.opponents.append(Car(x, -CONFIG['CAR_HEIGHT'], opponent_car_img, speed))
            self.last_opponent_time = current_time
            self.opponent_interval = max(CONFIG['OPPONENT_MIN_INTERVAL'], CONFIG['OPPONENT_MAX_INTERVAL'] - self.score / 300)

    def check_collisions(self):
        player_rect = pygame.Rect(self.player.x, self.player.y, self.player.width, self.player.height)

        for opponent in self.opponents:
            if player_rect.colliderect(pygame.Rect(opponent.x, opponent.y, opponent.width, opponent.height)):
                self.game_over = True
                return

        for obj in self.environment:
            if player_rect.colliderect(obj.get_rect()):
                if obj.type == ObjectType.BARRIER:
                    self.score += 100
                    score_sound.play()
                    obj.y = -HEIGHT - obj.height
                elif obj.type == ObjectType.PERSON:
                    crash_sound.play()
                    self.game_over = True
                    return

    def update(self):
        if not self.game_over:
            if not self.engine_sound_played and time.time() - self.start_time >= 5:
                try:
                    engine_sound.play(-1)
                    self.engine_sound_played = True
                except pygame.error as e:
                    print(f"Failed to play engine sound: {e}")

            self.add_opponent()
            self.opponents = [opponent for opponent in self.opponents if not opponent.move()]

            for obj in self.environment:
                obj.y += self.player.speed * 0.5
                if obj.y > HEIGHT:
                    if obj.type == ObjectType.TREE:
                        retries = 0
                        while retries < 50:
                            side = random.choice(["left", "right"])
                            x = (CONFIG['ROAD_X'] - CONFIG['TREE_WIDTH'] - random.randint(10, 50)) if side == "left" else \
                                (CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] + random.randint(10, 50))
                            obj.x = x
                            obj.y = -obj.height - random.randint(0, 100)
                            if not self.check_overlap(obj, [o for o in self.environment if o.type in [ObjectType.TREE, ObjectType.FLAG]]):
                                break
                            retries += 1
                        if retries >= 50:
                            obj.y = -obj.height - random.randint(0, 100)  # Fallback placement
                    elif obj.type == ObjectType.FLAG:
                        retries = 0
                        while retries < 50:
                            side = random.choice(["left", "right"])
                            x = (CONFIG['ROAD_X'] - CONFIG['FLAG_WIDTH'] - random.randint(5, 30)) if side == "left" else \
                                (CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] + random.randint(5, 30))
                            obj.x = x
                            obj.y = -obj.height - random.randint(0, 100)
                            if not self.check_overlap(obj, [o for o in self.environment if o.type in [ObjectType.TREE, ObjectType.FLAG]]):
                                break
                            retries += 1
                        if retries >= 50:
                            obj.y = -obj.height - random.randint(0, 100)  # Fallback placement
                    elif obj.type == ObjectType.BARRIER:
                        obj.x = random.randint(CONFIG['ROAD_X'] + 20, CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - CONFIG['BARRIER_WIDTH'] - 20)
                        obj.y = -obj.height - random.randint(0, 100)
                    elif obj.type == ObjectType.PERSON:
                        obj.x = random.randint(CONFIG['ROAD_X'] + 20, CONFIG['ROAD_X'] + CONFIG['ROAD_WIDTH'] - CONFIG['PERSON_WIDTH'] - 20)
                        obj.y = -obj.height - random.randint(0, 100)

            self.check_collisions()

    def draw(self):
        self.draw_road()
        for obj in self.environment:
            obj.draw(screen)
        for opponent in self.opponents:
            opponent.draw(screen)
        self.player.draw(screen)

        font = pygame.font.SysFont(None, 36)
        score_text = font.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_text, (10, 10))
        speed_text = font.render(f"Speed: {int(self.player.speed * 10)}", True, WHITE)
        screen.blit(speed_text, (10, 50))

        if self.game_over:
            try:
                engine_sound.stop()
            except pygame.error as e:
                print(f"Failed to stop engine sound: {e}")
            font = pygame.font.SysFont(None, 100)
            game_over_text = font.render("GAME OVER", True, RED)
            screen.blit(game_over_text, (WIDTH // 2 - 150, HEIGHT // 5 - 50))
            restart_text = font.render("R-Restart/Q-Quit", True, RED)
            screen.blit(restart_text, (WIDTH // 2 - 220, HEIGHT // 2 + 50))

def main():
    game = Game()
    running = True

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if game.game_over:
                    if event.key == pygame.K_r:
                        game = Game()
                    elif event.key == pygame.K_q:
                        running = False
                elif event.key == pygame.K_m:
                    try:
                        engine_sound.set_volume(0 if engine_sound.get_volume() > 0 else 0.3)
                    except pygame.error as e:
                        print(f"Failed to toggle mute: {e}")

        if not game.game_over:
            keys = pygame.key.get_pressed()
            direction = None
            if keys[pygame.K_LEFT]:
                direction = "left"
            elif keys[pygame.K_RIGHT]:
                direction = "right"
            game.player.move(direction)

        game.update()
        game.draw()
        pygame.display.flip()
        clock.tick(CONFIG['FPS'])

    try:
        pygame.quit()
    except pygame.error as e:
        print(f"Failed to quit Pygame: {e}")

if __name__ == "__main__":
    main()