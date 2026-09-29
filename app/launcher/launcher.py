"""One-click Medha development/runtime launcher for Windows.

Starts the existing FastAPI backend and React/Vite frontend, waits for
backend health, opens Medha in the default browser, and cleans up child
processes on exit.
"""

from __future__ import annotations

import os
import signal
import logging
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
BACKEND_URL = "http://127.0.0.1:8000/api/health"
FRONTEND_URL = "http://127.0.0.1:5173"
LOG_DIR = ROOT / "logs"
LOG_PATH = LOG_DIR / "launcher.log"

_processes: list[subprocess.Popen] = []


def _npm_command() -> str:
    """Return an npm executable path that works with Windows subprocess."""
    if os.name == "nt":
        executable = shutil.which("npm.cmd")
        if executable:
            return executable
    executable = shutil.which("npm")
    if executable:
        return executable
    raise RuntimeError(
        "npm was not found. Install Node.js (which includes npm) and retry."
    )


def _python_command() -> list[str]:
    return [sys.executable]


def _check_prerequisites() -> None:
    if not FRONTEND.exists():
        raise RuntimeError(f"Frontend directory not found: {FRONTEND}")
    _npm_command()


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


def _wait_for_backend(timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    last_error = "not checked"

    while time.monotonic() < deadline:
        if any(p.poll() is not None for p in _processes):
            exited = [p.pid for p in _processes if p.poll() is not None]
            raise RuntimeError(f"A Medha process exited during startup: {exited}")

        try:
            with urllib.request.urlopen(BACKEND_URL, timeout=2) as response:
                if response.status == 200:
                    print("[Medha] Backend health check passed.")
                    return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = str(exc)

        time.sleep(1)

    raise RuntimeError(f"Backend did not become healthy within {timeout:.0f}s: {last_error}")


def _wait_for_frontend(timeout: float = 30.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(FRONTEND_URL, timeout=2) as response:
                if response.status < 500:
                    print("[Medha] Frontend is ready.")
                    return
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(1)

    raise RuntimeError(f"Frontend did not become ready within {timeout:.0f}s")


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
    logging.info("Medha launcher starting")
    print("=" * 52)
    print(" MEDHA")
    print(" Independent local personal AI runtime")
    print("=" * 52)

    try:
        npm = _npm_command()
        _check_prerequisites()

        signal.signal(signal.SIGINT, _stop_all)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, _stop_all)

        backend = _start(
            _python_command()
            + [
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

        _wait_for_backend()

        frontend = _start(
            [npm, "exec", "vite", "--", "--host", "127.0.0.1"],
            FRONTEND,
            "frontend",
        )

        _wait_for_frontend()
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
