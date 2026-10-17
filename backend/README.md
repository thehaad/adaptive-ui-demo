# AdaptiveUI backend

```bash
uv run fastapi dev main.py   # http://localhost:8000/api/layout
```

Expo web (http://localhost:8081) is allowed via CORS. For native devices set
`EXPO_PUBLIC_API_URL` (e.g. `http://10.0.2.2:8000` on the Android emulator, or
your LAN IP with `--host 0.0.0.0`).
