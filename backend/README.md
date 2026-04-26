# WorldFork Backend

Backend-only core V1 spine for WorldFork.

## Local setup

1. Create PostgreSQL database and set `DATABASE_URL`.
2. Install dependencies from `backend/pyproject.toml`.
3. Run Alembic migrations from `backend/`.
4. Start the API with `uvicorn app.main:app --reload`.
5. Optional worker: `celery -A backend.app.workers.celery_app worker -Q p0`.

The service stores canonical platform state in PostgreSQL and large/raw payloads in the artifact store configured by `ARTIFACT_ROOT`.

## Sample run

After migrations, start the API and then run:

```bash
curl -X POST http://localhost:8003/api/sample-runs
```

This creates a Big Bang, runs several backend ticks, creates multiverse/final reports, and writes artifacts under `ARTIFACT_ROOT`.

## CLI

Use the packaged CLI to control the backend from scripts, automation, or Claude-like tools:

```bash
python -m backend.cli status
python -m backend.cli bigbang list
python -m backend.cli bigbang create "Policy Divergence" --scenario-text "..."
python -m backend.cli multiverse dag <big_bang_uuid>
```

Big Bang creation is prose-first. Send `scenario_text` as one plain-text string; if a PDF is involved, convert it to text before calling the API. The backend preserves the full text, chunks long text into artifacts when needed, and initializes `M1:T0` from that corpus.
