"""
Local-machine-only helper that makes sure a real, queryable OpenCode server is
available at OPENCODE_SERVER_URL for app/services/ai_opencode_policy_evaluation.py.

Why this exists: opencode's default `opencode` command starts an interactive
TUI session that does NOT expose an HTTP API on this machine - only
`opencode serve` does. Every time it's started, `opencode serve` binds to a
fresh ephemeral port unless one is pinned with --port, and it reads its own
Basic Auth password from the OPENCODE_SERVER_PASSWORD environment variable at
startup (confirmed directly against the installed opencode binary - it is not
a CLI flag). This script:

  1. Checks whether .env's OPENCODE_SERVER_URL is already reachable with
     OPENCODE_SERVER_PASSWORD. If so, does nothing - the feature already works.
  2. If not, looks for any other opencode.exe/opencode process on this machine
     that already has a server listening and answering to that same password
     (e.g. one started manually on a different port), and if found, rewrites
     .env's OPENCODE_SERVER_URL to point at it instead of guessing/duplicating.
  3. Otherwise, launches a new detached `opencode serve` bound to the port in
     .env's OPENCODE_SERVER_URL (default 28894), passing OPENCODE_SERVER_PASSWORD
     only to that child process's environment, and waits for it to come up.

This never talks to any other machine and never changes the local-only design
in docs/local-ai-setup.md - it only automates "start/find the server for me"
on the one machine it's run on. Run it any time with:

    python scripts/opencode_local_session.py

Safe to re-run - it's idempotent and leaves an already-working setup alone.
"""
import os
import re
import sys
import time
import base64
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / '.env'
DEFAULT_URL = 'http://127.0.0.1:28894'
STARTUP_TIMEOUT = 20  # seconds to wait for a freshly launched `opencode serve` to come up
STARTUP_POLL = 1


def _read_env():
    values = {}
    if not ENV_PATH.exists():
        return values
    for line in ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        values[key.strip()] = value.strip()
    return values


def _write_env_url(new_url):
    text = ENV_PATH.read_text(encoding='utf-8') if ENV_PATH.exists() else ''
    if re.search(r'^OPENCODE_SERVER_URL=.*$', text, re.MULTILINE):
        text = re.sub(r'^OPENCODE_SERVER_URL=.*$', f'OPENCODE_SERVER_URL={new_url}', text, flags=re.MULTILINE)
    else:
        if text and not text.endswith('\n'):
            text += '\n'
        text += f'OPENCODE_SERVER_URL={new_url}\n'
    ENV_PATH.write_text(text, encoding='utf-8')


def _check_reachable(url, password, timeout=3):
    auth = base64.b64encode(f'opencode:{password}'.encode()).decode()
    req = urllib.request.Request(url.rstrip('/') + '/api/session', headers={'Authorization': f'Basic {auth}'})
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return True
    except Exception:
        return False


def _listening_opencode_ports():
    """Windows-only: ports any opencode*.exe process is currently LISTENing on,
    found via PowerShell (no extra Python deps needed for this one-off check)."""
    if os.name != 'nt':
        return []
    ps_script = (
        "Get-Process | Where-Object { $_.ProcessName -match 'opencode' } | "
        "ForEach-Object { Get-NetTCPConnection -OwningProcess $_.Id -State Listen "
        "-ErrorAction SilentlyContinue } | Select-Object -ExpandProperty LocalPort"
    )
    try:
        out = subprocess.run(
            ['powershell', '-NoProfile', '-Command', ps_script],
            capture_output=True, text=True, timeout=15,
        )
    except Exception:
        return []
    ports = []
    for line in out.stdout.splitlines():
        line = line.strip()
        if line.isdigit():
            ports.append(int(line))
    return ports


def _port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(('127.0.0.1', port)) == 0


def main():
    env = _read_env()
    password = env.get('OPENCODE_SERVER_PASSWORD') or os.environ.get('OPENCODE_SERVER_PASSWORD')
    if not password:
        print('OPENCODE_SERVER_PASSWORD is not set in .env - see docs/local-ai-setup.md step 3. Nothing to do.')
        return 1

    configured_url = env.get('OPENCODE_SERVER_URL', DEFAULT_URL)

    if _check_reachable(configured_url, password):
        print(f'OK: {configured_url} is already up and answering - Evaluate should work.')
        return 0

    print(f'{configured_url} is not reachable. Looking for another opencode server already running on this machine...')
    for port in _listening_opencode_ports():
        candidate_url = f'http://127.0.0.1:{port}'
        if candidate_url == configured_url.rstrip('/'):
            continue
        if _check_reachable(candidate_url, password):
            print(f'Found a working opencode server at {candidate_url} - updating .env to use it.')
            _write_env_url(candidate_url)
            return 0

    print('No existing reachable server found. Starting a new `opencode serve`...')
    m = re.search(r':(\d+)$', configured_url)
    port = int(m.group(1)) if m else 28894
    if _port_in_use(port):
        print(f'Port {port} is already occupied by something that is not answering as an OpenCode '
              f'server with this password - pick a different OPENCODE_SERVER_URL in .env and retry.')
        return 1

    opencode_exe = shutil.which('opencode')
    if not opencode_exe:
        print('`opencode` was not found on PATH - install it per docs/local-ai-setup.md step 1.')
        return 1

    # Forward every .env value (not just the server password) into the server process's own
    # environment - this is how OpenCode auto-detects direct providers like `deepseek` from a
    # *_API_KEY variable (via its models.dev provider catalog) without a separate `opencode
    # auth login`. Explicit .env values win over anything already in the parent shell's env.
    child_env = dict(os.environ)
    child_env.update(env)
    child_env['OPENCODE_SERVER_PASSWORD'] = password
    creationflags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0
    subprocess.Popen(
        [opencode_exe, 'serve', '--port', str(port), '--hostname', '127.0.0.1'],
        env=child_env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True,
        shell=(os.name == 'nt'),
    )

    deadline = time.monotonic() + STARTUP_TIMEOUT
    url = f'http://127.0.0.1:{port}'
    while time.monotonic() < deadline:
        if _check_reachable(url, password):
            if url != configured_url.rstrip('/'):
                _write_env_url(url)
            print(f'OK: started `opencode serve` on {url} and it is answering - Evaluate should work.')
            return 0
        time.sleep(STARTUP_POLL)

    print(f'Started `opencode serve` on {url} but it did not answer within {STARTUP_TIMEOUT}s - check '
          f'`opencode serve --print-logs` manually.')
    return 1


if __name__ == '__main__':
    sys.exit(main())
