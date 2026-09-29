import os
import platform
import shutil
import subprocess
import time
from typing import Any

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import mss
except ImportError:
    mss = None

try:
    import pygetwindow
except ImportError:
    pygetwindow = None

try:
    import psutil
except ImportError:
    psutil = None


class DesktopAgentError(RuntimeError):
    pass


class DesktopAgent:
    """Explicit Windows desktop-control primitives."""

    SUPPORTED_APPS = {
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "paint": ["mspaint.exe"],
        "explorer": ["explorer.exe"],
        "terminal": ["wt.exe"],
        "cmd": ["cmd.exe"],
        "chrome": [
            "chrome.exe",
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ],
        "google chrome": [
            "chrome.exe",
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
        ],
        "vscode": [
            "code.exe",
            os.path.expandvars(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
        ],
        "vs code": [
            "code.exe",
            os.path.expandvars(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
        ],
        "visual studio code": [
            "code.exe",
            os.path.expandvars(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
        ],
    }

    def __init__(self):
        self.is_windows = platform.system().lower() == "windows"

    def _require_windows(self):
        if not self.is_windows:
            raise DesktopAgentError("Desktop control is currently supported on Windows only.")

    def _require(self, module, name):
        if module is None:
            raise DesktopAgentError(
                f"{name} is not installed. Install requirements-desktop.txt first."
            )

    def status(self) -> dict[str, Any]:
        return {
            "platform": platform.system(),
            "supported": self.is_windows,
            "screen_control": pyautogui is not None and mss is not None,
            "window_control": pygetwindow is not None,
            "process_info": psutil is not None,
        }

    def screenshot(self, output_path: str) -> dict[str, Any]:
        self._require_windows()
        self._require(mss, "mss")
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with mss.mss() as capture:
            monitor = capture.monitors[0]
            shot = capture.grab(monitor)
            mss.tools.to_png(shot.rgb, shot.size, output=output_path)
        return {"path": os.path.abspath(output_path)}

    def windows(self) -> list[dict[str, Any]]:
        self._require_windows()
        self._require(pygetwindow, "PyGetWindow")
        result = []
        for window in pygetwindow.getAllWindows():
            title = (window.title or "").strip()
            if not title:
                continue
            result.append({
                "title": title,
                "left": window.left,
                "top": window.top,
                "width": window.width,
                "height": window.height,
                "visible": bool(window.visible),
                "minimized": bool(window.isMinimized),
                "maximized": bool(window.isMaximized),
            })
        return result

    def focus_window(self, title: str) -> dict[str, Any]:
        self._require_windows()
        self._require(pygetwindow, "PyGetWindow")
        matches = pygetwindow.getWindowsWithTitle(title)
        if not matches:
            raise DesktopAgentError(f"No window found matching: {title}")
        window = matches[0]
        if window.isMinimized:
            window.restore()
        window.activate()
        time.sleep(0.15)
        return {"title": window.title}

    def _resolve_executable(self, app: str) -> str:
        candidates = self.SUPPORTED_APPS.get(app.strip().lower())
        if not candidates:
            raise DesktopAgentError(f"App '{app}' is not in the safe application allowlist.")

        for candidate in candidates:
            if os.path.isabs(candidate) and os.path.isfile(candidate):
                return candidate
            resolved = shutil.which(candidate)
            if resolved:
                return resolved

        raise DesktopAgentError(
            f"App '{app}' is allowed but its executable was not found on this Windows installation."
        )

    def open_app(self, app: str) -> dict[str, Any]:
        self._require_windows()
        key = app.strip().lower()
        executable = self._resolve_executable(key)
        process = subprocess.Popen(
            [executable],
            shell=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return {"app": key, "pid": process.pid, "executable": executable}

    def close_app(self, app: str) -> dict[str, Any]:
        self._require_windows()
        self._require(pygetwindow, "PyGetWindow")
        key = app.strip().lower()
        title_terms = {
            "chrome": ["chrome"],
            "google chrome": ["chrome"],
            "vscode": ["visual studio code"],
            "vs code": ["visual studio code"],
            "visual studio code": ["visual studio code"],
            "notepad": ["notepad"],
            "paint": ["paint"],
            "calculator": ["calculator"],
            "explorer": ["file explorer"],
        }.get(key, [key])

        matches = []
        for window in pygetwindow.getAllWindows():
            title = (window.title or "").strip()
            lowered = title.casefold()
            if title and any(term in lowered for term in title_terms):
                matches.append(window)

        if not matches:
            raise DesktopAgentError(f"No open window found for '{app}'.")

        closed = 0
        for window in matches:
            try:
                window.close()
                closed += 1
            except Exception:
                continue

        if not closed:
            raise DesktopAgentError(f"Could not close '{app}'.")
        return {"app": key, "closed_windows": closed}

    def click(self, x: int, y: int, button: str = "left") -> dict[str, Any]:
        self._require_windows()
        self._require(pyautogui, "PyAutoGUI")
        if button not in {"left", "right", "middle"}:
            raise DesktopAgentError("Unsupported mouse button.")
        pyautogui.click(x=int(x), y=int(y), button=button)
        return {"x": int(x), "y": int(y), "button": button}

    def type_text(self, text: str, interval: float = 0.01) -> dict[str, Any]:
        self._require_windows()
        self._require(pyautogui, "PyAutoGUI")
        pyautogui.write(str(text), interval=max(0.0, min(float(interval), 0.2)))
        return {"characters": len(str(text))}

    def hotkey(self, keys: list[str]) -> dict[str, Any]:
        self._require_windows()
        self._require(pyautogui, "PyAutoGUI")
        if not keys or len(keys) > 6:
            raise DesktopAgentError("A hotkey must contain between 1 and 6 keys.")
        pyautogui.hotkey(*[str(key).lower() for key in keys])
        return {"keys": keys}

    def scroll(self, clicks: int) -> dict[str, Any]:
        self._require_windows()
        self._require(pyautogui, "PyAutoGUI")
        clicks = max(-20, min(int(clicks), 20))
        pyautogui.scroll(clicks)
        return {"clicks": clicks}

    def processes(self, limit: int = 100) -> list[dict[str, Any]]:
        self._require_windows()
        self._require(psutil, "psutil")
        result = []
        for process in psutil.process_iter(["pid", "name"]):
            try:
                result.append({"pid": process.info["pid"], "name": process.info["name"]})
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            if len(result) >= max(1, min(int(limit), 500)):
                break
        return result
