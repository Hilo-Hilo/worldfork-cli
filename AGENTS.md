# AGENTS.md

If you are a coding agent (Codex, Claude Code, or anything that drives this CLI from the shell), read [`skill.md`](./skill.md) **first**. It is the canonical reference for:

- The root command (`worldfork`) and how `--help` is structured.
- The `--verbosity {summary,normal,full}` flag and `--fields a,b,c` projector — the only way to keep trace responses from blowing your context window.
- The canonical discovery flow: `model defaults` → `bigbang list` → `multiverse tree` → `universe actors` → `cohort transcript`.
- Async vs sync semantics for `bigbang run-until-complete` (default is async; `--sync` blocks for tens of minutes to hours).
- Live model routing via `worldfork model {list,get,set,defaults}` — no container restart needed.

Everything below is just a quick reference; defer to `skill.md` for full detail.

## Setup

```bash
pipx install git+https://github.com/Hilo-Hilo/worldfork-cli.git
export WORLD_FORK_API_BASE=http://localhost:8003   # or your backend URL
worldfork --help
```

## Hard rules

- **Always** start exploratory calls at `--verbosity summary`. A single `universe trace` at `full` is 200+ KB.
- **Never** run `bigbang run-until-complete --sync` without an explicit `--timeout`. The CLI defaults to no timeout; the simulation can take hours.
- The CLI is synchronous; the backend is async via Celery. Mutations enqueue jobs and return — poll with `worldfork jobs list` / `worldfork logs errors` / `worldfork multiverse metrics`.
- Top-level flags (`--verbosity`, `--json`, `--timeout`, `--base-url`) must come **before** the subcommand. argparse rejects them after.

## Common pitfalls

- `worldfork --json` alone is not a context guard — pair it with `--verbosity summary` or `--fields ...`.
- `logs requests` does not accept `--actor-id`/`--cohort-id` server-side. To find a cohort's calls, fetch `--limit N` rows then filter client-side via `jq`.
- Some backend deployments only mount `/health` at root, not `/api/health`. If `worldfork status` 404s, point the upstream at the `/api/health` alias or use `worldfork query GET http://host/health`.
- The CLI sends `display_name` in `bigbang create`. Older backends that expect `name` will reject the call — use `worldfork query POST /big-bangs --payload-file ...` as an escape hatch.

## Don't

- Don't pipe a `full` trace through `jq` to subset it. Use `--verbosity summary` or `--fields` so the network and the model both see less.
- Don't `worldfork model set` for a single run if a global preset already covers it. Use `worldfork model defaults` once per backend.
- Don't write client-side polling loops for completion when `worldfork query GET /big-bangs/<id>` returns the status field — let the agent harness's monitoring handle it.
