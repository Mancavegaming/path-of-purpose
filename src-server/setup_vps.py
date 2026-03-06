"""
Path of Purpose — VPS Server Setup
====================================
One-file installer that:
  1. Requests admin elevation (firewall + service install require it)
  2. Lets the user choose an install directory
  3. Checks for / installs Python 3.11+
  4. Extracts bundled src-server/ and src-python/ to install dir
  5. Creates a venv and installs packages
  6. Collects secrets via GUI form
  7. Writes .env (auto-generates JWT secret)
  8. Opens firewall port
  9. Downloads NSSM and installs a Windows service
 10. Verifies the /health endpoint
 11. Shows a summary with IP + port

Build with:
    cd "D:\\Dev\\Path of Purpose"
    pyinstaller --onefile ^
      --add-data "src-server;src-server" ^
      --add-data "src-python;src-python" ^
      --name "PathOfPurpose-ServerSetup" ^
      src-server/setup_vps.py
"""

from __future__ import annotations

import ctypes
import os
import secrets
import shutil
import socket
import subprocess
import sys
import textwrap
import zipfile
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen, urlretrieve

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SERVICE_NAME = "PathOfPurpose"
PYTHON_DOWNLOAD_URL = (
    "https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe"
)
NSSM_DOWNLOAD_URL = "https://nssm.cc/release/nssm-2.24.zip"
DEFAULT_INSTALL_DIR = r"C:\PathOfPurpose"
MIN_PYTHON_VERSION = (3, 11)

# ---------------------------------------------------------------------------
# 1. Admin elevation
# ---------------------------------------------------------------------------


def is_admin() -> bool:
    """Return True if running as Administrator."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_admin() -> None:
    """Re-launch this script elevated if not already admin."""
    if is_admin():
        return
    # Re-launch with ShellExecuteW "runas"
    params = " ".join(f'"{a}"' for a in sys.argv)
    executable = sys.executable
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", executable, params, None, 1
    )
    sys.exit(0)


# ---------------------------------------------------------------------------
# 2. Find / install Python
# ---------------------------------------------------------------------------


def _parse_python_version(ver_string: str) -> tuple[int, ...]:
    """Parse 'Python 3.12.9' → (3, 12, 9)."""
    parts = ver_string.strip().split()[-1]
    return tuple(int(x) for x in parts.split("."))


def find_python() -> str | None:
    """Return path to a suitable python.exe (3.11+), or None."""
    candidates = ["python", "python3"]
    # Also check common install locations
    for base in [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python",
        Path(r"C:\Python312"),
        Path(r"C:\Python311"),
        Path(r"C:\Python313"),
    ]:
        if base.exists():
            for child in base.iterdir():
                exe = child / "python.exe"
                if exe.exists():
                    candidates.append(str(exe))

    for cmd in candidates:
        try:
            result = subprocess.run(
                [cmd, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                ver = _parse_python_version(result.stdout or result.stderr)
                if ver >= MIN_PYTHON_VERSION:
                    # Resolve full path
                    if os.sep not in cmd and "/" not in cmd:
                        which = shutil.which(cmd)
                        return which or cmd
                    return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            continue
    return None


def download_python(status_callback) -> str:
    """Download and silently install Python, return path to python.exe."""
    installer = Path(os.environ.get("TEMP", ".")) / "python-installer.exe"
    status_callback("Downloading Python 3.12 …")
    urlretrieve(PYTHON_DOWNLOAD_URL, str(installer))

    status_callback("Installing Python 3.12 (silent) …")
    subprocess.run(
        [
            str(installer),
            "/quiet",
            "InstallAllUsers=1",
            "PrependPath=1",
            "Include_test=0",
        ],
        check=True,
        timeout=300,
    )
    installer.unlink(missing_ok=True)

    # After install, find it
    python = find_python()
    if python is None:
        raise RuntimeError(
            "Python was installed but could not be found on PATH. "
            "Please add Python to your PATH and re-run this installer."
        )
    return python


# ---------------------------------------------------------------------------
# 3. Choose install directory (tkinter)
# ---------------------------------------------------------------------------


def choose_install_dir() -> Path:
    """Show a folder picker, return chosen path."""
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    chosen = filedialog.askdirectory(
        title="Choose installation directory",
        initialdir=DEFAULT_INSTALL_DIR,
    )
    root.destroy()
    if not chosen:
        # User cancelled — use default
        return Path(DEFAULT_INSTALL_DIR)
    return Path(chosen)


# ---------------------------------------------------------------------------
# 4. Extract bundled source
# ---------------------------------------------------------------------------


def get_bundle_dir() -> Path:
    """Return the PyInstaller bundle temp dir, or the repo root for dev."""
    if getattr(sys, "_MEIPASS", None):
        return Path(sys._MEIPASS)
    # Dev mode: assume running from repo root or src-server/
    candidate = Path(__file__).resolve().parent.parent
    if (candidate / "src-server").exists():
        return candidate
    return Path.cwd()


def extract_source(install_dir: Path, status_callback) -> None:
    """Copy src-server/ and src-python/ from bundle to install dir."""
    bundle = get_bundle_dir()
    for folder in ("src-server", "src-python"):
        src = bundle / folder
        dst = install_dir / folder
        if not src.exists():
            raise FileNotFoundError(
                f"Bundled folder '{folder}' not found at {src}. "
                "Make sure you built the exe with --add-data."
            )
        status_callback(f"Copying {folder} …")
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(str(src), str(dst))


# ---------------------------------------------------------------------------
# 5. Create venv + install packages
# ---------------------------------------------------------------------------


def create_venv(python: str, install_dir: Path, status_callback) -> Path:
    """Create venv and pip install -e src-server -e src-python. Return venv path."""
    venv_dir = install_dir / "venv"
    status_callback("Creating Python virtual environment …")
    subprocess.run(
        [python, "-m", "venv", str(venv_dir)],
        check=True,
        timeout=120,
    )

    pip = str(venv_dir / "Scripts" / "pip.exe")

    status_callback("Installing dependencies (this may take a minute) …")
    subprocess.run(
        [
            pip, "install", "-e",
            str(install_dir / "src-python"),
            "-e",
            str(install_dir / "src-server"),
        ],
        check=True,
        timeout=600,
    )
    return venv_dir


# ---------------------------------------------------------------------------
# 6. Collect secrets (tkinter form)
# ---------------------------------------------------------------------------

FIELD_DEFS: list[tuple[str, str, str, bool]] = [
    # (env_var_name, label, default, read_only)
    ("GEMINI_API_KEY", "Google Gemini API Key", "", False),
    ("AI_PROVIDER", "AI Provider", "gemini", True),
    ("DISCORD_CLIENT_ID", "Discord Client ID", "", False),
    ("DISCORD_CLIENT_SECRET", "Discord Client Secret", "", False),
    ("DISCORD_GUILD_ID", "Discord Server ID", "1463950138430193758", True),
    ("STRIPE_SECRET_KEY", "Stripe Secret Key", "", False),
    ("STRIPE_WEBHOOK_SECRET", "Stripe Webhook Secret", "", False),
    ("STRIPE_PRICE_ID", "Stripe Price ID", "", False),
    ("SERVER_PORT", "Server Port", "8080", False),
    ("JWT_SECRET", "JWT Secret (auto-generated)", "", True),
]


def collect_secrets() -> dict[str, str] | None:
    """Show tkinter form, return dict of env vars or None if cancelled."""
    import tkinter as tk
    from tkinter import messagebox

    jwt_secret = secrets.token_urlsafe(48)
    result: dict[str, str] | None = None

    root = tk.Tk()
    root.title("Path of Purpose — Server Configuration")
    root.resizable(False, False)
    root.configure(bg="#1e1e2e")

    entries: dict[str, tk.Entry] = {}

    tk.Label(
        root,
        text="Path of Purpose — Server Setup",
        font=("Segoe UI", 14, "bold"),
        fg="#cdd6f4",
        bg="#1e1e2e",
    ).grid(row=0, column=0, columnspan=2, pady=(15, 10), padx=20)

    for i, (env_name, label, default, read_only) in enumerate(FIELD_DEFS, start=1):
        tk.Label(
            root,
            text=label + ":",
            anchor="w",
            fg="#bac2de",
            bg="#1e1e2e",
            font=("Segoe UI", 10),
        ).grid(row=i, column=0, sticky="w", padx=(20, 10), pady=4)

        entry = tk.Entry(root, width=50, font=("Consolas", 10))
        if env_name == "JWT_SECRET":
            entry.insert(0, jwt_secret)
            entry.configure(state="readonly")
        elif default:
            entry.insert(0, default)

        # Mask secret fields
        if "SECRET" in env_name or "KEY" in env_name:
            if not read_only:
                entry.configure(show="*")

        entry.grid(row=i, column=1, padx=(0, 20), pady=4)
        entries[env_name] = entry

    def on_submit():
        nonlocal result
        values: dict[str, str] = {}
        for env_name, label, _default, _ro in FIELD_DEFS:
            val = entries[env_name].get().strip()
            if env_name == "JWT_SECRET":
                val = jwt_secret
            if not val and env_name != "SERVER_PORT":
                messagebox.showerror("Missing field", f"Please fill in: {label}")
                return
            values[env_name] = val
        if not values.get("SERVER_PORT"):
            values["SERVER_PORT"] = "8080"
        result = values
        root.destroy()

    def on_cancel():
        root.destroy()

    btn_frame = tk.Frame(root, bg="#1e1e2e")
    btn_frame.grid(row=len(FIELD_DEFS) + 1, column=0, columnspan=2, pady=15)

    tk.Button(
        btn_frame,
        text="Install",
        command=on_submit,
        bg="#89b4fa",
        fg="#1e1e2e",
        font=("Segoe UI", 11, "bold"),
        width=12,
        relief="flat",
    ).pack(side="left", padx=10)

    tk.Button(
        btn_frame,
        text="Cancel",
        command=on_cancel,
        bg="#585b70",
        fg="#cdd6f4",
        font=("Segoe UI", 11),
        width=12,
        relief="flat",
    ).pack(side="left", padx=10)

    root.mainloop()
    return result


# ---------------------------------------------------------------------------
# 7. Write .env
# ---------------------------------------------------------------------------


def write_env(install_dir: Path, env_vars: dict[str, str]) -> Path:
    """Write .env file into install_dir/src-server/."""
    env_path = install_dir / "src-server" / ".env"
    lines = [f"{k}={v}" for k, v in env_vars.items()]
    # Add server host binding
    lines.append("SERVER_HOST=0.0.0.0")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return env_path


# ---------------------------------------------------------------------------
# 8. Open firewall port
# ---------------------------------------------------------------------------


def open_firewall(port: int) -> None:
    """Add a Windows Firewall inbound rule for the given port."""
    rule_name = f"PathOfPurpose-API-{port}"
    # Remove existing rule if present (ignore errors)
    subprocess.run(
        [
            "netsh", "advfirewall", "firewall", "delete", "rule",
            f"name={rule_name}",
        ],
        capture_output=True,
    )
    subprocess.run(
        [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={rule_name}",
            "dir=in",
            "action=allow",
            "protocol=TCP",
            f"localport={port}",
        ],
        check=True,
    )


# ---------------------------------------------------------------------------
# 9. Download NSSM
# ---------------------------------------------------------------------------


def install_nssm(install_dir: Path, status_callback) -> Path:
    """Download NSSM and extract nssm.exe. Return path to nssm.exe."""
    nssm_exe = install_dir / "nssm.exe"
    if nssm_exe.exists():
        return nssm_exe

    zip_path = install_dir / "nssm.zip"
    status_callback("Downloading NSSM …")
    urlretrieve(NSSM_DOWNLOAD_URL, str(zip_path))

    status_callback("Extracting NSSM …")
    with zipfile.ZipFile(str(zip_path), "r") as zf:
        # Find the 64-bit nssm.exe inside the zip
        for name in zf.namelist():
            if name.endswith("win64/nssm.exe"):
                with zf.open(name) as src, open(str(nssm_exe), "wb") as dst:
                    dst.write(src.read())
                break
        else:
            raise FileNotFoundError("Could not find win64/nssm.exe in NSSM zip")
    zip_path.unlink(missing_ok=True)
    return nssm_exe


# ---------------------------------------------------------------------------
# 10. Install + start Windows Service
# ---------------------------------------------------------------------------


def install_service(
    nssm: Path, venv_dir: Path, install_dir: Path, port: int
) -> None:
    """Install and start the service via NSSM."""
    python_exe = str(venv_dir / "Scripts" / "python.exe")
    app_module = "pop_server.run"

    # Remove existing service if present (ignore errors)
    subprocess.run([str(nssm), "stop", SERVICE_NAME], capture_output=True)
    subprocess.run([str(nssm), "remove", SERVICE_NAME, "confirm"], capture_output=True)

    # Install
    subprocess.run(
        [
            str(nssm), "install", SERVICE_NAME,
            python_exe, "-m", "uvicorn",
            f"{app_module}:app",
            "--host", "0.0.0.0",
            "--port", str(port),
        ],
        check=True,
    )

    # Configure
    server_dir = str(install_dir / "src-server")
    subprocess.run(
        [str(nssm), "set", SERVICE_NAME, "AppDirectory", server_dir],
        check=True,
    )
    subprocess.run(
        [str(nssm), "set", SERVICE_NAME, "DisplayName", "Path of Purpose API"],
        check=True,
    )
    subprocess.run(
        [str(nssm), "set", SERVICE_NAME, "Description",
         "Path of Purpose backend API server"],
        check=True,
    )
    # Stdout/stderr logging
    log_dir = install_dir / "logs"
    log_dir.mkdir(exist_ok=True)
    subprocess.run(
        [str(nssm), "set", SERVICE_NAME, "AppStdout",
         str(log_dir / "server-stdout.log")],
        check=True,
    )
    subprocess.run(
        [str(nssm), "set", SERVICE_NAME, "AppStderr",
         str(log_dir / "server-stderr.log")],
        check=True,
    )

    # Start
    subprocess.run([str(nssm), "start", SERVICE_NAME], check=True)


# ---------------------------------------------------------------------------
# 11. Verify /health
# ---------------------------------------------------------------------------


def verify_health(port: int, retries: int = 5) -> bool:
    """Hit /health and return True if it responds OK."""
    import time

    url = f"http://localhost:{port}/health"
    for attempt in range(retries):
        try:
            resp = urlopen(url, timeout=5)
            if resp.status == 200:
                return True
        except (URLError, OSError):
            pass
        time.sleep(2)
    return False


# ---------------------------------------------------------------------------
# 12. Summary dialog
# ---------------------------------------------------------------------------


def get_server_ip() -> str:
    """Best-effort to find the server's LAN/public IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def show_summary(port: int, healthy: bool, install_dir: Path) -> None:
    """Show final summary via tkinter messagebox."""
    import tkinter as tk
    from tkinter import messagebox

    ip = get_server_ip()
    status = "RUNNING" if healthy else "FAILED TO START (check logs)"

    msg = textwrap.dedent(f"""\
        Path of Purpose API Server Setup Complete!

        Status:        {status}
        Service Name:  {SERVICE_NAME}
        Install Dir:   {install_dir}
        Endpoint:      http://{ip}:{port}
        Health Check:  http://{ip}:{port}/health
        Logs:          {install_dir / "logs"}

        Manage with:
          nssm stop {SERVICE_NAME}
          nssm start {SERVICE_NAME}
          nssm restart {SERVICE_NAME}
          nssm remove {SERVICE_NAME} confirm
    """)

    root = tk.Tk()
    root.withdraw()
    if healthy:
        messagebox.showinfo("Setup Complete", msg)
    else:
        messagebox.showwarning("Setup Complete (with warnings)", msg)
    root.destroy()


# ---------------------------------------------------------------------------
# Progress window
# ---------------------------------------------------------------------------


class ProgressWindow:
    """Simple tkinter window showing install progress."""

    def __init__(self):
        import tkinter as tk

        self.root = tk.Tk()
        self.root.title("Path of Purpose — Installing")
        self.root.geometry("500x120")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")

        self.label = tk.Label(
            self.root,
            text="Starting installation …",
            font=("Segoe UI", 11),
            fg="#cdd6f4",
            bg="#1e1e2e",
            wraplength=460,
        )
        self.label.pack(pady=30, padx=20)
        self.root.update()

    def update(self, text: str) -> None:
        self.label.configure(text=text)
        self.root.update()

    def close(self) -> None:
        self.root.destroy()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    # Step 1: Ensure admin
    ensure_admin()

    # Step 2: Choose install directory
    install_dir = choose_install_dir()
    install_dir.mkdir(parents=True, exist_ok=True)

    # Step 3: Collect secrets before starting long operations
    env_vars = collect_secrets()
    if env_vars is None:
        print("Setup cancelled by user.")
        return

    port = int(env_vars.get("SERVER_PORT", "8080"))

    # Show progress window for remaining steps
    progress = ProgressWindow()

    try:
        # Step 4: Find or install Python
        progress.update("Checking for Python 3.11+ …")
        python = find_python()
        if python is None:
            python = download_python(progress.update)
        progress.update(f"Using Python: {python}")

        # Step 5: Extract bundled source
        extract_source(install_dir, progress.update)

        # Step 6: Create venv + install packages
        venv_dir = create_venv(python, install_dir, progress.update)

        # Step 7: Write .env
        progress.update("Writing configuration …")
        write_env(install_dir, env_vars)

        # Step 8: Open firewall port
        progress.update(f"Opening firewall port {port} …")
        open_firewall(port)

        # Step 9: Download NSSM
        nssm = install_nssm(install_dir, progress.update)

        # Step 10: Install + start service
        progress.update("Installing Windows service …")
        install_service(nssm, venv_dir, install_dir, port)

        # Step 11: Verify health
        progress.update("Verifying server health …")
        healthy = verify_health(port)

        progress.close()

        # Step 12: Show summary
        show_summary(port, healthy, install_dir)

    except Exception as exc:
        progress.close()
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Setup Error",
            f"Installation failed:\n\n{exc}\n\n"
            f"Check {install_dir / 'logs'} for details.",
        )
        root.destroy()
        raise


if __name__ == "__main__":
    main()
