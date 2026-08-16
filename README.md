# romo-bot

Sends a daily WhatsApp message with tide times and weather for Rømø, Denmark
to a group chat. Runs once a day as a scheduled GitHub Actions job — there is
no server to host, and no MCP server involved.

## How it works

```
GitHub Actions (cron, once/day)
        │
        ▼
romo_bot.__main__:main
        │
        ├── OpenMeteoTideClient    ──► marine-api.open-meteo.com  (tide extremes)
        ├── OpenMeteoWeatherClient ──► api.open-meteo.com          (weather)
        ├── ReportFormatter        ──  formats the message text
        └── NeonizeMessageSender   ──► WhatsApp (via a paired session)
```

Every dependency above is a narrow `Protocol` (`TideDataSource`,
`WeatherDataSource`, `MessageSender` in `src/romo_bot/clients/protocols.py`).
`DailyReportService` only knows about those protocols, not the concrete
clients — so the WhatsApp/Open-Meteo specifics are swappable and the
orchestration logic is tested with fakes, no network or WhatsApp session
required (see `tests/`).

Tide/weather fetching and message sending are unofficial/best-effort:
Open-Meteo's marine model is ~8km resolution and can't fully resolve the
Wadden Sea's tidal flats around Rømø — treat the tide times as an estimate,
not a substitute for an official tide table when it actually matters (e.g.
mudflat walking safety). WhatsApp sending uses [neonize](https://github.com/krypton-byte/neonize),
an unofficial client library — WhatsApp's terms don't sanction unofficial
clients, so there's a small standing risk of the linked number getting
flagged, even for one message a day to one group.

## Prerequisites

- Python 3.12+, [Poetry](https://python-poetry.org/) — or just a browser, see
  below.
- **Linux x86_64** — `neonize` currently only ships a manylinux wheel. If
  you're on macOS/Windows, run the one-time pairing step below inside Docker,
  a Linux VM/WSL, or Codespaces (see below). The GitHub Actions runners are
  Linux, so the scheduled job itself is unaffected.
- A WhatsApp account, already a member of the target group.

## One-time setup — from just a phone (no computer needed)

Pairing needs a real, unrestricted connection to WhatsApp's servers to run
the script below once — something this repo's automation can't do on your
behalf. The easiest way to get that from only a phone is **GitHub
Codespaces**: a full Linux terminal that runs in your phone's browser, free
for personal use (no install).

WhatsApp's normal QR pairing needs *two* screens (one to show the code, one
to scan it with the camera) — impossible with one phone. Use
`scripts/pair_by_phone.py` instead: it gets you a short code to **type**
into WhatsApp, which works on a single device.

1. On your phone, open **github.com/JannisBaur/romo-bot** → tap **Code** →
   **Codespaces** tab → **Create codespace on main**. Give it a minute to
   start; you'll land in a browser-based VS Code with a terminal panel.

2. In that terminal, run:

   ```bash
   pip install poetry && poetry install
   ```

3. Pair by phone number (replace with your own number, country code + digits
   only, no `+`/spaces/dashes — e.g. `4512345678` for Denmark). If your
   country uses a trunk prefix (e.g. Germany: `0176 12345678`), drop the
   leading `0` once the country code is prepended → `491761234567`, not
   `490176...`:

   ```bash
   WHATSAPP_PHONE_NUMBER=4512345678 poetry run python scripts/pair_by_phone.py
   ```

   It prints an 8-character code. On your phone: **WhatsApp → Settings →
   Linked Devices → Link a Device → "Link with phone number instead"** →
   enter the code. Once the terminal prints "Paired successfully", press
   `Ctrl+C`. This creates `data/session.db` — **never commit this file**,
   it's equivalent to being logged into your WhatsApp account.

   If it exits with "Could not request a pairing code", just re-run the
   command — this happens if the code was requested before the connection to
   WhatsApp had fully settled, and a retry almost always works.

4. Find the group's JID:

   ```bash
   poetry run python scripts/list_groups.py
   ```

   Copy the `<id>@g.us` value for your target group.

5. Package the session:

   ```bash
   base64 -w0 data/session.db > session.b64
   cat session.b64
   ```

   Copy the printed text (long single line).

6. Still on your phone, go to the repo's **Settings → Secrets and variables →
   Actions** in the browser (works fine on mobile) and add:
   - `WHATSAPP_SESSION_DB_B64` — the text you copied in step 5
   - `WHATSAPP_GROUP_JID` — the JID from step 4

   Back in the Codespace terminal, run `rm session.b64` — it's the same
   sensitive material as `data/session.db`. You can also delete the
   Codespace afterwards (Codespaces list → `...` → Delete) since its only
   job was this one-time pairing step.

7. In the repo's **Actions** tab, open **Daily Rømø report** → **Run
   workflow** to trigger it by hand and confirm the message actually arrives
   before relying on the daily schedule.

### One-time setup — from a computer

If you do have a regular computer (with a phone nearby to scan a QR code),
the flow is the same as above except step 3 uses the QR script instead:

```bash
poetry install
poetry run python scripts/pair.py   # scan the printed QR with WhatsApp
```

Everything else (steps 4–7 above) is identical.

### Adjusting the schedule or location

- Cron schedule: edit `.github/workflows/daily-report.yml` (`cron: "0 5 * * *"`
  is UTC; [crontab.guru](https://crontab.guru) helps with conversions).
- Coordinates: `romo_bot.config` defaults to central Rømø
  (`LATITUDE=55.13`, `LONGITUDE=8.45`, offset slightly into open water so
  the marine model has data to work with). Override via `LATITUDE` /
  `LONGITUDE` environment variables if needed.

### Re-pairing

If the scheduled job starts failing with "No paired WhatsApp session found"
or a connection error, the linked device was likely invalidated by WhatsApp
(this can happen after long inactivity). Repeat the one-time setup above
(either variant) to re-pair and refresh the `WHATSAPP_SESSION_DB_B64` secret.

## Development

```bash
poetry install
poetry run ruff check .        # lint + security (ruff's bandit-equivalent rules)
poetry run ruff format --check .
poetry run mypy                # strict type checking
poetry run pytest --cov=romo_bot
```

All four run in CI (`.github/workflows/ci.yml`) on every push/PR to `main`.

### Design notes

- **SOLID**: `DailyReportService` depends only on the `TideDataSource` /
  `WeatherDataSource` / `MessageSender` protocols (dependency inversion), so
  adding a new data source or sender means writing a new class, not editing
  the service (open/closed).
- **Pure core**: `romo_bot.tide.find_tide_extremes` is a deterministic pure
  function (no I/O, no wall-clock) — cheap to test exhaustively.
- **Isolated boundary**: all `neonize` calls live in
  `romo_bot/clients/whatsapp.py`. `neonize` ships no type stubs, so it's the
  one module where mypy treats the library as `Any` — everything else is
  fully typed.
- **Composition root**: `romo_bot/__main__.py` is the only place concrete
  clients get wired together; nothing else imports them directly.
