# romo-info

Publishes a daily web page with tide times, wind and tonight's stargazing
conditions for Rømø, Denmark, plus where to look for amber once you're there. Runs twice a
day as a scheduled GitHub Actions job and deploys to GitHub Pages — there is no server to host, no
credentials to store, and no MCP/LLM agent involved.

## How it works

```
GitHub Actions (cron, twice/day)
        │
        ▼
romo_info.__main__:main
        │
        ├── DmiTideTableClient     ──  bundled DMI Havneby tide table (no network)
        ├── OpenMeteoWeatherClient ──► api.open-meteo.com                  (wind)
        ├── stargazing             ──  moon phase (computed) + night cloud
        ├── meteors                ──  bundled IMO shower calendar (no network)
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

**Wind** is the only weather reported, and it's deliberate. General
conditions (temperature, cloud, chance of rain) were dropped: every phone
already has a weather app that does them better, and compressing a
six-hour window into one summary kept overstating things — first by
labelling a mostly-clear afternoon after its single drizzliest hour, then
by reporting that window's peak chance of rain as if it applied all
afternoon. Wind stays in full -- speed, bearing, and whether that bearing is
onshore -- because it is amber information: an onshore blow pushes
loosened amber towards the beach where an offshore one of the same
strength does not. Only daily wind is fetched, so no hourly series is
requested beyond the cloud cover the stargazing note needs. Transient network failures are retried
(3 attempts with backoff) so one dropped connection doesn't cost the day's
report.

**Amber odds are deliberately not computed here.** There used to be a
rule-based verdict and a five-day storm outlook; both are gone. Ravvejr
publishes a [five-day amber forecast for
Lakolk](https://ravvejr.dk/lakolk-strand/), and a hand-rolled heuristic
sitting next to it just gives the reader two verdicts with no way to
choose between them — worse than one. The page links to theirs and
keeps only the static advice on where and how to search — the tide list
itself already shows when the water is on its way out.

That advice is sourced rather than folklore: amber reaches this coast
when a storm loosens it from the seabed and calmer weather then washes it
ashore, and it strands in the wrack line among debris of similar density
— the *ravpindelag*. An earlier version of this project asserted the
Baltic "onshore wind blows it ashore" story, which does not apply to
Rømø's North Sea side; the sources are cited on the page itself.

**Stargazing** reports tonight's dark window, the mean cloud cover across
those hours, how much of the moon is lit, and — when it's meaningfully
better than the average — the clearest hour, since a mean alone can't tell
"hazy all night" from "clear until midnight, then closes in". The window
runs from dusk to **02:00** rather than to sunrise: a summer night here
lasts until nearly 04:00 and nobody is standing outside for it, so
including those hours would average in weather no one is going to see. Moon illumination is
*computed* (`romo_info/stargazing.py`) from the mean synodic month rather
than fetched — it's a pure astronomical function, accurate to a percent or
two, which is far finer than "will moonlight drown out the sky tonight?"
needs. The page updates **twice a day** for this: forecasting tonight's
cloud from the morning run means a ~15-hour lead time, where the
late-afternoon run is nearer four and materially more accurate.

**Meteor showers** come from the International Meteor Organization's
[2026 Meteor Shower Calendar](https://www.imo.net/files/meteor-shower/cal2026.pdf),
Table 5, transcribed into `romo_info/meteors.py`. These are astronomical
predictions, not a forecast, so they're a bundled table like the tide
data — and like it, **it needs refreshing each year**: the IMO states its
maximum dates are accurate only for 2026 (activity periods barely move;
peaks shift a day or so).

Not every shower in that table is listed. Left out on purpose: the two
daytime showers, radiants too far south to ever rise at 55°N (the
Puppid-Velids and α-Centaurids never clear the horizon here), anything
below ZHR 10, and showers the IMO marks "Var" — declining to predict a
rate is not an invitation to invent one. The line is omitted entirely
when nothing is running, which is most of the year. Quoted rates say
"under ideal skies" because ZHR assumes the radiant overhead under a
perfect sky; real counts are always lower.

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

- Cron schedule: edit `.github/workflows/daily-report.yml` (two entries, `"0 5 * * *"`
  and `"0 16 * * *"`, both UTC; [crontab.guru](https://crontab.guru) helps with conversions).
  GitHub's cron is fixed UTC with no DST awareness, so the local time
  shifts by an hour when Denmark changes clocks.
- How many days to show: `DAYS_TO_REPORT`. The workflow sets `3`; the
  code default is `1`. Days past tomorrow are labelled by weekday name.
- Weather coordinates: `romo_info.config` defaults to central Rømø
  (`LATITUDE=55.13`, `LONGITUDE=8.45`). This only affects the *wind*
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
  /`extremes_for_date`, `romo_info.weather.had_recent_onshore_storm`
  /`next_onshore_storm`/`strongest_onshore_day`,
  and `romo_info.amber.AmberAdvisor` are all deterministic (no I/O,
  wall-clock passed in explicitly where it matters) — cheap to test
  exhaustively with fixed inputs, no network or mocking required.
- **Composition root**: `romo_info/__main__.py` is the only place concrete
  clients get wired together; nothing else imports them directly.
- **Escaping**: `ReportFormatter` HTML-escapes everything that comes from
  the data sources, so a stray `<` or `&` in an API response can't break
  (or inject into) the page.
