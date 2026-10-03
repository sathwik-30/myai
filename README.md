# Medha

Medha is a local personal AI application with a FastAPI backend and React/Vite frontend.

## Windows quick start

### Requirements

Install Python 3.11+ and Node.js 18+.

### Start Medha

From the repository root, run:

```cmd
scripts\Medha.bat
```

The launcher automatically:

1. Creates `.venv` if it does not exist.
2. Installs backend Python dependencies.
3. Installs desktop-control dependencies when the requirements file exists.
4. Installs frontend npm dependencies when `node_modules` is missing.
5. Starts FastAPI on `http://127.0.0.1:8000`.
6. Waits for the backend health endpoint.
7. Starts Vite on `http://127.0.0.1:5173`.
8. Opens Medha in the default browser.

Close the launcher window to stop Medha.

## Manual development

Backend:

```cmd
.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Frontend:

```cmd
cd frontend
npm run dev
```

## First run

The first launch may take several minutes because dependencies may need to be installed. Later launches reuse the existing environment.

## Troubleshooting

Check:

```text
logs\launcher.log
```

For a clean dependency setup, delete `.venv` and `frontend\node_modules`, then run `scripts\Medha.bat` again.
