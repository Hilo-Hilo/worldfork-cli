# WorldFork

WorldFork is an explainable, recursively branching social-simulation platform with a backend API and CLI interface. A user creates a root scenario called a **Big Bang**, and the system initializes a structured simulated society with dynamic cohort states, hero agents, news/media channels, social-media feeds, event queues, and sociology rules. The simulation advances in configurable ticks, and branching points can recursively fork into multiverses via the God-agent.

## Quickstart

```bash
cp .env.example .env
vim .env   # paste real OPENROUTER_API_KEY; leave ZEP_ENABLED=false

make build
make up
make migrate
make seed
make cli ARGS="status"
```

| Service | URL |
|---------|-----|
| API | http://localhost:8003 |
| API docs | http://localhost:8003/docs |

## CLI usage

```bash
python -m backend.cli --help
make cli ARGS="bigbang list"
make cli ARGS="bigbang create \"Cold war 2026\" --scenario-text \"simulate...\""
make cli ARGS="jobs list --limit 10"
make cli ARGS="multiverse dag <big_bang_uuid>"
make cli ARGS="troubleshoot --include-jobs"
```

## Docker profiles

The `cli` service is optional and can be launched from compose when you want a one-off
containerized CLI run:

```bash
docker compose --profile cli run --rm cli status
```

## Claude skill

The backend branch includes [`skill.md`](./skill.md) with action verbs and usage
notes for Claude-style automation integrations.

## Reference

- **Implementation plan**: `/home/hacktech-collab/.claude/plans/implement-this-plan-in-valiant-toast.md`
- **PRD**: `prd-do-not-delete/prd.md`
