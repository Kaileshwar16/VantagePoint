# Release readiness — September 9, 2026

Status: hardened development application; **not yet certified or validated for commercial production**.

## Implemented and checked

- Staff-only authenticated API, browser sign-in/sign-out and CSRF protection.
- Safe production configuration defaults, bounded API pages and basic request throttling.
- Public-web destination validation with IP pinning, TLS hostname checks, redirect
  revalidation and bounded response bodies.
- Input checks for time windows, comparisons, source verification and collection types.
- Consistent collection job completion times, item counts and failure responses.
- Evidence Quality dashboard and source review controls with reviewer/time metadata.
- Removal of unsupported industry statistics and automatic financial forecasts.
- Legacy financial estimates and unsupported legacy insight text withheld from API output.
- RSS publication-date case fix; unknown publication dates and reporting quarters stay unknown.
- Frontend pagination follows result pages; API errors are visible; stale report
  selection, invalid geographic substring matches and fabricated geographic weights fixed.
- Backend dependency manifest, environment examples, setup instructions and CI checks.

Validation: 30 isolated Django tests pass, Django system and production deployment
checks pass, no missing migrations, frontend ESLint and production build pass.
The build still reports a large JavaScript chunk. Production deployment check used
representative environment values, not a real deployment secret or host.

## Data audit

The local database contained six companies and 195 data points, zero verified records,
and 35 records without publication dates. Source URL presence is not source validity.
The existing database and user edits were preserved. No company figure, scraped claim,
or source redistribution right was independently validated in this pass. A clean
production database and a reviewed import are required. The repository already tracks
SQLite/bytecode files; ignore rules prevent new artifacts but do not remove tracked files.
Remove those from the distribution package, preserving any local data you need.

## Release blockers and work still needed

1. **Real evidence:** review source content and publication dates, remove demo claims
   from any import, verify company profile fields, and establish source-specific
   collection and redistribution permissions. Add structured company field provenance
   before describing profiles as verified.
2. **Collection operations:** current scraping/analysis runs synchronously. Implement
   durable background jobs, per-company concurrency limits, retry/backoff, job progress,
   monitoring and a scheduler before unattended or high-volume use. Some signal
   extractors still suppress individual upstream errors or match news summaries rather
   than authoritative filings/transcripts; absence of results is not success evidence.
3. **Analysis quality:** validate extraction precision, deduplicate syndicated reports
   and events, calibrate or eliminate remaining heuristic scores, and make repeated
   analysis idempotent. Legacy patterns/battlecards need regeneration and review. Some
   template-based strategic interpretations remain hypotheses requiring source review.
4. **Deployment:** provision HTTPS, production WSGI server, PostgreSQL, backups and
   restore tests, centralized logs, rate limiting shared across workers and egress
   restrictions. Review dependency vulnerability reports before release; the manifest
   records the installed baseline and is not a clean vulnerability audit.
5. **Customer boundaries:** deploy separately for each organization. Shared SaaS needs
   explicit tenant ownership, query isolation, organization roles, invitation flows,
   audit retention and deletion policies. Current staff access is a shared trusted
   workspace, not granular enterprise authorization.
6. **Acceptance testing:** browser automation/visual inspection, real live source
   collection, mobile/accessibility checks, load tests and PostgreSQL/Gunicorn deployment
   tests were not run. No browser automation runtime was available in this workspace.
   Complete these against a staging deployment and representative customer workflows.

Do not promise accurate forecasts, autonomous fact-checking, unlimited source coverage,
or multi-tenant isolation in sales material for this version.
