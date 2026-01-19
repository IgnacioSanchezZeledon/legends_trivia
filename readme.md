# Legends Trivia

**Legends Trivia** is an educational desktop game developed in Python.  
Its purpose is to support English language learning using **traditional Costa Rican legends** as the core thematic content.

The application is designed as a fully interactive game with levels, progress tracking, sound effects, and background music.

---

## Features

- Interactive trivia game focused on English learning
- Content based on Costa Rican legends
- Level-based progression system
- Player progress tracking
- Background music and sound effects
- Desktop graphical interface built with Tkinter
- Standalone Windows executable generated with PyInstaller

---

## Requirements

- Python 3.10 or later
- Operating System: Windows

---

## Installation (Development Mode)

1. Clone the repository:

```bash
git clone <repository-url>
cd LegendsTrivia
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
python app.py
```

---

## Dependencies

All dependencies are listed in `requirements.txt`, including:

- `pygame`
- `Pillow`
- `customtkinter`
- `tkextrafont`

---

## Building the Executable

The project is configured to be packaged using **PyInstaller** with a `.spec` file.

To generate the executable, run the following command from the project root:

```bash
py -m PyInstaller LegendsTrivia.spec
```

- The final executable will be created inside the `dist/` directory.
- All required assets (images, fonts, audio, and icons) are included in the build configuration.

---

## Architecture

The project follows an **MVC (Model–View–Controller)** architecture:

- **Models** handle game data such as questions, levels, and player progress.
- **Views** manage the graphical user interface.
- **Controllers** coordinate logic and interaction between models and views.

This design improves maintainability and scalability.

---

## Educational Purpose

Legends Trivia was created as a learning tool to:

- Improve English reading comprehension
- Reinforce vocabulary through contextual content
- Promote Costa Rican cultural heritage through its legends

---

## License

This project is intended for educational and personal use.

If you plan to redistribute or modify the project, ensure that all multimedia assets comply with their respective licenses.
