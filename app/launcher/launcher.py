"""One-click Medha Windows launcher.

Creates a project-local virtual environment on first run, installs the
backend/frontend dependencies when needed, starts FastAPI and Vite, waits for
both services, opens the browser, and cleans up child processes on exit.
"""

from __future__ import annotations

import logging
import os
import signal
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
VENV = ROOT / ".venv"
BACKEND_URL = "http://127.0.0.1:8000/api/health"
FRONTEND_URL = "http://127.0.0.1:5173"
LOG_DIR = ROOT / "logs"
LOG_PATH = LOG_DIR / "launcher.log"

_processes: list[subprocess.Popen] = []


def _system_python() -> str:
    for command in ("py", "python"):
        executable = shutil.which(command)
        if executable:
            return executable
    raise RuntimeError("Python 3.11+ was not found. Install Python and run Medha again.")


def _venv_python() -> Path:
    return VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def _npm_command() -> str:
    if os.name == "nt":
        executable = shutil.which("npm.cmd")
        if executable:
            return executable
    executable = shutil.which("npm")
    if executable:
        return executable
    raise RuntimeError("Node.js/npm was not found. Install Node.js and run Medha again.")


def _run(command: list[str], cwd: Path, label: str) -> None:
    print(f"[Medha] {label}...")
    result = subprocess.run(command, cwd=str(cwd), check=False)
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed with exit code {result.returncode}.")


def _ensure_environment() -> tuple[Path, str]:
    if not FRONTEND.exists():
        raise RuntimeError(f"Frontend directory not found: {FRONTEND}")

    system_python = _system_python()
    python = _venv_python()

    if not python.exists():
        _run([system_python, "-m", "venv", str(VENV)], ROOT, "Creating Python virtual environment")
        python = _venv_python()

    if not python.exists():
        raise RuntimeError(f"Python virtual environment was not created: {python}")

    _run(
        [str(python), "-m", "pip", "install", "-r", str(ROOT / "backend" / "requirements.txt")],
        ROOT,
        "Installing backend dependencies",
    )

    desktop_requirements = ROOT / "backend" / "requirements-desktop.txt"
    if desktop_requirements.exists():
        _run(
            [str(python), "-m", "pip", "install", "-r", str(desktop_requirements)],
            ROOT,
            "Installing desktop-control dependencies",
        )

    npm = _npm_command()
    node_modules = FRONTEND / "node_modules"
    if not node_modules.exists():
        _run([npm, "install"], FRONTEND, "Installing frontend dependencies")

    return python, npm


def _start(command: list[str], cwd: Path, name: str) -> subprocess.Popen:
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        stdout=None,
        stderr=None,
        creationflags=creationflags,
    )
    _processes.append(process)
    print(f"[Medha] Started {name} (PID {process.pid})")
    return process


def _wait_for_url(url: str, timeout: float, name: str) -> None:
    deadline = time.monotonic() + timeout
    last_error = "not checked"

    while time.monotonic() < deadline:
        if any(p.poll() is not None for p in _processes):
            exited = [p.pid for p in _processes if p.poll() is not None]
            raise RuntimeError(f"A Medha process exited during {name} startup: {exited}")

        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status < 500:
                    print(f"[Medha] {name} is ready.")
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)

        time.sleep(1)

    raise RuntimeError(f"{name} did not become ready within {timeout:.0f}s: {last_error}")


def _open_browser() -> None:
    import webbrowser
    webbrowser.open(FRONTEND_URL)
    print(f"[Medha] Opened {FRONTEND_URL}")


def _stop_all(*_args: object) -> None:
    if not _processes:
        return

    print("\n[Medha] Shutting down services...")
    for process in reversed(_processes):
        if process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass

    deadline = time.monotonic() + 5
    while time.monotonic() < deadline and any(
        process.poll() is None for process in _processes
    ):
        time.sleep(0.1)

    for process in reversed(_processes):
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass

    _processes.clear()
    print("[Medha] Services stopped.")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        filename=LOG_PATH,
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    print("=" * 52)
    print(" MEDHA")
    print(" Independent local personal AI runtime")
    print("=" * 52)

    try:
        python, npm = _ensure_environment()

        signal.signal(signal.SIGINT, _stop_all)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _stop_all)

        backend = _start(
            [
                str(python),
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ],
            ROOT,
            "backend",
        )

        _wait_for_url(BACKEND_URL, 60, "Backend")

        frontend = _start(
            [npm, "exec", "vite", "--", "--host", "127.0.0.1"],
            FRONTEND,
            "frontend",
        )

        _wait_for_url(FRONTEND_URL, 45, "Frontend")
        _open_browser()

        print("\n[Medha] Running.")
        print("[Medha] Close this window to stop Medha.")
        print("[Medha] Backend:  http://127.0.0.1:8000")
        print("[Medha] Frontend: http://127.0.0.1:5173")

        while True:
            if backend.poll() is not None:
                raise RuntimeError(f"Backend exited with code {backend.returncode}")
            if frontend.poll() is not None:
                raise RuntimeError(f"Frontend exited with code {frontend.returncode}")
            time.sleep(1)

    except KeyboardInterrupt:
        return 0
    except Exception as exc:
        logging.exception("Medha startup failed")
        print(f"\n[Medha] Startup failed: {exc}")
        print(f"[Medha] See log: {LOG_PATH}")
        return 1
    finally:
        _stop_all()
        logging.info("Medha launcher stopped")


if __name__ == "__main__":
    raise SystemExit(main())
