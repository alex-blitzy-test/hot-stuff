# Blitzy Project Guide — hot-stuff Documentation

> **Project:** `hot-stuff` — Billboard Hot 100 audio-feature analytics application
> **Branch:** `blitzy-47db5674-564a-4ebd-8fd4-b6c399ac3ba5` · **HEAD:** `97cbb9b` · **Base:** `origin/main` (`2fd0190`)
> **Task type:** Documentation-only (DOCUMENT CODE) · **Source-logic changes:** none

---

## 1. Executive Summary

### 1.1 Project Overview

`hot-stuff` is a Billboard Hot 100 audio-feature analytics application: a single Flask process serves a compiled React single-page app at `/` and a JSON API under `/api/*`, backed by PostgreSQL 15 and populated by an external weekly scraper + Spotipy enrichment pipeline. This project delivers **comprehensive documentation** for that application — Google-style Python docstrings across the backend "server" modules plus a comprehensive, multi-section `README.md` covering setup, API reference, data models, architecture, and deployment. The work targets developers onboarding to or operating the app. It is **documentation-only**: no application behavior, signatures, dependencies, or infrastructure were modified.

### 1.2 Completion Status

```mermaid
%%{init: {'theme':'base','themeVariables':{'pie1':'#5B39F3','pie2':'#FFFFFF','pieStrokeColor':'#B23AF2','pieOuterStrokeColor':'#B23AF2','pieStrokeWidth':'2px','pieSectionTextColor':'#000000','pieTitleTextSize':'17px'}}}%%
pie showData
    title Overall Completion — 85.3% (29h of 34h)
    "Completed Work (AI)" : 29
    "Remaining Work" : 5
```

| Metric | Hours |
|--------|-------|
| **Total Hours** | **34.0** |
| Completed Hours (AI + Manual) | 29.0 (AI 29.0 + Manual 0.0) |
| Remaining Hours | 5.0 |
| **Percent Complete** | **85.3%** |

> Completion is computed per the AAP-scoped, hours-based methodology: `29 / (29 + 5) = 85.3%`. Every AAP-scoped documentation deliverable is 100% delivered and validated; the remaining 5 hours are genuine human-in-the-loop path-to-production work (interpretation confirmation, review/merge, product-label reconciliation).

### 1.3 Key Accomplishments

- ✅ **Backend docstrings — 15/15 documentable units (100%)**: module docstrings for `app.py` and `api/__init__.py`; Google-style docstrings for all 6 route handlers; class docstrings for all 4 model/schema classes; and the 3 helpers expanded to Google style.
- ✅ **Comprehensive README — 13/13 target sections**: expanded from ~30 lines to 419 lines / ~38 KB while preserving the original Billboard Hot 100 narrative.
- ✅ **API Reference — 6/6 routes** documented with method, path parameters, a `curl` example, and a JSON response shape.
- ✅ **4 Mermaid diagrams** (system-context, request-flow sequence, entity-relationship, deployment topology) — exceeds the AAP minimum of 2.
- ✅ **Accuracy correction**: the erroneous "3 year rolling average" wording replaced with the authoritative **5-year** value (matching `df[feature].rolling(5).mean()`); zero stale references remain in scope.
- ✅ **150+ line-anchored `Source:<path>:<line>` citations** for traceability across the six files.
- ✅ **Zero source-logic changes** — verified: the six files are byte-identical to HEAD and `py_compile` passes.

### 1.4 Critical Unresolved Issues

| Issue | Impact | Owner | ETA |
|-------|--------|-------|-----|
| Interpretation of "server.js" / "JSDoc" is unconfirmed | Scope-defining: if literal JavaScript was intended, deliverables target the wrong surface | Requester / Reviewer | Before merge (≈2h) |
| Frontend chart legend still reads "3 Year Rolling Average" | Product/doc inconsistency vs the corrected 5-year value (out-of-scope React source change) | Frontend developer | Post-merge (≈1h) |

> No issue blocks the documentation itself — all deliverables compile, are accurate against live execution, and are committed. Both items require human decisions, not agent rework.

### 1.5 Access Issues

| System/Resource | Type of Access | Issue Description | Resolution Status | Owner |
|-----------------|----------------|-------------------|-------------------|-------|
| GitHub repository | Read/Write (branch push) | None — branch and 12 `docs:` commits are present and pushed | ✅ Resolved | Blitzy |
| PostgreSQL data | Runtime data | End-to-end HTTP verification needs a pre-populated DB from the external (out-of-repo) scraper/Spotipy pipeline; not required for a documentation task | ⚠ Not required for this task | Data pipeline owner |

> No access issues prevent build validation, review, or merge of this documentation change.

### 1.6 Recommended Next Steps

1. **[High]** Confirm the reinterpretation of "server.js → Python/Flask backend" and "JSDoc → Google-style docstrings" (assumptions A1–A4) with the requester.
2. **[Medium]** Perform a technical spot-check of the documentation (API examples, model fields, versions, diagrams) and merge the PR.
3. **[Low]** Reconcile the frontend `LineChart.js` "3 Year Rolling Average" legend with the corrected 5-year value.
4. **[Low]** (Optional) Adopt docstring linting (pydoclint / Ruff `D` rules) or generate Sphinx HTML docs.
5. **[Low]** (Optional) Apply the production hardening the README documents (WSGI server, disable debug, externalize credentials, restrict CORS).

---

## 2. Project Hours Breakdown

### 2.1 Completed Work Detail

| Component | Hours | Description |
|-----------|-------|-------------|
| Backend module docstrings — `app.py`, `api/__init__.py` | 1.5 | Entry-point + Flask-bootstrap module docstrings; single-origin, CORS, DB config, run/deploy notes |
| Route handler docstrings — `api/routes.py` | 3.0 | Google-style docstrings for all 6 handlers + module docstring (route, method, params, return shape) |
| Model/schema class docstrings — `api/models.py` | 2.5 | Class docstrings for `Tracks`, `TrackSchema`, `YearlyAvg`, `YearlyAvgSchema`; ~24 columns/fields + `spotify_id`-omission note |
| Helper docstrings + inline explanations — `api/funcs.py` | 2.0 | 3 helpers expanded to Google style; inline comments for week normalization, `.rolling(5)`, ×100 scaling |
| README — Overview, Features, Tech Stack, Project Structure, ToC | 2.5 | Narrative preserved + versioned stack + annotated file tree + table of contents |
| README — Getting Started (Docker + local + Windows caveats) | 2.5 | Docker Compose path, venv/local path, `NODE_OPTIONS` caveat, Windows portability notes |
| README — API Reference (6 routes + curl + JSON + 5-year fix) | 3.5 | Full reference for all endpoints with examples; rolling-average correction |
| README — Data Models + Configuration | 2.0 | `Tracks`/`YearlyAvg` field tables, schema field lists, environment-variable reference tables |
| README — Deployment + Data Pipeline | 2.0 | Docker image, Compose topology/ports, dev-server + debug-mode security posture, external-pipeline prerequisite |
| Architecture + 4 Mermaid diagrams | 2.5 | System-context, request-flow sequence, entity-relationship, deployment-topology diagrams |
| Source citations (150+, line-anchored) | 2.0 | `Source:<path>:<line>` references verified in-range across the six files |
| Code-review & QA remediation (12 commits) | 3.0 | Iterative CR/QA cycles: citation accuracy, invented-unit removal, schema-reuse claim, assumptions, credentials, SPA title, Windows caveats, debug-mode security |
| **Total Completed** | **29.0** | |

> **Validation:** the Hours column sums to **29.0**, matching Completed Hours in Section 1.2.

### 2.2 Remaining Work Detail

| Category | Hours | Priority |
|----------|-------|----------|
| Confirm interpretation assumptions A1–A4 (server.js→Python; JSDoc→docstrings; README=UPDATE; external pipeline=prerequisite) | 2.0 | High |
| Documentation technical review + PR review/merge | 2.0 | Medium |
| Reconcile frontend "3 Year Rolling Average" legend with the corrected 5-year value | 1.0 | Low |
| **Total Remaining** | **5.0** | |

> **Validation:** the Hours column sums to **5.0**, matching Remaining Hours in Section 1.2 and the "Remaining Work" value in the Section 7 pie chart. Section 2.1 (29.0) + Section 2.2 (5.0) = **34.0** = Total Project Hours.

### 2.3 Basis of Estimate & Confidence

- **Completed (29.0h) — High confidence.** Anchored to direct evidence: 886 inserted documentation lines across 6 files, 12 attributable commits, AST-verified docstring coverage, and validated citations/diagrams/examples.
- **Remaining (5.0h) — Medium confidence.** Human review/confirmation effort is inherently approximate; the estimate assumes the interpretation is confirmed (no re-scope). No test-rework hours apply — the project has no test suite by design (AAP §0.9).
- **Optional enhancements** (docstring linting, Sphinx, production hardening) are explicitly out of AAP scope and carry **0 hours** in the totals; they appear only as recommendations.

---

## 3. Test Results

This is a documentation task; the repository has **no automated test suite** by design (AAP §0.9 — no test run is required for a documentation-only change). Accordingly, the results below are the **behavioral, structural, and compilation verifications executed by Blitzy's autonomous validation systems** (Python 3.11.9 venv = the Docker runtime target), which stand in for a test suite.

| Test Category | Framework / Method | Total | Passed | Failed | Coverage % | Notes |
|---------------|--------------------|-------|--------|--------|-----------|-------|
| Compilation | `py_compile` / `compileall` | 5 | 5 | 0 | 100% of backend files | All 5 `.py` files exit 0 (independently re-confirmed on host Python 3.13.13) |
| Runtime import & route registration | Flask app import + `url_map` | 1 | 1 | 0 | n/a | `from api import app` loads cleanly; registers **exactly** the 6 documented routes, zero extras |
| Behavioral verification (helpers) | Manual execution of `api/funcs.py` | 3 | 3 | 0 | 3/3 helpers | `get_rolling_avg` → 5-period window; `get_weekly_data` → ×100 int scaling; `get_query_week` → Saturday normalization — all match docs |
| Docstring coverage | Python `ast` | 15 | 15 | 0 | 100% of AAP units | 2 module + 6 handler + 4 class + 3 helper units documented |
| Source-citation resolution | Custom in-range validator | 206 | 206 | 0 | 100% | All `Source:<path>:<line>` references resolve in-range (independent re-count corroborates pervasive line-accurate citations) |
| Encoding validation | UTF-8 check | 6 | 6 | 0 | 100% | All 6 in-scope files valid UTF-8; 0 replacement chars / mojibake |
| Lint (documentation content) | `ruff` 0.15.21 (no-fix) | — | Pass | 0 | n/a | `E501` line-length clean; doc edits introduced no new findings |

> **Integrity note:** every row above originates from Blitzy's autonomous validation logs for this project. There are **no fabricated tests**; where a conventional unit/integration suite would appear, none exists because the project ships without one.

---

## 4. Runtime Validation & UI Verification

- ✅ **Backend import** — `from api import app` initializes Flask + SQLAlchemy + Marshmallow with no database connection required at import time (single-origin bootstrap executes cleanly).
- ✅ **Route surface** — `app.url_map` registers exactly the six documented GET routes: `/`, `/api/`, `/api/track/<spotify_id>`, `/api/week/<week>`, `/api/artist/<artist>`, `/api/analysis/<feature>`.
- ✅ **Static SPA serving** — `frontend/build/` is present (`index.html`, `static/`, `asset-manifest.json`, `manifest.json`, `favicon.ico`); Flask serves it at `/` via `static_url_path='/'`.
- ✅ **Compilation** — `py_compile` passes on all backend modules.
- ⚠ **End-to-end HTTP responses** — `Partial`: full request/response validation requires a **pre-populated PostgreSQL** loaded by the external (out-of-repo) scraper/Spotipy pipeline (AAP prerequisite A4). This is expected and documented; it is not a defect of this task.
- ⚠ **Frontend chart legend** — `Partial`: the React `LineChart.js` legend still displays "3 Year Rolling Average," which is inconsistent with the backend's 5-period computation and the corrected documentation. Flagged for a post-merge fix (out-of-scope source change).
- ✅ **No runtime regression** — the change is documentation-only; the six files are byte-identical to HEAD and behavior is unchanged.

---

## 5. Compliance & Quality Review

| AAP Deliverable / Benchmark | Target | Result | Status |
|-----------------------------|--------|--------|--------|
| R1 — Backend docstrings | 15/15 units, Google style | 15/15; `Args:`/`Returns:` present | ✅ Pass |
| R2 — README setup instructions | Docker + local + prerequisites | Getting Started with all paths + `NODE_OPTIONS` + Windows caveats | ✅ Pass |
| R3 — API documentation | 6/6 routes + examples + accuracy fix | 6 routes, 6 curl + JSON; "3 year" → "5-year" corrected | ✅ Pass |
| R4 — Deployment guide | Image, Compose, ports, env, caveats | Deployment + Production considerations + Configuration | ✅ Pass |
| R5 — Inline code explanations | Non-obvious logic explained | Week normalization, `.rolling(5)`, ×100 scaling, `spotify_id` note | ✅ Pass |
| README section coverage | 13/13 sections | 13/13 `##` sections present | ✅ Pass |
| Diagrams | ≥ 2 Mermaid | 4 well-formed Mermaid diagrams | ✅ Pass |
| Citation traceability | `Source:` per technical claim | 150+ line-anchored citations, in-range | ✅ Pass |
| Documentation-only constraint (§0.8.2) | Zero source-logic changes | Behavior diff empty; files byte-identical to HEAD | ✅ Pass |
| Minimal-change / preserve narrative (§0.1.2) | Preserve + expand README | Original Billboard narrative retained | ✅ Pass |

**Fixes applied during autonomous CR/QA validation:** corrected source-citation line accuracy, removed invented units, fixed a schema-reuse claim, documented interpretation assumptions and hardcoded credentials, corrected the SPA title, added Windows portability caveats, and documented the debug-mode/interactive-debugger security posture.

**Outstanding (by design, not defects):** 2 inner Marshmallow `Meta` config classes and `Tracks.__init__` are intentionally left without their own docstrings (the `__init__` `spotify_id` omission is documented in the class docstring). 36 optional Ruff `D` docstring findings and 4 pre-existing source `F/E` findings are **not** fixed — source changes are out of scope (§0.8.2); the trailing side-effect import in `api/__init__.py` is intentional and documented.

---

## 6. Risk Assessment

| Risk | Category | Severity | Probability | Mitigation | Status |
|------|----------|----------|-------------|------------|--------|
| Unconfirmed interpretation of "server.js"/"JSDoc" (A1–A4) | Integration | High | Low–Med | Human confirmation before merge (task H1); interpretation is the only viable reading | Open |
| Hardcoded DB credentials (`postgres:postgres`) | Security | High | High (if deployed as-is) | Documented in README; externalize to secrets/env for prod | Documented |
| Flask dev server + debug mode (`gunicorn` pinned but unused) | Security | High | High (if deployed as-is) | README "Production considerations" documents it; switch to WSGI + disable debug | Documented |
| Permissive CORS (`CORS(app)` allows all origins) | Security | Medium | Medium | Documented; restrict origins for prod | Documented |
| External data-pipeline prerequisite (empty DB → empty/errored responses) | Operational | Medium | High (fresh setup) | Documented as a prerequisite in README | Documented |
| Documentation drift over time (no automated doc-sync gate) | Technical | Low–Med | Medium | 150+ line-anchored citations aid re-verification; optional lint in CI | Open (optional) |
| Frontend legend mismatch ("3 Year" vs 5-year) | Integration | Low | Present | Post-merge React fix (task L1) | Flagged |
| Citation line-number drift if source moves | Technical | Low | Low–Med | Validated in-range at delivery; re-verify on source edits | Mitigated |
| Pre-existing source lint findings (unused import, f-string, etc.) | Technical | Low | N/A (pre-existing) | Address in a separate source-change task | Accepted |
| No health-check endpoint / monitoring | Operational | Low | Low | Future operational enhancement | Open (out of scope) |

> **Risk headline:** No high-severity risk is attributable to the documentation change itself. The High-severity items are either pre-existing product characteristics the documentation now correctly **surfaces** (credentials, dev server) or a human confirmation gate the AAP deliberately raised (interpretation). Overall risk posture for merging these docs: **Low**.

---

## 7. Visual Project Status

**Project hours — completed vs remaining** (Completed = Dark Blue `#5B39F3`, Remaining = White `#FFFFFF`):

```mermaid
%%{init: {'theme':'base','themeVariables':{'pie1':'#5B39F3','pie2':'#FFFFFF','pieStrokeColor':'#B23AF2','pieOuterStrokeColor':'#B23AF2','pieStrokeWidth':'2px','pieSectionTextColor':'#000000','pieTitleTextSize':'16px'}}}%%
pie showData
    title Project Hours Breakdown
    "Completed Work" : 29
    "Remaining Work" : 5
```

**Remaining work by priority (hours):**

| Priority | Hours | Tasks |
|----------|-------|-------|
| High | 2.0 | Confirm interpretation A1–A4 |
| Medium | 2.0 | Documentation review + PR merge |
| Low | 1.0 | Reconcile frontend legend |
| **Total** | **5.0** | |

```mermaid
%%{init: {'theme':'base','themeVariables':{'pie1':'#5B39F3','pie2':'#B23AF2','pie3':'#A8FDD9','pieStrokeColor':'#333333','pieStrokeWidth':'1px','pieSectionTextColor':'#000000','pieTitleTextSize':'15px'}}}%%
pie showData
    title Remaining Hours by Priority
    "High" : 2
    "Medium" : 2
    "Low" : 1
```

> **Integrity:** "Remaining Work" = **5** here equals Remaining Hours in Section 1.2 and the sum of the Section 2.2 Hours column. "Completed Work" = **29** equals Completed Hours in Section 1.2.

---

## 8. Summary & Recommendations

**Achievements.** The project delivers a complete, accurate documentation set for `hot-stuff`: Google-style docstrings across 15/15 backend documentable units, a 13-section README with 4 Mermaid diagrams, a 6/6-route API reference with worked `curl` examples, data-model and configuration references, a deployment guide, and 150+ line-anchored source citations. The documentation was validated against live code execution (helper behavior, route registration, compilation) and corrects a material inaccuracy (the rolling-average window is **5** periods, not 3).

**Remaining gaps.** The project is **85.3% complete**. The remaining 5 hours are entirely human-in-the-loop: (1) confirming that the reinterpretation of "server.js/JSDoc" into the Python backend + docstrings matches intent; (2) a technical review and PR merge; and (3) reconciling the frontend chart legend for product/documentation consistency. There are **no agent-fixable code defects outstanding**.

**Critical path to production.** Confirm interpretation → review & merge the PR → (post-merge) reconcile the UI legend. If a team later chooses to enforce docstring conventions or publish HTML docs, adopt Ruff `D` rules / pydoclint or Sphinx 8.x (Python-3.11-compatible) — optional and out of the current scope.

**Success metrics (all met):** 15/15 docstring units · 6/6 API routes · 13/13 README sections · 4 diagrams (≥2 required) · 0 stale "3 year" references · `py_compile` EXIT 0 · 0 source-logic changes.

**Production readiness.** The **documentation deliverable** is production-ready pending human confirmation and merge. The **underlying application** is not production-hardened as shipped (dev server, debug mode, hardcoded credentials, permissive CORS) — these are pre-existing characteristics the documentation now transparently describes, with remediation guidance, but does not change.

| Assessment | Verdict |
|------------|---------|
| AAP-scoped deliverable completion | 100% delivered & validated |
| Overall project completion (incl. path-to-production) | 85.3% |
| Documentation ready to merge? | Yes, after interpretation confirmation |
| Blocking defects | None |

---

## 9. Development Guide

> Documentation-only change — no build or server start is required to review it. The steps below run and verify the underlying application.

### 9.1 System Prerequisites

- **Path A (recommended):** Docker Engine + Docker Compose.
- **Path B (local):** Python **3.11** (Docker target) and Node.js **20** + npm.
- **Both paths:** a **pre-populated PostgreSQL 15** database, loaded by the external weekly scraper + Spotipy pipeline (out of repo). Without data, API endpoints return empty/errored responses.

### 9.2 Environment Setup

- `.flaskenv` provides `FLASK_APP=app.py` and `FLASK_ENV=development`.
- The database URL is set in `api/__init__.py` to `postgresql://postgres:postgres@postgres/db`, where the host segment `postgres` is the Docker Compose service name (not a DNS host).

### 9.3 Run with Docker Compose

```bash
# From the repository root
docker-compose up           # Compose v1
# or, on modern Docker:
docker compose up           # Compose v2 plugin
```

- Brings up `api` (built from the local `Dockerfile`) and `postgres` (`postgres:15`).
- Host port **80** → container port **5000**. Open http://localhost/.

### 9.4 Local Development

```bash
# Backend
python -m venv venv
# Activate — Windows:        venv\Scripts\activate
#            macOS/Linux:    source venv/bin/activate
pip install -r requirements.txt
flask run                    # reads .flaskenv (FLASK_APP/FLASK_ENV)
# ...or run the module directly (binds 0.0.0.0:5000):
python app.py

# Frontend (produces the build Flask serves from frontend/build)
cd frontend
npm install
# react-scripts 4.0.3 needs the legacy OpenSSL provider on Node 17+:
NODE_OPTIONS=--openssl-legacy-provider npm run build
```

### 9.5 Verification

```bash
# Compilation (documentation-safe, read-only)
python -m py_compile app.py api/__init__.py api/routes.py api/models.py api/funcs.py
# Expected: exit code 0, no output

# App reachable (after data is loaded)
curl http://localhost/api/week/2021-01-02
```

### 9.6 Example Usage (one per route — copy-pasteable)

```bash
curl http://localhost/                                   # React SPA (index.html)
curl -i http://localhost/api/                            # 302 redirect → /api/week/{currentWeek}
curl http://localhost/api/track/0VjIjW4GlUZAMYd2vXMi3b   # track(s) by Spotify ID, ordered by rank
curl http://localhost/api/week/2021-01-02                # {week, songs, averages, avgTempo}
curl http://localhost/api/artist/Drake                   # tracks by artist (case-insensitive), newest first
curl http://localhost/api/analysis/energy                # {feature, data:[{year, value, rolling}]}
```

### 9.7 Troubleshooting

- **`npm run build` fails with an OpenSSL error** → prefix with `NODE_OPTIONS=--openssl-legacy-provider` (react-scripts 4.0.3 on Node 17+).
- **API returns empty arrays / 500s** → PostgreSQL is not populated; run the external scraper/Spotipy pipeline first.
- **Not production-ready as shipped** → the container runs Flask's dev server with debug mode; `gunicorn` is pinned but unused. For production, run a WSGI server, disable debug, externalize the DB credentials, and restrict CORS.
- **Windows local dev** → activate with `venv\Scripts\activate` and run `python app.py`.
- **Compose command not found** → use `docker-compose up` (v1) or `docker compose up` (v2), whichever your Docker install provides.

---

## 10. Appendices

### A. Command Reference

| Command | Purpose |
|---------|---------|
| `git log --oneline 2fd0190..HEAD` | List the 12 documentation commits |
| `python -m py_compile app.py api/*.py` | Verify backend compiles |
| `docker-compose up` / `docker compose up` | Start `api` + `postgres` |
| `flask run` | Run backend locally (reads `.flaskenv`) |
| `python app.py` | Run backend directly (binds `0.0.0.0:5000`) |
| `NODE_OPTIONS=--openssl-legacy-provider npm run build` | Build the React SPA |

### B. Port Reference

| Port | Where | Purpose |
|------|-------|---------|
| 80 | Host | Published by Compose → container 5000 |
| 5000 | Container / Flask | Flask app (`EXPOSE 5000`, dev server default) |
| 5432 | Host & `postgres` container | PostgreSQL 15 |

### C. Key File Locations

| Path | Role |
|------|------|
| `README.md` | Comprehensive project documentation (13 sections) |
| `app.py` | Entry point (imports `app`, runs dev server) |
| `api/__init__.py` | Flask bootstrap (app, CORS, DB, Marshmallow) |
| `api/routes.py` | 6 HTTP route handlers |
| `api/models.py` | `Tracks`, `YearlyAvg` ORM models + schemas |
| `api/funcs.py` | Helpers: week normalization, rolling average, weekly aggregation |
| `Dockerfile` / `docker-compose.yml` | Image + `api`/`postgres` topology |
| `.flaskenv` | `FLASK_APP`, `FLASK_ENV` |
| `frontend/build/` | Compiled React SPA served at `/` |

### D. Technology Versions

| Component | Version | Source |
|-----------|---------|--------|
| Python (runtime) | 3.11-slim-buster | Dockerfile |
| PostgreSQL | 15 | docker-compose.yml |
| Flask | 2.0.1 | requirements.txt |
| Flask-Cors | 3.0.10 | requirements.txt |
| flask-marshmallow | 0.14.0 | requirements.txt |
| Flask-SQLAlchemy | 2.5.1 | requirements.txt |
| SQLAlchemy | 1.4.19 | requirements.txt |
| marshmallow / -sqlalchemy | 3.12.1 / 0.26.1 | requirements.txt |
| gunicorn | 20.1.0 (pinned, unused by CMD) | requirements.txt |
| psycopg2 / -binary | 2.9.6 / 2.9.5 | requirements.txt |
| numpy / pandas | 1.24.2 / 2.0.0 | requirements.txt |
| react / react-dom | 17.0.2 | frontend/package.json |
| react-scripts | 4.0.3 | frontend/package.json |
| @amcharts/amcharts4 | 4.10.19 | frontend/package.json |

### E. Environment Variable Reference

| Variable | Value / Example | Purpose |
|----------|-----------------|---------|
| `FLASK_APP` | `app.py` | Flask entry point (`.flaskenv`) |
| `FLASK_ENV` | `development` | Enables debug mode / auto-reload |
| `SQLALCHEMY_DATABASE_URI` | `postgresql://postgres:postgres@postgres/db` | DB connection (host = Compose service name) |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | `postgres` / `postgres` / `db` | PostgreSQL container init |
| `NODE_OPTIONS` | `--openssl-legacy-provider` | Required by react-scripts 4.0.3 on Node 17+ |

### F. Developer Tools Guide (optional — out of current scope)

| Tool | Version | Use |
|------|---------|-----|
| pydoclint | 0.9.1 | Lint that docstring `Args`/`Returns`/`Raises` match signatures |
| Ruff (`D` rules) | current | PEP 257 docstring checks (successor to the deprecated pydocstyle) |
| Sphinx | 8.x (Python 3.11-compatible; not 9.x) | Generate HTML API docs from Google-style docstrings via `sphinx.ext.napoleon` |

### G. Glossary

| Term | Meaning |
|------|---------|
| Audio feature | A Spotify-derived numeric attribute (energy, danceability, valence, etc.) |
| Chart week | A Billboard Hot 100 week, normalized to a Saturday label (`YYYY-MM-DD`) |
| Rolling average | The **5-period** rolling mean of a yearly feature series (`df[feature].rolling(5).mean()`) |
| Single-origin | One Flask process serving both the React SPA (`/`) and the JSON API (`/api/*`) |
| SPA | Single-page application (the compiled React client in `frontend/build`) |
| Data pipeline | External weekly scraper + Spotipy enrichment that populates PostgreSQL (out of repo) |

---

*Completion is measured against AAP-scoped and path-to-production work only. All test results originate from Blitzy's autonomous validation logs. Colors: Completed = `#5B39F3`, Remaining = `#FFFFFF`.*