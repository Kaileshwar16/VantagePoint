# VantagePoint frontend

See [the project README](../README.md) for setup, authentication, data reliability,
production configuration and validation instructions.

```bash
npm ci
npm run dev
npm run lint
npm run build
```

The local dev server proxies `/api` to Django at `127.0.0.1:8000`. Production requires
an HTTPS same-origin reverse proxy and SPA fallback for frontend routes.
