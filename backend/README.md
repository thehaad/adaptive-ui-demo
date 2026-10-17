# AdaptiveUI backend

```bash
uv run fastapi dev main.py   # http://localhost:8000/api/layout
```

Expo web (http://localhost:8081) is allowed via CORS. For native devices set
`EXPO_PUBLIC_API_URL` (e.g. `http://10.0.2.2:8000` on the Android emulator, or
your LAN IP with `--host 0.0.0.0`).

## Outcome insights (read-only)

```bash
uv run python insights.py --db path/to/sessions.db   # prints the aggregate summary and whether Claude receives it
```

Past AI-composed sessions are grouped by structure (guided vs compact) and summarized
deterministically; the summary is given to Claude only as an observational tie-breaker.
Set `ADAPTIVEUI_INSIGHTS=off` to disable it. Synthetic histories for demos and tests:

```bash
uv run python -m tools.seed_synthetic --scenario guided_better --db /tmp/demo.db
# scenarios: guided_better, compact_better, balanced, no_history (never writes the default database)
```

## Tests (offline, no Anthropic requests)

```bash
uv run python -m unittest discover -s tests -t .
```
