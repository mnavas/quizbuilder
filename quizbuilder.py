#!/usr/bin/env python3
"""QuizBuilder CLI — install, start, stop, update, and manage your server."""

import getpass
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

# ── Colors ────────────────────────────────────────────────────────────────────

def _cmd():
    """Returns the right command prefix for the current platform."""
    return "quizbuilder" if platform.system() == "Windows" else "./quizbuilder"

def _supports_color():
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.kernel32.SetConsoleMode(
                ctypes.windll.kernel32.GetStdHandle(-11), 7)
            return True
        except Exception:
            return False
    return sys.stdout.isatty()

_COLOR = _supports_color()

def _c(text, code): return f"\033[{code}m{text}\033[0m" if _COLOR else text
def green(t):  return _c(t, "32")
def yellow(t): return _c(t, "33")
def red(t):    return _c(t, "31")
def cyan(t):   return _c(t, "36")
def bold(t):   return _c(t, "1")
def dim(t):    return _c(t, "2")

def ok(msg):     print(green("✓ ") + msg)
def warn(msg):   print(yellow("⚠ ") + msg)
def err(msg):    print(red("✗ ") + msg)
def info(msg):   print(cyan("→ ") + msg)
def step(n, msg): print(f"\n{bold(str(n) + '.')} {msg}")

# ── Helpers ───────────────────────────────────────────────────────────────────

HERE = Path(__file__).parent.resolve()

def run(cmd, check=True):
    subprocess.run(cmd, shell=True, check=check, cwd=HERE)

def run_ok(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, cwd=HERE)
    return r.returncode == 0

def ask(prompt, default=None):
    suffix = f" [{default}]" if default else ""
    val = input(f"  {prompt}{suffix}: ").strip()
    return val or default or ""

def ask_password(prompt):
    while True:
        pw = getpass.getpass(f"  {prompt}: ")
        if len(pw) < 8:
            warn("  Password must be at least 8 characters.")
            continue
        pw2 = getpass.getpass(f"  Confirm: ")
        if pw != pw2:
            warn("  Passwords do not match, try again.")
            continue
        return pw

def ask_yes(prompt, default=True):
    suffix = "[Y/n]" if default else "[y/N]"
    val = input(f"  {prompt} {suffix} ").strip().lower()
    return (val in ("y", "yes")) if val else default

# ── Docker ────────────────────────────────────────────────────────────────────

def ensure_docker():
    if not run_ok("docker --version"):
        err("Docker is not installed.")
        sys_name = platform.system()
        if sys_name == "Linux":
            if ask_yes("Install Docker now?"):
                info("Running the official Docker install script…")
                run("curl -fsSL https://get.docker.com | sh")
                user = os.environ.get("USER", "")
                if user:
                    run(f"sudo usermod -aG docker {user}", check=False)
                ok("Docker installed.")
                print("  " + dim(f"You may need to log out and back in, then run: {_cmd()} install"))
                sys.exit(0)
        else:
            print(f"  Download Docker Desktop: {cyan('https://www.docker.com/products/docker-desktop/')}")
        sys.exit(1)

    if not run_ok("docker info"):
        err("Docker is installed but not running.")
        if platform.system() == "Linux":
            if ask_yes("Start Docker now?"):
                run("sudo systemctl start docker", check=False)
                time.sleep(2)
                if not run_ok("docker info"):
                    err("Could not start Docker. Try: sudo systemctl start docker")
                    sys.exit(1)
                ok("Docker started.")
                return
        else:
            print("  Please open Docker Desktop and wait for it to start, then try again.")
        sys.exit(1)

    if not run_ok("docker compose version"):
        err("Docker Compose plugin not found. Please update Docker Desktop.")
        sys.exit(1)

    ok("Docker is ready.")

# ── Git ───────────────────────────────────────────────────────────────────────

def ensure_git():
    if run_ok("git --version"):
        ok("Git is ready.")
        return
    err("Git is not installed.")
    if platform.system() == "Linux":
        if ask_yes("Install Git now?"):
            if run_ok("which apt-get"):
                run("sudo apt-get install -y git")
            elif run_ok("which yum"):
                run("sudo yum install -y git")
            else:
                print(f"  Install Git from: {cyan('https://git-scm.com/downloads')}")
                sys.exit(1)
            ok("Git installed.")
            return
    else:
        print(f"  Install Git from: {cyan('https://git-scm.com/downloads')}")
    sys.exit(1)

# ── Volumes ───────────────────────────────────────────────────────────────────

def ensure_volumes():
    for vol in ("quizbuilder_postgres-data", "quizbuilder_media-data"):
        if not run_ok(f"docker volume inspect {vol}"):
            run(f"docker volume create {vol}")
            ok(f"Created volume: {vol}")
        else:
            ok(f"Volume ready: {vol}")

# ── Network ───────────────────────────────────────────────────────────────────

def get_local_ips():
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        s.connect(("10.254.254.254", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except Exception:
        pass
    try:
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ips.add(info[4][0])
    except Exception:
        pass
    ips.discard("127.0.0.1")
    return sorted(ips)

# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_install():
    print(f"\n{bold('QuizBuilder — Installation')}\n")

    env_file = HERE / ".env"
    if env_file.exists():
        ok("QuizBuilder is already installed.")
        print("  Run " + bold(f"{_cmd()} start") + "   to start the server.")
        print("  Run " + bold(f"{_cmd()} status") + "  to check if it's running.")
        return

    step(1, "Checking Docker…")
    ensure_docker()

    step(2, "Creating storage volumes…")
    ensure_volumes()

    step(3, "Configuration")
    env_example = HERE / ".env.example"
    if not env_example.exists():
        err(".env.example not found. Make sure you're in the QuizBuilder folder.")
        sys.exit(1)

    print()
    print(f"  {bold('Admin account')}")
    admin_email = ask("Admin email")
    while not re.match(r"^[^@]+@[^@]+\.[^@]+$", admin_email):
        warn("  That doesn't look like a valid email address.")
        admin_email = ask("Admin email")
    admin_password = ask_password("Admin password (min 8 chars)")

    print()
    print(f"  {bold('Security — auto-generated')}")
    db_password = secrets.token_urlsafe(20)
    secret_key  = secrets.token_hex(32)
    ok(f"DB password:  {dim(db_password)}")
    ok(f"Secret key:   {dim(secret_key[:20] + '…')}")
    print(f"  {dim('Both are saved in .env — keep that file private.')}")

    env_content = (env_example.read_text()
        .replace("change_this_strong_password",    db_password)
        .replace("change_this_64_char_random_string", secret_key)
        .replace("admin@yourdomain.com",            admin_email)
        .replace("change_this_password",            admin_password)
    )
    env_file.write_text(env_content)
    ok(".env saved.")

    step(4, "Starting QuizBuilder…")
    run("docker compose up -d")

    ips = get_local_ips()
    print()
    print("─" * 52)
    ok(bold("QuizBuilder is running!"))
    print()
    if ips:
        print("  Open in your browser:")
        for ip in ips:
            print("  " + cyan(f"http://{ip}:3000"))
    print()
    print(f"  Log in with: {bold(admin_email)}")
    print()


def cmd_start():
    _check_installed()
    info("Starting QuizBuilder…")
    run("docker compose up -d")
    ok("QuizBuilder started.")
    _print_urls()


def cmd_stop():
    info("Stopping QuizBuilder…")
    run("docker compose down")
    ok("QuizBuilder stopped.")


def cmd_restart():
    _check_installed()
    info("Restarting QuizBuilder…")
    run("docker compose restart")
    ok("QuizBuilder restarted.")
    _print_urls()


def cmd_logs():
    run("docker compose logs -f", check=False)


def cmd_status():
    run("docker compose ps")


def cmd_update():
    print(f"\n{bold('QuizBuilder — Update')}\n")

    step(1, "Checking Git…")
    ensure_git()

    step(2, "Pulling latest version…")
    run("git pull origin main")

    step(3, "Rebuilding images…")
    run("docker compose build")

    step(4, "Restarting…")
    run("docker compose up -d")

    print()
    ok(bold("QuizBuilder updated and restarted."))
    _print_urls()


def cmd_hostname():
    ips = get_local_ips()
    print()
    if not ips:
        warn("No network addresses detected.")
        return
    print(bold("QuizBuilder is reachable at:"))
    print()
    for ip in ips:
        print("  " + cyan(f"http://{ip}:3000"))
    print()
    print(dim("  Share any of these with users on the same network."))
    print()


def cmd_help():
    print(f"""
{bold('QuizBuilder')} — self-hosted quiz platform

{bold('USAGE')}
  ./quizbuilder <command>        (Mac / Linux)
  quizbuilder <command>          (Windows)

{bold('COMMANDS')}
  {green('install')}    First-time setup: checks Docker, sets passwords, starts the server
  {green('start')}      Start the server
  {green('stop')}       Stop the server
  {green('restart')}    Restart the server
  {green('logs')}       View live logs  (Ctrl+C to exit)
  {green('status')}     Show container status
  {green('update')}     Pull the latest version and restart
  {green('hostname')}   List all URLs where QuizBuilder is reachable on the network
  {green('help')}       Show this message
""")

# ── Internal ──────────────────────────────────────────────────────────────────

def _check_installed():
    if not (HERE / ".env").exists():
        err("QuizBuilder is not set up yet.")
        print("  Run " + bold(f"{_cmd()} install") + " first.")
        sys.exit(1)

def _print_urls():
    ips = get_local_ips()
    if ips:
        print("  " + cyan(f"http://{ips[0]}:3000"))

# ── Entry point ───────────────────────────────────────────────────────────────

COMMANDS = {
    "install":  cmd_install,
    "start":    cmd_start,
    "stop":     cmd_stop,
    "restart":  cmd_restart,
    "logs":     cmd_logs,
    "status":   cmd_status,
    "update":   cmd_update,
    "hostname": cmd_hostname,
    "help":     cmd_help,
    "-h":       cmd_help,
    "--help":   cmd_help,
}

def main():
    if len(sys.argv) < 2:
        cmd_help()
        sys.exit(0)
    cmd = sys.argv[1].lower()
    if cmd not in COMMANDS:
        err(f"Unknown command: {cmd}")
        print("  Run " + bold(f"{_cmd()} help") + " for available commands.")
        sys.exit(1)
    COMMANDS[cmd]()

if __name__ == "__main__":
    main()
