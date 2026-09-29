# Medha Runtime

Medha can be launched as a normal Windows application-style runtime without manually starting the backend and frontend.

## First-time setup

From the repository root:

    powershell -ExecutionPolicy Bypass -File .\scripts\install-medha.ps1

This installs Python backend dependencies and frontend dependencies.

## Daily startup

Double-click:

    scripts\Medha.bat

The launcher checks the local environment, starts FastAPI on 127.0.0.1:8000, waits for /api/health, starts Vite on 127.0.0.1:5173, waits for the frontend, opens Medha in the default browser, keeps both processes alive, and shuts them down when the launcher window closes.

The launcher starts Vite directly instead of npm run dev because the existing npm run dev command also starts the backend.

## Development

The existing development commands remain available. The launcher is an additional runtime convenience and does not replace the source-based workflow.

## Future desktop packaging

This runtime is the first layer. A future native desktop shell can use the same process-manager contract to provide a native Medha window, system tray, Windows startup, global hotkey, native notifications, and crash recovery UI.

Medha.bat is not a compiled executable yet. It is the one-click entry point while the native shell is being built.
