# Blitzy Project Guide — hot-stuff Documentation Task

> **Project:** `hot-stuff` — Billboard Hot 100 audio-feature analytics application
> **Task Type:** DOCUMENT CODE (documentation-only)
> **Branch:** `blitzy-47db5674-564a-4ebd-8fd4-b6c399ac3ba5` · **HEAD:** `2a0b902` · **Baseline (pre-doc):** `2fd0190`
> **Brand legend:** <span style="color:#5B39F3">**Completed / AI Work = Dark Blue (#5B39F3)**</span> · Remaining / Not Completed = White (#FFFFFF) · Headings/Accents = Violet-Black (#B23AF2) · Highlight = Mint (#A8FDD9)

---

## 1. Executive Summary

### 1.1 Project Overview

`hot-stuff` is a Billboard Hot 100 audio-feature analytics application: a Python/Flask backend serves a compiled React single-page app and a JSON API under one origin, backed by PostgreSQL. This engagement was a **documentation-only** task — add Google-style docstrings to the backend "server" modules and produce a comprehensive README (setup, API reference, deployment, inline explanations). The user's literal "add JSDoc to `server.js`" request was reconciled to the repository's actual Python/Flask backend, because no `server.js` exists. Target users are developers and operators onboarding to the app. Business impact: a former ~30-line README and a largely undocumented backend now carry complete, citation-backed documentation, shrinking onboarding time and clarifying architecture and data prerequisites.

### 1.2 Completion Status

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'pie1':'#5B39F3','pie2':'#FFFFFF','pieStrokeColor':'#B23AF2','pieStrokeWidth':'2px','pieOuterStrokeWidth':'2px','pieTitleTextSize':'18px','pieSectionTextSize':'15px','pieLegendTextSize':'15px'}}}%%
pie showData title Completion — 88.9% (32h of 36h)
    "Completed Work (h)" : 32
    "Remaining Work (h)" : 4
```

| Metric | Hours |
|--------|-------|
| **Total Hours** | **36** |
| **Completed Hours (AI + Manual)** | **32** (AI 32 + Manual 0) |
| **Remaining Hours** | **4** |
| **Percent Complete** | **88.9%** |

> Completion is measured strictly in **AAP-scoped + path-to-production hours** (PA1). **100% of the AAP documentation deliverables are complete and validated (zero defects).** The remaining 4 hours are exclusively human path-to-production work — assumption sign-off, PR review/merge, and optional hardening — which is why completion is capped below 100% per the "max 99% before human review" principle.

### 1.3 Key Accomplishments

- ✅ **Backend docstring coverage raised from 3/15 (20%) to 15/15 (100%)** — module docstrings on `app.py` and `api/__init__.py`, Google-style docstrings on all 6 route handlers, class docstrings on all 4 models/schemas, and expanded Google-style docstrings on the 3 helpers.
- ✅ **README expanded from ~30 lines / 1.5 KB to 447 lines / 36.5 KB** with all 13 planned sections (Overview → Deployment), preserving the original Billboard Hot 100 narrative.
- ✅ **Full API Reference for all 6 routes** (`/`, `/api/`, `/api/track/<id>`, `/api/week/<week>`, `/api/artist/<artist>`, `/api/analysis/<feature>`) with one `curl` example each.
- ✅ **Setup + Deployment guides** covering Docker Compose and local development, with the `NODE_OPTIONS=--openssl-legacy-provider` caveat and the external data-pipeline prerequisite.
- ✅ **4 Mermaid diagrams** (system-context, request-flow, ERD, deployment topology) render to valid SVG.
- ✅ **Mandated accuracy correction applied** — "3 year rolling average" → "5-year" to match `df.rolling(5)`; zero stale wording remains.
- ✅ **Documentation-only integrity proven** — docstring-stripped AST identical to baseline; `frontend/` untouched; all 5 modules compile clean on Python 3.11 and 3.13.
- ✅ **177 in-code `Source:` citations** (228 across the full validation audit) all resolve to in-bounds lines.

### 1.4 Critical Unresolved Issues

There are **no defects blocking release**. The items below are pending human decisions/sign-offs, not code failures.

| Issue | Impact | Owner | ETA |
|-------|--------|-------|-----|
| Interpretation assumptions A1–A4 await user confirmation (server.js→Python, JSDoc→docstrings, README-as-update, external data pipeline) | Low — interpretation is well-justified and documented in README "A note on scope"; only sign-off is pending | Product owner / requester | 1.5h |
| Documentation PR not yet peer-reviewed / merged | Low — standard path-to-production gate | Reviewing engineer | 1.5h |
| Frontend chart legend "3 Year Rolling Average" still contradicts corrected docs (`LineChart.js:L47`) | Low — cosmetic UI label; out of the documentation task's scope | Frontend engineer | 0.5h |

### 1.5 Access Issues

**No access issues identified.** The repository was fully accessible on branch `blitzy-47db5674-564a-4ebd-8fd4-b6c399ac3ba5` with a clean working tree; all 6 in-scope files, manifests, Docker definitions, and git history were readable, and no third-party credentials or external services were required for this documentation-only task.

| System/Resource | Type of Access | Issue Description | Resolution Status | Owner |
|-----------------|----------------|-------------------|-------------------|-------|
| Git repository (`hot-stuff`) | Read/Write | None | ✅ No issue | — |
| Backend source (`app.py`, `api/*.py`) | Read/Write | None | ✅ No issue | — |
| Toolchain (Python, Node, Docker, Git) | Execute | None (Docker Compose plugin absent on assessment host, but not required to validate a documentation task) | ✅ No issue | — |

### 1.6 Recommended Next Steps

1. **[High]** Confirm the flagged interpretation (server.js → Python/Flask backend; JSDoc → Google-style docstrings) by reviewing the README "A note on scope" section and the backend docstrings — or request the literal-JavaScript alternative. *(~1.5h)*
2. **[High]** Peer-review the documentation PR (6 files, 972 insertions / 19 deletions, doc-only) and merge to `main`; verify Mermaid renders on the Git host. *(~1.5h)*
3. **[Medium]** Apply the one-line frontend legend fix in `LineChart.js:L47` ("3 Year" → "5-Year Rolling Average") so the UI matches the corrected docs and code. *(~0.5h)*
4. **[Low]** Optionally add docstring linting (pydoclint 0.9.1 or Ruff `D` rules) to CI to prevent future documentation drift. *(~0.5h)*
5. **[Low]** Plan a **separate** production-hardening initiative (rotate DB credentials, switch to gunicorn, upgrade the EOL base image, restrict CORS, provision the data pipeline) — these are disclosed in the README but are out of this documentation task's scope.

---

## 2. Project Hours Breakdown

### 2.1 Completed Work Detail

<span style="color:#5B39F3">**All completed work below was delivered autonomously (AI) and validated. Total = 32 hours.**</span>

| Component | Hours | Description |
|-----------|-------|-------------|
| `app.py` + `api/__init__.py` module docs (R1) | 3 | Module docstrings for the entry point and Flask bootstrap (single-origin static serving, CORS, DB config, deliberate trailing-import rationale) + inline comments |
| `api/routes.py` docstrings (R1) | 5 | Module docstring + Google-style docstrings for all 6 handlers (Route / Args / Returns / Source) |
| `api/models.py` docstrings (R1) | 4 | Class docstrings for `Tracks`, `TrackSchema`, `YearlyAvg`, `YearlyAvgSchema`; every column/field documented; `Tracks.__init__` `spotify_id` omission documented (not changed) |
| `api/funcs.py` docstrings + inline (R1, R5) | 3 | 3 helper docstrings expanded to Google style; inline explanations of week normalization, `.rolling(5)`, and ×100 scaling; original summary wording preserved |
| README — Getting Started (R2) | 3 | Docker Compose + local dev setup (venv, `FLASK_APP`/`FLASK_ENV`, `npm` build), prerequisites, `NODE_OPTIONS` caveat |
| README — API Reference (R3) | 5 | All 6 routes with path params, `curl` requests, and JSON response shapes |
| README — Deployment (R4) | 3 | Docker image, Compose topology, ports, env vars, dev-server caveat, and a Production hardening disclosure |
| README — structural sections | 3 | Overview (preserved Billboard narrative), Features, Tech Stack, Project Structure, Configuration, Data Models, Data Pipeline |
| Architecture + 4 Mermaid diagrams | 2 | System-context, request-flow sequence, entity-relationship, and Compose deployment-topology diagrams |
| Accuracy correction + citations + QA | 1 | "5-year" rolling-average correction, 177 `Source:` citations, version verification, multi-round QA fixes |
| **Total Completed** | **32** | |

### 2.2 Remaining Work Detail

**All remaining work is human path-to-production. Total = 4 hours.**

| Category | Hours | Priority |
|----------|-------|----------|
| Confirm flagged interpretation assumptions A1–A4 (AAP defers these to the user) | 1.5 | High |
| Documentation PR peer review + merge to `main` | 1.5 | High |
| Frontend chart-legend fix decision/apply (`LineChart.js:L47`; out-of-scope source change) | 0.5 | Medium |
| Optional docstring-lint CI integration (pydoclint / Ruff `D` rules) | 0.5 | Low |
| **Total Remaining** | **4** | |

### 2.3 Hours Reconciliation

| Check | Value | Status |
|-------|-------|--------|
| Section 2.1 completed sum | 32h | ✅ |
| Section 2.2 remaining sum | 4h | ✅ |
| 2.1 + 2.2 = Section 1.2 Total | 32 + 4 = 36h | ✅ |
| Section 1.2 remaining = 2.2 sum = Section 7 pie remaining | 4h = 4h = 4h | ✅ |
| Completion = Completed / Total | 32 / 36 = 88.9% | ✅ |

---

## 3. Test Results

This is a **documentation-only** task; the repository contains **no unit/integration test suite** (confirmed by AAP §0.2.2 and repository scan). Accordingly, Blitzy's **autonomous validation gates** stand in for functional testing. Every entry below originates from Blitzy's autonomous validation logs for this project and was independently re-confirmed during this assessment.

| Test Category | Framework | Total | Passed | Failed | Coverage % | Notes |
|---------------|-----------|-------|--------|--------|-----------|-------|
| Compilation | `py_compile` (CPython 3.11.15 & 3.13.13) | 5 | 5 | 0 | 100% of modules | All 5 backend modules compile clean on both interpreters |
| Runtime import & route registration | Flask / Python import | 7 | 7 | 0 | — | `import api`/`import app` succeed; 6 API routes + static route register on `url_map` (7 rules) |
| Docstring coverage | AST probe | 15 | 15 | 0 | 100% | 15/15 AAP documentable units carry docstrings (baseline 3/15) |
| Documentation accuracy (citations) | Citation audit | 228 | 228 | 0 | — | All `Source: <path>:L<line>` citations resolve in-bounds (0 dangling) |
| Content assertions | Content audit | 31 | 31 | 0 | — | Version pins, ports, route shapes, schema field lists match source exactly |
| Diagram rendering | mermaid-cli (mmdc 11.16.0) | 4 | 4 | 0 | — | All README Mermaid diagrams render to valid SVG |
| Logic-change proof | Docstring-stripped AST diff | 5 | 5 | 0 | — | Each module's code AST identical to baseline `2fd0190` → zero logic change |
| **Total** | | **269** | **269** | **0** | **100%** | Zero failures across all autonomous validation gates |

> **Integrity note:** No unit/integration/E2E test suite exists for this project; the figures above are Blitzy autonomous **validation-gate** results (compilation, runtime import, coverage, citation accuracy, diagram rendering, and logic-change proof), not application unit tests. They are reported here because they are the authoritative automated evidence produced for this documentation task.

---

## 4. Runtime Validation & UI Verification

**Backend runtime (validated on a faithful CPython 3.11.15 container replica with exact pinned dependencies):**

- ✅ **Operational** — `import api` and `import app` succeed; the Flask `app` object constructs.
- ✅ **Operational** — All 6 API routes register on the URL map (`/`, `/api/`, `/api/track/<spotify_id>`, `/api/week/<week>`, `/api/artist/<artist>`, `/api/analysis/<feature>`); with the static route, 7 URL rules total.
- ✅ **Operational** — All docstrings are live (AST-attached) on the imported objects.
- ✅ **Operational** — All 5 modules compile under both Python 3.11 and 3.13.

**Documentation artifacts:**

- ✅ **Operational** — All 4 README Mermaid diagrams render to valid SVG (mmdc 11.16.0).
- ✅ **Operational** — 6 `curl` examples and 4 JSON response examples are structurally valid against handler/schema definitions.

**UI verification:**

- ⚠ **Partial (out of scope)** — The React frontend was **not** built or exercised in this documentation-only task; `frontend/` is untouched. A known pre-existing UI inconsistency remains: `LineChart.js:L47` shows "3 Year Rolling Average" while the code computes a 5-period mean — flagged for a follow-up source fix.

**End-to-end data flow:**

- ⚠ **Partial (external dependency)** — Full runtime behavior requires a **pre-populated PostgreSQL** produced by an external, out-of-repository weekly scraper + Spotipy pipeline. With an empty database, endpoints return empty result sets. This prerequisite is documented in the README "Data Pipeline" section.

---

## 5. Compliance & Quality Review

AAP deliverables mapped to Blitzy quality/compliance benchmarks. Fixes applied during autonomous validation are noted.

| AAP Deliverable | Benchmark | Status | Progress |
|-----------------|-----------|--------|----------|
| R1 — Backend docstrings (15 units) | Google-style, PEP 257 compliant | ✅ PASS | 15/15 (100%) |
| R2 — Comprehensive README setup | Docker + local, prerequisites, caveats | ✅ PASS | 100% |
| R3 — API documentation | All 6 routes: method, params, example req/resp | ✅ PASS | 6/6 (100%) |
| R4 — Deployment guide | Image, Compose topology, ports, env, caveats | ✅ PASS | 100% |
| R5 — Inline code explanations | Non-obvious logic annotated | ✅ PASS | 100% |
| Accuracy correction | "5-year" matches `df.rolling(5)` | ✅ PASS | 0 stale "3 year" |
| Source citations | `Source: <path>:<line>` per technical claim | ✅ PASS | 228/228 resolve |
| Documentation-only constraint | No source-logic changes | ✅ PASS | AST identical to baseline |
| `spotify_id` omission handling | Document, do not fix | ✅ PASS | Documented in class/inline |
| Diagram coverage | ≥ system-context + request-flow | ✅ PASS | 4 diagrams |
| README route coverage | 6/6 (incl. previously missing `/` and `/api/`) | ✅ PASS | 6/6 |

**Fixes applied during autonomous validation (QA cycles):** corrected stale Data Pipeline self-citations; corrected empty-database API behavior claim; fixed Getting Started operational accuracy; added the `/api/` redirect and root title to the API Reference; reworded schema docstrings to avoid overstating serialized field order; removed invented column units; added credential and production-hardening caveats.

**Outstanding compliance items:** human confirmation of interpretation assumptions A1–A4 (deferred to the user by design). No quality defects remain.

---

## 6. Risk Assessment

| Risk | Category | Severity | Probability | Mitigation | Status |
|------|----------|----------|-------------|-----------|--------|
| Documentation drift (docs stale if code changes) | Technical | Low | Medium | 177 inline `Source:` citations aid traceability; optional docstring-lint CI | Mitigated |
| Flask dev server in container (`CMD python3 app.py`; gunicorn pinned but unused) | Technical | Medium | High if deployed as-is | Documented in README dev-server caveat + Production hardening | Documented (fix out of scope) |
| EOL base image `python:3.11-slim-buster` (Debian 10 Buster, EOL 2024-06-30) | Technical | Medium | Medium | Disclosed in README Production hardening | Documented (fix out of scope) |
| Default DB credentials `postgres:postgres`; hardcoded `SQLALCHEMY_DATABASE_URI` | Security | High | High if deployed as-is | Documented as dev-only defaults; "replace before production" | Documented (human action) |
| Permissive CORS (`CORS(app)` — all origins) | Security | Medium | Medium | Disclosed in Production hardening | Documented |
| No auth / missing security headers | Security | Medium | Medium | Disclosed in Production hardening | Documented |
| External data-pipeline prerequisite; empty DB → empty responses | Operational | Medium | High | Documented as prerequisite (Data Pipeline / assumption A4); empty-DB behavior corrected | Documented |
| No health-check endpoint / monitoring | Operational | Low | Medium | Noted; remediation out of scope | Accepted |
| Unconfirmed interpretation assumptions A1–A4 (literal JS/JSDoc alternative) | Integration | Medium | Low | Interpretation explicitly documented + flagged (README "A note on scope") | Open (human) |
| Frontend "3 Year Rolling Average" legend contradicts corrected 5-year docs | Integration | Low | High | Flagged in README + AAP §0.8.2; 0.5h source fix out of doc scope | Open (flagged) |
| `start-api` npm script is POSIX-only (fails on Windows shells) | Integration | Low | Low | Documented; pre-existing script unchanged | Documented |

> The application security/infrastructure risks (dev server, EOL image, default credentials, permissive CORS, data prerequisite) are **surfaced by the documentation** as disclosures for the human team. Their remediation is source/infrastructure work explicitly outside this documentation task's scope; they do not reduce documentation completion.

---

## 7. Visual Project Status

### Project Hours Breakdown

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'pie1':'#5B39F3','pie2':'#FFFFFF','pieStrokeColor':'#B23AF2','pieStrokeWidth':'2px','pieOuterStrokeWidth':'2px','pieTitleTextSize':'18px','pieSectionTextSize':'15px','pieLegendTextSize':'15px'}}}%%
pie showData title Project Hours — Completed vs Remaining
    "Completed Work" : 32
    "Remaining Work" : 4
```

### Remaining Work by Priority (hours)

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'xyChart': {'plotColorPalette':'#5B39F3'}}}}%%
xychart-beta
    title "Remaining Hours by Priority"
    x-axis ["High", "Medium", "Low"]
    y-axis "Hours" 0 --> 4
    bar [3, 0.5, 0.5]
```

| Priority | Remaining Hours | Items |
|----------|-----------------|-------|
| High | 3.0 | Confirm assumptions (1.5) + PR review/merge (1.5) |
| Medium | 0.5 | Frontend legend fix |
| Low | 0.5 | Optional docstring-lint CI |
| **Total** | **4.0** | |

> **Integrity:** "Remaining Work" = **4h**, identical to Section 1.2 metrics and the Section 2.2 sum.

---

## 8. Summary & Recommendations

**Achievements.** The documentation task is **88.9% complete (32 of 36 hours)** and, critically, **100% of the AAP documentation deliverables are delivered and validated with zero defects.** Backend docstring coverage went from 20% to 100% across all 15 units; the README grew from ~30 lines to a comprehensive 447-line, 13-section document with a full 6-route API reference, setup and deployment guides, 4 Mermaid diagrams, and 177 source citations. The mandated "5-year rolling average" correction is applied, and documentation-only integrity is proven (docstring-stripped AST identical to baseline; `frontend/` untouched).

**Remaining gaps.** The 4 remaining hours are exclusively **human path-to-production** activities: confirming the flagged interpretation assumptions the AAP intentionally deferred to the user (1.5h), peer-reviewing and merging the documentation PR (1.5h), an optional one-line frontend legend fix (0.5h), and optionally wiring docstring linting into CI (0.5h).

**Critical path to production.** (1) Confirm interpretation → (2) review & merge the PR. These two High-priority items (3h combined) are the only steps required to consider the documentation itself production-ready and released.

**Success metrics.** 15/15 docstring coverage · 6/6 routes documented · 13/13 README sections · 269/269 autonomous validation checks passing · 0 stale accuracy defects · 0 source-logic changes.

**Production readiness assessment.** The **documentation deliverable is production-ready.** The **underlying application** is not — the README responsibly discloses several hardening items (default credentials, Flask dev server, EOL base image, permissive CORS, external data prerequisite). These are out of this documentation task's scope and should be addressed as a separate, explicitly-estimated hardening initiative before any production deployment of the app.

---

## 9. Development Guide

> Commands are drawn from the delivered, validated README. Commands directly executed on the assessment host are marked ✅ verified.

### 9.1 System Prerequisites

- **Recommended path:** Docker Engine (✅ verified: Docker 29.6.1) + Docker Compose v2 (`docker compose`) or v1 (`docker-compose`).
- **Local path:** Python **3.11** (matches the container; the code also compiles on 3.13 ✅) and Node.js with npm (✅ verified: node v22.23.1 / npm 10.9.8) for building the React SPA.
- **Git** (✅ verified: git 2.55.0).
- **Data prerequisite:** a **pre-populated PostgreSQL** database produced by the external weekly scraper + Spotipy pipeline (out of repository). With an empty DB, API responses are empty.

### 9.2 Environment Setup

Environment variables (documented in the README Configuration section):

```bash
# Backend (from .flaskenv)
FLASK_APP=app.py
FLASK_ENV=development

# Database URI used by the app (host segment "postgres" = Compose service name)
SQLALCHEMY_DATABASE_URI=postgresql://postgres:postgres@postgres/db

# PostgreSQL container (docker-compose.yml) — DEV DEFAULTS; replace for production
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=db

# Frontend build workaround for react-scripts 4.0.3 on modern Node
NODE_OPTIONS=--openssl-legacy-provider   # Windows: set NODE_OPTIONS=--openssl-legacy-provider
```

### 9.3 Dependency Installation

```bash
# Backend (from repository root)
python3 -m venv venv            # Windows: python -m venv venv   (or: py -3.11 -m venv venv)
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
```

### 9.4 Application Startup

**Option A — Docker Compose (recommended):**

```bash
# Docker Compose v2 (note the space):
docker compose up
# ...or where only the deprecated standalone v1 binary exists:
docker-compose up
# App: http://localhost:80   PostgreSQL: localhost:5432
```

**Option B — Local development:**

```bash
# Build the SPA that Flask serves from frontend/build
cd frontend && npm run build && cd ..

# Run the backend (uses .flaskenv), or run the entry point directly
flask run                       # http://127.0.0.1:5000
# ...or
python3 app.py                  # binds 0.0.0.0:5000

# Alternatively, run the CRA dev server (proxies API calls to :5000)
cd frontend && npm start
```

### 9.5 Verification Steps

```bash
# 1) Documentation-only integrity gate — all backend modules compile (✅ verified: EXIT 0)
python -m py_compile app.py api/__init__.py api/routes.py api/models.py api/funcs.py

# 2) App reachability (React SPA at root)
curl http://localhost/

# 3) API smoke checks
curl http://localhost/api/                              # 302 redirect to current chart week
curl http://localhost/api/week/2023-01-07               # week payload: {week, songs, averages, avgTempo}
curl http://localhost/api/analysis/energy               # {feature, data:[{year, value, rolling}]}
```

### 9.6 Example Usage

```bash
# Tracks for one Spotify ID (ordered by rank)
curl http://localhost/api/track/0VjIjW4GlUZAMYd2vXMi3b

# Case-insensitive artist search (newest chart week first)
curl http://localhost/api/artist/drake

# Yearly mean + 5-period rolling average for an audio feature
curl http://localhost/api/analysis/danceability
```

### 9.7 Troubleshooting

- **`error:0308010C:digital envelope routines::unsupported` during `npm run build`** → set `NODE_OPTIONS=--openssl-legacy-provider` (required by react-scripts 4.0.3 on modern Node). Windows: `set NODE_OPTIONS=--openssl-legacy-provider`.
- **Empty API responses** → the database is not populated. hot-stuff expects a pre-populated PostgreSQL from the external scraper + Spotipy pipeline (out of repository).
- **`npm run start-api` fails on Windows** → this script is POSIX-only (`cd .. && venv/bin/flask run ...`); run `flask run` from the repository root instead.
- **Port 80 already in use** (Docker) → change the host port mapping in `docker-compose.yml` (`"80:5000"` → e.g. `"8080:5000"`).
- **`docker compose` "unknown command"** → your Docker install lacks the Compose v2 plugin; use the standalone `docker-compose up` (v1) instead.

---

## 10. Appendices

### Appendix A — Command Reference

| Command | Purpose |
|---------|---------|
| `docker compose up` / `docker-compose up` | Build and start api + postgres |
| `python3 -m venv venv` | Create local virtual environment |
| `pip install -r requirements.txt` | Install backend dependencies |
| `flask run` | Run backend via `.flaskenv` settings |
| `python3 app.py` | Run backend entry point (binds 0.0.0.0:5000) |
| `npm install` / `npm run build` | Install / build the React SPA |
| `npm start` | CRA dev server (proxies to :5000) |
| `python -m py_compile app.py api/*.py` | Documentation-only integrity gate |

### Appendix B — Port Reference

| Port | Service | Source |
|------|---------|--------|
| 80 (host) → 5000 (container) | Flask app (SPA + API) | `docker-compose.yml` / `Dockerfile EXPOSE 5000` |
| 5000 | Flask dev server (local, direct) | `app.py` (`app.run(host='0.0.0.0')`) |
| 5432 | PostgreSQL | `docker-compose.yml` |

### Appendix C — Key File Locations

| Path | Role |
|------|------|
| `app.py` | Backend entry point (module docstring added) |
| `api/__init__.py` | Flask bootstrap: app, CORS, DB, extensions (module docstring added) |
| `api/routes.py` | 6 HTTP route handlers (module + handler docstrings added) |
| `api/models.py` | ORM models + Marshmallow schemas (class docstrings added) |
| `api/funcs.py` | Helpers: week normalization, rolling average, weekly aggregation |
| `README.md` | Comprehensive 13-section project documentation |
| `requirements.txt` / `Dockerfile` / `docker-compose.yml` / `.flaskenv` | Runtime, image, topology, and Flask env configuration |
| `frontend/src/components/trends/LineChart.js` | React chart (contains the flagged "3 Year" legend at L47) |

### Appendix D — Technology Versions

| Component | Version | Source |
|-----------|---------|--------|
| Python (runtime) | 3.11-slim-buster | `Dockerfile` |
| PostgreSQL (container) | 15 | `docker-compose.yml` |
| Flask | 2.0.1 | `requirements.txt` |
| Flask-Cors | 3.0.10 | `requirements.txt` |
| flask-marshmallow | 0.14.0 | `requirements.txt` |
| Flask-SQLAlchemy | 2.5.1 | `requirements.txt` |
| marshmallow / marshmallow-sqlalchemy | 3.12.1 / 0.26.1 | `requirements.txt` |
| SQLAlchemy | 1.4.19 | `requirements.txt` |
| numpy / pandas | 1.24.2 / 2.0.0 | `requirements.txt` |
| psycopg2 / psycopg2-binary | 2.9.6 / 2.9.5 | `requirements.txt` |
| gunicorn | 20.1.0 (pinned, unused by container `CMD`) | `requirements.txt` |
| Werkzeug | 2.2.3 | `requirements.txt` |
| react / react-dom | 17.0.2 | `frontend/package.json` |
| react-scripts | 4.0.3 (needs `NODE_OPTIONS=--openssl-legacy-provider`) | `frontend/package.json` |
| @amcharts/amcharts4 | 4.10.19 | `frontend/package.json` |
| styled-components | 5.3.0 | `frontend/package.json` |

### Appendix E — Environment Variable Reference

| Variable | Example / Default | Purpose |
|----------|-------------------|---------|
| `FLASK_APP` | `app.py` | Flask entry point (`.flaskenv`) |
| `FLASK_ENV` | `development` | Flask environment (`.flaskenv`) |
| `SQLALCHEMY_DATABASE_URI` | `postgresql://postgres:postgres@postgres/db` | DB connection (host = Compose service name) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `postgres` / `postgres` / `db` | PostgreSQL container config (dev-only defaults) |
| `NODE_OPTIONS` | `--openssl-legacy-provider` | Frontend build workaround for react-scripts 4.0.3 |

### Appendix F — Developer Tools Guide (optional, per AAP §0.6.1)

| Tool | Version | Purpose | Note |
|------|---------|---------|------|
| pydoclint | 0.9.1 | Verify `Args`/`Returns`/`Raises` match signatures | Maintained docstring linter (Python 3.8+) |
| pydocstyle | 6.3.0 | PEP 257 style checks | **Final release; deprecated** — prefer Ruff `D` rules |
| Sphinx | 8.x (e.g. 8.3.0) | Generate HTML API docs via `sphinx.ext.napoleon` | Pin 8.x for Python 3.11 (Sphinx 9.x needs Python ≥ 3.12) |
| mermaid-cli (mmdc) | 11.16.0 | Validate/render README Mermaid diagrams | Used in autonomous validation |

> None of these are required by the task; they are optional aids for a team that later wants enforced docstring conventions or generated HTML docs. No new runtime dependencies are introduced.

### Appendix G — Glossary

| Term | Definition |
|------|------------|
| Audio feature | A Spotify-derived numeric attribute of a track (energy, danceability, valence, tempo, etc.) |
| Chart week | A Billboard Hot 100 week, normalized to its Saturday date |
| Rolling average | The 5-period rolling mean of a yearly audio-feature series (`df.rolling(5).mean()`) |
| Single-origin design | One Flask process serves both the compiled React SPA (`/`) and the JSON API (`/api/*`) |
| Google-style docstring | PEP 257-compliant docstring with structured `Args:` / `Returns:` / `Raises:` sections |
| AAP | Agent Action Plan — the governing project specification |