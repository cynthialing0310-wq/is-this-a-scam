# Decisions log

Significant choices made while building the project: what we chose, the alternatives, and why.

---

## 2026-10-22 — Web framework: FastAPI

**Chose:** FastAPI, run with the Uvicorn server.

**Alternatives:** Flask, Django.

**Why:** FastAPI validates incoming data using type hints and Pydantic, the same library we'll use to validate the AI's JSON output, so the whole app uses one approach to validation. The slowest step in the app will be waiting on the Claude API, and FastAPI's async support lets the server handle other requests while it waits. It also generates interactive API docs at `/docs`. Django's database layer and admin panel would go unused, since our only database is a small feedback table. Flask would also have worked at this scale; the main gains are consistency and developer experience, not raw speed.

---

## 2026-10-22 — Project layout: `app/` package at the root

**Chose:** All application code in an `app/` folder, tests in a separate `tests/` folder, one module per job (web layer, rule checks, AI client, combining logic).

**Alternatives:** A flat layout (all files at the root); a `src/` layout.

**Why:** Separate modules keep the rule checks, the AI client and the web layer apart so each can be tested on its own. A flat layout gets messy once there are templates, prompts and eval scripts. The `src/` layout suits packaged libraries more than web apps, and the FastAPI docs use `app/` at the root.

---

## 2026-10-22 — Dependencies: pinned `requirements.txt`

**Chose:** A `requirements.txt` listing the packages we chose directly, each pinned to an exact version with `==`.

**Alternatives:** `pyproject.toml` (the newer standard, used by tools like `uv` and Poetry); `pip freeze` output, which pins every sub-package too.

**Why:** `requirements.txt` is simple, works on every hosting platform and in GitHub Actions, and is easy to explain. Listing only our direct choices keeps it readable. The trade-off is that sub-packages aren't pinned, so they could change slightly between installs. We may revisit this before deploying.

---

## 2026-10-22 — Deploy early, to Render

**Chose:** Deploy now with a landing page, before the checker is built, using Render's free tier. Render redeploys automatically on every push to `main`.

**Alternatives:** Deploy at the end (the original Milestone 8); Railway (trial credit only); Fly.io or Google Cloud Run (faster wake-up, but need a payment card and Docker); Hugging Face Spaces.

**Why:** I wanted a public link for my CV straight away. Deploying early also surfaces hosting problems while the app is still small, and every later improvement goes live with a push. Render was the simplest free option that connects directly to GitHub. The trade-off is that the free tier sleeps after about 15 minutes idle, so the first visit can take 30–60 seconds. We may revisit this if that puts off visitors.

---

## 2026-10-22 — Test client dependency: `httpx2` instead of `httpx`

**Chose:** `httpx2` for FastAPI's `TestClient`.

**Alternatives:** `httpx`, which still works.

**Why:** With `httpx`, the test run printed a deprecation warning from Starlette (the library FastAPI is built on) saying `httpx` support is deprecated and to install `httpx2`. Switching removed the warning, and the test still passes. `httpx2` is published by the original author of `httpx`.
