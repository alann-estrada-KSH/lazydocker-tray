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

At runtime the app needs, on the user's machine:

- [`docker`](https://docs.docker.com/get-docker/) on `PATH`
- [`lazydocker`](https://github.com/jesseduffield/lazydocker) on `PATH` (for the "Open LazyDocker" action)
- A terminal emulator (Linux: konsole / gnome-terminal / xfce4-terminal / alacritty / xterm)

The packaged builds bundle Python + Qt, so end users do **not** need Python installed.

## Installation

### Windows

Download `LazyDockerTray-Setup-x.x.x.exe` from [Releases](https://github.com/alannnn-estrada/lazydocker-tray/releases/latest) and run the installer.
Optionally tick "start at login". The app checks for a newer release on startup and notifies you with a link.

### macOS

Download `LazyDockerTray-darwin-x64-x.x.x.zip` from [Releases](https://github.com/alannnn-estrada/lazydocker-tray/releases/latest), unzip, and move `lazydocker-tray.app` to `/Applications`.

> Not notarized. On first launch, right-click → Open to bypass Gatekeeper.

### Linux — via package manager (recommended)

Adds a repository so `apt` / `dnf` keep the app updated automatically.

**Debian / Ubuntu**

```bash
echo "deb [trusted=yes] https://alannnn-estrada.github.io/lazydocker-tray/apt stable main" \
  | sudo tee /etc/apt/sources.list.d/lazydocker-tray.list
sudo apt update
sudo apt install lazydocker-tray
```

**Fedora / RHEL / openSUSE**

```bash
sudo curl -o /etc/yum.repos.d/lazydocker-tray.repo \
  https://alannnn-estrada.github.io/lazydocker-tray/rpm/lazydocker-tray.repo
sudo dnf install lazydocker-tray
```

**Updating** (once the repository is added)

```bash
# Debian / Ubuntu
sudo apt update && sudo apt upgrade lazydocker-tray
# Fedora / RHEL
sudo dnf upgrade lazydocker-tray
```

### Linux — manual download

Download the `.deb` or `.rpm` from [Releases](https://github.com/alannnn-estrada/lazydocker-tray/releases/latest):

```bash
# Debian / Ubuntu
sudo dpkg -i lazydocker-tray_x.x.x_amd64.deb
# Fedora / RHEL
sudo rpm -i lazydocker-tray-x.x.x.x86_64.rpm
```

After installing, launch **LazyDocker Tray** from your app menu. **Left-click** the tray icon
opens lazydocker, **right-click** opens the menu.

## Run from source (development)

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python lazydocker_tray.py
```

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

## Releasing

Everything is built by CI ([`.github/workflows/release.yml`](.github/workflows/release.yml)) when you push a tag:

```bash
git tag v0.1.0 && git push --tags
```

On each `v*` tag the pipeline:

1. Builds the app with PyInstaller on Linux, Windows, and macOS.
2. Packages `.deb` + `.rpm` (fpm), a Windows installer (Inno Setup), and a macOS `.app` zip.
3. Publishes them all to a GitHub **Release**.
4. Rebuilds the **apt** and **dnf** repositories and deploys them to GitHub Pages.

> Keep `__version__` in `lazydocker_tray.py` in sync with the tag — the in-app update check
> compares it against the latest GitHub release.

**One-time setup:** enable GitHub Pages for the repo with source = "GitHub Actions"
(Settings → Pages). The bundle is ~120–180 MB because it ships Python + Qt; the app still
needs `docker`, `lazydocker`, and a terminal emulator present on the user's machine.

To build a binary locally:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name lazydocker-tray lazydocker_tray.py   # -> dist/
```

## License

[MIT](LICENSE) © 2026 Alan Estrada
