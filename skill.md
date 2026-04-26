# Skill: worldfork-cli

Use this skill to drive a headless WorldFork backend from the shell. The root command is **`worldfork`** (after `pipx install` / `pip install`). Without install: `python -m worldfork`. The local checkout directory is incidental — there is no `WorldFork-Hanson` command and never was.

`worldfork --help` always works. So does `worldfork <group> --help` and `worldfork <group> <subcommand> --help`. Read help when in doubt; don't guess.

## Mental model

- The CLI is **synchronous**. One invocation, one HTTP request, one response. No daemon.
- The backend offloads heavy work to **Celery**. Most mutations enqueue a job and return immediately. To track progress, poll with `worldfork jobs list`, `worldfork logs errors`, or `worldfork multiverse metrics` — the CLI does **not** wait for you.
- The one exception is `bigbang run-until-complete --sync`, which blocks the request until the entire simulation finishes (tens of minutes to hours). Default behaviour is async.
- Default HTTP timeout is **none** — the CLI will wait indefinitely. Pass `--timeout SECONDS` to cap.

## The single most important flag: `--verbosity`

Trace endpoints and log endpoints return rich payloads — a single tick trace can be **50–200 KB of JSON** with 13 actors × ~17 fields each. Reading it raw will overflow your context window before you learn anything.

| Tier | What you get | When to use |
|---|---|---|
| `summary` | Identifiers + status only (~80 bytes per record) | First exploratory call. Almost always start here. |
| `normal` | Key business fields (rationales, deltas, status) (~500 bytes) | Default. Once you've narrowed scope. |
| `full` | Everything the API returned | Only when you genuinely need the prompt packet, raw response, or full state snapshot. |

```bash
worldfork --verbosity summary status                # 1-line health + count
worldfork --verbosity summary universe trace UNI 1  # actors as id + kind only
worldfork --verbosity full    universe trace UNI 1  # original fat payload
```

`--verbosity` is a **top-level** flag and must come before the subcommand:

```bash
worldfork --verbosity summary bigbang list   # correct
worldfork bigbang list --verbosity summary   # WRONG — argparse error
```

### When you need exactly N keys: `--fields`

`--fields a,b,c` overrides `--verbosity` and projects each record to just those top-level keys. Available on `universe trace`, `cohort transcript`, and every `logs` subcommand.

```bash
worldfork universe trace UNI 1 --fields actor_id,rationale,state_delta
worldfork logs requests --limit 10 --fields call_id,total_tokens,latency_ms
```

Top-level keys only — no dotted paths. For deeper projection, pipe `--json` output through `jq`.

## Canonical discovery flow

When given a fresh backend, walk it in this order. Each step uses the smallest payload that answers the question:

```bash
# 0. (One-time) Pick the model the simulation should use.
worldfork model list                           # see what's currently routed
worldfork model set google/gemini-3.1-flash-lite-preview   # hot-swap, no restart

# 1. Confirm backend is alive and how many runs exist.
worldfork --verbosity summary status

# 2. List runs. Pick a run_id.
worldfork --verbosity summary bigbang list

# 3. See universes inside that run. Pick a universe_id.
worldfork --verbosity summary multiverse tree <run_id>

# 4. See the actors (cohorts/heroes/gods) in that universe.
worldfork universe actors <universe_id>

# 5. Walk one cohort across ticks at low verbosity.
worldfork --verbosity summary cohort transcript <universe_id> <cohort_id> \
  --from-tick 1 --to-tick 5

# 6. Once you've identified an interesting tick, zoom in at higher verbosity.
worldfork --verbosity normal cohort transcript <universe_id> <cohort_id> \
  --from-tick 5 --to-tick 5

# 7. Only if you need the full prompt packet / raw response, escalate to full.
worldfork --verbosity full --json universe trace <universe_id> 5 \
  --actor-id <cohort_id>
```

Steps 1–4 should each cost well under 1 KB. Step 7 is where the payload is large; pair with `--actor-id` so you only get the one row.

## Cohort and actor filtering

`universe trace` accepts client-side filters that shrink the actor list before projection:

```bash
worldfork universe trace UNI 1 --actor-kind cohort        # only cohorts
worldfork universe trace UNI 1 --actor-id coh_01kq…       # one actor
worldfork universe trace UNI 1 --actor-kind cohort \
  --fields actor_id,rationale                             # cohorts, two keys each
```

`worldfork cohort transcript` is a higher-level convenience that walks a tick range and stitches one cohort's row across ticks. It's N HTTP calls — one per tick — so bound the range.

## Live hot model swap — `worldfork model`

The backend keeps a per-job-type routing table (preferred + fallback model, timeout, rate limits). It's mutable through `PATCH /api/settings/model-routing` and the worker reads it on every call — **swapping a model takes effect on the next tick, no container restart, no env edit**.

```bash
worldfork model list                           # see all 14 entries
worldfork model get simulate_universe_tick     # one entry

# CLI's recommended preset (gemma-4-31b-it / gpt-5.4 / gemini-3.1-flash-lite).
worldfork model defaults --dry-run             # preview what would change
worldfork model defaults                       # apply

# Or set per-call. Default scope = every job_type. Default fallback = gemini-3.1-flash-lite-preview.
worldfork model set google/gemini-3.1-flash-lite-preview

# Scope to one job_type, override fallback explicitly.
worldfork model set anthropic/claude-haiku-4-5 \
  --job-type god_agent_review \
  --fallback openai/gpt-4o-mini

# Pass --fallback "" to leave the existing fallback alone.
worldfork model set google/gemini-3.1-flash-lite-preview --fallback ""
```

### The default preset

`worldfork model defaults` applies a tiered routing per the PRD's god-agent tier:

| Tier | job_types | Model |
|---|---|---|
| God-class | `initialize_big_bang`, `god_agent_review`, `force_deviation`, `aggregate_run_results` | `openai/gpt-5.4` |
| Standard | everything else (10 entries: tick simulation, deliberation, propagation, sociology, branching, review-index build, export, apply) | `google/gemma-4-31b-it` |
| Fallback | every entry | `google/gemini-3.1-flash-lite-preview` |

`aggregate_run_results` is in the god tier because it's the LLM call that produces the run-level **classification** (conflict_trajectory, institutional_legitimacy, etc.) that gets persisted into `results.classifications`. It is the classifier; there is no separate classifier job_type.

Use `worldfork model defaults` **before** `bigbang run-until-complete` (or any `bigbang start`) so the simulation runs on the model you want without a container roundtrip. Verify with `worldfork --verbosity normal logs requests --run-id <id> --limit 1` — `model_used` will show the resolved slug (often pinned to a date-stamped snapshot).

Knobs not exposed yet (use `worldfork query PATCH /settings/model-routing --data '...'` for now): `temperature`, `top_p`, `max_tokens`, `requests_per_minute`, `tokens_per_minute`, `timeout_seconds`, `daily_budget_usd`.

## Async vs sync — `bigbang run-until-complete`

```bash
# Async (default): enqueues a job, returns the job_id. Poll for completion.
worldfork bigbang run-until-complete <run_id> --max-ticks 24

# Sync: blocks the CLI on the API connection until the whole simulation finishes.
worldfork --timeout 7200 bigbang run-until-complete <run_id> --sync --max-ticks 24
```

`--sync` prints a stderr warning before issuing the request. Wall time scales with `--max-ticks` × active universes × LLM latency. Expect tens of minutes to hours for non-trivial scenarios.

## When `--json` is right

Use `--json` whenever you'll programmatically parse the output (extracting an id for the next call, counting rows, piping to `jq`, etc.). Pair it with `--verbosity summary` so the JSON itself stays small:

```bash
RUN=$(worldfork --json --verbosity summary bigbang list | jq -r '.[0].id')
worldfork --verbosity summary multiverse tree "$RUN"
```

Without `--json`, output is human-formatted (tables for lists, indented JSON for objects).

## Escape hatch — `worldfork query`

Any backend route the CLI doesn't wrap is reachable via `worldfork query`:

```bash
worldfork --json query GET /jobs/queues
worldfork query POST /jobs --data '{"job_type":"run_big_bang_until_complete","payload":{}}'
```

`query` does not respect `--verbosity`; the response is returned raw. Use `jq` for projection.

## Mutating commands — quick reference

These all take effect on the backend. Most enqueue a job and return immediately.

```bash
worldfork bigbang create "Name" --scenario-text "..."
worldfork bigbang start | pause | resume <run_id>
worldfork bigbang final-report <run_id> [--title …] [--summary …]
worldfork multiverse step <run_id>
worldfork universe step <universe_id> [--tick N]
worldfork universe force-deviation <universe_id> <tick> --mode {god_prompt,structured_delta} \
  [--reason …] [--prompt … | --prompt-file …] [--delta … | --delta-file …]
worldfork jobs create <job_type> --payload '{...}' [--big-bang-id …]
worldfork jobs run <job_id>
worldfork set-key KEY VALUE   # writes to local .env, no API call
```

## Known limits

- The `logs` endpoints accept only the filters listed in their `--help`. `--actor-id`, `--cohort-id`, `--tick`, and date ranges are **not** server-side filters; do not assume they exist. To find logs for a specific cohort, use `universe trace` and project the actor row, or fetch `logs requests --universe-id X` and filter client-side with `jq`.
- Client-side filtering on a paginated `--limit N` response can miss matches outside the page. Bump `--limit` or paginate with `--offset` rather than relying on a small page hitting your filter.
- `worldfork query` always uses the API prefix (defaults to `/api`). Pass an absolute URL (`http://...`) to bypass.

## Failure mode handling

- **`HTTP 404 GET api/health`**: backend is missing the `/api/health` alias. Either upgrade the backend or use `--api-prefix ""` and call `query GET /health` directly.
- **`error: HTTP 5xx ...`**: check `worldfork logs errors --limit 10` and `worldfork jobs list --limit 10` to see what failed server-side.
- **CLI hangs**: there is no default timeout. If you suspect a stuck call, abort and re-run with `--timeout 30`.
