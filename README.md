# romo-info

Publishes a daily web page with tide times, weather, and an amber-hunting
outlook for Rømø, Denmark. Runs once a day as a scheduled GitHub Actions
job and deploys to GitHub Pages — there is no server to host, no
credentials to store, and no MCP/LLM agent involved.

## How it works

```
GitHub Actions (cron, once/day)
        │
        ▼
romo_info.__main__:main
        │
        ├── DmiTideTableClient     ──  bundled DMI Havneby tide table (no network)
        ├── OpenMeteoWeatherClient ──► api.open-meteo.com               (weather)
        ├── AmberAdvisor           ──  rule-based amber-hunting outlook
        ├── ReportFormatter        ──  renders the static HTML page
        └── FileReportPublisher    ──  writes public/index.html
        │
        ▼
actions/deploy-pages ──► GitHub Pages
```

Every dependency above is a narrow `Protocol` (`TideDataSource`,
`WeatherDataSource`, `ReportPublisher` in `src/romo_info/clients/protocols.py`).
`DailyReportService` only knows about those protocols, not the concrete
clients — so they're swappable and the orchestration logic is tested with
fakes, no network required (see `tests/`).

**No secrets, no tokens.** The workflow deploys using the `GITHUB_TOKEN`
that Actions provides automatically, scoped to Pages. Nothing needs to be
configured in repository secrets.

**Tide data** comes from a DMI (Danish Meteorological Institute) harmonic
tide table for the Havneby station, bundled directly in the repo
(`src/romo_info/data/havneby_tides_2026.txt`) rather than fetched live. This
is deliberate: DMI's live ocean-model API turned out to be unreliable from
shared cloud IPs, and a generic global marine model (tried first, since
removed) was off by up to ~2 hours for this stretch of Wadden Sea
coastline. The bundled table is the real station-calibrated prediction,
matches official sources closely, and has zero runtime network dependency
for tides — but it **only covers one calendar year**; see "Refreshing the
tide table" below.

**Weather** is split into Morning / Afternoon / Evening (`romo_info/weather.py`
buckets Open-Meteo's hourly data into those windows) rather than one blended
daily summary, since "sunny morning, rain later" is a lot more actionable
than a single averaged line. Transient network failures are retried (3
attempts with backoff) so one dropped connection doesn't cost the day's
report.

**Amber-hunting outlook** is a small deterministic rule
(`romo_info/amber.py` + `romo_info/weather.had_recent_onshore_storm`), based
on how amber actually reaches Denmark's North Sea coast: a storm (onshore,
classically from the SW) loosens it from the seabed first, then it washes
ashore during the *calmer* weather that follows, easiest to spot on the
beach exposed by the falling tide. So it checks the past 3 days for a
strong onshore blow, not just today's wind — a same-day-only check would
get this backwards. No AI/LLM call involved — this is domain knowledge
expressed as a plain, tested, free rule, not a judgment call that needs an
API key. (Verified against multiple Danish West Coast amber-hunting
sources — this differs from the "onshore wind blows it ashore" folklore
more commonly cited for Baltic Sea amber coasts, which don't apply to
Rømø's North Sea side.) The wind thresholds — >16 m/s (~58 km/h) to stir
amber loose, <10 m/s (~36 km/h) to be calm enough to search — come from
those same sources rather than being guessed. A strong onshore day that
*misses* the storm threshold is still reported as a near miss rather than
being silently discarded.

The page also carries a report-wide storm outlook
(`romo_info.weather.next_onshore_storm`) looking 5 days past the last
reported day, purely to flag an *upcoming* onshore storm worth planning
around — e.g. "storm forecast Wed, worth checking again a day or two
after". Open-Meteo's own forecast skill drops off well before that
horizon, so this is a heads-up, not a promise. It's shown once at the end,
not duplicated per day, since it's the same forward-looking info regardless
of which day's section you're reading.

## Setup

1. Make the repository **public**. On GitHub Free, Pages only publishes
   from public repositories; private-repo Pages needs Pro or higher. (The
   published page is publicly reachable either way — the plan only decides
   whether the *source* may stay private.)
2. In the repo's **Settings → Pages**, set **Source** to **GitHub Actions**.
3. In the **Actions** tab, open **Daily Rømø report** → **Run workflow** to
   trigger it by hand and confirm the page builds and deploys.
4. The published URL appears in the workflow run summary (and under
   Settings → Pages). That's the link to share.

That's the whole setup — no accounts to link, no secrets, no local commands.

### Adjusting the schedule or location

- Cron schedule: edit `.github/workflows/daily-report.yml` (`cron: "0 5 * * *"`
  is UTC; [crontab.guru](https://crontab.guru) helps with conversions).
  GitHub's cron is fixed UTC with no DST awareness, so the local time
  shifts by an hour when Denmark changes clocks.
- How many days to show: `DAYS_TO_REPORT` (default `1` — today only; set
  `2` for today + tomorrow, and so on). Set it in the workflow's `env:` for
  the "Build report page" step.
- Weather coordinates: `romo_info.config` defaults to central Rømø
  (`LATITUDE=55.13`, `LONGITUDE=8.45`). This only affects the *weather*
  forecast — tide data comes from the fixed Havneby station table.
- Output location: `OUTPUT_PATH` (default `public/index.html`). The
  workflow uploads whatever is in `public/`, so change both together.

### Refreshing the tide table

The bundled tide table (`src/romo_info/data/havneby_tides_2026.txt`) only
covers 2026. Once that runs out (or a bit before, so there's no gap), fetch
next year's table the same way this one was created and swap it in:

```bash
curl -s "https://ocean.dmi.dk/tides/MLWS/2027/Havneby.t.txt" -o src/romo_info/data/havneby_tides_2027.txt
```

then update the filename in `romo_info/clients/dmi_tide.py`
(`DmiTideTableClient`'s default `table_filename`), commit, and push. This is
a once-a-year, few-minutes task — no code logic changes needed, just
swapping which static file is read.

## Development

```bash
poetry install
poetry run ruff check .        # lint + security (ruff's bandit-equivalent rules)
poetry run ruff format --check .
poetry run mypy                # strict type checking
poetry run pytest --cov=romo_info
```

All four run in CI (`.github/workflows/ci.yml`) on every push/PR to `main`.

To preview the page locally without deploying:

```bash
poetry run python -m romo_info && open public/index.html
```

### Design notes

- **SOLID**: `DailyReportService` depends only on the `TideDataSource` /
  `WeatherDataSource` / `ReportPublisher` protocols (dependency inversion),
  so adding a new data source or output target means writing a new class,
  not editing the service (open/closed).
- **Pure core**: `romo_info.tide.find_tide_extremes`, `romo_info.clients.dmi_tide.parse_table`
  /`extremes_for_date`, `romo_info.weather.bucket_day_parts`
  /`had_recent_onshore_storm`/`next_onshore_storm`/`strongest_onshore_day`,
  and `romo_info.amber.AmberAdvisor` are all deterministic (no I/O,
  wall-clock passed in explicitly where it matters) — cheap to test
  exhaustively with fixed inputs, no network or mocking required.
- **Composition root**: `romo_info/__main__.py` is the only place concrete
  clients get wired together; nothing else imports them directly.
- **Escaping**: `ReportFormatter` HTML-escapes everything that comes from
  the data sources, so a stray `<` or `&` in an API response can't break
  (or inject into) the page.
