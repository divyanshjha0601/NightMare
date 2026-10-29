# 🌑 NIGHTMARE: The Abandoned House

### A 3D Horror Survival Game Built with Python & Ursina Engine

**Find the keys. Escape the house. Don't let the monster find you.**

Nightmare: The Abandoned House is a first-person 3D horror survival game developed using Python and the Ursina Engine. Trapped inside a mysterious abandoned house, players must explore a randomly generated maze, collect keys, manage their flashlight battery, and escape while being hunted by an intelligent monster.

With dynamic lighting, atmospheric horror sounds, a stamina system, and an AI-driven enemy, every playthrough creates a tense survival experience.

Can you survive the nightmare?

---

## 🎮 Game Overview

You wake up inside a dark, abandoned house filled with mysterious rooms and terrifying sounds.

Your objective is to find all 5 hidden keys and unlock the exit. But you are not alone.

A dangerous creature is roaming the house. It can hear your footsteps, detect your presence, and chase you when you get too close.

Your flashlight is your only source of visibility, but its battery is limited. Running can help you escape, but it drains your stamina.

Every decision matters.

**Explore carefully. Stay quiet. Survive.**

---

## ✨ Features

### 🏚️ Procedurally Generated Maze
- Explore a 4×4 maze containing 16 rooms.
- Randomized maze layout for every new game.
- Navigate through interconnected rooms and corridors.

### 👹 Intelligent Monster AI
The monster uses multiple behavioral states:

- **Patrol:** Roams around the house.
- **Search:** Investigates the player's last known location.
- **Chase:** Pursues the player when it detects them.
- **Look:** Pauses and scans its surroundings.

The monster can detect players through sight and sound. Collecting more keys also increases its chase speed.

### 🔑 Key Collection & Escape
- Find 5 keys hidden throughout the house.
- Collect all keys to unlock the exit.
- Reach the exit to complete the game.

### 🔦 Flashlight & Battery System
- Use your flashlight to navigate dark rooms.
- Manage limited flashlight battery.
- Find batteries to recharge your flashlight.
- Experience sudden blackouts and flickering lights.

### 🏃 Sprint & Stamina System
- Move normally to conserve stamina.
- Sprint when the monster gets close.
- Stamina regenerates when you stop sprinting.

### 🔊 Procedural Horror Audio
Horror sounds are generated directly through Python code.

Includes:
- Ambient horror drones
- Heartbeat effects
- Footsteps
- Monster growls
- Whispers
- Knocking and creaking sounds
- Screams and jumpscares

No external sound files are required for the generated audio effects.

### 🌫️ Dynamic Horror Atmosphere
- Fog and darkness
- Flickering lights
- Random blackouts
- Camera shake
- Red danger effects
- Heartbeat intensity based on monster proximity

### 🗺️ In-Game Map
Use the map to understand your surroundings and navigate the maze.

---

## 🕹️ Controls

| Key | Action |
|---|---|
| W | Move Forward |
| A | Move Left |
| S | Move Backward |
| D | Move Right |
| Mouse | Look Around |
| Shift | Sprint |
| Space | Jump |
| F | Toggle Flashlight |
| M / Tab | Toggle Map |
| P | Pause / Resume |
| R | Restart Game |
| Esc | Quit Game |

---

## 🛠️ Built With

| Technology | Purpose |
|---|---|
| Python | Core game logic |
| Ursina Engine | 3D game development |
| Panda3D | 3D rendering foundation |
| Python Standard Library | Procedural audio, randomization, math, and game systems |
| Git & GitHub | Version control and project hosting |

---

## 🚀 Installation & Setup

Follow these steps to run the game locally.

### Prerequisites

- Python 3.10 or later
- Git
- Visual Studio Code (recommended)

### 1. Clone the Repository

```bash
git clone https://github.com/divyanshjha0601/NightMare.git
```

### 2. Navigate to the Project Directory

```bash
cd NightMare
```

### 3. Install Dependencies

Install the Ursina Engine:

```bash
pip install ursina
```

### 4. Run the Game

If your main Python file is named `nightmare.py`:

```bash
python nightmare.py
```

If your main file has a different name, replace `nightmare.py` with your actual filename.

---

## 🎯 Objective

Your mission is to:

1. Explore the abandoned house.
2. Locate all 5 hidden keys.
3. Collect batteries to maintain your flashlight.
4. Avoid the monster using stealth and sprinting.
5. Unlock the exit.
6. Escape the house and survive.

**The monster is always listening.**

---

## 📸 Screenshots & Gameplay
<video controls src="screen shot/Recording 2026-10-29 115751.mp4" title="Game play video"></video>
![map](<screen shot/Screenshot 2026-10-29 115407.png>)
![monster tackle](<screen shot/Screenshot 2026-10-29 115503.png>)





---

## 🧠 What I Learned

Developing this project helped me explore:

- 3D game development with Python
- First-person player movement and camera controls
- Procedural maze generation
- Enemy AI and pathfinding
- Collision detection
- Dynamic lighting and fog
- Procedural audio generation
- Game state management
- Resource management systems
- Git and GitHub version control

---

## 🔮 Future Improvements

Potential future updates:

- [ ] Multiple difficulty levels
- [ ] More monster types
- [ ] Additional abandoned environments
- [ ] More puzzles and hidden objectives
- [ ] Improved graphics and visual effects
- [ ] Main menu and settings
- [ ] Save and load functionality
- [ ] Additional horror encounters

---

## 👨‍💻 Developer

**Divyansh Jha**

B.Tech — Artificial Intelligence & Data Science

GitHub: [@divyanshjha0601](https://github.com/divyanshjha0601)

Project Repository: [NightMare](https://github.com/divyanshjha0601/NightMare)

---

## ⭐ Support

If you enjoy this project, consider giving the repository a ⭐ on GitHub.

Your support motivates me to develop more creative games and explore new technologies.

---

### ☠️ Can You Survive the Nightmare?

*The house is waiting. The monster is hunting. Your escape begins now.*
