# lazydocker-tray

A lightweight cross-platform **system tray** indicator for Docker, with one-click access to
[lazydocker](https://github.com/jesseduffield/lazydocker) and your Compose projects.

- 🟢 / 🟡 / 🔴 colored badge on the Docker logo — engine up & healthy / unhealthy or empty / down
- Tooltip with container counts and aggregate CPU / RAM
- Right-click menu: open lazydocker, auto-detected Compose projects (up / down / logs in the right dir), `docker system prune`
- Light on resources: cheap state poll every 6s, expensive `docker stats` only every 30s, all off the GUI thread
- i18n: English / Spanish, auto-detected from your locale

> Built on [PySide6](https://doc.qt.io/qtforpython/). Works on Linux (X11/Wayland), macOS, and Windows.

## Requirements

- Python 3.9+
- [`docker`](https://docs.docker.com/get-docker/) on `PATH`
- [`lazydocker`](https://github.com/jesseduffield/lazydocker) on `PATH` (optional, for the "Open LazyDocker" action)
- A terminal emulator (Linux: konsole / gnome-terminal / xfce4-terminal / alacritty / xterm)

## Install & run

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python lazydocker_tray.py
```

The icon appears in your system tray. **Left-click** opens lazydocker, **right-click** opens the menu.

## Language

Auto-detected from your system locale. Force it with an env var:

```bash
TRAY_LANG=es python lazydocker_tray.py   # Spanish
TRAY_LANG=en python lazydocker_tray.py   # English
```

Add a language by extending the `STRINGS` dict at the top of `lazydocker_tray.py`.

## Tooltip: "Healthy" / "Unhealthy"

These count only containers that define a Docker `HEALTHCHECK`. Containers without one are
not counted in either — so `Containers: 10, Healthy: 0` just means none declare a healthcheck.

## Build a standalone binary

CI builds binaries for Linux, macOS, and Windows on every `v*` tag (see
[`.github/workflows/build.yml`](.github/workflows/build.yml)). Locally:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name lazydocker-tray lazydocker_tray.py
# -> dist/lazydocker-tray
```

> The bundle is ~120–180 MB because it ships Python + Qt. The binary still needs `docker`,
> `lazydocker`, and a terminal emulator present on the user's machine.

## License

[MIT](LICENSE) © 2026 Alan Estrada
