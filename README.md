# FarmRaid

```
  _____                    ____        _     _
 |  ___|_ _ _ __ _ __ ___ |  _ \ __ _(_) __| |
 | |_ / _` | '__| '_ ` _ \| |_) / _` | |/ _` |
 |  _| (_| | |  | | | | | |  _ < (_| | | (_| |
 |_|  \__,_|_|  |_| |_| |_|_| \_\__,_|_|\__,_|
```

> A modern, UI-driven exploit farm for Attack & Defense CTF competitions.

Inspired by [DestructiveFarm](https://github.com/DestructiveVoice/DestructiveFarm) and [S4DFarm](https://github.com/C4T-BuT-S4D/S4DFarm), built from scratch with a **fully UI-driven configuration** — no code changes needed between competitions.

---

## Features

- **Zero-code setup** — configure teams, flag format, submission protocol, and rate limits entirely from the web UI; no config files to edit
- **Upload exploits from the browser** — Python and Bash scripts, drag & drop with per-exploit period and timeout
- **Auto dependency install** — place a `requirements.txt` next to your uploaded exploit and the server runs `pip install` automatically before execution
- **Real-time dashboard** — live flag feed over WebSockets, per-exploit and per-team stats, timeline chart
- **7 submission protocols** — ForcAD TCP/HTTP, RuCTFE HTTP, FAUST, VolgaCTF, Custom HTTP, Custom TCP
- **Client runner** — `client/start_sploit.py` for running exploits from your own machine and submitting flags back to the farm
- **Docker Compose deploy** — `docker compose up` and it works

---

## Quick Start

**Requirements:** Docker ≥ 24, Docker Compose V2 (`docker compose`, not `docker-compose`).

```bash
git clone https://github.com/yourorg/farmraid
cd farmraid
cp .env.example .env   # edit passwords before a real competition
docker compose up -d
```

Open **http://localhost** in your browser.

### First-run setup

A setup wizard appears on first launch. Work through the tabs in **Settings** in order:

1. **Competition** — set the competition name, flag format regex (e.g. `[A-Z0-9]{31}=`), and flag lifetime
2. **Submission** — pick a protocol (see [Protocols](#protocols)) and fill in its parameters
3. **Server** — change the default password (`changeme`)

Then:

4. Go to **Teams** — add teams manually or paste a bulk list of IPs
5. Go to **Exploits** — drag & drop your script, set period and timeout, enable it
6. Watch flags roll in on the **Dashboard**

---

## Exploit Contract

The contract is identical whether you upload scripts to the server UI or run them locally with `client/start_sploit.py`.

### Invocation

```
python3 exploit.py <team_ip>
bash exploit.sh <team_ip>
```

The target team's IP is always passed as the **first positional argument**.

### Environment variables

| Variable | Available | Value |
|---|---|---|
| `TARGET_IP` | Server runner only | Same as `argv[1]` — convenience alias |
| `FARM_HOST` | Server runner only | URL of the FarmRaid server (e.g. `http://localhost:8000`) |
| `PYTHONUNBUFFERED` | Client runner only | `1` — forces line-buffered stdout |

### Flag output

Print flags **anywhere in stdout** — one per line, embedded in debug output, repeated — it does not matter. Flags are extracted with:

```python
re.findall(FLAG_FORMAT, stdout)
```

where `FLAG_FORMAT` is the regex configured in Settings. No special output structure is required.

**Tip for Python exploits:** use `print(flag, flush=True)` so output is not lost if the process is killed at timeout.

### Exit codes and stderr

- Exit codes are **ignored** by both runners.
- **Server runner** — stderr is captured separately and displayed in the exploit run log panel in the UI.
- **Client runner** — stderr is merged into stdout, so it is also scanned for flags.

### Timeout

Scripts are killed (`SIGKILL`) after the configured timeout. Any output produced before the kill is still scanned for flags.

### Auto dependency install (server-side only)

Place a `requirements.txt` next to your uploaded exploit. The server checks two locations in priority order:

1. `<exploit_name>_requirements.txt` — per-exploit, avoids conflicts between scripts
2. `requirements.txt` in the uploads directory — shared fallback

If found, the server runs:

```
pip install -r requirements.txt --break-system-packages
```

before execution (120-second timeout). The following libraries are pre-installed in the server image and never need to be listed:

```
requests  pwntools  pycryptodome  paramiko
```

The **client runner does not auto-install dependencies.** Install them manually before running `start_sploit.py`.

### Quick templates

**Python:**

```python
#!/usr/bin/env python3
import sys

TARGET = sys.argv[1]

def exploit(ip):
    return []  # return a list of flag strings

if __name__ == "__main__":
    for flag in exploit(TARGET):
        print(flag, flush=True)
```

**Bash:**

```bash
#!/bin/bash
TARGET=$1
# echo flags to stdout
```

Full annotated templates with common patterns are in [`examples/`](examples/).

---

## Protocols

Configure the submission protocol in **Settings → Submission**. All `team_token` fields are optional — leave them blank when the competition authenticates by source IP.

### `forcad_tcp` — ForcAD / RuCTFE (TCP)

Used by ForcAD, RuCTFE, ctfcup. Connects via TCP, optionally sends a team token, then submits flags one per line and reads one verdict per flag.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `host` | string | — | Submission server host |
| `port` | integer | `31337` | Submission server port |
| `team_token` | string | — | Team token (optional) |

### `forcad_http` — ForcAD (HTTP)

ForcAD HTTP checker. Single `PUT` request with a JSON array of flags; parses per-flag verdicts from the response.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | string | — | Submission URL (e.g. `http://10.10.10.10:8080/flags`) |
| `team_token` | string | — | Sent as `Authorization: Bearer <token>` (optional) |

### `ructfe_http` — RuCTFE (HTTP)

RuCTFE HTTP variant. `PUT` request with token sent as `X-Team-Token` header.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | string | — | Submission URL (e.g. `http://monitor.ructfe.org/flags`) |
| `team_token` | string | — | Sent as `X-Team-Token` (optional) |

### `faust` — FAUST CTF (TCP)

Used by FAUST CTF. Connects via TCP, sends all flags newline-separated, reads per-flag `OK`/`DUP`/`ERR` responses.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `host` | string | — | Submission server host |
| `port` | integer | `31337` | Submission server port |

### `volgactf` — VolgaCTF

HTTP `POST` per flag to the VolgaCTF API. Authenticated by the attacking team's source IP — no token needed.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `host` | string | — | Monitor host (e.g. `monitor.volgactf.ru`) |
| `version` | string | `v1` | API version |

### `custom_http` — Custom HTTP

Fully configurable HTTP submission. All flags are sent in one request.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | string | — | Submission URL |
| `method` | string | `POST` | `POST`, `PUT`, or `GET` |
| `body_template` | textarea | — | Request body; `{flags}` is replaced with a JSON array of flags |
| `headers` | textarea | — | Extra headers as a JSON object, e.g. `{"X-Token": "abc"}` |
| `accept_regex` | string | — | Regex matched against the response to mark flags accepted |
| `reject_regex` | string | — | Regex matched against the response to mark flags rejected |

### `custom_tcp` — Custom TCP

Generic TCP submission for non-standard protocols. Sends flags one per line, reads one response per flag.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `host` | string | — | Submission server host |
| `port` | integer | `31337` | Submission server port |
| `team_token` | string | — | Sent on connect or after the handshake line (optional) |
| `token_line` | string | — | Wait for this substring before sending the token (optional) |
| `flag_regex` | string | — | Regex to classify each per-flag response line; blank = built-in verdict parsing |
| `timeout` | integer | `10` | Connection timeout in seconds |

---

## Client Runner

`client/start_sploit.py` runs exploits from **your own machine** against all active teams registered in the farm. Flags are submitted back to the server, which queues and forwards them via the configured protocol.

```bash
# Install the one required dependency
pip install requests

# Basic usage
python3 client/start_sploit.py \
    --host http://FARM_IP \
    --password changeme \
    ./exploit.py

# Custom timing and concurrency
python3 client/start_sploit.py \
    --host http://FARM_IP \
    --password changeme \
    --period 60 \
    --timeout 20 \
    --threads 20 \
    ./exploit.py
```

### Options

| Flag | Default | Description |
|---|---|---|
| `exploit` | required | Path to exploit script |
| `--host` | required | FarmRaid server URL |
| `--password` | required | FarmRaid server password |
| `--period` | `120` | Seconds between attack rounds |
| `--timeout` | `30` | Max seconds per exploit run |
| `--threads` | `10` | Max concurrent exploit instances |

### Behaviour

- Authenticates once with a JWT token at startup.
- Re-fetches the team list and flag format from the server at the start of every round (picks up UI changes without restarting).
- Runs the exploit concurrently against all active teams, limited to `--threads` simultaneous subprocesses.
- Extracts flags from stdout with `re.findall(FLAG_FORMAT, output)`.
- Deduplicates flags globally across the entire session.
- Submits found flags to the server every 5 seconds in batches of up to 10 000.
- On Ctrl+C: flushes any remaining queued flags synchronously before exiting; prints them to stdout if the final submission fails so no flags are silently lost.

### Interpreter selection

| File extension | Interpreter |
|---|---|
| `.py` | Same Python running `start_sploit.py` |
| `.sh` | `bash` |
| Other | Direct execution (requires a shebang) |

### Dependencies

The client runner does **not** auto-install exploit dependencies. Install everything before running:

```bash
# Common CTF libraries (same set pre-installed server-side)
pip install -r examples/requirements.txt

# Or individually
pip install requests pwntools pycryptodome paramiko
```

---

## Configuration (.env)

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PASSWORD` | `farmpass` | PostgreSQL password |
| `REDIS_PASSWORD` | `redispass` | Redis password |
| `SECRET_KEY` | `change-this-secret-key-in-production` | JWT signing secret — **always change this** |

---

## Screenshots

*Coming soon.*

---

## Security notes

- Uploaded exploit scripts run directly inside the server container. Treat them as **trusted code** — only upload your own exploits.
- Default password is `changeme`. Change it in **Settings → Server** before the competition.
- No HTTPS by default — designed for isolated CTF LAN environments. Put nginx or Caddy in front for remote access.
- Do not expose the farm to the public internet.

---

## License

MIT
