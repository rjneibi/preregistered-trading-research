# Reproducing

There are three levels. Each prints a pass or fail and exits non-zero on failure.

| Level | Command | Needs | Time measured here | Disk |
|---|---|---|---|---|
| `verify` | `python scripts/verify.py` | Python 3.11 and `requirements.txt` | Under a minute | None beyond the clone |
| `public` | `make audit-public` | Public data, about 22 GB, plus bash, git and curl | 89 minutes | 22 GB data plus 6 GB workspace |
| `full` | `make audit` | Public data plus the broker exports | 1 hour 41 minutes | 23 GB data plus 9 GB workspace |

Times are from one Windows 11 PC with a 6-core Ryzen 5 7600X and 32 GB of RAM, with another job running. They exclude downloads. Without `make`, `python scripts/reproduce_all.py verify|public|full` does the same.

## 1. Setup

```
git clone <this repository>
cd preregistered-trading-research
python -m pip install -r requirements.txt
```

Python must be 3.11. If `python` is another version, set `PYTHON311` to a 3.11 interpreter. The `public` and `full` levels build three fresh virtual environments from the pinned files in `audit/infrastructure/`, so they need network access to PyPI. On a network that intercepts TLS, set `PIP_EXTRA=--use-feature=truststore`. On Windows, bash comes with Git for Windows.

## 2. Level `verify`, no data

```
python scripts/verify.py
```

This checks, without any market data:

- every stored output against `audit/results.sha256`, 87 files. A clean run compares 73 of them, and one of those, `phaseC/deferred_checks.json`, cannot be regenerated. The other 14 are spot-check samples and the records of earlier runs, which are hashed but not regenerated
- that every number in the main reports appears in an evidence file, through `audit/stats/traceability.py`. A match shows the number exists in the evidence, not that it describes the right thing, and the experiment READMEs, `NEGATIVE_RESULTS.md`, `GLOSSARY.md` and `LITERATURE.md` are not checked
- the tests in `tests/`
- the forward-test freeze, `audit/forward/FREEZE.sha256`
- internal links, and that no absolute path is committed

## 3. Getting the data

```
python scripts/download_data.py --list
python scripts/download_data.py --dir data/raw
```

`data/raw/` is ignored by git. Files land at their manifest path, and each is compared with the SHA-256 the audit used. The groups, sources and licences are in [data/MANIFEST.md](data/MANIFEST.md). One group or year at a time also works, for example `--group dukascopy_xag --years 2016`.

What a fresh fetch was checked against, and how it came out:

| Group | Checked | Result |
|---|---|---|
| `histdata_xau` | 2020 | Same 354,291 rows |
| `calendar_series` | All 4 files | Same bytes |
| `dukascopy_xag` | 2016, bid and ask | Same bytes, 53 seconds |
| `dukascopy_ticks` | XAG April 2016 | 19 hours had ticks in both copies, and all 19 were identical. The fresh fetch got ticks for only 44 hours, because the downloader writes an empty hour when a request fails or is throttled |
| `binance` | Klines, through the public mirror | Same rows |

That check also showed the audit's own copy of that month, and of XAU September 2018, to be incomplete. See [DECISIONS.md](DECISIONS.md), item 19. A tick month that comes back much smaller than its manifest size has been throttled and should be fetched again.

Other groups and years were not fetched again, so a source revising history would show up only as a reported difference. `public_api` files grow with every fetch, so their hashes will differ. The tick group sends one request per hour of data, about 200,000 in all, and waits out rate limits, so it takes days.

Not fetchable here:

| Group | Why |
|---|---|
| `broker_mt5` | MetaTrader 5 demo exports. They need a terminal and a login, and broker data may not be redistributed |
| `demo_journal` | The demo bot's journal. It holds demo balances, so it is not published |
| `flip_events` | Signal lists left by an earlier run whose writer is not in the snapshot |
| `yahoo_intraday` | Yahoo no longer serves those intraday dates |

## 4. Level `public`

```
make audit-public          # or: DATA_DIR="$PWD/data/raw" bash audit/tools/make_audit.sh ../_audit_clean public
```

The script clones the committed repository into the work folder, fills the path tokens with `audit/tools/render_paths.py`, copies the data in with `audit/tools/assemble_data.py`, builds the environments, runs every stage in `audit/tools/run_all.sh`, and compares each output with the committed file through `audit/tools/check_hashes.py`. It never writes into your clone.

At this level the 19 stages in [audit/tools/stages_broker.txt](audit/tools/stages_broker.txt) still run, because some of them build sandboxes that later stages use, but each reads a file that is not public, so their failure is recorded as `rc=expected-N` and does not fail the level. The 23 outputs that depend on files that are not public are listed with a reason in [audit/tools/outputs_broker.txt](audit/tools/outputs_broker.txt). Five of them come from stages that finish but write ERROR entries for the missing symbols. Results resting on those files, among them the index and ETF studies XM-1 and SW-1, the gate table and E6, can be read and checked against their hashes but not regenerated. Every other output is regenerated and compared.

Its last run, from a clean clone of this tree:

| Item | Value |
|---|---|
| Stages | 70 run: 51 passed, 19 failed as expected, 0 failed otherwise |
| Outputs | 49 same, 5 differ for a listed reason, 0 differ without one |
| Not regenerated | 19, each listed with its reason |
| Input files | 296 public files, all matching their hashes |

The 5 that differ are the ones that write ERROR entries. The run record is not committed for this level, because `CLEAN_RUN.json` holds the full level's record. The same check prints these counts at the end of a run.

## 5. Level `full`

This needs the broker exports at their manifest paths in `DATA_DIR`, so as published only the author can run it. Its last run, from a clean clone of this tree:

| Item | Value |
|---|---|
| Stages | 70 run, 0 failed |
| Outputs | 72 same, 0 differ |
| Not regenerated | 1, `phaseC/deferred_checks.json`, a dated record whose inputs were fetched once into a scratch folder |
| Input files | 532, all matching their hashes |

The record is [audit/tools/CLEAN_RUN.json](audit/tools/CLEAN_RUN.json), and the stage times are in [audit/tools/CLEAN_RUN_stages.txt](audit/tools/CLEAN_RUN_stages.txt).

## Checking output hashes by hand

`audit/results.sha256` holds one line per output: the SHA-256 of the file with line endings normalised to LF, then its path under `audit/`. Outputs that record a folder hold tokens such as `@GANN_ROOT@` in place of it, and `check_hashes.py` puts the tokens back before hashing, so the hashes do not depend on where you cloned. A single file can be checked like this:

```
python -c "import hashlib,sys; print(hashlib.sha256(open(sys.argv[1],'rb').read().replace(b'\r\n',b'\n')).hexdigest())" audit/VERDICTS.md
```

## Determinism

Seeds are fixed, package versions are pinned, and `PYTHONHASHSEED=0` is set by `run_all.sh`. One stored search, TVS-1 phase 2, seeded its grid from Python's salted `hash()` and cannot be replayed. `phaseC/tvs_recheck.py` re-evaluates a sample of its stored configurations instead.
