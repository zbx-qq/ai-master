# Changelog

All notable changes to this project are documented here.

## Public upload - 2026-07-11

### Security
- Removed real ChatGPT session cookies from the uploaded source.
- Removed hard-coded API keys and account passwords.
- Added `.env.example` and `cs.example.json`.
- Added `.gitignore` rules for local credentials and session files.
- Disabled the automated account-registration and session-token collection script in the public repository.

## 1.1.0 - 2025-10-23

### Added
- Cookie auto-normalization for `__Secure-` and `__Host-` prefixes.
- Optional cookie fields: `secure`, `httpOnly`, and `sameSite`.
- Centralized settings, rate limiting, task queues, response parsing, and browser resource management.

### Fixed
- Playwright cookie-field validation errors.
- Secure-cookie attribute handling.

## 1.0.0 - 2025-10-23

### Added
- FastAPI endpoints.
- Playwright browser automation.
- Async task processing.
- Structured logging and health checks.
