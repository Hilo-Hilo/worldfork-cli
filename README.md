# worldfork-cli

`worldfork` is a small, dependency-light command-line client for a [WorldFork](https://github.com/Hilo-Hilo/WorldFork) backend — a platform for explainable, recursively branching social simulations.

It is **only the client**. There is no FastAPI app, no Docker stack, no Celery workers, and no browser frontend in this repository. You point the CLI at a running backend with `WORLD_FORK_API_BASE` (or `--base-url`) and it does the rest over HTTP.

## Install

```bash
# Recommended: isolated install via pipx
pipx install git+https://github.com/Hilo-Hilo/worldfork-cli.git

# Or as a regular pip dependency
pip install git+https://github.com/Hilo-Hilo/worldfork-cli.git

# Or for local development
git clone https://github.com/Hilo-Hilo/worldfork-cli.git
cd worldfork-cli
pip install -e ".[dev]"
```

After install you have a `worldfork` console script:

```bash
worldfork --help
```

## Configure

The CLI reads two env vars at startup:

| Variable | Purpose | Default |
| --- | --- | --- |
| `WORLD_FORK_API_BASE` | Backend root URL (wins over `BACKEND_API_BASE`) | `http://127.0.0.1:8003` |
| `BACKEND_API_BASE` | Same, kept for compatibility | — |

Override per-invocation with `--base-url`:

```bash
worldfork --base-url https://worldfork.example.com status
```

Copy `.env.example` to `.env` if you want a checked-in baseline; the CLI does not read `.env` itself, but `worldfork set-key` writes to it.

## Quickstart

```bash
worldfork status
worldfork bigbang list
worldfork --json bigbang list | jq '.[0].id'
worldfork bigbang create "Cold War 2026" \
  --scenario-text "A contested election triggers institutional conflict."
worldfork bigbang run-until-complete <big_bang_id>      # async (default)
worldfork multiverse dag <big_bang_id>
worldfork logs errors --limit 20
```

## Command map

All commands accept `--json` for machine-readable output. The top-level flags `--base-url`, `--api-prefix`, `--timeout`, `--json`, and `--env-file` must come **before** the subcommand.

### Read-only

| Command | What it does |
| --- | --- |
| `worldfork status` | `GET /api/health` + `GET /api/big-bangs`, prints a summary table. |
| `worldfork troubleshoot [--include-jobs] [--limit N] [--run-id X]` | Health + recent error log digest. |
| `worldfork query GET /path` | Arbitrary backend GET. Supports `--data` / `--payload-file` for write methods. |
| `worldfork search "<query>" [--limit 6]` | DuckDuckGo HTML search; no backend involvement. |
| `worldfork bigbang list` | List Big Bangs. |
| `worldfork bigbang reports <big_bang_id>` | List reports. |
| `worldfork runs [--status X] [--q text] [--limit N]` | List run metadata. |
| `worldfork multiverse tree <big_bang_id>` | Raw dependency snapshot. |
| `worldfork multiverse dag <big_bang_id>` | Rendered DAG with status labels. |
| `worldfork multiverse metrics <big_bang_id>` | Aggregate multiverse metrics. |
| `worldfork universe trace <universe_id> <tick> [--include-raw]` | Per-tick actor trace. |
| `worldfork jobs types` | Registered job types. |
| `worldfork jobs list [--big-bang-id X] [--limit N]` | Recent jobs. |
| `worldfork logs requests [--run-id] [--universe-id] [--provider] [--status] [--limit N] [--offset N]` | LLM/provider request logs. |
| `worldfork logs errors [--run-id] [--limit N] [--offset N]` | Error logs. |
| `worldfork logs webhooks [--run-id] [--status] [--limit N] [--offset N]` | Webhook delivery logs. |
| `worldfork logs audit [--limit N] [--offset N]` | Audit logs. |

### Mutating

| Command | What it does |
| --- | --- |
| `worldfork set-key KEY VALUE [--env-file .env]` | Rewrite a `KEY=VALUE` line in a local env file. **No API call.** |
| `worldfork bigbang create NAME [--description] [--scenario-text \| --payload path]` | Create a Big Bang. Reads scenario from stdin if neither flag is set. |
| `worldfork bigbang start \| pause \| resume <big_bang_id>` | State transitions. |
| `worldfork bigbang run-until-complete <big_bang_id> [--max-ticks N] [--sync]` | See **Async vs sync** below. |
| `worldfork bigbang final-report <big_bang_id> [--title] [--summary]` | Generate the final report. |
| `worldfork multiverse step <big_bang_id>` | Queue one tick across active universes. |
| `worldfork universe step <universe_id> [--tick N]` | Simulate one tick. |
| `worldfork universe force-deviation <universe_id> <tick> --mode {god_prompt,structured_delta} [--reason] [--prompt \| --prompt-file] [--delta \| --delta-file] [--no-auto-start]` | Manual operator branch. |
| `worldfork jobs create <job_type> --payload '{...}' [--big-bang-id] [--idempotency-key]` | Enqueue a job. |
| `worldfork jobs run <job_id>` | Run a queued job inline. |

## Async vs sync

The CLI itself is **synchronous** — one process, one blocking HTTP request per command.

The backend offloads heavy work to Celery. Most "mutating" commands enqueue a job and return immediately; you follow up with `jobs list`, `logs errors`, or `multiverse metrics` to track progress.

**`bigbang run-until-complete` is async by default.** It enqueues a `run_big_bang_until_complete` job and prints the job id:

```bash
$ worldfork bigbang run-until-complete <big_bang_id>
Queued run_big_bang_until_complete for <big_bang_id>.
  job_id: <uuid>
  Track with: worldfork jobs list / logs errors / multiverse metrics
```

Pass `--sync` to block the CLI on the API until the simulation finishes. **This will take a long time.** Wall time depends on:

- `--max-ticks` (default 24)
- the model the backend uses for agent calls (LLM latency dominates)
- active universe count and branching

Expect tens of minutes to hours for non-trivial scenarios. The `--sync` path prints a stderr warning before issuing the request.

## Timeouts

There is **no HTTP timeout by default**. Every command waits as long as the API takes. This matters for `--sync`, large `multiverse step` jobs, and slow providers.

Cap an individual request with `--timeout SECONDS`:

```bash
worldfork --timeout 30 status
worldfork --timeout 7200 bigbang run-until-complete <id> --sync
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
```

Project layout:

```
src/worldfork/
  __init__.py     # version
  __main__.py     # `python -m worldfork`
  cli.py          # argparse construction + main()
  client.py       # WorldForkClient (httpx wrapper)
  commands.py     # all command handlers
  output.py       # formatting helpers
tests/
  test_smoke.py   # parser + arg parsing, no network
```

## Backend compatibility

`worldfork` assumes the backend exposes a `/health` route at root **and** under the `/api` prefix (`/api/health`). If your deployment only has `/health`, either add an alias or pass `--api-prefix ""` and prefix paths manually with `query`.

The CLI was written against the `cli-backend` branch of the WorldFork repository.

## License

MIT — see [LICENSE](LICENSE).
