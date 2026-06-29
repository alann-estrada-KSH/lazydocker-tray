#!/usr/bin/env python3
"""System tray indicator for Docker + lazydocker. Cross-platform (Linux/macOS/Windows).

Icon: Docker logo with a colored badge.  green = up & healthy  yellow = up/unhealthy/none  red = down
Tooltip: state + container counts + aggregate CPU/RAM (refreshed on a slow timer to stay light).

Deps: PySide6  (pip install PySide6). Needs `docker` and `lazydocker` on PATH.
"""

import json
import os
import platform
import shutil
import subprocess
import sys
import threading

from PySide6.QtCore import QObject, QTimer, Signal, Qt, QLocale
from PySide6.QtGui import (
    QAction, QIcon, QPainter, QPixmap, QColor, QBrush, QPen, QCursor,
)
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

# ---------- i18n (lazy: dict, no gettext). Override with TRAY_LANG=es|en ----------

STRINGS = {
    "en": {
        "open_lazydocker": "Open LazyDocker",
        "compose_projects": "Compose Projects",
        "none_detected": "(none detected)",
        "prune": "docker system prune",
        "quit": "Quit",
        "engine": "Docker Engine",
        "stopped": "Stopped",
        "running": "Running",
        "containers": "Containers",
        "healthy": "Healthy",
        "unhealthy": "Unhealthy",
        "checking": "Docker: checking…",
        "no_docker": "docker not found in PATH",
    },
    "es": {
        "open_lazydocker": "Abrir LazyDocker",
        "compose_projects": "Proyectos Compose",
        "none_detected": "(ninguno detectado)",
        "prune": "docker system prune",
        "quit": "Salir",
        "engine": "Docker Engine",
        "stopped": "Detenido",
        "running": "En ejecución",
        "containers": "Contenedores",
        "healthy": "Sanos",
        "unhealthy": "No sanos",
        "checking": "Docker: comprobando…",
        "no_docker": "docker no encontrado en PATH",
    },
}

_lang = (os.environ.get("TRAY_LANG") or QLocale.system().name()[:2]).lower()
T = STRINGS.get(_lang, STRINGS["en"])

# --- cadence: state is cheap, stats is the expensive call -> poll it 5x less often
STATE_SECONDS = 6
STATS_SECONDS = 30
# ponytail: compose/logs commands run here; "" -> terminal opens in $HOME (you cd yourself)
COMPOSE_DIR = ""

NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0  # hide console on Windows


# ---------- terminal launching (cross-platform) ----------

def run_in_terminal(command, cwd=None):
    cwd = cwd or COMPOSE_DIR or None
    system = platform.system()
    if system == "Darwin":
        script = f'tell app "Terminal" to do script "{command}"'
        subprocess.Popen(["osascript", "-e", script], cwd=cwd)
        return
    if system == "Windows":
        subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", command], cwd=cwd, shell=True)
        return
    terminals = [
        ("konsole", ["konsole", "-e", "bash", "-c", f"{command}; exec bash"]),
        ("gnome-terminal", ["gnome-terminal", "--", "bash", "-c", f"{command}; exec bash"]),
        ("xfce4-terminal", ["xfce4-terminal", "-e", f"bash -c '{command}; exec bash'"]),
        ("alacritty", ["alacritty", "-e", "bash", "-c", f"{command}; exec bash"]),
        ("xterm", ["xterm", "-e", f"bash -c '{command}; exec bash'"]),
    ]
    for name, argv in terminals:
        if shutil.which(name):
            subprocess.Popen(argv, cwd=cwd)
            return
    raise RuntimeError("No supported terminal emulator found")


# ---------- docker polling ----------

def _docker(args, timeout=8):
    try:
        p = subprocess.run(
            ["docker", *args], capture_output=True, text=True,
            timeout=timeout, creationflags=NO_WINDOW,
        )
        return p.returncode, p.stdout.strip()
    except Exception:
        return 1, ""


def _mem_to_bytes(s):
    s = s.strip()
    units = {"GiB": 2**30, "MiB": 2**20, "KiB": 2**10, "B": 1,
             "GB": 10**9, "MB": 10**6, "kB": 10**3}
    for u, mult in units.items():
        if s.endswith(u):
            try:
                return float(s[: -len(u)]) * mult
            except ValueError:
                return 0.0
    return 0.0


def poll_state():
    """Cheap: one `docker ps` (also tells us if the daemon is down via rc)."""
    rc, out = _docker(["ps", "--format", "{{.Status}}"])
    if rc != 0:
        return {"state": "down"}
    lines = [ln for ln in out.splitlines() if ln]
    return {
        "state": "up",
        "running": len(lines),
        "healthy": sum(1 for ln in lines if "(healthy)" in ln),
        "unhealthy": sum(1 for ln in lines if "(unhealthy)" in ln),
    }


def poll_stats():
    """Expensive: aggregate CPU%/RAM via `docker stats --no-stream`."""
    rc, out = _docker(
        ["stats", "--no-stream", "--format", "{{.CPUPerc}}|{{.MemUsage}}"], timeout=15
    )
    if rc != 0:
        return {"cpu": 0.0, "mem_bytes": 0.0}
    cpu, mem = 0.0, 0.0
    for ln in out.splitlines():
        if "|" not in ln:
            continue
        cpu_s, mem_s = ln.split("|", 1)
        try:
            cpu += float(cpu_s.strip().rstrip("%"))
        except ValueError:
            pass
        mem += _mem_to_bytes(mem_s.split("/")[0])
    return {"cpu": cpu, "mem_bytes": mem}


# ---------- icon: docker logo + colored badge ----------

COLORS = {"up": "#2ecc71", "warn": "#f1c40f", "down": "#e74c3c"}
DOT = {"up": "🟢", "warn": "🟡", "down": "🔴"}


def _base_pixmap(size):
    """Docker theme icon if available, else a blue rounded square stand-in."""
    icon = QIcon.fromTheme("docker")
    if not icon.isNull():
        pm = icon.pixmap(size, size)
        if not pm.isNull():
            return pm
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QBrush(QColor("#2496ed")))  # docker blue
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(6, 12, size - 12, size - 24, 8, 8)
    p.end()
    return pm


def make_icon(base_pm, color_hex, size=64):
    pm = base_pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation).copy()
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    r = size // 3
    p.setBrush(QBrush(QColor(color_hex)))
    p.setPen(QPen(QColor("#ffffff"), max(2, size // 32)))
    p.drawEllipse(size - r - 2, size - r - 2, r, r)  # badge bottom-right
    p.end()
    return QIcon(pm)


# ---------- worker: poll off the GUI thread ----------

class Poller(QObject):
    stateReady = Signal(dict)
    statsReady = Signal(dict)

    def fetch_state(self):
        threading.Thread(target=lambda: self.stateReady.emit(poll_state()), daemon=True).start()

    def fetch_stats(self):
        threading.Thread(target=lambda: self.statsReady.emit(poll_stats()), daemon=True).start()


# ---------- app ----------

def build():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    base_pm = _base_pixmap(64)
    icons = {k: make_icon(base_pm, c) for k, c in COLORS.items()}
    tray = QSystemTrayIcon(icons["down"])

    has = lambda cmd: shutil.which(cmd) is not None

    menu = QMenu()

    def add(target, label, fn, enabled=True):
        act = QAction(label, target)
        act.triggered.connect(lambda: fn())
        act.setEnabled(enabled)
        target.addAction(act)

    add(menu, T["open_lazydocker"], lambda: run_in_terminal("lazydocker"), has("lazydocker"))
    menu.addSeparator()

    # Auto-detected compose projects via `docker compose ls`, so up/down/logs
    # run in each project's real dir without hardcoding a path.
    projects_menu = menu.addMenu(T["compose_projects"])

    def discover_projects():
        """[(name, status, working_dir)] via `docker compose ls`."""
        rc, out = _docker(["compose", "ls", "--all", "--format", "json"])
        if rc != 0 or not out:
            return []
        try:
            data = json.loads(out)
        except ValueError:
            return []
        result = []
        for proj in data:
            cfg = (proj.get("ConfigFiles") or "").split(",")[0]
            if proj.get("Name") and cfg:
                result.append((proj["Name"], proj.get("Status", ""), os.path.dirname(cfg)))
        return result

    def refresh_projects():
        projects_menu.clear()
        projects = discover_projects()
        if not projects:
            a = projects_menu.addAction(T["none_detected"])
            a.setEnabled(False)
            return
        for name, status, wd in sorted(projects):
            sub = projects_menu.addMenu(name)
            head = sub.addAction(status or wd)
            head.setEnabled(False)
            sub.addSeparator()
            add(sub, "up -d", lambda d=wd: run_in_terminal("docker compose up -d", d))
            add(sub, "down", lambda d=wd: run_in_terminal("docker compose down", d))
            add(sub, "logs -f", lambda d=wd: run_in_terminal("docker compose logs -f --tail=100", d))

    projects_menu.aboutToShow.connect(refresh_projects)

    add(menu, T["prune"], lambda: run_in_terminal("docker system prune"))
    menu.addSeparator()
    add(menu, T["quit"], app.quit)

    tray.setContextMenu(menu)

    # KDE/Wayland StatusNotifier often won't show the default context menu; force it.
    def on_activated(reason):
        if reason == QSystemTrayIcon.Context:
            if not menu.isVisible():
                menu.popup(QCursor.pos())
        elif reason == QSystemTrayIcon.Trigger and has("lazydocker"):
            run_in_terminal("lazydocker")
    tray.activated.connect(on_activated)

    # latest values, rendered together into the tooltip
    cur = {"state": "down", "running": 0, "healthy": 0, "unhealthy": 0,
           "cpu": 0.0, "mem_bytes": 0.0}

    def render():
        if cur["state"] == "down":
            tray.setIcon(icons["down"])
            tray.setToolTip(f"{DOT['down']} {T['engine']}\n{T['stopped']}")
            return
        key = "up" if (cur["unhealthy"] == 0 and cur["running"] > 0) else "warn"
        tray.setIcon(icons[key])
        tray.setToolTip(
            f"{DOT[key]} {T['engine']} — {T['running']}\n\n"
            f"{T['containers']}: {cur['running']}\n"
            f"{T['healthy']}: {cur['healthy']}   {T['unhealthy']}: {cur['unhealthy']}\n"
            f"CPU: {cur['cpu']:.0f}%   RAM: {cur['mem_bytes'] / 2**30:.1f} GB"
        )

    def on_state(st):
        cur.update(st)
        if st.get("state") == "down":
            cur.update(running=0, healthy=0, unhealthy=0, cpu=0.0, mem_bytes=0.0)
        render()

    def on_stats(st):
        if cur["state"] == "up":
            cur.update(st)
            render()

    poller = Poller()
    poller.stateReady.connect(on_state)
    poller.statsReady.connect(on_stats)

    t_state = QTimer(); t_state.timeout.connect(poller.fetch_state); t_state.start(STATE_SECONDS * 1000)
    t_stats = QTimer(); t_stats.timeout.connect(poller.fetch_stats); t_stats.start(STATS_SECONDS * 1000)
    poller.fetch_state(); poller.fetch_stats()  # immediate first poll

    tray.show()
    return app, tray, poller, t_state, t_stats  # keep refs alive


def main():
    if not shutil.which("docker"):
        print(T["no_docker"], file=sys.stderr)
        sys.exit(1)
    app, *_keep = build()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
