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

- Python 3.12+, [Poetry](https://python-poetry.org/).
- **Linux x86_64** — `neonize` currently only ships a manylinux wheel. If
  you're on macOS/Windows, run the one-time pairing step below inside Docker
  or a Linux VM/WSL. The GitHub Actions runners are Linux, so the scheduled
  job itself is unaffected.
- A WhatsApp account, already a member of the target group.

## One-time setup

1. Install dependencies:

   ```bash
   poetry install
   ```

2. Pair the bot with your WhatsApp account:

   ```bash
   poetry run python scripts/pair.py
   ```

   Scan the printed QR code with WhatsApp on your phone (**Settings → Linked
   Devices → Link a Device**). Once it prints "Paired successfully", press
   `Ctrl+C`. This creates `data/session.db` — **never commit this file**,
   it's equivalent to being logged into your WhatsApp account.

3. Find the group's JID:

   ```bash
   poetry run python scripts/list_groups.py
   ```

   Copy the `<id>@g.us` value for your target group.

4. Package the session for GitHub Actions:

   ```bash
   base64 -w0 data/session.db > session.b64
   ```

5. In the GitHub repo → **Settings → Secrets and variables → Actions**, add:
   - `WHATSAPP_SESSION_DB_B64` — contents of `session.b64`
   - `WHATSAPP_GROUP_JID` — the JID from step 3

   Delete `session.b64` locally afterwards (`rm session.b64`) — it's the
   same sensitive material as `data/session.db`.

6. Push this repo (private!) to GitHub and confirm the **Daily Rømø report**
   workflow is enabled under the Actions tab. Trigger it once by hand
   (`workflow_dispatch`) to confirm it sends correctly before waiting for
   the schedule.

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
(this can happen after long inactivity). Repeat steps 2–5 above to re-pair
and refresh the secret.

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
