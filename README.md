# VantagePoint

Private competitive-intelligence workspace built with Django REST Framework and React.
One organization per deployment. All API users must be active Django staff users; this
is not a multi-tenant SaaS application and does not isolate different customers within
one database. Staff users share the workspace and can edit its records.

## Local setup

Requires Python 3.12+ and Node.js 22.12+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
cd backend
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173 and sign in with your Django staff account. Vite proxies
`/api` to port 8000. Do not put API keys or passwords in frontend environment variables.
The default API URL is `/api`; `VITE_API_URL` optionally overrides it at build time.

The repository includes a previously used SQLite database. **Do not ship it to a buyer
or use it as a production starting point.** Preserve your local copy if you need its
records; provision an empty production database and import reviewed data separately.
`seed_data` only works with DEBUG enabled and an empty database. Its records are
explicitly fictional and must never be represented as real company intelligence.

## Evidence and analysis

- Evidence Quality shows missing sources, missing dates, old records, future dates,
  verification coverage, failed collections and the last completed collection.
- Data Points lets a reviewer open the original source and mark a record verified.
  Verification requires a source; future publication dates cannot be verified.
  Editing evidence clears its prior verification unless it is explicitly reviewed
  again. Reviewer ID and time are stored with the record.
- Scraped records start unverified. Source links, sentiment, category, strength,
  impact and confidence scores are not independent fact checks.
- Article-based analysis uses verified records and publication dates. Signals still
  use capture dates and automated extraction; they require human interpretation.
- Company headcount, revenue, headquarters and similar profile fields are manual,
  unverified inputs. Their current accuracy is not established by this application.
- Dead Reckoning displays observation reports. Financial/headcount forecasts and
  inferred product/market totals are withheld, including legacy saved projections.
  Revenue is not ARR. A report is not a unique product, market, hire or funding round.
- Existing heuristic scores are not calibrated probabilities. Legacy insight text
  is withheld until regenerated. Lack of collected news does not demonstrate business
  weakness, lack of funding or inactivity.

## Checks

```bash
DEBUG=true PYTHONDONTWRITEBYTECODE=1 python backend/manage.py check
DEBUG=true PYTHONDONTWRITEBYTECODE=1 python backend/manage.py makemigrations --check --dry-run
DEBUG=true PYTHONDONTWRITEBYTECODE=1 python backend/manage.py test api scraping analysis --noinput
npm --prefix frontend run lint
npm --prefix frontend run build
```

CI runs backend tests, migration checks, frontend lint and build. Tests use an isolated
temporary database and mocked external HTTP responses. They do not modify local records.

## Production configuration

Set `DEBUG=false`, a unique random `DJANGO_SECRET_KEY` of at least 50 characters,
`ALLOWED_HOSTS`, and `CORS_ALLOWED_ORIGINS` to your HTTPS frontend origin. Startup fails
without a production secret. HTTPS redirects, secure cookies and HSTS are enabled.
Only set `TRUST_PROXY=true` when the trusted reverse proxy strips incoming forwarded
headers and sets `X-Forwarded-Proto` itself.

Use PostgreSQL (`USE_POSTGRES=true`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`,
`DB_PORT`) with a separately installed supported psycopg driver. Install and configure
an appropriate WSGI server, e.g. Gunicorn, for `vantagepoint.wsgi:application`; never use
Django runserver or Vite's development/preview server as the public production server.
Production server/driver installation and PostgreSQL deployment have not been tested
in this workspace.

Build the frontend, serve `frontend/dist` over HTTPS, and route `/api/` and `/admin/`
to Django on the same origin. Configure SPA fallback to `index.html` for frontend
routes only. Run migrations and `collectstatic`; serve collected Django static files
separately. Configure database backups with a tested restore procedure, logs, alerting,
and a network egress policy that blocks internal/metadata destinations.

```bash
cd backend
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

The application validates public destinations, pins connections to a validated IP,
checks TLS hostnames, validates redirects, and bounds response size. This does not
replace deployment egress controls or source-specific collection permissions.

See [RELEASE_READINESS.md](RELEASE_READINESS.md) for the tested scope and remaining work.
The configuration follows the [Django deployment checklist](https://docs.djangoproject.com/en/6.0/howto/deployment/checklist/)
and the [OWASP SSRF prevention guidance](https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html).
