# Medha Windows Desktop Agent

First desktop-control layer for Medha.

Install from the repository root:

    python -m pip install -r requirements-desktop.txt

Capabilities:
- Screen capture
- Window enumeration and focus
- Safe application launch for a small allowlist
- Mouse clicks
- Keyboard typing
- Hotkeys
- Scrolling
- Process inspection

All desktop API endpoints require the normal Medha Bearer token.

The bridge does not expose arbitrary shell or PowerShell execution. The core
override remains authoritative, and destructive or irreversible actions must be
confirmed by the agent layer before execution.

This is a foundation for the full autonomous desktop agent.
