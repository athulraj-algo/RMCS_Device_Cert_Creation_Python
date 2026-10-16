"""
RMCS Device Certificate Tool - desktop window.

Run with:  python app.py
CA files are read from the bundled resources/ folder.
Device folders are created in devices/ next to the app.
"""

import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

import certgen
from certgen import DeviceInfo


# ------------------------------------------------------------------
# Paths: work both as "python app.py" and as a PyInstaller .exe
# ------------------------------------------------------------------

def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resources_dir():
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "resources"
    return app_dir() / "resources"


def devices_dir():
    return app_dir() / "devices"


def open_folder(path):
    if sys.platform.startswith("win"):
        os.startfile(path)  # noqa: S606 - Windows only
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


# ------------------------------------------------------------------
# Window
# ------------------------------------------------------------------

LABEL_WIDTH = 100
STATUS_CLEAR_MS = 15_000  # messages disappear after 15 seconds


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RMCS Device Certificate Tool")
        self.resizable(False, False)
        self.last_folder = None
        self._clear_job = None

        self.device_id = tk.StringVar()
        self.client_id = tk.StringVar()
        self.project_id = tk.StringVar()
        self.password = tk.StringVar()
        self.show_password = tk.BooleanVar(value=False)

        self._build()
        self._check_resources()
        self.bind("<Return>", lambda _e: self.generate())

    # ---------------- layout ----------------

    def _build(self):
        root = ttk.Frame(self, padding=16)
        root.grid(sticky="nsew")

        ttk.Label(root, text="Create a device certificate",
                  font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))
        self.resource_label = ttk.Label(root, text="", wraplength=400)
        self.resource_label.grid(row=1, column=0, sticky="w", pady=(0, 12))

        device = ttk.LabelFrame(root, text="Device", padding=10)
        device.grid(row=2, column=0, sticky="ew")
        device.grid_columnconfigure(0, minsize=LABEL_WIDTH)

        ttk.Label(device, text="Device ID *").grid(row=0, column=0, sticky="w", pady=3)
        self.device_entry = ttk.Entry(device, textvariable=self.device_id, width=36)
        self.device_entry.grid(row=0, column=1, sticky="ew", pady=3, padx=(10, 0))
        ttk.Label(device, text="Becomes the folder name and certificate name",
                  foreground="gray").grid(row=1, column=1, sticky="w", padx=(10, 0))

        ttk.Label(device, text="Client ID").grid(row=2, column=0, sticky="w", pady=3)
        ttk.Entry(device, textvariable=self.client_id, width=36).grid(
            row=2, column=1, sticky="ew", pady=3, padx=(10, 0))

        ttk.Label(device, text="Project ID").grid(row=3, column=0, sticky="w", pady=3)
        ttk.Entry(device, textvariable=self.project_id, width=36).grid(
            row=3, column=1, sticky="ew", pady=3, padx=(10, 0))

        security = ttk.LabelFrame(root, text="Sub-CA key", padding=10)
        security.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        security.grid_columnconfigure(0, minsize=LABEL_WIDTH)

        ttk.Label(security, text="Password").grid(row=0, column=0, sticky="w")
        self.password_entry = ttk.Entry(security, textvariable=self.password,
                                        show="•", width=36)
        self.password_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        self.eye_button = ttk.Button(security,text="⚫",cursor="hand2",width=3,padding=0)
        self.eye_button.configure(style="Small.TButton")
        self.eye_button.grid(row=0, column=2, padx=(6, 0))
        self.eye_button.bind("<Button-1>", lambda _e: self._toggle_password())
        style = ttk.Style()
        style.configure("Small.TButton", font=("Segoe UI Emoji", 6), padding=0)
        ttk.Label(security, text="Leave empty if the Sub-CA key has no password",
                  foreground="gray").grid(row=1, column=1, sticky="w", padx=(10, 0))

        buttons = ttk.Frame(root)
        buttons.grid(row=4, column=0, sticky="w", pady=(14, 0))
        self.generate_button = ttk.Button(buttons, text="Generate", command=self.generate)
        self.generate_button.pack(side="left")
        self.open_button = ttk.Button(buttons, text="Open folder", state="disabled",
                                      command=lambda: open_folder(self.last_folder))
        self.open_button.pack(side="left", padx=(8, 0))

        self.status = ttk.Label(root, text="", wraplength=400)
        self.status.grid(row=5, column=0, sticky="w", pady=(12, 0))

        self.device_entry.focus_set()

    # ---------------- behaviour ----------------

    def _check_resources(self):
        missing = [
            name for name in (certgen.ROOT_CERT_FILE, certgen.SUB_CA_CERT_FILE,
                              certgen.SUB_CA_KEY_FILE)
            if not (resources_dir() / name).is_file()
        ]
        if missing:
            self.resource_label.config(
                text=f"Missing in {resources_dir()}: {', '.join(missing)}",
                foreground="red")
            self.generate_button.config(state="disabled")
        else:
            self.resource_label.config(
                text=f"Device folders are saved in: {devices_dir()}", foreground="gray")

    def _toggle_password(self):
        if self.password_entry.cget("show") == "":  # visible → hide
            self.password_entry.config(show="•")
            self.eye_button.config(text="⚫")
        else:  # hidden → show
            self.password_entry.config(show="")
            self.eye_button.config(text="⚪")

    def _set_status(self, text, colour):
        # Cancel the previous timer so a new message gets its full 15 seconds.
        if self._clear_job is not None:
            self.after_cancel(self._clear_job)
        self.status.config(text=text, foreground=colour)
        self._clear_job = self.after(STATUS_CLEAR_MS, self._clear_status)
        self.update_idletasks()

    def _clear_status(self):
        self._clear_job = None
        self.status.config(text="")

    def _confirm_overwrite(self, device_id):
        return messagebox.askyesno(
            "Overwrite existing certificates?",
            f"A folder for device '{device_id}' already exists:\n"
            f"{devices_dir() / device_id}\n\n"
            "Continuing will DELETE everything in that folder and create a new key "
            "and certificate. The device must then be updated with the new files.\n\n"
            "Note: the old certificate is not revoked. It will still be accepted by "
            "EMQX until it expires.\n\n"
            "Overwrite?",
            icon="warning",
            default="no",
            parent=self,
        )

    def generate(self):
        if str(self.generate_button["state"]) == "disabled":
            return
        self.open_button.config(state="disabled")

        info = DeviceInfo(
            device_id=self.device_id.get().strip(),
            client_id=self.client_id.get().strip(),
            project_id=self.project_id.get().strip(),
        )

        try:
            # 1. Check the device ID, 2. check the password / CA files,
            # and only then 3. ask about overwriting an existing folder.
            certgen.validate_device_info(info)
            bundle = certgen.load_ca_bundle(resources_dir(), self.password.get())

            overwrite = False
            if certgen.device_folder_exists(devices_dir(), info.device_id):
                if not self._confirm_overwrite(info.device_id):
                    self._set_status("Cancelled. The existing folder was not changed.", "gray")
                    return
                overwrite = True

            self._set_status("Generating...", "gray")
            folder = certgen.issue_device(bundle, info, devices_dir(), overwrite=overwrite)
        except (ValueError, FileExistsError, FileNotFoundError, PermissionError) as error:
            self._set_status(str(error), "red")
            return
        except Exception as error:  # unexpected: show it instead of crashing
            self._set_status(f"Unexpected error: {error}", "red")
            messagebox.showerror("Unexpected error", str(error))
            return

        self.last_folder = folder
        self.open_button.config(state="normal")
        action = "Replaced" if overwrite else "Created"
        self._set_status(f"{action} {folder}", "green")
        self.device_id.set("")
        self.client_id.set("")
        self.project_id.set("")
        self.password.set("")
        self.password_entry.config(show="•")  # hide the password again
        self.eye_button.config(text="⚫")  # reset the eye icon to "hidden"
        self.device_entry.focus_set()


if __name__ == "__main__":
    App().mainloop()