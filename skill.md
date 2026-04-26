# Skill: worldfork-cli

Use this skill to interact with a headless WorldFork backend via `backend.cli`.

## Entry points

- Base command: `python -m backend.cli`
- Installed console script (when package installed): `worldfork`
- Default API base: `http://127.0.0.1:8003`
- Default API prefix: `/api`

## Typical actions

- `status`: check backend health and Big Bang list size
- `set-key <key> <value> [--env-file .env]`: write provider credentials/env values
- `bigbang list|create|start|pause|resume|run-until-complete|reports|final-report`
- `runs`: list run metadata
- `multiverse tree|dag|metrics|step`: inspect and advance simulation graphs
- `universe step|force-deviation|trace`: apply interventions and inspect tick trace
- `jobs types|list|create|run`: queue/run jobs manually
- `logs requests|errors|webhooks|audit`: inspect event log streams
- `search <query>`: run web search for external references
- `troubleshoot`: aggregate health + recent errors into a compact report

## Guidance for assistant use

- Prefer `--json` when outputs are fed into downstream reasoning.
- Use `--base-url http://127.0.0.1:8003` when the API is available on the standard API port.
- Use `query` for direct passthrough calls when no dedicated command exists.
- Keep operations non-destructive unless explicitly requested; avoid `create`/`run` unless approved.
