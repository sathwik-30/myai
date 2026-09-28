"""Native Windows popup for Medha.

This launcher connects to the existing local Medha API. The bearer token is
kept only in memory for this desktop session.
"""

import json
import threading
import tkinter as tk
from tkinter import messagebox
from urllib import request as urlrequest


API = "http://127.0.0.1:8000/api"


def http(method, path, token, payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urlrequest.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    with urlrequest.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


class MedhaDesktop:
    def __init__(self, root):
        self.root = root
        self.root.title("Medha")
        self.root.geometry("420x560")
        self.root.attributes("-topmost", True)
        self.token = None

        self._build()

    def _build(self):
        frame = tk.Frame(self.root, padx=14, pady=14)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Medha", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        tk.Label(frame, text="Desktop assistant", font=("Segoe UI", 10)).pack(
            anchor="w", pady=(0, 12)
        )

        auth = tk.Frame(frame)
        auth.pack(fill="x")

        self.username = tk.Entry(auth)
        self.username.insert(0, "username")
        self.username.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.password = tk.Entry(auth, show="*")
        self.password.pack(side="left", fill="x", expand=True, padx=(0, 6))

        tk.Button(auth, text="Login", command=self.login).pack(side="right")

        self.output = tk.Text(frame, wrap="word", state="disabled")
        self.output.pack(fill="both", expand=True, pady=12)

        self.input = tk.Entry(frame)
        self.input.pack(fill="x")
        self.input.bind("<Return>", lambda _event: self.send())

        tk.Button(frame, text="Send", command=self.send).pack(anchor="e", pady=(8, 0))

    def write(self, speaker, text):
        self.output.configure(state="normal")
        self.output.insert("end", f"{speaker}: {text}\n\n")
        self.output.see("end")
        self.output.configure(state="disabled")

    def login(self):
        try:
            result = http(
                "POST",
                "/auth/login",
                "",
                {
                    "username": self.username.get().strip(),
                    "password": self.password.get(),
                },
            )
            self.token = result["access_token"]
            self.write("Medha", "Connected to your desktop session.")
        except Exception as exc:
            messagebox.showerror("Medha login", f"Login failed: {exc}")

    def send(self):
        if not self.token:
            messagebox.showinfo("Medha", "Log in first.")
            return

        message = self.input.get().strip()
        if not message:
            return

        self.input.delete(0, "end")
        self.write("You", message)

        def worker():
            try:
                result = http("GET", "/desktop/status", self.token)
                reply = f"Desktop connected: {result.get('platform')}"
            except Exception as exc:
                reply = f"Desktop connection error: {exc}"
            self.root.after(0, lambda: self.write("Medha", reply))

        threading.Thread(target=worker, daemon=True).start()


if __name__ == "__main__":
    root = tk.Tk()
    MedhaDesktop(root)
    root.mainloop()
