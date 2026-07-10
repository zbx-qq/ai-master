# TODO

## Core stability

- Reconcile the `crawler()` function signature across API, queue, and scheduler callers.
- Add explicit validation when `API_BASE_URL` or `API_KEY` is missing.
- Remove unused imports and duplicated scheduler implementations.
- Prevent request middleware from logging sensitive request bodies.

## Testing

- Replace manual browser scripts with isolated tests against an authorized test site.
- Add unit tests for cookie normalization, SSE parsing, rate limiting, and task states.
- Add integration tests for the FastAPI endpoints.

## Deployment

- Add a production Dockerfile.
- Add CI checks for Python compilation, Ruff, and secret scanning.
- Restrict CORS origins in production.
- Add authentication and HTTPS enforcement.

## Observability

- Add structured JSON logs and metrics.
- Add browser/session cleanup monitoring.
- Add persistent task storage where required.
