# worldfork-cli

Headless backend and text-first CLI for WorldFork — a platform for explainable, recursively branching social simulations. There is no browser frontend in this repo: everything happens through a FastAPI backend, a Docker stack, and `backend.cli`, which coding agents (Claude Code, Codex, local scripts) can drive directly.

A user creates a root scenario called a **Big Bang**. The backend initializes a simulated society with cohort states, hero agents, media channels, social feeds, event queues, sociology rules, tick progression, God-agent reviews, and multiverse branching. Operators read and steer that state through CLI commands.

## What Is Included

- FastAPI backend at `http://localhost:8003`
- PostgreSQL and Redis via Docker Compose
- Celery workers for background jobs and simulation tasks
- CLI entry point at `python -m backend.cli`
- `skill.md` for Claude-style agent integrations
- Text and JSON outputs for dependency graphs, reports, logs, jobs, and interventions

## Prerequisites

- Docker Desktop or another Docker Compose compatible runtime
- Python 3.11+ if you want to run the CLI or tests outside Docker
- `make`
- An OpenRouter key for real model-backed runs

The backend can boot without a real provider key, but full simulation workflows that call LLM providers need `OPENROUTER_API_KEY`.

## Quickstart

```bash
git clone https://github.com/Hilo-Hilo/worldfork-cli.git
cd worldfork-cli
cp .env.example .env
```

Edit `.env` and set at least:

```bash
OPENROUTER_API_KEY=your_key_here
ZEP_ENABLED=false
BACKEND_API_BASE=http://localhost:8003
```

Start the stack:

```bash
make build
make up
make migrate
```

Check that the API and CLI can talk:

```bash
make cli ARGS="status"
```

API docs are available at:

```text
http://localhost:8003/docs
```

## Docker Services

The default Compose stack starts:

| Service | Purpose |
| --- | --- |
| `postgres` | Persistent platform state |
| `redis` | Broker/cache for jobs and streams |
| `api` | FastAPI backend on host port `8003` |
| `worker_p0` to `worker_p3` | Celery workers for priority queues |
| `beat` | Scheduled background worker |

Useful commands:

```bash
make up
make logs
make down
make clean-data
```

Run the CLI inside Docker:

```bash
docker compose --profile cli run --rm cli status
docker compose --profile cli run --rm cli jobs list --limit 10
```

Run the CLI from the host:

```bash
make cli ARGS="status"
PYTHONPATH=. python -m backend.cli --help
```

## CLI Basics

The CLI defaults to:

```text
http://127.0.0.1:8003/api
```

You can override the API root with either:

```bash
BACKEND_API_BASE=http://localhost:8003
WORLD_FORK_API_BASE=http://localhost:8003
```

Use `--json` when another agent or script needs structured output:

```bash
make cli ARGS="--json status"
make cli ARGS="--json jobs list --limit 5"
```

### Timeouts

The CLI ships with **no HTTP timeout by default** — every command waits as long as the API takes to respond. This matters because some operations (`bigbang run-until-complete --sync`, large `multiverse step` jobs, slow LLM providers) can take many minutes.

Pass `--timeout SECONDS` to cap an individual request:

```bash
make cli ARGS="--timeout 30 status"
```

Note: the `--timeout` flag belongs to the top-level CLI, not subcommands. It must come before the subcommand name (`bigbang`, `jobs`, etc.).

## Common Workflows

List current runs:

```bash
make cli ARGS="bigbang list"
```

Create a Big Bang from prose:

```bash
make cli ARGS="bigbang create \"Cold War 2026\" --scenario-text \"A contested election triggers institutional conflict across media, courts, and public coalitions.\""
```

Create from a JSON payload:

```bash
make cli ARGS="bigbang create \"Policy Divergence\" --payload examples/payload.json"
```

Start, pause, resume, or run a Big Bang:

```bash
make cli ARGS="bigbang start <big_bang_uuid>"
make cli ARGS="bigbang pause <big_bang_uuid>"
make cli ARGS="bigbang resume <big_bang_uuid>"
make cli ARGS="bigbang run-until-complete <big_bang_uuid>"
```

### `run-until-complete`: async by default

`bigbang run-until-complete` enqueues a `run_big_bang_until_complete` job and returns immediately with a `job_id`. Track it with `jobs list`, `logs errors`, or `multiverse metrics`.

```bash
make cli ARGS="bigbang run-until-complete <big_bang_uuid> --max-ticks 24"
# Queued run_big_bang_until_complete for <big_bang_uuid>.
#   job_id: <uuid>
#   Track with: jobs list / logs errors / multiverse metrics
```

Pass `--sync` to block the CLI on the API until the simulation finishes:

```bash
make cli ARGS="bigbang run-until-complete <big_bang_uuid> --sync --max-ticks 24"
```

**WARNING.** `--sync` runs the entire simulation in the API request thread. Wall time depends on:

- `--max-ticks` (default 24)
- `DEFAULT_MODEL` / `FALLBACK_MODEL` set in `.env` — LLM latency dominates
- active universe count and branching factor

Expect tens of minutes to hours for non-trivial scenarios. Combine `--sync` with an explicit cap if you want a hard deadline:

```bash
make cli ARGS="--timeout 7200 bigbang run-until-complete <big_bang_uuid> --sync"
```

Inspect multiverse state:

```bash
make cli ARGS="multiverse tree <big_bang_uuid>"
make cli ARGS="multiverse dag <big_bang_uuid>"
make cli ARGS="multiverse metrics <big_bang_uuid>"
```

Advance or steer simulations:

```bash
make cli ARGS="multiverse step <big_bang_uuid>"
make cli ARGS="universe step <universe_uuid>"
make cli ARGS="universe force-deviation <universe_uuid> 3 --reason \"Manual operator branch\" --prompt \"Investigate divergent coalition response.\""
make cli ARGS="universe trace <universe_uuid> 3"
```

Inspect jobs, logs, and reports:

```bash
make cli ARGS="jobs types"
make cli ARGS="jobs list --limit 20"
make cli ARGS="logs errors --limit 20"
make cli ARGS="logs requests --limit 20"
make cli ARGS="bigbang reports <big_bang_uuid>"
make cli ARGS="bigbang final-report <big_bang_uuid>"
```

Run troubleshooting summary:

```bash
make cli ARGS="troubleshoot --include-jobs"
```

Run web search through the CLI:

```bash
make cli ARGS="search \"current AI governance regulatory timeline\""
```

Write keys into `.env` without opening an editor:

```bash
make cli ARGS="set-key OPENROUTER_API_KEY your_key_here"
make cli ARGS="set-key DEFAULT_MODEL deepseek/deepseek-v3.2"
```

## Generic API Queries

If the CLI does not yet expose a dedicated command, use `query`:

```bash
make cli ARGS="query GET /api/big-bangs"
make cli ARGS="query POST /api/jobs --data '{\"job_type\":\"run_big_bang_until_complete\",\"payload\":{}}'"
```

Use `/docs` to inspect the current API routes and payload schemas.

## Testing

Fast smoke test after Docker boot:

```bash
make cli ARGS="status"
make cli ARGS="jobs list --limit 5"
make cli ARGS="bigbang list"
make cli ARGS="troubleshoot --include-jobs"
```

Containerized test run:

```bash
make test
```

Local test tiers, assuming `.venv` exists and dependencies are installed:

```bash
make test-unit
make test-integration
make test-e2e
make test-all
```

Lint/type checks:

```bash
make lint
```

Recommended first validation for a new contributor:

```bash
cp .env.example .env
make build
make up
make migrate
make cli ARGS="status"
make cli ARGS="jobs types"
```

## Async vs sync model

- **CLI process**: synchronous. `backend/cli.py` uses `httpx.Client` (not `AsyncClient`). One invocation = one process = one blocking HTTP request.
- **Server handlers**: mostly synchronous FastAPI endpoints (plain `def`, not `async def`). They block on the SQLAlchemy session for the duration of the request.
- **Background work**: lives in **Celery**, not the request path. `bigbang start`, `multiverse step`, `universe step`, `jobs create`, and the default `bigbang run-until-complete` all enqueue work to the priority workers (`worker_p0`–`p3`) and return quickly. The CLI does not poll for completion — follow up with `jobs list` / `logs errors` / `multiverse metrics`.
- **Blocking exception**: `bigbang run-until-complete --sync` is synchronous server-side; the CLI sits on the HTTP connection until the simulation finishes. See the warning above.

## Agent Integration

`skill.md` describes the command vocabulary for Claude Code, Codex, or any agent that can call shell commands. The intended pattern is:

1. Start the Docker backend.
2. Set provider keys with `backend.cli set-key`.
3. Use `status`, `troubleshoot`, `jobs`, `logs`, and `query` for situational awareness.
4. Use `bigbang`, `multiverse`, and `universe` commands to create, advance, inspect, and steer simulations.
5. Prefer `--json` when the calling agent needs machine-readable output.

Example agent-friendly calls:

```bash
PYTHONPATH=. python -m backend.cli --json status
PYTHONPATH=. python -m backend.cli --json multiverse dag <big_bang_uuid>
PYTHONPATH=. python -m backend.cli --json logs errors --limit 10
PYTHONPATH=. python -m backend.cli --json troubleshoot --include-jobs
```

## Troubleshooting

Check containers:

```bash
docker compose ps
docker compose logs api
docker compose logs worker_p0
```

If migrations fail, verify database URLs in `.env`:

```text
DATABASE_URL=postgresql+asyncpg://worldfork:worldfork@localhost:5433/worldfork
DATABASE_URL_SYNC=postgresql+psycopg://worldfork:worldfork@localhost:5433/worldfork
```

If the host CLI cannot connect, confirm the API is reachable:

```bash
curl http://localhost:8003/health
```

If a real run fails before model output, confirm:

```bash
make cli ARGS="set-key OPENROUTER_API_KEY your_key_here"
make cli ARGS="set-key DEFAULT_MODEL deepseek/deepseek-v3.2"
make cli ARGS="troubleshoot --include-jobs"
```

Reset local Docker state when you want a clean database and Redis volume:

```bash
make clean-data
make up
make migrate
```

## Project Layout

```text
backend/                 FastAPI app, simulation engine, providers, tests, CLI
backend/cli.py           Text-first CLI entry point
infra/                   Docker, Postgres, and Alembic infrastructure
source_of_truth/         Canonical simulation configuration and schemas
runs/                    Runtime artifacts mounted into containers
skill.md                 Agent-facing skill instructions
docker-compose.yml       Backend, worker, Redis, Postgres, and CLI services
```

This branch intentionally does not include a browser frontend. All interaction is through the API, CLI, logs, reports, and structured JSON/text outputs.
