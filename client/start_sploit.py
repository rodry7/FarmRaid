#!/usr/bin/env python3
"""
FarmRaid client — run your exploit against every active team and submit captured flags.

Usage:
    python3 start_sploit.py --host http://localhost:8000 --password changeme ./exploit.py
    python3 start_sploit.py --host http://localhost:8000 --password changeme ./exploit.py \
        --period 60 --timeout 20 --threads 20
"""

import argparse
import logging
import os
import re
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin

import requests

# ── ANSI colour helpers ───────────────────────────────────────────────────────

_TTY = sys.stdout.isatty() and os.name != "nt"


def _esc(*codes: int) -> str:
    return f"\033[{';'.join(map(str, codes))}m" if _TTY else ""


RESET   = _esc(0)
BOLD    = _esc(1)
RED     = _esc(31)
GREEN   = _esc(32)
YELLOW  = _esc(33)
CYAN    = _esc(36)
DIM     = _esc(2)

# Distinct colours used to tag team IPs in output.
_PALETTE = [_esc(c) for c in (32, 33, 34, 35, 36, 91, 92, 93, 94, 95, 96)]
_team_colors: dict[str, str] = {}
_team_color_lock = threading.Lock()


def _team_color(ip: str) -> str:
    with _team_color_lock:
        if ip not in _team_colors:
            _team_colors[ip] = _PALETTE[len(_team_colors) % len(_PALETTE)]
        return _team_colors[ip]


def col(text: str, *codes: str) -> str:
    """Wrap text in ANSI codes; no-op when not a TTY."""
    if not _TTY or not codes:
        return text
    return "".join(codes) + text + RESET


# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    format=f"%(asctime)s  {col('%(levelname)-8s', YELLOW)}  %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger("farmraid")

# ── Banner ────────────────────────────────────────────────────────────────────

BANNER = r"""
  _____                    ____        _     _
 |  ___|_ _ _ __ _ __ ___ |  _ \ __ _(_) __| |
 | |_ / _` | '__| '_ ` _ \| |_) / _` | |/ _` |
 |  _| (_| | |  | | | | | |  _ < (_| | | (_| |
 |_|  \__,_|_|  |_| |_| |_|_| \_\__,_|_|\__,_|
"""

# ── CLI ───────────────────────────────────────────────────────────────────────


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run an exploit against all active FarmRaid teams and submit flags.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument(
        "exploit",
        help="Exploit script — receives team IP as the first positional argument",
    )
    p.add_argument("--host",     required=True,        help="FarmRaid server URL")
    p.add_argument("--password", required=True,        help="FarmRaid server password")
    p.add_argument("--period",   type=float, default=120, metavar="SECS",
                   help="Seconds between attack rounds")
    p.add_argument("--timeout",  type=int,   default=30,  metavar="SECS",
                   help="Max seconds per exploit run")
    p.add_argument("--threads",  type=int,   default=10,  metavar="N",
                   help="Max concurrent exploit instances")
    return p.parse_args()


# ── Server API ────────────────────────────────────────────────────────────────

_API_TIMEOUT = 10  # seconds for HTTP requests to the farm server
_token: str | None = None
_token_lock = threading.Lock()


def _url(host: str, path: str) -> str:
    return urljoin(host.rstrip("/") + "/", path.lstrip("/"))


def _headers() -> dict[str, str]:
    with _token_lock:
        return {"Authorization": f"Bearer {_token}"} if _token else {}


def login(host: str, password: str) -> None:
    global _token
    r = requests.post(
        _url(host, "/api/auth/login"),
        json={"password": password},
        timeout=_API_TIMEOUT,
    )
    r.raise_for_status()
    with _token_lock:
        _token = r.json()["token"]


def fetch_teams(host: str) -> list[dict]:
    """Return all active teams from the server."""
    r = requests.get(_url(host, "/api/teams"), headers=_headers(), timeout=_API_TIMEOUT)
    r.raise_for_status()
    return [t for t in r.json() if t.get("active")]


def fetch_flag_format(host: str) -> str:
    """Return the flag format regex string from the server config."""
    r = requests.get(_url(host, "/api/config"), headers=_headers(), timeout=_API_TIMEOUT)
    r.raise_for_status()
    return r.json().get("competition", {}).get("flag_format", r"[A-Z0-9]{31}=")


def submit_flags(
    host: str,
    items: list[tuple[str, str | None]],
    exploit_name: str,
) -> list[dict]:
    """Submit a batch of (flag, team_ip) pairs.  Returns per-flag result dicts."""
    r = requests.post(
        _url(host, "/api/flags/submit"),
        json={
            "flags": [{"flag": f, "team_ip": ip} for f, ip in items],
            "exploit_name": exploit_name,
        },
        headers=_headers(),
        timeout=_API_TIMEOUT,
    )
    r.raise_for_status()
    return r.json()  # list of {flag, status, response}


# ── Thread-safe flag store ────────────────────────────────────────────────────


class FlagStore:
    """Deduplication store + ordered submission queue, safe for concurrent writes."""

    def __init__(self) -> None:
        self._seen: set[str] = set()
        self._queue: list[tuple[str, str | None]] = []  # (flag, team_ip)
        self._lock = threading.Lock()

    def add(self, flags: list[str], team_ip: str | None = None) -> int:
        """Enqueue unseen flags tagged with their source team IP.  Returns new count."""
        added = 0
        with self._lock:
            for f in flags:
                if f not in self._seen:
                    self._seen.add(f)
                    self._queue.append((f, team_ip))
                    added += 1
        return added

    def pick(self, n: int) -> list[tuple[str, str | None]]:
        with self._lock:
            return list(self._queue[:n])

    def mark_sent(self, n: int) -> None:
        with self._lock:
            self._queue = self._queue[n:]

    @property
    def pending(self) -> int:
        with self._lock:
            return len(self._queue)


_store = FlagStore()
_exit = threading.Event()

# ── Background submission loop ────────────────────────────────────────────────

_POST_PERIOD = 5      # seconds between submission attempts
_POST_BATCH  = 10_000 # max flags per request


def _submit_loop(host: str, exploit_name: str) -> None:
    while not _exit.wait(_POST_PERIOD):
        batch = _store.pick(_POST_BATCH)
        if not batch:
            continue
        try:
            results = submit_flags(host, batch, exploit_name)
            _store.mark_sent(len(batch))

            by_status: dict[str, int] = {}
            for r in results:
                by_status[r["status"]] = by_status.get(r["status"], 0) + 1

            summary = "  ".join(
                col(f"{v} {k}", GREEN if k == "accepted" else RED if k in ("rejected", "error") else YELLOW)
                for k, v in by_status.items()
            )
            log.info("Submitted %d flag(s): %s  (%d in queue)", len(batch), summary, _store.pending)
        except Exception as exc:
            log.warning("Submission failed, will retry: %s", exc)


# ── Exploit runner ────────────────────────────────────────────────────────────

_print_lock = threading.Lock()

# Interpreter selection by extension; unknown extensions try the shebang.
_INTERP: dict[str, list[str]] = {
    ".py": [sys.executable],
    ".sh": ["bash"],
}


def _build_command(exploit: str, team_ip: str) -> list[str]:
    ext = os.path.splitext(exploit)[1].lower()
    return _INTERP.get(ext, []) + [exploit, team_ip]


def _run_exploit(
    exploit: str,
    team_ip: str,
    timeout: int,
    flag_re: re.Pattern,
) -> None:
    color = _team_color(team_ip)
    tag = col(f"[{team_ip}]", color, BOLD)

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"  # force line-buffered output for Python exploits
    env["TARGET_IP"] = team_ip

    cmd = _build_command(exploit, team_ip)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # merge stderr so we capture everything
            env=env,
        )
    except FileNotFoundError as exc:
        log.error("%s  cannot start exploit: %s", tag, exc)
        return
    except Exception as exc:
        log.error("%s  failed to launch: %s", tag, exc)
        return

    timed_out = False
    try:
        out_bytes, _ = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        proc.kill()
        out_bytes, _ = proc.communicate()

    output = out_bytes.decode(errors="replace")
    found: list[str] = flag_re.findall(output)
    new_count = _store.add(found, team_ip)

    # Always print a line per team so the user knows the round is progressing.
    if new_count:
        flag_text = col(f"+{new_count} flag(s)", GREEN)
    elif found:
        flag_text = col(f"{len(found)} dup(s)", YELLOW)
    else:
        flag_text = col("no flags", DIM)

    timeout_tag = col(" [timeout]", YELLOW) if timed_out else ""

    with _print_lock:
        print(f"  {tag}  {flag_text}{timeout_tag}")
        if new_count:
            for f in found[:3]:
                print(f"    {col(f, CYAN)}")
            if new_count > 3:
                print(f"    {col(f'… and {new_count - 3} more', CYAN)}")


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    args = parse_args()
    exploit = os.path.abspath(args.exploit)

    if not os.path.isfile(exploit):
        log.critical("Exploit not found: %s", exploit)
        sys.exit(1)

    exploit_name = os.path.basename(exploit)

    # Print banner + config summary.
    if _TTY:
        print(col(BANNER.strip("\n"), CYAN))
    else:
        print(BANNER.strip("\n"))
    print(f"\n  host     {col(args.host, BOLD)}")
    print(f"  exploit  {col(exploit_name, BOLD)}")
    print(f"  period   {args.period}s   timeout {args.timeout}s   threads {args.threads}\n")

    # Authenticate once.
    try:
        login(args.host, args.password)
        log.info("Authenticated with %s", col(args.host, CYAN))
    except Exception as exc:
        log.critical("Authentication failed: %s", exc)
        sys.exit(1)

    # Kick off the background submission thread.
    threading.Thread(target=_submit_loop, args=(args.host, exploit_name), daemon=True).start()

    pool = ThreadPoolExecutor(max_workers=args.threads)
    flag_re: re.Pattern | None = None
    attack_no = 0

    try:
        while not _exit.is_set():
            attack_no += 1
            round_start = time.monotonic()

            # Fetch teams — re-fetched every round to pick up UI changes.
            try:
                teams = fetch_teams(args.host)
            except Exception as exc:
                log.error("Failed to fetch teams: %s", exc)
                _exit.wait(args.period)
                continue

            # Fetch flag format — re-fetched every round for the same reason.
            try:
                flag_format = fetch_flag_format(args.host)
                flag_re = re.compile(flag_format)
            except Exception as exc:
                log.error("Failed to fetch flag format: %s", exc)
                if flag_re is None:
                    log.critical("No flag format available; cannot continue")
                    sys.exit(1)
                log.info("Using previous flag format")

            if not teams:
                log.warning("No active teams — waiting for the next cycle")
            else:
                print(
                    f"\n{col(f'── Round #{attack_no}', BOLD)}  "
                    f"{col(str(len(teams)) + ' team(s)', YELLOW)}  "
                    f"[{time.strftime('%H:%M:%S')}]"
                )
                for team in teams:
                    pool.submit(_run_exploit, exploit, team["ip"], args.timeout, flag_re)

            # Sleep for the remainder of the period before starting the next round.
            elapsed = time.monotonic() - round_start
            wait = max(0.0, args.period - elapsed)
            if wait > 0.5:
                log.info("Next round in %.0fs  (%d flag(s) pending submission)", wait, _store.pending)
            _exit.wait(wait)

    except KeyboardInterrupt:
        pass
    finally:
        print(f"\n{col('Shutting down…', YELLOW)}")
        _exit.set()
        pool.shutdown(wait=False)

        # One final synchronous submission of anything still queued.
        remaining = _store.pick(_POST_BATCH)
        if remaining:
            log.info("Flushing %d remaining flag(s)…", len(remaining))
            try:
                results = submit_flags(args.host, remaining, exploit_name)
                _store.mark_sent(len(remaining))
                accepted = sum(1 for r in results if r.get("status") == "accepted")
                log.info("Flushed — %d accepted", accepted)
            except Exception as exc:
                log.warning("Final flush failed: %s", exc)
                log.info("Unsubmitted flags (%d):", len(remaining))
                for f, _ in remaining:
                    print(f"  {f}")


if __name__ == "__main__":
    main()
