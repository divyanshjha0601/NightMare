from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from panda3d.core import Filename
from pathlib import Path
from array import array
from types import SimpleNamespace
import random
import math
import heapq
import wave
import sys

# =========================================================
# NIGHTMARE: THE ABANDONED HOUSE   (v2 - Horror Edition)
# Python + Ursina
#
# Install:  pip install ursina
# Run:      python nightmare_game.py
#
# NEW IN THIS VERSION
#  - 4x4 = 16 rooms, har run mein random maze layout
#  - 5 keys dhoondni hain (sab keys = exit khulega)
#  - Batteries (flashlight ki battery drain hoti hai)
#  - Smart monster: patrol -> sunta/dekhta hai -> chase -> search
#  - Horror sounds (khud generate hote hain, koi file download nahi)
#  - Flickering light, blackout, heartbeat, whispers, jumpscare
#  - Map (M ya TAB), stamina, sprint
# =========================================================

app = Ursina()  # type: ignore

window.title = "NIGHTMARE - The Abandoned House"
window.exit_button.visible = False
window.fps_counter.enabled = True


def rgb255(r, g, b, a=255):
    """0-255 colour -> Ursina colour (0-1 floats)."""
    return Color(r / 255, g / 255, b / 255, a / 255)


def clamp01(v):
    return max(0.0, min(1.0, v))


# ---------------- CONFIGURATION --------------------------

ROOMS = 4                       # 4 x 4 rooms
ROOM_SIZE = 12
HOUSE_SIZE = ROOMS * ROOM_SIZE  # 48
half = HOUSE_SIZE / 2
WALL_HEIGHT = 4
T = 0.5                         # wall thickness
DOOR_W = 3.6

NUM_KEYS = 5
NUM_BATTERIES = 4
BATTERY_SECONDS = 200           # full battery kitni der chalti hai

PLAYER_SPEED = 4.5
SPRINT_SPEED = 7.5
STAMINA_DRAIN = 0.40
STAMINA_REGEN = 0.20
STAMINA_MIN_TO_SPRINT = 0.25

MONSTER_PATROL = 2.3
MONSTER_SEARCH = 3.0
MONSTER_CHASE = 3.9             # + 0.25 per key collected
MONSTER_CATCH_DISTANCE = 1.3
SIGHT_LIGHT_ON = 18
SIGHT_LIGHT_OFF = 9
HEAR_WALK = 4.5
HEAR_SPRINT = 13

EXIT_COL = ROOMS - 1
EXIT_X = -half + ROOM_SIZE * (EXIT_COL + 0.5)

FOG_COLOR = rgb255(6, 6, 10)

# ---------------- COLORS ---------------------------------

WALL_TINTS = [rgb255(118, 106, 110), rgb255(104, 108, 100), rgb255(120, 98, 94)]
FLOOR_TINTS = [rgb255(62, 55, 50), rgb255(50, 50, 56), rgb255(66, 52, 46), rgb255(44, 48, 44)]
CRATE_COLOR = rgb255(100, 72, 46)
RED_COLOR = rgb255(180, 15, 25)

window.color = FOG_COLOR
scene.fog_color = FOG_COLOR
scene.fog_density = (1.5, 17)

# =========================================================
# SOUND  (sab sounds code se generate hote hain)
# =========================================================
# ===SOUND_START===
SR = 22050
TAU = 2 * math.pi
SOUND_DIR = Path(__file__).resolve().parent / "nightmare_sounds"


def _n(sec):
    return int(SR * sec)


def _noise(n):
    return [random.uniform(-1, 1) for _ in range(n)]


def _lp(x, a):
    y = []
    p = 0.0
    for s in x:
        p += a * (s - p)
        y.append(p)
    return y


def _save(name, data):
    SOUND_DIR.mkdir(exist_ok=True)
    peak = max(1e-6, max(abs(s) for s in data))
    arr = array('h', (int(max(-1.0, min(1.0, s / peak * 0.9)) * 32767) for s in data))
    if sys.byteorder == 'big':
        arr.byteswap()
    with wave.open(str(SOUND_DIR / (name + ".wav")), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(arr.tobytes())


def gen_drone():
    out = []
    for i in range(_n(8.0)):
        t = i / SR
        v = (0.50 * math.sin(TAU * 55.0 * t) + 0.40 * math.sin(TAU * 55.5 * t)
             + 0.28 * math.sin(TAU * 82.5 * t) + 0.12 * math.sin(TAU * 110.25 * t)
             + 0.05 * math.sin(TAU * 233.0 * t) * (0.5 + 0.5 * math.sin(TAU * 0.125 * t)))
        out.append(v * (0.7 + 0.3 * math.sin(TAU * 0.25 * t)))
    return out


def gen_heart():
    out = []
    for i in range(_n(1.0)):
        t = i / SR
        v = 0.0
        for t0, amp in ((0.0, 1.0), (0.24, 0.7)):
            d = t - t0
            if d >= 0:
                v += amp * math.sin(TAU * 52 * d) * math.exp(-d * 20)
        out.append(v)
    return out


def gen_step(a, f):
    n = _n(0.22)
    nz = _lp(_noise(n), a)
    return [nz[i] * 3 * math.exp(-(i / SR) * 28) + math.sin(TAU * f * i / SR) * math.exp(-(i / SR) * 35)
            for i in range(n)]


def gen_mstep():
    n = _n(0.45)
    nz = _lp(_noise(n), 0.06)
    return [math.sin(TAU * 45 * i / SR) * math.exp(-(i / SR) * 14)
            + nz[i] * 4 * math.exp(-(i / SR) * 10) for i in range(n)]


def gen_whisper(dur=2.4):
    n = _n(dur)
    raw = _noise(n)
    band = [a - b for a, b in zip(_lp(raw, 0.45), _lp(raw, 0.06))]
    env = [0.0] * n
    t = 0.1
    while t < dur - 0.3:
        L = random.uniform(0.10, 0.32)
        amp = random.uniform(0.4, 1.0)
        for i in range(int(t * SR), min(n, int((t + L) * SR))):
            u = (i / SR - t) / L
            env[i] = max(env[i], amp * math.sin(math.pi * u) ** 2)
        t += L + random.uniform(0.02, 0.18)
    return [band[i] * env[i] for i in range(n)]


def gen_growl():
    n = _n(1.9)
    ph = 0.0
    raw = []
    for i in range(n):
        t = i / SR
        f = 58 + 10 * math.sin(TAU * 5.5 * t) - 8 * t
        ph += f / SR
        saw = 2 * (ph % 1) - 1
        rumble = 0.6 + 0.4 * math.sin(TAU * 28 * t)
        env = min(1, t / 0.12) * math.exp(-t * 1.3)
        raw.append((saw * rumble + random.uniform(-1, 1) * 0.35) * env)
    return _lp(raw, 0.18)


def gen_scream():
    n = _n(1.5)
    ph = ph2 = 0.0
    out = []
    for i in range(n):
        t = i / SR
        f = 650 + 500 * math.sin(TAU * 2.2 * t) + 700 * t
        ph += f / SR
        ph2 += (f * 1.51) / SR
        v = math.tanh(3.0 * ((2 * (ph % 1) - 1) * 0.6 + math.sin(TAU * ph2) * 0.5
                             + random.uniform(-1, 1) * 0.3))
        env = min(1, t / 0.02) * max(0.0, 1 - t / 1.5) ** 0.7
        out.append(v * env)
    return out


def gen_wail():
    n = _n(3.2)
    ph = 0.0
    out = []
    for i in range(n):
        t = i / SR
        f = 310 + 70 * math.sin(TAU * 0.6 * t) + 6 * math.sin(TAU * 5.2 * t) - 20 * t
        ph += f / SR
        env = math.sin(math.pi * t / 3.2) ** 1.6
        v = (math.sin(TAU * ph) + 0.5 * math.sin(TAU * ph * 2.01)
             + 0.25 * math.sin(TAU * ph * 3.02) + random.uniform(-1, 1) * 0.08) * env
        out.append(v)
    return out


def gen_knock():
    n = _n(1.3)
    out = [0.0] * n
    for t0 in (0.0, 0.38, 0.72):
        for i in range(int(t0 * SR), min(n, int((t0 + 0.25) * SR))):
            d = i / SR - t0
            out[i] += (math.sin(TAU * 85 * d) * math.exp(-d * 26)
                       + random.uniform(-1, 1) * 0.4 * math.exp(-d * 70))
    return out


def gen_creak():
    n = _n(1.9)
    ph = 0.0
    nz = _lp(_noise(n), 0.1)
    out = []
    for i in range(n):
        t = i / SR
        f = 120 + 110 * abs(math.sin(TAU * 0.55 * t)) + 30 * math.sin(TAU * 11 * t)
        ph += f / SR
        env = math.sin(math.pi * t / 1.9)
        out.append(((2 * (ph % 1) - 1) * 0.5 + nz[i] * 2) * env * (0.6 + 0.4 * math.sin(TAU * 37 * t)))
    return _lp(out, 0.28)


def gen_key():
    out = []
    for i in range(_n(1.4)):
        t = i / SR
        v = 0.0
        for f, t0 in ((1568, 0.0), (2093, 0.08), (2637, 0.16), (3136, 0.26)):
            d = t - t0
            if d >= 0:
                v += math.sin(TAU * f * d) * math.exp(-d * 5) * 0.5
        out.append(v)
    return out


def gen_pickup():
    out = []
    for i in range(_n(0.35)):
        t = i / SR
        f = 500 + 700 * t
        out.append(math.sin(TAU * f * t) * math.exp(-t * 7))
    return out


def gen_unlock():
    n = _n(1.6)
    nz = _lp(_noise(n), 0.2)
    out = []
    for i in range(n):
        t = i / SR
        v = math.sin(TAU * 55 * t) * math.exp(-t * 9) * 1.2 + nz[i] * 3 * math.exp(-t * 30)
        d = t - 0.15
        if d >= 0:
            v += (math.sin(TAU * 880 * d) * 0.25 + math.sin(TAU * 1330 * d) * 0.15) * math.exp(-d * 4.5)
        out.append(v)
    return out


def gen_locked():
    n = _n(0.7)
    out = [0.0] * n
    for t0 in (0.0, 0.12, 0.24):
        for i in range(int(t0 * SR), min(n, int((t0 + 0.12) * SR))):
            d = i / SR - t0
            out[i] += random.uniform(-1, 1) * math.exp(-d * 40) + math.sin(TAU * 140 * d) * math.exp(-d * 30)
    return out


def gen_breath():
    n = _n(1.6)
    nz = _lp(_noise(n), 0.2)
    return [nz[i] * math.sin(math.pi * i / n) ** 2 for i in range(n)]


def gen_buzz():
    n = _n(0.5)
    out = []
    for i in range(n):
        t = i / SR
        gate = 1.0 if int(t * 40) % 3 else 0.1
        saw = 2 * ((100 * t) % 1) - 1
        out.append((saw + random.uniform(-1, 1) * 0.5) * gate * math.exp(-t * 3))
    return out


def gen_click():
    n = _n(0.06)
    return [random.uniform(-1, 1) * math.exp(-(i / SR) * 90)
            + math.sin(TAU * 1200 * i / SR) * math.exp(-(i / SR) * 100) for i in range(n)]


SOUND_MAKERS = {
    "drone": gen_drone, "heart": gen_heart,
    "foot1": lambda: gen_step(0.12, 75), "foot2": lambda: gen_step(0.20, 62),
    "mstep": gen_mstep,
    "whisper1": gen_whisper, "whisper2": gen_whisper, "whisper3": gen_whisper,
    "growl": gen_growl, "scream": gen_scream, "wail": gen_wail,
    "knock": gen_knock, "creak": gen_creak, "key": gen_key,
    "pickup": gen_pickup, "unlock": gen_unlock, "locked": gen_locked,
    "breath": gen_breath, "buzz": gen_buzz, "click": gen_click,
}


def build_sounds():
    missing = [n for n in SOUND_MAKERS if not (SOUND_DIR / (n + ".wav")).exists()]
    if missing:
        print("Horror sounds generate ho rahi hain (sirf pehli baar)...")
    for n in missing:
        _save(n, SOUND_MAKERS[n]())
# ===SOUND_END===


SFX = {}
try:
    build_sounds()
    for _name in SOUND_MAKERS:
        SFX[_name] = app.loader.loadSfx(Filename.fromOsSpecific(str(SOUND_DIR / (_name + ".wav"))))
except Exception as ex:  # game bina sound ke bhi chalega
    print("Audio load nahi hua:", ex)
    SFX = {}

WHISPERS = ("whisper1", "whisper2", "whisper3")


def play(name, vol=1.0, rate=1.0, pan=0.0):
    s = SFX.get(name)
    if s is None:
        return
    s.setVolume(clamp01(vol))
    s.setPlayRate(rate)
    s.setBalance(max(-1.0, min(1.0, pan)))
    s.play()


for _loop in ("drone", "heart"):
    if _loop in SFX:
        SFX[_loop].setLoop(True)
        SFX[_loop].setVolume(0.0)
        SFX[_loop].play()


def set_loops(drone_vol, heart_vol, heart_rate=1.0):
    if "drone" in SFX:
        SFX["drone"].setVolume(clamp01(drone_vol))
    if "heart" in SFX:
        SFX["heart"].setVolume(clamp01(heart_vol))
        SFX["heart"].setPlayRate(heart_rate)


def dvol(d, maxd):
    return clamp01(1 - d / maxd) ** 1.5


# =========================================================
# LEVEL GENERATION  (random 4x4 maze of rooms)
# =========================================================

obstacles = []      # (cx, cz, sx, sz) - pathfinding grid ke liye
wall_rects = []     # sirf walls - map ke liye


def add_solid(cx, cz, sx, sz, height, tint, tex="brick", tex_scale=None, is_wall=False):
    e = Entity(
        model="cube",
        position=(cx, height / 2, cz),
        scale=(sx, height, sz),
        color=tint,
        texture=tex,
        collider="box",
    )
    if tex_scale is not None:
        e.texture_scale = tex_scale
    obstacles.append((cx, cz, sx, sz))
    if is_wall:
        wall_rects.append((cx, cz, sx, sz))
    return e


def room_center(i, j):
    return (-half + ROOM_SIZE * (i + 0.5), -half + ROOM_SIZE * (j + 0.5))


def room_of(x, z):
    i = max(0, min(ROOMS - 1, int((x + half) // ROOM_SIZE)))
    j = max(0, min(ROOMS - 1, int((z + half) // ROOM_SIZE)))
    return i, j


def edge(a, b):
    return tuple(sorted((a, b)))


# ----- maze: har room connected, plus kuch extra doors (loops) -----
open_edges = set()
visited = {(0, 0)}
stack = [(0, 0)]
while stack:
    c = stack[-1]
    nbrs = [(c[0] + dx, c[1] + dz) for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1))
            if 0 <= c[0] + dx < ROOMS and 0 <= c[1] + dz < ROOMS
            and (c[0] + dx, c[1] + dz) not in visited]
    if nbrs:
        n = random.choice(nbrs)
        open_edges.add(edge(c, n))
        visited.add(n)
        stack.append(n)
    else:
        stack.pop()

all_edges = ([edge((i, j), (i + 1, j)) for i in range(ROOMS - 1) for j in range(ROOMS)]
             + [edge((i, j), (i, j + 1)) for i in range(ROOMS) for j in range(ROOMS - 1)])
closed = [e for e in all_edges if e not in open_edges]
for e in random.sample(closed, min(5, len(closed))):
    open_edges.add(e)


def wall_seg(axis, line, a0, a1, has_gap):
    """axis 'h': wall along X at z=line.  axis 'v': wall along Z at x=line."""
    a0 -= T / 2
    a1 += T / 2
    mid = (a0 + a1) / 2
    pieces = [(a0, a1)] if not has_gap else [(a0, mid - DOOR_W / 2), (mid + DOOR_W / 2, a1)]
    tint = random.choice(WALL_TINTS)
    for p0, p1 in pieces:
        length = p1 - p0
        centre = (p0 + p1) / 2
        ts = (length / 2.5, WALL_HEIGHT / 2.5)
        if axis == 'h':
            add_solid(centre, line, length, T, WALL_HEIGHT, tint, "brick", ts, True)
        else:
            add_solid(line, centre, T, length, WALL_HEIGHT, tint, "brick", ts, True)
    if has_gap:   # dar ke upar ka hissa (no collider)
        if axis == 'h':
            Entity(model="cube", position=(mid, 3.4, line), scale=(DOOR_W, 1.2, T),
                   color=tint, texture="brick")
        else:
            Entity(model="cube", position=(line, 3.4, mid), scale=(T, 1.2, DOOR_W),
                   color=tint, texture="brick")


# ----- floor / ceiling -----
floor = Entity(model="cube", position=(0, -0.2, 0), scale=(HOUSE_SIZE + 1, 0.4, HOUSE_SIZE + 1),
               color=rgb255(40, 36, 34), texture="white_cube", collider="box")
floor.texture_scale = (HOUSE_SIZE / 2, HOUSE_SIZE / 2)

ceiling = Entity(model="cube", position=(0, WALL_HEIGHT + 0.1, 0),
                 scale=(HOUSE_SIZE + 1, 0.2, HOUSE_SIZE + 1), color=rgb255(22, 20, 24))

for ri in range(ROOMS):
    for rj in range(ROOMS):
        cx, cz = room_center(ri, rj)
        fl = Entity(model="cube", position=(cx, 0.006, cz), scale=(ROOM_SIZE, 0.012, ROOM_SIZE),
                    color=random.choice(FLOOR_TINTS), texture="white_cube")
        fl.texture_scale = (ROOM_SIZE / 2, ROOM_SIZE / 2)

# ----- walls -----
for ri in range(ROOMS):
    for rj in range(ROOMS):
        x0 = -half + ROOM_SIZE * ri
        z0 = -half + ROOM_SIZE * rj
        if ri < ROOMS - 1:
            wall_seg('v', x0 + ROOM_SIZE, z0, z0 + ROOM_SIZE,
                     edge((ri, rj), (ri + 1, rj)) in open_edges)
        if rj < ROOMS - 1:
            wall_seg('h', z0 + ROOM_SIZE, x0, x0 + ROOM_SIZE,
                     edge((ri, rj), (ri, rj + 1)) in open_edges)
        if ri == 0:
            wall_seg('v', -half, z0, z0 + ROOM_SIZE, False)
        if ri == ROOMS - 1:
            wall_seg('v', half, z0, z0 + ROOM_SIZE, False)
        if rj == 0:
            wall_seg('h', -half, x0, x0 + ROOM_SIZE, False)
        if rj == ROOMS - 1:
            wall_seg('h', half, x0, x0 + ROOM_SIZE, ri == EXIT_COL)

# ----- locked exit door -----
exit_light = Entity(model="cube", position=(EXIT_X, 1.4, half + 0.9), scale=(DOOR_W + 1, 2.8, 0.1),
                    color=rgb255(200, 210, 225))
exit_door = Entity(model="cube", position=(EXIT_X, 1.4, half), scale=(DOOR_W, 2.8, T * 0.8),
                   color=rgb255(72, 26, 26), texture="white_cube", collider="box")
exit_lock = Entity(model="cube", position=(EXIT_X, 1.3, half - 0.35), scale=(0.35, 0.4, 0.15),
                   color=color.yellow)
obstacles.append((EXIT_X, half, DOOR_W, T))   # monster bahar na nikle

# ----- props, decorations -----


def wall_decor(cx, cz, side, off, y, w, h, tint, inset=0.0, thick=0.04):
    d = ROOM_SIZE / 2 - T / 2 - 0.03 - inset
    if side == 'N':
        pos, sc = (cx + off, y, cz + d), (w, h, thick)
    elif side == 'S':
        pos, sc = (cx + off, y, cz - d), (w, h, thick)
    elif side == 'E':
        pos, sc = (cx + d, y, cz + off), (thick, h, w)
    else:
        pos, sc = (cx - d, y, cz + off), (thick, h, w)
    return Entity(model="cube", position=pos, scale=sc, color=tint)


def rand_off(lo=2.6, hi=4.8):
    return random.choice((-1, 1)) * random.uniform(lo, hi)


def portrait(cx, cz):
    side = random.choice("NSEW")
    off = rand_off()
    y = 2.1
    wall_decor(cx, cz, side, off, y, 1.0, 1.3, rgb255(35, 22, 15))
    wall_decor(cx, cz, side, off, y, 0.8, 1.1, rgb255(150, 140, 125), inset=0.03)
    eye = RED_COLOR if random.random() < 0.18 else rgb255(8, 8, 8)
    for s in (-1, 1):
        wall_decor(cx, cz, side, off + s * 0.17, y + 0.15, 0.11, 0.07, eye, inset=0.05)
    wall_decor(cx, cz, side, off, y - 0.25, 0.30, 0.04, rgb255(10, 5, 5), inset=0.05)


def make_prop(cx, cz):
    kind = random.choice(("crate", "crate", "table", "wardrobe", "bed", "boxes"))
    if kind == "crate":
        s = random.uniform(1.3, 2.1)
        add_solid(cx, cz, s, s, random.uniform(1.0, 1.5), CRATE_COLOR, "white_cube", (1, 1))
    elif kind == "table":
        a, b = (2.2, 1.3) if random.random() < 0.5 else (1.3, 2.2)
        add_solid(cx, cz, a, b, 0.9, rgb255(80, 56, 38), "white_cube", (1, 1))
    elif kind == "wardrobe":
        a, b = (1.9, 0.9) if random.random() < 0.5 else (0.9, 1.9)
        add_solid(cx, cz, a, b, 2.8, rgb255(50, 34, 26), "white_cube", (1, 1))
    elif kind == "bed":
        a, b = (2.2, 1.4) if random.random() < 0.5 else (1.4, 2.2)
        add_solid(cx, cz, a, b, 0.7, rgb255(92, 86, 96), "white_cube", (1, 1))
    else:
        add_solid(cx, cz, 1.6, 1.6, 1.0, rgb255(88, 70, 50), "white_cube", (1, 1))
        add_solid(cx + 0.2, cz + 0.1, 1.0, 1.0, 1.9, rgb255(76, 60, 44), "white_cube", (1, 1))


corner_offsets = [(4.2, 4.2), (4.2, -4.2), (-4.2, 4.2), (-4.2, -4.2)]

for ri in range(ROOMS):
    for rj in range(ROOMS):
        cx, cz = room_center(ri, rj)
        for ox, oz in random.sample(corner_offsets, random.randint(2, 3)):
            make_prop(cx + ox, cz + oz)
        if random.random() < 0.55:
            Entity(model="cube", position=(cx, 0.014, cz),
                   scale=(random.uniform(5, 7), 0.02, random.uniform(4, 6)),
                   color=random.choice((rgb255(70, 20, 22), rgb255(30, 44, 36), rgb255(48, 38, 28))))
        if random.random() < 0.8:
            portrait(cx, cz)
        for _ in range(random.randint(1, 3)):     # wall blood
            wall_decor(cx, cz, random.choice("NSEW"), rand_off(2.6, 5.0), random.uniform(0.8, 3.0),
                       random.uniform(0.3, 1.2), random.uniform(0.4, 1.6),
                       rgb255(random.randint(80, 140), 5, 10), thick=0.03)
        for _ in range(random.randint(2, 5)):     # floor stains
            Entity(model="cube",
                   position=(cx + random.uniform(-5, 5), 0.02, cz + random.uniform(-5, 5)),
                   scale=(random.uniform(0.3, 1.2), 0.01, random.uniform(0.3, 1.2)),
                   rotation_y=random.randint(0, 90),
                   color=random.choice((rgb255(90, 8, 12), rgb255(26, 22, 24))))

# =========================================================
# PLAYER
# =========================================================

START_ROOM = (0, 0)
EXIT_ROOM = (EXIT_COL, ROOMS - 1)
MONSTER_ROOM = (ROOMS - 2, 2)
START_POSITION = Vec3(*(lambda c: (c[0], 0, c[1]))(room_center(*START_ROOM)))
MONSTER_START = Vec3(*(lambda c: (c[0], 0, c[1]))(room_center(*MONSTER_ROOM)))

player = FirstPersonController(
    position=START_POSITION,
    speed=PLAYER_SPEED,
    jump_height=1.2,
    gravity=0.8,
)
player.cursor.visible = False
NORMAL_SENSITIVITY = Vec2(40, 40)
player.mouse_sensitivity = NORMAL_SENSITIVITY

# =========================================================
# PICKUPS (keys + batteries)
# =========================================================

pickups = []


def make_key_model(pos):
    root = Entity(position=pos)
    Entity(parent=root, model="cube", scale=(0.55, 0.12, 0.12), color=color.yellow)
    Entity(parent=root, model="sphere", position=(-0.33, 0, 0), scale=0.28, color=color.yellow)
    Entity(parent=root, model="cube", position=(0.2, -0.12, 0), scale=(0.08, 0.16, 0.12), color=color.yellow)
    Entity(parent=root, model="cube", position=(0.08, -0.1, 0), scale=(0.08, 0.12, 0.12), color=color.yellow)
    return root


def make_battery_model(pos):
    root = Entity(position=pos)
    Entity(parent=root, model="cube", scale=(0.22, 0.4, 0.22), color=rgb255(40, 190, 70))
    Entity(parent=root, model="cube", position=(0, 0.25, 0), scale=(0.09, 0.08, 0.09), color=rgb255(200, 200, 200))
    return root


def spawn_pickups():
    for p in pickups:
        destroy(p["root"])
    pickups.clear()
    cands = [(i, j) for i in range(ROOMS) for j in range(ROOMS)
             if (i, j) not in (START_ROOM, EXIT_ROOM, MONSTER_ROOM)]
    random.shuffle(cands)
    for (i, j) in cands[:NUM_KEYS]:
        cx, cz = room_center(i, j)
        pos = (cx + random.uniform(-1.5, 1.5), 1.0, cz + random.uniform(-1.5, 1.5))
        pickups.append(dict(kind="key", root=make_key_model(pos), base_y=1.0,
                            taken=False, phase=random.uniform(0, 6)))
    for (i, j) in random.sample(cands, NUM_BATTERIES):
        cx, cz = room_center(i, j)
        pos = (cx + random.choice((-2, 2)), 0.6, cz + random.choice((-2, 2)))
        pickups.append(dict(kind="battery", root=make_battery_model(pos), base_y=0.6,
                            taken=False, phase=random.uniform(0, 6)))


spawn_pickups()

# =========================================================
# MONSTER  (lamba, patla, creepy)
# =========================================================

monster = Entity(position=MONSTER_START)
SKIN = rgb255(66, 58, 62)

Entity(parent=monster, model="cube", position=(0, 1.55, 0), scale=(0.65, 1.5, 0.38), color=SKIN)
for lx in (-0.2, 0.2):
    Entity(parent=monster, model="cube", position=(lx, 0.55, 0), scale=(0.2, 1.1, 0.22), color=rgb255(48, 42, 46))
head = Entity(parent=monster, position=(0, 2.55, 0.08))
Entity(parent=head, model="sphere", scale=(0.52, 0.72, 0.52), color=rgb255(175, 168, 160))
for ex in (-0.12, 0.12):
    Entity(parent=head, model="sphere", position=(ex, 0.07, 0.22), scale=0.11, color=color.red)
Entity(parent=head, model="cube", position=(0, -0.2, 0.22), scale=(0.26, 0.07, 0.05), color=rgb255(8, 4, 4))

arm_pivots = []
for ax in (-0.45, 0.45):
    pv = Entity(parent=monster, position=(ax, 2.2, 0.05))
    Entity(parent=pv, model="cube", position=(0, -0.8, 0), scale=(0.11, 1.6, 0.11), color=SKIN)
    for cxo in (-0.04, 0, 0.04):
        Entity(parent=pv, model="cube", position=(cxo, -1.7, 0.03), scale=(0.02, 0.22, 0.02),
               color=rgb255(210, 205, 195))
    arm_pivots.append(pv)

# =========================================================
# HUD
# =========================================================

try:
    from PIL import Image
    _sz = 128
    _img = Image.new("RGBA", (_sz, _sz))
    _px = _img.load()
    for _y in range(_sz):
        for _x in range(_sz):
            _r = math.hypot(_x / (_sz - 1) - 0.5, _y / (_sz - 1) - 0.5) * 2
            _a = clamp01((_r - 0.55) / 0.85)
            _px[_x, _y] = (0, 0, 0, int(255 * (_a ** 1.4) * 0.85))
    Entity(parent=camera.ui, model="quad", texture=Texture(_img),
           scale=(window.aspect_ratio, 1), z=2)
except Exception:
    pass

danger_overlay = Entity(parent=camera.ui, model="quad", scale=(3, 1.5),
                        color=Color(0.6, 0, 0, 0), z=1.5)

title_text = Text(text="N I G H T M A R E", parent=camera.ui, position=(0, 0.46),
                  origin=(0, 0), scale=1.5, color=color.red)
objective_text = Text(text=f"Ghar mein {NUM_KEYS} keys dhoondo aur bhaag jao!", parent=camera.ui,
                      position=(-0.86, 0.42), scale=0.9, color=color.white)
timer_text = Text(text="Time: 0s", parent=camera.ui, position=(0.62, 0.47), scale=0.9, color=color.white)
keys_text = Text(text=f"KEYS: 0/{NUM_KEYS}", parent=camera.ui, position=(0.62, 0.43),
                 scale=1.1, color=color.yellow)
status_text = Text(text="", parent=camera.ui, position=(0, 0.05), origin=(0, 0),
                   scale=1.6, color=color.red, enabled=False)
toast_text = Text(text="", parent=camera.ui, position=(0, -0.22), origin=(0, 0),
                  scale=1.2, color=color.white, enabled=False)
hint_text = Text(
    text=("WASD: Move | Mouse: Look | Shift: Sprint | Space: Jump\n"
          "F: Flashlight | M/Tab: Map | P: Pause | R: Restart | Esc: Quit"),
    parent=camera.ui, position=(-0.86, -0.40), scale=0.65, color=rgb255(200, 200, 205))
crosshair = Text(text="+", parent=camera.ui, position=(0, 0), origin=(0, 0), scale=1.2, color=color.white)
exit_label = Text(text="Exit Open  >>>", parent=camera.ui, position=(0, 0.33),
                  origin=(0, 0), scale=2, color=color.lime, enabled=False)

stamina_bg = Entity(parent=camera.ui, model="quad", position=(-0.2, -0.45), origin=(-0.5, 0),
                    scale=(0.4, 0.014), color=rgb255(40, 40, 40))
stamina_fill = Entity(parent=camera.ui, model="quad", position=(-0.2, -0.45), origin=(-0.5, 0),
                      scale=(0.4, 0.014), color=rgb255(60, 200, 90), z=-0.01)
Text(text="STAMINA", parent=camera.ui, position=(-0.2, -0.43), scale=0.6, color=rgb255(200, 200, 200))

flashlight_body = Entity(parent=camera.ui, model="quad", position=(0.75, -0.38),
                         scale=(0.05, 0.16), rotation_z=-20, color=rgb255(70, 70, 75))
flashlight_lens = Entity(parent=camera.ui, model="quad", position=(0.77, -0.30),
                         scale=(0.07, 0.03), rotation_z=-20, color=rgb255(255, 240, 180), z=-0.01)
battery_bg = Entity(parent=camera.ui, model="quad", position=(0.60, -0.46), origin=(-0.5, 0),
                    scale=(0.2, 0.014), color=rgb255(40, 40, 40))
battery_fill = Entity(parent=camera.ui, model="quad", position=(0.60, -0.46), origin=(-0.5, 0),
                      scale=(0.2, 0.014), color=rgb255(230, 210, 60), z=-0.01)
Text(text="BATTERY", parent=camera.ui, position=(0.60, -0.44), scale=0.6, color=rgb255(200, 200, 200))

# ----- map (M / Tab) -----
MAP_K = 0.9 / HOUSE_SIZE
map_root = Entity(parent=camera.ui, enabled=False)
Entity(parent=map_root, model="quad", scale=(0.98, 0.98), color=Color(0, 0, 0, 0.88), z=0.2)
for (wcx, wcz, wsx, wsz) in wall_rects:
    Entity(parent=map_root, model="quad", position=(wcx * MAP_K, wcz * MAP_K, 0.1),
           scale=(max(wsx * MAP_K, 0.004), max(wsz * MAP_K, 0.004)), color=rgb255(170, 170, 180))
Entity(parent=map_root, model="quad", position=(EXIT_X * MAP_K, half * MAP_K, 0.05),
       scale=(DOOR_W * MAP_K, 0.012), color=color.lime)
Text(text="EXIT", parent=map_root, position=(EXIT_X * MAP_K - 0.02, half * MAP_K + 0.03),
     scale=0.7, color=color.lime)
Text(text="MAP  (M se band karo)", parent=map_root, position=(-0.45, 0.48), scale=0.8, color=color.white)
map_dot = Entity(parent=map_root, model="quad", scale=0.018, color=color.red, z=0.03)
map_pointer = Entity(parent=map_root, model="quad", scale=0.01, color=color.white, z=0.02)

# =========================================================
# PATHFINDING GRID
# =========================================================

CELL = 0.5
GRID_MIN = -HOUSE_SIZE / 2
GRID_N = int(HOUSE_SIZE / CELL)
MONSTER_RADIUS = 0.55

blocked = [[False] * GRID_N for _ in range(GRID_N)]
for (ocx, ocz, osx, osz) in obstacles:
    bx0 = ocx - osx / 2 - MONSTER_RADIUS
    bx1 = ocx + osx / 2 + MONSTER_RADIUS
    bz0 = ocz - osz / 2 - MONSTER_RADIUS
    bz1 = ocz + osz / 2 + MONSTER_RADIUS
    for gx in range(GRID_N):
        wx = GRID_MIN + (gx + 0.5) * CELL
        if wx < bx0 or wx > bx1:
            continue
        for gz in range(GRID_N):
            wz = GRID_MIN + (gz + 0.5) * CELL
            if bz0 <= wz <= bz1:
                blocked[gx][gz] = True


def world_to_cell(x, z):
    gx = int((x - GRID_MIN) / CELL)
    gz = int((z - GRID_MIN) / CELL)
    return (max(0, min(GRID_N - 1, gx)), max(0, min(GRID_N - 1, gz)))


def cell_to_world(gx, gz):
    return (GRID_MIN + (gx + 0.5) * CELL, GRID_MIN + (gz + 0.5) * CELL)


def is_blocked_world(x, z):
    gx, gz = world_to_cell(x, z)
    return blocked[gx][gz]


def nearest_free(cell, max_radius=8):
    if not blocked[cell[0]][cell[1]]:
        return cell
    for r in range(1, max_radius + 1):
        for dx in range(-r, r + 1):
            for dz in range(-r, r + 1):
                if max(abs(dx), abs(dz)) != r:
                    continue
                nx, nz = cell[0] + dx, cell[1] + dz
                if 0 <= nx < GRID_N and 0 <= nz < GRID_N and not blocked[nx][nz]:
                    return (nx, nz)
    return cell


def line_clear(x0, z0, x1, z1):
    dx, dz = x1 - x0, z1 - z0
    steps = max(1, int(math.hypot(dx, dz) / 0.2))
    for i in range(steps + 1):
        t = i / steps
        if is_blocked_world(x0 + dx * t, z0 + dz * t):
            return False
    return True


NEIGHBORS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def find_path(start, goal):
    """A* on the grid. Returns list of cells (start..goal) or []."""
    def h(c):
        dx, dz = abs(c[0] - goal[0]), abs(c[1] - goal[1])
        return (dx + dz) + (1.414 - 2) * min(dx, dz)

    open_heap = [(h(start), 0.0, start)]
    came = {start: None}
    cost = {start: 0.0}
    while open_heap:
        _, g, cur = heapq.heappop(open_heap)
        if cur == goal:
            break
        if g > cost.get(cur, 1e9):
            continue
        for dx, dz in NEIGHBORS:
            nx, nz = cur[0] + dx, cur[1] + dz
            if not (0 <= nx < GRID_N and 0 <= nz < GRID_N):
                continue
            if blocked[nx][nz]:
                continue
            if dx and dz and (blocked[cur[0] + dx][cur[1]] or blocked[cur[0]][cur[1] + dz]):
                continue
            ng = g + (1.414 if dx and dz else 1.0)
            n = (nx, nz)
            if ng < cost.get(n, 1e9):
                cost[n] = ng
                came[n] = cur
                heapq.heappush(open_heap, (ng + h(n), ng, n))
    if goal not in came:
        return []
    path = []
    c = goal
    while c is not None:
        path.append(c)
        c = came[c]
    path.reverse()
    return path


# =========================================================
# GAME STATE
# =========================================================

def fresh_state():
    return SimpleNamespace(
        game_state="playing", paused=False, t=0.0, shown_sec=-1,
        stamina=1.0, exhausted=False, keys=0, battery=1.0, flashlight_on=True,
        flicker=0.0, blackout=0.0, ambient_t=random.uniform(10, 18),
        foot_t=0.0, mfoot_t=0.0, growl_t=5.0, roar_cd=0.0, lock_msg_t=0.0,
        toast_t=0.0, dying_t=0.0, door_open=False, map_visible=False,
        bob=0.0, sprinting=False, moving=False, walk_anim=0.0, title_t=8.0,
    )


def fresh_monster():
    return SimpleNamespace(state="look", path=[], idx=0, goal=(0.0, 0.0),
                           repath=0.0, wait=6.0, last_seen=(0.0, 0.0), lost=0.0)


S = fresh_state()
M = fresh_monster()


def toast(msg, col=color.white, dur=3.0):
    toast_text.text = msg
    toast_text.color = col
    toast_text.enabled = True
    S.toast_t = dur


def trigger_blackout(dur):
    S.blackout = dur
    play("buzz", 0.7)


def freeze_player(freeze):
    player.mouse_sensitivity = Vec2(0, 0) if freeze else NORMAL_SENSITIVITY
    if freeze:
        player.speed = 0


def update_keys_hud():
    keys_text.text = f"KEYS: {S.keys}/{NUM_KEYS}"


def unlock_exit():
    S.door_open = True
    exit_door.collider = None
    exit_door.animate_y(WALL_HEIGHT * 1.6, duration=2.5)
    exit_lock.enabled = False
    exit_label.enabled = True
    objective_text.text = "All Keys Are Collected! "
    objective_text.color = color.lime
    play("unlock", 1.0)
    invoke(play, "creak", 0.8, 0.8, delay=0.6)
    toast("", color.lime, 4.0)
    M.state = "search"
    M.goal = (player.x, player.z)
    M.repath = 0.0


def collect(p):
    p["taken"] = True
    p["root"].enabled = False
    if p["kind"] == "key":
        S.keys += 1
        update_keys_hud()
        play("key", 0.9)
        play(random.choice(WHISPERS), 0.6, 0.9)
        if S.keys >= NUM_KEYS:
            unlock_exit()
        else:
            toast(f"Key {S.keys}/{NUM_KEYS} ", color.yellow)
            objective_text.text = f": {S.keys}/{NUM_KEYS}"
            trigger_blackout(0.9)
            if M.state != "chase":
                M.state = "search"
                M.goal = (player.x, player.z)
                M.repath = 0.0
    else:
        S.battery = min(1.0, S.battery + 0.45)
        play("pickup", 0.8)
        toast("Battery found!", color.lime, 2.0)


def set_game_over(won):
    if S.game_state != "playing":
        return
    freeze_player(True)
    mouse.locked = False
    if won:
        S.game_state = "won"
        play("key", 1.0)
        status_text.text = f"Escaped\nTime: {S.t:.1f}s\nPress R TO RESTART"
        status_text.color = color.lime
        status_text.enabled = True
        danger_overlay.color = Color(0.6, 0, 0, 0)
    else:
        S.game_state = "dying"       # jumpscare
        S.dying_t = 1.8
        play("scream", 1.0)
        yaw = math.radians(player.rotation_y)
        monster.scale = 0.8
        monster.x = player.x + math.sin(yaw) * 0.95
        monster.z = player.z + math.cos(yaw) * 0.95
        monster.y = 0
        monster.rotation_y = player.rotation_y + 180
        danger_overlay.color = Color(0.7, 0, 0, 0.55)


def reset_game():
    global S, M
    S = fresh_state()
    M = fresh_monster()
    player.position = START_POSITION
    player.rotation = (0, 0, 0)
    player.camera_pivot.rotation = (0, 0, 0)
    player.speed = PLAYER_SPEED
    freeze_player(False)
    camera.rotation_z = 0
    camera.x = 0
    camera.y = 0
    camera.fov = 90
    monster.position = MONSTER_START
    monster.rotation = (0, 0, 0)
    monster.scale = 1
    exit_door.y = 1.4
    exit_door.collider = "box"
    exit_lock.enabled = True
    exit_label.enabled = False
    spawn_pickups()
    update_keys_hud()
    objective_text.text = f" {NUM_KEYS} "
    objective_text.color = color.white
    status_text.text = ""
    status_text.enabled = False
    toast_text.enabled = False
    title_text.enabled = True
    map_root.enabled = False
    danger_overlay.color = Color(0.6, 0, 0, 0)
    mouse.locked = True


def toggle_pause():
    if S.game_state != "playing":
        return
    S.paused = not S.paused
    mouse.locked = not S.paused
    freeze_player(S.paused)
    if S.paused:
        set_loops(0, 0)
        status_text.text = "PAUSED\nPress P to continue"
        status_text.color = color.white
        status_text.enabled = True
    else:
        status_text.enabled = False


# =========================================================
# INPUT
# =========================================================

def input(key):
    if key == "escape":
        application.quit()

    if key == "f" and S.game_state == "playing" and not S.paused:
        if S.battery <= 0:
            toast("BATTERY EMPTY", color.red, 2.0)
        else:
            S.flashlight_on = not S.flashlight_on
            play("click", 0.6)

    if key == "p":
        toggle_pause()

    if key in ("m", "tab") and S.game_state == "playing":
        S.map_visible = not S.map_visible
        map_root.enabled = S.map_visible

    if key == "r" and S.game_state in ("won", "lost"):
        reset_game()


# =========================================================
# MONSTER AI
# =========================================================

def pick_patrol_goal():
    if random.random() < 0.35:
        i, j = room_of(player.x, player.z)       # player ke room ki taraf
    else:
        i, j = random.randrange(ROOMS), random.randrange(ROOMS)
    cx, cz = room_center(i, j)
    return (cx + random.uniform(-1.5, 1.5), cz + random.uniform(-1.5, 1.5))


def follow_target():
    mx, mz = monster.x, monster.z
    gx, gz = M.goal
    if line_clear(mx, mz, gx, gz):
        return gx, gz
    if not M.path:
        return None
    while M.idx < len(M.path) - 1:
        wx, wz = cell_to_world(*M.path[M.idx])
        if (wx - mx) ** 2 + (wz - mz) ** 2 < 0.3 ** 2:
            M.idx += 1
        else:
            break
    best = M.idx
    last = min(len(M.path) - 1, M.idx + 12)
    for i in range(last, M.idx, -1):
        wx, wz = cell_to_world(*M.path[i])
        if line_clear(mx, mz, wx, wz):
            best = i
            break
    return cell_to_world(*M.path[best])


def update_monster(dt):
    dxp, dzp = player.x - monster.x, player.z - monster.z
    dist = math.hypot(dxp, dzp)

    sight = SIGHT_LIGHT_ON if (S.flashlight_on and S.battery > 0) else SIGHT_LIGHT_OFF
    sees = dist < sight and line_clear(monster.x, monster.z, player.x, player.z)
    heard = S.moving and dist < (HEAR_SPRINT if S.sprinting else HEAR_WALK)

    if sees or heard:
        if M.state != "chase":
            M.state = "chase"
            if S.roar_cd <= 0:
                S.roar_cd = 8.0
                play("scream", 0.55 * (0.4 + dvol(dist, 30)), 0.55)
                play("growl", 0.9)
        M.lost = 0.0
        M.last_seen = (player.x, player.z)
    elif M.state == "chase":
        M.lost += dt
        if M.lost > 3.0:
            M.state = "search"
            M.goal = M.last_seen
            M.repath = 0.0

    speed = 0.0
    if M.state == "look":
        M.wait -= dt
        monster.rotation_y += 35 * dt
        if M.wait <= 0:
            M.state = "patrol"
            M.goal = pick_patrol_goal()
            M.repath = 0.0
    else:
        if M.state == "chase":
            speed = MONSTER_CHASE + 0.25 * S.keys
            M.goal = (player.x, player.z) if (sees or heard) else M.last_seen
        elif M.state == "search":
            speed = MONSTER_SEARCH
        else:
            speed = MONSTER_PATROL

        M.repath -= dt
        if M.repath <= 0:
            M.repath = 0.35 if M.state == "chase" else 99.0
            start = nearest_free(world_to_cell(monster.x, monster.z))
            goal = nearest_free(world_to_cell(*M.goal))
            M.path = find_path(start, goal)
            M.idx = 0

        if M.state != "chase":
            arrived = math.hypot(M.goal[0] - monster.x, M.goal[1] - monster.z) < 0.9
            stuck = (not M.path) and not line_clear(monster.x, monster.z, M.goal[0], M.goal[1])
            if arrived or stuck:
                M.state = "look"
                M.wait = random.uniform(1.5, 3.5) if arrived else 0.5
                speed = 0.0

        if speed > 0:
            tgt = follow_target()
            if tgt is not None:
                tx, tz = tgt
                dx, dz = tx - monster.x, tz - monster.z
                d = math.hypot(dx, dz)
                if d > 0.05:
                    step = min(d, speed * dt)
                    monster.x += dx / d * step
                    monster.z += dz / d * step
                    monster.rotation_y = math.degrees(math.atan2(dx, dz))

    # animation
    S.walk_anim += dt * speed * 2.6
    amp = min(1.0, speed / 3.0)
    for k, pv in enumerate(arm_pivots):
        pv.rotation_x = math.sin(S.walk_anim + k * math.pi) * 30 * amp + math.sin(S.t * 1.3 + k) * 4
    head.rotation_z = math.sin(S.t * 2.1) * 8
    head.rotation_x = 12 + math.sin(S.t * 1.7) * 5
    monster.y = abs(math.sin(S.walk_anim)) * 0.05 * amp

    # monster sounds
    if speed > 0:
        S.mfoot_t -= dt
        if S.mfoot_t <= 0:
            S.mfoot_t = 1.0 / (speed * 0.6)
            v = dvol(dist, 26)
            if v > 0.02:
                play("mstep", v * 0.95, random.uniform(0.85, 1.1),
                     max(-1.0, min(1.0, dxp * -0.05)))
    if M.state == "chase":
        S.growl_t -= dt
        if S.growl_t <= 0:
            S.growl_t = random.uniform(5, 8)
            play("growl", 0.4 + 0.6 * dvol(dist, 22), random.uniform(0.9, 1.1))
    return dist


# =========================================================
# LIGHT / FX
# =========================================================

def update_light(dt, danger):
    if S.flashlight_on and S.battery > 0:
        S.battery = max(0.0, S.battery - dt / BATTERY_SECONDS)
    lit = S.flashlight_on and S.battery > 0
    if lit:
        near, far = 1.5, 5.0 + 12.5 * (S.battery ** 0.5)
    else:
        near, far = 0.3, 5.0
    rate = 0.15 + (2.5 if S.battery < 0.2 else 0.0) + danger * 3.5
    if lit and S.flicker <= 0 and random.random() < rate * dt:
        S.flicker = random.uniform(0.04, 0.22)
    if S.flicker > 0:
        S.flicker -= dt
        far *= 0.35
        near *= 0.3
    if S.blackout > 0:
        S.blackout -= dt
        near, far = 0.2, 1.6
    scene.fog_density = (near, far)
    flashlight_lens.color = rgb255(255, 240, 180) if lit else rgb255(50, 50, 50)
    battery_fill.scale_x = 0.2 * S.battery
    battery_fill.color = rgb255(200, 60, 60) if S.battery < 0.2 else rgb255(230, 210, 60)


# =========================================================
# MAIN UPDATE
# =========================================================

def update():
    dt = time.dt

    if S.game_state == "dying":
        S.dying_t -= dt
        camera.rotation_z = random.uniform(-4, 4)
        camera.x = random.uniform(-0.05, 0.05)
        camera.y = random.uniform(-0.05, 0.05)
        if S.dying_t <= 0:
            S.game_state = "lost"
            camera.rotation_z = 0
            camera.x = 0
            camera.y = 0
            set_loops(0, 0)
            status_text.text = "YOU ARE CAUGHT!\nPress R to restart"
            status_text.color = color.red
            status_text.enabled = True
        return

    if S.game_state != "playing" or S.paused:
        return

    S.t += dt
    S.roar_cd = max(0.0, S.roar_cd - dt)

    secs = int(S.t)
    if secs != S.shown_sec:
        S.shown_sec = secs
        timer_text.text = f"Time: {secs}s"
    if title_text.enabled and S.t > S.title_t:
        title_text.enabled = False

    # ----- movement / stamina -----
    S.moving = bool(held_keys["w"] or held_keys["a"] or held_keys["s"] or held_keys["d"])
    wants_sprint = held_keys["shift"] and S.moving

    if S.exhausted and S.stamina >= STAMINA_MIN_TO_SPRINT:
        S.exhausted = False

    if wants_sprint and not S.exhausted and S.stamina > 0:
        player.speed = SPRINT_SPEED
        S.sprinting = True
        S.stamina = max(0.0, S.stamina - STAMINA_DRAIN * dt)
        if S.stamina <= 0:
            S.exhausted = True
            play("breath", 0.7)
    else:
        S.sprinting = False
        player.speed = PLAYER_SPEED
        S.stamina = min(1.0, S.stamina + STAMINA_REGEN * dt)

    stamina_fill.scale_x = 0.4 * S.stamina
    stamina_fill.color = rgb255(200, 60, 60) if S.exhausted else rgb255(60, 200, 90)

    # ----- camera feel: head-bob + sprint FOV -----
    if S.moving:
        S.bob += dt * (13 if S.sprinting else 8)
    camera_bob = math.sin(S.bob) * 0.04 if S.moving else 0.0
    camera.fov = lerp(camera.fov, 100 if S.sprinting else 90, min(1.0, 8 * dt))

    # ----- footsteps -----
    if S.moving and player.grounded:
        S.foot_t -= dt
        if S.foot_t <= 0:
            S.foot_t = 0.34 if S.sprinting else 0.52
            play(random.choice(("foot1", "foot2")), 0.9 if S.sprinting else 0.45,
                 random.uniform(0.92, 1.08), random.uniform(-0.15, 0.15))
    else:
        S.foot_t = min(S.foot_t, 0.1)

    # ----- pickups -----
    for p in pickups:
        if p["taken"]:
            continue
        p["root"].rotation_y += 90 * dt
        p["root"].y = p["base_y"] + math.sin(S.t * 2 + p["phase"]) * 0.1
        if math.hypot(player.x - p["root"].x, player.z - p["root"].z) < 1.7:
            collect(p)

    # ----- locked door hint -----
    if not S.door_open:
        S.lock_msg_t -= dt
        if math.hypot(player.x - EXIT_X, player.z - half) < 3.0 and S.lock_msg_t <= 0:
            S.lock_msg_t = 3.0
            play("locked", 0.8)
            toast(f"Door locked. {NUM_KEYS - S.keys} keys are needed.", color.red, 2.5)

    # ----- monster -----
    dist = update_monster(dt)
    danger = clamp01(1 - dist / 9.0)

    update_light(dt, danger)

    # danger FX
    danger_overlay.color = Color(0.6, 0, 0, danger * 0.45)
    fc = Color(6 / 255 + danger * 0.10, 6 / 255, 10 / 255, 1)
    scene.fog_color = fc
    window.color = fc
    camera.rotation_z = random.uniform(-1, 1) * danger * 1.8
    camera.x = random.uniform(-1, 1) * danger * 0.03
    camera.y = camera_bob

    hb = clamp01(1 - dist / 16.0)
    if M.state == "chase":
        hb = max(hb, 0.25)
    set_loops(0.45, hb ** 1.1 * 0.9, 0.9 + hb * 0.8)

    # ----- ambient scary events -----
    S.ambient_t -= dt
    if S.ambient_t <= 0:
        S.ambient_t = random.uniform(12, 26)
        ev = random.choices(("whisper", "knock", "wail", "creak", "blackout"),
                            weights=(35, 20, 15, 15, 15))[0]
        pan = random.uniform(-0.9, 0.9)
        if ev == "whisper":
            play(random.choice(WHISPERS), random.uniform(0.4, 0.8), random.uniform(0.85, 1.1), pan)
        elif ev == "knock":
            play("knock", random.uniform(0.5, 0.9), 1.0, pan)
        elif ev == "wail":
            play("wail", 0.45, random.uniform(0.9, 1.05), pan)
        elif ev == "creak":
            play("creak", 0.6, random.uniform(0.8, 1.2), pan)
        else:
            trigger_blackout(random.uniform(0.8, 2.0))

    # ----- map -----
    if S.map_visible:
        map_dot.position = (player.x * MAP_K, player.z * MAP_K, 0.03)
        yaw = math.radians(player.rotation_y)
        map_pointer.position = (player.x * MAP_K + math.sin(yaw) * 0.022,
                                player.z * MAP_K + math.cos(yaw) * 0.022, 0.02)

    # ----- toast timer -----
    if S.toast_t > 0:
        S.toast_t -= dt
        if S.toast_t <= 0:
            toast_text.enabled = False

    # ----- caught / escape -----
    if dist < MONSTER_CATCH_DISTANCE:
        set_game_over(False)
        return

    if S.door_open and player.z > half - 1.5 and abs(player.x - EXIT_X) < 2.4:
        set_game_over(True)


# =========================================================
# START GAME
# =========================================================

mouse.locked = True
toast("Find all keys and escape!", color.white, 5.0)

if __name__ == "__main__":
    app.run()