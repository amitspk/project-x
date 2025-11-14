# FYI Widget Admin UI

A lightweight control panel for the FYI Widget platform, giving administrators a visual way to manage publishers, monitor the worker queue, rotate API keys, and remove test content without touching raw endpoints.

## Getting started

```bash
cd fyi_widget_admin_ui
npm install
npm run dev
```

By default the app points to `http://127.0.0.1:8005`. Adjust the base URL and admin key from the **Settings** page after the UI loads.

## Docker

```bash
# from the repository root
docker build -t fyi-widget-admin-ui -f fyi_widget_admin_ui/Dockerfile .
docker run -p 5174:5173 fyi-widget-admin-ui
```

Or use the provided compose file for dev:

```bash
cd SelfLearning
docker compose -f deployment/dev/docker-compose.admin-ui.yml up --build -d
```

For production there is a compose file that pulls the published image:

```bash
cd SelfLearning
docker compose -f deployment/prod/docker-compose.admin-ui.yml up -d
```

Set the load-balanced API endpoint (served via Nginx) before starting prod:

```
ADMIN_UI_API_BASE_URL=https://your-nginx-api.example.com
```

### Building a production image for Docker Hub

Because esbuild can panic when cross-compiling under QEMU on Apple Silicon, build the static bundle locally first, then package it with the lightweight release Dockerfile:

```bash
cd SelfLearning/fyi_widget_admin_ui
npm ci
npm run build
docker buildx build --platform linux/amd64 -t docker.io/amit11081994/fyi-widget-admin-ui:latest -f Dockerfile.release . --push
```

The release Dockerfile expects `dist/` to be present and only copies it into an nginx image, so cross-building succeeds cleanly.

## Key features

- **Dashboard** – quick queue snapshot and common task reminders.
- **Publishers** – onboard, filter, edit config (including `max_total_blogs` and `whitelisted_blog_urls`), reactivate, or rotate API keys.
- **Jobs & Queue** – live stats, job lookup, and cancellation tools.
- **Content cleanup** – irreversible deletion of a blog and all generated content.
- **Settings** – client-side storage for API base URL and admin key.

All API calls use the existing admin endpoints (`X-Admin-Key`). Secrets never leave the browser.
