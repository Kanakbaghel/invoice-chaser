# Deploying the Invoice Chaser webapp

This is a Flask app (`webapp/app.py`) serving a static-ish frontend
(`webapp/templates/index.html`, `webapp/static/`) plus a small JSON API
that wraps `src/`. No database, no build step, no separate frontend
framework — one `pip install` and one process to run.

## Files that matter for deploy
- `requirements.txt` (repo root) — now includes `gunicorn` for production serving
- `webapp/app.py` — entry point, reads `PORT` from env, binds `0.0.0.0`
- `webapp/Procfile` — tells the host how to start it

## Option A — Render.com (free tier, recommended, matches app.py's own docstring)
1. Push this repo to your GitHub.
2. Render dashboard → **New → Web Service** → connect the repo.
3. Settings:
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn --chdir webapp -w 2 app:app`
   - **Instance type:** Free is fine for a demo.
4. Deploy. Render assigns the `PORT` env var automatically — `app.py`
   already reads it, no code change needed.

## Option B — Railway
1. Railway → **New Project → Deploy from GitHub repo**.
2. Railway auto-detects Python. If it asks for a start command, use:
   `gunicorn --chdir webapp -w 2 app:app`
3. Railway sets `PORT` automatically, same as above.

## Option C — Any plain VM / container
```bash
pip install -r requirements.txt
gunicorn --chdir webapp -w 2 -b 0.0.0.0:${PORT:-5000} app:app
```

## Local run (dev server, not for production)
```bash
pip install -r requirements.txt
python webapp/app.py   # http://localhost:5000
```

## Verified before packaging
- `/`, `/api/languages`, `/api/sample`, CSV upload (`/api/upload/columns`
  → `/api/upload/compute`) all return correct data under both the Flask
  dev server and `gunicorn`.
- Sample-data bundle and CSV-upload bundle both include populated
  `why` text on every overdue row, risk profile, and action-plan item,
  plus a non-empty `impact.summary_text`.
- No orphaned element IDs between `main.js` and `index.html`.
- CSS is brace-balanced; new responsive rules confirmed inside the
  existing `620px`/`1000px` breakpoints; both theme variable blocks
  (`:root` dark default and `[data-theme="light"]`) already define
  every custom property the new sections use — no new tokens added.
