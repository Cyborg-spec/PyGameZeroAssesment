import math
import random
from pygame import Rect
import pgzrun

WIDTH = 800
HEIGHT = 600
TITLE = "Dungeon Runner"

STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_WIN = "win"
STATE_LOSE = "lose"

PLAYER_SPEED = 3.0
BASE_ENEMY_SPEED = 1.5
ANIM_SPEED = 0.13

STEP_INTERVAL = 0.25


class AnimatedActor(Actor):
    def __init__(self, idle_images, walk_images, pos):
        super().__init__(idle_images[0], pos)
        self.idle_images = idle_images
        self.walk_images = walk_images
        self.frame_index = 0
        self.timer = 0.0
        self.moving = False

    def animate(self, dt):
        images = self.walk_images if self.moving else self.idle_images
        if len(images) <= 1:
            return
        self.timer += dt
        while self.timer >= ANIM_SPEED:
            self.timer -= ANIM_SPEED
            self.frame_index = (self.frame_index + 1) % len(images)
            self.image = images[self.frame_index]


class GameManager:
    def __init__(self):
        self.state = STATE_MENU
        self.level = 1
        self.sound_on = True
        self.shake_timer = 0

    def play_music(self):
        if not self.sound_on:
            return
        try:
            music.play("bg_music")
            music.set_volume(0.7)
        except Exception:
            pass

    def stop_music(self):
        try:
            music.stop()
        except Exception:
            pass

    def play_sfx(self, name, volume=0.5):
        if not self.sound_on:
            return
        try:
            s = getattr(sounds, name)
            s.set_volume(volume)
            s.play()
        except Exception:
            pass

    def toggle_sound(self):
        self.sound_on = not self.sound_on
        if self.sound_on and self.state == STATE_PLAYING:
            self.play_music()
        else:
            self.stop_music()

    def trigger_shake(self, frames=15):
        self.shake_timer = frames

    def get_shake_offset(self):
        if self.shake_timer > 0:
            self.shake_timer -= 1
            return random.randint(-4, 4), random.randint(-4, 4)
        return 0, 0


game = GameManager()


class Player(AnimatedActor):
    def __init__(self, pos):
        super().__init__(
            ["hero_idle_0", "hero_idle_1"],
            ["hero_walk_0", "hero_walk_1"],
            pos,
        )
        self.speed = PLAYER_SPEED
        self.collider = Rect(self.x - 6, self.y - 12, 12, 24)
        self.step_timer = 0.0

    def update(self, dt):
        dx = dy = 0.0
        self.moving = False
        self.step_timer = max(self.step_timer - dt, 0.0)

        if keyboard.left or keyboard.a:
            dx -= 1.0
        if keyboard.right or keyboard.d:
            dx += 1.0
        if keyboard.up or keyboard.w:
            dy -= 1.0
        if keyboard.down or keyboard.s:
            dy += 1.0

        old_x, old_y = self.x, self.y

        if dx != 0.0 or dy != 0.0:
            self.moving = True
            length = math.hypot(dx, dy)
            if length > 0.0:
                dx /= length
                dy /= length
                move_dist = self.speed * dt * 60.0
                self.x += dx * move_dist
                self.y += dy * move_dist
                if self.step_timer <= 0.0:
                    game.play_sfx("step", volume=0.15)
                    self.step_timer = STEP_INTERVAL

        half_w = 8
        half_h = 14
        self.x = max(half_w, min(WIDTH - half_w, self.x))
        self.y = max(half_h, min(HEIGHT - half_h, self.y))

        self.collider.x = self.x - 6
        self.collider.y = self.y - 12

        for r in wall_rects:
            if self.collider.colliderect(r):
                self.x, self.y = old_x, old_y
                self.collider.x = self.x - 6
                self.collider.y = self.y - 12
                break

        self.animate(dt)


class Enemy(AnimatedActor):
    def __init__(self, enemy_type, pos, speed):
        if enemy_type == 1:
            idle = ["enemy1_idle_0", "enemy1_idle_1"]
            walk = ["enemy1_walk_0", "enemy1_walk_1"]
        else:
            idle = ["enemy2_idle_0", "enemy2_idle_1"]
            walk = ["enemy2_walk_0", "enemy2_walk_1"]

        super().__init__(idle, walk, pos)
        self.speed = speed
        angle = random.uniform(0, 2 * math.pi)
        self.dir_x = math.cos(angle)
        self.dir_y = math.sin(angle)
        self.collider = Rect(self.x - 10, self.y - 10, 20, 20)

    def update(self, dt):
        self.moving = True

        move_dist = self.speed * dt * 60.0
        old_x, old_y = self.x, self.y

        self.x += self.dir_x * move_dist
        self.collider.x = self.x - 10
        hit_wall = False
        for r in wall_rects:
            if self.collider.colliderect(r):
                hit_wall = True
                break
        if hit_wall or self.left < 0 or self.right > WIDTH:
            self.x = old_x
            self.collider.x = self.x - 10
            self.dir_x *= -1.0

        self.y += self.dir_y * move_dist
        self.collider.y = self.y - 10
        hit_wall = False
        for r in wall_rects:
            if self.collider.colliderect(r):
                hit_wall = True
                break
        if hit_wall or self.top < 0 or self.bottom > HEIGHT:
            self.y = old_y
            self.collider.y = self.y - 10
            self.dir_y *= -1.0

        self.animate(dt)


player = None
enemies = []
walls = []
wall_rects = []
exit_door = Actor("tile_exit", (WIDTH - 60, HEIGHT // 2))

btn_start = Rect(WIDTH // 2 - 100, 260, 200, 60)
btn_sound = Rect(WIDTH // 2 - 100, 340, 200, 60)
btn_exit = Rect(WIDTH // 2 - 100, 420, 200, 60)


def draw_tiled_floor(shake_x, shake_y):
    try:
        tile = images.tile_floor
        tw = tile.get_width()
        th = tile.get_height()
        for x in range(-tw, WIDTH + tw, tw):
            for y in range(-th, HEIGHT + th, th):
                screen.blit("tile_floor", (x + shake_x, y + shake_y))
    except Exception:
        screen.fill((0, 0, 0))


def start_level(level):
    global player, enemies, walls, wall_rects

    player = Player((80, HEIGHT // 2))
    enemies = []
    walls = []
    wall_rects = []

    try:
        tw = images.tile_wall.get_width()
        th = images.tile_wall.get_height()
    except Exception:
        tw = th = 32

    if level >= 2:
        x = WIDTH // 2
        for y in range(100, HEIGHT - 100, th):
            w = Actor("tile_wall", (x, y))
            walls.append(w)

    if level >= 3:
        y = HEIGHT // 3
        for x in range(150, WIDTH - 150, tw):
            w = Actor("tile_wall", (x, y))
            walls.append(w)

    for w in walls:
        wall_rects.append(Rect(w.left, w.top, w.width, w.height))

    num_enemies = 2 + level
    speed = BASE_ENEMY_SPEED + (level * 0.2)

    player_rect = Rect(player.x - 12, player.y - 18, 24, 36)
    exit_rect = Rect(exit_door.left, exit_door.top, exit_door.width, exit_door.height)

    for i in range(num_enemies):
        enemy_type = 1 if i % 2 == 0 else 2

        placed = False
        attempts = 0
        while not placed and attempts < 100:
            attempts += 1
            ex = random.randint(80, WIDTH - 80)
            ey = random.randint(80, HEIGHT - 80)

            test_rect = Rect(ex - 12, ey - 12, 24, 24)

            if test_rect.colliderect(player_rect):
                continue
            if test_rect.colliderect(exit_rect):
                continue

            collides_wall = False
            for r in wall_rects:
                if test_rect.colliderect(r):
                    collides_wall = True
                    break
            if collides_wall:
                continue

            enemies.append(Enemy(enemy_type, (ex, ey), speed))
            placed = True


def draw_button(rect, text, color):
    screen.draw.filled_rect(Rect(rect.x + 3, rect.y + 3, rect.width, rect.height), (0, 0, 0))
    screen.draw.filled_rect(rect, color)
    screen.draw.text(text, center=rect.center, fontsize=32, color="white")


def draw():
    shake_x, shake_y = game.get_shake_offset()
    screen.clear()

    if game.state == STATE_MENU:
        screen.fill((10, 10, 20))
        screen.draw.text("DUNGEON RUNNER", center=(WIDTH // 2, 140),
                         fontsize=64, color="orange", owidth=2, ocolor="black")
        draw_button(btn_start, "START", "dodgerblue")
        status = "ON" if game.sound_on else "OFF"
        draw_button(btn_sound, f"SOUND: {status}", "green")
        draw_button(btn_exit, "EXIT", "crimson")

    else:
        draw_tiled_floor(shake_x, shake_y)

        try:
            tile = images.tile_wall
            tw, th = tile.get_width(), tile.get_height()
            for x in range(0, WIDTH, tw):
                screen.blit("tile_wall", (x + shake_x, 0 + shake_y))
                screen.blit("tile_wall", (x + shake_x, HEIGHT - th + shake_y))
            for y in range(0, HEIGHT, th):
                screen.blit("tile_wall", (0 + shake_x, y + shake_y))
                screen.blit("tile_wall", (WIDTH - tw + shake_x, y + shake_y))
        except Exception:
            pass

        for w in walls:
            old_w = w.pos
            w.pos = (w.x + shake_x, w.y + shake_y)
            w.draw()
            w.pos = old_w

        old_pos = exit_door.pos
        exit_door.pos = (exit_door.x + shake_x, exit_door.y + shake_y)
        exit_door.draw()
        exit_door.pos = old_pos

        if player:
            screen.blit(player.image, (player.x - 8 + shake_x, player.y - 14 + shake_y))

        for e in enemies:
            old_e = e.pos
            e.pos = (e.x + shake_x, e.y + shake_y)
            e.draw()
            e.pos = old_e

        screen.draw.text(f"LEVEL {game.level}", topleft=(10, 10),
                         fontsize=32, color="white", owidth=1, ocolor="black")

        if game.state == STATE_WIN:
            screen.draw.textbox("YOU REACHED THE EXIT! CLICK FOR NEXT LEVEL",
                                Rect(WIDTH // 2 - 260, HEIGHT // 2 - 40, 520, 80),
                                color="gold", owidth=1, ocolor="black")
        elif game.state == STATE_LOSE:
            screen.draw.textbox("YOU DIED! CLICK TO RETURN TO MENU",
                                Rect(WIDTH // 2 - 260, HEIGHT // 2 - 40, 520, 80),
                                color="red", owidth=1, ocolor="black")


def update(dt):
    if game.state != STATE_PLAYING:
        return

    player.update(dt)
    for e in enemies:
        e.update(dt)

    for e in enemies:
        if player.collider.colliderect(e.collider):
            game.play_sfx("hit", volume=0.6)
            game.trigger_shake(25)
            game.state = STATE_LOSE
            game.stop_music()
            return

    if player.colliderect(exit_door):
        game.play_sfx("win", volume=0.7)
        game.state = STATE_WIN
        game.stop_music()


def on_mouse_down(pos):
    if game.state == STATE_MENU:
        if btn_start.collidepoint(pos):
            game.level = 1
            start_level(game.level)
            game.state = STATE_PLAYING
            game.play_music()
        elif btn_sound.collidepoint(pos):
            game.toggle_sound()
        elif btn_exit.collidepoint(pos):
            quit()

    elif game.state == STATE_WIN:
        game.level += 1
        start_level(game.level)
        game.state = STATE_PLAYING
        game.play_music()

    elif game.state == STATE_LOSE:
        game.state = STATE_MENU


pgzrun.go()
