# The Last Expedition

A top-down survival game built with Python and Pygame.

## Features

- Title screen and instructions menu
- WASD or arrow-key movement
- Walls and map navigation
- Collect supplies and reach the exit
- AI rivals that navigate around walls
- Health, countdown timer, and shrinking safe zone
- Win, defeat, and restart flow
- Optional background music and sound effects

## Requirements

- Python 3.10 or newer
- Pygame

## Install and run

1. Install Python from https://www.python.org/downloads/
2. Open a terminal in this folder.
3. Install the dependency:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Start the game:

   ```bash
   python main.py
   ```

## Controls

- **WASD / Arrow keys:** Move
- **V:** Toggle sound
- **R:** Restart after a round ends
- **M:** Return to the title screen when available
- **Esc:** Quit

## Optional audio

Put audio files in the `sounds` folder using these exact names:

- `background_music.ogg`
- `collect.wav`
- `warning.wav`
- `victory.wav`
- `defeat.wav`

Audio files are optional. If a file is missing, the game can still run without that sound.

Use audio you created yourself or that you have permission to use. Check each asset's license before publishing.

## Project structure

```text
The-Last-Expedition/
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
└── sounds/
    └── README.txt
```

## GitHub

When uploading this project, include `main.py`, `requirements.txt`, `README.md`, `.gitignore`, and any audio assets you have permission to distribute. Do not upload your `.venv` folder.
