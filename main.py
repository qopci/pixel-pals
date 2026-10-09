
import json
import random
import math
import array
from pathlib import Path

import pygame

# ============================================================
# PIXEL PALS - a cozy virtual pet game
# ============================================================

pygame.init()

# Tiny synthesized sound effects: no external audio files are required.
try:
    pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
    def make_tone(frequency, duration=0.11, volume=0.22, end_frequency=None):
        sample_rate = 22050
        count = int(sample_rate * duration)
        samples = array.array("h")
        end_frequency = end_frequency or frequency
        for i in range(count):
            progress = i / max(1, count - 1)
            freq = frequency + (end_frequency - frequency) * progress
            envelope = min(1.0, i / 180, (count - i) / 500)
            value = int(32767 * volume * envelope * math.sin(2 * math.pi * freq * i / sample_rate))
            samples.append(value)
        return pygame.mixer.Sound(buffer=samples.tobytes())

    SOUNDS = {
        "feed": make_tone(620, 0.10, end_frequency=880),
        "play": make_tone(520, 0.16, end_frequency=1040),
        "clean": make_tone(880, 0.12, end_frequency=660),
        "sleep": make_tone(440, 0.24, volume=0.18, end_frequency=330),
        "pet": make_tone(700, 0.13, end_frequency=920),
        "click": make_tone(560, 0.055, volume=0.14),
        "room": make_tone(420, 0.10, end_frequency=620),
        "select": make_tone(760, 0.07, volume=0.16),
        # Distinct synthesized animal calls, with no external audio files.
        # The pitches and contours are stylized game sounds rather than recordings.
        "animal_cat": make_tone(430, 0.24, volume=0.23, end_frequency=980),
        "animal_dog": make_tone(180, 0.09, volume=0.28, end_frequency=115) ,
        "animal_hamster": make_tone(1150, 0.10, volume=0.19, end_frequency=1500),
        "animal_rabbit": make_tone(850, 0.13, volume=0.17, end_frequency=1180),
        "animal_turtle": make_tone(520, 0.18, volume=0.15, end_frequency=390),
    }
except pygame.error:
    SOUNDS = {}

sounds_muted = False

def play_sound(name):
    if sounds_muted:
        return
    sound = SOUNDS.get(name)
    if sound:
        try:
            sound.play()
        except pygame.error:
            pass

WIDTH, HEIGHT = 1000, 700
FPS = 60
SAVE_PATH = Path(__file__).resolve().parent / "pet_save.json"
ASSET_PATH = Path(__file__).resolve().parent / "assets"

window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
canvas = pygame.Surface((WIDTH, HEIGHT))
pygame.display.set_caption("Pixel Pals")
clock = pygame.time.Clock()

fullscreen = False
paused = False
game_over = False
running = True

# ---------- Palette ----------
INK = (29, 29, 43)
INK_LIGHT = (55, 53, 76)
CREAM = (255, 246, 225)
PAPER = (238, 228, 207)
PINK = (246, 127, 155)
GOLD = (255, 195, 75)
GREEN = (117, 218, 137)
BLUE = (112, 179, 245)
PURPLE = (190, 157, 244)
MUTED = (167, 158, 155)

FONT = pygame.font.SysFont("segoeui", 20)
SMALL = pygame.font.SysFont("segoeui", 16)
TINY = pygame.font.SysFont("segoeui", 14)
TITLE = pygame.font.SysFont("segoeui", 26, bold=True)
BIG = pygame.font.SysFont("segoeui", 32, bold=True)

# ---------- Content ----------
SPECIES = ["cat", "dog", "hamster", "rabbit", "turtle"]

PET_DEFAULTS = {
    "cat": {"name": "Mochi", "hunger": 80, "happiness": 85,
            "energy": 80, "cleanliness": 85},
    "dog": {"name": "Biscuit", "hunger": 80, "happiness": 85,
            "energy": 80, "cleanliness": 85},
    "hamster": {"name": "Peanut", "hunger": 80, "happiness": 85,
                "energy": 80, "cleanliness": 85},
    "rabbit": {"name": "Clover", "hunger": 80, "happiness": 85,
               "energy": 80, "cleanliness": 85},
    "turtle": {"name": "Pebble", "hunger": 80, "happiness": 85,
               "energy": 80, "cleanliness": 85},
}

ROOMS = [
    "kitchen", "bedroom", "livingroom",
    "bathroom", "garden", "attic"
]

FOODS = [
    "watermelon", "pineapple", "apple", "kibble",
    "fish", "chicken", "milk", "carrot",
    "strawberry", "cookie", "treat", "water"
]

FOOD_LABELS = {
    "watermelon": "Watermelon",
    "pineapple": "Pineapple",
    "apple": "Apple",
    "kibble": "Kibble",
    "fish": "Fish",
    "chicken": "Chicken",
    "milk": "Milk",
    "carrot": "Carrot",
    "strawberry": "Berry",
    "cookie": "Cookie",
    "treat": "Treat",
    "water": "Water",
}

FOOD_COLORS = {
    "watermelon": (246, 91, 119),
    "pineapple": (245, 177, 48),
    "apple": (221, 65, 79),
    "kibble": (154, 111, 77),
    "fish": (83, 167, 236),
    "chicken": (231, 154, 67),
    "milk": (227, 239, 247),
    "carrot": (245, 131, 52),
    "strawberry": (240, 74, 103),
    "cookie": (194, 135, 85),
    "treat": (245, 113, 160),
    "water": (90, 184, 241),
}

# Initial inventory
DEFAULT_INVENTORY = {
    "watermelon": 4, "pineapple": 1, "apple": 1,
    "kibble": 8, "fish": 3, "chicken": 3,
    "milk": 2, "carrot": 3, "strawberry": 3,
    "cookie": 2, "treat": 4, "water": 6,
}

# ---------- Save data ----------
pets = {species: data.copy() for species, data in PET_DEFAULTS.items()}
inventory = DEFAULT_INVENTORY.copy()
coins = 120
active_pet = "cat"
room_index = 0
selected_item = 0
item_page = 0
message = "Welcome home! Choose an item or spend time with your pet."
message_started = pygame.time.get_ticks()
last_displayed_message = message
active_animation = None
animation_started = 0
last_decay = pygame.time.get_ticks()
last_save = last_decay

# Cache loaded images so we don't reload them every frame.
image_cache = {}


def load_image(category, filename):
    """Load an optional PNG from assets; return None if it's missing."""
    key = (category, filename)
    if key in image_cache:
        return image_cache[key]

    path = ASSET_PATH / category / f"{filename}.png"
    image = None

    if path.exists():
        try:
            image = pygame.image.load(str(path)).convert_alpha()
        except (pygame.error, OSError) as error:
            print(f"Could not load {path}: {error}")

    image_cache[key] = image
    return image


def fit_image(image, size):
    """Resize artwork smoothly enough for display; source art can stay pixelated."""
    if image is None:
        return None
    return pygame.transform.scale(image, size)


def save_game():
    data = {
        "pets": pets,
        "active_pet": active_pet,
        "room_index": room_index,
        "coins": coins,
        "inventory": inventory,
        "selected_item": selected_item,
    }

    try:
        with SAVE_PATH.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2)
    except (OSError, TypeError) as error:
        print("Could not save the game:", error)


def load_game():
    global pets, inventory, coins, active_pet
    global room_index, selected_item, item_page

    if not SAVE_PATH.exists():
        return

    try:
        with SAVE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return

        saved_pets = data.get("pets", {})
        if isinstance(saved_pets, dict):
            for species in SPECIES:
                saved = saved_pets.get(species, {})
                if not isinstance(saved, dict):
                    continue

                for key in ("name", "hunger", "happiness", "energy", "cleanliness"):
                    if key in saved:
                        if key == "name":
                            if isinstance(saved[key], str) and saved[key].strip():
                                pets[species][key] = saved[key][:20]
                        else:
                            try:
                                pets[species][key] = max(
                                    0, min(100, int(saved[key]))
                                )
                            except (ValueError, TypeError):
                                pass

        saved_inventory = data.get("inventory", {})
        if isinstance(saved_inventory, dict):
            for item in FOODS:
                try:
                    inventory[item] = max(
                        0, min(100, int(saved_inventory.get(item, inventory[item])))
                    )
                except (ValueError, TypeError):
                    pass

        try:
            coins = max(0, int(data.get("coins", coins)))
            room_index = int(data.get("room_index", 0)) % len(ROOMS)
            selected_item = int(data.get("selected_item", 0)) % len(FOODS)
        except (ValueError, TypeError):
            pass

        if data.get("active_pet") in SPECIES:
            active_pet = data["active_pet"]

        item_page = (selected_item // 3) * 3

    except (OSError, json.JSONDecodeError) as error:
        print("Could not read save file:", error)


# ---------- Drawing helpers ----------
def draw_text(label, x, y, font=FONT, color=CREAM, center=False):
    """Render smooth, readable UI text; keep centered labels inside the canvas."""
    text = str(label)
    render_font = font
    surface = render_font.render(text, True, color)
    # Long messages and labels scale down gently rather than clipping at panel edges.
    max_width = 580 if center and y == 462 else 0
    if max_width and surface.get_width() > max_width:
        size = render_font.get_height()
        while size > 12 and surface.get_width() > max_width:
            size -= 1
            render_font = pygame.font.SysFont("segoeui", size, bold=font.get_bold())
            surface = render_font.render(text, True, color)
    rect = surface.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    canvas.blit(surface, rect)


def panel(x, y, w, h, color=PAPER, border=INK, thickness=4):
    pygame.draw.rect(canvas, border, (x, y, w, h))
    pygame.draw.rect(
        canvas, color,
        (x + thickness, y + thickness, w - thickness * 2, h - thickness * 2)
    )


def pixel_rect(color, x, y, w, h):
    pygame.draw.rect(canvas, color, (int(x), int(y), int(w), int(h)))



def draw_food_icon(item, x, y, size=38):
    """Draw polished pixel-inspired food icons without external assets."""
    image = load_image("food", item)
    if image:
        canvas.blit(fit_image(image, (size, size)), (x - size // 2, y - size // 2))
        return

    # Draw at a stable scale so the icons have a consistent visual language.
    s = max(1, size / 38)
    def block(color, rx, ry, rw, rh):
        pygame.draw.rect(canvas, color, (round(x + rx*s), round(y + ry*s),
                                         max(1, round(rw*s)), max(1, round(rh*s))))
    def outline(rect, radius=5, color=INK):
        pygame.draw.rect(canvas, color, rect, max(1, round(2*s)), border_radius=round(radius*s))

    shadow = (45, 39, 57)
    cream = (255, 241, 205)
    green = (93, 171, 91)
    red = (232, 75, 100)
    if item == "watermelon":
        pygame.draw.polygon(canvas, shadow, [(x-15*s,y-1*s),(x+15*s,y-1*s),(x+2*s,y+15*s),(x-2*s,y+15*s)])
        pygame.draw.polygon(canvas, (55, 145, 91), [(x-14*s,y-2*s),(x+14*s,y-2*s),(x+2*s,y+13*s),(x-2*s,y+13*s)])
        pygame.draw.polygon(canvas, (255, 104, 124), [(x-10*s,y),(x+10*s,y),(x+2*s,y+10*s),(x-2*s,y+10*s)])
        for dx,dy in [(-5,2),(1,4),(5,1),(-1,8)]:
            block(INK, dx, dy, 2, 3)
    elif item == "pineapple":
        pygame.draw.polygon(canvas, shadow, [(x-5*s,y-9*s),(x-9*s,y-18*s),(x-2*s,y-13*s),(x+1*s,y-21*s),(x+5*s,y-12*s),(x+10*s,y-16*s),(x+8*s,y-7*s)])
        pygame.draw.polygon(canvas, green, [(x-4*s,y-9*s),(x-7*s,y-16*s),(x-1*s,y-12*s),(x+2*s,y-19*s),(x+5*s,y-11*s),(x+9*s,y-14*s),(x+7*s,y-7*s)])
        pygame.draw.ellipse(canvas, shadow, (x-11*s,y-11*s,22*s,28*s))
        pygame.draw.ellipse(canvas, (246,184,65), (x-9*s,y-9*s,18*s,24*s))
        for dx,dy in [(-4,-4),(3,-2),(-2,2),(4,5),(-5,7),(1,9)]:
            block((191,119,45), dx, dy, 3, 2)
    elif item in ("apple", "strawberry"):
        if item == "apple":
            pygame.draw.ellipse(canvas, shadow, (x-13*s,y-11*s,26*s,25*s))
            pygame.draw.ellipse(canvas, red, (x-11*s,y-10*s,22*s,21*s))
            pygame.draw.ellipse(canvas, (255,137,143), (x-7*s,y-7*s,7*s,8*s))
            block((105,70,47), -1, -14, 3, 7)
            pygame.draw.ellipse(canvas, green, (x+1*s,y-15*s,11*s,6*s))
        else:
            pygame.draw.polygon(canvas, shadow, [(x,y-11*s),(x+12*s,y-4*s),(x+8*s,y+11*s),(x,y+16*s),(x-8*s,y+11*s),(x-12*s,y-4*s)])
            pygame.draw.polygon(canvas, (244,69,99), [(x,y-9*s),(x+10*s,y-3*s),(x+7*s,y+9*s),(x,y+13*s),(x-7*s,y+9*s),(x-10*s,y-3*s)])
            for dx,dy in [(-5,0),(2,-2),(5,4),(-2,7),(1,3)]:
                block((255,220,133), dx, dy, 2, 3)
            pygame.draw.polygon(canvas, green, [(x,y-9*s),(x-4*s,y-17*s),(x+1*s,y-13*s),(x+7*s,y-17*s),(x+6*s,y-9*s)])
    elif item == "carrot":
        pygame.draw.polygon(canvas, shadow, [(x-10*s,y-12*s),(x+10*s,y-12*s),(x+2*s,y+15*s),(x-2*s,y+15*s)])
        pygame.draw.polygon(canvas, (245,132,54), [(x-8*s,y-11*s),(x+8*s,y-11*s),(x+1*s,y+12*s),(x-1*s,y+12*s)])
        for dy in [-5,1,6]:
            pygame.draw.line(canvas, (255,193,99), (x-4*s,y+dy*s),(x+3*s,y+(dy+1)*s), max(1,round(2*s)))
        pygame.draw.polygon(canvas, green, [(x-3*s,y-11*s),(x-7*s,y-19*s),(x-1*s,y-15*s),(x+3*s,y-21*s),(x+4*s,y-12*s),(x+10*s,y-16*s),(x+7*s,y-9*s)])
    elif item == "fish":
        pygame.draw.ellipse(canvas, shadow, (x-15*s,y-8*s,25*s,17*s))
        pygame.draw.polygon(canvas, shadow, [(x+7*s,y),(x+17*s,y-9*s),(x+17*s,y+9*s)])
        pygame.draw.ellipse(canvas, (91,177,238), (x-13*s,y-7*s,22*s,14*s))
        pygame.draw.polygon(canvas, (91,177,238), [(x+7*s,y),(x+15*s,y-7*s),(x+15*s,y+7*s)])
        pygame.draw.ellipse(canvas, (176,226,255), (x-8*s,y-5*s,8*s,5*s))
        pygame.draw.circle(canvas, INK, (round(x-5*s),round(y-1*s)), max(1,round(2*s)))
        for dx in [0,5]:
            pygame.draw.arc(canvas, (52,130,194), (x+dx*s,y-5*s,8*s,10*s), 0.5, 4.8, max(1,round(1*s)))
    elif item == "chicken":
        pygame.draw.ellipse(canvas, shadow, (x-12*s,y-10*s,22*s,22*s))
        pygame.draw.ellipse(canvas, (241,172,88), (x-10*s,y-9*s,18*s,19*s))
        pygame.draw.ellipse(canvas, (255,216,145), (x-6*s,y-6*s,8*s,9*s))
        pygame.draw.line(canvas, cream, (x+7*s,y+5*s),(x+15*s,y+12*s), max(2,round(5*s)))
        pygame.draw.circle(canvas, cream, (round(x+15*s),round(y+11*s)), max(2,round(4*s)))
    elif item == "milk":
        pygame.draw.rect(canvas, shadow, (x-9*s,y-13*s,18*s,27*s), border_radius=round(3*s))
        pygame.draw.rect(canvas, (248,249,237), (x-7*s,y-11*s,14*s,23*s), border_radius=round(2*s))
        pygame.draw.rect(canvas, (133,200,235), (x-7*s,y-2*s,14*s,10*s))
        pygame.draw.rect(canvas, (255,255,255), (x-4*s,y-8*s,3*s,7*s))
        pygame.draw.rect(canvas, (255,221,146), (x-5*s,y-17*s,10*s,5*s))
    elif item == "kibble":
        for dx,dy,col in [(-7,-5,(157,108,72)),(2,-8,(188,137,87)),(-2,1,(137,88,61)),(7,3,(174,119,75)),(-8,7,(190,145,91)),(3,8,(145,94,65))]:
            pygame.draw.rect(canvas, shadow, (x+(dx-3)*s,y+(dy-2)*s,7*s,6*s), border_radius=round(2*s))
            pygame.draw.rect(canvas, col, (x+(dx-2)*s,y+(dy-1)*s,5*s,4*s), border_radius=round(2*s))
    elif item == "cookie":
        pygame.draw.circle(canvas, shadow, (round(x),round(y+1*s)), round(14*s))
        pygame.draw.circle(canvas, (210,157,101), (round(x),round(y)), round(13*s))
        pygame.draw.circle(canvas, (255,207,143), (round(x-4*s),round(y-5*s)), round(5*s))
        for dx,dy in [(-5,2),(3,-4),(6,3),(-1,7),(1,1)]:
            pygame.draw.rect(canvas, (103,69,60), (x+dx*s,y+dy*s,3*s,3*s))
    elif item == "treat":
        pygame.draw.rect(canvas, shadow, (x-12*s,y-8*s,24*s,17*s), border_radius=round(5*s))
        pygame.draw.rect(canvas, (245,113,160), (x-10*s,y-7*s,20*s,14*s), border_radius=round(4*s))
        pygame.draw.rect(canvas, (255,198,217), (x-6*s,y-5*s,7*s,4*s), border_radius=round(2*s))
        pygame.draw.rect(canvas, cream, (x+7*s,y-3*s,5*s,7*s), border_radius=round(2*s))
    elif item == "water":
        pygame.draw.rect(canvas, shadow, (x-10*s,y-12*s,20*s,25*s), border_radius=round(4*s))
        pygame.draw.rect(canvas, (132,208,255), (x-8*s,y-10*s,16*s,21*s), border_radius=round(3*s))
        pygame.draw.rect(canvas, (220,246,255), (x-5*s,y-7*s,4*s,12*s))
        pygame.draw.rect(canvas, (86,159,224), (x-6*s,y-16*s,12*s,5*s), border_radius=round(2*s))
    else:
        # Fallback icon for any food item without a custom drawing above.
        radius = max(5, round(size * 0.32))
        food_color = FOOD_COLORS.get(item, PINK)
        center = (round(x), round(y))
        pygame.draw.circle(canvas, food_color, center, radius)
        pygame.draw.circle(canvas, INK, center, radius, max(1, round(2 * s)))
# ---------- Room backgrounds ----------

def draw_room_fallback(room):
    """Rich, cozy room illustrations drawn entirely with Pygame."""
    palettes = {
        "kitchen": ((250, 216, 173), (190, 120, 91), (247, 196, 113), (99, 74, 91)),
        "bedroom": ((226, 205, 235), (143, 111, 161), (245, 204, 211), (83, 68, 101)),
        "livingroom": ((246, 211, 170), (157, 105, 82), (216, 151, 123), (100, 68, 72)),
        "bathroom": ((190, 226, 232), (122, 177, 193), (242, 247, 237), (70, 104, 125)),
        "garden": ((171, 218, 151), (93, 150, 88), (248, 215, 133), (66, 111, 76)),
        "attic": ((200, 157, 126), (129, 86, 78), (239, 190, 129), (88, 59, 69)),
    }
    wall, floor, accent, trim = palettes[room]
    canvas.fill(wall)

    # Soft wall lighting: broad tonal bands keep the rooms smooth, not grid-like.
    for band in range(7):
        y0 = 72 + band * 44
        tint = tuple(min(255, c + max(0, 12 - band * 2)) for c in wall)
        pygame.draw.rect(canvas, tint, (0, y0, WIDTH, 44))
    pygame.draw.rect(canvas, tuple(min(255, c + 15) for c in wall), (0, 72, WIDTH, 5))

    if room not in ("garden", "attic"):
        # Window with a sunset gradient and curtains.
        pygame.draw.rect(canvas, trim, (775,100,151,154), border_radius=4)
        pygame.draw.rect(canvas, (255,237,190), (784,109,133,136))
        pygame.draw.rect(canvas, (153,211,232), (790,115,121,124))
        pygame.draw.circle(canvas, (255,224,139), (887,139), 19)
        pygame.draw.polygon(canvas, (190,226,218), [(790,220),(823,179),(846,205),(869,174),(911,221)])
        pygame.draw.rect(canvas, CREAM, (843,115,5,124))
        pygame.draw.rect(canvas, CREAM, (790,174,121,5))
        pygame.draw.polygon(canvas, accent, [(775,100),(808,100),(800,253),(775,253)])
        pygame.draw.polygon(canvas, accent, [(895,100),(926,100),(926,253),(904,253)])
        pygame.draw.rect(canvas, trim, (764,250,174,10))

    # Floor and baseboards.
    pygame.draw.rect(canvas, trim, (0,374,WIDTH,326))
    pygame.draw.rect(canvas, floor, (0,380,WIDTH,320))
    pygame.draw.rect(canvas, accent, (0,374,WIDTH,11))
    for y in range(432, 700, 72):
        pygame.draw.line(canvas, tuple(max(0,c-10) for c in floor), (0,y),(WIDTH,y), 1)
    # Gentle floorboard seams, staggered so they read as wood rather than a pixel grid.
    for row, y in enumerate(range(432, 700, 144)):
        for x in range((row % 2) * 85, WIDTH, 170):
            pygame.draw.line(canvas, tuple(min(255,c+10) for c in floor), (x,y),(x+100,y), 1)

    # A patterned rug makes the pet feel grounded.
    pygame.draw.ellipse(canvas, trim, (320,470,365,150))
    pygame.draw.ellipse(canvas, accent, (330,478,345,132))
    pygame.draw.ellipse(canvas, tuple(min(255,c+14) for c in accent), (342,488,321,112))

    if room == "kitchen":
        # Checker tile, counter, cupboards and little jars.
        for row in range(4):
            for col in range(10):
                tile = (250,235,207) if (row+col)%2 == 0 else (225,202,177)
                pygame.draw.rect(canvas, tile, (col*100,390+row*78,100,78))
                pygame.draw.rect(canvas, (255,246,222), (col*100,390+row*78,100,78), 1)
        pygame.draw.rect(canvas, trim, (42,170,180,184), border_radius=4)
        pygame.draw.rect(canvas, (232,192,150), (49,177,166,168))
        for y in (224,280):
            pygame.draw.line(canvas, trim, (50,y),(215,y),4)
        for x in (76,128,180):
            pygame.draw.rect(canvas, (255,232,190), (x,190,29,28), border_radius=3)
            pygame.draw.rect(canvas, accent, (x+5,196,19,16), border_radius=2)
        pygame.draw.rect(canvas, trim, (286,294,360,30), border_radius=4)
        pygame.draw.rect(canvas, (249,220,180), (280,285,370,20), border_radius=4)
        pygame.draw.rect(canvas, (157,191,198), (300,239,70,45), border_radius=4)
        pygame.draw.rect(canvas, CREAM, (306,245,58,33), border_radius=3)
        pygame.draw.rect(canvas, (245,160,112), (407,254,34,31), border_radius=4)
        pygame.draw.rect(canvas, (245,160,112), (412,245,24,12), border_radius=3)
        # Small leafy plant placed neatly on the kitchen shelf/counter.
        pygame.draw.line(canvas, (66,126,78), (560,280),(560,235), 4)
        for lx, ly in [( -18,-18),(-23,-35),(0,-31),(17,-42),(23,-20),(-3,-49)]:
            pygame.draw.ellipse(canvas, (73,155,91), (560+lx-9, 235+ly-5, 21, 13))
            pygame.draw.line(canvas, (126,191,112), (560,280),(560+lx,235+ly), 2)
        pygame.draw.rect(canvas, (202,126,90), (542,264,36,19), border_radius=4)
        pygame.draw.rect(canvas, (233,157,111), (539,261,42,7), border_radius=3)
    elif room == "bedroom":
        # A more obvious cozy bed with a tall headboard, wooden frame, pillows and quilt.
        pygame.draw.rect(canvas, trim, (55,205,292,190), border_radius=10)
        pygame.draw.rect(canvas, (185,132,113), (63,214,276,176), border_radius=8)
        pygame.draw.rect(canvas, (250,238,222), (70,224,262,159), border_radius=7)
        pygame.draw.rect(canvas, (160,174,222), (70,281,262,102), border_radius=6)
        pygame.draw.rect(canvas, (191,201,237), (70,277,262,10), border_radius=4)
        for bx in range(85,323,38):
            pygame.draw.line(canvas, (191,201,237), (bx,294),(bx,376),2)
        pygame.draw.rect(canvas, CREAM, (83,235,103,47), border_radius=7)
        pygame.draw.rect(canvas, (255,248,232), (91,241,87,34), border_radius=5)
        pygame.draw.rect(canvas, CREAM, (199,235,103,47), border_radius=7)
        pygame.draw.rect(canvas, (255,248,232), (207,241,87,34), border_radius=5)
        pygame.draw.rect(canvas, trim, (46,377,310,22), border_radius=5)
        pygame.draw.rect(canvas, (137,92,69), (73,392,15,28), border_radius=3)
        pygame.draw.rect(canvas, (137,92,69), (316,392,15,28), border_radius=3)
        # Bedside table and warm lamp, tucked beside the bed on the left.
        pygame.draw.rect(canvas, trim, (356,310,63,70), border_radius=4)
        pygame.draw.rect(canvas, accent, (365,318,45,40), border_radius=3)
        pygame.draw.rect(canvas, GOLD, (380,289,15,23), border_radius=3)
        pygame.draw.polygon(canvas, (255,230,163), [(367,292),(407,292),(399,271),(376,271)])
    elif room == "livingroom":
        # Sofa with plush cushions and coffee table.
        pygame.draw.rect(canvas, trim, (55,285,310,111), border_radius=14)
        pygame.draw.rect(canvas, accent, (70,266,280,99), border_radius=13)
        pygame.draw.rect(canvas, (236,169,139), (85,278,78,71), border_radius=9)
        pygame.draw.rect(canvas, (239,188,158), (174,278,78,71), border_radius=9)
        pygame.draw.rect(canvas, (236,169,139), (263,278,72,71), border_radius=9)
        pygame.draw.rect(canvas, trim, (78,353,264,42), border_radius=8)
        pygame.draw.ellipse(canvas, trim, (366,380,285,67))
        pygame.draw.ellipse(canvas, (206,149,109), (376,374,265,60))
        pygame.draw.rect(canvas, (137,92,69), (400,410,16,52), border_radius=3)
        pygame.draw.rect(canvas, (137,92,69), (600,410,16,52), border_radius=3)
        pygame.draw.rect(canvas, (255,228,188), (480,382,58,27), border_radius=4)
        pygame.draw.circle(canvas, (237,136,141), (508,378), 10)
    elif room == "bathroom":
        for row in range(4):
            for col in range(10):
                pygame.draw.rect(canvas, (226,245,242) if (row+col)%2 else (205,232,234),
                                 (col*100,385+row*70,100,70))
                pygame.draw.rect(canvas, (164,207,213), (col*100,385+row*70,100,70), 1)
        pygame.draw.rect(canvas, trim, (610,200,285,181), border_radius=12)
        pygame.draw.rect(canvas, (245,250,241), (621,212,263,155), border_radius=10)
        pygame.draw.rect(canvas, (126,197,213), (635,227,235,125), border_radius=8)
        pygame.draw.arc(canvas, (250,253,245), (670,218,170,43), 3.2, 6.1, 4)
        pygame.draw.rect(canvas, trim, (98,270,144,89), border_radius=8)
        pygame.draw.rect(canvas, (247,249,240), (108,279,124,69), border_radius=6)
        pygame.draw.ellipse(canvas, (153,215,223), (119,286,102,48))
        pygame.draw.rect(canvas, trim, (284,270,80,108), border_radius=5)
        pygame.draw.rect(canvas, (248,248,232), (292,278,64,92), border_radius=4)
        pygame.draw.rect(canvas, (123,194,212), (300,300,48,9))
    elif room == "garden":
        canvas.fill((179,222,161))
        pygame.draw.circle(canvas, (255,228,142), (855,122), 47)
        for x,y in [(65,125),(255,190),(710,145),(930,220)]:
            pygame.draw.ellipse(canvas, (119,185,126), (x-26,y-10,52,24))
            pygame.draw.ellipse(canvas, (119,185,126), (x-10,y-25,24,50))
        pygame.draw.rect(canvas, (111,170,100), (0,345,WIDTH,355))
        for x in range(0,WIDTH,80):
            pygame.draw.ellipse(canvas, (130,189,105), (x,370+(x%3)*5,65,23))
        # White picket fence.
        pygame.draw.rect(canvas, (245,235,207), (0,292,WIDTH,12))
        pygame.draw.rect(canvas, (245,235,207), (0,330,WIDTH,10))
        for x in range(12,WIDTH,48):
            pygame.draw.rect(canvas, (255,246,224), (x,270,25,65), border_radius=3)
            pygame.draw.polygon(canvas, (255,246,224), [(x,273),(x+12,257),(x+25,273)])
        # Flower beds.
        for x in range(40,970,90):
            pygame.draw.ellipse(canvas, (80,128,69), (x-15,580,52,19))
            for dx,col in [(-4,PINK),(8,GOLD),(20,(180,145,232))]:
                pygame.draw.line(canvas, (58,128,70), (x+dx,590),(x+dx,568),3)
                pygame.draw.circle(canvas, col, (x+dx,566),6)
    elif room == "attic":
        pygame.draw.polygon(canvas, (156,104,88), [(0,250),(500,68),(1000,250)])
        pygame.draw.polygon(canvas, (181,126,102), [(0,250),(500,88),(1000,250),(1000,374),(0,374)])
        for x in range(60,1000,100):
            pygame.draw.line(canvas, (143,89,78), (500,92),(x,250),4)
        pygame.draw.rect(canvas, trim, (354,140,236,113), border_radius=4)
        pygame.draw.rect(canvas, (151,198,207), (365,151,214,91))
        pygame.draw.line(canvas, CREAM, (472,151),(472,242),5)
        pygame.draw.line(canvas, CREAM, (365,196),(579,196),5)
        pygame.draw.rect(canvas, trim, (687,309,154,70), border_radius=4)
        pygame.draw.rect(canvas, (180,126,88), (696,318,136,52), border_radius=3)
        for x in range(706,825,24):
            pygame.draw.line(canvas, (125,81,71), (x,320),(x,368),2)
        pygame.draw.rect(canvas, trim, (80,312,140,66), border_radius=5)
        pygame.draw.rect(canvas, (205,159,110), (88,320,124,50), border_radius=4)

    # A few room-specific finishing touches add personality without clutter.
    if room == "bedroom":
        pygame.draw.circle(canvas, (255, 232, 167), (842, 132), 13)
        pygame.draw.circle(canvas, (226, 205, 235), (848, 127), 12)
    elif room == "livingroom":
        # Framed landscape art and sofa piping.
        pygame.draw.rect(canvas, CREAM, (445, 153, 116, 79), border_radius=4)
        pygame.draw.rect(canvas, trim, (451, 159, 104, 67), border_radius=3)
        pygame.draw.circle(canvas, GOLD, (530, 173), 9)
        pygame.draw.polygon(canvas, (126, 174, 139), [(455, 219), (481, 185), (500, 211), (521, 190), (551, 219)])
        pygame.draw.line(canvas, (255, 223, 192), (634, 357), (885, 357), 2)
    elif room == "kitchen":
        # Warm pendant light over the counter.
        pygame.draw.line(canvas, trim, (500, 73), (500, 128), 3)
        pygame.draw.polygon(canvas, GOLD, [(478, 129), (522, 129), (513, 145), (487, 145)])
        pygame.draw.circle(canvas, (255, 230, 165), (500, 150), 17)
    elif room == "bathroom":
        # Folded towels beside the bath.
        for ty, tc in [(225, (255, 250, 238)), (238, (176, 219, 226)), (251, (255, 250, 238))]:
            pygame.draw.rect(canvas, tc, (405, ty, 76, 11), border_radius=3)
            pygame.draw.line(canvas, (180, 207, 211), (412, ty + 4), (474, ty + 4), 1)
    elif room == "garden":
        # Small stepping stones through the lawn.
        for sx, sy, sw in [(380, 618, 54), (448, 601, 58), (521, 618, 55), (592, 600, 58)]:
            pygame.draw.ellipse(canvas, (202, 205, 164), (sx, sy, sw, 19))
            pygame.draw.ellipse(canvas, (224, 223, 190), (sx + 4, sy + 3, sw - 8, 12))
def draw_room():
    room = ROOMS[room_index]
    image = load_image("rooms", room)

    if image:
        canvas.blit(fit_image(image, (WIDTH, HEIGHT)), (0, 0))
        # Draw key furniture over room artwork too, so the rooms always feel furnished.
        if room == "livingroom":
            # Cozy three-seat couch with arms, cushions, and wooden feet.
            pygame.draw.rect(canvas, (111, 72, 72), (76, 348, 265, 53), border_radius=12)
            pygame.draw.rect(canvas, (190, 111, 102), (56, 276, 305, 112), border_radius=18)
            pygame.draw.rect(canvas, (218, 147, 128), (71, 260, 275, 105), border_radius=16)
            pygame.draw.rect(canvas, (236, 177, 151), (85, 273, 78, 78), border_radius=12)
            pygame.draw.rect(canvas, (239, 185, 158), (169, 273, 80, 78), border_radius=12)
            pygame.draw.rect(canvas, (236, 177, 151), (255, 273, 76, 78), border_radius=12)
            pygame.draw.rect(canvas, (164, 99, 88), (78, 382, 17, 34), border_radius=4)
            pygame.draw.rect(canvas, (164, 99, 88), (322, 382, 17, 34), border_radius=4)
            pygame.draw.line(canvas, (255, 224, 199), (90, 358), (328, 358), 3)
        elif room == "bedroom":
            # A clear bed silhouette: tall headboard, two pillows, quilt, and frame.
            pygame.draw.rect(canvas, (133, 91, 111), (61, 207, 272, 191), border_radius=13)
            pygame.draw.rect(canvas, (249, 237, 224), (72, 222, 250, 160), border_radius=9)
            pygame.draw.rect(canvas, (156, 165, 217), (72, 276, 250, 106), border_radius=7)
            pygame.draw.rect(canvas, (192, 200, 239), (72, 271, 250, 12), border_radius=5)
            pygame.draw.rect(canvas, (255, 250, 239), (86, 231, 100, 44), border_radius=8)
            pygame.draw.rect(canvas, (255, 250, 239), (205, 231, 100, 44), border_radius=8)
            for bx in range(86, 315, 38):
                pygame.draw.line(canvas, (205, 211, 242), (bx, 294), (bx, 374), 2)
            pygame.draw.rect(canvas, (133, 91, 111), (53, 378, 290, 20), border_radius=5)
            pygame.draw.rect(canvas, (119, 79, 64), (70, 394, 15, 27), border_radius=3)
            pygame.draw.rect(canvas, (119, 79, 64), (311, 394, 15, 27), border_radius=3)

    else:
        draw_room_fallback(room)

    # Room-specific wall decor is overlaid even when custom background images are used.
    if room == "livingroom":
        # Wall shelf to the right of the couch, with books and a small potted plant.
        pygame.draw.rect(canvas, (91, 61, 56), (565, 258, 152, 10), border_radius=3)
        pygame.draw.rect(canvas, (199, 139, 93), (565, 253, 152, 7), border_radius=3)
        pygame.draw.rect(canvas, (143, 91, 72), (580, 224, 20, 29), border_radius=2)
        pygame.draw.rect(canvas, (224, 177, 121), (604, 231, 17, 22), border_radius=2)
        pygame.draw.rect(canvas, (104, 151, 105), (641, 235, 30, 18), border_radius=3)
        pygame.draw.line(canvas, (67, 123, 75), (656, 235), (656, 213), 3)
        pygame.draw.ellipse(canvas, (83, 158, 91), (640, 215, 17, 9))
        pygame.draw.ellipse(canvas, (105, 175, 100), (655, 207, 17, 10))
        pygame.draw.ellipse(canvas, (71, 145, 83), (655, 220, 17, 9))
    elif room == "bedroom":
        # A framed landscape painting on the wall beside the window.
        pygame.draw.rect(canvas, (83, 68, 101), (590, 127, 112, 83), border_radius=4)
        pygame.draw.rect(canvas, (250, 238, 222), (596, 133, 100, 71), border_radius=2)
        pygame.draw.rect(canvas, (170, 211, 224), (602, 139, 88, 59))
        pygame.draw.circle(canvas, (255, 218, 132), (669, 151), 10)
        pygame.draw.polygon(canvas, (109, 157, 122), [(603, 192), (626, 163), (644, 187), (662, 169), (689, 193)])

    # Soft darkened area behind the HUD text
    pygame.draw.rect(canvas, (30, 28, 44), (0, 0, WIDTH, 83))


# ---------- Fallback animal sprites ----------

def draw_pet_fallback(species, center_x=500, base_y=450, sleeping=False):
    """Cute, carefully layered pet portraits made from rounded pixel shapes."""
    x, y = center_x, base_y
    palette = {
        "cat": {"fur":(174,157,174),"light":(211,193,207),"dark":(112,91,120),"inner":(239,151,177),"eye":(143,195,111)},
        "dog": {"fur":(211,157,103),"light":(245,205,153),"dark":(137,87,61),"inner":(112,75,61),"eye":(117,177,190)},
        "hamster":{"fur":(220,174,113),"light":(255,222,166),"dark":(154,111,69),"inner":(244,160,174),"eye":(80,65,61)},
        "rabbit":{"fur":(240,227,220),"light":(255,246,233),"dark":(173,147,147),"inner":(238,151,180),"eye":(102,137,161)},
        "turtle":{"fur":(121,190,121),"light":(178,222,139),"dark":(54,116,77),"inner":(91,154,99),"eye":(61,89,64)},
    }[species]
    fur, light, dark, inner, eye = (palette[k] for k in ("fur","light","dark","inner","eye"))
    outline = INK

    # Ground shadow and soft halo.
    pygame.draw.ellipse(canvas, (95,78,102), (x-105,y-16,210,31))
    pygame.draw.ellipse(canvas, (255,237,196), (x-97,y-27,194,27))

    if species == "turtle":
        # Four little feet with toe highlights.
        for fx in (x-48,x+30):
            pygame.draw.ellipse(canvas, outline, (fx-12,y-31,31,27))
            pygame.draw.ellipse(canvas, fur, (fx-8,y-27,23,19))
            pygame.draw.circle(canvas, light, (fx+5,y-21), 3)
        # Shell and shell panels.
        pygame.draw.ellipse(canvas, outline, (x-72,y-119,144,104))
        pygame.draw.ellipse(canvas, dark, (x-66,y-114,132,94))
        pygame.draw.ellipse(canvas, (91,158,94), (x-59,y-108,118,82))
        pygame.draw.polygon(canvas, (133,190,105), [(x-31,y-99),(x-4,y-110),(x+27,y-98),(x+32,y-72),(x+2,y-61),(x-28,y-72)])
        pygame.draw.line(canvas, (62,125,79), (x-3,y-106),(x+2,y-64),3)
        pygame.draw.line(canvas, (62,125,79), (x-57,y-81),(x+56,y-81),3)
        # Head.
        pygame.draw.ellipse(canvas, outline, (x+43,y-94,62,57))
        pygame.draw.ellipse(canvas, fur, (x+48,y-89,51,47))
        pygame.draw.ellipse(canvas, light, (x+57,y-80,24,19))
        if sleeping:
            # Closed, relaxed eyelid on the turtle's visible eye.
            pygame.draw.arc(canvas, dark, (x+69,y-82,22,15), math.pi, 2*math.pi, 3)
            pygame.draw.arc(canvas, dark, (x+72,y-80,16,10), math.pi, 2*math.pi, 2)
        else:
            pygame.draw.circle(canvas, CREAM, (x+79,y-76), 10)
            pygame.draw.circle(canvas, eye, (x+82,y-76), 5)
            pygame.draw.circle(canvas, CREAM, (x+83,y-78), 2)
        # No nose: draw an unmistakable happy smile (ends up, middle down).
        pygame.draw.lines(canvas, dark, False, [
            (x+86, y-63), (x+90, y-60), (x+94, y-59),
            (x+98, y-60), (x+102, y-63)
        ], 2)
        return

    # Body, feet, and tail.
    pygame.draw.ellipse(canvas, outline, (x-75,y-118,150,111))
    pygame.draw.ellipse(canvas, fur, (x-69,y-112,138,99))
    pygame.draw.ellipse(canvas, light, (x-43,y-91,84,70))
    for fx in (x-49,x+20):
        pygame.draw.ellipse(canvas, outline, (fx-8,y-29,42,29))
        pygame.draw.ellipse(canvas, light, (fx-3,y-25,32,21))
        pygame.draw.ellipse(canvas, (255,226,222), (fx+4,y-22,7,5))
    if species == "cat":
        pygame.draw.arc(canvas, outline, (x+47,y-100,55,65), 4.0, 1.7, 10)
        pygame.draw.arc(canvas, fur, (x+51,y-96,47,56), 4.0, 1.7, 7)
        pygame.draw.line(canvas, dark, (x+84,y-72),(x+94,y-60),3)
    elif species == "dog":
        pygame.draw.ellipse(canvas, outline, (x-81,y-167,47,75))
        pygame.draw.ellipse(canvas, dark, (x-76,y-162,36,65))
        pygame.draw.ellipse(canvas, outline, (x+34,y-166,47,75))
        pygame.draw.ellipse(canvas, dark, (x+39,y-161,36,65))
        pygame.draw.arc(canvas, outline, (x+53,y-110,40,38), 3.8, 1.4, 7)
    elif species == "hamster":
        pygame.draw.circle(canvas, outline, (x-43,y-136), 26)
        pygame.draw.circle(canvas, fur, (x-43,y-136), 21)
        pygame.draw.circle(canvas, inner, (x-43,y-136), 13)
        pygame.draw.circle(canvas, outline, (x+43,y-136), 26)
        pygame.draw.circle(canvas, fur, (x+43,y-136), 21)
        pygame.draw.circle(canvas, inner, (x+43,y-136), 13)
    elif species == "rabbit":
        pygame.draw.ellipse(canvas, outline, (x-50,y-214,37,99))
        pygame.draw.ellipse(canvas, light, (x-45,y-208,27,87))
        pygame.draw.ellipse(canvas, inner, (x-38,y-198,13,65))
        pygame.draw.ellipse(canvas, outline, (x+13,y-214,37,99))
        pygame.draw.ellipse(canvas, light, (x+18,y-208,27,87))
        pygame.draw.ellipse(canvas, inner, (x+25,y-198,13,65))
        pygame.draw.circle(canvas, light, (x+66,y-66), 15)

    # Large head with cheek fluff.
    head_top = y-166 if species != "rabbit" else y-158
    pygame.draw.ellipse(canvas, outline, (x-72,head_top,144,119))
    pygame.draw.ellipse(canvas, fur, (x-66,head_top+6,132,107))
    pygame.draw.ellipse(canvas, light, (x-53,head_top+28,106,72))
    # Species-specific face markings.
    if species == "cat":
        pygame.draw.polygon(canvas, dark, [(x-40,head_top+8),(x-27,head_top+37),(x-50,head_top+31)])
        pygame.draw.polygon(canvas, dark, [(x+40,head_top+8),(x+27,head_top+37),(x+50,head_top+31)])
        pygame.draw.line(canvas, dark, (x-31,head_top+14),(x-25,head_top+25),3)
        pygame.draw.line(canvas, dark, (x+31,head_top+14),(x+25,head_top+25),3)
    elif species == "dog":
        pygame.draw.ellipse(canvas, light, (x-24,head_top+8,48,44))
        pygame.draw.ellipse(canvas, dark, (x-18,head_top+37,36,24))
        pygame.draw.ellipse(canvas, (248,220,174), (x-54,head_top+63,39,25))
        pygame.draw.ellipse(canvas, (248,220,174), (x+15,head_top+63,39,25))
    elif species == "hamster":
        pygame.draw.ellipse(canvas, light, (x-60,head_top+54,43,34))
        pygame.draw.ellipse(canvas, light, (x+17,head_top+54,43,34))
        pygame.draw.ellipse(canvas, inner, (x-55,head_top+61,31,24))
        pygame.draw.ellipse(canvas, inner, (x+24,head_top+61,31,24))
    elif species == "rabbit":
        pygame.draw.ellipse(canvas, (255,250,241), (x-58,head_top+52,49,36))
        pygame.draw.ellipse(canvas, (255,250,241), (x+9,head_top+52,49,36))

    # Expressive eyes; sleep closes them with little curved eyelids.
    eye_y = head_top+49
    for ex in (x-32,x+32):
        if sleeping:
            pygame.draw.arc(canvas, outline, (ex-12, eye_y+3, 24, 13), math.pi, 2*math.pi, 3)
            pygame.draw.arc(canvas, outline, (ex-9, eye_y+3, 18, 10), math.pi, 2*math.pi, 2)
        else:
            pygame.draw.ellipse(canvas, outline, (ex-12,eye_y-2,24,29))
            pygame.draw.ellipse(canvas, eye, (ex-9,eye_y+1,18,22))
            pygame.draw.ellipse(canvas, outline, (ex-4,eye_y+3,10,18))
            pygame.draw.circle(canvas, (255,255,255), (ex-3,eye_y+5), 4)
            pygame.draw.circle(canvas, (255,255,255), (ex+4,eye_y+14), 2)

    # Tiny ;3-inspired mouth, flipped upside-down for every animal except the turtle.
    pygame.draw.ellipse(canvas, light, (x-19, head_top+73, 38, 24))
    pygame.draw.arc(canvas, outline, (x-7, head_top+79, 14, 9), math.pi+0.05, 2*math.pi-0.05, 2)
    pygame.draw.circle(canvas, (246,150,169), (x-43,head_top+78), 7)
    pygame.draw.circle(canvas, (246,150,169), (x+43,head_top+78), 7)
    if species == "cat":
        for side in (-1,1):
            for dy in (0,7):
                pygame.draw.line(canvas, dark, (x+side*38,head_top+83+dy),(x+side*59,head_top+78+dy),2)
    # Soft forehead tuft / markings.
    if species == "cat":
        pygame.draw.polygon(canvas, light, [(x-10,head_top+5),(x,head_top-7),(x+11,head_top+5)])
    elif species == "dog":
        pygame.draw.ellipse(canvas, (255,227,183), (x-10,head_top+13,20,27))
    elif species == "rabbit":
        pygame.draw.ellipse(canvas, (255,255,250), (x-8,head_top+10,16,23))
def draw_pet():
    species = active_pet
    sprite = load_image("pets", species)
    now = pygame.time.get_ticks()
    elapsed = (now - animation_started) / 1000 if active_animation else 99
    anim = active_animation if elapsed < 1.35 else None
    phase = now / 150.0

    # Each species has its own rhythm and action-specific movement.
    species_phase = {"cat": 0.0, "dog": 0.8, "hamster": 1.6, "rabbit": 2.3, "turtle": 3.0}.get(species, 0)
    bob = int(math.sin(phase + species_phase) * 2)
    # Keep the full animal visible in the central stage, clear of the HUD and bottom panels.
    center_x, base_y = 500, 472 + bob
    if anim == "play":
        base_y -= int(abs(math.sin(elapsed * 9 + species_phase)) * (17 if species != "turtle" else 7))
        center_x += int(math.sin(elapsed * 8 + species_phase) * 9)
    elif anim == "feed":
        base_y += int(math.sin(elapsed * 15) * 4)
        center_x += int(math.sin(elapsed * 12 + species_phase) * 3)
    elif anim == "clean":
        center_x += int(math.sin(elapsed * 18 + species_phase) * 7)
    elif anim == "pet":
        base_y -= int(abs(math.sin(elapsed * 8 + species_phase)) * 6)
    elif anim == "sleep":
        base_y += int(math.sin(elapsed * 4) * 2) + 4

    # A floor shadow helps sprites sit naturally in the room.
    pygame.draw.ellipse(canvas, (35, 31, 48), (center_x-95, 460 + bob, 190, 24))

    if sprite:
        # Scale proportionally (never squash/stretch) so ears, tails and feet stay visible.
        max_w, max_h = 238, 238
        ratio = min(max_w / sprite.get_width(), max_h / sprite.get_height())
        image_size = (max(1, int(sprite.get_width() * ratio)),
                      max(1, int(sprite.get_height() * ratio)))
        image = pygame.transform.smoothscale(sprite, image_size)
        if anim == "clean":
            image = pygame.transform.rotate(image, math.sin(elapsed * 18 + species_phase) * 3)
        image_x = center_x - image.get_width() // 2
        image_y = max(130, base_y - image.get_height() - 2)
        canvas.blit(image, (image_x, image_y))
        # Sleepy eyelids are placed relative to the scaled portrait, not fixed screen coordinates.
        if anim == "sleep":
            eye_y = image_y + int(image.get_height() * 0.40)
            eye_dx = int(image.get_width() * 0.17)
            for ex in (center_x - eye_dx, center_x + eye_dx):
                pygame.draw.arc(canvas, INK, (ex - 10, eye_y, 20, 12), math.pi, 2 * math.pi, 3)
    else:
        draw_pet_fallback(species, center_x, base_y, sleeping=(anim == "sleep"))

    # A cheerful expression/effect for cared-for pets, including pets using image assets.
    # The little floating hearts make the mood visibly happy without covering the face.
    pet_happy = pets[species]["happiness"] >= 65
    if pet_happy and anim in ("feed", "play", "pet", "clean"):
        for i in range(2):
            hx = center_x + (-58 if i == 0 else 58) + int(math.sin(elapsed * 5 + i) * 3)
            hy = base_y - 142 - int((elapsed * 24 + i * 18) % 18)
            heart_color = (245, 105, 145)
            pygame.draw.circle(canvas, heart_color, (hx-4, hy), 5)
            pygame.draw.circle(canvas, heart_color, (hx+4, hy), 5)
            pygame.draw.polygon(canvas, heart_color, [(hx-9,hy+1),(hx+9,hy+1),(hx,hy+11)])

    # Tiny action particles make every action feel responsive.
    if anim:
        colors = {"feed": GOLD, "play": PINK, "clean": BLUE, "sleep": PURPLE, "pet": PINK}
        color = colors.get(anim, GOLD)
        for i in range(3):
            drift = int((elapsed * 32 + i * 29) % 42)
            px = center_x + (-45 + i * 42) + int(math.sin(elapsed * 7 + i) * 4)
            py = base_y - 120 - drift
            if anim == "sleep":
                draw_text("z" if i % 2 else "Z", px, py, TINY, color, center=True)
            else:
                tiny_sparkle(px, py, color, 3)


# ---------- Pet stats and status ----------
STAT_COLORS = {
    "hunger": PINK,
    "happiness": GOLD,
    "energy": BLUE,
    "cleanliness": GREEN,
}

STAT_LABELS = {
    "hunger": "HUNGER",
    "happiness": "HAPPY",
    "energy": "ENERGY",
    "cleanliness": "CLEAN",
}



def draw_stats():
    pet = pets[active_pet]
    # Layered cream panel with a dark frame and warm inner edge.
    pygame.draw.rect(canvas, INK, (225, 514, 550, 54), border_radius=7)
    pygame.draw.rect(canvas, (255, 245, 220), (230, 518, 540, 46), border_radius=5)
    pygame.draw.rect(canvas, (229, 205, 176), (234, 521, 532, 40), 1, border_radius=4)
    for i, key in enumerate(STAT_LABELS):
        x = 246 + i * 132
        value = pet[key]
        color = STAT_COLORS[key]
        draw_text(STAT_LABELS[key].title(), x, 523, TINY, INK)
        draw_text(f"{value}%", x+104, 523, TINY, INK, center=True)
        pygame.draw.rect(canvas, (73, 62, 78), (x, 542, 106, 11), border_radius=3)
        pygame.draw.rect(canvas, (219, 207, 189), (x+2, 544, 102, 7), border_radius=2)
        fill_width = int(102 * value / 100)
        if fill_width:
            pygame.draw.rect(canvas, color, (x+2, 544, fill_width, 7), border_radius=2)


def soft_panel(x, y, w, h, fill, outline=None, radius=14, shadow=True):
    """Rounded, layered UI panel with a soft pixel-art drop shadow."""
    if shadow:
        pygame.draw.rect(canvas, (24, 23, 38), (x + 4, y + 5, w, h), border_radius=radius)
        pygame.draw.rect(canvas, (42, 38, 57), (x + 2, y + 3, w, h), border_radius=radius)
    pygame.draw.rect(canvas, fill, (x, y, w, h), border_radius=radius)
    # subtle top highlight and bottom edge make the panel feel raised
    pygame.draw.line(canvas, tuple(min(255, c + 22) for c in fill),
                     (x + radius, y + 2), (x + w - radius, y + 2), 2)
    if outline:
        pygame.draw.rect(canvas, outline, (x, y, w, h), 2, border_radius=radius)


def tiny_sparkle(x, y, color=CREAM, size=4):
    """Four-point twinkle used as a restrained decorative accent."""
    pygame.draw.line(canvas, color, (x, y - size), (x, y + size), 2)
    pygame.draw.line(canvas, color, (x - size, y), (x + size, y), 2)
    pygame.draw.circle(canvas, color, (x, y), 1)


# ---------- HUD ----------
def draw_hud():
    # Coin purse: warm cream card with a coin medallion.
    soft_panel(18, 14, 150, 55, (255, 248, 231), (225, 204, 164), 13)
    pygame.draw.circle(canvas, (127, 83, 41), (48, 42), 18)
    pygame.draw.circle(canvas, GOLD, (48, 40), 14)
    pygame.draw.circle(canvas, (255, 224, 125), (44, 36), 4)
    draw_text("$", 48, 41, FONT, (129, 81, 29), center=True)
    draw_text(coins, 78, 29, FONT, INK)

    # Room title sits on a little translucent-looking plaque.
    room = ROOMS[room_index].replace("livingroom", "living room")
    soft_panel(WIDTH // 2 - 125, 13, 250, 48, (54, 47, 72), (110, 91, 126), 14)
    draw_text(room.upper(), WIDTH // 2, 27, TITLE, CREAM, center=True)
    # Navigation arrows keep their original click zones.
    pygame.draw.circle(canvas, (69, 57, 87), (WIDTH // 2 - 151, 43), 21)
    pygame.draw.circle(canvas, GOLD, (WIDTH // 2 - 151, 43), 18, 2)
    pygame.draw.circle(canvas, (69, 57, 87), (WIDTH // 2 + 151, 43), 21)
    pygame.draw.circle(canvas, GOLD, (WIDTH // 2 + 151, 43), 18, 2)
    draw_text("<", WIDTH // 2 - 151, 31, BIG, GOLD, center=True)
    draw_text(">", WIDTH // 2 + 151, 31, BIG, GOLD, center=True)

    # Pause control.
    soft_panel(923, 14, 58, 55, (255, 248, 231), (225, 204, 164), 13)
    pygame.draw.rect(canvas, INK, (940, 28, 6, 26), border_radius=2)
    pygame.draw.rect(canvas, INK, (953, 28, 6, 26), border_radius=2)

    # Pet identity tag.
    pet = pets[active_pet]
    soft_panel(373, 75, 254, 40, (49, 43, 65), (112, 91, 125), 12, shadow=False)
    tiny_sparkle(391, 95, GOLD, 4)
    tiny_sparkle(609, 95, PINK, 4)
    draw_text(f"{pet['name']}  |  {active_pet.upper()}",
              WIDTH // 2, 88, SMALL, CREAM, center=True)

    # Care controls: clean, wide buttons with a simple drawn icon and readable label.
    # Icons are drawn with Pygame primitives so they never turn into missing-glyph squares.
    actions = [
        ("FEED", 130, GREEN, "feed"),
        ("PLAY", 220, PINK, "play"),
        ("CLEAN", 310, BLUE, "clean"),
        ("SLEEP", 400, PURPLE, "sleep"),
    ]
    for label, y, color, kind in actions:
        x, w, h = 940, 70, 50
        rect = pygame.Rect(x - w // 2, y - h // 2, w, h)
        pygame.draw.rect(canvas, (38, 33, 51), rect.move(0, 3), border_radius=16)
        pygame.draw.rect(canvas, (255, 250, 240), rect, border_radius=16)
        pygame.draw.rect(canvas, color, rect.inflate(-5, -5), border_radius=13)
        # Small, consistent line icons; no font glyphs required.
        cx, cy = x, y - 8
        dark = (57, 51, 69)
        if kind == "feed":
            pygame.draw.ellipse(canvas, dark, (cx - 12, cy - 4, 24, 11), 2)
            pygame.draw.arc(canvas, dark, (cx - 12, cy - 9, 24, 12), 0.1, 3.0, 2)
            pygame.draw.circle(canvas, dark, (cx - 5, cy - 1), 2)
            pygame.draw.circle(canvas, dark, (cx + 3, cy + 1), 2)
        elif kind == "play":
            pygame.draw.circle(canvas, dark, (cx, cy), 10, 2)
            pygame.draw.polygon(canvas, dark, [(cx - 3, cy - 5), (cx + 6, cy), (cx - 3, cy + 5)])
        elif kind == "clean":
            pygame.draw.line(canvas, dark, (cx - 8, cy + 6), (cx + 5, cy - 7), 4)
            pygame.draw.line(canvas, dark, (cx + 3, cy - 9), (cx + 9, cy - 3), 6)
            pygame.draw.line(canvas, (255, 255, 255), (cx - 10, cy - 7), (cx - 7, cy - 10), 2)
            pygame.draw.line(canvas, (255, 255, 255), (cx + 9, cy + 4), (cx + 12, cy + 1), 2)
        elif kind == "sleep":
            draw_text("Z", cx - 4, cy - 15, SMALL, dark, center=True)
            draw_text("z", cx + 7, cy - 5, TINY, dark, center=True)
        draw_text(label, x, y + 10, TINY, dark, center=True)

    # Compact icon-only sound toggle beneath SLEEP, with no text to overlap.
    mute_rect = pygame.Rect(919, 452, 42, 38)
    mute_color = (250, 205, 211) if sounds_muted else (205, 239, 202)
    pygame.draw.rect(canvas, (38, 33, 51), mute_rect.move(0, 3), border_radius=11)
    pygame.draw.rect(canvas, (255, 250, 240), mute_rect, border_radius=11)
    pygame.draw.rect(canvas, mute_color, mute_rect.inflate(-4, -4), border_radius=9)
    sx, sy = mute_rect.centerx - 2, mute_rect.centery
    pygame.draw.polygon(canvas, INK, [(sx - 8, sy - 5), (sx - 3, sy - 5),
                                      (sx + 4, sy - 11), (sx + 4, sy + 11),
                                      (sx - 3, sy + 5), (sx - 8, sy + 5)])
    if sounds_muted:
        pygame.draw.line(canvas, INK, (sx + 8, sy - 7), (sx + 16, sy + 7), 3)
        pygame.draw.line(canvas, INK, (sx + 16, sy - 7), (sx + 8, sy + 7), 3)
    else:
        pygame.draw.arc(canvas, INK, (sx + 1, sy - 9, 15, 18), -1.1, 1.1, 2)

    # Food refill shop: pay coins to restock every food type.
    refill_rect = pygame.Rect(18, 77, 150, 39)
    pygame.draw.rect(canvas, (38, 33, 51), refill_rect.move(0, 3), border_radius=11)
    pygame.draw.rect(canvas, (255, 250, 240), refill_rect, border_radius=11)
    pygame.draw.rect(canvas, (255, 224, 142), refill_rect.inflate(-4, -4), border_radius=9)
    draw_text("REFILL FOOD", refill_rect.centerx, refill_rect.y + 5, TINY, INK, center=True)
    draw_text("25 coins", refill_rect.centerx, refill_rect.y + 20, TINY, (129, 81, 29), center=True)

    # Petting button, using a simple hand/paw-like mark rather than a heart glyph.
    pet_rect = pygame.Rect(28, 393, 80, 76)
    pygame.draw.rect(canvas, (38, 33, 51), pet_rect.move(0, 3), border_radius=16)
    pygame.draw.rect(canvas, (255, 250, 240), pet_rect, border_radius=16)
    pygame.draw.rect(canvas, BLUE, pet_rect.inflate(-5, -5), border_radius=13)
    pygame.draw.circle(canvas, INK, (68, 418), 7)
    for px, py in [(58, 410), (65, 406), (73, 406), (80, 411)]:
        pygame.draw.circle(canvas, INK, (px, py), 3)
    draw_text("PET", 68, 443, TINY, INK, center=True)

    # Pet selector tray.
    soft_panel(155, 581, 690, 45, (51, 44, 67), (112, 91, 125), 13)
    draw_text("YOUR PETS", 207, 595, TINY, (218, 207, 229), center=True)
    for i, species in enumerate(SPECIES):
        x = 310 + i * 105
        selected = species == active_pet
        if selected:
            pygame.draw.rect(canvas, (255, 223, 129), (x - 43, 588, 86, 31), border_radius=9)
            pygame.draw.rect(canvas, GOLD, (x - 43, 588, 86, 31), 2, border_radius=9)
            draw_text(species.title(), x, 596, TINY, INK, center=True)
        else:
            draw_text(species.title(), x, 596, TINY, CREAM, center=True)

    # Inventory shelf with a clear selected state.
    soft_panel(210, 629, 580, 64, (255, 248, 231), (225, 204, 164), 13)
    draw_text("<", 238, 643, BIG, INK, center=True)
    draw_text(">", 762, 643, BIG, INK, center=True)

    visible_items = FOODS[item_page:item_page + 3]
    for i, item in enumerate(visible_items):
        index = item_page + i
        x = 340 + i * 160
        if index == selected_item:
            pygame.draw.rect(canvas, (255, 224, 142), (x - 53, 634, 106, 54), border_radius=10)
            pygame.draw.rect(canvas, (214, 153, 54), (x - 53, 634, 106, 54), 2, border_radius=10)
        else:
            pygame.draw.rect(canvas, (245, 235, 214), (x - 53, 634, 106, 54), border_radius=10)
            pygame.draw.rect(canvas, (224, 211, 188), (x - 53, 634, 106, 54), 1, border_radius=10)

        draw_food_icon(item, x, 648, 27)
        draw_text(FOOD_LABELS[item], x, 667, TINY, INK, center=True)
        count_color = (132, 83, 36) if inventory[item] else (184, 65, 78)
        draw_text(f"x{inventory[item]}", x + 36, 639, TINY, count_color, center=True)


def draw_message(now):
    # Keep the status bubble visible briefly, then gently fade it away.
    elapsed = now - message_started
    visible_for = 5000
    fade_duration = 500
    if elapsed >= visible_for:
        return
    opacity = 255
    if elapsed > visible_for - fade_duration:
        opacity = max(0, int(255 * (visible_for - elapsed) / fade_duration))

    bubble = pygame.Surface((560, 42), pygame.SRCALPHA)
    pygame.draw.rect(bubble, (255, 248, 231, opacity), (0, 0, 560, 30), border_radius=10)
    pygame.draw.rect(bubble, (225, 204, 164, opacity), (0, 0, 560, 30), width=1, border_radius=10)
    pygame.draw.polygon(bubble, (255, 248, 231, opacity), [(268, 30), (280, 39), (292, 30)])
    pygame.draw.circle(bubble, (*PINK, opacity), (18, 15), 3)
    text_surface = TINY.render(message, True, INK)
    text_surface.set_alpha(opacity)
    bubble.blit(text_surface, (280 - text_surface.get_width() // 2, 7))
    canvas.blit(bubble, (220, 462))


# ---------- Gameplay ----------
def clamp_pet(pet):
    for key in ("hunger", "happiness", "energy", "cleanliness"):
        pet[key] = max(0, min(100, int(pet[key])))


def perform_action(action):
    global coins, message, active_animation, animation_started, game_over

    if game_over:
        return

    active_animation = action
    animation_started = pygame.time.get_ticks()
    # Each animal makes its own signature call when you interact with it.
    play_sound("animal_" + active_pet)
    pet = pets[active_pet]

    if action == "feed":
        # Don't consume food or coins when the active pet is already fully fed.
        if pet["hunger"] >= 100:
            message = f"{pet['name']} is already full!"
            return

        item = FOODS[selected_item]
        if inventory[item] <= 0:
            message = f"You're out of {FOOD_LABELS[item].lower()}! Choose another item."
            return

        inventory[item] -= 1
        pet["hunger"] += 18
        pet["happiness"] += 3
        pet["cleanliness"] -= 2
        message = f"{pet['name']} enjoyed the {FOOD_LABELS[item].lower()}!"

    elif action == "play":
        pet["happiness"] += 18
        pet["energy"] -= 13
        pet["hunger"] -= 7
        message = f"{pet['name']} had fun playing with you!"

    elif action == "pet":
        pet["happiness"] += 10
        message = f"{pet['name']} loves spending time with you!"

    elif action == "clean":
        pet["cleanliness"] += 25
        pet["happiness"] -= 5
        message = f"{pet['name']} is feeling fresh and clean!"

    elif action == "sleep":
        pet["energy"] += 25
        pet["hunger"] -= 4
        message = f"{pet['name']} had a lovely little nap."

    clamp_pet(pet)
    # Every successful care action earns coins, not just playing.
    coins += 2
    # Check every pet and every need after each care action, too.
    check_game_over()
    save_game()


def switch_pet(species):
    global active_pet, message
    if species in pets:
        play_sound("select")
        active_pet = species
        message = f"You're hanging out with {pets[species]['name']} now!"
        save_game()


def change_room(direction):
    global room_index, message
    room_index = (room_index + direction) % len(ROOMS)
    play_sound("room")
    message = f"Welcome to the {ROOMS[room_index].replace('livingroom', 'living room')}!"
    save_game()


def handle_click(position):
    global paused, selected_item, item_page, message, sounds_muted, game_over, coins, pets, inventory, active_pet, room_index, last_decay

    x, y = position

    if game_over:
        # Starting again resets the whole run: all pets, food, coins, and room.
        if 350 <= x <= 650 and 365 <= y <= 430:
            pets = {species: data.copy() for species, data in PET_DEFAULTS.items()}
            inventory = DEFAULT_INVENTORY.copy()
            coins = 120
            active_pet = "cat"
            room_index = 0
            selected_item = 0
            item_page = 0
            paused = False
            game_over = False
            last_decay = pygame.time.get_ticks()
            message = "Welcome home! Choose an item or spend time with your pet."
            play_sound("select")
            save_game()
        return

    # Pause button
    if 915 <= x <= 990 and 10 <= y <= 80:
        paused = not paused
        play_sound("click")
        message = "Game paused." if paused else "Welcome back!"
        return

    if paused:
        return

    # Room arrows around the title
    if 330 <= x <= 390 and 15 <= y <= 70:
        change_room(-1)
        return
    if 610 <= x <= 670 and 15 <= y <= 70:
        change_room(1)
        return

    # Icon-only sound toggle directly below SLEEP.
    if 919 <= x <= 961 and 452 <= y <= 490:
        sounds_muted = not sounds_muted
        if not sounds_muted:
            play_sound("click")
        message = "Sounds muted." if sounds_muted else "Sounds are on!"
        return

    # Refill every food type for 25 coins, so running out never blocks care.
    if 18 <= x <= 168 and 77 <= y <= 116:
        refill_cost = 25
        refill_amount = 3
        foods_to_refill = [food for food in FOODS if inventory[food] < 100]
        if not foods_to_refill:
            message = "Your food inventory is full (100 max for each food)!"
        elif coins < refill_cost:
            message = "You need 25 coins to refill food. Play to earn coins!"
        else:
            coins -= refill_cost
            for food in foods_to_refill:
                inventory[food] = min(100, inventory[food] + refill_amount)
            message = "Food restocked! +3 of each available food (100 max each)."
            play_sound("select")
            save_game()
        return

    # Care buttons
    if x >= 895:
        if 95 <= y <= 165:
            perform_action("feed")
        elif 185 <= y <= 255:
            perform_action("play")
        elif 275 <= y <= 345:
            perform_action("clean")
        elif 365 <= y <= 435:
            perform_action("sleep")
        return

    # Petting
    if 25 <= x <= 110 and 390 <= y <= 475:
        perform_action("pet")
        return

    # Animal selector
    if 155 <= x <= 845 and 580 <= y <= 628:
        for i, species in enumerate(SPECIES):
            center_x = 310 + i * 105
            if abs(x - center_x) <= 43:
                switch_pet(species)
                return

    # Food selector arrows
    if 210 <= x <= 270 and 630 <= y <= 695:
        item_page = (item_page - 3) % len(FOODS)
        selected_item = item_page
        play_sound("select")
        return

    if 730 <= x <= 790 and 630 <= y <= 695:
        item_page = (item_page + 3) % len(FOODS)
        selected_item = item_page
        play_sound("select")
        return

    # Click food card
    if 280 <= x <= 720 and 630 <= y <= 695:
        for i in range(3):
            center_x = 340 + i * 160
            if abs(x - center_x) <= 53:
                index = item_page + i
                if index < len(FOODS):
                    selected_item = index
                    play_sound("select")
                    return


def check_game_over():
    """End the run as soon as any pet's hunger, happiness, energy, or cleanliness reaches zero."""
    global game_over, message
    if game_over:
        return True

    for pet in pets.values():
        # Check each need independently so matching hunger/energy values cannot hide a failure.
        failed_stat = next(
            (key for key in ("hunger", "happiness", "energy", "cleanliness") if pet[key] <= 0),
            None,
        )
        if failed_stat is not None:
            game_over = True
            stat_names = {
                "hunger": "hunger", "happiness": "happiness",
                "energy": "energy", "cleanliness": "cleanliness",
            }
            message = f"Oh no! {pet['name']} ran out of {stat_names[failed_stat]}. Game over!"
            return True
    return False


def decay_stats():
    """Decrease needs at different rates and check for game over immediately."""
    global game_over, message
    if game_over:
        return

    # Different rates keep the bars from simply matching one another over time.
    decay_amounts = {"hunger": 1, "happiness": 1, "energy": 1, "cleanliness": 1}
    for pet in pets.values():
        for key, amount in decay_amounts.items():
            pet[key] = max(0, pet[key] - amount)

    # Any need reaching exactly zero ends the game, including energy.
    check_game_over()


def current_message():
    pet = pets[active_pet]
    for key in ("hunger", "happiness", "energy", "cleanliness"):
        if pet[key] <= 20:
            return f"{pet['name']} needs attention! Check their stats."
    return None


# ---------- Main loop ----------
load_game()

while running:
    clock.tick(FPS)
    now = pygame.time.get_ticks()
    if message != last_displayed_message:
        last_displayed_message = message
        message_started = now

    if not paused and not game_over and now - last_decay >= 30000:
        decay_stats()
        last_decay = now
        warning = current_message()
        if warning:
            message = warning
        save_game()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            save_game()
            running = False

        elif event.type == pygame.VIDEORESIZE and not fullscreen:
            window = pygame.display.set_mode(event.size, pygame.RESIZABLE)

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_x = int(event.pos[0] * WIDTH / window.get_width())
            mouse_y = int(event.pos[1] * HEIGHT / window.get_height())
            handle_click((mouse_x, mouse_y))

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_F11:
                fullscreen = not fullscreen
                if fullscreen:
                    window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)

            elif event.key == pygame.K_ESCAPE:
                if fullscreen:
                    fullscreen = False
                    window = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                else:
                    paused = not paused

            elif event.key == pygame.K_LEFT and not paused:
                item_page = (item_page - 3) % len(FOODS)
                selected_item = item_page

            elif event.key == pygame.K_RIGHT and not paused:
                item_page = (item_page + 3) % len(FOODS)
                selected_item = item_page

            elif event.key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5):
                if not paused:
                    switch_pet(SPECIES[event.key - pygame.K_1])

            elif event.key == pygame.K_q and not paused:
                change_room(-1)

            elif event.key == pygame.K_e and not paused:
                change_room(1)

            elif event.key == pygame.K_SPACE and not paused:
                perform_action("pet")

    # Draw scene
    draw_room()
    draw_pet()
    draw_message(now)
    draw_stats()
    draw_hud()

    if game_over:
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((24, 20, 35, 205))
        canvas.blit(shade, (0, 0))
        soft_panel(260, 245, 480, 220, (255, 246, 225), (226, 190, 135), 22)
        draw_text("GAME OVER", WIDTH // 2, 278, BIG, (144, 62, 83), center=True)
        draw_text("One of your pet's needs reached zero.", WIDTH // 2, 326, SMALL, INK, center=True)
        restart_rect = pygame.Rect(350, 365, 300, 60)
        pygame.draw.rect(canvas, (142, 103, 185), restart_rect, border_radius=16)
        draw_text("CARE FOR PETS AGAIN", restart_rect.centerx, restart_rect.y + 17, SMALL, CREAM, center=True)

    if paused and not game_over:
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((15, 14, 25, 190))
        canvas.blit(shade, (0, 0))
        draw_text("PAUSED", WIDTH // 2, 310, BIG, CREAM, center=True)
        draw_text("ESC to resume  |  F11 fullscreen", WIDTH // 2, 360,
                  SMALL, CREAM, center=True)

    # Scale to the current window or fullscreen display.
    scaled = pygame.transform.scale(canvas, window.get_size())
    window.blit(scaled, (0, 0))
    pygame.display.flip()

pygame.quit()