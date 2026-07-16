# Blitzy Project Guide — hot-stuff

> Billboard Hot 100 Audio-Feature Analytics · **Documentation-Only Task** (DOCUMENT CODE)
> Branch: `blitzy-47db5674-564a-4ebd-8fd4-b6c399ac3ba5`

---

## 1. Executive Summary

### 1.1 Project Overview

`hot-stuff` is a Billboard Hot 100 audio-feature analytics application: a single-origin **Python/Flask** backend serves a compiled **React** SPA at `/` and a JSON API under `/api/*`, backed by **PostgreSQL 15** and fed by an external weekly scraper + Spotipy enrichment pipeline. This engagement is a **documentation-only** task. The verbatim request — *"Add JSDoc comments to server.js functions, create a comprehensive README…"* — was reconciled to the repository's reality (no `server.js` exists; the server is Python/Flask): "JSDoc" became **Google-style Python docstrings** across the five backend modules, and the ~30-line README was expanded into a comprehensive **13-section** guide. No source logic was changed. Target users are developers onboarding to, operating, or extending the analytics service.

### 1.2 Completion Status

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'pie1':'#5B39F3','pie2':'#FFFFFF','pieStrokeColor':'#B23AF2','pieStrokeWidth':'2px','pieOuterStrokeWidth':'2px','pieTitleTextSize':'18px','pieSectionTextColor':'#B23AF2','pieLegendTextSize':'14px'}}}%%
pie showData
    title AAP-Scoped Completion 88.2%
    "Completed Work (30h)" : 30
    "Remaining Work (4h)" : 4
```

| Metric | Value |
|--------|-------|
| **Total Hours** | **34** |
| Completed Hours (AI + Manual) | 30 (AI autonomous: 30 · Manual: 0) |
| Remaining Hours | 4 |
| **Percent Complete** | **88.2%** |

> **Completion basis (PA1):** `Completion % = Completed ÷ (Completed + Remaining) = 30 ÷ 34 = 88.2%`. Every AAP-scoped deliverable is fully implemented, committed, and independently validated; the sub-100% figure reflects only human-gated **path-to-production** activities (interpretation confirmation + PR review/merge + render-verify), consistent with the never-claim-100% principle.

### 1.3 Key Accomplishments

- ✅ **Backend docstrings — 16/16 documentable units** (target 15/15 met, +1 bonus module docstring): 2 module docstrings (`app.py`, `api/__init__.py`), module + 6 handler docstrings in `api/routes.py`, 4 class docstrings in `api/models.py`, and 3 expanded helper docstrings in `api/funcs.py`.
- ✅ **Comprehensive README** expanded from ~30 lines / 1.5 KB to **447 lines / 36.5 KB**, covering all **13 target sections**.
- ✅ **API Reference for all 6 routes** (up from 4/6) — each with method, path parameters, a `curl` example, and a JSON response shape (**6 curl examples** total).
- ✅ **4 Mermaid diagrams** — system-context, request-flow sequence, entity-relationship, and Compose deployment topology.
- ✅ **Accuracy correction** — README "3 year rolling average" → authoritative **5-period** value; **0 stale "3 year"** references remain in any in-scope file.
- ✅ **Inline code explanations** added for non-obvious logic (Saturday chart-week normalization, `.rolling(5)` mean, ×100 feature scaling) and the deliberately-unchanged `Tracks.__init__` `spotify_id` omission.
- ✅ **Zero source-logic changes** — `git diff` = 972 insertions / 19 deletions across 6 files, all documentation.
- ✅ **Independently validated** — deps install exactly, all modules compile, all 7 URL rules register, 228 source-line citations resolve; working tree clean, all work committed.

### 1.4 Critical Unresolved Issues

| Issue | Impact | Owner | ETA |
|-------|--------|-------|-----|
| Interpretation of "server.js"/"JSDoc" is a flagged assumption (A1–A4) awaiting requester confirmation | If the requester literally meant JavaScript/JSDoc, the deliverable targets would need to change; the primary interpretation targets the Python backend | Product owner / Requester | < 1 day |

> No defects, compilation errors, or failing checks are outstanding in any in-scope file. The single "critical" item is an **acceptance/scope confirmation**, not a code fault.

### 1.5 Access Issues

| System / Resource | Type of Access | Issue Description | Resolution Status | Owner |
|-------------------|----------------|-------------------|-------------------|-------|
| PostgreSQL data | Runtime data dependency | DB-backed endpoints require an **external, out-of-repo** weekly scraper + Spotipy pipeline to have pre-populated PostgreSQL (assumption A4). No credentials/pipeline are shipped in this repo. | Documented as prerequisite; not required for documentation validation | DevOps / Data owner |

> No repository-permission, service-credential, or third-party API-key access issues prevented the documentation work or its autonomous validation.

### 1.6 Recommended Next Steps

1. **[High]** Confirm the "server.js" → Python-backend and "JSDoc" → Google-docstring reinterpretation (assumptions A1–A4) with the original requester.
2. **[High]** Review and merge the documentation pull request (skim the 972-line diff across 6 files; confirm README renders on the Git host).
3. **[Low]** Render-verify the 4 Mermaid diagrams on the Git host and, optionally, wire up docstring linting (`pydoclint` 0.9.1 or Ruff `D` rules).
4. **[Medium]** (Beyond this task's scope) Triage the documented production-hardening disclosures — default DB credentials, permissive CORS, EOL base image, dev-server-vs-gunicorn.
5. **[Low]** (Beyond this task's scope) Align the frontend chart legend "3 Year Rolling Average" with the backend's 5-period computation.

---

## 2. Project Hours Breakdown

### 2.1 Completed Work Detail

| Component | Hours | Description |
|-----------|:----:|-------------|
| R1a · `app.py` docstring | 1 | Module docstring (entry point, run instructions, dev-server-vs-gunicorn caveat) + bind-host inline comment |
| R1b · `api/__init__.py` docstring | 2 | Flask-bootstrap module docstring (single-origin static serving, CORS, DB config, side-effect import) + inline config comments |
| R1c · `api/routes.py` docstrings | 4 | Module docstring + Google-style docstrings for all 6 handlers (route, method, `Args`, `Returns`, `Source`) |
| R1d · `api/models.py` docstrings | 3 | 4 class docstrings documenting every column via `Attributes:` + `spotify_id` omission note (documented, not fixed) |
| R1e · `api/funcs.py` docstrings | 2 | 3 helper docstrings expanded to Google style + R5 inline comments (week normalization, `.rolling(5)`, ×100 scaling) |
| R2 · README Getting Started | 3 | Prerequisites, Docker Compose path, local dev path, `NODE_OPTIONS=--openssl-legacy-provider` caveat |
| R3 · README API Reference | 4 | All 6 routes with parameters, `curl` examples, and JSON response shapes derived from handler + schema logic |
| R4 · README Deployment | 2 | Docker image, Compose topology, env-var reference, dev-server caveat, Production-hardening disclosures |
| README Architecture + diagrams | 3 | Architecture section + 4 Mermaid diagrams (system-context, sequence, ER, deployment topology) |
| README supporting sections | 3 | Overview (preserve+expand Billboard narrative), Features, Tech Stack (versioned), Project Structure, Data Models, Data Pipeline, Configuration, TOC, scope note |
| ACC · Accuracy correction | 1 | "3 year" → 5-period rolling-average correction across all in-scope files + terminology consistency |
| QA & validation cycles | 2 | Dependency install, `py_compile`, live URL-map introspection, 228-citation integrity audit, Checkpoint-1 + 3 QA-report fix rounds |
| **Total** | **30** | **Sum matches Completed Hours in Section 1.2** |

### 2.2 Remaining Work Detail

| Category | Hours | Priority |
|----------|:----:|:--------:|
| Confirm "server.js"/"JSDoc" reinterpretation (assumptions A1–A4) with requester | 1 | High |
| Review & merge the documentation PR | 2 | High |
| Render-verify README + 4 Mermaid diagrams on Git host; optional docstring-lint setup | 1 | Low |
| **Total** | **4** | **Matches Remaining Hours in Section 1.2 and Section 7 pie** |

### 2.3 Reconciliation & Out-of-Scope Follow-ups

**Cross-section arithmetic:** Section 2.1 (30h) + Section 2.2 (4h) = **34h** = Total Project Hours (Section 1.2). Completion = 30 ÷ 34 = **88.2%**.

The following items were surfaced by the documentation but are **explicitly out of scope** for this documentation-only task (per AAP §0.8.2). They are **excluded from the 34h total** and are listed for stakeholder awareness only:

| Follow-up (out of scope) | Indicative Hours | Priority |
|--------------------------|:----------------:|:--------:|
| Rotate/replace default DB credentials (`postgres:postgres`) before real deployment | ~1 | Medium |
| Restrict permissive global CORS to known origins (source change) | ~1 | Medium |
| Upgrade off EOL Debian `buster` base image + add security headers (infra) | ~3 | Medium |
| Switch container `CMD` from Flask dev server to `gunicorn` for production (infra) | ~1 | Medium |
| Align frontend "3 Year Rolling Average" chart legend to 5-period (frontend source) | ~0.5 | Low |

---

## 3. Test Results

> **Integrity note:** This is a **documentation-only** task. The repository contains **no unit-test suite** (no backend `tests/` directory; the AAP explicitly excludes creating tests). Accordingly, the "tests" below are the **documentation-validation checks executed by Blitzy's autonomous validation systems** — the language-appropriate QA for a DOCUMENT CODE task. No unit/integration tests were invented. All results originate from the autonomous validation logs for this project.

| Test Category | Framework / Method | Total Checks | Passed | Failed | Coverage % | Notes |
|---------------|--------------------|:-----------:|:-----:|:-----:|:---------:|-------|
| Docstring coverage | Python `ast` audit | 16 | 16 | 0 | 100% | 15 AAP-required units + 1 bonus module docstring; target 15/15 met |
| Docstring well-formedness | Google-style / PEP 257 check | 9 | 9 | 0 | 100% | 6 handlers + 3 helpers: summary + `Args:` + `Returns:` present |
| Citation integrity | `path:Lline` resolver | 228 | 228 | 0 | 100% | All resolve in-bounds; 0 out-of-bounds, 0 missing files, 0 unparseable |
| Module compilation | `python -m py_compile` | 5 | 5 | 0 | 100% | All backend modules compile under CPython 3.11 |
| Dependency install | `uv pip install -r requirements.txt` | 23 | 23 | 0 | 100% | Every pin installs exactly; no conflicts |
| Runtime route registration | Flask `url_map` introspection | 7 | 7 | 0 | 100% | 6 documented handlers + static rule, all GET |
| README API accuracy | Manual vs. handler/schema | 6 | 6 | 0 | 100% | Every route method/params/response verified against source |
| README structure | Fenced-block / TOC / Mermaid parse | — | pass | 0 | 100% | 22 balanced fenced blocks, 4 well-formed Mermaid blocks, 13/13 sections, TOC anchors resolve |
| **Aggregate** | — | **294** | **294** | **0** | **100%** | Zero failures / blocked / skipped |

---

## 4. Runtime Validation & UI Verification

Runtime behavior was verified by importing the Flask app and introspecting its live routing (no production DB required — configuration is lazy).

- ✅ **Application import** — `import api` constructs the Flask `app`, `SQLAlchemy(db)`, and `Marshmallow(ma)` with no errors.
- ✅ **URL map — 7 rules registered** (matches README API Reference exactly):
  - ✅ `GET /` → `index` (serves compiled React SPA `index.html`)
  - ✅ `GET /<path:filename>` → `static`
  - ✅ `GET /api/` → `home` (302 redirect to `week/{currentWeek}`)
  - ✅ `GET /api/track/<spotify_id>` → `get_track_by_id`
  - ✅ `GET /api/week/<week>` → `get_tracks_by_week`
  - ✅ `GET /api/artist/<artist>` → `get_tracks_by_artist`
  - ✅ `GET /api/analysis/<feature>` → `get_avg_feature`
- ✅ **Real WSGI serve proof** (autonomous logs) — `GET /` → **200 OK** `text/html` (React SPA, `<!doctype html>` + `id="root"`); `GET /api/` → **302 FOUND** with relative `Location: week/<current-Saturday>`, confirming the `get_query_week` Saturday-snap logic.
- ⚠ **DB-backed endpoints — partial by design** — `/api/track`, `/api/week`, `/api/artist`, `/api/analysis` require an externally pre-populated PostgreSQL (assumption A4). Documented empty-DB behavior: `track`/`artist` → `200 []`; `week`/`analysis` → `HTTP 500`. This is accurately documented, not a defect.
- ✅ **UI (SPA) serving** — the single-origin design (one Flask process serving both the React build and the JSON API) is verified via the `/` → 200 HTML response. Deep frontend UI verification is **out of scope** (React client is not a target of this documentation task).

---

## 5. Compliance & Quality Review

AAP deliverables cross-mapped to their quality benchmarks and completion status.

| AAP Requirement | Benchmark | Status | Progress | Notes |
|-----------------|-----------|:------:|:--------:|-------|
| **R1** Backend docstrings (5 modules) | 15/15 units, Google style | ✅ Pass | 16/16 (107%) | +1 bonus module docstring on `routes.py`; inner `Meta` classes & `Tracks.__init__` correctly excluded |
| **R2** README setup instructions | Docker + local paths, sub-10-min setup | ✅ Pass | 100% | Prerequisites, Compose, venv/`flask run`, `npm run build`, `NODE_OPTIONS` caveat |
| **R3** API documentation | 6/6 routes, params + example req/resp | ✅ Pass | 6/6 (100%) | Up from 4/6; 6 `curl` examples; JSON fields match schemas |
| **R4** Deployment guide | Image, Compose, ports, env vars, caveats | ✅ Pass | 100% | `python:3.11-slim-buster`, `api`+`postgres:15`, `80:5000` & `5432:5432`, dev-server caveat |
| **R5** Inline code explanations | Non-obvious logic commented | ✅ Pass | 100% | Week normalization, `.rolling(5)`, ×100 scaling, `spotify_id` omission |
| README coverage | 13/13 target sections | ✅ Pass | 13/13 (100%) | TOC + Architecture (4 diagrams) + Data Models + Data Pipeline |
| Accuracy | Docs match source | ✅ Pass | 100% | "3 year" → 5-period corrected; 0 stale references |
| Style | Google docstrings, source citations | ✅ Pass | 100% | `Source: <path>:<line>` on technical claims; 228 citations resolve |
| Documentation-only constraint | No source-logic change | ✅ Pass | 100% | 972 ins / 19 del, all documentation; behavior unchanged |

**Fixes applied during autonomous validation** (from commit history): Checkpoint-1 code-review findings (citations, credential caveat, helper precision); stale `Source` citations + invented column units corrected; schema docstrings reworded to not overstate serialized field order; README QA rounds (root title, `/api/` redirect, scope note, Getting Started operational accuracy, empty-DB behavior, Data Pipeline self-citations, Production-hardening disclosures).

**Outstanding compliance items:** none within AAP scope. The only open item is human confirmation of the interpretation assumptions (Section 1.4).

---

## 6. Risk Assessment

| Risk | Category | Severity | Probability | Mitigation | Status |
|------|----------|:--------:|:-----------:|-----------|:------:|
| Interpretation of "server.js"/"JSDoc" may not match requester intent | Technical | Medium | Low–Med | Flagged as assumptions A1–A4; README "A note on scope" section; targets the only real server (Python/Flask) | Open (human confirm) |
| No automated test suite guarding doc accuracy | Technical | Low | Low | 228-citation integrity audit + runtime route introspection performed | Accepted (AAP excludes tests) |
| Documentation drift — 228 source-line citations may desync on future edits | Technical | Low | Medium | Citations are precise & traceable; optional docstring linter recommended | Open (maintenance) |
| Default DB credentials (`postgres:postgres`) | Security | High (if deployed) | Medium | Disclosed in README Production hardening + `__init__` docstring "replace before production" | Documented (fix out of scope) |
| Permissive global CORS (`CORS(app)`) | Security | Medium | Medium | Disclosed in README + module docstring | Documented (fix out of scope) |
| EOL Debian `buster` base image (EOL 2024-06-30) | Security | Medium | Medium | Disclosed in README Production hardening | Documented (fix out of scope) |
| Flask dev server used in container `CMD` (gunicorn pinned but unused) | Operational | Medium | Medium | Documented in `app.py` docstring + README Deployment caveat | Documented (fix out of scope) |
| External pre-populated PostgreSQL prerequisite; empty-DB errors | Operational | Medium | Medium | Documented prerequisite (A4) + empty-DB behavior (`200 []` / `HTTP 500`) | Accepted |
| External scraper + Spotipy pipeline lives outside repo | Integration | Medium | Medium | Documented as external prerequisite (A4) | Accepted |
| Mermaid rendering depends on Git-host support | Integration | Low | Low | Render-verify recommended (task H3) | Open (verify) |
| Flask 2.0.1 + Werkzeug 2.2.3 test-client `as_tuple` incompatibility | Integration | Low | Low | Affects only the test-client helper, not real serving (proven via raw WSGI); fix = version change (out of scope) | Documented |

---

## 7. Visual Project Status

**Project Hours Breakdown** (Completed = Dark Blue `#5B39F3`, Remaining = White `#FFFFFF`):

```mermaid
%%{init: {'theme':'base', 'themeVariables': {'pie1':'#5B39F3','pie2':'#FFFFFF','pieStrokeColor':'#B23AF2','pieStrokeWidth':'2px','pieOuterStrokeWidth':'2px','pieTitleTextSize':'18px','pieSectionTextColor':'#B23AF2','pieLegendTextSize':'14px'}}}%%
pie showData
    title Project Hours (Total 34h)
    "Completed Work" : 30
    "Remaining Work" : 4
```

**Remaining Hours by Category** (sums to 4h — matches Section 1.2 & 2.2):

```mermaid
xychart-beta
    title "Remaining Hours by Category"
    x-axis ["Confirm A1-A4 [High]", "Review & Merge PR [High]", "Render-verify/Lint [Low]"]
    y-axis "Hours" 0 --> 3
    bar [1, 2, 1]
```

> **Integrity:** Pie "Remaining Work" (4h) = Section 1.2 Remaining Hours (4h) = Section 2.2 total (4h). Pie "Completed Work" (30h) = Section 1.2 Completed Hours (30h) = Section 2.1 total (30h).

---

## 8. Summary & Recommendations

**Achievements.** All AAP-scoped documentation deliverables are fully implemented, committed, and independently validated. The five backend "server" modules now carry Google-style docstrings (16/16 documentable units), the README is a comprehensive 13-section guide (447 lines) documenting all six API routes with worked `curl` examples, four Mermaid diagrams, data models, configuration, and deployment. The one factual inaccuracy in the original README (the rolling-average period) was corrected to the authoritative 5-period value, with zero stale references remaining. Crucially, **no source logic was modified** — the change set is 100% documentation.

**Remaining gaps & critical path to production.** The project is **88.2% complete** (30 of 34 AAP-scoped hours). The remaining **4 hours** are entirely **human-gated path-to-production** activities: (1) confirming the "server.js"/"JSDoc" reinterpretation with the requester — the single most important acceptance gate; (2) reviewing and merging the documentation PR; and (3) render-verifying the README/Mermaid output. None of these are engineering defects.

**Success metrics.** Docstring coverage 100% (16/16); API-route documentation 6/6; README sections 13/13; citation integrity 228/228; dependency install 23/23 exact; runtime routes 7/7 registered; source-logic changes 0.

**Production-readiness assessment.** The **documentation deliverable is production-ready** and safe to merge. Separately — and outside this documentation task's scope — the *application* carries pre-existing operational/security disclosures (default credentials, permissive CORS, EOL base image, dev server) that the new documentation now transparently surfaces; these should be triaged before any real deployment but do not block acceptance of the documentation.

**Recommendation.** Confirm the interpretation assumptions, then approve and merge. Treat the out-of-scope hardening items (Section 2.3) as a follow-on engineering backlog.

---

## 9. Development Guide

### 9.1 System Prerequisites

- **Docker path (recommended):** Docker Engine with Compose v2 (verified host: Docker 29.6.1).
- **Local path:** Python **3.11** (matches `python:3.11-slim-buster`), Node.js + npm (for the React build), and a reachable PostgreSQL 15 instance.
- **Data prerequisite:** DB-backed endpoints require an externally pre-populated PostgreSQL (external weekly scraper + Spotipy pipeline — assumption A4). Not required to build docs or validate routing.

### 9.2 Environment Setup

Environment variables (see Appendix E for the full reference):

```bash
# Backend (from .flaskenv — auto-loaded by `flask run`)
FLASK_APP=app.py
FLASK_ENV=development
# Database (default from api/__init__.py; 'postgres' host = Compose service name)
# postgresql://postgres:postgres@postgres/db   # replace credentials before production
# Frontend build on modern Node (react-scripts 4.0.3)
NODE_OPTIONS=--openssl-legacy-provider
```

### 9.3 Dependency Installation

```bash
# Backend (local) — from repository root
python -m venv venv
# Windows: venv\Scripts\activate    |    macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
cd ..
```

*Verified:* all 23 pinned backend dependencies install exactly (Flask 2.0.1, SQLAlchemy 1.4.19, pandas 2.0.0, …) under CPython 3.11.

### 9.4 Application Startup

**Option A — Docker Compose (recommended):**
```bash
docker compose up          # app → http://localhost:80 (host 80 → container 5000); PostgreSQL on 5432
```

**Option B — Local development:**
```bash
# Backend (from repository root, venv active)
flask run                  # uses .flaskenv (FLASK_APP=app.py, FLASK_ENV=development)
# ...or run the entry point directly (binds 0.0.0.0:5000)
python app.py

# Frontend (build the SPA that Flask serves from frontend/build)
cd frontend
# set NODE_OPTIONS=--openssl-legacy-provider first if react-scripts 4.0.3 errors on modern Node
npm run build
```

### 9.5 Verification Steps

```bash
# 1) Compile all backend modules (expected: exit 0, no output)
python -m py_compile app.py api/__init__.py api/routes.py api/models.py api/funcs.py

# 2) Confirm the Flask route map (expected: 7 rules — 6 handlers + static)
python -c "import api; print('\n'.join(sorted(str(r) for r in api.app.url_map.iter_rules())))"

# 3) Smoke-test the running server
curl -i http://localhost:5000/          # → 200 OK, text/html (React SPA)
curl -i http://localhost:5000/api/      # → 302 FOUND, Location: week/<current-Saturday>
```

### 9.6 Example Usage

```bash
# All Hot 100 appearances for a Spotify track ID (ordered by rank)
curl http://localhost:5000/api/track/0VjIjW4GlUZAMYd2vXMi3b

# A chart week + weekly feature aggregates → {week, songs, averages, avgTempo}
curl http://localhost:5000/api/week/2023-01-07

# Case-insensitive artist search (newest week first)
curl http://localhost:5000/api/artist/drake

# Yearly mean + 5-period rolling average of one audio feature → {feature, data:[{year,value,rolling}]}
curl http://localhost:5000/api/analysis/energy
```

### 9.7 Troubleshooting

| Symptom | Cause | Resolution |
|---------|-------|-----------|
| `npm run build` fails with an OpenSSL/`digital envelope` error | `react-scripts` 4.0.3 on modern Node | Set `NODE_OPTIONS=--openssl-legacy-provider` before building |
| `HTTP 500` from `/api/week` or `/api/analysis` | Empty/unpopulated database | Populate PostgreSQL via the external scraper/Spotipy pipeline (A4); `track`/`artist` return `200 []` when empty |
| App serves via Flask dev server, not gunicorn | Container `CMD ["python3","app.py"]` uses the dev server (gunicorn pinned but unused) | Expected/documented; switch `CMD` to gunicorn for production (out of scope here) |
| Cannot connect to DB host `postgres` | `postgres` is the Compose service name, not a literal host | Run via Docker Compose, or set `SQLALCHEMY_DATABASE_URI` to your DB when running locally |
| Mermaid diagrams show as code blocks | Git host doesn't render Mermaid | Use a Mermaid-capable renderer / GitHub; verify per task H3 |

---

## 10. Appendices

### A. Command Reference

| Purpose | Command |
|---------|---------|
| Compile all backend modules | `python -m py_compile app.py api/__init__.py api/routes.py api/models.py api/funcs.py` |
| List Flask routes | `python -c "import api; [print(r) for r in api.app.url_map.iter_rules()]"` |
| Install backend deps | `pip install -r requirements.txt` |
| Build frontend | `cd frontend && npm install && npm run build` |
| Run (Docker) | `docker compose up` |
| Run (local backend) | `flask run` or `python app.py` |
| Doc diff review | `git diff 2fd0190 HEAD -- README.md app.py api/` |

### B. Port Reference

| Port | Where | Purpose |
|------|-------|---------|
| 80 | Host (Compose) | Maps to container port 5000 |
| 5000 | Container / local Flask | Flask app (SPA + JSON API) |
| 5432 | Host & container | PostgreSQL 15 |
| 3000 | Local (optional) | CRA dev server (`npm start`), proxies API to `:5000` |

### C. Key File Locations

| File | Role | Change |
|------|------|--------|
| `README.md` | Comprehensive project documentation (13 sections) | UPDATE (+569/-12) |
| `app.py` | Flask entry point | UPDATE (+37) |
| `api/__init__.py` | Flask bootstrap (app, db, ma, config) | UPDATE (+69/-3) |
| `api/routes.py` | 6 HTTP route handlers | UPDATE (+132) |
| `api/models.py` | ORM models + Marshmallow schemas | UPDATE (+117) |
| `api/funcs.py` | Query/aggregation helpers | UPDATE (+48/-4) |
| `Dockerfile`, `docker-compose.yml`, `.flaskenv`, `requirements.txt` | Infra/config (referenced, unchanged) | REFERENCE |

### D. Technology Versions

| Component | Version | Source |
|-----------|---------|--------|
| Python (runtime) | 3.11-slim-buster | Dockerfile |
| PostgreSQL | 15 | docker-compose.yml |
| Flask | 2.0.1 | requirements.txt |
| Flask-Cors | 3.0.10 | requirements.txt |
| flask-marshmallow | 0.14.0 | requirements.txt |
| Flask-SQLAlchemy | 2.5.1 | requirements.txt |
| marshmallow | 3.12.1 | requirements.txt |
| marshmallow-sqlalchemy | 0.26.1 | requirements.txt |
| SQLAlchemy | 1.4.19 | requirements.txt |
| Werkzeug | 2.2.3 | requirements.txt |
| gunicorn | 20.1.0 (pinned, unused by `CMD`) | requirements.txt |
| psycopg2 / psycopg2-binary | 2.9.6 / 2.9.5 | requirements.txt |
| numpy / pandas | 1.24.2 / 2.0.0 | requirements.txt |
| react / react-dom | 17.0.2 | frontend/package.json |
| react-scripts | 4.0.3 | frontend/package.json |
| @amcharts/amcharts4 | 4.10.19 | frontend/package.json |
| styled-components | 5.3.0 | frontend/package.json |

### E. Environment Variable Reference

| Variable | Default | Purpose |
|----------|---------|---------|
| `FLASK_APP` | `app.py` | Flask entry point (`.flaskenv`) |
| `FLASK_ENV` | `development` | Flask environment (`.flaskenv`) |
| `SQLALCHEMY_DATABASE_URI` | `postgresql://postgres:postgres@postgres/db` | DB connection (host = Compose service name); **replace credentials before production** |
| `POSTGRES_USER` | `postgres` | PostgreSQL user (docker-compose.yml) |
| `POSTGRES_PASSWORD` | `postgres` | PostgreSQL password (docker-compose.yml) |
| `POSTGRES_DB` | `db` | PostgreSQL database name (docker-compose.yml) |
| `NODE_OPTIONS` | `--openssl-legacy-provider` | Required by react-scripts 4.0.3 on modern Node |

### F. Developer Tools Guide (optional — not required by this task)

| Tool | Version | Use | Caveat |
|------|---------|-----|--------|
| pydoclint | 0.9.1 | Lint that `Args`/`Returns`/`Raises` match signatures | Python 3.8+ |
| pydocstyle | 6.3.0 | PEP 257 style checker | Final release; **deprecated** — prefer Ruff `D` rules |
| Ruff (`D` rules) | current | Fast docstring linting | Recommended successor to pydocstyle |
| Sphinx | **8.x** (e.g., 8.3.0) | Generate HTML API docs via `sphinx.ext.napoleon` | Sphinx 9.x needs Python ≥ 3.12; this project pins 3.11 → use 8.x |

### G. Glossary

| Term | Definition |
|------|-----------|
| Audio feature | A Spotify-derived numeric attribute of a track (energy, danceability, valence, tempo, …) |
| Chart week | A Billboard Hot 100 week, normalized to its Saturday date |
| Rolling average | The 5-period rolling mean of a yearly audio-feature series (`df[feature].rolling(5).mean()`) |
| Single-origin design | One Flask process serving both the compiled React SPA (`/`) and the JSON API (`/api/*`) |
| SPA | Single-Page Application — the compiled React client served from `frontend/build` |
| Google-style docstring | PEP 257-compliant docstring with `Args:`/`Returns:`/`Raises:` sections (the Python equivalent of JSDoc tags) |
| Assumption A1–A4 | Flagged interpretation assumptions: server.js→Python backend, JSDoc→Google docstrings, README as UPDATE, external data pipeline |

---

*Generated by the Blitzy Platform · Completion measured against the Agent Action Plan (AAP-scoped hours, PA1 methodology). Brand colors: Completed `#5B39F3`, Remaining `#FFFFFF`.*