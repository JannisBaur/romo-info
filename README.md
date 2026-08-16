# romo-bot

Sends a daily WhatsApp message with tide times, weather, and an amber-hunting
outlook for Rømø, Denmark to a group chat. Runs once a day as a scheduled
GitHub Actions job — there is no server to host, and no MCP/LLM agent
involved.

## How it works

```
GitHub Actions (cron, once/day)
        │
        ▼
romo_bot.__main__:main
        │
        ├── DmiTideTableClient     ──  bundled DMI Havneby tide table (no network)
        ├── OpenMeteoWeatherClient ──► api.open-meteo.com               (weather)
        ├── AmberAdvisor           ──  rule-based amber-hunting outlook
        ├── ReportFormatter        ──  formats the message text
        └── NeonizeMessageSender   ──► WhatsApp (via a paired session)
```

Every dependency above is a narrow `Protocol` (`TideDataSource`,
`WeatherDataSource`, `MessageSender` in `src/romo_bot/clients/protocols.py`).
`DailyReportService` only knows about those protocols, not the concrete
clients — so they're swappable and the orchestration logic is tested with
fakes, no network or WhatsApp session required (see `tests/`).

**Tide data** comes from a DMI (Danish Meteorological Institute) harmonic
tide table for the Havneby station, bundled directly in the repo
(`src/romo_bot/data/havneby_tides_2026.txt`) rather than fetched live. This
is deliberate: DMI's live ocean-model API turned out to be unreliable from
shared cloud IPs (Codespaces/GitHub Actions), and a generic global marine
model (tried first, since removed) was off by up to ~2 hours for this
stretch of Wadden Sea coastline. The bundled table is the real
station-calibrated prediction, matches official sources closely, and has
zero runtime network dependency for tides — but it **only covers one
calendar year**; see "Refreshing the tide table" below.

**Amber-hunting outlook** is a small deterministic rule (`romo_bot/amber.py`):
strong wind onshore (SW through W to NW, since Rømø's beach faces west)
washes amber ashore, and it's easiest to spot on the beach exposed around
low tide. No AI/LLM call involved — this is well-known amber-hunter
knowledge expressed as a plain, tested, free rule, not a judgment call that
needs an API key.

WhatsApp sending uses [neonize](https://github.com/krypton-byte/neonize), an
unofficial client library — WhatsApp's terms don't sanction unofficial
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

5. Encrypt the session file and commit the ciphertext. **The session file
   itself is too large for a GitHub secret** (secrets cap out well under
   1MB; `session.db` is a couple of MB) — so instead, encrypt it with a
   random passphrase, commit the *encrypted* file (safe to store in the
   private repo), and keep only the short passphrase as a secret:

   ```bash
   PASSPHRASE=$(openssl rand -base64 32)
   openssl enc -aes-256-cbc -pbkdf2 -salt \
     -in data/session.db -out data/session.db.enc \
     -pass env:PASSPHRASE
   echo "$PASSPHRASE"
   ```

   Copy the printed passphrase (short — one line, easy to copy reliably).

6. Set two secrets from the Codespace terminal using the GitHub CLI (already
   logged in there):

   ```bash
   gh secret set WHATSAPP_SESSION_PASSPHRASE -b"$PASSPHRASE"
   gh secret set WHATSAPP_GROUP_JID -b"<paste the JID from step 4>"
   ```

   Then commit and push the encrypted file (this is ciphertext — safe to
   store in the repo, unreadable without the passphrase secret):

   ```bash
   git add data/session.db.enc
   git commit -m "Add encrypted WhatsApp session"
   git push
   rm data/session.db
   ```

   You can delete the Codespace afterwards (Codespaces list → `...` →
   Delete) since its only job was this one-time pairing step.

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
- Weather coordinates: `romo_bot.config` defaults to central Rømø
  (`LATITUDE=55.13`, `LONGITUDE=8.45`). Override via `LATITUDE` /
  `LONGITUDE` environment variables if needed. This only affects the
  *weather* forecast — tide data comes from the fixed Havneby station table
  (see below), not these coordinates.

### Refreshing the tide table

The bundled tide table (`src/romo_bot/data/havneby_tides_2026.txt`) only
covers 2026. Once that runs out (or a bit before, so there's no gap), fetch
next year's table the same way this one was created and swap it in:

```bash
curl -s "https://ocean.dmi.dk/tides/MLWS/2027/Havneby.t.txt" -o src/romo_bot/data/havneby_tides_2027.txt
```

then update the filename in `romo_bot/clients/dmi_tide.py`
(`DmiTideTableClient`'s default `table_filename`) and in `__main__.py` if
overridden there, commit, and push. This is a once-a-year, few-minutes task
— no code logic changes needed, just swapping which static file is read.

### Re-pairing

If the scheduled job starts failing with "No paired WhatsApp session found"
or a connection error, the linked device was likely invalidated by WhatsApp
(this can happen after long inactivity). Repeat the one-time setup above
(either variant) to re-pair, then re-run step 5–6 to replace
`data/session.db.enc` and the `WHATSAPP_SESSION_PASSPHRASE` secret.

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
- **Pure core**: `romo_bot.tide.find_tide_extremes`, `romo_bot.clients.dmi_tide.parse_table`
  /`extremes_for_date`, and `romo_bot.amber.AmberAdvisor` are all deterministic
  (no I/O, no wall-clock passed in explicitly where it matters) — cheap to
  test exhaustively with fixed inputs, no network or mocking required.
- **Isolated boundary**: all `neonize` calls live in
  `romo_bot/clients/whatsapp.py`. `neonize` ships no type stubs, so it's the
  one module where mypy treats the library as `Any` — everything else is
  fully typed.
- **Composition root**: `romo_bot/__main__.py` is the only place concrete
  clients get wired together; nothing else imports them directly.
