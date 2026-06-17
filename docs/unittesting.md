# Unit testing

The test suite uses the **Python standard-library `unittest`** — no `pytest`, no
external dependencies, and **no network access**. Everything (HTTP, the worker
pool's clock/sleep, randomness) is injected with fakes, so the suite is fast and
deterministic (122 tests in well under a second).

## Running the tests

```bash
make tests                       # run the whole suite (alias for test-unit)
make test-unit                   # same thing, verbose
make test-one T=test_worker_pool # run a single module
make test-one T=test_worker_pool.WallHandlingTests          # one class
make test-one T=test_pacing.RateControllerPacingTests.test_jitter_varies_the_gap  # one test
```

Without the Makefile:

```bash
python3 -m unittest discover -s tests -p "test_*.py" -v   # all
python3 -m unittest -v tests.test_concurrency             # one module
```

`make all` runs the full quality pipeline (`clean → autofix → format → lint →
test-unit → test-full`). The CI runs the same `unittest` suite on every push.

## What each test module covers

### Download pacing & the WAF-wall handling
These cover the adaptive parallel downloader (see
[configuration.md](configuration.md#download-performance) → `dlworkers` /
`dlthreshold`).

| Module | Tests | Covers |
|---|--:|---|
| `test_pacing.py` | 12 | `RateController`: AIMD rate, per-request **jitter**, the **escalating delay** on a sustained wall (climbs ~`0.8*1.5^failures` → ~15s, resets on success), convergence simulation, and the `DownloadResult`/`TaskMetrics` data types. |
| `test_concurrency.py` | 5 | `ConcurrencyLimiter` — the **"wave"**: collapse toward 1 worker on a 429, ramp back on a success streak, bounds in-flight, no deadlock. |
| `test_worker_pool.py` | 16 | `PacedWorkerPool`: every task finalised (no deadlock), keep-alive session reuse, progress, retry of genuine errors, **ride-the-wall** (re-queue 429s, give up only after a long run → `WallHandlingTests`), adaptive-concurrency collapse/recover, save-as-you-go `on_result`. |
| `test_http.py` | 5 | `execute()` HTTP adapter against a **fake session**: GET vs POST, 429/503/WAF-marker → `rate_limited`, never raises. |
| `test_download_config.py` | 5 | `get_download_workers()` / `get_download_threshold()` resolution (`auto`, integer overrides, fallbacks). |

### Configuration
| Module | Tests | Covers |
|---|--:|---|
| `test_migration.py` | 4 | Schema migration: a **version-5** config upgrades to the current version and gets the `<imagesources>` block injected (uses `fixtures/config_v5.xml`). |
| `test_image_source.py` | 10 | The configurable `<imagesources>` block (first `enabled` host wins, parsing, fallbacks). |
| `test_config_backup_retention.py` | 8 | `reconf` config-backup retention: keep the N most recent **distinct** backups, skip an identical one, `unlimited`/count resolution. |
| `test_args_validation.py` | 10 | `ArgumentValidator` — CLI argument validation (days range, zip/postal, mutually exclusive flags…). |

### Cache
| Module | Tests | Covers |
|---|--:|---|
| `test_cache_migration.py` | 7 | The `guide/` + `series/` (`SH*`) + `movies/` (`MV*`) cache layout, and automatic migration of older flat / `series/`-only caches. |

### Parsing & XMLTV output
| Module | Tests | Covers |
|---|--:|---|
| `test_series_parser.py` | 8 | `SeriesParser`: crew capture, TV-series credits, per-episode synopsis, display rating, images. |
| `test_series_application.py` | 3 | Regression: extended details must enrich **every airing** of a series, not just the first. |
| `test_xmltv_golden.py` | 1 | **Golden-file** regression — see below. |

### Utilities
| Module | Tests | Covers |
|---|--:|---|
| `test_helpers.py` | 11 | Pure helpers in `gracenote2epg.utils` (time/format helpers). |
| `test_geocoding.py` | 7 | The bundled stdlib postal-code geocoder (no `pgeocode`). |
| `test_logrotate_periods.py` | 10 | The pure period math extracted into `logrotate.periods`. |

## The golden file (XMLTV output regression)

`test_xmltv_golden.py` feeds a small, fixed parsed schedule (a movie + a TV show)
through `XmltvGenerator` and compares the output byte-for-byte to a committed
golden file, `tests/fixtures/xmltv_golden.xml`. The timezone is pinned to UTC so
the result is stable across machines.

If you **intentionally** change the generated XMLTV format (a new element, an
attribute, ordering…), the test will fail until you regenerate the golden:

```bash
make golden-update        # = python3 -m tests.test_xmltv_golden --update-golden
git diff tests/fixtures/xmltv_golden.xml   # review, then commit
```

Only regenerate after an *intended* change — an unexpected diff means a
regression. Most changes (download pacing, logging, retention…) don't touch the
XMLTV output and leave the golden untouched.

## Fixtures

- `tests/fixtures/config_v5.xml` — a version-5 config, input for the migration test.
- `tests/fixtures/xmltv_golden.xml` — the expected XMLTV output (above).

> Note: `tests/baseline/` (if present locally) is **not** part of the suite — it
> is untracked scratch data and is not referenced by any test.

## Conventions for new tests

- One `test_<area>.py` module per area; subclass `unittest.TestCase`.
- No network and no real sleeping: inject fakes (see `instant_governor` in
  `test_worker_pool.py`, the `FakeTime` clock in `test_pacing.py`, and the fake
  session in `test_http.py`).
- Don't load `tests/baseline/` or any real config in-place — copy to a temp dir
  first (a `ConfigManager.load_config()` would migrate/rewrite the file).
