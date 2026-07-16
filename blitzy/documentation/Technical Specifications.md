# Technical Specification

# 1. Introduction

## 1.1 Executive Summary

### 1.1.1 Project Overview

This repository implements a full-stack web application for exploring the **Billboard Hot 100** — described in `README.md` as the music-industry standard weekly record chart in the United States — and the **Spotify audio-feature** characteristics of the songs that appear on it. The application presents itself to users under the title **"Hot Stuff"** (rendered in `frontend/src/App.js`), is packaged as the npm project `top-100` (`frontend/package.json`), and carries the repository name `hot-stuff` (`README.md`).

The system is composed of two cooperating tiers backed by a relational database:

- A **Python/Flask REST API** (`api/` package, launched by `app.py`) that reads weekly chart records and yearly aggregates from a PostgreSQL database and serves them as JSON, while also serving the compiled front-end.
- A **React single-page application** (`frontend/`) that consumes the API and renders interactive charts using the amCharts library.

Per `README.md`, the underlying chart data is produced by *a separate weekly script that scrapes the Billboard site and enriches each song with Spotify audio features via the Spotipy library*; that ingestion script is external to this repository (it is not present in the codebase, and `requirements.txt` does not include Spotipy or any scraping library). This specification therefore documents the **serving and visualization application** — the API, the web client, and their containerized runtime.

### 1.1.2 Core Business Problem

Billboard Hot 100 rankings and Spotify's per-track audio features (tempo, energy, danceability, valence, and related measures) exist as separate, largely tabular data sources that are not, on their own, easy to browse historically or analyze for long-term musical trends. The application addresses this by consolidating weekly chart rankings — enriched with audio features and pre-computed yearly averages — into a single queryable API (`api/routes.py`) and an interactive browser UI (`frontend/src/`). This lets a user look up the ranked songs for any given week and observe how measurable musical characteristics of the Hot 100 have shifted across decades.

### 1.1.3 Key Stakeholders and Users

The codebase exposes no authentication, login, or user-account logic anywhere in `api/`, `frontend/src/`, or `app.py`, so the application is designed for **open, unauthenticated access**. The footer in `frontend/src/App.js` ("AUG | 2021") and the "Source Code" link to `github.com/augardiner/hot-100` in `frontend/src/components/about/AboutSection.js` indicate a single author/owner and a personal, portfolio-style project rather than an enterprise, multi-tenant system.

| Stakeholder / User | Role Relative to the System | Evidence |
|---|---|---|
| Project author / owner ("AUG") | Builds, deploys, and maintains the application | `frontend/src/App.js` footer; `AboutSection.js` source link |
| End users (music enthusiasts, analysts, general public) | Browse weekly charts and audio-feature trends via the web UI | `frontend/src/components/` (Tracks, Trends, About views) |
| API consumers | Retrieve chart/feature JSON directly from the HTTP endpoints | `api/routes.py` (`/api/week`, `/api/artist`, `/api/track`, `/api/analysis`) |
| External data pipeline (out of repo) | Weekly Billboard scrape + Spotipy enrichment that populates the database | `README.md` (scraper/Spotipy description) |

### 1.1.4 Expected Value Proposition

Because the repository contains no stated business objectives, revenue model, or success metrics, the value proposition is expressed in terms of the capabilities the code actually delivers rather than any projected commercial impact:

- **Interactive weekly chart browsing** — the Tracks view retrieves and lists the ranked songs for a selected week and summarizes their audio features as an amCharts radar chart (`frontend/src/components/tracks/`).
- **Long-term trend analysis** — the Trends view plots the annual average and a rolling average of a selected audio feature over time as an amCharts line chart (`frontend/src/components/trends/`).
- **Programmatic access** — a small, documented set of JSON endpoints (`api/routes.py`) makes the same data available to other clients.
- **Reproducible, self-contained deployment** — a `Dockerfile` and `docker-compose.yml` package the API and a PostgreSQL 15 database into a runnable stack with pinned dependencies (`requirements.txt`, `frontend/package-lock.json`), and the Flask app serves the pre-built React client from a single origin (`api/__init__.py`).

## 1.2 System Overview

### 1.2.1 Project Context

#### 1.2.1.1 Business Context and Market Positioning

The system operates in the **music-data / chart-analytics** space, centered exclusively on the United States **Billboard Hot 100**. `README.md` characterizes the Hot 100 as the industry-standard weekly chart whose rankings derive from sales, radio play, and streaming. The application's purpose is to make this chart data — and the Spotify audio features of each charting song — browsable and visually analyzable through a web UI.

The repository shows the hallmarks of a **single-author, personal/portfolio project** rather than a commercial or enterprise product: there is no authentication, billing, tenancy, or user-management code; the front-end footer reads "AUG | 2021" (`frontend/src/App.js`); and the About view links to a personal GitHub repository (`frontend/src/components/about/AboutSection.js`). It is positioned as an interactive showcase of historical chart and audio-feature data, not as a multi-user SaaS platform.

#### 1.2.1.2 Current System State and Limitations

There is no evidence in the repository that this application replaces or upgrades a prior system. The following are observable constraints of the current implementation rather than limitations of a superseded system:

- **Fixed historical data window in the UI.** The Tracks view initializes to a hard-coded week of `2021-11-13`, and the date picker restricts selection to the range `1958-07-27` … `2021-11-13` (`frontend/src/components/tracks/TracksSection.js`, `frontend/src/components/tracks/DatePicker.js`). The dynamic "current date" logic exists but is commented out, so the deployed UI targets a static historical dataset rather than the live current week.
- **Dependency on an external, out-of-repo data pipeline.** The database is populated by the weekly scraper/Spotipy enrichment script described in `README.md`, which is not part of this repository. The application assumes a pre-populated PostgreSQL database and contains no ingestion, schema-migration, or seed logic.
- **Development-mode runtime.** `.flaskenv` sets `FLASK_ENV=development`, and the container entry point runs the Flask development server (`Dockerfile` `CMD ["python3", "app.py"]` → `app.run(host='0.0.0.0')`). Although `gunicorn` is pinned in `requirements.txt`, it is not wired into the container start command.

#### 1.2.1.3 Integration with the Existing Landscape

The application is a **self-contained, containerized stack** with a small integration surface, as declared in `docker-compose.yml`:

| Integration Point | Direction | Mechanism / Evidence |
|---|---|---|
| PostgreSQL database (`postgres:15`) | API reads/writes | SQLAlchemy DSN `postgresql://postgres:postgres@postgres/db` in `api/__init__.py` |
| External weekly ingestion script | Writes chart rows into DB | Described in `README.md`; not in repository |
| Spotify audio features (via Spotipy) | Consumed by the external script | `README.md`; surfaced descriptively in `frontend/src/components/trends/features.json` |
| Web browser client | Consumes API over HTTP | React SPA in `frontend/`; dev proxy `http://localhost:5000` in `frontend/package.json`; `CORS(app)` in `api/__init__.py` |

### 1.2.2 High-Level Description

#### 1.2.2.1 Primary System Capabilities

The API layer (`api/routes.py`) exposes the following capabilities; the React client (`frontend/src/`) surfaces two of them directly in its UI:

| Capability | HTTP Endpoint | Consumed by UI? |
|---|---|---|
| Ranked songs for a given week + weekly feature averages | `GET /api/week/<week>` | Yes — Tracks view |
| Annual average + rolling average of an audio feature | `GET /api/analysis/<feature>` | Yes — Trends view |
| All chart appearances for a Spotify track ID | `GET /api/track/<spotify_id>` | No (endpoint only) |
| Case-insensitive artist search across appearances | `GET /api/artist/<artist>` | No (endpoint only) |
| Redirect to the current computed week | `GET /api/` | Indirectly |
| Serve the compiled React application | `GET /` | Yes (app shell) |

Supporting analytical logic lives in `api/funcs.py`: `get_query_week` normalizes any date to a Saturday-aligned chart week (reflecting Billboard's weekly cadence), `get_weekly_data` computes per-feature means for a week, and `get_rolling_avg` derives a pandas rolling-mean series for the trend chart.

#### 1.2.2.2 Major System Components

| Component | Responsibility | Key File(s) |
|---|---|---|
| Flask application bootstrap | Creates the app, enables CORS, configures the PostgreSQL DSN, initializes SQLAlchemy + Marshmallow, serves the React build | `api/__init__.py` |
| HTTP route layer | Defines the six routes and composes JSON responses | `api/routes.py` |
| Data models & schemas | `Tracks` and `YearlyAvg` ORM models plus their Marshmallow serialization schemas | `api/models.py` |
| Aggregation helpers | Week normalization, weekly means, rolling averages (pandas) | `api/funcs.py` |
| React single-page app | Tab-based UI (Tracks, Trends, About), data fetching, amCharts visualizations | `frontend/src/` |
| PostgreSQL database | Persists chart rows and yearly aggregates | `docker-compose.yml` (`postgres:15`) |
| Container & orchestration | Builds the API image and runs the API + database stack | `Dockerfile`, `docker-compose.yml`, `requirements.txt` |
| External ingestion (out of repo) | Weekly Billboard scrape + Spotipy enrichment populating the DB | Described in `README.md` |

The end-to-end topology is summarized below:

```mermaid
flowchart TD
    subgraph External["External - not in this repository"]
        Scraper["Weekly Billboard scraper<br/>+ Spotipy audio-feature enrichment"]
    end

    subgraph Stack["Docker Compose stack"]
        subgraph ApiService["api service - Flask, container port 5000, host 80"]
            Flask["Flask app bootstrap<br/>api/__init__.py"]
            Routes["HTTP route layer<br/>api/routes.py"]
            Models["ORM models + schemas<br/>api/models.py"]
            Funcs["Aggregation helpers<br/>api/funcs.py"]
            StaticBuild["Compiled React build<br/>frontend/build"]
        end
        subgraph DbService["postgres service - postgres:15, port 5432"]
            DB[("PostgreSQL 'db'<br/>Tracks, YearlyAvg")]
        end
    end

    subgraph ClientTier["Web Browser"]
        SPA["React SPA<br/>Tracks / Trends / About"]
    end

    Scraper -->|"weekly writes"| DB
    Flask --> Routes
    Routes --> Models
    Routes --> Funcs
    Models -->|"SQLAlchemy ORM"| DB
    Flask --> StaticBuild
    StaticBuild -->|"index.html + JS/CSS bundle"| SPA
    SPA -->|"GET /api/week and /api/analysis via fetch"| Routes
```

#### 1.2.2.3 Core Technical Approach

The backend is a **Flask** service that uses **Flask-SQLAlchemy** for ORM access to PostgreSQL (via `psycopg2`), **Flask-Marshmallow** for JSON serialization, **Flask-CORS** for cross-origin access, and **pandas/numpy** for the aggregation helpers (`requirements.txt`, `api/`). The Flask instance is configured with `static_folder='../frontend/build'` so that, in production, the same process that serves the JSON API also serves the compiled single-page application from one origin (`api/__init__.py`).

The frontend is a **Create React App** project (React 17, `react-scripts` 4.0.3) that renders a tab-based SPA using **styled-components** for layout and **@amcharts/amcharts4** for the radar and line charts (`frontend/package.json`, `frontend/src/components/`). It fetches data with the native `fetch` API; during development a proxy forwards `/api/*` calls to the Flask server on port 5000 (`frontend/package.json`). The entire system is packaged with Docker: a `python:3.11-slim-buster` image for the API and an official `postgres:15` image for the database, coordinated by `docker-compose.yml`.

### 1.2.3 Success Criteria

#### 1.2.3.1 Absence of Formally Defined Metrics

The repository does **not** define any formal service-level agreements (SLAs), key performance indicators (KPIs), quantitative performance targets, or acceptance-test suite. There are no test files, no CI/CD configuration (no `.github/` or pipeline definitions), and no monitoring or analytics instrumentation anywhere in the codebase. Consequently, the criteria below are **derived from the observable design intent of the code** and are stated as functional-correctness expectations, not as measured or contractual guarantees.

#### 1.2.3.2 Derived Measurable Objectives (Functional Correctness)

| Objective | Observable Basis in the Repository |
|---|---|
| Weekly endpoint returns songs for the requested week ordered by rank, plus feature averages | `api/routes.py` (`get_tracks_by_week`), `api/funcs.py` (`get_weekly_data`) |
| Requested dates resolve to the correct Saturday-aligned chart week | `api/funcs.py` (`get_query_week`) |
| Analysis endpoint returns annual values and a rolling-average series for a feature | `api/routes.py` (`get_avg_feature`), `api/funcs.py` (`get_rolling_avg`) |
| UI renders the radar and line charts and lists ranked songs without error | `frontend/src/components/tracks/`, `frontend/src/components/trends/` |
| Container stack builds and runs the API against PostgreSQL reproducibly | `Dockerfile`, `docker-compose.yml`, pinned `requirements.txt` / `frontend/package-lock.json` |

#### 1.2.3.3 Critical Success Factors

- **Externally populated database.** Because ingestion is out of repo, the application only functions correctly when the external weekly script has populated the `Tracks` and `YearlyAvg` tables (`README.md`, `api/models.py`).
- **Database connectivity at the expected host.** The hard-coded DSN targets a host named `postgres`, which is satisfied by the Compose service name; the API depends on that database being reachable (`api/__init__.py`, `docker-compose.yml` `depends_on`).
- **Consistent front-end/back-end response contract.** The React components expect the specific JSON shapes (`data.averages`, `data.songs`, `data.data`) produced by the routes; correctness depends on these staying aligned (`frontend/src/components/`, `api/routes.py`).

> Note: `README.md` and the Trends line-chart legend label the trend series a "3 Year Rolling Average" (`frontend/src/components/trends/LineChart.js`), whereas `api/funcs.py` computes a 5-period rolling mean (`.rolling(5)`). This is a documented inconsistency between stated intent and implementation.

## 1.3 Scope

This scope reflects what is actually implemented in the repository. It documents the serving-and-visualization application (Flask API, React client, and container orchestration) and treats the externally maintained data-ingestion pipeline as a boundary, per `README.md`.

### 1.3.1 In-Scope

#### 1.3.1.1 Core Features and Functionalities

**Must-have capabilities** — the endpoints and views that constitute the delivered system:

| Capability | Description | Evidence |
|---|---|---|
| Weekly chart retrieval | Return rank-ordered songs for a Saturday-aligned week plus per-feature averages and average tempo | `api/routes.py` (`get_tracks_by_week`), `api/funcs.py` |
| Feature trend analysis | Return annual averages and a rolling-average series for a selected audio feature | `api/routes.py` (`get_avg_feature`), `api/funcs.py` (`get_rolling_avg`) |
| Track history by Spotify ID | Return all chart appearances for a `spotify_id` | `api/routes.py` (`get_track_by_id`) |
| Artist search | Case-insensitive substring search over the artist column, newest week first | `api/routes.py` (`get_tracks_by_artist`) |
| Current-week redirect | Redirect `/api/` to the computed current week | `api/routes.py` (`home`), `api/funcs.py` (`get_query_week`) |
| Interactive visualization UI | Radar chart of weekly feature means; line chart of annual + rolling averages; ranked song list; feature descriptions | `frontend/src/components/tracks/`, `frontend/src/components/trends/` |
| Single-origin app delivery | Flask serves the compiled React build at `/` | `api/__init__.py`, `api/routes.py` (`index`) |

**Primary user workflows** (as wired in `frontend/src/`):

- *Browse a week:* the user picks a date in the Tracks view → the client calls `GET /api/week/<week>` → the response drives an amCharts radar chart of feature averages and a scrollable list of ranked songs (`frontend/src/components/tracks/TracksSection.js`).
- *Analyze a feature over time:* the user selects one of seven audio features in the Trends view → the client calls `GET /api/analysis/<feature>` → the response renders an amCharts line chart of the annual and rolling averages, alongside descriptions from `frontend/src/components/trends/features.json`.

**Essential integrations:** a PostgreSQL 15 database accessed via SQLAlchemy (`api/__init__.py`, `docker-compose.yml`) and a standard web browser consuming the HTTP API (dev proxy in `frontend/package.json`; `CORS(app)` in `api/__init__.py`).

**Key technical requirements:** Python 3.11 with Flask, Flask-SQLAlchemy, Flask-Marshmallow, Flask-CORS, pandas/numpy, and `psycopg2` (`requirements.txt`, `Dockerfile`); React 17 with `@amcharts/amcharts4` and `styled-components` built via `react-scripts` (`frontend/package.json`); Docker + Docker Compose for build and runtime (`Dockerfile`, `docker-compose.yml`).

#### 1.3.1.2 Implementation Boundaries

| Boundary Dimension | In-Scope Definition | Evidence |
|---|---|---|
| System boundary | Read-only Flask JSON API + React client + Docker/Compose orchestration | `api/`, `frontend/`, `Dockerfile`, `docker-compose.yml` |
| User groups | Public, unauthenticated users; no roles or accounts | No auth code in `api/`, `frontend/src/`, `app.py` |
| Geographic / market coverage | United States Billboard Hot 100 chart domain only | `README.md`; `frontend/src/components/about/AboutSection.js` |
| Data domains | Weekly chart rows (`Tracks`: week, rank, track, artist, spotify_id, 9 audio features) and yearly aggregates (`YearlyAvg`) | `api/models.py` |
| Temporal coverage (UI) | Weeks selectable from `1958-07-27` to `2021-11-13`; default `2021-11-13` | `frontend/src/components/tracks/DatePicker.js`, `TracksSection.js` |

The API is **read-only** with respect to clients: every route uses `GET` and only queries and serializes data — there are no create, update, or delete endpoints (`api/routes.py`).

### 1.3.2 Out-of-Scope

The following are explicitly **not** implemented within this repository. Each is grounded in an observed absence or an external dependency.

| Category | Excluded Element | Evidence of Exclusion |
|---|---|---|
| Data ingestion | Billboard scraping and Spotipy/Spotify audio-feature enrichment | Described as a "separate script" in `README.md`; no scraper code and no `spotipy`/`requests` in `requirements.txt` |
| Database provisioning | Schema migrations, seed data, DB initialization | No migration/Alembic/`.sql`/seed files; app assumes pre-populated tables |
| Security | Authentication, authorization, accounts, rate limiting | No auth/login/token/session code anywhere in the application source |
| UI surfaces for existing endpoints | Front-end views for `/api/artist/<artist>` and `/api/track/<spotify_id>` | Only `/api/week` and `/api/analysis` are fetched by the UI (`frontend/src/components/`); the other two are documented in `AboutSection.js` but not consumed |
| Alternative visualization stack | Plotly-based charts | `plotly.js` / `react-plotly.js` are declared in `frontend/package.json` but never imported in `frontend/src/` |
| Production serving hardening | Gunicorn/WSGI production configuration | `gunicorn` is pinned in `requirements.txt` but the container runs the Flask dev server (`Dockerfile` `CMD`, `FLASK_ENV=development`) |
| Automated quality gates | Test suites and CI/CD pipelines | No test files; Testing-Library deps present but unused; no `.github/` or pipeline configs |

**Future-phase considerations:** the repository contains no roadmap document. The only forward-looking signals are commented-out code fragments — the dynamic "current week" default and date initialization in the Tracks view (`frontend/src/components/tracks/TracksSection.js`, `DatePicker.js`) and a commented-out "Source Code" link in the footer (`frontend/src/App.js`) — which suggest a live/current-week mode and a source link were contemplated but are not active.

**Integration points not covered:** the application does not call the Spotify Web API or Billboard directly at request time; those interactions belong to the external ingestion script (`README.md`). The app's only runtime integration is with its PostgreSQL database.

**Unsupported use cases:** real-time or current-week chart display (the deployed UI is pinned to the fixed `2021-11-13` window); querying weeks outside the `1958-07-27`…`2021-11-13` range through the UI; any client-initiated data modification (the API is read-only); and multi-user, authenticated, or personalized experiences.

## 1.4 References

The following repository files and folders were inspected and cited as evidence for this Introduction. No external web sources were used; the domain facts about the Billboard Hot 100 and Spotify audio features are drawn from the repository's own `README.md` and `AboutSection.js`.

**Root-level files**

- `README.md` — Project purpose, Billboard Hot 100 domain description, external weekly scraper + Spotipy enrichment, the four documented API endpoints, and the React/amCharts front-end statement
- `app.py` — Flask application launcher (`app.run(host='0.0.0.0')`)
- `requirements.txt` — Pinned Python dependencies; established Flask/SQLAlchemy/Marshmallow/pandas/psycopg2/gunicorn versions and the absence of Spotipy/scraping libraries
- `.flaskenv` — `FLASK_ENV=development` runtime setting
- `Dockerfile` — `python:3.11-slim-buster` API image build and dev-server `CMD`
- `docker-compose.yml` — API + `postgres:15` service topology, ports, credentials, and `depends_on`

**Backend package (`api/`)**

- `api/` — Flask backend package; used to confirm absence of authentication code
- `api/__init__.py` — App bootstrap: CORS, PostgreSQL DSN, SQLAlchemy/Marshmallow init, serving the React build
- `api/models.py` — `Tracks` and `YearlyAvg` ORM models and Marshmallow schemas; data-domain fields
- `api/routes.py` — The six HTTP routes and read-only response composition
- `api/funcs.py` — Week normalization (`get_query_week`), weekly means (`get_weekly_data`), rolling average (`get_rolling_avg`)

**Front-end workspace (`frontend/`)**

- `frontend/package.json` — React 17 / amCharts / plotly (declared, unused) / styled-components dependencies, scripts, and dev proxy to port 5000
- `frontend/package-lock.json` — Deterministic dependency locking (reproducible-build evidence)
- `frontend/src/` — React source root; used to confirm absence of authentication code
- `frontend/src/App.js` — Tab-based SPA shell, "Hot Stuff" title, "AUG | 2021" footer, commented-out source link
- `frontend/src/components/` — Feature modules (Tracks, Trends, About) surfaced in the UI
- `frontend/src/components/tracks/TracksSection.js` — `GET /api/week` consumption; hard-coded `2021-11-13` default
- `frontend/src/components/tracks/DatePicker.js` — Date bounds `1958-07-27` … `2021-11-13`
- `frontend/src/components/tracks/RadarChart.js` — amCharts radar chart of weekly feature means
- `frontend/src/components/trends/TrendsSection.js` — `GET /api/analysis` consumption
- `frontend/src/components/trends/LineChart.js` — amCharts line chart; "3 Year Rolling Average" legend label
- `frontend/src/components/trends/FeatureSelect.js` — Seven selectable audio features
- `frontend/src/components/trends/features.json` — Audio-feature descriptions with Spotify source link
- `frontend/src/components/about/AboutSection.js` — In-app description of the domain, API, endpoints, and source link

# 2. Product Requirements

## 2.1 Feature Catalog and Prioritization Overview

This section decomposes the **"Hot Stuff"** Billboard Hot 100 application into discrete, testable features. The decomposition is derived entirely from the implemented source code (`api/` and `frontend/src/`), the container/runtime manifests (`Dockerfile`, `docker-compose.yml`, `requirements.txt`, `.flaskenv`, `frontend/package.json`), and the project documentation (`README.md`). Where a requirement, priority, or status could not be observed directly in the repository, it is stated as a *derived* judgement grounded in the code, not as a formal product commitment.

The scope boundary established in **Section 1.3 (Scope)** applies throughout: this specification documents the *serving-and-visualization application* (Flask JSON API, React single-page client, and Docker orchestration). The weekly Billboard scraper and Spotify/Spotipy enrichment pipeline that populates the database is external to this repository and is therefore modeled as an external dependency rather than a feature.

### 2.1.1 Scope and Evidence Basis

The repository contains **no formal product-requirements document, roadmap, backlog, acceptance-test suite, or KPI/SLA definitions** (consistent with the findings in Section 1.2.3). As a result:

- **Priority (feature level: Critical/High/Medium/Low)** is *derived* from each feature's observable centrality — for example, whether the React UI actually consumes the capability, whether it loads on application start, and whether the application is unusable without it.
- **Status** reflects the *implementation state observed in the codebase*. Every feature catalogued here is present and wired into the running application, so all carry a Status of **Completed**. Two backend endpoints (F-003, F-004) are complete at the API layer but have no front-end consumer; this is noted explicitly rather than treated as "incomplete."
- **Requirement priority** uses the MoSCoW scheme (Must-Have/Should-Have/Could-Have) requested by this section's template, again derived from observable behavior.

### 2.1.2 Identifier and Classification Conventions

| Convention | Format / Values | Applied To |
|---|---|---|
| Feature identifier | `F-XXX` (F-001 … F-010) | Every catalogued feature |
| Requirement identifier | `F-XXX-RQ-YYY` | Every functional requirement under a feature |
| Feature priority | Critical / High / Medium / Low | Feature metadata (derived from centrality) |
| Requirement priority | Must-Have / Should-Have / Could-Have | Functional requirements (MoSCoW) |
| Complexity | High / Medium / Low | Functional requirements (implementation effort observed) |
| Status | Proposed / Approved / In Development / Completed | Feature metadata (all observed features = Completed) |

### 2.1.3 Master Feature Inventory

The application resolves to **ten discrete features**: five backend HTTP capabilities exposed by `api/routes.py`, one application-delivery capability, and four front-end experiences implemented in `frontend/src/`.

| Feature ID | Feature Name | Category | Priority |
|---|---|---|---|
| F-001 | Weekly Chart Retrieval API | Backend / Data-Access API | Critical |
| F-002 | Audio-Feature Trend Analysis API | Backend / Data-Access API | Critical |
| F-003 | Track History by Spotify ID API | Backend / Data-Access API | Low |
| F-004 | Artist Search API | Backend / Data-Access API | Low |
| F-005 | Current-Week Redirect | Backend / Data-Access API | Low |
| F-006 | Single-Origin SPA Delivery | Application Delivery | Critical |
| F-007 | Weekly Tracks Visualization View | Frontend / Data Visualization | Critical |
| F-008 | Audio-Feature Trends Visualization View | Frontend / Data Visualization | High |
| F-009 | About / Informational View | Frontend / Informational | Low |
| F-010 | Navigation Shell & Responsive Layout | Frontend / Navigation & UX | High |

**Status summary:** all ten features are implemented and active in the repository, so each has a Status of **Completed**. F-003 (Track History by Spotify ID) and F-004 (Artist Search) are complete at the HTTP layer in `api/routes.py` and documented in the About view, but no React component fetches them — they are backend-only capabilities with no UI surface (see Sections 2.2 and 2.4).

**Category groupings** used above:

- *Backend / Data-Access API* — read-only `GET` endpoints in `api/routes.py` that query PostgreSQL through SQLAlchemy and serialize with Marshmallow.
- *Application Delivery* — Flask serving the compiled React build from a single origin (`api/__init__.py`, `api/routes.py`).
- *Frontend / Data Visualization* — interactive amCharts-backed views that consume the API (`frontend/src/components/tracks/`, `frontend/src/components/trends/`).
- *Frontend / Informational* and *Frontend / Navigation & UX* — the static About view and the responsive navigation shell (`frontend/src/components/about/`, `frontend/src/components/navigation/`).

## 2.2 Feature Catalog

Each feature below is documented with its metadata, a four-facet description (Overview, Business Value, User Benefits, Technical Context), and its dependencies (Prerequisite Features, System Dependencies, External Dependencies, Integration Requirements). Every claim is traceable to a specific file in the repository.

### 2.2.1 F-001 — Weekly Chart Retrieval API

**Metadata**

| Attribute | Value |
|---|---|
| Unique ID | F-001 |
| Feature Name | Weekly Chart Retrieval API (`GET /api/week/<week>`) |
| Category | Backend / Data-Access API |
| Priority | Critical |
| Status | Completed |

**Description**

| Facet | Detail |
|---|---|
| Overview | Returns the rank-ordered songs for a Saturday-aligned chart week, together with derived per-feature averages and an average tempo, as a single JSON object (`get_tracks_by_week` in `api/routes.py`). |
| Business Value | The core data service of the product; it powers the default landing experience and is one of only two endpoints the UI actually consumes. |
| User Benefits | Lets a user retrieve the Hot 100 for any supported historical week and see a summarized "audio fingerprint" of that week. |
| Technical Context | Normalizes the route parameter with `get_query_week`, queries `Tracks` filtered by week and ordered by `rank`, serializes via `TrackSchema(many=True)`, computes `averages`/`avgTempo` with `get_weekly_data`, and returns `{week, songs, averages, avgTempo}` (`api/routes.py`, `api/funcs.py`, `api/models.py`). |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | None (foundational). Provides data to F-007 and is the redirect target of F-005. |
| System Dependencies | Flask app (`api/__init__.py`); `Tracks` model + `TrackSchema` (`api/models.py`); `get_query_week` + `get_weekly_data` (`api/funcs.py`); pandas; PostgreSQL via SQLAlchemy. |
| External Dependencies | A pre-populated `Tracks` table produced by the external weekly ingestion pipeline (`README.md`); not created by this repository. |
| Integration Requirements | PostgreSQL reachable at DSN `postgresql://postgres:postgres@postgres/db`; consumed by F-007 over HTTP (dev proxy `http://localhost:5000`, same-origin in production). |

### 2.2.2 F-002 — Audio-Feature Trend Analysis API

**Metadata**

| Attribute | Value |
|---|---|
| Unique ID | F-002 |
| Feature Name | Audio-Feature Trend Analysis API (`GET /api/analysis/<feature>`) |
| Category | Backend / Data-Access API |
| Priority | Critical |
| Status | Completed |

**Description**

| Facet | Detail |
|---|---|
| Overview | Returns the annual value series and a rolling-average series for one requested audio feature, from the pre-aggregated `YearlyAvg` table (`get_avg_feature` in `api/routes.py`). |
| Business Value | Delivers the long-term trend-analysis capability; the second of the two endpoints consumed by the UI. |
| User Benefits | Lets a user observe how a measurable musical characteristic of the Hot 100 (e.g., energy, danceability) has shifted across decades. |
| Technical Context | Executes `YearlyAvg.query.with_entities(YearlyAvg.year, getattr(YearlyAvg, feature))`, serializes with `YearlyAvgSchema(many=True)`, derives the rolling series with `get_rolling_avg` (pandas `.rolling(5)`), and returns `{feature, data}` with HTTP 200. Note: the response series is labeled a "3 Year Rolling Average" in the UI/README while the code computes a 5-period window — a documented inconsistency (Section 1.2.3). |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | None (foundational). Provides data to F-008. |
| System Dependencies | Flask app; `YearlyAvg` model + `YearlyAvgSchema` (`api/models.py`); `get_rolling_avg` (`api/funcs.py`); pandas; PostgreSQL via SQLAlchemy. |
| External Dependencies | A pre-populated `YearlyAvg` table produced by the external ingestion pipeline (`README.md`). |
| Integration Requirements | The `<feature>` path value must name an existing `YearlyAvg` column because it is resolved with `getattr`; consumed by F-008 over HTTP. |

### 2.2.3 F-003 — Track History by Spotify ID API

**Metadata**

| Attribute | Value |
|---|---|
| Unique ID | F-003 |
| Feature Name | Track History by Spotify ID API (`GET /api/track/<spotify_id>`) |
| Category | Backend / Data-Access API |
| Priority | Low |
| Status | Completed (backend only — no UI consumer) |

**Description**

| Facet | Detail |
|---|---|
| Overview | Returns every chart appearance whose `spotify_id` exactly equals the supplied identifier, ordered by rank (`get_track_by_id` in `api/routes.py`). |
| Business Value | Provides programmatic per-track historical lookup for API consumers. |
| User Benefits | An API client can retrieve all weeks a specific track charted; there is no front-end screen for this. |
| Technical Context | `Tracks.query.filter_by(spotify_id=spotify_id).order_by(Tracks.rank).all()`, serialized with `TrackSchema(many=True)` and returned via `jsonify` (`api/routes.py`). |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | None. |
| System Dependencies | Flask app; `Tracks` model + `TrackSchema`; PostgreSQL via SQLAlchemy. |
| External Dependencies | Pre-populated `Tracks` table (external ingestion). |
| Integration Requirements | No front-end integration; documented descriptively in the About view (`frontend/src/components/about/AboutSection.js`) but not fetched by any component. |

### 2.2.4 F-004 — Artist Search API

**Metadata**

| Attribute | Value |
|---|---|
| Unique ID | F-004 |
| Feature Name | Artist Search API (`GET /api/artist/<artist>`) |
| Category | Backend / Data-Access API |
| Priority | Low |
| Status | Completed (backend only — no UI consumer) |

**Description**

| Facet | Detail |
|---|---|
| Overview | Returns all appearances where the `artist` column contains the query string, matched case-insensitively and ordered newest-week-first (`get_tracks_by_artist` in `api/routes.py`). |
| Business Value | Provides artist-centric discovery for API consumers. |
| User Benefits | An API client can find every charting appearance of a given artist; there is no front-end screen for this. |
| Technical Context | `Tracks.query.filter(func.lower(Tracks.artist).like(func.lower(f'%{artist}%'))).order_by(Tracks.week.desc()).all()`, serialized with `TrackSchema(many=True)` (`api/routes.py`). |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | None. |
| System Dependencies | Flask app; `Tracks` model + `TrackSchema`; SQLAlchemy `func`; PostgreSQL. |
| External Dependencies | Pre-populated `Tracks` table (external ingestion). |
| Integration Requirements | No front-end integration; documented descriptively in the About view but not fetched by any component. |

### 2.2.5 F-005 — Current-Week Redirect

**Metadata**

| Attribute | Value |
|---|---|
| Unique ID | F-005 |
| Feature Name | Current-Week Redirect (`GET /api/`) |
| Category | Backend / Data-Access API |
| Priority | Low |
| Status | Completed |

**Description**

| Facet | Detail |
|---|---|
| Overview | Redirects the API root to the weekly endpoint for the currently computed chart week (`home` in `api/routes.py`). |
| Business Value | Convenience entry point that surfaces "the latest week" without the caller needing to know the date. |
| User Benefits | Requesting `/api/` lands the caller on the current computed week's dataset. |
| Technical Context | Computes `currentWeek = get_query_week(None)` (which defaults to `datetime.today()`) and issues `redirect(f'week/{currentWeek}')`, a relative HTTP redirect to F-001 (`api/routes.py`, `api/funcs.py`). |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-001 (the redirect target endpoint). |
| System Dependencies | Flask app; `get_query_week` (`api/funcs.py`). |
| External Dependencies | Relies indirectly on a populated `Tracks` table for the redirected week to return data. |
| Integration Requirements | Emits a relative redirect to `week/<YYYY-MM-DD>`; correctness depends on the server clock/timezone used by `datetime.today()`. |

### 2.2.6 F-006 — Single-Origin SPA Delivery

**Metadata**

| Attribute | Value |
|---|---|
| Unique ID | F-006 |
| Feature Name | Single-Origin SPA Delivery (`GET /`) |
| Category | Application Delivery |
| Priority | Critical |
| Status | Completed |

**Description**

| Facet | Detail |
|---|---|
| Overview | The same Flask process that serves the JSON API also serves the compiled React application (`index.html` and hashed assets) from the site root (`api/__init__.py`, `index` route in `api/routes.py`). |
| Business Value | Enables a single deployable process for both UI and API, simplifying the container deployment. |
| User Benefits | Users load the full application from one URL; in production the UI's API calls are same-origin. |
| Technical Context | `Flask(__name__, static_folder='../frontend/build', static_url_path='/')` with `CORS(app)` (`api/__init__.py`); `index()` returns `app.send_static_file('index.html')` (`api/routes.py`). The served artifacts are the CRA production build in `frontend/build`. |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | None. |
| System Dependencies | Flask static file serving; the compiled `frontend/build` artifact set. |
| External Dependencies | None at runtime. |
| Integration Requirements | Hosts the React SPA (F-007, F-008, F-009, F-010); `CORS(app)` permits cross-origin access during development. |

### 2.2.7 F-007 — Weekly Tracks Visualization View

**Metadata**

| Attribute | Value |
|---|---|
| Unique ID | F-007 |
| Feature Name | Weekly Tracks Visualization View (Tracks tab) |
| Category | Frontend / Data Visualization |
| Priority | Critical |
| Status | Completed |

**Description**

| Facet | Detail |
|---|---|
| Overview | The default UI tab: a date picker, an amCharts radar chart of weekly feature averages, and a scrollable ranked song list (`frontend/src/components/tracks/`). |
| Business Value | The primary user-facing experience and the application's landing view (tab index 0). |
| User Benefits | Interactively browse any supported historical week and visually compare that week's feature averages against a 0–100 scale. |
| Technical Context | `TracksSection.js` fetches `/api/week/<date>` (default `2021-11-13` loaded on mount via `useEffect`), manages `data`/`isLoaded`/`error` state, renders `Radar` with `data.averages` and maps `data.songs` to rank/artist/track rows; `DatePicker.js` is a controlled `<input type='date'>` (min `1958-07-27`, max `2021-11-13`); `RadarChart.js` builds an amCharts `RadarChart` with a 0–100 `ValueAxis` and `full`/`mean` series. |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-001 (data source); F-006 (delivery); F-010 (navigation to reach the tab). |
| System Dependencies | React 17; `@amcharts/amcharts4`; the browser `fetch` API. |
| External Dependencies | None beyond the API at runtime. |
| Integration Requirements | Consumes F-001 over HTTP; requires the response to contain `averages` (radar input) and `songs` (list input); dev requests are proxied to `http://localhost:5000`. |

### 2.2.8 F-008 — Audio-Feature Trends Visualization View

**Metadata**

| Attribute | Value |
|---|---|
| Unique ID | F-008 |
| Feature Name | Audio-Feature Trends Visualization View (Trends tab) |
| Category | Frontend / Data Visualization |
| Priority | High |
| Status | Completed |

**Description**

| Facet | Detail |
|---|---|
| Overview | A feature selector, an amCharts line chart comparing an "Annual Average" series with a rolling-average series, and a glossary of audio-feature definitions (`frontend/src/components/trends/`). |
| Business Value | Surfaces the long-term trend-analysis capability (F-002) directly to end users. |
| User Benefits | Users select one of seven audio features and view its historical trajectory plus a plain-language definition. |
| Technical Context | `TrendsSection.js` fetches `/api/analysis/<feature>` (default `tempo` on mount) and renders `Line` with `data.data` plus a glossary iterated from `features.json`; `FeatureSelect.js` offers a fixed 7-option dropdown (tempo, energy, danceability, instrumentalness, liveness, speechiness, acousticness); `LineChart.js` builds an amCharts `XYChart` with a yearly `DateAxis` and two `LineSeries` labeled "Annual Average" and "3 Year Rolling Average" (the latter fed by the 5-period `rolling` field from F-002). |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-002 (data source); F-006 (delivery); F-010 (navigation). |
| System Dependencies | React 17; `@amcharts/amcharts4`; `fetch`; static `features.json` glossary. |
| External Dependencies | An informational outbound link to the Spotify Web API audio-features reference (display only; not called at runtime). |
| Integration Requirements | Consumes F-002 over HTTP; expects `data.data` rows carrying `year`, `value`, and `rolling`. |

### 2.2.9 F-009 — About / Informational View

**Metadata**

| Attribute | Value |
|---|---|
| Unique ID | F-009 |
| Feature Name | About / Informational View (About tab) |
| Category | Frontend / Informational |
| Priority | Low |
| Status | Completed |

**Description**

| Facet | Detail |
|---|---|
| Overview | A static, read-only page describing the Billboard Hot 100, the Flask API and its endpoints, the front-end stack, and external references (`frontend/src/components/about/AboutSection.js`). |
| Business Value | Provides in-app documentation and attribution. |
| User Benefits | Lets users understand the project, its data sources, and the available endpoints without leaving the app. |
| Technical Context | A single stateless functional component that renders informational JSX, documents `/api/week`, `/api/artist`, `/api/track`, `/api/analysis`, and links out to Billboard, Wikipedia, amCharts, and the GitHub repository; it imports the shared `Hamburger` control. |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-006 (delivery); F-010 (navigation — rendered at tab index 3). |
| System Dependencies | React 17; the shared `Hamburger` component (`frontend/src/components/navigation/Hamburger.js`). |
| External Dependencies | Outbound informational hyperlinks only (no runtime calls). |
| Integration Requirements | Receives `showNav` from `App.js` and forwards it to `Hamburger`; performs no data fetching. |

### 2.2.10 F-010 — Navigation Shell & Responsive Layout

**Metadata**

| Attribute | Value |
|---|---|
| Unique ID | F-010 |
| Feature Name | Navigation Shell & Responsive Layout |
| Category | Frontend / Navigation & UX |
| Priority | High |
| Status | Completed |

**Description**

| Facet | Detail |
|---|---|
| Overview | A fixed sidebar containing tab primitives (Tracks, Trends, About), a mobile hamburger toggle, responsive width/opacity behavior, and per-section show/hide logic (`frontend/src/App.js`, `frontend/src/components/navigation/`). |
| Business Value | Binds the three views into a single-page application and governs how users move between them. |
| User Benefits | Consistent navigation with responsive desktop/mobile behavior (persistent sidebar on wide screens; toggled overlay on narrow screens). |
| Technical Context | `App.js` holds `nav` (sidebar-open boolean) and `activeTab` (integer) state; `Sidebar.js` renders `Tab` "Tracks" (id 0), `Tab` "Trends" (id 1) and `SmallTab` "About" (id 3), forcing the sidebar visible at `min-width:800px` (width 15vw) versus a 35vw opacity-toggled overlay below that; `Section.js` applies `display:none` to inactive sections; `Hamburger.js` toggles `nav`. Tab index 2 is intentionally unused (no matching tab or view). |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-006 (the shell is delivered as part of the served SPA). |
| System Dependencies | React 17 `useState`; `styled-components`. |
| External Dependencies | None. |
| Integration Requirements | Hosts and toggles F-007, F-008, and F-009; passes the `showNav` callback into each section's `Hamburger`; updates `activeTab` only when a different tab id is clicked. |

## 2.3 Functional Requirements

Each feature is expressed as one or more testable functional requirements (`F-XXX-RQ-YYY`) with concrete acceptance criteria, followed by a technical-specifications table and a validation-rules table. Because the repository defines **no quantitative performance targets, SLAs, or compliance obligations** (Section 1.2.3), the corresponding cells report the observable characteristics of the implementation rather than invented numbers.

### 2.3.1 F-001 — Weekly Chart Retrieval API

**Requirement Details**

| Req ID | Description | Acceptance Criteria | Priority / Complexity |
|---|---|---|---|
| F-001-RQ-001 | Return the songs charting in the resolved week, ordered by rank | `GET /api/week/2021-11-13` returns a JSON object whose `songs` array is ordered by ascending `rank` and contains the schema fields | Must-Have / Low |
| F-001-RQ-002 | Normalize any requested date to a Saturday-aligned chart week | For an input date, the returned `week` equals the last/next Saturday per `get_query_week` rules (Sun/Mon/Tue and Wed before 10:00 → previous Saturday) | Must-Have / Medium |
| F-001-RQ-003 | Include derived weekly feature averages and average tempo | Response includes `averages` (energy, danceability, speechiness, acousticness, instrumentalness, each scaled ×100 with `full`=100) and integer `avgTempo` | Must-Have / Low |

**Technical Specifications**

| Specification | Detail |
|---|---|
| Input Parameters | Path parameter `<week>` (string, expected `YYYY-MM-DD`) |
| Output / Response | JSON `{week, songs[], averages[], avgTempo}` (`api/routes.py`) |
| Performance Criteria | No quantitative target defined; single `filter_by`+`order_by` query plus a pandas aggregation over one week of rows |
| Data Requirements | Reads the `Tracks` table (week, rank, track, artist, spotify_id, 9 audio-feature columns) |

**Validation Rules**

| Rule Category | Detail |
|---|---|
| Business Rules | Week is normalized to a Saturday (Billboard's weekly cadence); songs ordered by rank |
| Data Validation | `datetime.strptime(date, '%Y-%m-%d')` — a non-matching date format raises `ValueError` (HTTP 500); no explicit input allow-listing |
| Security Requirements | Public, unauthenticated `GET`; value bound through the SQLAlchemy ORM (`filter_by`), not raw SQL |
| Compliance Requirements | None defined in the repository |

### 2.3.2 F-002 — Audio-Feature Trend Analysis API

**Requirement Details**

| Req ID | Description | Acceptance Criteria | Priority / Complexity |
|---|---|---|---|
| F-002-RQ-001 | Return the per-year value series for a requested feature | `GET /api/analysis/energy` returns `{feature:"energy", data:[…]}` where each row carries `year` and `value` | Must-Have / Low |
| F-002-RQ-002 | Attach a rolling-average series and drop the incomplete leading window | Each row includes `rolling`; rows whose rolling value is `NaN` (the initial 5-period window) are removed | Must-Have / Medium |
| F-002-RQ-003 | Resolve the requested feature to a model column | `<feature>` maps to a `YearlyAvg` column via `getattr`; the UI-supported set is energy, valence, liveness, speechiness, acousticness, danceability, instrumentalness, tempo | Should-Have / Low |

**Technical Specifications**

| Specification | Detail |
|---|---|
| Input Parameters | Path parameter `<feature>` (string; must name a `YearlyAvg` column) |
| Output / Response | JSON `{feature, data:[{year, value, rolling}]}` with explicit HTTP 200 (`api/routes.py`) |
| Performance Criteria | No quantitative target defined; pandas `.rolling(5).mean()` over the yearly-aggregate rows |
| Data Requirements | Reads the `YearlyAvg` table (year + 8 feature columns; note: no `loudness`) |

**Validation Rules**

| Rule Category | Detail |
|---|---|
| Business Rules | Rolling window = 5 periods in code, though labeled "3 Year Rolling Average" in the UI/README (documented inconsistency) |
| Data Validation | `getattr(YearlyAvg, feature)` with an unknown feature raises `AttributeError` (HTTP 500); no server-side allow-list (the UI constrains the choice to 7 features) |
| Security Requirements | Public, unauthenticated `GET`; feature resolved via attribute lookup on the model class, not string-built SQL |
| Compliance Requirements | None defined in the repository |

### 2.3.3 F-003 — Track History by Spotify ID API

**Requirement Details**

| Req ID | Description | Acceptance Criteria | Priority / Complexity |
|---|---|---|---|
| F-003-RQ-001 | Return all appearances for an exact Spotify ID, ordered by rank | `GET /api/track/<spotify_id>` returns a JSON array of rows where `spotify_id` equals the value, ordered by `rank`; an empty array when there is no match | Should-Have / Low |

**Technical Specifications**

| Specification | Detail |
|---|---|
| Input Parameters | Path parameter `<spotify_id>` (string, exact match) |
| Output / Response | JSON array of track objects (`TrackSchema`) |
| Performance Criteria | No quantitative target defined; single `filter_by` equality query |
| Data Requirements | Reads the `Tracks` table |

**Validation Rules**

| Rule Category | Detail |
|---|---|
| Business Rules | Exact equality match on `spotify_id`; results ordered by rank |
| Data Validation | No input validation; any string is accepted and a non-match yields an empty array |
| Security Requirements | Public, unauthenticated `GET`; value bound through ORM `filter_by` |
| Compliance Requirements | None defined in the repository |

### 2.3.4 F-004 — Artist Search API

**Requirement Details**

| Req ID | Description | Acceptance Criteria | Priority / Complexity |
|---|---|---|---|
| F-004-RQ-001 | Case-insensitive substring search over the artist column, newest week first | `GET /api/artist/<q>` returns rows where `lower(artist)` contains `lower(q)`, ordered by `week` descending; empty array when there is no match | Should-Have / Low |

**Technical Specifications**

| Specification | Detail |
|---|---|
| Input Parameters | Path parameter `<artist>` (substring to match) |
| Output / Response | JSON array of track objects (`TrackSchema`) |
| Performance Criteria | No quantitative target defined; a `LIKE '%…%'` scan with a leading wildcard is not index-optimizable |
| Data Requirements | Reads the `Tracks` table |

**Validation Rules**

| Rule Category | Detail |
|---|---|
| Business Rules | "Contains" (substring) match, case-insensitive, ordered newest-week-first |
| Data Validation | No sanitization of `LIKE` metacharacters (`%`, `_`) in the query value; they behave as wildcards |
| Security Requirements | Public, unauthenticated `GET`; the value is bound as a parameter by SQLAlchemy `func.lower(...).like(...)`, not concatenated into raw SQL |
| Compliance Requirements | None defined in the repository |

### 2.3.5 F-005 — Current-Week Redirect

**Requirement Details**

| Req ID | Description | Acceptance Criteria | Priority / Complexity |
|---|---|---|---|
| F-005-RQ-001 | Redirect the API root to the current computed chart week | `GET /api/` returns an HTTP 302 redirect to the relative path `week/<current Saturday>` computed by `get_query_week(None)` | Should-Have / Low |

**Technical Specifications**

| Specification | Detail |
|---|---|
| Input Parameters | None |
| Output / Response | HTTP 302 redirect to `week/<YYYY-MM-DD>` (`api/routes.py`) |
| Performance Criteria | No quantitative target defined; constant-time date computation |
| Data Requirements | None directly; the resolved week is derived from `datetime.today()` |

**Validation Rules**

| Rule Category | Detail |
|---|---|
| Business Rules | Current week derived from the server date via `get_query_week(None)` |
| Data Validation | Not applicable (no input) |
| Security Requirements | Public, unauthenticated `GET` |
| Compliance Requirements | None defined in the repository |

### 2.3.6 F-006 — Single-Origin SPA Delivery

**Requirement Details**

| Req ID | Description | Acceptance Criteria | Priority / Complexity |
|---|---|---|---|
| F-006-RQ-001 | Serve the SPA entry document at the site root | `GET /` returns `index.html` from `frontend/build` via `app.send_static_file` | Must-Have / Low |
| F-006-RQ-002 | Serve the compiled static assets from the same origin | Hashed JS/CSS bundles under `frontend/build/static` are served through `static_url_path='/'` | Must-Have / Low |

**Technical Specifications**

| Specification | Detail |
|---|---|
| Input Parameters | HTTP `GET` for `/` and for hashed asset paths |
| Output / Response | `index.html` and the compiled JS/CSS bundles |
| Performance Criteria | No quantitative target defined; served by the Flask development server (`Dockerfile` `CMD python3 app.py`) |
| Data Requirements | Reads the compiled `frontend/build` artifact set (no database access) |

**Validation Rules**

| Rule Category | Detail |
|---|---|
| Business Rules | One process serves both the JSON API and the compiled SPA from a single origin |
| Data Validation | Not applicable |
| Security Requirements | `CORS(app)` is enabled permissively; no authentication; the container runs the Flask dev server (not the pinned `gunicorn`), so it is not production-hardened |
| Compliance Requirements | None defined in the repository |

### 2.3.7 F-007 — Weekly Tracks Visualization View

**Requirement Details**

| Req ID | Description | Acceptance Criteria | Priority / Complexity |
|---|---|---|---|
| F-007-RQ-001 | Load a default week on first render | On mount, `TracksSection` fetches `/api/week/2021-11-13` and renders the result | Must-Have / Low |
| F-007-RQ-002 | Allow selection of a week within the supported bounds | The date input restricts values to `1958-07-27`…`2021-11-13`; submitting a date triggers a refetch for that date | Must-Have / Low |
| F-007-RQ-003 | Render the radar chart and ranked list with loading/error/empty handling | Radar built from `data.averages`; list built from `data.songs` (rank/artist/track); shows `. . .` while loading, `response.statusText` on a non-2xx response, and `No Data Found` on an empty array | Should-Have / Medium |

**Technical Specifications**

| Specification | Detail |
|---|---|
| Input Parameters | User-selected date (from `DatePicker`); the JSON response from F-001 |
| Output / Response | An amCharts radar chart (0–100 axis) and a scrollable ranked song list |
| Performance Criteria | No quantitative target defined; one `fetch` per week selection, re-rendering an amCharts instance |
| Data Requirements | Consumes `averages` and `songs` from F-001 |

**Validation Rules**

| Rule Category | Detail |
|---|---|
| Business Rules | Default and maximum selectable date are pinned to `2021-11-13` (a fixed historical window; the dynamic "today" logic is commented out) |
| Data Validation | Date constrained by the input's `min`/`max`; submission guarded by a truthy value in `DatePicker` |
| Security Requirements | No authentication; requests are same-origin in production and proxied to `http://localhost:5000` in development |
| Compliance Requirements | None defined in the repository |

### 2.3.8 F-008 — Audio-Feature Trends Visualization View

**Requirement Details**

| Req ID | Description | Acceptance Criteria | Priority / Complexity |
|---|---|---|---|
| F-008-RQ-001 | Load a default feature on first render | On mount, `TrendsSection` fetches `/api/analysis/tempo` and renders the result | Must-Have / Low |
| F-008-RQ-002 | Allow selection of a feature from a fixed set | The dropdown offers exactly seven features (tempo, energy, danceability, instrumentalness, liveness, speechiness, acousticness); submitting refetches for the selected feature | Must-Have / Low |
| F-008-RQ-003 | Render the two-series line chart and the feature glossary with loading/error handling | The chart shows an "Annual Average" series and a "3 Year Rolling Average" series from `data.data`; the glossary is rendered from `features.json`; loading/error states are shown | Should-Have / Medium |

**Technical Specifications**

| Specification | Detail |
|---|---|
| Input Parameters | Selected feature (from `FeatureSelect`); the JSON response from F-002 |
| Output / Response | An amCharts line chart (yearly `DateAxis`, two series) plus seven feature descriptions |
| Performance Criteria | No quantitative target defined; one `fetch` per feature selection |
| Data Requirements | Consumes `data.data` (`year`, `value`, `rolling`) from F-002; reads static `features.json` |

**Validation Rules**

| Rule Category | Detail |
|---|---|
| Business Rules | Seven selectable features; the rolling series is labeled "3 Year" while F-002 computes a 5-period window |
| Data Validation | Submission guarded by a truthy value; `FeatureSelect` initializes its own state without a value (the `initValue` prop is not consumed), so clicking "Go" without changing the dropdown sends nothing |
| Security Requirements | No authentication; the Spotify docs link is display-only (`rel='noopener noreferrer'`) |
| Compliance Requirements | None defined in the repository |

### 2.3.9 F-009 — About / Informational View

**Requirement Details**

| Req ID | Description | Acceptance Criteria | Priority / Complexity |
|---|---|---|---|
| F-009-RQ-001 | Render static informational content, endpoint documentation, and external links | The About tab displays the Billboard, API, and Front End blocks, documents the four endpoints, and renders working external links (Billboard, Wikipedia, amCharts, GitHub) | Could-Have / Low |

**Technical Specifications**

| Specification | Detail |
|---|---|
| Input Parameters | `showNav` prop from `App.js` |
| Output / Response | Static informational JSX (no data fetching) |
| Performance Criteria | Not applicable (static render) |
| Data Requirements | None |

**Validation Rules**

| Rule Category | Detail |
|---|---|
| Business Rules | Read-only content that mirrors `README.md` |
| Data Validation | Not applicable |
| Security Requirements | External anchors use `target='_blank'` with `rel='noopener noreferrer'` |
| Compliance Requirements | None defined in the repository |

### 2.3.10 F-010 — Navigation Shell & Responsive Layout

**Requirement Details**

| Req ID | Description | Acceptance Criteria | Priority / Complexity |
|---|---|---|---|
| F-010-RQ-001 | Switch the active view when a tab is selected | Clicking a tab sets `activeTab` to its id (0 Tracks, 1 Trends, 3 About) and renders only the matching `Section`; re-clicking the active tab is a no-op | Must-Have / Low |
| F-010-RQ-002 | Provide responsive sidebar behavior | The `Hamburger` toggles `nav`; at `min-width:800px` the sidebar is always visible (15vw); on narrow screens it is a 35vw opacity-toggled overlay that closes on tab selection | Should-Have / Medium |

**Technical Specifications**

| Specification | Detail |
|---|---|
| Input Parameters | Tab click events (element `id`); hamburger click events |
| Output / Response | Updated `activeTab` / `nav` state driving conditional rendering (`Section` `display:none` when inactive) |
| Performance Criteria | Not applicable (local React state) |
| Data Requirements | None |

**Validation Rules**

| Rule Category | Detail |
|---|---|
| Business Rules | `activeTab` updates only when a different id is clicked; About maps to id 3 (id 2 is intentionally unused) |
| Data Validation | The clicked element `id` is parsed with `parseInt(e.target.id, 0)` |
| Security Requirements | Not applicable (client-side navigation only) |
| Compliance Requirements | None defined in the repository |

## 2.4 Feature Relationships

This section documents only the relationships that are directly evidenced in the source code and manifests. The end-to-end runtime topology (containers, database, and external ingestion) is diagrammed in **Section 1.2.2.2**; the map below focuses specifically on inter-feature dependencies.

### 2.4.1 Feature Dependency Map

```mermaid
flowchart TD
    subgraph FrontendViews["Frontend Views"]
        F007["F-007 Weekly Tracks View"]
        F008["F-008 Trends View"]
        F009["F-009 About View"]
    end
    subgraph FrontendShell["Frontend Shell and Delivery"]
        F006["F-006 Single-Origin SPA Delivery"]
        F010["F-010 Navigation Shell"]
    end
    subgraph BackendAPI["Backend Data-Access API"]
        F001["F-001 Weekly Chart Retrieval"]
        F002["F-002 Trend Analysis"]
        F003["F-003 Track by Spotify ID"]
        F004["F-004 Artist Search"]
        F005["F-005 Current-Week Redirect"]
    end
    subgraph SharedBackend["Shared Backend Components"]
        Persist["Persistence and Serialization<br/>Tracks / YearlyAvg + Marshmallow Schemas"]
        Funcs["Aggregation Helpers<br/>get_query_week / get_weekly_data / get_rolling_avg"]
    end
    DB[("PostgreSQL db")]
    Ext["External Ingestion Pipeline<br/>(out of repository)"]

    F007 -->|"GET /api/week"| F001
    F008 -->|"GET /api/analysis"| F002
    F005 -->|"302 redirect"| F001
    F007 --> F010
    F008 --> F010
    F009 --> F010
    F010 --> F006
    F007 --> F006
    F008 --> F006
    F009 --> F006
    F001 --> Persist
    F002 --> Persist
    F003 --> Persist
    F004 --> Persist
    F001 --> Funcs
    F002 --> Funcs
    F005 --> Funcs
    Persist --> DB
    Ext -->|"weekly writes"| DB
```

**Notable observations from the map:**

- The UI consumes only **two** of the five backend endpoints (F-007→F-001 and F-008→F-002). F-003 and F-004 have no front-end consumer, and F-005 is only an internal redirect to F-001.
- Every front-end view depends on both **F-006** (which delivers the compiled SPA) and **F-010** (which renders and toggles the views).
- All data-access features ultimately depend on the shared persistence layer and, transitively, on a PostgreSQL database that is populated by the out-of-repository ingestion pipeline.

### 2.4.2 Integration Points

| Integration Point | Participants | Mechanism / Evidence |
|---|---|---|
| UI → weekly data | F-007 → F-001 | `fetch('/api/week/<date>')`; dev proxy `http://localhost:5000`, same-origin in production (`TracksSection.js`, `frontend/package.json`) |
| UI → trend data | F-008 → F-002 | `fetch('/api/analysis/<feature>')` (`TrendsSection.js`) |
| API root → weekly endpoint | F-005 → F-001 | HTTP 302 relative redirect to `week/<date>` (`api/routes.py`) |
| API → database | F-001…F-004 → PostgreSQL | SQLAlchemy ORM over DSN `postgresql://postgres:postgres@postgres/db` (`api/__init__.py`) |
| SPA hosting | F-006 → F-007/F-008/F-009/F-010 | Flask serves the compiled `frontend/build` at `/` (`api/__init__.py`) |
| External ingestion → database | out-of-repo pipeline → `Tracks`/`YearlyAvg` | Weekly scrape + Spotipy enrichment described in `README.md` (not in this repository) |

### 2.4.3 Shared Components

Shared components are code modules reused by more than one feature (or co-located in a shared module). Genuine multi-feature reuse is distinguished from single-consumer helpers.

| Shared Component | Reused By | Evidence |
|---|---|---|
| Flask app + `db`/`ma` + CORS bootstrap | F-001…F-005 and F-006 | `api/__init__.py` |
| `Tracks` model + `TrackSchema` | F-001, F-003, F-004 | `api/models.py` |
| `get_query_week` week normalization | F-001, F-005 | `api/funcs.py` |
| `@amcharts/amcharts4` charting | F-007 (radar), F-008 (line) | `RadarChart.js`, `LineChart.js` |
| `Hamburger` navigation control | F-007, F-008, F-009 | `frontend/src/components/navigation/Hamburger.js` |
| `Tab` / `SmallTab` / `Section` primitives | F-010 | `frontend/src/components/navigation/` |

Single-consumer helpers co-located in the shared layers (not reused across features): `get_weekly_data` serves only F-001, `get_rolling_avg` serves only F-002, and `YearlyAvg` + `YearlyAvgSchema` serve only F-002 (`api/funcs.py`, `api/models.py`).

### 2.4.4 Common Services

Common services are the runtime/infrastructure capabilities shared across features.

| Common Service | Role | Evidence |
|---|---|---|
| PostgreSQL 15 database | Persistence backing all data-access features | `docker-compose.yml` (`postgres:15`) |
| Flask static file serving | Delivers the compiled SPA (F-006) | `api/__init__.py` (`static_folder='../frontend/build'`) |
| CORS middleware | Permits cross-origin API access during development | `CORS(app)` in `api/__init__.py` |
| Browser `fetch` + CRA dev proxy | Client↔server transport for F-007/F-008 | `frontend/package.json` (`"proxy": "http://localhost:5000"`) |

## 2.5 Implementation Considerations

Implementation considerations are split into system-wide concerns (which apply to most or all features and are stated once to avoid repetition) and feature-specific considerations presented in two tables covering technical constraints, performance, scalability, security, and maintenance.

### 2.5.1 Cross-Cutting Considerations

The following considerations are observable in the repository and apply broadly across the feature set:

- **Runtime hardening.** The container runs the Flask **development server** (`Dockerfile` `CMD ["python3","app.py"]` → `app.run(host='0.0.0.0')`; `.flaskenv` sets `FLASK_ENV=development`). `gunicorn` is pinned in `requirements.txt` but is **not** wired into the container start command — a maintenance/production-hardening gap affecting all served features (F-001…F-006).
- **Authentication & authorization.** There is **no** auth, session, token, account, or rate-limiting code anywhere in `api/`, `frontend/src/`, or `app.py`. Every feature is publicly accessible and read-only.
- **Configuration & secrets.** The database DSN and credentials are **hard-coded** (`postgresql://postgres:postgres@postgres/db` in `api/__init__.py`; `POSTGRES_USER/PASSWORD` in `docker-compose.yml`). There is no environment-variable override or secrets management for the DSN.
- **Data availability.** All data-access features assume a **pre-populated** database supplied by the external ingestion pipeline; the repository contains no migrations, seed data, or database-initialization scripts.
- **Fixed historical window.** The deployed UI is pinned to the range `1958-07-27`…`2021-11-13` (default `2021-11-13`); the dynamic "current week" logic is present but commented out (`TracksSection.js`, `DatePicker.js`).
- **Quality gates.** There are **no automated tests and no CI/CD**. Testing-Library dependencies are declared in `frontend/package.json` but unused. The acceptance criteria in Section 2.3 are therefore *derived and testable*, not enforced by an existing suite.
- **Reproducibility.** Backend dependencies are pinned in `requirements.txt` and the frontend is locked via `package-lock.json`, supporting reproducible builds.
- **Declared-but-unused dependencies.** `axios`, `plotly.js`, and `react-plotly.js` are declared in `frontend/package.json` but never imported in `frontend/src/` (the code uses native `fetch` and `@amcharts/amcharts4`), adding avoidable dependency footprint.

### 2.5.2 Technical Constraints, Performance, and Scalability by Feature

| Feature | Technical Constraints | Performance & Scalability |
|---|---|---|
| F-001 | Input must parse as `YYYY-MM-DD`; loads a full week of rows before aggregating in pandas | No defined target; one query + one pandas aggregation per request; bounded by ~100 rows/week; no caching |
| F-002 | `<feature>` must match a `YearlyAvg` column (`getattr`); rolling window fixed at 5 | Small yearly-aggregate dataset; pandas `.rolling(5)` per request; no caching |
| F-003 | Exact `spotify_id` equality only | Single equality query; no explicit index declared on the column (`api/models.py`); scales with match count |
| F-004 | Substring `LIKE '%…%'` with a leading wildcard | Leading-wildcard `LIKE` cannot use a B-tree index → full-column scan; scales poorly on large tables |
| F-005 | Depends on the server clock/timezone via `get_query_week(None)` | Constant-time date computation |
| F-006 | Requires a prebuilt `frontend/build` in the image; served by the Flask dev server | Dev server not tuned for concurrency; static assets are hashed for cache-busting |
| F-007 | Date bounded `1958-07-27`…`2021-11-13`; default pinned to `2021-11-13` | Rebuilds an amCharts instance per fetch; entirely client-side rendering |
| F-008 | Fixed 7-feature dropdown; rolling-series label mismatch with backend window | Rebuilds an amCharts instance per fetch; client-side only |
| F-009 | Static content duplicates `README.md` narrative | Negligible (static render) |
| F-010 | Responsive breakpoint hard-coded at `800px`; tab id 2 unused | Local React state only; negligible cost |

### 2.5.3 Security Implications and Maintenance by Feature

| Feature | Security Implications | Maintenance Requirements |
|---|---|---|
| F-001 | Public `GET`; ORM-parameterized query; a malformed date raises an unhandled `ValueError` (HTTP 500) | Response contract `{week, songs, averages, avgTempo}` must stay aligned with `TracksSection` |
| F-002 | Public `GET`; `getattr` on the model (unknown feature → `AttributeError`/HTTP 500); no server-side allow-list | Keep the rolling-window label consistent (Section 1.2.3) and the feature set aligned with `FeatureSelect` |
| F-003 | Public `GET`; ORM `filter_by` (no injection surface) | No UI consumer; schema stability matters for external API callers |
| F-004 | Public `GET`; `LIKE` metacharacters (`%`,`_`) in the query are unescaped (wildcard behavior, not SQL injection) | No UI consumer; consider escaping user wildcards if a UI is added |
| F-005 | Public `GET`; redirect target derived from the server date | Timezone/clock dependence should be considered when deploying |
| F-006 | Permissive `CORS(app)`; dev server not hardened; no authentication | UI changes require rebuilding `frontend/build` before they are served |
| F-007 | No authentication; requests same-origin (prod) or proxied (dev) | Extending the date window requires manually editing the hard-coded default/max values |
| F-008 | No authentication; external Spotify link uses `rel='noopener noreferrer'` | `features.json` uses the misspelled key `desctiption`; the 7-feature set must track backend columns |
| F-009 | External links use `target='_blank'` + `rel='noopener noreferrer'` | Content is duplicated from `README.md`, so updates must be made in both places |
| F-010 | Not applicable (client-side navigation only) | The tab-index scheme (0/1/3, id 2 unused) means adding a view requires coordinated edits to `App.js` and `Sidebar.js` |

## 2.6 Requirements Traceability Matrix

This matrix traces each functional requirement to its parent feature, the primary source evidence in the repository, and the related section elsewhere in this specification. All requirements listed are implemented (Status: Completed); the matrix therefore doubles as a coverage record between the requirement set and the codebase.

### 2.6.1 Requirement-to-Source Traceability

| Requirement ID | Feature | Primary Source Evidence | Related Spec Section |
|---|---|---|---|
| F-001-RQ-001 | F-001 | `api/routes.py` (`get_tracks_by_week`) | 1.3.1.1 |
| F-001-RQ-002 | F-001 | `api/funcs.py` (`get_query_week`) | 1.2.2.1 |
| F-001-RQ-003 | F-001 | `api/funcs.py` (`get_weekly_data`) | 1.2.2.1 |
| F-002-RQ-001 | F-002 | `api/routes.py` (`get_avg_feature`), `api/models.py` | 1.3.1.1 |
| F-002-RQ-002 | F-002 | `api/funcs.py` (`get_rolling_avg`) | 1.2.3.3 |
| F-002-RQ-003 | F-002 | `api/routes.py` (`getattr`), `api/models.py` (`YearlyAvg`) | 1.2.2.1 |
| F-003-RQ-001 | F-003 | `api/routes.py` (`get_track_by_id`), `api/models.py` | 1.3.2 |
| F-004-RQ-001 | F-004 | `api/routes.py` (`get_tracks_by_artist`) | 1.3.2 |
| F-005-RQ-001 | F-005 | `api/routes.py` (`home`), `api/funcs.py` | 1.2.2.1 |
| F-006-RQ-001 | F-006 | `api/routes.py` (`index`), `api/__init__.py` | 1.2.2.3 |
| F-006-RQ-002 | F-006 | `api/__init__.py` (`static_folder`), `frontend/build/` | 1.2.2.3 |
| F-007-RQ-001 | F-007 | `frontend/src/components/tracks/TracksSection.js` | 1.3.1.1 |
| F-007-RQ-002 | F-007 | `frontend/src/components/tracks/DatePicker.js` | 1.3.1.2 |
| F-007-RQ-003 | F-007 | `frontend/src/components/tracks/RadarChart.js`, `TracksSection.js` | 1.3.1.1 |
| F-008-RQ-001 | F-008 | `frontend/src/components/trends/TrendsSection.js` | 1.3.1.1 |
| F-008-RQ-002 | F-008 | `frontend/src/components/trends/FeatureSelect.js` | 1.3.1.1 |
| F-008-RQ-003 | F-008 | `frontend/src/components/trends/LineChart.js`, `features.json` | 1.3.1.1 |
| F-009-RQ-001 | F-009 | `frontend/src/components/about/AboutSection.js` | 1.3.2 |
| F-010-RQ-001 | F-010 | `frontend/src/App.js`, `frontend/src/components/navigation/Sidebar.js` | 1.2.2.2 |
| F-010-RQ-002 | F-010 | `frontend/src/components/navigation/Sidebar.js`, `Hamburger.js`, `Section.js` | 1.2.2.2 |

### 2.6.2 Coverage Summary

| Metric | Value |
|---|---|
| Features catalogued | 10 (F-001 … F-010) |
| Functional requirements defined | 20 (F-001-RQ-001 … F-010-RQ-002) |
| Requirements with implementation evidence | 20 of 20 (100%) |
| Features consumed by the React UI | 4 (F-001, F-002 via views; F-006, F-010 as shell) |
| Backend endpoints without a UI consumer | 2 (F-003, F-004) |
| Requirements enforced by an automated test suite | 0 (no test suite exists — Section 1.2.3.1) |

## 2.7 Assumptions, Constraints, and Version Tracking

The requirements above rest on a set of assumptions and operate within constraints that are all observable in the repository. This section makes those explicit and records the version basis for the requirement set.

### 2.7.1 Assumptions

| # | Assumption | Basis |
|---|---|---|
| A-1 | The PostgreSQL database is pre-populated with `Tracks` and `YearlyAvg` data by the external weekly ingestion pipeline | `README.md`; no ingestion/migration/seed code in the repository |
| A-2 | The database is reachable at host `postgres`, database `db`, with credentials `postgres`/`postgres` | `api/__init__.py` DSN; `docker-compose.yml` environment |
| A-3 | The compiled React build exists at `frontend/build` so F-006 can serve it | `api/__init__.py` `static_folder`; `Dockerfile` `COPY . .` |
| A-4 | Client-supplied `<feature>` values name valid `YearlyAvg` columns (enforced by the UI dropdown, not the API) | `api/routes.py` `getattr`; `FeatureSelect.js` fixed options |
| A-5 | Requested weeks fall within the populated data range (the UI bounds selection to `1958-07-27`…`2021-11-13`) | `DatePicker.js` `min`/`max` |
| A-6 | The server clock/timezone is meaningful for current-week computation | `api/funcs.py` `get_query_week` uses `datetime.today()`/`datetime.now()` |

### 2.7.2 Constraints

| # | Constraint | Basis |
|---|---|---|
| C-1 | The API is **read-only**: all routes are `GET`; no create/update/delete exist | `api/routes.py` |
| C-2 | The application is **public and unauthenticated**; no roles, accounts, or rate limiting | Absence of auth code across `api/`, `frontend/src/`, `app.py` |
| C-3 | The runtime uses the **Flask development server**, not the pinned `gunicorn` | `Dockerfile` `CMD`; `.flaskenv` `FLASK_ENV=development` |
| C-4 | The deployed UI targets a **fixed historical window** (default/max `2021-11-13`) | `TracksSection.js`, `DatePicker.js` |
| C-5 | The rolling-average window is **5 periods in code** yet labeled "3 Year Rolling Average" in the UI/README | `api/funcs.py` `.rolling(5)`; `LineChart.js`; `README.md` |
| C-6 | Requirements are **not verified by any automated test suite or CI/CD** | No tests, no `.github/`/pipeline config |
| C-7 | Database DSN and credentials are **hard-coded** (no environment override) | `api/__init__.py`; `docker-compose.yml` |
| C-8 | Two endpoints (F-003, F-004) have **no front-end surface** | `frontend/src/components/` fetch only `/api/week` and `/api/analysis` |
| C-9 | Charts use **amCharts only**; `plotly.js`/`react-plotly.js`/`axios` are declared but unused | `frontend/package.json` vs `frontend/src/` imports |

### 2.7.3 Requirement Version Tracking

The repository maintains **no formal requirement-versioning artifact** — there is no requirements changelog, no per-requirement version tags, and no roadmap document. Requirement versions are therefore anchored to the observable repository state at documentation time.

| Attribute | Value |
|---|---|
| Requirement set version | 1.0 (initial reverse-documentation of the implemented system) |
| Baseline | Current repository state of `api/` and `frontend/src/` |
| Declared application version | `0.1.0` (from `frontend/package.json`, npm project `top-100`) |
| Backend version string | Not declared in the repository |
| Requirement change history | None maintained in the repository |

All 20 requirements in Section 2.3 are recorded at **version 1.0** with **Status: Completed**, reflecting that each is present and active in the codebase as documented. Any future divergence (for example, correcting the rolling-window label in C-5 or adding a UI for F-003/F-004) should increment the affected requirement's version in a subsequent revision of this specification.

## 2.8 References

The following repository files, folders, and specification sections were examined as evidence for the features and requirements documented in Section 2. No external web sources were consulted; all findings are grounded in the repository and in previously authored sections of this specification.

**Backend source files**

- `api/__init__.py` — Flask app bootstrap, `static_folder`, `CORS(app)`, hard-coded DSN; established F-006 delivery and shared bootstrap.
- `api/routes.py` — the six HTTP routes; established F-001 through F-006 behavior and response contracts.
- `api/models.py` — `Tracks`/`YearlyAvg` ORM models and Marshmallow schemas; established data requirements and serialization surfaces.
- `api/funcs.py` — `get_query_week`, `get_weekly_data`, `get_rolling_avg`; established week normalization and the 5-period rolling window.

**Frontend source files**

- `frontend/package.json` — dependencies, `proxy`, declared-but-unused libraries, app version `0.1.0`.
- `frontend/src/App.js` — SPA shell, tab-index scheme (0/1/3), navigation state; established F-010.
- `frontend/src/components/tracks/TracksSection.js`, `DatePicker.js`, `RadarChart.js` — established F-007 (fetch flow, date bounds, radar chart).
- `frontend/src/components/trends/TrendsSection.js`, `FeatureSelect.js`, `LineChart.js`, `features.json` — established F-008 (feature selection, line chart, glossary).
- `frontend/src/components/about/AboutSection.js` — established F-009 (static informational view).
- `frontend/src/components/navigation/Sidebar.js`, `Tab.js`, `SmallTab.js`, `Hamburger.js`, `Section.js` — established F-010 navigation primitives and responsive behavior.

**Infrastructure and root files**

- `README.md` — project purpose, endpoint documentation, and the external weekly scraper/Spotipy pipeline (external dependency).
- `requirements.txt` — pinned backend dependencies; confirmed the absence of `spotipy`/scraping libraries.
- `Dockerfile` — `python:3.11-slim-buster` image; container `CMD` running the Flask dev server.
- `docker-compose.yml` — `api` + `postgres:15` services, ports, credentials, volumes.
- `.flaskenv` — `FLASK_ENV=development` (dev-server runtime).
- `app.py` — minimal launcher (`app.run(host='0.0.0.0')`).

**Folders inspected**

- `api/` — the Flask backend package (four modules).
- `frontend/` and `frontend/src/components/` — the React client and its feature areas (navigation, tracks, trends, about).
- `frontend/build/` — the compiled production artifacts served by F-006.

**Cross-referenced specification sections**

- **1.1 Executive Summary** — product framing, stakeholders, and value proposition.
- **1.2 System Overview** — system capabilities, components, topology diagram, and the documented rolling-window inconsistency.
- **1.3 Scope** — in-scope/out-of-scope boundaries corroborating F-003/F-004 (endpoint-only), the fixed date window, and excluded concerns (auth, ingestion, tests, Plotly).

# 3. Technology Stack

## 3.1 Programming Languages

The Hot Stuff application is a two-tier web system whose source is divided cleanly between a **Python** backend (the `api/` package plus the `app.py` launcher) and a **JavaScript** single-page frontend (the `frontend/` Create React App project). Supporting query, markup, styling, and data-serialization languages appear where the two tiers meet the relational database, the browser, and their configuration files. The languages present are inferred directly from the repository's source files, manifests, and container definition — no additional language runtimes (e.g., TypeScript, Swift, Kotlin, Objective-C) exist anywhere in the tree.

| Language | Version | Component / Platform | Primary Role |
|---|---|---|---|
| Python | 3.11 (container base image) | Backend `api/` package and `app.py` | HTTP API, ORM models, aggregation logic |
| JavaScript (ECMAScript 2015+ with JSX) | React 17 / react-scripts 4.0.3 toolchain | `frontend/src/` single-page app | UI components, chart rendering, data fetching |
| SQL (PostgreSQL dialect) | PostgreSQL 15 engine | Persistence layer (generated by the ORM) | Relational queries against the `Tracks` and `YearlyAvg` tables |
| HTML5 | — | `frontend/public/index.html` and build output | SPA host document |
| CSS (styled-components CSS-in-JS + global stylesheet) | styled-components ^5.3.0 | `frontend/src/` | Component-scoped and global styling |
| JSON | — | `features.json`, PWA/asset manifests, `package.json` | Static content and configuration |

### 3.1.1 Backend Language — Python

Python is the exclusive backend language. The entire server tier — the application launcher `app.py`, the Flask application factory `api/__init__.py`, the ORM models `api/models.py`, the HTTP routes `api/routes.py`, and the pure aggregation helpers `api/funcs.py` — is written in Python, and every declared server dependency in `requirements.txt` is a Python (PyPI) package.

**Version.** The Python version is fixed **only** by the container base image `python:3.11-slim-buster` declared in the `Dockerfile`, establishing Python 3.11 as the runtime for the containerized `api` service. The repository contains **no other Python version pin** — there is no `.python-version`, `runtime.txt`, `Pipfile`, `pyproject.toml`, or `setup.py`. Local development instead relies on a virtual environment (the `frontend/package.json` `start-api` script invokes `venv/bin/flask run --no-debugger`, and `.gitignore` excludes `venv`), so the developer's local interpreter version is not constrained by the repository itself.

**Selection rationale.** Python is a natural fit for this workload: the backend's distinctive logic is date/week normalization and numeric aggregation of Billboard chart audio-features, which `api/funcs.py` implements on top of the `pandas`/`numpy` scientific stack. Pairing that data-analysis capability with the lightweight Flask web layer lets a small, read-only JSON API and its data-shaping code live in a single language and ecosystem.

**Constraints and dependencies.** Because the backend links against PostgreSQL through the `psycopg2` driver, the `Dockerfile` installs the system build prerequisites `libpq-dev` and `gcc` before running `pip3 install`. The container therefore depends on those native toolchain packages being present at image-build time, in addition to the pinned Python wheels for `pandas`, `numpy`, and the Flask extension set.

### 3.1.2 Frontend Language — JavaScript (ECMAScript + JSX)

The frontend is written in **plain JavaScript** using JSX, not TypeScript. Every source module under `frontend/src/` carries a `.js` extension (for example `App.js`, `index.js`, and the components under `components/navigation`, `components/tracks`, `components/trends`, and `components/about`), and the project contains **no `tsconfig.json` and no `@types/*` dependencies**, confirming a JavaScript-only codebase. `frontend/src/index.js` bootstraps the UI with `ReactDOM.render(<App/>)` inside `React.StrictMode`, and components author markup as inline JSX.

**Version / toolchain.** The JavaScript is compiled by the Create React App toolchain — `react-scripts` 4.0.3 — which supplies Babel transpilation and a Webpack build. The supported browser targets are defined by the `browserslist` field in `frontend/package.json` (production: `>0.2%`, `not dead`, `not op_mini all`; development: the last one Chrome/Firefox/Safari version).

**Selection rationale.** JavaScript with React is the standard language for a component-based single-page interface, and Create React App provides a zero-configuration build, dev server, and test runner. Choosing plain JavaScript over TypeScript keeps the small component tree (roughly a dozen components) lightweight and avoids a type-checking build step.

**Constraints and dependencies.** The `api` service in `docker-compose.yml` sets `NODE_OPTIONS=--openssl-legacy-provider`, the workaround required to run the older Webpack bundled with `react-scripts` 4.0.3 under newer Node.js/OpenSSL 3 releases — a direct consequence of the pinned CRA version. During development the frontend also depends on the CRA proxy (`"proxy": "http://localhost:5000"` in `frontend/package.json`) to reach the Flask API without cross-origin calls.

### 3.1.3 Query, Markup, Styling, and Serialization Languages

Beyond the two primary programming languages, several supporting languages are used at the tier boundaries:

- **SQL (PostgreSQL dialect)** — No raw SQL is hand-written in the repository. Instead, `api/models.py` defines the `Tracks` and `YearlyAvg` tables declaratively and `api/routes.py` issues queries through the SQLAlchemy ORM query API (`filter_by`, `order_by`, `with_entities`, and a case-insensitive `func.lower(...) LIKE` filter for artist search). SQLAlchemy generates the underlying PostgreSQL SQL at runtime.
- **HTML5** — `frontend/public/index.html` (and its compiled counterpart in `frontend/build/`) is the single host document for the SPA; its `<title>` is "Hot Stuff".
- **CSS via CSS-in-JS** — Layout and theming are expressed with `styled-components` in the navigation components (`Sidebar.js`, `Tab.js`, `SmallTab.js`, `Section.js`), complemented by a single global stylesheet at `frontend/src/styles/index.css`. There is **no TailwindCSS or other CSS framework** in the project.
- **JSON** — Used for static content and configuration: the audio-feature glossary `frontend/src/components/trends/features.json`, the npm manifest `frontend/package.json`, and the PWA/asset manifests (`manifest.json`, `asset-manifest.json`).


## 3.2 Frameworks & Libraries

The system is built on two core application frameworks — **Flask** on the backend and **React** (via Create React App) on the frontend — each surrounded by a focused set of supporting libraries for persistence, serialization, cross-origin access, data aggregation, charting, and styling. All backend versions are exactly pinned with `==` in `requirements.txt`; all frontend versions are declared with caret ranges in `frontend/package.json` and locked to exact resolved versions in `frontend/package-lock.json`. The diagram below summarizes how the principal frameworks and libraries relate across the two tiers.

```mermaid
flowchart TB
    subgraph BackendTier["Backend — Python 3.11"]
        Flask["Flask 2.0.1<br/>WSGI app and routing"]
        FSA["Flask-SQLAlchemy 2.5.1<br/>+ SQLAlchemy 1.4.19"]
        FMA["Flask-Marshmallow 0.14.0<br/>+ marshmallow 3.12.1"]
        FCORS["Flask-Cors 3.0.10"]
        PD["pandas 2.0.0 / numpy 1.24.2"]
        GU["gunicorn 20.1.0<br/>declared, not in container CMD"]
        Flask --> FSA
        Flask --> FMA
        Flask --> FCORS
        Flask --> PD
    end
    subgraph FrontendTier["Frontend — JavaScript / CRA"]
        RS["react-scripts 4.0.3"]
        React["React 17.0.2 + ReactDOM 17.0.2"]
        AM["@amcharts/amcharts4 ^4.10.19"]
        SC["styled-components ^5.3.0"]
        RS --> React
        React --> AM
        React --> SC
    end
    React -->|"fetch /api/*"| Flask
    FSA -->|"psycopg2 driver"| PG[("PostgreSQL 15")]
```

### 3.2.1 Backend Core Framework — Flask

The backend is a **Flask 2.0.1** application (pinned in `requirements.txt`). The application object is constructed in `api/__init__.py` with `Flask(__name__, static_folder='../frontend/build', static_url_path='/')`, which makes a single Flask process responsible for **both** serving the compiled React SPA from `/` and exposing the JSON API under `/api/*`. Routing is declarative via `@app.route` decorators in `api/routes.py`, and responses are produced with Flask's `jsonify` and `redirect` helpers. Flask pulls in its standard transitive stack, also explicitly pinned: **Werkzeug 2.2.3** (WSGI/HTTP), **Jinja2 3.0.1** with **MarkupSafe 2.1.2** (templating/escaping), **click 8.1.3** (the `flask` CLI), and **itsdangerous 2.0.1** (signing).

**Selection rationale.** Flask is a minimalist WSGI microframework well suited to this system's small, read-only surface — six routes total — and its ability to serve static assets from the same origin removes the need for a separate web server or reverse proxy in front of the SPA. This single-origin design is also why the frontend can use relative `fetch('/api/...')` calls in production.

**Production-server note.** Although **gunicorn 20.1.0** (a production WSGI server) is pinned in `requirements.txt`, the container does **not** invoke it: the `Dockerfile` `CMD` runs `python3 app.py`, and `app.py` calls `app.run(host='0.0.0.0')`, i.e., Flask's built-in development server. `.flaskenv` further sets `FLASK_ENV=development`. gunicorn is therefore available as a dependency but is not wired into the runtime entry point.

### 3.2.2 Backend Supporting Libraries

The Flask application composes several extension and utility libraries, all pinned in `requirements.txt`:

| Library | Version | Role in the system |
|---|---|---|
| Flask-SQLAlchemy | 2.5.1 | Flask integration for the SQLAlchemy ORM; provides `db` and the model base used in `api/models.py` |
| SQLAlchemy | 1.4.19 | Core ORM/engine that maps `Tracks`/`YearlyAvg` and generates PostgreSQL SQL |
| psycopg2 / psycopg2-binary | 2.9.6 / 2.9.5 | PostgreSQL DB-API driver used by SQLAlchemy for the `postgresql://` DSN |
| Flask-Marshmallow | 0.14.0 | Flask integration binding Marshmallow schemas to the app (`ma` in `api/__init__.py`) |
| marshmallow | 3.12.1 | Object serialization for `TrackSchema` / `YearlyAvgSchema` in `api/models.py` |
| marshmallow-sqlalchemy | 0.26.1 | Bridges Marshmallow schemas to SQLAlchemy models |
| Flask-Cors | 3.0.10 | Enables CORS via `CORS(app)` in `api/__init__.py` (applied permissively to all routes/origins) |
| pandas | 2.0.0 | Powers aggregation in `api/funcs.py` — weekly feature means and the `rolling(5).mean()` trend series |
| numpy | 1.24.2 | Numeric backend for pandas (transitive; no direct import in `api/`) |
| gunicorn | 20.1.0 | Production WSGI server (declared but not used by the container `CMD`) |
| python-dotenv | 0.18.0 | Loads environment variables (e.g., `.flaskenv`) for the `flask` CLI |
| python-dateutil / pytz / tzdata | 2.8.2 / 2021.1 / 2023.3 | Date and timezone support underpinning the Saturday-based week logic in `api/funcs.py` |
| greenlet / six | 2.0.2 / 1.16.0 | Low-level transitive dependencies (SQLAlchemy / compatibility shims) |

**Rationale for the major choices.** SQLAlchemy + Flask-SQLAlchemy provide a declarative ORM so the chart schema is expressed as Python classes rather than hand-written SQL; Marshmallow (with its Flask and SQLAlchemy adapters) cleanly serializes those models into the JSON returned by the API; Flask-Cors permits the decoupled React client to call the API during development; and pandas supplies the vectorized mean/rolling-average computations that are the analytical heart of the `/api/week` and `/api/analysis` endpoints.

### 3.2.3 Frontend Core Framework — React & Create React App

The frontend is a **React 17.0.2** single-page application paired with **ReactDOM 17.0.2**, scaffolded and built by **Create React App (`react-scripts` 4.0.3)** — all declared in `frontend/package.json`. `frontend/src/index.js` mounts the root `<App/>` component in `React.StrictMode`, and `frontend/src/App.js` implements a tabbed shell (Tracks, Trends, About) using React function components and the `useState`/`useEffect` hooks.

**Selection rationale.** React's component model maps directly onto the app's discrete UI regions (navigation sidebar, weekly-tracks view, trends view, about view), and Create React App supplies an out-of-the-box toolchain (dev server, Webpack/Babel build, Jest test runner, `browserslist` targeting) with no custom build configuration to maintain.

**Compatibility constraint.** As noted in §3.1.2, running `react-scripts` 4.0.3 on modern Node.js requires the `NODE_OPTIONS=--openssl-legacy-provider` flag, which `docker-compose.yml` sets on the `api` service. This couples the pinned CRA version to a specific Node/OpenSSL compatibility workaround.

### 3.2.4 Frontend Supporting Libraries

Only two supporting libraries are **actually imported** by the React source; the remainder are declared in `frontend/package.json` but are not referenced anywhere under `frontend/src/`.

| Library | Version (declared) | Status | Role / Evidence |
|---|---|---|---|
| @amcharts/amcharts4 | ^4.10.19 | **In use** | Charting engine; imported in `components/tracks/RadarChart.js` (RadarChart) and `components/trends/LineChart.js` (XYChart with two line series) |
| styled-components | ^5.3.0 | **In use** | CSS-in-JS styling in `components/navigation/{Sidebar,Tab,SmallTab,Section}.js` |
| axios | ^0.21.1 | Declared, unused | HTTP client never imported; the app uses the browser-native `fetch` API instead (`TracksSection.js`, `TrendsSection.js`) |
| plotly.js | ^1.58.4 | Declared, unused | No import anywhere in `frontend/src/` |
| react-plotly.js | ^2.5.1 | Declared, unused | No import anywhere in `frontend/src/` |
| web-vitals | ^1.0.1 | Declared, unused | No `reportWebVitals` usage in `frontend/src/` |
| @testing-library/jest-dom | ^5.11.4 | Declared, unused | No test files exist in the repository |
| @testing-library/react | ^11.1.0 | Declared, unused | No test files exist in the repository |
| @testing-library/user-event | ^12.1.10 | Declared, unused | No test files exist in the repository |

**Rationale and notes.** amCharts 4 was chosen as the single visualization library for both the radar chart (per-week audio-feature averages) and the multi-series line chart (annual average plus rolling average). Layout and theming are handled by `styled-components` rather than a utility CSS framework. Data retrieval deliberately relies on the native `fetch` API, so `axios` is redundant; likewise `plotly.js`/`react-plotly.js` (an alternative charting stack) and `web-vitals` are present in the manifest but never wired in. The Testing-Library packages are installed to support the CRA `test` script, but the project contains no test files, so they are effectively dormant. These declared-but-unused dependencies are documented here because they inflate the installed dependency graph without contributing to the shipped bundle behavior.

### 3.2.5 Version Compatibility and Currency Considerations

**Reproducibility.** Backend builds are reproducible because every package in `requirements.txt` is pinned with `==` (including Flask's transitive stack), and frontend builds are reproducible because `frontend/package-lock.json` locks exact resolved versions for the caret-ranged entries in `frontend/package.json`.

**Internal compatibility.** The pinned set forms a self-consistent 2021–2023-era stack: Flask 2.0.1 alongside Werkzeug 2.2.3, Jinja2 3.0.1, itsdangerous 2.0.1, click 8.1.3, and MarkupSafe 2.1.2; SQLAlchemy 1.4.19 driven through Flask-SQLAlchemy 2.5.1; and marshmallow 3.12.1 paired with Flask-Marshmallow 0.14.0 and marshmallow-sqlalchemy 0.26.1. On the frontend, React 17.0.2 / ReactDOM 17.0.2 are matched to react-scripts 4.0.3, whose build requires the `NODE_OPTIONS=--openssl-legacy-provider` flag under newer Node runtimes.

**Currency and security implications.** The chosen framework versions trail the current upstream releases. Flask 2.0.1 predates the current Flask 3.1.x line (3.1.3 is the latest stable release as of early 2026), and React 17.0.2 is two major versions behind the current React 19.x line (with React 18 widely treated as the recommended long-term production baseline). The PostgreSQL 15 engine used by the `postgres` service (see §3.5) remains a community-supported major version — the latest stable series is 18.x — so the database engine, unlike the application frameworks, is still within its support window. Because the application dependencies are drawn from 2021–2023 release lines, they predate subsequent upstream security and bug-fix releases; the reproducible-pinning approach that aids build determinism also means those fixes are not picked up until the pins are deliberately advanced. No specific vulnerability is asserted here — this is a version-currency observation, and a dependency-upgrade path is the corresponding maintenance consideration.


## 3.3 Open Source Dependencies

Every runtime dependency in the system is a free/open-source package sourced from one of two public registries: **PyPI** for the Python backend (declared in `requirements.txt`) and the **npm registry** for the JavaScript frontend (declared in `frontend/package.json`). This subsection enumerates the complete dependency bill of materials with exact versions; the functional role of the principal libraries is described in §3.2.

### 3.3.1 Python (PyPI) Dependencies

`requirements.txt` pins **23 packages** with exact `==` versions. The table classifies each as a **direct** dependency (a framework or library the backend explicitly composes or imports) or a **transitive** dependency (pulled in by one of the direct packages but pinned here for reproducibility).

| Package | Version | Registry | Classification |
|---|---|---|---|
| Flask | 2.0.1 | PyPI | Direct (web framework) |
| Flask-Cors | 3.0.10 | PyPI | Direct (CORS) |
| Flask-SQLAlchemy | 2.5.1 | PyPI | Direct (ORM integration) |
| flask-marshmallow | 0.14.0 | PyPI | Direct (serialization integration) |
| SQLAlchemy | 1.4.19 | PyPI | Direct (ORM core) |
| marshmallow | 3.12.1 | PyPI | Direct (serialization) |
| marshmallow-sqlalchemy | 0.26.1 | PyPI | Direct (ORM↔schema bridge) |
| psycopg2 | 2.9.6 | PyPI | Direct (PostgreSQL driver) |
| psycopg2-binary | 2.9.5 | PyPI | Direct (PostgreSQL driver, binary build) |
| pandas | 2.0.0 | PyPI | Direct (aggregation in `api/funcs.py`) |
| gunicorn | 20.1.0 | PyPI | Direct (WSGI server; declared, not in container CMD) |
| python-dotenv | 0.18.0 | PyPI | Direct (env/`.flaskenv` loading) |
| Werkzeug | 2.2.3 | PyPI | Transitive (Flask) |
| Jinja2 | 3.0.1 | PyPI | Transitive (Flask) |
| MarkupSafe | 2.1.2 | PyPI | Transitive (Jinja2) |
| itsdangerous | 2.0.1 | PyPI | Transitive (Flask) |
| click | 8.1.3 | PyPI | Transitive (Flask CLI) |
| numpy | 1.24.2 | PyPI | Transitive (pandas) |
| python-dateutil | 2.8.2 | PyPI | Transitive (pandas) |
| pytz | 2021.1 | PyPI | Transitive (pandas / timezone) |
| tzdata | 2023.3 | PyPI | Transitive (timezone data) |
| greenlet | 2.0.2 | PyPI | Transitive (SQLAlchemy) |
| six | 1.16.0 | PyPI | Transitive (compatibility shim) |

### 3.3.2 JavaScript (npm) Dependencies

`frontend/package.json` declares **12 packages** in its `dependencies` block using caret (`^`) ranges; `frontend/package-lock.json` locks the exact resolved versions. Create React App does not separate `devDependencies` here — the build toolchain (`react-scripts`) and the (unused) Testing-Library packages are all listed under `dependencies`.

| Package | Version (declared) | Registry | Classification |
|---|---|---|---|
| react | ^17.0.2 | npm | Direct (UI framework) |
| react-dom | ^17.0.2 | npm | Direct (DOM renderer) |
| react-scripts | 4.0.3 | npm | Direct (CRA build toolchain) |
| @amcharts/amcharts4 | ^4.10.19 | npm | Direct, in use (charts) |
| styled-components | ^5.3.0 | npm | Direct, in use (CSS-in-JS) |
| axios | ^0.21.1 | npm | Direct, declared but unused |
| plotly.js | ^1.58.4 | npm | Direct, declared but unused |
| react-plotly.js | ^2.5.1 | npm | Direct, declared but unused |
| web-vitals | ^1.0.1 | npm | Direct, declared but unused |
| @testing-library/jest-dom | ^5.11.4 | npm | Direct, declared but unused (no tests) |
| @testing-library/react | ^11.1.0 | npm | Direct, declared but unused (no tests) |
| @testing-library/user-event | ^12.1.10 | npm | Direct, declared but unused (no tests) |

### 3.3.3 Dependency Management, Registries, and Reproducibility

**Package managers and registries.** Backend dependencies are installed with `pip` from **PyPI** during the Docker image build (`RUN pip3 install -r requirements.txt` in the `Dockerfile`). Frontend dependencies are installed with `npm`/`yarn` from the **npm registry**; the `.gitignore` excludes `frontend/node_modules` and `.dockerignore` excludes `/frontend/node_modules`, so the dependency tree is reconstructed from the manifest and lockfile rather than committed.

**Reproducibility.** Both dependency sets are deterministically reproducible: `requirements.txt` uses exact `==` pins for all 23 Python packages (including the transitive Flask/pandas/SQLAlchemy chain), and `frontend/package-lock.json` records the exact resolved versions and integrity hashes for the caret-ranged npm entries.

**Dependency-graph observations.** Two characteristics of the graph are worth recording for maintenance planning. First, the backend list is effectively a frozen `pip freeze` snapshot: roughly half the entries (Werkzeug, Jinja2, MarkupSafe, itsdangerous, click, numpy, python-dateutil, pytz, tzdata, greenlet, six) are transitive rather than first-order dependencies. Second, a meaningful fraction of the **frontend** manifest is inert — `axios`, `plotly.js`, `react-plotly.js`, `web-vitals`, and the three `@testing-library/*` packages are declared but never imported by any module under `frontend/src/` (see §3.2.4), which enlarges the installed dependency graph and its aggregate security-update surface without affecting the shipped application behavior.


## 3.4 Third-Party Services

A defining characteristic of this system's technology footprint is that **the deployed application makes no outbound third-party API calls at runtime.** The Flask backend serves only its own PostgreSQL-backed data and static assets, and the React frontend calls only the same-origin `/api/*` routes. All external-service dependencies live in an **out-of-repository ingestion pipeline** that populates the database, and there are no authentication, monitoring, or cloud-provider service integrations anywhere in the codebase. Each category below reflects exactly what the repository does — and does not — integrate with.

### 3.4.1 External Data Sources (Upstream Ingestion Pipeline)

The system's data originates from two external sources, but both are consumed by a **separate weekly script that is not part of this repository.** `README.md` states that "a separate script, running weekly … scrapes the Billboard site page and adds each song into the database," and that this script uses **Spotipy** (the Spotify Web API Python client) to fetch Spotify **Audio Features** for each track. `frontend/src/components/about/AboutSection.js` mirrors this description and links to the Billboard site, Wikipedia, the Spotipy documentation, and the Spotify Web API audio-features reference.

| External source | Integration point | Location | In this repo? |
|---|---|---|---|
| Billboard Hot 100 (web page) | Weekly scrape → `Tracks` rows | External weekly script | No — described only in `README.md` / About view |
| Spotify Web API (Audio Features) | Enrichment via **Spotipy** (docs reference 2.18.0) | External weekly script | No — **spotipy is absent** from `requirements.txt` and unused in `api/` |

The backend therefore consumes the **results** of this pipeline (audio-feature values already stored in the `Tracks` and `YearlyAvg` tables per `api/models.py`) rather than calling Spotify or Billboard itself. There is no scraper module, no `spotipy` import, and no HTTP-client (e.g., `requests`) usage anywhere in `api/`. The Spotify Web API links surfaced in the Trends and About views are **informational hyperlinks** (documentation references shown to the user), not live service integrations.

### 3.4.2 Authentication Services

**None.** The system integrates with no external identity or authentication provider — there is no Auth0, OAuth, OIDC, SSO, or API-key mechanism anywhere in the codebase. `api/__init__.py` applies `CORS(app)` permissively to all routes and origins and registers no authentication middleware, and no route in `api/routes.py` performs any authorization check. The only credentials present in the project are the hard-coded PostgreSQL username/password (`postgres`/`postgres`) embedded in the connection DSN in `api/__init__.py` and in the `postgres` service environment in `docker-compose.yml`; these are database credentials, not an end-user authentication service. All six API routes and the SPA are effectively public and unauthenticated.

### 3.4.3 Monitoring and Observability Tools

**None.** The repository contains no integration with any monitoring, application-performance-management, error-tracking, logging-aggregation, or analytics service (for example, there is no Sentry, Datadog, New Relic, Prometheus, or similar client library in `requirements.txt` or `frontend/package.json`). The frontend even declares the `web-vitals` performance-metrics package, but it is never wired in (no `reportWebVitals` call exists in `frontend/src/`), so no client-side telemetry is emitted. Runtime visibility is limited to the default console/stderr output of the Flask development server and the `postgres` container.

### 3.4.4 Cloud Services

**None.** There is no cloud-provider integration and no infrastructure-as-code in the repository. No AWS, Google Cloud, or Azure SDKs are declared, and there are no cloud configuration or IaC artifacts (no Terraform `.tf` files, no CloudFormation, no serverless manifests) anywhere in the tree. The entire system is designed to run as a **local, self-contained Docker Compose stack** — the `api` and `postgres` services defined in `docker-compose.yml` — with no dependency on managed cloud databases, object storage, secrets managers, or hosted queues. Deployment and orchestration details are covered in §3.6.


## 3.5 Databases & Storage

The system uses a single relational database — **PostgreSQL** — as its only persistent datastore. There is no secondary database, no NoSQL/document store, no caching tier, and no object-storage service; all persistence is handled by one PostgreSQL instance accessed through the SQLAlchemy ORM.

### 3.5.1 Primary Database — PostgreSQL 15

The database is provisioned by the `postgres` service in `docker-compose.yml` using the official **`postgres:15`** image, with the database name `db` and username/password `postgres`/`postgres` supplied via the `POSTGRES_DB`, `POSTGRES_USER`, and `POSTGRES_PASSWORD` environment variables. The service publishes port `5432:5432` to the host.

The backend connects to it from `api/__init__.py` through the SQLAlchemy DSN `postgresql://postgres:postgres@postgres/db`, where the host `postgres` resolves to the Compose service name on the internal Docker network and `db` is the database. The `psycopg2` driver (see §3.3.1) carries out the wire protocol. PostgreSQL 15 was chosen as a mature, standards-compliant relational engine appropriate for the structured, tabular chart data the application stores, and it remains a community-supported major version (the current stable series is 18.x), so the engine itself is not end-of-life.

The relational schema is defined declaratively in `api/models.py` as two tables:

| Table | Purpose | Notable columns |
|---|---|---|
| `Tracks` | One row per song-per-chart-week | `week` (Date), `rank` (Int), `track`/`artist`/`spotify_id` (String), and nine audio-feature Floats (tempo, energy, danceability, valence, liveness, speechiness, acousticness, instrumentalness, loudness) |
| `YearlyAvg` | Pre-computed per-year audio-feature averages | `year` (String) plus eight feature Floats (no `loudness`) |

### 3.5.2 Data Persistence Strategy

Persistence is mediated entirely by the **SQLAlchemy ORM via Flask-SQLAlchemy** (`db = SQLAlchemy(app)` in `api/__init__.py`), with `SQLALCHEMY_TRACK_MODIFICATIONS` disabled. The application's data-access pattern is **read-only**: `api/routes.py` issues only `SELECT`-style ORM queries (`query.filter_by(...)`, `order_by(...)`, `with_entities(...)`, and a case-insensitive `func.lower(...) LIKE` artist filter) and Marshmallow schemas serialize the results to JSON. No route performs `INSERT`, `UPDATE`, or `DELETE`.

Crucially, **the repository contains no schema-creation, migration, or seed code** — there is no `db.create_all()` call, no Alembic/Flask-Migrate configuration, and no `.sql` or seed scripts anywhere in the tree. Table creation and all data population are the responsibility of the external weekly ingestion pipeline described in §3.4.1. The application code thus defines the ORM mapping it expects but delegates database provisioning and writes to that out-of-repository process.

### 3.5.3 Caching Solutions

**None.** There is no caching layer in the system. No in-memory cache or cache server (e.g., Redis or Memcached) and no caching library appear in `requirements.txt`, `frontend/package.json`, or `docker-compose.yml`. Every API request results in a direct query against PostgreSQL. The only pre-aggregation present is the persisted `YearlyAvg` table (computed upstream), which reduces per-request work for the trends endpoint but is a data-modeling choice rather than a runtime cache.

### 3.5.4 Storage Services and Volumes

The project uses **Docker volumes** for storage and has no external/managed storage service. Two volume-related declarations exist in `docker-compose.yml`, and their exact wiring is worth recording precisely:

- The `postgres` service declares a **bind mount** `./data:/data`, mapping the host directory `./data` into the container at `/data`.
- A top-level **named volume** `data:` is declared but is **not referenced by any service**.

Because no `PGDATA` environment variable is set, PostgreSQL uses its default data directory `/var/lib/postgresql/data` — a different path from the `/data` mount point. The configured bind mount therefore targets a location outside PostgreSQL's default data directory, and the declared named volume is unused; this is an observation about how the persistence storage is wired rather than an assertion of runtime behavior. The `./data` directory is excluded from both source control and the image build (`/data` appears in `.gitignore` and `.dockerignore`). Separately, the `api` service bind-mounts the entire repository into the container via `.:/app/`, so backend source is provided at runtime from the host working copy rather than solely from the image layers.

**Security note.** The PostgreSQL credentials are hard-coded (`postgres`/`postgres`) in both the connection DSN and the Compose environment, with no secret-management or environment-override mechanism, and port `5432` is published to the host — considerations that carry over into the deployment discussion in §3.6.


## 3.6 Development & Deployment

The project is developed with the standard tooling of its two frameworks (the Flask CLI plus a Python virtual environment, and the Create React App toolchain) and is deployed as a two-service **Docker Compose stack**. There is no automated CI/CD pipeline. The runtime topology is summarized below.

```mermaid
flowchart LR
    Browser["Web Browser"]
    HostVol["Host directory ./data"]
    subgraph Compose["Docker Compose Stack"]
        subgraph ApiSvc["api service — built from Dockerfile"]
            FlaskApp["Flask dev server<br/>python3 app.py<br/>app.run 0.0.0.0:5000"]
            Static["React build served at /<br/>frontend/build"]
        end
        subgraph DbSvc["postgres service"]
            PG[("postgres:15<br/>database 'db' on 5432")]
        end
        FlaskApp --> Static
        FlaskApp -->|"psycopg2"| PG
    end
    Browser -->|"host port 80 to container 5000"| FlaskApp
    HostVol -.->|"bind mount to /data"| PG
```

### 3.6.1 Development Tools and Environment

**Backend development** relies on the Flask CLI configured by `.flaskenv` (`FLASK_APP=app.py`, `FLASK_ENV=development`) and a local Python virtual environment (`venv`, excluded via `.gitignore`). The frontend `package.json` even provides a convenience `start-api` script — `cd .. && venv/bin/flask run --no-debugger` — to launch the backend from the frontend directory during development.

**Frontend development** uses the Create React App dev server via the `start` script (`react-scripts start`). The `"proxy": "http://localhost:5000"` setting in `frontend/package.json` transparently forwards the client's relative `/api/*` calls to the local Flask server, avoiding cross-origin issues during development. Linting is provided by CRA's built-in ESLint configuration (`eslintConfig` extends `react-app` and `react-app/jest`); there is no separate Python linter/formatter configuration in the repository.

The `.gitignore` codifies the expected developer workflow — ignoring `node_modules`, `venv`, `/coverage`, `__pycache__`, `.env.local`/`.env.*.local`, npm/yarn debug logs, and `/data` — confirming a mixed Python-venv + Node/npm local environment.

### 3.6.2 Build System

The system has two distinct build paths that meet at Flask's static folder:

- **Frontend build.** `react-scripts build` compiles the React source under `frontend/src/` into an optimized static bundle at `frontend/build/` (containing `index.html`, `asset-manifest.json`, PWA `manifest.json`, and hashed `static/` assets). A pre-built `frontend/build/` is present in the repository.
- **Backend build.** There is no separate compilation step; the "build" is dependency installation — `pip3 install -r requirements.txt` — performed inside the Docker image.

**Component integration requirement.** Because `api/__init__.py` configures Flask with `static_folder='../frontend/build'` and `static_url_path='/'`, the compiled frontend must exist at `frontend/build/` for the single Flask process to serve the SPA at `/` alongside the `/api/*` routes. The frontend build therefore has to be produced (via `react-scripts build`) before the backend can serve the UI — the two components are coupled through that build directory, which is why a compiled build is committed to the repository.

### 3.6.3 Containerization

Containerization is the primary deployment mechanism. The **`Dockerfile`** builds the backend image `FROM python:3.11-slim-buster`, sets `WORKDIR /app`, installs the native build prerequisites (`apt-get install libpq-dev gcc`) for `psycopg2`, installs the pinned Python dependencies, copies the repository, exposes port `5000`, and sets `CMD ["python3", "app.py"]`.

**`docker-compose.yml`** (Compose file format `version "3"`) wires two services:

| Service | Key configuration | Purpose |
|---|---|---|
| `api` | `build: .`, `restart: on-failure`, `depends_on: postgres`, `NODE_OPTIONS=--openssl-legacy-provider`, `ports "80:5000"`, `volumes .:/app/` | Runs the Flask app image; maps host port 80 to container 5000; bind-mounts the repo |
| `postgres` | `image: postgres:15`, `ports "5432:5432"`, `POSTGRES_USER/PASSWORD/DB`, `volumes ./data:/data` | Provides the PostgreSQL 15 database |

**Runtime caveat.** The container `CMD` launches Flask's built-in **development server** (`python3 app.py` → `app.run(host='0.0.0.0')`), not the `gunicorn` production server that is present in `requirements.txt`. Consequently the deployed process is the Flask dev server bound to all interfaces on port 5000, exposed to the host on port 80. A single Flask process serves both the JSON API and the static React build (single-origin delivery), which is why the production frontend can issue relative `fetch('/api/...')` requests without the CRA dev proxy.

### 3.6.4 CI/CD Pipeline

**None.** The repository contains no continuous-integration or continuous-deployment configuration of any kind: there is no `.github/` directory (and therefore no GitHub Actions workflows), no `Jenkinsfile`, and no GitLab/Travis/CircleCI configuration. The only automation/orchestration artifact is `docker-compose.yml`, so building and deploying is a manual operation (for example, `docker-compose up --build`). Because the project also has **no automated tests** (no `*.test.*`, no `test_*.py`, no `setupTests.js`), there is likewise no test gate that a pipeline could enforce. Establishing a CI/CD pipeline, a production-grade WSGI server invocation, and externalized secrets would be prerequisites for a hardened production deployment, but none of these are present in the current codebase.


## 3.7 References

The following repository files, directories, and external sources were examined as evidence for the technology-stack determinations in §3.1–§3.6.

### 3.7.1 Repository Files

- `app.py` - Flask launcher (`from api import app`; `app.run(host='0.0.0.0')`); established the Python entry point and dev-server runtime.
- `requirements.txt` - The 23 exactly-pinned PyPI backend dependencies and their versions (Flask 2.0.1, SQLAlchemy 1.4.19, pandas 2.0.0, gunicorn 20.1.0, psycopg2, etc.).
- `Dockerfile` - Backend image definition: `python:3.11-slim-buster` base (Python 3.11), `libpq-dev`/`gcc` build deps, `pip3 install`, `EXPOSE 5000`, `CMD python3 app.py`.
- `docker-compose.yml` - The two-service stack (`api`, `postgres:15`), port mappings (`80:5000`, `5432:5432`), `NODE_OPTIONS` flag, hard-coded DB credentials, and volume wiring.
- `.dockerignore` - Confirmed `/frontend/node_modules`, `/venv`, `/data` are excluded from the image build.
- `.flaskenv` - `FLASK_APP=app.py`, `FLASK_ENV=development`; established the Flask CLI/dev configuration.
- `.gitignore` - The mixed venv + node_modules developer workflow and `/data` exclusion.
- `README.md` - System purpose (Billboard Hot 100), the external weekly ingestion script, and the Spotipy/Spotify Web API enrichment description.
- `api/__init__.py` - Flask app factory: `static_folder='../frontend/build'`, `CORS(app)`, the `postgresql://postgres:postgres@postgres/db` DSN, `db`/`ma` initialization.
- `api/models.py` - The `Tracks` and `YearlyAvg` ORM models and their Marshmallow schemas.
- `api/routes.py` - The six routes and their read-only ORM query patterns.
- `api/funcs.py` - The pandas-based aggregation helpers (`get_query_week`, `get_rolling_avg` using `rolling(5)`, `get_weekly_data`).
- `frontend/package.json` - The 12 declared npm dependencies and versions, `scripts` (including `start-api`), `browserslist`, `eslintConfig`, and the `proxy` setting.
- `frontend/package-lock.json` - Established exact resolved/locked npm versions for reproducible frontend builds.
- `frontend/public/index.html` - The SPA host document (title "Hot Stuff").
- `frontend/src/index.js` - React bootstrap (`ReactDOM.render` in `StrictMode`); confirmed plain JavaScript.
- `frontend/src/App.js` - The tabbed SPA shell using React function components/hooks.
- `frontend/src/styles/index.css` - The single global stylesheet (alongside styled-components).
- `frontend/src/components/tracks/TracksSection.js` - Native `fetch('/api/week/...')` usage (not axios).
- `frontend/src/components/tracks/RadarChart.js` - `@amcharts/amcharts4` RadarChart usage.
- `frontend/src/components/trends/TrendsSection.js` - Native `fetch('/api/analysis/...')` and the Spotify docs hyperlink.
- `frontend/src/components/trends/LineChart.js` - `@amcharts/amcharts4` XYChart with two line series.
- `frontend/src/components/trends/features.json` - JSON audio-feature glossary (static content).
- `frontend/src/components/navigation/Sidebar.js`, `Tab.js`, `SmallTab.js`, `Section.js` - `styled-components` CSS-in-JS usage.
- `frontend/src/components/about/AboutSection.js` - The external-source descriptions and documentation links (Billboard, Spotipy, Spotify audio-features).

### 3.7.2 Repository Directories

- `api/` - The Python/Flask backend package (four modules) confirming the entire server tier is Python.
- `frontend/` - The Create React App project root.
- `frontend/src/` - The JavaScript SPA source; grepped to confirm actual vs. declared library usage (fetch, amCharts, styled-components in use; axios/plotly/web-vitals/Testing-Library unused).
- `frontend/build/` - The committed compiled React bundle served by Flask (`index.html`, `asset-manifest.json`, `manifest.json`, `static/`).
- `frontend/public/` - CRA public assets (`index.html`, `manifest.json`, `favicon.ico`).

### 3.7.3 External Web Sources

- [web] PyPI — Flask project page (pypi.org/project/Flask) - Confirmed the current stable Flask release (3.1.3, Feb 2026) and that Flask supports Python 3.9+, used to contextualize the repo's Flask 2.0.1 version currency.
- [web] React versions (react.dev/versions) and npm `react` package - Confirmed the current React release line (19.x, latest 19.2.7) and React 18 as the recommended production LTS, used to contextualize the repo's React 17.0.2.
- [web] PostgreSQL versioning policy (postgresql.org) and endoflife.date/Instaclustr - Confirmed the latest stable PostgreSQL (18.4) and that major versions are supported five years, establishing that the repo's PostgreSQL 15 remains community-supported.


# 4. Process Flowchart

## 4.1 System Workflows

This section documents the runtime workflows of the **Hot Stuff** Billboard Hot 100 analytics application exactly as they are implemented in the repository. All flows are grounded in the Flask route layer (`api/routes.py`), the pure aggregation helpers (`api/funcs.py`), and the React single-page application (`frontend/src/`). The end-to-end container/database topology is diagrammed in **Section 1.2.2.2** and the inter-feature dependency map in **Section 2.4.1**; the diagrams below are deliberately distinct and focus on *process sequencing, decision logic, and data movement*.

Two architectural facts shape every workflow and are established directly by the code:

- **The application is read-only at runtime.** No route in `api/routes.py` performs an `INSERT`, `UPDATE`, or `DELETE`; every handler issues a `SELECT` through the SQLAlchemy ORM. The database is populated exclusively by an **external, out-of-repository** weekly ingestion pipeline described in `README.md`.
- **All in-application interactions are synchronous HTTP request/response.** There is no message queue, event bus, WebSocket, scheduler, or background worker anywhere in `api/` or `frontend/src/`. The only asynchronous cadence in the overall system is the external weekly scraper.

### 4.1.1 Core Business Processes

The product surfaces three user-facing experiences, but only two of them are true end-to-end data journeys. Per **Section 2.4.1**, the React UI consumes just two of the backend's data endpoints:

| Business Process | Journey | UI → API → Data | Requirements |
|---|---|---|---|
| Browse a week's Hot 100 | Weekly Chart Retrieval | Tracks tab (F-007) → `GET /api/week/<week>` (F-001) → `Tracks` table | F-007-RQ-001…003, F-001-RQ-001…003 |
| Analyze a feature over time | Audio-Feature Trend Analysis | Trends tab (F-008) → `GET /api/analysis/<feature>` (F-002) → `YearlyAvg` table | F-008-RQ-001…003, F-002-RQ-001…003 |
| Read project information | Informational | About tab (F-009) — static, no data fetch | F-009-RQ-001 |

All three are hosted inside the single-origin SPA delivered by `GET /` (F-006) and switched by the navigation shell (F-010).

#### 4.1.1.1 High-Level System Workflow

The following swim-lane flowchart shows the complete end-to-end path from the browser through the Flask API, the aggregation helpers, and PostgreSQL, plus the external weekly batch that seeds the data. Edge labels on the API lanes indicate the internal call order within each route handler.

```mermaid
flowchart TD
    subgraph Browser["Web Browser / End User"]
        B1["Open root URL<br/>GET /"]
        B2["React SPA shell renders<br/>App.js: activeTab=0, nav=false"]
        B3{"Which tab<br/>is active?"}
        B4["Tracks: pick a week in DatePicker<br/>then click Go"]
        B5["Trends: pick a feature in FeatureSelect<br/>then click Go"]
        B6["About: read static content"]
        B7["Render radar chart<br/>+ ranked song list"]
        B8["Render line chart<br/>+ feature glossary"]
    end

    subgraph Flask["Flask API - api/routes.py, container port 5000"]
        A0["index(): send_static_file index.html"]
        A1["get_tracks_by_week(week)"]
        A2["get_avg_feature(feature)"]
    end

    subgraph Helpers["Aggregation Helpers - api/funcs.py"]
        H1["get_query_week()"]
        H2["get_weekly_data()"]
        H3["get_rolling_avg()"]
    end

    subgraph Data["PostgreSQL 15 - service postgres"]
        T[("Tracks")]
        Y[("YearlyAvg")]
    end

    subgraph Ext["External pipeline - out of repository"]
        E1["Weekly Billboard scraper<br/>+ Spotipy enrichment"]
    end

    E1 -->|"weekly batch INSERT"| T
    E1 -->|"weekly batch INSERT"| Y

    B1 --> A0
    A0 -->|"index.html + hashed JS/CSS"| B2
    B2 --> B3
    B3 -->|"Tracks id 0"| B4
    B3 -->|"Trends id 1"| B5
    B3 -->|"About id 3"| B6
    B4 -->|"fetch /api/week/:week"| A1
    B5 -->|"fetch /api/analysis/:feature"| A2

    A1 -->|"step 1: normalize date"| H1
    A1 -->|"step 2: SELECT by week, order by rank"| T
    A1 -->|"step 3: weekly means + avgTempo"| H2
    A1 -->|"JSON: week, songs, averages, avgTempo"| B7

    A2 -->|"step 1: SELECT year + feature column"| Y
    A2 -->|"step 2: rolling average, drop NaN"| H3
    A2 -->|"JSON: feature, data"| B8
```

#### 4.1.1.2 End-to-End User Journeys

- **Journey 1 — Weekly Chart Browsing (default landing).** On first load, `App.js` renders with `activeTab=0`, so the Tracks view is visible. `TracksSection.js` runs a mount-time `useEffect` that calls `getData('2021-11-13')`, immediately fetching the default week (F-007-RQ-001). The user may then select any date between `1958-07-27` and `2021-11-13` in `DatePicker.js` and click **Go** to trigger a refetch (F-007-RQ-002). The response object populates the amCharts radar (`data.averages`) and the scrollable ranked list (`data.songs`, rendered as rank/artist/track rows) in `RadarChart.js` / `TracksSection.js`.
- **Journey 2 — Trend Analysis.** When the user clicks the Trends tab (`activeTab=1`), `TrendsSection.js` mounts and its `useEffect` calls `getData('tempo')`, fetching the default feature (F-008-RQ-001). Selecting one of the seven options in `FeatureSelect.js` and clicking **Go** refetches for that feature (F-008-RQ-002). The `data.data` series drives the amCharts line chart with its "Annual Average" and "3 Year Rolling Average" lines (`LineChart.js`), and the glossary is rendered from the static `features.json`.
- **Journey 3 — About.** Clicking the About tab (`activeTab=3`) renders `AboutSection.js`, a stateless component with no data fetch (F-009-RQ-001).

#### 4.1.1.3 Decision Points

Every branch point in the code base is enumerated below. There are no server-side branching validations; the decision logic is concentrated in the week-normalization helper and the client-side fetch handlers.

| Decision Point | Location | Branches |
|---|---|---|
| Active tab dispatch | `App.js` `handleClick` | `parseInt(e.target.id) !== activeTab` → switch view + close nav; otherwise no-op |
| Saturday-week alignment | `api/funcs.py` `get_query_week` | weekday ∈ {Sun, Mon, Tue} **or** (Wed before 10:00) → previous Saturday; else → next Saturday |
| Date-submit guard | `DatePicker.js` `handleSubmit` | `if (inputValue)` truthy → call `submitFunc`; else → do nothing |
| Feature-submit guard | `FeatureSelect.js` `handleSubmit` | `if (value)` present → call `submitFunc`; else → do nothing |
| HTTP status check | `TracksSection.js` / `TrendsSection.js` `getData` | `response.status > 299` → set `error = response.statusText`; else → parse JSON |
| Empty-payload check | `TracksSection.js` / `TrendsSection.js` `getData` | `data.length === 0` → `error = 'No Data Found'`; else → store payload (see note) |
| Render state gate | `TracksSection.js` / `TrendsSection.js` JSX | `error` → error heading; `!isLoaded` → `. . .`; `isLoaded && !error` → data render |

> **Behavioral note:** The `data.length === 0` empty-payload check is effectively dead code for the two UI endpoints, because `GET /api/week` and `GET /api/analysis` each return a JSON **object** (`{week, songs, averages, avgTempo}` and `{feature, data}` respectively), whose `.length` is `undefined`. Consequently `undefined === 0` is always false and the flow always takes the "store payload" branch. Empty/missing-data handling therefore relies solely on the HTTP status check.

#### 4.1.1.4 Error Handling Paths (Overview)

Error handling is minimal and split across the two tiers; the detailed error flowcharts appear in **Section 4.5**:

- **Backend:** Route handlers in `api/routes.py` contain **no** `try/except`. Malformed dates (`strptime` → `ValueError`), unknown feature names (`getattr` → `AttributeError`), empty aggregation inputs (`data[0]` → `IndexError`), and database unavailability (SQLAlchemy `OperationalError`) all propagate as unhandled exceptions that Werkzeug returns as **HTTP 500**.
- **Frontend:** `getData` inspects `response.status` and, on any status `> 299`, surfaces `response.statusText` as an on-screen error heading. There is **no** `try/catch` around `fetch`, so a network-level failure (e.g., API unreachable) becomes an unhandled promise rejection rather than a rendered error state.
- **Infrastructure:** The `api` service in `docker-compose.yml` is configured with `restart: on-failure`, providing process-level recovery if the Flask process exits with an error.

### 4.1.2 Integration Workflows

The system has a small, well-defined integration surface. Integrations operate at two distinct cadences: a **weekly batch** that loads the database (external), and **on-demand HTTP** request/response between the SPA and the API.

#### 4.1.2.1 Data Flow Between Systems

```mermaid
flowchart LR
    subgraph WeeklyBatch["Weekly batch cadence - external, out of repository"]
        S1["Billboard Hot 100 web page"]
        S2["Scraper script<br/>(runs weekly)"]
        S3["Spotipy client -><br/>Spotify audio features"]
    end

    subgraph OnDemand["On-demand cadence - per HTTP request"]
        C1["React SPA<br/>native fetch()"]
        AP["Flask API<br/>api/routes.py"]
    end

    DB[("PostgreSQL 15<br/>Tracks + YearlyAvg")]

    S1 --> S2
    S3 --> S2
    S2 -->|"weekly INSERT of chart rows"| DB
    C1 -->|"GET /api/week, /api/analysis"| AP
    AP -->|"SQLAlchemy SELECT"| DB
    DB -->|"result rows"| AP
    AP -->|"JSON payload"| C1
```

#### 4.1.2.2 API Interactions

The complete HTTP contract exposed by `api/routes.py` is summarized below. All endpoints are unauthenticated `GET` requests. During development, browser calls to `/api/*` are transparently forwarded by the Create React App proxy `"proxy": "http://localhost:5000"` (`frontend/package.json`); in production the SPA and API are same-origin (F-006).

| Endpoint | Handler | Consumer | Response Shape |
|---|---|---|---|
| `GET /` | `index()` | Browser (app shell) | `index.html` + hashed assets |
| `GET /api/` | `home()` | Any client | HTTP 302 redirect to `week/<current Saturday>` |
| `GET /api/week/<week>` | `get_tracks_by_week()` | Tracks view (F-007) | `{week, songs[], averages[], avgTempo}` |
| `GET /api/analysis/<feature>` | `get_avg_feature()` | Trends view (F-008) | `{feature, data[]}` (HTTP 200 explicit) |
| `GET /api/track/<spotify_id>` | `get_track_by_id()` | None (API only) | JSON array of track objects |
| `GET /api/artist/<artist>` | `get_tracks_by_artist()` | None (API only) | JSON array of track objects |

#### 4.1.2.3 Event Processing Flows

There is **no event-driven processing** in this repository. A code-level review of `api/` and `frontend/src/` finds no message broker, publish/subscribe mechanism, WebSocket, server-sent events, Celery/RQ worker, or in-process event emitter. The only user-facing "events" are DOM interactions (tab clicks, form submits) handled synchronously by React, and the only server "events" are inbound HTTP requests. Accordingly, no event-processing sequence can be documented — its absence is itself a design characteristic of this synchronous, request/response application.

#### 4.1.2.4 Batch Processing Sequences

The single batch process in the overall system is the **external weekly ingestion pipeline** documented in `README.md`, which is *not part of this repository*. Its described sequence is:

```mermaid
flowchart TD
    W0(["Weekly trigger<br/>(external schedule)"])
    W1["Scrape the Billboard Hot 100 page<br/>for the current week"]
    W2["For each charting song, call Spotipy<br/>to fetch Spotify audio features"]
    W3["Write rows into the database<br/>(Tracks; YearlyAvg aggregates)"]
    W4(["Database ready for API reads"])

    W0 --> W1 --> W2 --> W3 --> W4
```

This application contains **no in-repository batch jobs, cron definitions, schema migrations, or seed scripts**; it assumes the `Tracks` and `YearlyAvg` tables are already populated (a critical success factor noted in **Section 1.2.3.3**). The only batch-adjacent artifact inside the repository is the frontend production build produced by `react-scripts build` (`frontend/build`), which is a one-time compile step rather than a recurring data pipeline.


## 4.2 Core Feature Process Flows

This section provides a detailed process flow for each core feature. For the two data-bearing user journeys (F-001/F-007 and F-002/F-008) both a **process flowchart** (with system boundaries, decision diamonds, user touchpoints, and error states) and an **integration sequence diagram** are provided. Every step is traceable to `api/routes.py`, `api/funcs.py`, `api/models.py`, or the corresponding `frontend/src/components/` module.

Because the repository defines **no SLAs, latency budgets, or throughput targets** (Sections 1.2.3.1 and 2.3), the "Timing" notes below describe only *observable* execution characteristics — the number of database round-trips, the size of the in-memory aggregation, and the runtime that serves the request — rather than contractual guarantees.

### 4.2.1 Weekly Chart Retrieval and Tracks Visualization (F-001, F-005, F-007)

This is the application's default landing journey. The Tracks view (`frontend/src/components/tracks/`) fetches `GET /api/week/<week>` (F-001), which normalizes the requested date to a Saturday-aligned chart week, reads the `Tracks` table, and returns the ranked songs together with derived per-feature averages.

#### 4.2.1.1 Detailed Process Flow

The flowchart spans both tiers; the `Flask handler` subgraph marks the server-side system boundary. Nodes outside it execute in the browser (`TracksSection.js`, `DatePicker.js`).

```mermaid
flowchart TD
    Start([User action]) --> Src{"Trigger source?"}
    Src -->|"component mount (useEffect)"| Def["getData('2021-11-13')"]
    Src -->|"Go clicked"| Guard{"DatePicker: inputValue truthy?"}
    Guard -->|no| Noop([No request sent])
    Guard -->|yes| Def2["getData(selectedDate)"]
    Def --> Pre["setIsLoaded(false); setError(false)"]
    Def2 --> Pre
    Pre --> Fetch["fetch /api/week/:date"]

    subgraph API["Flask handler: get_tracks_by_week(week)"]
        Norm["get_query_week(week)"]
        NormDec{"parses as YYYY-MM-DD?"}
        Align{"Sun/Mon/Tue, or Wed before 10:00?"}
        LastSat["week = previous Saturday"]
        NextSat["week = next Saturday"]
        Query["SELECT tracks WHERE week ORDER BY rank"]
        QDec{"any songs returned?"}
        Agg["get_weekly_data: 5 means x100 + avgTempo"]
        Build["jsonify: week, songs, averages, avgTempo"]
        Err["unhandled exception"]
    end

    Fetch --> Norm
    Norm --> NormDec
    NormDec -->|"no (ValueError)"| Err
    NormDec -->|yes| Align
    Align -->|yes| LastSat
    Align -->|no| NextSat
    LastSat --> Query
    NextSat --> Query
    Query --> QDec
    QDec -->|"no (KeyError in aggregation)"| Err
    QDec -->|yes| Agg
    Agg --> Build

    Build -->|"HTTP 200"| Status{"response.status > 299?"}
    Err -->|"HTTP 500"| Status
    Status -->|yes| ShowErr["setError(statusText); setIsLoaded(true)"]
    Status -->|no| Parse["data = await response.json()"]
    Parse --> Store["setData(data); setIsLoaded(true)"]
    Store --> Render["Render radar (data.averages)<br/>+ ranked list (data.songs)"]
    ShowErr --> RenderErr["Render error heading"]
    Render --> Done([Rendered])
    RenderErr --> Done
```

#### 4.2.1.2 Integration Sequence

```mermaid
sequenceDiagram
    actor User
    participant SPA as TracksSection (React)
    participant API as Flask get_tracks_by_week
    participant F as api/funcs.py
    participant DB as PostgreSQL (Tracks)

    User->>SPA: pick week + click Go
    SPA->>SPA: setIsLoaded(false)#59; setError(false)
    SPA->>API: GET /api/week/:week
    API->>F: get_query_week(week)
    F-->>API: Saturday-aligned week label
    API->>DB: SELECT * FROM tracks WHERE week=? ORDER BY rank
    DB-->>API: song rows (schema-serialized)
    API->>F: get_weekly_data(songs)
    F-->>API: averages[] + avgTempo
    API-->>SPA: 200 JSON (week, songs, averages, avgTempo)
    SPA->>SPA: setData(data)#59; setIsLoaded(true)
    SPA-->>User: radar chart + scrollable ranked list
```

#### 4.2.1.3 Current-Week Redirect (F-005)

`GET /api/` (`home()`) is a convenience entry point that computes the current chart week from the server clock and issues a **relative HTTP 302** to the weekly endpoint (F-005-RQ-001). It shares the `get_query_week` helper with F-001.

```mermaid
flowchart LR
    C(["GET /api/"]) --> H["home(): get_query_week(None) -> datetime.today()"]
    H --> R["302 redirect to week/current-Saturday"]
    R --> W(["GET /api/week/current-Saturday (F-001)"])
```

#### 4.2.1.4 System Boundaries, Validation, and Timing

- **System boundary:** The browser communicates with the Flask process over HTTP only; the Flask process reaches PostgreSQL over the SQLAlchemy DSN `postgresql://postgres:postgres@postgres/db` (`api/__init__.py`).
- **Validation (business rules):** The week is normalized to a Saturday to match Billboard's weekly cadence (F-001-RQ-002); songs are ordered by ascending `rank` (F-001-RQ-001); `averages` scale each of five features by ×100 with a fixed `full=100`, and `avgTempo` is an integer mean (F-001-RQ-003).
- **User touchpoints:** the `DatePicker` `<input type='date'>` (min `1958-07-27`, max `2021-11-13`) and the **Go** button.
- **Error states:** malformed date → `ValueError` → HTTP 500; an out-of-dataset week that yields zero songs → `get_weekly_data` raises during aggregation → HTTP 500; a non-2xx response surfaces `response.statusText` in the UI.
- **Timing (observed):** one ORM `SELECT` for a single week (~100 rows) plus a small pandas aggregation, served synchronously by the Flask development server (`app.py` → `app.run`). No response caching, cache-control headers, or pagination are configured on the API route.

### 4.2.2 Audio-Feature Trend Analysis and Trends Visualization (F-002, F-008)

The Trends view (`frontend/src/components/trends/`) fetches `GET /api/analysis/<feature>` (F-002), which resolves the requested feature to a `YearlyAvg` column, reads the pre-aggregated yearly series, computes a rolling average, and returns both series for the amCharts line chart.

#### 4.2.2.1 Detailed Process Flow

```mermaid
flowchart TD
    Start([User action]) --> Src{"Trigger source?"}
    Src -->|"component mount (useEffect)"| Def["getData('tempo')"]
    Src -->|"Go clicked"| Guard{"FeatureSelect: value present?"}
    Guard -->|no| Noop([No request sent])
    Guard -->|yes| Def2["getData(feature)"]
    Def --> Pre["setIsLoaded(false); setError(false)"]
    Def2 --> Pre
    Pre --> Fetch["fetch /api/analysis/:feature"]

    subgraph API["Flask handler: get_avg_feature(feature)"]
        Resolve["getattr(YearlyAvg, feature)"]
        RDec{"feature is a valid column?"}
        Query["SELECT year, feature FROM yearly_avg"]
        Dump["YearlyAvgSchema(many=True).dump"]
        EDec{"result rows exist?"}
        Roll["get_rolling_avg: rolling(5) mean, drop NaN window"]
        Build["jsonify: feature, data (HTTP 200)"]
        Err["unhandled exception"]
    end

    Fetch --> Resolve
    Resolve --> RDec
    RDec -->|"no (AttributeError)"| Err
    RDec -->|yes| Query
    Query --> Dump
    Dump --> EDec
    EDec -->|"no (IndexError on data[0])"| Err
    EDec -->|yes| Roll
    Roll --> Build

    Build -->|"HTTP 200"| Status{"response.status > 299?"}
    Err -->|"HTTP 500"| Status
    Status -->|yes| ShowErr["setError(statusText); setIsLoaded(true)"]
    Status -->|no| Parse["data = await response.json()"]
    Parse --> Store["setData(data); setIsLoaded(true)"]
    Store --> Render["Render line chart (data.data):<br/>Annual + 3 Year Rolling series"]
    ShowErr --> RenderErr["Render error heading"]
    Render --> Done([Rendered])
    RenderErr --> Done
```

#### 4.2.2.2 Integration Sequence

```mermaid
sequenceDiagram
    actor User
    participant SPA as TrendsSection (React)
    participant API as Flask get_avg_feature
    participant F as api/funcs.py
    participant DB as PostgreSQL (YearlyAvg)

    User->>SPA: pick feature + click Go
    SPA->>SPA: setIsLoaded(false)#59; setError(false)
    SPA->>API: GET /api/analysis/:feature
    API->>API: getattr(YearlyAvg, feature)
    API->>DB: SELECT year, feature FROM yearly_avg
    DB-->>API: yearly rows (schema-serialized)
    API->>F: get_rolling_avg(data)
    F-->>API: value + rolling series (leading NaN dropped)
    API-->>SPA: 200 JSON (feature, data)
    SPA->>SPA: setData(data)#59; setIsLoaded(true)
    SPA-->>User: line chart + audio-feature glossary
```

#### 4.2.2.3 System Boundaries, Validation, and Timing

- **Validation (business rules):** the requested feature is resolved to a model column via `getattr(YearlyAvg, feature)`, not string-built SQL (F-002-RQ-003); the rolling window is `rolling(5)` in code although labeled "3 Year Rolling Average" in the UI and `README.md` (a documented inconsistency, Section 1.2.3); rows in the incomplete leading window (`NaN`) are dropped (F-002-RQ-002).
- **Client-side constraint:** `FeatureSelect.js` restricts the choice to seven features (`tempo, energy, danceability, instrumentalness, liveness, speechiness, acousticness`), so the UI never sends an invalid feature; the server itself performs **no allow-listing** — a direct call such as `/api/analysis/notacolumn` raises `AttributeError` → HTTP 500.
- **Error states:** invalid feature → `AttributeError` → 500; empty query result → `get_rolling_avg` accesses `data[0]` → `IndexError` → 500; non-2xx → `response.statusText` shown in the UI.
- **Timing (observed):** a single ORM `SELECT` of two columns across the yearly-aggregate rows plus one pandas `.rolling(5).mean()` pass; synchronous; no caching.

### 4.2.3 Auxiliary Data-Access APIs (F-003, F-004)

Two endpoints exist in `api/routes.py` but have **no front-end consumer** (Section 2.4.1); they are reachable only by direct API clients and are documented descriptively in the About view. Both return a plain JSON **array** (via `jsonify` on a `TrackSchema(many=True)` dump) and both return an **empty array** (not an error) when there is no match.

```mermaid
flowchart TD
    subgraph TrackFlow["GET /api/track/:spotify_id  (F-003)"]
        TA(["API client request"])
        TB["Tracks.query.filter_by(spotify_id).order_by(rank).all()"]
        TC["TrackSchema(many=True).dump -> jsonify"]
        TD{"any exact match?"}
        TE(["JSON array, ordered by rank"])
        TF(["empty array []"])
    end

    subgraph ArtistFlow["GET /api/artist/:artist  (F-004)"]
        AA(["API client request"])
        AB["filter lower(artist) LIKE lower(%artist%)"]
        AC["order_by week DESC .all()"]
        AD["TrackSchema(many=True).dump -> jsonify"]
        AE{"any substring match?"}
        AF(["JSON array, newest week first"])
        AG(["empty array []"])
    end

    TA --> TB --> TC --> TD
    TD -->|yes| TE
    TD -->|no| TF
    AA --> AB --> AC --> AD --> AE
    AE -->|yes| AF
    AE -->|no| AG
```

**Validation and boundaries.** F-003 performs an exact-equality match on `spotify_id` (F-003-RQ-001). F-004 performs a case-insensitive substring `LIKE '%…%'` match ordered newest-week-first (F-004-RQ-001); the leading-wildcard `LIKE` is not index-optimizable, and `%`/`_` metacharacters in the query value are **not** sanitized (they behave as wildcards). Both bind their inputs through the SQLAlchemy ORM rather than raw SQL, and both are public, unauthenticated `GET`s.

### 4.2.4 Single-Origin SPA Delivery and Navigation (F-006, F-009, F-010)

The compiled React app is delivered by the same Flask process that serves the API (F-006): `Flask(__name__, static_folder='../frontend/build', static_url_path='/')` in `api/__init__.py`, with `index()` returning `index.html`. After the shell loads, all view switching is **client-side** local state in `App.js` (F-010); no further server round-trip occurs for navigation, and the About view (F-009) performs no fetch.

```mermaid
flowchart TD
    U([User navigates to site]) --> G1["GET /"]
    G1 --> IDX["index(): app.send_static_file('index.html')"]
    IDX --> Assets["Browser loads hashed JS/CSS<br/>via static_url_path='/'"]
    Assets --> Boot["index.js: ReactDOM.render(App) into #root"]
    Boot --> Shell["App.js: nav=false, activeTab=0"]
    Shell --> ShowTracks["Section activeTab===0 visible (Tracks);<br/>others display:none"]
    ShowTracks --> Interact{"User interaction?"}
    Interact -->|"tab click"| HC["handleClick: parseInt(e.target.id)"]
    HC --> Diff{"id !== activeTab?"}
    Diff -->|no| NoopN([no-op])
    Diff -->|yes| Set["setActiveTab(id); setNav(false)"]
    Set --> Reveal["matching Section shown; others hidden"]
    Interact -->|"hamburger click"| Ham["showNav: setNav(!nav)"]
    Ham --> Side["Sidebar opacity toggled by nav<br/>(min-width 800px: always visible, 15vw)"]
    NoopN --> Interact
    Reveal --> Interact
    Side --> Interact
```

**Validation and boundaries.** Tabs map to fixed ids — Tracks `0`, Trends `1`, About `3` (id `2` is intentionally unused); `activeTab` updates only when a *different* id is clicked, so re-clicking the active tab is a no-op (F-010-RQ-001). The `Section` wrapper applies `display:none` to inactive views rather than unmounting them, so the Tracks and Trends `useEffect` fetches fire once on initial mount and their state persists across tab switches. Static assets carry content-hashed filenames (CRA build), enabling long-lived browser caching; the API JSON routes set no explicit cache headers.

## 4.3 Validation Rules, Authorization, and Compliance Checkpoints

This section consolidates the business rules, data-validation behavior, authorization posture, and compliance obligations that apply at each step of the workflows above. The over-arching finding — verified across `api/routes.py`, `frontend/src/`, and the per-feature validation tables in **Section 2.3** — is that **all meaningful input validation is performed client-side**, the server performs **no request validation, authentication, or authorization**, and **no regulatory-compliance controls are defined** anywhere in the repository.

### 4.3.1 Business Rules at Each Step

| Workflow Step | Business Rule | Source |
|---|---|---|
| Week normalization | Any date resolves to a Saturday-aligned chart week; Sun/Mon/Tue (and Wed before 10:00) map to the **previous** Saturday, otherwise the **next** Saturday | `api/funcs.py` `get_query_week` |
| Weekly song ordering | Songs are returned ordered by ascending `rank` | `api/routes.py` `get_tracks_by_week` |
| Weekly averages | Five features (`energy, danceability, speechiness, acousticness, instrumentalness`) scaled ×100 with `full=100`; `avgTempo` is an integer mean | `api/funcs.py` `get_weekly_data` |
| Trend feature resolution | The requested feature must name a `YearlyAvg` column (resolved via `getattr`) | `api/routes.py` `get_avg_feature` |
| Rolling average | `rolling(5)` mean; rows in the incomplete leading window (`NaN`) are dropped | `api/funcs.py` `get_rolling_avg` |
| Artist search | Case-insensitive substring match, ordered newest-week-first | `api/routes.py` `get_tracks_by_artist` |
| Track lookup | Exact `spotify_id` equality, ordered by `rank` | `api/routes.py` `get_track_by_id` |
| Date selection bounds | Selectable dates constrained to `1958-07-27` … `2021-11-13` | `frontend/src/components/tracks/DatePicker.js` |
| Tab navigation | `activeTab` changes only on a *different* id; ids are Tracks `0`, Trends `1`, About `3` (id `2` unused) | `frontend/src/App.js` `handleClick` |

### 4.3.2 Data Validation Requirements

Validation is asymmetric: the React UI applies guards that keep the requests it originates well-formed, but the Flask endpoints accept whatever reaches them and rely on Python/pandas to raise on bad input.

| Input | Client-Side Validation | Server-Side Validation |
|---|---|---|
| Week date | HTML5 `<input type='date'>` `min`/`max` bounds + `if (inputValue)` truthy submit guard (`DatePicker.js`) | `datetime.strptime(date, '%Y-%m-%d')` format check only — malformed → `ValueError` → HTTP 500; **no** range or allow-list check |
| Feature | Fixed seven-option `<select>` + `if (value)` truthy submit guard (`FeatureSelect.js`) | `getattr(YearlyAvg, feature)` column resolution — unknown → `AttributeError` → HTTP 500; **no** allow-list |
| `spotify_id` | Not applicable (no UI) | None — any string accepted; non-match returns an empty array |
| `artist` | Not applicable (no UI) | None — `LIKE` metacharacters (`%`, `_`) are **not** sanitized and act as wildcards |

The following flowchart contrasts the validated UI path with an unvalidated direct-API path and shows the single server-side "checkpoint" — which is really just Python raising on unusable input:

```mermaid
flowchart TD
    Entry{"Request origin?"}
    Entry -->|"via React UI"| UI["Client guards applied:<br/>date min/max, truthy submit,<br/>fixed feature list"]
    Entry -->|"direct API call"| Direct["No client guards applied"]
    UI --> Server["Flask route handler<br/>(api/routes.py)"]
    Direct --> Server
    Server --> NoMw["No auth middleware<br/>No request-schema validation<br/>No input allow-list"]
    NoMw --> Coerce{"Input usable at runtime?"}
    Coerce -->|"valid date + real column + DB reachable"| OK(["200 / 302 response"])
    Coerce -->|"malformed date / unknown feature /<br/>empty result set / DB unreachable"| Fail(["Unhandled exception -> HTTP 500"])
```

### 4.3.3 Authorization Checkpoints

There are **no authorization checkpoints** in this system. A review of `api/`, `frontend/src/`, and `app.py` finds no login, session, token, API key, role, or permission logic. All six routes in `api/routes.py` are public, unauthenticated `GET` requests, corroborated by every feature's "Security Requirements" row in **Section 2.3** ("Public, unauthenticated `GET`"). Two related observations:

- **CORS is fully permissive.** `CORS(app)` in `api/__init__.py` is applied with no origin restrictions, allowing cross-origin access to the API.
- **The only credential in the repository is the database password.** The PostgreSQL username/password (`postgres`/`postgres`) appears in `docker-compose.yml` and in the DSN in `api/__init__.py`; it authenticates the API-to-database connection, not any end user.

```mermaid
flowchart LR
    Anyone(["Any HTTP client<br/>(no credentials)"]) --> Route["Flask route<br/>(no auth guard)"]
    Route --> Data[("PostgreSQL<br/>(API-owned credentials only)")]
    Route --> Resp(["Response returned to any caller"])
```

### 4.3.4 Regulatory Compliance Checks

**No regulatory-compliance controls are defined in the repository.** Every feature's "Compliance Requirements" row in **Section 2.3** reads "None defined in the repository," and a code review confirms there is no PII handling, consent capture, audit logging, data-retention enforcement, or geographic-restriction logic. This is consistent with the data domain: the application serves **public** Billboard chart rankings and Spotify audio-feature aggregates (`README.md`), and the single external reference to Spotify (in `TrendsSection.js`) is a display-only documentation hyperlink (`rel='noopener noreferrer'`), not a runtime data exchange. No compliance decision points therefore appear in any workflow.


## 4.4 State Management and Transaction Boundaries

State in this system lives almost entirely in the browser as React component state; the Flask backend is effectively **stateless** and **read-only**. There is no server-side session, no application-level cache, and no write transaction anywhere in the code base.

### 4.4.1 Frontend State Management

All frontend state is local React `useState`; there is no Redux, Context, or external store. Two independent state scopes exist.

**Shell navigation state (`App.js`).** The shell owns `nav` (boolean sidebar-open flag, initial `false`) and `activeTab` (integer, initial `0`). `showNav` toggles `nav`; `handleClick` sets `activeTab` to the clicked tab id **only when it differs** from the current value and simultaneously closes the sidebar (`setNav(false)`). The `activeTab` transitions are:

```mermaid
stateDiagram-v2
    [*] --> Tracks: activeTab=0 (initial)
    Tracks --> Trends: click Trends (id 1)
    Tracks --> About: click About (id 3)
    Trends --> Tracks: click Tracks (id 0)
    Trends --> About: click About (id 3)
    About --> Tracks: click Tracks (id 0)
    About --> Trends: click Trends (id 1)
```

Re-clicking the already-active tab is a no-op (the `id !== activeTab` guard). The `nav` boolean is an orthogonal state toggled by the `Hamburger` control and forced back to `false` on any tab change; on screens wider than `800px` the sidebar is always visible regardless of `nav` (`Sidebar.js` media query).

**Data-fetch state (`TracksSection.js` and `TrendsSection.js`).** Each section maintains three values — `data` (initial `[]`), `isLoaded` (initial `false`), and `error` (initial `null`) — which together form a small fetch state machine driven by `getData`:

```mermaid
stateDiagram-v2
    [*] --> Loading: mount, useEffect getData(default)
    Loading --> Loaded: 2xx response, setData(data), isLoaded=true
    Loading --> Errored: non-2xx, error=statusText, isLoaded=true
    Loaded --> Loading: submit new week/feature (isLoaded=false, error=false)
    Errored --> Loading: submit new week/feature (isLoaded=false, error=false)
```

Two behaviors are notable and evidenced in the code:

- **State is retained across tab switches.** `Section.js` hides inactive views with `display:none` rather than unmounting them, so a section's `data`/`isLoaded`/`error` persist while another tab is active, and the mount-time `useEffect` fetch fires only **once** per session.
- **The "empty" transition is unreachable for the two UI endpoints.** The `data.length === 0` branch that would set `error='No Data Found'` never fires for the object-shaped `/api/week` and `/api/analysis` responses (see the behavioral note in Section 4.1.1.3), so in practice the machine moves only between `Loading`, `Loaded`, and `Errored`.

### 4.4.2 Backend State, Persistence, and Transaction Boundaries

The Flask service holds no per-user or cross-request state. Application objects (`app`, `db`, `ma`, the schema instances in `api/routes.py`) are created once at import time and shared read-only across requests.

| Concern | Observed Behavior | Evidence |
|---|---|---|
| Server session state | None; every request is independent (no session, cookies, or mutated globals) | `api/`, `app.py` |
| ORM session | Flask-SQLAlchemy manages a scoped session per request, torn down at request end | `api/__init__.py` (`db = SQLAlchemy(app)`) |
| Transaction boundary | Implicit, read-only transaction per request; **no** `commit`/`rollback` in code because there are no writes | `api/routes.py` (handlers use only `.query…​.all()` / `.with_entities`) |
| Data persistence points | `Tracks` and `YearlyAvg` tables in PostgreSQL, populated by the external pipeline | `api/models.py`, `README.md` |
| Volume persistence | PostgreSQL data mapped via `./data:/data` with a top-level named volume `data` | `docker-compose.yml` |
| Change tracking | `SQLALCHEMY_TRACK_MODIFICATIONS = False` (removes event overhead; not a data store) | `api/__init__.py` |

Because the application never issues an `INSERT`/`UPDATE`/`DELETE`, there are no multi-statement transaction boundaries, no optimistic-locking or versioning logic, and no compensating actions to document. The database's own durability (the mounted volume) is the sole persistence guarantee, and the freshness of that data depends entirely on the out-of-repository weekly writer.

### 4.4.3 Caching

The repository configures **no application-level caching**. There is no Redis, Memcached, `Flask-Caching`, HTTP `Cache-Control` header, or in-process memoization on any API route — each request re-queries PostgreSQL and re-runs the pandas aggregation. The caching that does exist is incidental to the delivery mechanism:

- **Browser asset caching:** the Create React App production build emits content-hashed filenames under `frontend/build/static`, which are long-cacheable by the browser; Flask serves them through `static_url_path='/'` (`api/__init__.py`).
- **In-memory chart state:** amCharts holds the current radar/line dataset in the browser for the lifetime of the mounted component (`RadarChart.js`, `LineChart.js`); it is replaced on each successful fetch and is not a persistent cache.

No caching requirement, invalidation strategy, or TTL is defined anywhere in the code base.


## 4.5 Error Handling and Recovery Flows

Error handling in this repository is deliberately minimal and consistent across features. The backend has **no exception handling** (no `try/except`, no `@app.errorhandler`), so all failures become Werkzeug **HTTP 500** responses; the frontend inspects only the HTTP status code and renders a single error heading. There is **no logging, monitoring, alerting, automated retry, or data fallback** anywhere in `api/` or `frontend/src/`. Recovery is user-driven (resubmit) and, at the process level, container-driven (`restart: on-failure`).

### 4.5.1 Error Classification and Propagation

| Error Source | Trigger | Mechanism | User-Visible Result |
|---|---|---|---|
| Malformed date | `strptime(date, '%Y-%m-%d')` on a non-matching string | Unhandled `ValueError` | HTTP 500 → UI shows `statusText` |
| Unknown feature | `getattr(YearlyAvg, feature)` for a non-column | Unhandled `AttributeError` | HTTP 500 → UI shows `statusText` |
| Empty analysis result | `get_rolling_avg` reads `data[0]` on an empty list | Unhandled `IndexError` | HTTP 500 |
| Empty week result | `get_weekly_data` aggregates an empty song list | Unhandled `KeyError` / `ValueError` | HTTP 500 |
| Database unreachable | Connection failure at query time | Unhandled SQLAlchemy `OperationalError` | HTTP 500 |
| HTTP error (any status > 299) | Backend returned 4xx/5xx | Frontend `response.status > 299` check | `error` set to `response.statusText`, rendered as a heading |
| Network failure | `fetch` promise rejects (API unreachable) | **Not** caught (no `try/catch`) | Unhandled promise rejection; **no** error UI is shown |

### 4.5.2 Backend Error Handling Flow

The backend has a single implicit error path: any exception raised inside a route handler propagates to Werkzeug, which returns a generic HTTP 500. No error is logged to an external system and no retry is attempted.

```mermaid
flowchart TD
    Req(["Inbound GET request"]) --> Handler["Route handler executes<br/>(no try/except)"]
    Handler --> Op{"Operation outcome?"}
    Op -->|"success"| OK(["2xx JSON or 302 redirect"])
    Op -->|"strptime ValueError"| Ex["Exception raised"]
    Op -->|"getattr AttributeError"| Ex
    Op -->|"empty data[0] IndexError"| Ex
    Op -->|"DB OperationalError"| Ex
    Ex --> WZ["Werkzeug default error handling"]
    WZ --> R500(["HTTP 500 response"])
    R500 --> NoLog["No application logging,<br/>alerting, or retry"]
```

> The Flask process is started via `python3 app.py` → `app.run(host='0.0.0.0')` (the Werkzeug development server). The local development script `start-api` invokes `flask run --no-debugger` (`frontend/package.json`), i.e. the interactive debugger is explicitly disabled, so a 500 is returned rather than an interactive traceback page in that mode.

### 4.5.3 Frontend Error Handling Flow

`getData` in both `TracksSection.js` and `TrendsSection.js` distinguishes only two outcomes after the network call — an HTTP error status, or a parseable body. Crucially, the `fetch` call is **not** wrapped in `try/catch`, so a transport-level failure is not converted into a rendered error state.

```mermaid
flowchart TD
    Call(["getData(input)"]) --> Reset["setIsLoaded(false); setError(false)"]
    Reset --> Fetch["await fetch(/api/endpoint/param)"]
    Fetch --> NetDec{"network reachable?"}
    NetDec -->|"no (fetch rejects)"| Unhandled(["Unhandled promise rejection<br/>- no error heading shown"])
    NetDec -->|"yes"| StatusDec{"response.status > 299?"}
    StatusDec -->|"yes"| SetErr["setError(response.statusText);<br/>setIsLoaded(true)"]
    StatusDec -->|"no"| Parse["data = await response.json()"]
    Parse --> Store["setData(data); setIsLoaded(true)"]
    SetErr --> ShowErr["Render h1.error heading"]
    Store --> ShowData["Render chart + list/glossary"]
    ShowErr --> Recover{"user submits again?"}
    Recover -->|"yes"| Call
    Recover -->|"no"| Stay(["error heading remains"])
```

The user-facing error notification is the styled `<h1 className='error'>{error}</h1>` heading defined in each section and styled by the `.error` class in `frontend/src/styles/index.css`; while a request is in flight the `.loading` heading renders `. . .`.

### 4.5.4 Retry, Fallback, and Error Notification

| Capability | Status in Repository | Detail |
|---|---|---|
| Automated retry | **Not implemented** | No retry loop, exponential backoff, or retry library; a failed request stays failed until the user acts |
| Fallback / degraded mode | **Not implemented** | On error the sections do not substitute cached or default data; the chart simply retains or shows empty data while the error heading is displayed |
| Error notification | **In-UI only** | A single on-screen heading shows `response.statusText` or (for the unreachable empty check) `'No Data Found'`; there is no toast, email, Slack, or error-tracking (e.g., Sentry) integration |
| Observability | **None** | No structured logging, metrics, tracing, or health-check endpoint anywhere in `api/` |

### 4.5.5 Recovery Procedures

Two recovery mechanisms exist, at different layers:

- **User-driven (application layer):** After an error heading appears, the user re-selects a week (`DatePicker`) or feature (`FeatureSelect`) and clicks **Go**, which re-invokes `getData` and drives the fetch state machine back through `Loading` (Section 4.4.1). This is the only application-level recovery path.
- **Process-driven (infrastructure layer):** The `api` service declares `restart: on-failure` in `docker-compose.yml`, so if the Flask **process** exits with a non-zero status the container is restarted. Per-request 500s do not exit the process, so this policy protects only against process-level crashes, not against individual failed requests.

The startup/recovery interaction with the database is shown below. Note that `depends_on: postgres` orders container **start** but does **not** wait for PostgreSQL to be *ready to accept connections*, so a request issued before the database is ready will produce a 500 without crashing the API process:

```mermaid
flowchart TD
    Up(["docker compose up"]) --> DepOrder["api starts after postgres starts<br/>(depends_on: start order only)"]
    DepOrder --> Boot["api runs python3 app.py"]
    Boot --> FirstReq{"DB reachable at query time?"}
    FirstReq -->|"postgres not ready yet"| ReqFail["request -> HTTP 500<br/>(process stays up)"]
    FirstReq -->|"ready"| Serve(["serving requests"])
    ReqFail --> ProcDec{"process exited non-zero?"}
    ProcDec -->|"no (per-request error only)"| Serve
    ProcDec -->|"yes"| Restart["restart: on-failure<br/>restarts the container"]
    Restart --> Boot
```

There are no database migrations, seed scripts, or data-repair routines in the repository; if the `Tracks`/`YearlyAvg` tables are empty or stale, recovery depends entirely on the out-of-repository weekly ingestion pipeline re-populating them (Section 1.2.3.3).


## 4.6 References

The following repository artifacts were inspected directly to construct the workflows, flowcharts, sequence diagrams, and state diagrams in this section.

**Backend and infrastructure files**

- `app.py` - Confirmed the launcher runs `app.run(host='0.0.0.0')` (Werkzeug development server), the runtime that serves every request flow.
- `api/__init__.py` - Established the Flask bootstrap: single-origin static serving (`static_folder='../frontend/build'`, `static_url_path='/'`), `CORS(app)`, the PostgreSQL DSN, `SQLALCHEMY_TRACK_MODIFICATIONS=False`, and the shared `db`/`ma` objects.
- `api/routes.py` - Source of all six route flows; verified the absence of `try/except`, the redirect logic (F-005), and the JSON response composition for every endpoint.
- `api/funcs.py` - Established the decision logic in `get_query_week` (Saturday alignment), the aggregation in `get_weekly_data`, and the `rolling(5)` computation and NaN-drop in `get_rolling_avg`.
- `api/models.py` - Provided the `Tracks`/`YearlyAvg` models and `TrackSchema`/`YearlyAvgSchema` field sets that define the response shapes and persistence points.
- `Dockerfile` - Confirmed `EXPOSE 5000` and `CMD ["python3", "app.py"]`.
- `docker-compose.yml` - Established the `api`/`postgres` services, `restart: on-failure`, `depends_on: postgres`, port mappings, and the `./data` volume used in the recovery and persistence flows.
- `requirements.txt` - Confirmed the pinned runtime dependencies (Flask, pandas, SQLAlchemy, psycopg2, gunicorn) underpinning the backend flows.
- `README.md` - Source for the external weekly scraper + Spotipy ingestion (batch) sequence and the public data domain (compliance discussion).
- `.flaskenv` - Confirmed `FLASK_APP=app.py` / `FLASK_ENV=development` (runtime-mode context).

**Frontend files**

- `frontend/package.json` - Established the dev proxy `"proxy": "http://localhost:5000"` and the `start-api` script (`flask run --no-debugger`) referenced in the error-handling flow.
- `frontend/src/App.js` - Source of the shell navigation state machine (`nav`, `activeTab`, `handleClick`, `showNav`) and the `Section` rendering for tabs 0/1/3.
- `frontend/src/index.js` - Confirmed the React bootstrap (`ReactDOM.render` into `#root`) in the SPA-delivery flow.
- `frontend/src/components/tracks/TracksSection.js` - Source of the weekly-chart fetch/state/error flow and the mount-time default (`2021-11-13`).
- `frontend/src/components/tracks/DatePicker.js` - Established the client-side date validation (`min='1958-07-27'`, `max='2021-11-13'`, truthy submit guard).
- `frontend/src/components/tracks/RadarChart.js` - Confirmed the amCharts radar rendering fed by `data.averages`.
- `frontend/src/components/trends/TrendsSection.js` - Source of the trend-analysis fetch/state/error flow and the mount-time default (`tempo`).
- `frontend/src/components/trends/FeatureSelect.js` - Established the fixed seven-feature dropdown and truthy submit guard.
- `frontend/src/components/trends/LineChart.js` - Confirmed the two-series ("Annual Average" / "3 Year Rolling Average") line chart fed by `data.data`.
- `frontend/src/components/trends/features.json` - The static glossary rendered by the Trends view.
- `frontend/src/components/navigation/Sidebar.js` - Established the responsive sidebar behavior and tab ids used in the navigation flow.
- `frontend/src/components/navigation/Section.js` - Confirmed `display:none` for inactive views (state-retention behavior).
- `frontend/src/components/navigation/Hamburger.js` - Confirmed the `showNav` toggle touchpoint.
- `frontend/src/components/about/AboutSection.js` - Confirmed the static, no-fetch About view (F-009).
- `frontend/src/styles/index.css` - Source of the `.error` and `.loading` heading styles used for in-UI error notification.

**Folders**

- `api/` - The Flask backend package (bootstrap, models, routes, helpers) driving all server-side flows.
- `frontend/src/components/tracks/` - The Tracks-view module (weekly chart journey).
- `frontend/src/components/trends/` - The Trends-view module (trend-analysis journey).
- `frontend/src/components/navigation/` - The navigation shell (tabs, sidebar, hamburger, section visibility).
- `frontend/build/` - The compiled CRA static assets served at `/` by Flask.

**Cross-referenced specification sections**

- `1.2 System Overview` - System topology (1.2.2.2), success criteria, and the documented rolling-window inconsistency (1.2.3).
- `2.2 Feature Catalog` - Feature definitions F-001 … F-010 used to scope the process flows.
- `2.3 Functional Requirements` - Requirement IDs (F-XXX-RQ-YYY) and per-feature validation-rule tables cited throughout Sections 4.2 and 4.3.
- `2.4 Feature Relationships` - Integration points, the feature dependency map, and shared/common services informing Section 4.1.


# 5. System Architecture

## 5.1 High-Level Architecture

### 5.1.1 System Overview

The system is a **two-tier, single-origin web application**: a monolithic **Flask** backend (the `api` service) that exposes a small read-only JSON HTTP API *and* serves a compiled **React 17** single-page application (SPA), backed by a single **PostgreSQL 15** database (the `postgres` service). The whole stack is packaged and coordinated as a **Docker Compose stack** (`docker-compose.yml`, `Dockerfile`). Data is written into the database by an **external, out-of-repository weekly ingestion pipeline** (a Billboard scraper with Spotipy audio-feature enrichment described in `README.md`); the application itself never writes to the database and never makes outbound third-party calls at runtime.

**Architecture style and rationale.** Within that two-tier boundary the backend follows a conventional **layered architecture** with clearly separated responsibilities across four files: a configuration/bootstrap layer (`api/__init__.py`), an HTTP route layer (`api/routes.py`), a data-model + serialization layer (`api/models.py`), and a stateless aggregation-helper layer (`api/funcs.py`). The choice of a small monolith is consistent with the evidence of a single-author portfolio project — there is no service mesh, message broker, or inter-service RPC anywhere in the tree; every capability is reachable in-process. The single most consequential structural decision is that the Flask instance is created with `static_folder='../frontend/build'` and `static_url_path='/'` (`api/__init__.py`), so **one process serves both the API and the SPA from one origin**, eliminating a separate web server or CDN in the deployed footprint.

**Key architectural principles and patterns observed in the code:**

- **Layered separation of concerns** — bootstrap, routing, models/schemas, and pure helper functions are isolated by file (`api/__init__.py`, `api/routes.py`, `api/models.py`, `api/funcs.py`).
- **Stateless, read-only request handling** — every route in `api/routes.py` performs only `.query…all()` / `.with_entities(...)` reads; there is no session state, no `commit`/`rollback`, and no server-side cache.
- **ORM + schema-serialization pattern** — SQLAlchemy models (`Tracks`, `YearlyAvg`) are decoupled from their JSON wire representation by Marshmallow schemas (`TrackSchema`, `YearlyAvgSchema`) whose `Meta.fields` control serialization.
- **Read/write path separation** — the deployed application owns only the read path; the write path (database population) is externalized to the weekly pipeline, so the two never share code, only the database.
- **Single-origin SPA delivery** — the compiled CRA build is served by Flask static serving, so production requires no cross-origin configuration even though `CORS(app)` is enabled permissively.
- **Component-based SPA with local state** — the React client is composed of feature components (Tracks, Trends, About, navigation) driven entirely by React `useState`, with no global store.
- **Convention-over-configuration tooling** — Create React App (`react-scripts` 4.0.3) and Flask supply the build, dev-server, and routing conventions rather than bespoke infrastructure.

**System boundaries and major interfaces.** The application presents exactly three boundaries:

- **Northbound (client interface):** HTTP/JSON to the web browser via six routes declared in `api/routes.py` — `GET /` (SPA shell), `GET /api/` (302 redirect to the current week), `GET /api/week/<week>`, `GET /api/analysis/<feature>`, `GET /api/track/<spotify_id>`, and `GET /api/artist/<artist>`. The `api` service is published on host port **80 → container port 5000** (`docker-compose.yml`).
- **Southbound (persistence interface):** SQLAlchemy over `psycopg2` to PostgreSQL using the hard-coded DSN `postgresql://postgres:postgres@postgres/db` (`api/__init__.py`); the `postgres` service publishes port **5432** (`docker-compose.yml`).
- **Ingestion boundary (shared database):** the external weekly pipeline writes `Tracks` and `YearlyAvg` rows directly into PostgreSQL; it integrates through the database only, with no API contract in this repository (`README.md`, `api/models.py`).

The layered decomposition and the read-versus-write path separation are summarized below.

```mermaid
flowchart TD
    subgraph Client["Presentation Tier - Web Browser"]
        SPA["React 17 SPA shell<br/>Tracks / Trends / About"]
        Charts["amCharts4 radar + line charts<br/>styled-components layout"]
    end

    subgraph ApiService["Application Tier - api service (Flask, host 80 to container 5000)"]
        Boot["Bootstrap & Config<br/>api/__init__.py"]
        RouteLayer["HTTP Route Layer<br/>api/routes.py (6 GET routes)"]
        Helpers["Aggregation Helpers<br/>api/funcs.py (pandas)"]
        ModelLayer["ORM Models + Marshmallow Schemas<br/>api/models.py"]
        StaticServe["Static Delivery<br/>Flask static_folder = frontend/build"]
    end

    subgraph DataTier["Persistence Tier - postgres service"]
        PG[("PostgreSQL 15 'db'<br/>Tracks, YearlyAvg")]
    end

    subgraph ExternalPath["External Write Path - not in this repository"]
        Pipeline["Weekly Billboard scraper<br/>+ Spotipy enrichment"]
    end

    SPA --> Charts
    SPA -->|"fetch JSON over HTTP (read path)"| RouteLayer
    Boot --> RouteLayer
    Boot --> StaticServe
    StaticServe -->|"index.html + hashed JS/CSS"| SPA
    RouteLayer --> Helpers
    RouteLayer --> ModelLayer
    ModelLayer -->|"SQLAlchemy ORM via psycopg2"| PG
    Pipeline -->|"weekly writes (out of repo)"| PG
```

### 5.1.2 Core Components

The system decomposes into the following core components. Because the section format limits tables to four columns, the component inventory is presented as a responsibilities/dependencies table followed by a companion table of integration points and critical considerations.

| Component | Primary Responsibility | Key Dependencies |
|---|---|---|
| React SPA (`frontend/src/`) | Render the tab-based UI (Tracks, Trends, About), fetch data, and drive amCharts visualizations | React 17, `react-scripts` 4.0.3, styled-components, `@amcharts/amcharts4`, native `fetch` |
| Flask bootstrap (`api/__init__.py`) | Create the app, enable CORS, configure the PostgreSQL DSN, initialize SQLAlchemy + Marshmallow, register routes, serve the React build | Flask 2.0.1, Flask-SQLAlchemy, Flask-Marshmallow, Flask-CORS |
| HTTP route layer (`api/routes.py`) | Define the six routes and compose JSON / redirect / static responses | `api/models.py`, `api/funcs.py`, `sqlalchemy.func` |
| Data models & schemas (`api/models.py`) | Declare `Tracks` and `YearlyAvg` ORM models and their Marshmallow serialization schemas | Flask-SQLAlchemy, Flask-Marshmallow |
| Aggregation helpers (`api/funcs.py`) | Normalize dates to chart weeks, compute weekly feature means, and derive rolling averages | pandas 2.0.0, Python `datetime` |
| PostgreSQL database (`postgres` service) | Persist chart rows and yearly aggregates | `postgres:15` image, mounted `./data` volume |
| Container orchestration (`Dockerfile`, `docker-compose.yml`) | Build the API image and run the API + database services together | Docker, Docker Compose v3 |
| External ingestion pipeline (out of repo) | Weekly Billboard scrape + Spotipy enrichment that populates the database | Described in `README.md`; not present in the tree |

| Component | Integration Points and Critical Considerations |
|---|---|
| React SPA (`frontend/src/`) | Consumes `/api/week` and `/api/analysis` via `fetch`; served same-origin in production, via dev proxy `http://localhost:5000` in development. Only two of six endpoints are surfaced in the UI; `axios`, `plotly.js`, and `react-plotly.js` are declared but unused. |
| Flask bootstrap (`api/__init__.py`) | Hard-coded DSN targets Docker host `postgres`; `CORS(app)` is fully permissive; `SQLALCHEMY_TRACK_MODIFICATIONS=False`. No environment-variable override for credentials or host. |
| HTTP route layer (`api/routes.py`) | Entry point for all client traffic; contains **no** `try/except`, input validation, or explicit 404/400 handling, so bad input surfaces as HTTP 500. |
| Data models & schemas (`api/models.py`) | The response contract (`data.songs`, `data.averages`, `data.data`) must stay aligned with the SPA; `YearlyAvg` omits `loudness`; `Tracks.__init__` omits `spotify_id`. |
| Aggregation helpers (`api/funcs.py`) | Pure and stateless; `get_rolling_avg` uses `.rolling(5)` while the UI legend/README say "3 Year Rolling Average" (documented inconsistency); empty inputs raise unhandled exceptions. |
| PostgreSQL database (`postgres` service) | No schema-creation/migration code in the repo — DDL and data are owned by the external pipeline; durability rests on the mounted volume. |
| Container orchestration | Runs the Flask **development server** (`CMD python3 app.py`), not the pinned `gunicorn`; `depends_on` orders start but does not wait for DB readiness; bind-mounts the whole repo into `/app/`. |
| External ingestion pipeline (out of repo) | The application is fully dependent on this pipeline for data freshness and correctness; its absence leaves the tables empty and endpoints returning empty results or 500s. |

### 5.1.3 Data Flow Description

**Primary data flows.** All runtime flows are read-oriented and initiated by the browser:

- **Application-shell delivery.** A `GET /` request is handled by `index()` (`api/routes.py`), which returns `app.send_static_file('index.html')` from `frontend/build`; the browser then loads the content-hashed JS/CSS bundle through Flask static serving at `static_url_path='/'`.
- **Weekly chart retrieval.** On mount, the Tracks view issues `fetch('/api/week/2021-11-13')`. `get_tracks_by_week` normalizes the date to a Saturday-aligned week via `get_query_week`, queries `Tracks.query.filter_by(week=week).order_by(Tracks.rank)`, serializes with `TrackSchema(many=True)`, then calls `get_weekly_data` to compute per-feature means and average tempo, returning the JSON object `{week, songs, averages, avgTempo}` that drives the radar chart and ranked list.
- **Trend analysis retrieval.** On mount, the Trends view issues `fetch('/api/analysis/tempo')`. `get_avg_feature` reads `YearlyAvg.query.with_entities(YearlyAvg.year, getattr(YearlyAvg, feature))`, serializes with `YearlyAvgSchema(many=True)`, and passes the result to `get_rolling_avg` before returning `{feature, data}` for the line chart.
- **Auxiliary reads (endpoint-only).** `GET /api/track/<spotify_id>` and `GET /api/artist/<artist>` return serialized `Tracks` lists but are not surfaced anywhere in the SPA.
- **Current-week redirect.** `GET /api/` computes the current week with `get_query_week(None)` and issues a relative HTTP 302 to `week/<current-Saturday>`.
- **External write flow.** Outside the repository, the weekly pipeline scrapes Billboard and enriches tracks with Spotify audio features (via Spotipy) and writes rows into `Tracks` and `YearlyAvg`.

**Integration patterns and protocols.** Client/server communication is **HTTP with JSON payloads** using the browser-native `fetch` API; requests are same-origin in production and proxied to `http://localhost:5000` during development (`frontend/package.json`). Server/database communication uses the **SQLAlchemy ORM over `psycopg2`** against the fixed DSN in `api/__init__.py`. Cross-origin access is granted broadly by `CORS(app)`. The external pipeline integrates by a **shared-database pattern** — it and the application communicate only through the PostgreSQL tables, never through an API.

**Data transformation points.** Data is reshaped at four well-defined points:

- **Date normalization** — `get_query_week` maps any requested date (or "today") to a Saturday-aligned chart-week label, reflecting Billboard's weekly cadence.
- **ORM-to-JSON serialization** — Marshmallow schemas project ORM rows to the wire format defined by each schema's `Meta.fields`.
- **Weekly aggregation** — `get_weekly_data` computes `int(mean × 100)` for `energy`, `danceability`, `speechiness`, `acousticness`, and `instrumentalness` (with a constant `full: 100` baseline) plus an integer `avgTempo`; only five of the nine stored features are aggregated for the radar view.
- **Rolling-average derivation** — `get_rolling_avg` builds a pandas DataFrame, computes a 5-period rolling mean, converts `NaN` to `None`, and drops the leading rows where the rolling value is `NaN`.

On the client, each section maps the returned JSON into amCharts data arrays (`data.averages` → radar; `data.data` → line).

**Key data stores and caches.** The **only persistent data store** is the PostgreSQL `db` database holding the `Tracks` and `YearlyAvg` tables, persisted through the `./data` mount declared in `docker-compose.yml`. The repository configures **no application-level cache** — there is no Redis, Memcached, Flask-Caching, HTTP `Cache-Control`, or in-process memoization, so every request re-queries the database and re-runs the pandas aggregation. The only caching present is incidental: content-hashed CRA static assets that browsers cache, and the in-memory amCharts dataset held by a mounted chart component for its lifetime.

### 5.1.4 External Integration Points

The deployed application's integration surface is deliberately small: it accepts inbound HTTP from browsers, reads from PostgreSQL, and depends on an out-of-repository pipeline for its data. It makes **no outbound third-party API calls at runtime** — the Spotify/Billboard references in the UI are informational hyperlinks, and Spotipy is not a dependency of this repository (`requirements.txt`, `frontend/src/components/trends/features.json`).

| System | Integration Type | Data Exchange Pattern | Protocol / Format |
|---|---|---|---|
| Web browser client | Inbound synchronous request/response | Client-initiated `fetch`; SPA served same-origin (dev proxy `:5000`) | HTTP/1.1; JSON, HTML, 302 redirect, hashed static assets |
| PostgreSQL database (`postgres:15`) | Outbound persistence (read-only) | Per-request ORM query; scoped session torn down at request end | PostgreSQL wire protocol via SQLAlchemy + `psycopg2` (DSN in `api/__init__.py`) |
| External weekly ingestion pipeline | Shared-database integration (out of repo) | Asynchronous weekly batch writes into `Tracks` / `YearlyAvg` | Direct SQL writes to PostgreSQL (no API contract in this repo) |
| Spotify Web API / Billboard | No runtime integration in this app | Consumed only by the external pipeline; surfaced as UI documentation links | N/A at runtime (informational hyperlinks only) |

**SLA requirements.** No service-level agreements, uptime targets, latency budgets, or throughput commitments are defined anywhere in the repository for any of these integration points. The only availability-adjacent mechanism present is the container-level `restart: on-failure` policy on the `api` service (`docker-compose.yml`), which restarts the process on a non-zero exit but is not a formal SLA. Consequently, the "SLA Requirements" dimension is documented here as **none defined** rather than fabricated.


## 5.2 Component Details

This section details each major component along five dimensions — purpose and responsibilities, technologies and frameworks, key interfaces and APIs, data persistence, and scaling considerations. Scaling statements describe only what is observable in the repository; where a scaling mechanism is absent it is stated as such rather than assumed.

### 5.2.1 Backend Application Components

The backend is the four-file `api/` package. All components are created once at import time and shared read-only across requests.

**Flask Application Bootstrap — `api/__init__.py`**

- **Purpose and responsibilities:** Construct the Flask app, enable CORS, configure the PostgreSQL connection, initialize the SQLAlchemy and Marshmallow extensions, and trigger route registration via `from api import routes`.
- **Technologies and frameworks:** Flask 2.0.1, Flask-SQLAlchemy 2.5.1, Flask-Marshmallow 0.14.0, Flask-Cors 3.0.10.
- **Key interfaces and APIs:** Exposes the module-level singletons `app`, `db`, and `ma` consumed by the other modules; sets `static_folder='../frontend/build'` and `static_url_path='/'` so the app doubles as the SPA's static server.
- **Data persistence:** Defines the DSN `postgresql://postgres:postgres@postgres/db` and sets `SQLALCHEMY_TRACK_MODIFICATIONS=False`; it holds no data itself.
- **Scaling considerations:** A single app object is instantiated per process; the DSN host (`postgres`) is hard-coded with no environment override, so scaling to multiple instances or an external database requires code changes rather than configuration.

**HTTP Route Layer — `api/routes.py`**

- **Purpose and responsibilities:** Declare the six routes and compose their responses (static file, redirect, or JSON).
- **Technologies and frameworks:** Flask routing/`jsonify`/`redirect`, SQLAlchemy `func` for case-insensitive matching, the ORM query API.
- **Key interfaces and APIs:** `GET /` (SPA shell), `GET /api/` (302 → current week), `GET /api/week/<week>`, `GET /api/analysis/<feature>`, `GET /api/track/<spotify_id>`, `GET /api/artist/<artist>`. Module-level schema instances `track_schema`, `tracks_schema`, `yearly_schema` are created once and reused.
- **Data persistence:** Issues only read queries (`.query…all()`, `.with_entities(...)`); no writes, commits, or rollbacks.
- **Scaling considerations:** Handlers are stateless and therefore replicable, but there is no pagination (a week returns up to its full ranked list; artist search returns every matching appearance), no rate limiting, and no `try/except`, so malformed input produces HTTP 500.

**Data Models & Serialization Schemas — `api/models.py`**

- **Purpose and responsibilities:** Define the `Tracks` and `YearlyAvg` ORM tables and the `TrackSchema`/`YearlyAvgSchema` Marshmallow schemas that shape JSON output.
- **Technologies and frameworks:** Flask-SQLAlchemy declarative models, Flask-Marshmallow schemas with explicit `Meta.fields`.
- **Key interfaces and APIs:** `Tracks` (id, week, rank, track, artist, spotify_id + nine audio-feature floats); `YearlyAvg` (index, year + eight feature floats, **no** `loudness`). `TrackSchema` exposes 15 fields; `YearlyAvgSchema` exposes year + eight features.
- **Data persistence:** Maps directly to the two PostgreSQL tables; contains no DDL, `create_all`, or migration logic — the schema is owned by the external pipeline.
- **Scaling considerations:** Schemas are thread-safe read-only singletons; no lazy/eager-loading tuning or indexing is defined in the repository (index definitions, if any, are external).

**Aggregation Helpers — `api/funcs.py`**

- **Purpose and responsibilities:** Provide the three pure functions `get_query_week` (Saturday-aligned week normalization), `get_weekly_data` (per-feature weekly means + average tempo), and `get_rolling_avg` (pandas rolling-mean series).
- **Technologies and frameworks:** Python `datetime`, pandas 2.0.0.
- **Key interfaces and APIs:** Called by `api/routes.py`; return plain Python structures (a date string, an averages dict, a list of records).
- **Data persistence:** None — stateless, in-memory computation only.
- **Scaling considerations:** CPU-bound pandas work is recomputed on **every** request with no memoization, so cost scales linearly with the per-request row count; empty inputs raise unhandled `IndexError`/`KeyError`/`ValueError`.

### 5.2.2 Frontend Presentation Components

The frontend is a Create React App SPA under `frontend/src/`, composed of a shell, navigation controls, and two data-driven feature views plus a static About view.

**Application Shell & Navigation — `App.js`, `components/navigation/`**

- **Purpose and responsibilities:** Own shell state (`nav` boolean, `activeTab` integer), route tab selection, and render the sidebar, title, and the active `Section`.
- **Technologies and frameworks:** React 17 `useState`, styled-components for `Sidebar`, `Tab`, `SmallTab`, `Section`.
- **Key interfaces and APIs:** `handleClick` sets `activeTab` (ids 0 Tracks, 1 Trends, 3 About; id 2 unused); `showNav` toggles the sidebar; `Section` hides inactive views with `display:none`; `Hamburger` toggles mobile navigation.
- **Data persistence:** None; state is in-memory React state, reset on reload.
- **Scaling considerations:** Purely client-side; served as cacheable static assets, so it scales with browser/CDN caching rather than server capacity.

**Tracks View — `components/tracks/` (`TracksSection`, `DatePicker`, `RadarChart`)**

- **Purpose and responsibilities:** Fetch a week's ranked songs and feature averages, and render a radar chart plus a ranked list.
- **Technologies and frameworks:** React `useState`/`useEffect`, native `fetch`, `@amcharts/amcharts4` RadarChart.
- **Key interfaces and APIs:** Consumes `GET /api/week/<date>`; `DatePicker` is an HTML5 `type=date` input bounded to `1958-07-27 … 2021-11-13`; defaults to and mounts with `2021-11-13`.
- **Data persistence:** Holds the fetched dataset in component state; `RadarChart` binds `data.averages` into the amCharts instance.
- **Scaling considerations:** `RadarChart` creates the amCharts instance **during render** with `chart.dispose()` commented out, so charts are re-instantiated on each render without cleanup — a client-side resource concern rather than a server-scaling one.

**Trends View — `components/trends/` (`TrendsSection`, `FeatureSelect`, `LineChart`, `features.json`)**

- **Purpose and responsibilities:** Fetch a feature's annual and rolling averages and render a two-series line chart plus an audio-feature glossary.
- **Technologies and frameworks:** React `useState`/`useEffect`, native `fetch`, `@amcharts/amcharts4` XYChart with a `DateAxis`.
- **Key interfaces and APIs:** Consumes `GET /api/analysis/<feature>`; `FeatureSelect` offers seven features (tempo, energy, danceability, instrumentalness, liveness, speechiness, acousticness) and mounts with `tempo`.
- **Data persistence:** Holds the fetched series in component state; the glossary is bundled locally in `features.json`.
- **Scaling considerations:** Same render-time chart-creation pattern as the radar chart; the line-chart legend reads "3 Year Rolling Average" while the backend computes `.rolling(5)`.

**About View — `components/about/AboutSection.js`**

- **Purpose and responsibilities:** Present static informational content and outbound documentation links (Billboard, Wikipedia, Spotipy, Spotify audio-features, amCharts, GitHub).
- **Technologies and frameworks:** Stateless React component; imports `Hamburger`.
- **Key interfaces and APIs:** No data fetching; links open with `target=_blank rel=noopener`.
- **Data persistence:** None.
- **Scaling considerations:** Fully static; negligible cost.

### 5.2.3 Data and Infrastructure Components

**PostgreSQL Database — `postgres` service**

- **Purpose and responsibilities:** Persist the `Tracks` and `YearlyAvg` tables that back every read endpoint.
- **Technologies and frameworks:** Official `postgres:15` image.
- **Key interfaces and APIs:** PostgreSQL wire protocol on port `5432`; reached by the API through SQLAlchemy + `psycopg2`.
- **Data persistence:** Durable via the `./data:/data` bind mount; a top-level named volume `data` is declared but not referenced by a service.
- **Scaling considerations:** A single database instance with no read replicas, no connection-pool tuning beyond SQLAlchemy defaults, and no in-repo indexes; vertical scaling of the container is the only lever present.

**Container Orchestration — `Dockerfile`, `docker-compose.yml`**

- **Purpose and responsibilities:** Build the API image (`python:3.11-slim-buster`) and run the `api` + `postgres` services together.
- **Technologies and frameworks:** Docker, Docker Compose v3.
- **Key interfaces and APIs:** Publishes `api` on host `80` → container `5000` and `postgres` on `5432`; `depends_on` orders start; `restart: on-failure` on `api`.
- **Data persistence:** Bind-mounts the repository into `/app/` and the DB data into `./data`.
- **Scaling considerations:** A single replica of each service is defined — there is no `deploy.replicas`, load balancer, or service discovery, and the container runs the **Flask development server** (`CMD python3 app.py`) rather than the pinned `gunicorn`, so process-level concurrency is limited and not production-tuned.

### 5.2.4 Component Interaction Diagram

The following diagram shows the internal module wiring and call/serve relationships between the frontend components, the backend package, and the database. It complements — rather than repeats — the deployment topology in Section 1.2 and the layered view in Section 5.1.

```mermaid
flowchart LR
    subgraph Frontend["React SPA - frontend/src"]
        AppShell["App.js<br/>nav + activeTab state"]
        Nav["navigation/<br/>Sidebar, Tab, SmallTab, Section, Hamburger"]
        TracksC["tracks/TracksSection.js"]
        TrendsC["trends/TrendsSection.js"]
        AboutC["about/AboutSection.js"]
        Radar["tracks/RadarChart.js"]
        Line["trends/LineChart.js"]
        Picker["tracks/DatePicker.js"]
        Selector["trends/FeatureSelect.js"]
    end

    subgraph Backend["Flask api service"]
        Init["__init__.py<br/>app, db, ma, CORS, DSN"]
        Routes["routes.py<br/>6 route handlers"]
        Models["models.py<br/>Tracks, YearlyAvg + schemas"]
        Funcs["funcs.py<br/>week / weekly / rolling helpers"]
    end

    DB[("PostgreSQL<br/>Tracks, YearlyAvg")]

    AppShell --> Nav
    AppShell --> TracksC
    AppShell --> TrendsC
    AppShell --> AboutC
    TracksC --> Picker
    TracksC --> Radar
    TrendsC --> Selector
    TrendsC --> Line
    TracksC -->|"fetch /api/week"| Routes
    TrendsC -->|"fetch /api/analysis"| Routes
    Init --> Routes
    Init --> Models
    Routes --> Models
    Routes --> Funcs
    Models -->|"SQLAlchemy ORM"| DB
    Init -->|"serves compiled build"| AppShell
```

### 5.2.5 State Transition Diagram — API Request Processing

The frontend fetch state machine and the navigation state machine are documented in Section 4.4. To avoid duplication, the diagram below models the complementary **backend** view: the processing states a single API request passes through inside a route handler, and the exception transitions that collapse to a Werkzeug HTTP 500 (the backend has no `try/except`).

```mermaid
stateDiagram-v2
    [*] --> Received: inbound GET, route matched
    Received --> Normalizing: week / analysis routes resolve week or feature
    Normalizing --> Querying: build SQLAlchemy read query
    Querying --> Aggregating: pandas helpers (week & analysis only)
    Querying --> Serializing: track & artist routes (no aggregation)
    Aggregating --> Serializing: Marshmallow dump then jsonify
    Serializing --> Responded: 2xx JSON (or 302 for /api/)
    Responded --> [*]
    Normalizing --> Failed: strptime ValueError / getattr AttributeError
    Querying --> Failed: SQLAlchemy OperationalError
    Aggregating --> Failed: IndexError / KeyError / ValueError
    Failed --> [*]: Werkzeug HTTP 500
```

### 5.2.6 Sequence Diagrams for Key Flows

The two UI-driving flows are shown as message sequences across the SPA, route layer, helpers, ORM/schemas, and PostgreSQL.

**Weekly chart retrieval (Tracks view → `GET /api/week/<week>`)**

```mermaid
sequenceDiagram
    participant B as React SPA (TracksSection)
    participant R as Flask get_tracks_by_week
    participant F as api/funcs.py
    participant M as Tracks ORM + TrackSchema
    participant DB as PostgreSQL
    B->>R: GET /api/week/2021-11-13
    R->>F: get_query_week("2021-11-13")
    F-->>R: Saturday-aligned week label
    R->>M: query.filter_by(week).order_by(rank).all()
    M->>DB: SELECT rows WHERE week ORDER BY rank
    DB-->>M: matching rows
    M-->>R: TrackSchema(many=True).dump(rows)
    R->>F: get_weekly_data(songs)
    F-->>R: averages (5 features) + avgTempo
    R-->>B: 200 JSON {week, songs, averages, avgTempo}
    B->>B: render Radar(data.averages) + ranked list
```

**Trend analysis retrieval (Trends view → `GET /api/analysis/<feature>`)**

```mermaid
sequenceDiagram
    participant B as React SPA (TrendsSection)
    participant R as Flask get_avg_feature
    participant M as YearlyAvg ORM + YearlyAvgSchema
    participant DB as PostgreSQL
    participant F as api/funcs.py
    B->>R: GET /api/analysis/tempo
    R->>M: with_entities(year, getattr(YearlyAvg, "tempo"))
    M->>DB: SELECT year, tempo FROM yearly_avg
    DB-->>M: yearly rows
    M-->>R: YearlyAvgSchema(many=True).dump(rows)
    R->>F: get_rolling_avg(data)
    F-->>R: [{year, value, rolling}] (rolling(5), NaN dropped)
    R-->>B: 200 JSON {feature, data}
    B->>B: render Line(data.data)
```


## 5.3 Technical Decisions

Because this is an existing system, the decisions below are **inferred from the implementation** and are presented with the evidence that supports them and the objective tradeoffs they carry. Where a capability was evidently *not* chosen (for example, caching or authentication), that omission is itself documented as a decision with consequences, not treated as an oversight to be invented around.

The following table summarizes the principal decision areas; each is expanded in the subsections that follow.

| Decision Area | Choice Evidenced in the Repo | Primary Tradeoff |
|---|---|---|
| Architecture style | Monolithic two-tier app; single origin serves API + SPA | Simplicity vs. coupled build/deploy/scaling |
| Communication pattern | Synchronous REST-style HTTP/JSON over native `fetch`; ORM to DB | Simple/cacheable vs. no push/real-time, no batching |
| Data storage | Relational PostgreSQL 15 via SQLAlchemy + precomputed `YearlyAvg` | Rich queries/aggregation vs. fixed schema owned externally |
| Caching | No application cache; recompute per request | Always-fresh & simple vs. repeated DB + pandas cost |
| Security | Public unauthenticated read; permissive CORS; ORM-parameterized queries | Frictionless access vs. no access control / hardening |

### 5.3.1 Architecture Style Decisions and Tradeoffs

The system is a **monolithic, two-tier, single-origin web application**. The decisive evidence is `api/__init__.py`, which creates one Flask process configured with `static_folder='../frontend/build'` and `static_url_path='/'`; that one process serves both the JSON API and the compiled React SPA. There is no separate web server, API gateway, service mesh, or second backend service anywhere in the tree.

- **Rationale (as evidenced):** The footprint matches a single-author portfolio project (footer "AUG | 2021"; a single GitHub link in the About view). A monolith minimizes moving parts — one image to build, one `depends_on` edge, one origin to reason about — which is coherent with the two-service `docker-compose.yml`.
- **Tradeoffs:** The API and SPA share a build and a deployment lifecycle and cannot be scaled independently; the layered file separation inside `api/` keeps concerns readable, but the whole backend must be redeployed for any change. A further consequence is that the read path (this repo) and the write path (the external weekly pipeline) are decoupled only through the shared database, so there is no single deployable that owns end-to-end data flow.

### 5.3.2 Communication Pattern Choices

Communication is **synchronous request/response** at every hop. The browser calls the API with the native `fetch` API over HTTP returning JSON (`frontend/src/components/tracks/TracksSection.js`, `.../trends/TrendsSection.js`); the API talks to PostgreSQL synchronously through the SQLAlchemy ORM (`api/routes.py`, `api/models.py`). There is no WebSocket, server-sent-event, message queue, task worker, or GraphQL layer in the repository.

- **Rationale (as evidenced):** The data is historical and read-only, so a simple pull-based REST-style contract is sufficient; `CORS(app)` keeps the dev proxy (`http://localhost:5000`) and same-origin production both workable without bespoke transport code.
- **Tradeoffs:** Synchronous pulls are easy to cache and debug but cannot push updates, batch requests, or select fields the way GraphQL could; each UI view issues exactly one mount-time request and re-requests on user action. Because handlers wrap no `try/except`, the "communication contract" for errors is implicit — any failure becomes an HTTP 500 that the client reads only as a status code.

### 5.3.3 Data Storage Solution Rationale

The storage engine is **relational PostgreSQL 15** accessed through **SQLAlchemy** with **Marshmallow** serialization (`docker-compose.yml`, `api/__init__.py`, `api/models.py`). Two tables are modeled: `Tracks` (row-per-song-per-week) and `YearlyAvg` (a **precomputed** per-year aggregate).

- **Rationale (as evidenced):** The domain is inherently tabular (rank, week, artist, audio features), and the trend view needs per-year aggregates; storing `YearlyAvg` as a materialized table lets the analysis endpoint read pre-aggregated rows instead of scanning all of `Tracks`. A relational store with an ORM also enables the case-insensitive `LIKE` artist query and the `order_by(rank)`/`order_by(week.desc())` ordering used in `api/routes.py`.
- **Tradeoffs:** A fixed relational schema is well-suited to this data but is **owned externally** — there is no `create_all`, migration, or seed logic in the repo, so schema evolution is coupled to the out-of-repo pipeline. The precomputed `YearlyAvg` trades storage and pipeline complexity for cheap reads, and notably omits `loudness`, so that feature cannot be trended even though it is stored on `Tracks`.

### 5.3.4 Caching Strategy Justification

The deliberate decision is **no application-level caching**. Section 4.4 confirms there is no Redis, Memcached, Flask-Caching, HTTP `Cache-Control`, or in-process memoization; each request re-queries PostgreSQL and re-runs the pandas aggregation.

- **Rationale (as evidenced):** For a low-traffic historical dataset, always recomputing from the source is the simplest correct behavior and avoids any cache-invalidation logic when the weekly pipeline updates the tables.
- **Tradeoffs:** Every `/api/week` and `/api/analysis` call pays the full DB-read + pandas cost, which does not amortize under load; the only caching that exists is **incidental** — content-hashed CRA static assets that browsers cache and the in-memory amCharts dataset held by a mounted component. No TTL, warm-up, or invalidation strategy is defined because none is needed by the current design.

### 5.3.5 Security Mechanism Selection

The security posture is **minimal and read-oriented**. All six routes are public `GET`s with no authentication or authorization; `CORS(app)` is applied permissively to all origins (`api/__init__.py`); the only credentials in the project are the hard-coded PostgreSQL username/password `postgres`/`postgres` in the DSN and in `docker-compose.yml`.

- **Mechanisms actually present:** Data access goes exclusively through the SQLAlchemy ORM, so query values are parameterized rather than string-concatenated into SQL — this mitigates classic SQL injection. The interactive debugger is disabled in the documented dev workflow (`flask run --no-debugger` in `frontend/package.json`), and `app.run` runs without `debug=True`.
- **Mechanisms deliberately absent:** No identity provider, session, token, or API key; no HTTPS/TLS termination in the repo (that would be an external reverse proxy, which is not present); no input allow-lists (`get_query_week`'s `strptime` and the `getattr(YearlyAvg, feature)` lookup accept arbitrary strings and raise on bad input); no rate limiting; and the artist `LIKE` filter does not escape `%`/`_` wildcard metacharacters (a wildcard-injection quirk, not SQL injection).
- **Tradeoffs:** The permissive, unauthenticated design maximizes convenience for a public read-only showcase but provides no confidentiality, integrity controls beyond the ORM, or abuse protection; hard-coded credentials and the whole-repo bind mount (`.:/app/`) are acceptable for local Compose but would be liabilities in any shared deployment.

### 5.3.6 Architecture Decision Records (ADRs)

The recurring decisions are captured below as concise ADRs. Each records the decision, the supporting evidence, and its consequences.

| ADR | Decision | Evidence | Consequences / Tradeoffs |
|---|---|---|---|
| ADR-01 | Monolithic two-tier app; Flask serves API **and** SPA from one origin | `api/__init__.py` (`static_folder`, `static_url_path='/'`) | Minimal ops surface; API + SPA cannot scale or deploy independently |
| ADR-02 | Synchronous REST-style HTTP/JSON via native `fetch`; ORM to DB | `TracksSection.js`, `TrendsSection.js`, `api/routes.py` | Simple & cacheable; no push/real-time; error contract is implicit (HTTP 500) |
| ADR-03 | Relational PostgreSQL + SQLAlchemy + precomputed `YearlyAvg` | `docker-compose.yml`, `api/models.py` | Cheap aggregate reads; schema owned externally; `loudness` not trendable |
| ADR-04 | No application caching; recompute every request | Absence in `requirements.txt`, `api/routes.py` (Section 4.4) | Always fresh, zero invalidation logic; full cost paid per request |
| ADR-05 | Public, unauthenticated access; permissive `CORS(app)` | `api/__init__.py`, `api/routes.py` | Frictionless read access; no access control or abuse protection |
| ADR-06 | Externalized weekly ingestion (read/write path separation) | `README.md`; no scraper/`spotipy` in repo | Small, focused app; correctness depends on the out-of-repo pipeline |
| ADR-07 | Run the Flask development server (not the pinned `gunicorn`) | `Dockerfile` `CMD ["python3","app.py"]`; `app.py` `app.run` | One-command run; not production-tuned for concurrency/hardening |
| ADR-08 | amCharts + styled-components on a CRA (React 17) SPA | `frontend/package.json`, `RadarChart.js`, `LineChart.js` | Rich charts with little code; `axios`/`plotly.js`/`react-plotly.js` declared but unused |

### 5.3.7 Architecture Decision Tree

The decision tree below reconstructs the reasoning path that yields the observed architecture; each branch corresponds to a decision recorded above. Branches marked "(not chosen)" indicate alternatives the code did not take.

```mermaid
flowchart TD
    Start(["Architecture decision drivers"]) --> Q1{"Multi-user / enterprise concerns<br/>(auth, tenancy, billing)?"}
    Q1 -->|"No - portfolio project"| Mono["Monolithic Flask app (ADR-01)"]
    Q1 -->|"Yes"| NA1["Split services + identity<br/>(not chosen)"]
    Mono --> Q2{"Serve the SPA from the<br/>same origin as the API?"}
    Q2 -->|"Yes"| Static["Flask static_folder serves<br/>frontend/build (ADR-01)"]
    Q2 -->|"No"| NA2["Separate web server / CDN<br/>(not chosen)"]
    Static --> Q3{"Does the app own<br/>the write path?"}
    Q3 -->|"No - external pipeline"| RO["Read-only API,<br/>shared-DB ingestion (ADR-06)"]
    Q3 -->|"Yes"| NA3["In-app scraper / writers<br/>(not chosen)"]
    RO --> Q4{"Relational aggregation needed<br/>(weekly & yearly means)?"}
    Q4 -->|"Yes"| PG["PostgreSQL + SQLAlchemy +<br/>precomputed YearlyAvg (ADR-03)"]
    Q4 -->|"No"| NA4["Document/NoSQL store<br/>(not chosen)"]
    PG --> Q5{"Defined hot-data / high-read<br/>requirement needing a cache?"}
    Q5 -->|"None defined"| NoCache["No application cache;<br/>recompute per request (ADR-04)"]
    Q5 -->|"Yes"| NA5["Redis / HTTP cache<br/>(not implemented)"]
    NoCache --> Done(["Observed architecture"])
```


## 5.4 Cross-Cutting Concerns

Cross-cutting concerns in this system are, by design, sparse. The application is a read-only historical-data showcase, so several enterprise concerns (observability, tracing, auth, DR tooling) are **not implemented**; those are documented here as observed absences with their evidence, rather than described aspirationally. The concerns that *are* present — a uniform error-to-HTTP-500 pattern and container-level restart — are detailed with citations.

### 5.4.1 Monitoring and Observability

There is **no monitoring or observability integration** anywhere in the repository. No application-performance-management, error-tracking, metrics, or analytics client (e.g., Sentry, Datadog, New Relic, Prometheus, OpenTelemetry) appears in `requirements.txt` or `frontend/package.json`, and there is no health-check or readiness endpoint among the six routes in `api/routes.py`. The frontend declares the `web-vitals` package but never calls `reportWebVitals`, so no client-side telemetry is emitted.

| Observability Capability | Status | Evidence |
|---|---|---|
| Metrics / APM | Not implemented | No client library in `requirements.txt` / `frontend/package.json` |
| Error tracking (e.g., Sentry) | Not implemented | Absent from dependencies; no init anywhere in `api/` or `frontend/src/` |
| Health-check / readiness endpoint | Not implemented | No such route in `api/routes.py`; `depends_on` gives start-order only |
| Client performance telemetry | Declared but unused | `web-vitals` in `package.json`; no `reportWebVitals` call in `frontend/src/` |

Runtime visibility is limited to whatever the Flask development server and the `postgres` container write to stderr, viewable via `docker logs`.

### 5.4.2 Logging and Tracing

The application performs **no explicit logging and no distributed tracing**. There is no `logging` configuration, no logger calls, and no correlation-ID or trace-context propagation in `api/`. The only log output is **incidental**: the Werkzeug development server prints a request line per HTTP call to stderr, and PostgreSQL writes its own container logs. Because the stack is a single in-process monolith calling a single database synchronously, there is no cross-service span to trace, but there is also no request identifier tying a browser action to its server-side handling.

| Logging / Tracing Capability | Status | Evidence |
|---|---|---|
| Structured application logging | Not implemented | No `logging` setup or log statements in `api/` |
| Request/access logging | Incidental only | Default Werkzeug dev-server stderr output |
| Distributed tracing / correlation IDs | Not implemented | No tracing library; single-process synchronous flow |
| Log aggregation / shipping | Not implemented | No log driver config beyond container defaults |

### 5.4.3 Error Handling Patterns

The error-handling pattern is uniform and minimal, and is documented in depth in Section 4.5. In summary: the backend has **no `try/except` and no `@app.errorhandler`**, so any exception raised inside a route becomes a Werkzeug **HTTP 500**; the frontend `getData` functions inspect only `response.status > 299` and render a single `<h1 className='error'>` heading, but do **not** wrap `fetch` in `try/catch`, so a transport-level failure becomes an unhandled promise rejection with no error UI. There is no retry, backoff, or fallback anywhere.

The diagram below gives a **cross-layer** view of error propagation — classifying each error by origin layer and tracing how far it surfaces — which complements the separate backend, frontend, and startup flows in Section 4.5.

```mermaid
flowchart TD
    subgraph Origin["Error origin by layer"]
        Client{{"Client input<br/>bad date / unknown feature"}}
        Data{{"Data condition<br/>empty / missing rows"}}
        Infra{{"Infrastructure<br/>DB unreachable / not ready"}}
    end
    Client --> Route["Route handler executes<br/>(no try/except)"]
    Data --> Route
    Infra --> Route
    Route --> Raise["Unhandled exception raised"]
    Raise --> WZ["Werkzeug returns HTTP 500"]
    WZ --> Gap["No logging, metrics,<br/>alerting, or tracing emitted"]
    WZ --> Net{"Response reaches browser?"}
    Net -->|"yes - 5xx status"| FE["getData: status > 299<br/>setError(statusText)"]
    Net -->|"no - fetch rejects"| Drop(["Unhandled promise rejection<br/>no error UI shown"])
    FE --> UI["Render h1.error heading"]
    UI --> Recover(["User resubmits:<br/>only app-level recovery"])
```

### 5.4.4 Authentication and Authorization Framework

There is **no authentication or authorization framework**. All six routes are public, unauthenticated `GET`s; `api/__init__.py` registers no auth middleware and applies `CORS(app)` permissively to every origin; no route in `api/routes.py` performs any access check. The only credentials in the project are the hard-coded PostgreSQL username/password (`postgres`/`postgres`) in the DSN and in `docker-compose.yml` — database credentials, not an end-user identity mechanism (see Section 3.4.2).

| AuthN/AuthZ Concern | Status | Evidence |
|---|---|---|
| End-user authentication | None | No identity provider, session, token, or API key in the codebase |
| Route authorization | None | No checks or decorators in `api/routes.py` |
| Cross-origin policy | Fully permissive | `CORS(app)` on all routes/origins (`api/__init__.py`) |
| Transport security (TLS) | Not in repo | No TLS termination; would require an external proxy (absent) |

### 5.4.5 Performance Requirements and SLAs

No formal performance requirements, SLAs, KPIs, latency budgets, or throughput targets are defined anywhere in the repository (consistent with Section 1.2.3). The performance-relevant characteristics that **can** be observed are architectural, not contractual:

- **Precomputed aggregates reduce read cost:** the analysis endpoint reads the materialized `YearlyAvg` table rather than scanning all of `Tracks` (`api/models.py`, `api/routes.py`).
- **No caching means full recompute per request:** every `/api/week` and `/api/analysis` call re-queries PostgreSQL and re-runs pandas (Section 4.4.3), so cost does not amortize under repeated load.
- **Single development-server process:** the container runs `python3 app.py` (`app.run`) rather than the pinned `gunicorn`, so there is no configured worker pool for concurrent request handling.
- **No pagination or result limits:** artist search returns all matching appearances and a week returns its full ranked list, so payload size scales with the data.
- **Browser-cacheable assets:** the CRA build emits content-hashed static files served by Flask, which browsers can cache across sessions.

Because no numeric targets exist in the code, this subsection states the **absence of defined SLAs** rather than inventing them.

### 5.4.6 Disaster Recovery Procedures

Disaster-recovery capability is limited to two low-level mechanisms and an external dependency; there are **no backups, replication, failover, or documented RPO/RTO** in the repository.

| DR Concern | Status | Evidence |
|---|---|---|
| Process recovery | Present (container-level) | `restart: on-failure` on the `api` service (`docker-compose.yml`) |
| Data durability | Volume-backed only | PostgreSQL data mapped via `./data:/data` (`docker-compose.yml`) |
| Backups / snapshots | Not implemented | No backup, dump, or snapshot scripts anywhere in the repo |
| Replication / failover | Not implemented | Single `postgres` service; no replica, standby, or clustering |
| Data re-population | External dependency | Empty/stale tables are refilled only by the out-of-repo weekly pipeline (Section 4.5.5) |

Two consequences follow from the evidence. First, `restart: on-failure` recovers only from a **process exit** — per-request HTTP 500s do not exit the process, so they are not "recovered" at the infrastructure layer. Second, `depends_on: postgres` orders container **start** but does not wait for the database to be **ready to accept connections**, so requests issued during that window return HTTP 500 until PostgreSQL is ready; there is no readiness gate or retry to smooth this. Recovery of the *data* itself depends entirely on the external ingestion pipeline re-populating `Tracks` and `YearlyAvg`, since the repository contains no migration, seed, or repair routines.


## 5.5 References

The following repository files, folders, and previously authored specification sections were examined as evidence for Section 5. No external web sources were relied upon for the architectural claims in this section.

**Backend source (`api/` package and launcher)**

- `app.py` — Flask launcher; `app.run(host='0.0.0.0')` (Werkzeug development server) confirming the runtime entry point.
- `api/__init__.py` — application bootstrap: `Flask(static_folder='../frontend/build', static_url_path='/')`, `CORS(app)`, hard-coded DSN `postgresql://postgres:postgres@postgres/db`, `SQLALCHEMY_TRACK_MODIFICATIONS=False`, `db`/`ma` initialization, side-effect route registration.
- `api/routes.py` — the six `GET` route handlers, JSON/redirect/static response composition, and the absence of `try/except`, input validation, and explicit 404/400 handling.
- `api/models.py` — `Tracks` and `YearlyAvg` ORM models and the `TrackSchema`/`YearlyAvgSchema` Marshmallow schemas (including the `loudness` omission on `YearlyAvg`).
- `api/funcs.py` — the stateless aggregation helpers `get_query_week`, `get_weekly_data`, and `get_rolling_avg` (`.rolling(5)`), and their unhandled-exception behavior on empty input.

**Frontend source (`frontend/`)**

- `frontend/package.json` — React 17 / `react-scripts` 4.0.3 dependencies, the `http://localhost:5000` dev proxy, the `start-api` (`flask run --no-debugger`) script, and the declared-but-unused `axios`/`plotly.js`/`react-plotly.js`/`web-vitals`.
- `frontend/src/App.js` — the SPA shell state (`nav`, `activeTab`), tab routing, `Section` wrappers, and footer.
- `frontend/src/index.js` — the React 17 `ReactDOM.render` bootstrap into `#root`.
- `frontend/src/components/tracks/TracksSection.js` — the `/api/week` fetch state machine and radar/list rendering.
- `frontend/src/components/tracks/DatePicker.js` — the bounded HTML5 date input (`1958-07-27 … 2021-11-13`).
- `frontend/src/components/tracks/RadarChart.js` — the amCharts RadarChart created during render with `chart.dispose()` commented out.
- `frontend/src/components/trends/TrendsSection.js` — the `/api/analysis` fetch and line-chart/glossary rendering.
- `frontend/src/components/trends/FeatureSelect.js` — the seven-feature selection dropdown.
- `frontend/src/components/trends/LineChart.js` — the amCharts XYChart with the "3 Year Rolling Average" legend label.
- `frontend/src/components/trends/features.json` — the audio-feature glossary and Spotify documentation link.
- `frontend/src/components/about/AboutSection.js` — the static About view and outbound documentation hyperlinks.
- `frontend/src/components/navigation/` — `Sidebar.js`, `Tab.js`, `SmallTab.js`, `Section.js`, `Hamburger.js` (styled-components navigation shell and responsive behavior).
- `frontend/src/styles/index.css` — global styles including the `.error` and `.loading` headings referenced by the error-handling flow.
- `frontend/build/` — the compiled CRA production output served by Flask static serving.

**Infrastructure, configuration, and documentation**

- `Dockerfile` — `python:3.11-slim-buster` image; `libpq-dev`/`gcc`; `EXPOSE 5000`; `CMD ["python3","app.py"]` (dev server, not `gunicorn`).
- `docker-compose.yml` — the `api` and `postgres` services, port mappings (`80:5000`, `5432`), hard-coded credentials, `./data:/data` volume, `depends_on`, and `restart: on-failure`.
- `requirements.txt` — pinned Python dependencies (Flask 2.0.1, Flask-SQLAlchemy, Flask-Marshmallow, Flask-Cors, pandas 2.0.0, `psycopg2`, and the declared-but-unwired `gunicorn` 20.1.0).
- `README.md` — the description of the out-of-repository weekly Billboard scraper and Spotipy audio-feature enrichment pipeline and the endpoint overview.

**Cross-referenced specification sections**

- Section 1.2 System Overview — deployment topology, major-components framing, and the absence of formally defined SLAs/KPIs (1.2.3).
- Section 3.4 Third-Party Services — confirmation of no runtime outbound calls, no auth service, no monitoring, and no cloud integrations.
- Section 4.4 State Management and Transaction Boundaries — stateless read-only backend, per-request ORM session, and the no-application-caching finding (4.4.3).
- Section 4.5 Error Handling and Recovery Flows — the HTTP-500 error pattern, frontend status handling, and startup/DB-readiness recovery behavior (4.5.5).


# 6. SYSTEM COMPONENTS DESIGN

## 6.1 Core Services Architecture

### 6.1.1 Architectural Approach and Applicability Assessment

**Core Services Architecture is not applicable for this system** in its conventional sense — that is, a set of independently deployable microservices that discover one another over the network, communicate through service-to-service calls or a message broker, and are individually load-balanced, circuit-broken, and auto-scaled. The repository implements no such topology.

The system is a **monolithic, two-tier, single-origin web application**, consistent with Section 5.1.1 and ADR-01 in Section 5.3.6. A single Flask process (the `api` service) serves both the read-only JSON HTTP API *and* the compiled React 17 single-page application (SPA), because `api/__init__.py` constructs the app with `static_folder='../frontend/build'` and `static_url_path='/'`. That one process is backed by a single **PostgreSQL 15** database (the `postgres` service), and the two are wired together by a two-service `docker-compose.yml`. There is no second backend service, no API gateway, no service mesh, no message broker, and no inter-service remote procedure call anywhere in the tree — every backend capability is reachable in-process. The two entries under `services:` in `docker-compose.yml` (`api` and `postgres`) constitute a conventional application-plus-database pair, not a service-oriented decomposition.

Because the concerns prescribed for this section (service discovery, inter-service communication, load balancing, circuit breakers, auto-scaling, failover) presuppose a multi-service topology that this system does not have, the remainder of Section 6.1 does not fabricate one. Instead it documents, with direct code evidence: (a) the small set of coarse-grained runtime units that *do* exist and their boundaries; (b) how each prescribed concern maps onto the observed monolith; and (c) which mechanisms are deliberately absent. This mirrors the evidence-based "document observed absences rather than aspirations" approach used in Section 5.4.

The table below summarizes why each core-services concern is not applicable or not implemented; the referenced sub-sections expand each with evidence.

| Core-Services Concern | Applicability to This System | Basis in the Repository |
|---|---|---|
| Independently deployable microservices | Not applicable | One Flask package (`api/`) in one image; only `api` + `postgres` in `docker-compose.yml` |
| Service mesh / message broker / internal RPC | Not present | No Istio/Envoy, no Celery/RabbitMQ/Kafka/Redis, no gRPC in `requirements.txt` |
| Service discovery | Minimal — container DNS only | Docker Compose service-name DNS resolves host `postgres` in the DSN (`api/__init__.py`); no registry |
| Load balancing across service instances | Not present | Single `api` instance; host `80→5000`; no reverse proxy / ingress / `deploy.replicas` |
| Circuit breakers / bulkheads | Not present | No `tenacity`/`circuitbreaker`/`hystrix`; no such logic in `api/routes.py` |
| Retry / fallback | Not present (server); UI-only (client) | No server retry; client renders an error string with no retry (`TracksSection.js`, `TrendsSection.js`) |

The units that do exist, and the (largely absent) discovery, balancing, and fault-isolation mechanisms around them, are detailed in Section 6.1.2.

### 6.1.2 Service Components

Although the system is not service-oriented, it is composed of a small number of **coarse-grained runtime units** with clear boundaries. This sub-section documents those units and their responsibilities, the communication patterns between them, and the discovery, load-balancing, and fault-isolation mechanisms around them (most of which are absent by design).

#### 6.1.2.1 Service Boundaries and Responsibilities

The deployed footprint comprises two containerized runtime units (the `api` and `postgres` services in `docker-compose.yml`) plus one browser-resident client and one out-of-repository batch producer. Their boundaries are summarized below.

| Runtime Unit | Primary Responsibility | Evidence |
|---|---|---|
| `api` service (Flask monolith) | Serve six HTTP routes, run pandas aggregations, query the DB, and serve the compiled SPA at `/` | `api/__init__.py`, `api/routes.py`, `api/funcs.py`, `api/models.py` |
| `postgres` service | Persist the `Tracks` and `YearlyAvg` tables (single PostgreSQL 15 instance) | `docker-compose.yml`, `api/models.py` |
| React SPA client (browser) | Render the Tracks/Trends/About UI, issue `fetch` calls, and draw amCharts visualizations | `frontend/src/` |
| External weekly ingestion pipeline (out of repo) | Scrape Billboard and enrich with Spotify audio features, writing rows into PostgreSQL | `README.md` (not present in the tree) |

The most consequential boundary decision is that the API and the SPA are **not** separate services: one Flask process owns both, so they share a build, an image, and a deployment lifecycle (Section 5.3.1). The read path (this repository) and the write path (the external pipeline) are decoupled only through the shared database, with no API contract between them. The runtime components and their data paths are shown in Figure 6.1.2-1.

```mermaid
flowchart TD
    subgraph ClientTier["Presentation Tier - Web Browser"]
        SPA["React 17 SPA<br/>Tracks / Trends / About"]
    end

    subgraph ApiService["api service - single Flask process (host 80 to container 5000)"]
        Routes["HTTP Route Layer<br/>api/routes.py (6 GET routes)"]
        StaticDelivery["Static SPA Delivery<br/>static_folder = frontend/build"]
        Helpers["Aggregation Helpers<br/>api/funcs.py (pandas)"]
        ORM["ORM Models + Marshmallow Schemas<br/>api/models.py"]
    end

    subgraph DataTier["postgres service"]
        PG[("PostgreSQL 15 'db'<br/>Tracks, YearlyAvg")]
    end

    subgraph ExternalPath["External Write Path - not in this repository"]
        Pipeline["Weekly Billboard scraper<br/>+ Spotipy enrichment"]
    end

    SPA -->|"HTTP/JSON fetch to /api/*"| Routes
    StaticDelivery -->|"index.html + hashed JS/CSS"| SPA
    Routes --> Helpers
    Routes --> ORM
    ORM -->|"SQLAlchemy over psycopg2"| PG
    Pipeline -->|"weekly batch writes"| PG
```

**Figure 6.1.2-1: Service Interaction Diagram — Runtime Components and Data Paths.** Solid arrows are runtime request/response and query flows; the dashed boundary "External Write Path" denotes the out-of-repository weekly producer that integrates only through the database.

#### 6.1.2.2 Inter-Service Communication Patterns

All communication is **synchronous request/response**, consistent with ADR-02 (Section 5.3.2). There are only two runtime communication paths inside the deployed system, plus one out-of-band batch path. No asynchronous messaging, event bus, WebSocket/server-sent-events, or internal RPC exists in the repository.

| Communication Path | Protocol and Format | Interaction Pattern |
|---|---|---|
| Browser SPA ↔ `api` service | HTTP/1.1 carrying JSON, HTML, or 302 redirects; browser-native `fetch` | Client-initiated, one request per view mount / user action; same-origin in production, dev-proxied to `:5000` |
| `api` service ↔ `postgres` | PostgreSQL wire protocol via SQLAlchemy + `psycopg2` | Synchronous per-request ORM query (`.query(...).all()` / `.with_entities(...)`); session torn down at request end |
| External pipeline ↔ database | Direct SQL writes (no API) | Shared-database integration; asynchronous weekly batch writes, out of repository |

Because route handlers wrap no `try/except`, the *error* contract of the client↔API path is implicit: any failure is surfaced as an HTTP 500 that the client reads only as a status code (Section 5.4.3).

#### 6.1.2.3 Service Discovery, Load Balancing, and Fault-Tolerance Patterns

The four remaining service-component concerns — service discovery, load balancing, circuit breakers, and retry/fallback — are addressed together here because each is either minimal or absent.

- **Service discovery.** The only discovery mechanism is **Docker Compose's built-in DNS**. The Flask DSN targets the logical host `postgres` (`postgresql://postgres:postgres@postgres/db` in `api/__init__.py`), which Compose resolves to the database container on the default network; `depends_on: postgres` only orders startup. There is no service registry (Consul/Eureka/etcd) and no health-based discovery. The browser reaches the `api` service through a fixed host-port mapping (`80→5000`), and during development through the CRA proxy to `http://localhost:5000` (`frontend/package.json`).
- **Load balancing strategy.** **None.** A single `api` container handles all traffic; the repository contains no reverse proxy, ingress controller, or load balancer, and `docker-compose.yml` declares no `deploy.replicas`. Traffic distribution is therefore 1:1 to the sole instance.
- **Circuit breaker patterns.** **None.** There is no circuit-breaker or bulkhead library and no timeout/failure-threshold logic; a slow or unavailable database blocks the synchronous request until it errors.
- **Retry and fallback mechanisms.** **None server-side** (no retry, backoff, or fallback in `api/`). Client-side, each `getData()` performs a **single** `fetch`; on `status > 299` it stores `response.statusText`, and on an empty result it shows `'No Data Found'` — with no retry, exponential backoff, or alternate data source (`TracksSection.js`, `TrendsSection.js`; Section 5.4.3).

| Concern | Status | Evidence |
|---|---|---|
| Service discovery | Container DNS only | Host `postgres` in DSN (`api/__init__.py`); `depends_on` ordering (`docker-compose.yml`) |
| Load balancing | Not present | Single instance; `80→5000`; no proxy/ingress/`replicas` (`docker-compose.yml`) |
| Circuit breakers | Not present | No breaker library; no timeout logic in `api/routes.py` |
| Retry / fallback | Server: none; client: single-shot | No server retry; single `fetch` + error text (`TracksSection.js`, `TrendsSection.js`) |

### 6.1.3 Scalability Design

The repository defines **no elastic scaling design**: there is no orchestrator, no autoscaler, no replica configuration, and no declared resource envelope. This sub-section documents the scaling *approach that the observed topology permits*, the auto-scaling/resource/capacity facilities (none defined), and the concrete performance optimizations that are present in the code.

#### 6.1.3.1 Horizontal and Vertical Scaling Approach

**Vertical scaling** is the only in-place lever available today: the single `api` container and the single `postgres` container each grow by allocating more host CPU and memory. Because `docker-compose.yml` declares no `deploy.resources` limits or reservations, the containers consume host defaults, so vertical headroom is bounded only by the host.

**Horizontal scaling is not implemented or configured.** The compose file declares no replicas and there is no load balancer to distribute traffic across replicas. The request handling *is* stateless and read-only (no session state, no server-side cache — Section 5.1.1), which in principle would permit multiple `api` replicas; however, three concrete factors in the repository prevent horizontal scale-out as-is:

1. The container's default command is the **single Flask development server** (`CMD ["python3","app.py"]` → `app.run`), not the pinned `gunicorn` worker pool, so there is no configured multi-worker concurrency (ADR-07, Section 3.6.3).
2. There is **no load balancer or reverse proxy** to front multiple instances; all traffic funnels through one `host:80 → container:5000` mapping.
3. The **API and SPA share one image and build lifecycle** (ADR-01), so they cannot be scaled independently, and the database is a **single instance with no read replicas**.

Figure 6.1.3-1 contrasts the observed single-instance topology (and its vertical lever) with the horizontal scale-out prerequisites that are absent from the repository.

```mermaid
flowchart TD
    Client["Web Browser"]

    subgraph Host["Single Host / Docker Engine - observed deployment"]
        Vert["Vertical lever: host CPU / RAM<br/>no resource limits declared"]
        subgraph Compose["Docker Compose Stack - one replica each"]
            Api["api container<br/>Flask dev server (python3 app.py)<br/>single process, host 80 to 5000"]
            PG[("postgres:15<br/>single instance, one volume")]
        end
    end

    subgraph Absent["Horizontal Scale-Out Prerequisites - NOT present in repository"]
        LB["Load balancer / reverse proxy"]
        Workers["gunicorn worker pool<br/>pinned but not wired"]
        Replicas["Additional api replicas"]
        DBRep["PostgreSQL read replicas / standby"]
    end

    Client -->|"host port 80"| Api
    Api -->|"psycopg2 (synchronous)"| PG
    Vert -.->|"in-place growth only"| Api
    LB -.-> Replicas
    Workers -.-> Replicas
    Replicas -.-> PG
    DBRep -.-> PG
```

**Figure 6.1.3-1: Scalability Architecture — Observed Topology and Absent Scale-Out Prerequisites.** Solid arrows show the current single-instance runtime; dashed elements in the "Absent" group are components that horizontal scaling would require but that the repository does not contain.

#### 6.1.3.2 Auto-Scaling, Resource Allocation, and Capacity Planning

These three facilities are **not defined** in the repository; each is documented below as an observed absence with its evidence.

- **Auto-scaling triggers and rules.** None. There is no orchestrator (no Kubernetes HPA, no Swarm/ECS autoscaler) and no metrics source to trigger on (no monitoring/APM — Section 5.4.1); `docker-compose.yml` has no autoscale directives.
- **Resource allocation strategy.** None declared. There are no `deploy.resources` CPU/memory limits or reservations, no worker-count tuning (the dev server is single-process), and no explicit SQLAlchemy connection-pool sizing (defaults apply). Containers therefore use host defaults.
- **Capacity planning guidelines.** None. No SLAs, throughput targets, latency budgets, load tests, or benchmarks exist anywhere in the repository (Sections 5.4.5 and 1.2.3). The observable capacity ceiling is set by the single dev-server process and the single database, and by the fact that queries are **unpaginated** (a week returns its full ranked list and artist search returns all matches), so payload size and query cost grow with the data volume.

| Capability | Status | Evidence |
|---|---|---|
| Auto-scaling triggers/rules | Not present | No orchestrator/autoscaler; no metrics (`docker-compose.yml`; Section 5.4.1) |
| Resource allocation | None declared | No `deploy.resources`; single-process server; default DB pool (`docker-compose.yml`) |
| Capacity planning | None defined | No SLAs/targets/load tests; unpaginated queries (`api/routes.py`; Section 5.4.5) |

#### 6.1.3.3 Performance Optimization Techniques

Despite the absence of a scaling design, the code contains a few deliberate, observable performance choices, alongside notable omissions.

Techniques present:

- **Precomputed aggregate table.** The trend endpoint reads the materialized `YearlyAvg` table rather than scanning all of `Tracks`, trading pipeline/storage cost for cheap reads (`api/models.py`, `api/routes.py`; Section 5.4.5).
- **Vectorized in-process aggregation.** Weekly means and the rolling average are computed with pandas over the query result set (`api/funcs.py`), rather than row-by-row.
- **Browser-cacheable static assets.** The CRA build emits content-hashed files served by Flask static serving, which browsers can cache across sessions (Section 5.1.3).
- **Parameterized queries.** All data access flows through the SQLAlchemy ORM, so values are parameterized rather than concatenated (Section 5.3.5).

Omissions that bound performance under load:

- **No application cache.** There is no Redis/Memcached/Flask-Caching/HTTP `Cache-Control`, so every `/api/week` and `/api/analysis` call re-queries PostgreSQL and re-runs pandas (ADR-04; Section 5.4.5).
- **No pagination or result limits** on week/artist reads (`api/routes.py`).
- **No secondary indexes.** `Tracks` and `YearlyAvg` define only primary keys (`api/models.py`), so filters on `week`, `artist`, and `spotify_id` are unindexed within this repository's model definitions.

| Technique | Status | Evidence |
|---|---|---|
| Precomputed `YearlyAvg` aggregate | Present | `api/models.py`, `api/routes.py` |
| Vectorized pandas aggregation | Present | `api/funcs.py` (`get_weekly_data`, `get_rolling_avg`) |
| Browser-cacheable hashed assets | Present (incidental) | CRA build served by Flask static (Section 5.1.3) |
| Application cache / pagination / secondary indexes | Not present | No cache libs; no `limit`; PK-only models (`api/models.py`; Section 5.4.5) |

### 6.1.4 Resilience Patterns

Resilience in this system is limited to a single container-level restart policy and minimal UI-level error handling; there are **no backups, replication, failover, or documented RPO/RTO**, consistent with Section 5.4.6. This sub-section documents the fault-tolerance and failover posture, the data-redundancy and disaster-recovery situation, and the service-degradation behavior — each with evidence.

#### 6.1.4.1 Fault Tolerance and Failover Configuration

The observed fault-tolerance mechanisms are coarse and few:

- **Container restart.** The `api` service is configured with `restart: on-failure` (`docker-compose.yml`), so Docker restarts the container on a non-zero process exit. This recovers only from **process crashes**, not from per-request HTTP 500s, which do not exit the process (Section 5.4.6).
- **Startup ordering vs. readiness.** `depends_on: postgres` orders container start but does **not** wait for the database to accept connections, so requests issued during the warm-up window return HTTP 500 with no readiness gate or retry.
- **Error handling.** With no `try/except` and no `@app.errorhandler`, any exception raised in a route becomes a Werkzeug HTTP 500 (Section 5.4.3, Section 4.5); there are no timeouts or bulkheads to contain a slow dependency.
- **Failover configuration.** **None.** There is exactly one instance of each service; the repository defines no standby, replica, or clustering for either `api` or `postgres`, and the `postgres` service has no restart policy at all.

Figure 6.1.4-1 maps the observed failure modes to their (limited) responses.

```mermaid
flowchart TD
    subgraph Failures["Observed Failure Modes"]
        Crash{{"api process<br/>crashes / exits"}}
        Boot{{"request during<br/>DB warm-up"}}
        BadReq{{"bad input or<br/>empty result set"}}
        DBLoss{{"postgres container<br/>lost / data gone"}}
    end

    Crash -->|"restart: on-failure"| Restart["Docker restarts api container"]
    Restart --> Up["Service resumes<br/>(no state to recover - read only)"]

    Boot -->|"depends_on = start order only"| Err500["Werkzeug returns HTTP 500"]
    BadReq -->|"no try/except"| Err500
    Err500 --> ClientMsg["Client: setError(statusText)<br/>or 'No Data Found' - no retry"]

    DBLoss -->|"no backup / replica / failover"| Manual["Manual recovery: re-run external<br/>weekly ingestion pipeline"]
```

**Figure 6.1.4-1: Resilience Pattern Implementation — Failure Modes and Observed Responses.** Only the `api` process-crash path has an automated infrastructure response (`restart: on-failure`); the remaining paths surface as HTTP 500s handled only at the UI, or require manual data re-population.

#### 6.1.4.2 Data Redundancy and Disaster Recovery

**Data redundancy approach.** The system runs a **single PostgreSQL 15 instance** with no replication, standby, or clustering. The only persistence-related configuration is the `./data:/data` bind mount on the `postgres` service (`docker-compose.yml`), which Section 5.4.6 records as the durability mechanism. One precise, evidence-based caveat applies: the `postgres:15` image stores its data in `/var/lib/postgresql/data` by default, and no `PGDATA` override is set, so the `./data:/data` mount does **not** map the database's actual data directory — durability across container re-creation is therefore not guaranteed by this mapping. Separately, the top-level named volume `data` is declared but referenced by no service.

**Disaster recovery procedures.** There are **no backups, dumps, or snapshots**, no replication or failover, and no defined RPO/RTO anywhere in the repository (Section 5.4.6). The application also contains no schema-creation, migration, seed, or repair routines (Section 5.3.3). Consequently, recovery of the *data* depends entirely on re-running the **external weekly ingestion pipeline** (out of repository) to re-populate `Tracks` and `YearlyAvg` (Section 4.5.5).

| Aspect | Status | Evidence |
|---|---|---|
| Data redundancy / replication | Single instance, none | One `postgres` service; no replica/standby (`docker-compose.yml`) |
| Volume durability | Mount present, PGDATA mismatch | `./data:/data`; default PGDATA `/var/lib/postgresql/data`, no override (`docker-compose.yml`) |
| Backups / snapshots / RPO-RTO | Not defined | No backup scripts; no RPO/RTO (Section 5.4.6) |
| Data recovery path | External dependency | Re-run out-of-repo weekly pipeline (`README.md`; Section 4.5.5) |

#### 6.1.4.3 Service Degradation Policies

There is no server-side graceful-degradation policy: the backend has no rate limiting, feature flags, bulkheads, or fallback responses, and no health/readiness endpoint to drive load-shedding (Sections 5.4.1 and 5.4.3); failures simply surface as HTTP 500. Degradation handling exists **only at the client UI layer**, and only partially.

- **Loading state.** While a request is in flight, the view renders a ". . ." indicator (`isLoaded` false).
- **Error state.** On an HTTP status `> 299`, the view renders `response.statusText` in an `<h1 className='error'>` heading; on an empty result it renders `'No Data Found'` (`TracksSection.js`, `TrendsSection.js`).
- **Gap.** A transport-level `fetch` rejection is not wrapped in `try/catch`, so it becomes an unhandled promise rejection with no error UI (Section 5.4.3). There is no progressive or partial degradation (e.g., stale cache, reduced feature set).

| Layer | Degradation Behavior | Evidence |
|---|---|---|
| `api` service (server) | None — failures become HTTP 500; no rate-limit/feature-flag/fallback | `api/routes.py` (no `try/except`); Sections 5.4.1, 5.4.3 |
| React SPA (client) | Loading indicator; error heading; `'No Data Found'`; single-shot | `TracksSection.js`, `TrendsSection.js` |
| Transport failure | No UI — unhandled promise rejection | No `try/catch` around `fetch` (Section 5.4.3) |

### 6.1.5 References

**Repository files examined for this section:**

- `app.py` - Confirmed the single entry point (`app.run(host='0.0.0.0')`), establishing the monolithic launch model.
- `api/__init__.py` - Established the single Flask process serving both API and SPA (`static_folder='../frontend/build'`), the hard-coded PostgreSQL DSN using Docker host `postgres`, and CORS configuration.
- `api/routes.py` - Confirmed the six synchronous GET routes and the absence of `try/except`, error handlers, retry, and circuit-breaker logic.
- `api/models.py` - Established the two ORM models (`Tracks`, `YearlyAvg`) with primary-key-only definitions (no secondary indexes/relationships).
- `api/funcs.py` - Established the in-process pandas aggregation helpers (`get_weekly_data`, `get_rolling_avg`) used as performance optimizations.
- `requirements.txt` - Confirmed the Flask/SQLAlchemy/psycopg2/pandas stack and the presence of `gunicorn` (not wired) plus the absence of any broker, discovery, or resilience libraries.
- `.flaskenv` - Confirmed the `development` run configuration.
- `Dockerfile` - Established the container build and the `CMD ["python3","app.py"]` (Flask dev server, not gunicorn).
- `docker-compose.yml` - Established the two-service topology, `restart: on-failure`, `depends_on` (start-order only), port mapping `80:5000`, the `./data:/data` volume, and the absence of replicas/healthchecks/resource limits.
- `.dockerignore` / `.gitignore` - Established build/runtime boundaries (excluded `node_modules`/`venv`/`data`; `frontend/build` intentionally retained).
- `README.md` - Established the external weekly ingestion pipeline (Billboard scrape + Spotipy) that is not present in the repository.
- `frontend/package.json` - Confirmed the React SPA client, the `"proxy": "http://localhost:5000"` dev setting, and the amCharts/axios dependencies.
- `frontend/src/App.js` - Confirmed the client-side, single-store SPA composition (no client-side service topology).
- `frontend/src/components/tracks/TracksSection.js` - Established the single-shot `fetch` pattern and UI-level loading/error/'No Data Found' degradation.
- `frontend/src/components/trends/TrendsSection.js` - Corroborated the same client fetch and degradation pattern for the trend view.

**Repository folders examined:**

- `api/` - The complete Flask backend package (four files); confirmed the monolith has no additional internal services.
- `frontend/` - The React client workspace; confirmed the SPA is served as static assets by the `api` service.

**Cross-referenced Technical Specification sections:**

- `5.1 High-Level Architecture` - Two-tier single-origin topology, component inventory, and data flows; corroborates the "no service mesh/broker/RPC" finding.
- `5.3 Technical Decisions` - ADR-01 (monolith), ADR-02 (synchronous REST/ORM), ADR-06 (externalized ingestion), ADR-07 (dev server vs. gunicorn).
- `5.4 Cross-Cutting Concerns` - Monitoring, error handling (5.4.3), performance/SLA absence (5.4.5), and disaster recovery (5.4.6).
- `3.6 Development & Deployment` - Containerization detail and the dev-server runtime caveat.
- `4.5 Error Handling and Recovery Flows` - Error propagation and recovery behavior referenced in the resilience discussion.
- `1.2 System Overview` - System scope confirming the absence of formal SLAs/KPIs.

**Web searches:** None conducted for this section; all findings are grounded in direct repository inspection.

## 6.2 Database Design

### 6.2.1 Schema Design

Database Design **is applicable** to this system. The application persists all of its data in a single relational database — **PostgreSQL 15**, provisioned as the `postgres` service in `docker-compose.yml` — which is its only persistent datastore (there is no secondary database, document store, key-value store, or object store, per Section 3.5). The relational schema is declared declaratively as two Flask-SQLAlchemy ORM models in `api/models.py`, and the backend reaches the database through the SQLAlchemy ORM over the `psycopg2` driver using the DSN `postgresql://postgres:postgres@postgres/db` in `api/__init__.py`.

One architectural fact governs every statement in this section: **the repository contains no schema-creation, migration, or seed code** — there is no `db.create_all()` call, no Alembic/Flask-Migrate configuration, and no `.sql` or seed file anywhere in the tree (verified across all Python and YAML sources). All Data Definition Language (DDL) and every write are owned by the **external weekly ingestion pipeline** described in `README.md` (a "separate script, running weekly, which scrapes the Billboard site page and adds each song into the database"), which is not present in this repository. The ORM models therefore describe the schema the application **expects and reads**, while the physical tables, column types, and any indexes actually present in the running database are created upstream by that pipeline. Design details below are drawn from the ORM model definitions and are flagged wherever the physical database could diverge from them.

#### 6.2.1.1 Entity Overview and Relationships

The schema comprises exactly two entities, both defined in `api/models.py`:

| Entity (ORM class) | Grain | Row Population |
|---|---|---|
| `Tracks` | One row per song per chart week | External pipeline (weekly batch INSERTs) |
| `YearlyAvg` | One row per calendar year (pre-computed audio-feature averages) | External pipeline (recomputed rollup) |

The two entities are **physically independent**: `api/models.py` declares no `db.ForeignKey`, no `db.relationship`, and no association table, so there is no referential-integrity link between them at the ORM layer. Their relationship is **logical and derived rather than enforced** — `YearlyAvg` holds per-year means of the same audio-feature dimensions stored per song in `Tracks`, so each `YearlyAvg` row is conceptually an aggregate of the many `Tracks` rows whose `week` falls in that `year`. That aggregation is performed **upstream by the external pipeline**, not by a database view, trigger, foreign key, or application write. This is a deliberately **denormalized, analytics-oriented pattern**: a fact-like detail table (`Tracks`) plus a companion pre-aggregated summary table (`YearlyAvg`) that exists to make the trend endpoint cheap to serve (see Section 6.2.4 and Section 6.1.3.3).

The entity-relationship diagram below shows both tables with their complete attribute lists and the single logical (non-enforced) relationship between them.

```mermaid
erDiagram
    TRACKS {
        integer id PK
        date week
        integer rank
        string track
        string artist
        string spotify_id
        float tempo
        float energy
        float danceability
        float valence
        float liveness
        float speechiness
        float acousticness
        float instrumentalness
        float loudness
    }
    YEARLY_AVG {
        integer index PK
        string year
        float energy
        float danceability
        float valence
        float liveness
        float speechiness
        float acousticness
        float instrumentalness
        float tempo
    }
    TRACKS }o..|| YEARLY_AVG : "aggregated by year into (logical, no FK)"
```

**Figure 6.2.1-1: Entity-Relationship Diagram.** Both entities are attributed from `api/models.py`. The dashed, non-identifying relationship denotes the logical yearly rollup performed by the external pipeline; **no physical foreign key exists**. Note that `loudness` is present on `TRACKS` but absent from `YEARLY_AVG`.

#### 6.2.1.2 Data Models and Structures

Each model maps to a PostgreSQL table via the Flask-SQLAlchemy default naming convention (CamelCase → snake_case), so `Tracks` maps to the table `tracks` and `YearlyAvg` maps to `yearly_avg` (no `__tablename__` is overridden; the `yearly_avg` name is corroborated by the SQL shown in the Section 5.2.6 sequence diagram). Columns are declared with no length, precision, `nullable`, `default`, or `server_default` arguments, so the "Mapped SQL Type" column below reflects the SQLAlchemy **default** DDL mapping (what a hypothetical `create_all` would emit); the authoritative physical types are those the external pipeline actually created.

**`tracks` table (`Tracks` model)** — 15 columns:

| Column | ORM Type | Mapped SQL Type | Role / Notes |
|---|---|---|---|
| `id` | `db.Integer` (PK) | `INTEGER` | Surrogate primary key |
| `week` | `db.Date` | `DATE` | Saturday-aligned chart week; equality filter for `/api/week` |
| `rank` | `db.Integer` | `INTEGER` | Chart position; `ORDER BY` key |
| `track` | `db.String` | `VARCHAR` (no length) | Song title |
| `artist` | `db.String` | `VARCHAR` (no length) | Performing artist; `LIKE` search target for `/api/artist` |
| `spotify_id` | `db.String` | `VARCHAR` (no length) | Spotify track id; equality filter for `/api/track`; **not assigned in `__init__`** |
| `tempo` | `db.Float` | `DOUBLE PRECISION` | Audio feature (BPM) |
| `energy` | `db.Float` | `DOUBLE PRECISION` | Audio feature |
| `danceability` | `db.Float` | `DOUBLE PRECISION` | Audio feature |
| `valence` | `db.Float` | `DOUBLE PRECISION` | Audio feature |
| `liveness` | `db.Float` | `DOUBLE PRECISION` | Audio feature |
| `speechiness` | `db.Float` | `DOUBLE PRECISION` | Audio feature |
| `acousticness` | `db.Float` | `DOUBLE PRECISION` | Audio feature |
| `instrumentalness` | `db.Float` | `DOUBLE PRECISION` | Audio feature |
| `loudness` | `db.Float` | `DOUBLE PRECISION` | Audio feature (absent from `yearly_avg`) |

**`yearly_avg` table (`YearlyAvg` model)** — 10 columns:

| Column | ORM Type | Mapped SQL Type | Role / Notes |
|---|---|---|---|
| `index` | `db.Integer` (PK) | `INTEGER` | Surrogate primary key; column literally named `index` |
| `year` | `db.String` | `VARCHAR` (no length) | Calendar year stored **as text**; projected by `/api/analysis` |
| `energy` | `db.Float` | `DOUBLE PRECISION` | Per-year mean |
| `danceability` | `db.Float` | `DOUBLE PRECISION` | Per-year mean |
| `valence` | `db.Float` | `DOUBLE PRECISION` | Per-year mean |
| `liveness` | `db.Float` | `DOUBLE PRECISION` | Per-year mean |
| `speechiness` | `db.Float` | `DOUBLE PRECISION` | Per-year mean |
| `acousticness` | `db.Float` | `DOUBLE PRECISION` | Per-year mean |
| `instrumentalness` | `db.Float` | `DOUBLE PRECISION` | Per-year mean |
| `tempo` | `db.Float` | `DOUBLE PRECISION` | Per-year mean |

Two structural observations follow directly from the model definitions:

- **Nullability.** Because no column other than the two primary keys carries a `nullable=False` argument, every non-key column is **nullable** under the SQLAlchemy default. There are no `CHECK` constraints, `UNIQUE` constraints, defaults, or enumerations declared anywhere.
- **`index` column signature.** `YearlyAvg` uses a primary-key column literally named `index` and stores `year` as a string. This shape is characteristic of a **pandas `DataFrame.to_sql()` export** (pandas 2.0.0 is a pinned dependency and is used in `api/funcs.py`), consistent with the external pipeline building `yearly_avg` from a pandas aggregation and writing it directly to PostgreSQL.

The database's row shapes are exposed to clients through two Marshmallow schemas in `api/models.py`, which define the serialization surface (they are the JSON projection, not additional persistence structures):

| Schema | Fields Exposed | Divergence from Table |
|---|---|---|
| `TrackSchema` | 15 fields incl. `id`, `week`, `rank`, `track`, `artist`, `spotify_id` + 9 audio features | Matches the `tracks` columns |
| `YearlyAvgSchema` | `year` + 8 audio features | **Omits** the `index` primary key; **omits** `loudness` |

#### 6.2.1.3 Indexing Strategy and Constraints

There is **no explicit indexing strategy declared in the repository**. The complete set of constraints and indexes defined in the ORM models is limited to one primary key per table, enumerated exhaustively below:

| Table | Constraint / Index | Column | Kind |
|---|---|---|---|
| `tracks` | Primary key | `id` | Declared via `primary_key=True` |
| `yearly_avg` | Primary key | `index` | Declared via `primary_key=True` |

No secondary indexes (`index=True` / `db.Index(...)`), unique constraints (`unique=True` / `UniqueConstraint`), foreign keys, or check constraints appear in `api/models.py` (verified by direct grep). Under standard PostgreSQL semantics a primary key is automatically backed by a **unique B-tree index**, so — if the external pipeline created the primary keys as declared — each table would carry exactly one such index on its key column. Because DDL is owned by that pipeline rather than by `db.create_all()`, the **physical indexes actually present cannot be confirmed from this repository**; any additional indexes the pipeline may have added are outside the codebase.

The practical consequence for the read workload (Section 6.2.4) is that the model definitions provide **no index support for the columns the API actually filters and sorts on** — `week`, `artist`, `spotify_id`, and `rank` on `tracks`. Within the repository's schema definition, those queries would rely on sequential scans unless the upstream pipeline added matching indexes. This is consistent with the "PK-only models / no secondary indexes" finding recorded in Section 6.1.3.3 and Section 5.2.3.

#### 6.2.1.4 Partitioning Approach

**No partitioning is configured.** `api/models.py` declares no `__table_args__`, no PostgreSQL declarative partitioning (`PARTITION BY RANGE/LIST/HASH`), and no partition-management tooling (e.g., `pg_partman`) appears anywhere in `requirements.txt` or the Compose stack. Both `tracks` and `yearly_avg` are modeled as single, monolithic tables.

The data has natural partition-key candidates — `tracks.week` (time-series chart data spanning 1958 onward) and `yearly_avg.year` — that would lend themselves to range partitioning at scale, but the repository does not exercise them. Given the read-only, single-instance deployment (Section 6.1.3) and the modest data domain, partitioning is neither present nor required by the current design.

#### 6.2.1.5 Replication Configuration

**No database replication is configured.** The `postgres` service in `docker-compose.yml` runs a **single PostgreSQL 15 instance** using the stock `postgres:15` image with default configuration. There is no standby/replica service, no streaming-replication or WAL-shipping configuration (`wal_level`, `hot_standby`, `primary_conninfo`), and no read replicas — verified by grep across the repository and corroborated by Section 5.2.3 ("a single database instance with no read replicas") and Section 6.1.4.2 ("single PostgreSQL 15 instance with no replication, standby, or clustering"). All reads and all upstream writes therefore target one primary instance.

Figure 6.2.1-2 depicts the observed single-primary data tier and the standard replication/high-availability components that the configuration does **not** include.

```mermaid
flowchart TD
    subgraph Clients["Database Clients"]
        Pipeline["External weekly pipeline<br/>out of repo - batch writes"]
        Api["api service<br/>synchronous read queries"]
    end

    subgraph Observed["Observed Data Tier - docker-compose postgres service"]
        Primary["postgres:15 primary<br/>database db - single instance"]
        Vol["Bind mount ./data:/data<br/>PGDATA /var/lib/postgresql/data not mapped"]
    end

    Pipeline -->|"weekly INSERT rows"| Primary
    Api -->|"SELECT via psycopg2"| Primary
    Primary --- Vol

    subgraph Absent["Replication / HA Prerequisites - NOT configured"]
        Standby["Hot standby / read replica"]
        WAL["WAL streaming / archiving"]
        Failover["Failover / clustering controller"]
    end

    Primary -.->|"no streaming replication"| Standby
    Primary -.->|"no WAL shipping"| WAL
    Primary -.->|"no automated failover"| Failover
```

**Figure 6.2.1-2: Replication Architecture — Observed Single Primary and Absent Replication Components.** Solid arrows show the current single-instance topology; dashed elements in the "Absent" group are replication/HA components the repository does not declare. This diagram is scoped to the database data tier and complements (does not duplicate) the application scalability diagram in Section 6.1.3.

#### 6.2.1.6 Backup Architecture

**No automated backup architecture is defined.** The only persistence-related configuration on the `postgres` service is a single bind mount, `./data:/data` (`docker-compose.yml`), and a top-level named volume `data` that **no service references**. There are no `pg_dump`/`pg_basebackup` invocations, no snapshot jobs, no WAL archiving, and no backup scripts anywhere in the repository (verified by grep).

A precise, evidence-based caveat applies to the one volume that is wired: the `postgres:15` image stores data in its default directory `/var/lib/postgresql/data`, and **no `PGDATA` environment variable overrides this**, so the `./data:/data` mount maps a path that is **not** the database's actual data directory. As recorded in Section 3.5.4 and Section 6.1.4.2, this mapping therefore does not by itself guarantee durability of the database files across container re-creation. Because the application also contains no schema-creation or seed logic, the effective recovery path for the data is to **re-run the external weekly ingestion pipeline** to repopulate `tracks` and `yearly_avg` (Section 6.1.4.2, Section 4.5.5). The backup and fault-tolerance posture is examined further from a compliance standpoint in Section 6.2.3.

| Backup / Durability Aspect | Status | Evidence |
|---|---|---|
| Automated backups / dumps / snapshots | Not present | No `pg_dump`/`pg_basebackup`/scripts (repository-wide grep) |
| WAL archiving / point-in-time recovery | Not present | No `wal_level`/archive config (`docker-compose.yml`) |
| Volume-based durability | Partial / mismatched | `./data:/data` mount; default `PGDATA` not mapped (`docker-compose.yml`) |
| Data recovery path | External dependency | Re-run out-of-repo weekly pipeline (`README.md`; Section 4.5.5) |


### 6.2.2 Data Management

Data management in this system is shaped by a strict separation of responsibilities: the **application in this repository is a read-only consumer**, while all data creation, schema evolution, and population belong to the out-of-repository weekly ingestion pipeline (Section 3.4, Section 6.1.2.1). The subsections below document each data-management concern as it is actually implemented — and, where a facility is absent, record the absence with evidence.

#### 6.2.2.1 Migration Procedures

**No database migration procedure exists in the repository.** There is no migration framework configured — `requirements.txt` pins neither Alembic nor Flask-Migrate — and there is no `migrations/` directory, `alembic.ini`, `env.py`, versioned migration script, or `db.create_all()` invocation anywhere in the tree (verified by grep). The `flask db` command group is therefore not available, and the application performs no schema bootstrapping at startup.

In practice this means schema changes are handled entirely **outside this codebase**: the external pipeline creates and alters the physical `tracks` and `yearly_avg` tables, and a corresponding change to the ORM class in `api/models.py` must be made by hand to keep the read model in sync. There is no automated, ordered, or reversible migration history, and no forward/rollback tooling. This is consistent with Section 3.5.2 ("the repository contains no schema-creation, migration, or seed code").

#### 6.2.2.2 Schema and Data Versioning Strategy

There is **no schema or data versioning mechanism**. Because no migration tool is present, there is no `alembic_version` (or equivalent) table tracking schema revisions, and the data model itself carries **no versioning columns** — neither `Tracks` nor `YearlyAvg` declares a `version`, `created_at`, `updated_at`, or soft-delete/`is_current` column (`api/models.py`). Row-level history and change tracking are therefore not modeled; the temporal dimensions that do exist (`tracks.week`, `yearly_avg.year`) are business data, not record-versioning metadata.

The only versioning actually present is at the **build and dependency level**, which pins the moving parts around the database rather than the schema:

| Versioned Artifact | Mechanism | Evidence |
|---|---|---|
| Database engine | Pinned image tag `postgres:15` | `docker-compose.yml` |
| Data-access libraries | Exact pins (SQLAlchemy 1.4.19, Flask-SQLAlchemy 2.5.1, psycopg2 2.9.6, pandas 2.0.0) | `requirements.txt` |
| Application (frontend) | Declared version `0.1.0` | `frontend/package.json` |

The backend package declares no version string of its own, and the repository's baseline is simply its current committed state.

#### 6.2.2.3 Archival Policies

**No archival, retention-tiering, or purge policy is defined.** The application issues only reads and never deletes (no `DELETE`/`UPDATE` anywhere in `api/routes.py`), so from the application's perspective data is effectively **append-only and retained indefinitely** — there is no time-to-live, no partition rotation to cold storage, no summarize-and-drop step, and no scheduled cleanup job. Historical chart data is intended to accumulate from the first Billboard Hot 100 week onward (`README.md` cites August 1958 as the chart's origin).

One related observation, which is a **client-side bound rather than a database archival rule**: the Tracks view's `DatePicker` restricts selectable weeks to the range `1958-07-27 … 2021-11-13` and defaults to `2021-11-13` (`frontend/src/components/tracks/DatePicker.js`, Section 5.2.2). That window reflects the historical extent of the deployed dataset the UI targets; it does not archive, tier, or expire any rows in PostgreSQL.

#### 6.2.2.4 Data Storage and Retrieval Mechanisms

**Storage.** Data at rest lives in the two PostgreSQL tables described in Section 6.2.1. The application writes nothing; the tables are populated by the external pipeline's weekly batch (Section 6.2.4.5). Persistence is mediated by Flask-SQLAlchemy (`db = SQLAlchemy(app)` with `SQLALCHEMY_TRACK_MODIFICATIONS = False`), and the ORM session is a per-request scoped session torn down at request end, running an implicit **read-only transaction** with no `commit`/`rollback` (Section 4.4.2).

**Retrieval.** All retrieval flows through the SQLAlchemy ORM query API in `api/routes.py`; results are materialized with `.all()` (no streaming, no server-side cursors), serialized to JSON by Marshmallow (`.dump()` → `jsonify`), and — for two endpoints — post-processed in pandas. The four data-reading endpoints use the following access patterns:

| Endpoint | Table | Filter Predicate | Sort |
|---|---|---|---|
| `GET /api/track/<spotify_id>` | `tracks` | `filter_by(spotify_id=...)` (equality) | `order_by(rank)` |
| `GET /api/week/<week>` | `tracks` | `filter_by(week=...)` (equality) | `order_by(rank)` |
| `GET /api/artist/<artist>` | `tracks` | `func.lower(artist) LIKE lower('%<artist>%')` | `order_by(week DESC)` |
| `GET /api/analysis/<feature>` | `yearly_avg` | none — `with_entities(year, <feature>)` projection | none |

Two retrieval mechanics are notable and evidenced in the code: none of these queries applies a `LIMIT`/`OFFSET`, so each returns its **full** result set (Section 5.2.1), and for `GET /api/analysis/<feature>` the projected column is selected dynamically with `getattr(YearlyAvg, feature)` from the raw path parameter. Aggregation for the two UI endpoints happens **in-process in pandas** (`api/funcs.py`): `get_weekly_data` computes weekly per-feature means, and `get_rolling_avg` computes a `.rolling(5)` mean series — the database itself performs no `GROUP BY`/`AVG`.

Figure 6.2.2-1 traces the **data lifecycle** end to end — the write path from the upstream sources into the tables, and the read path from the tables out to the client — complementing (not duplicating) the service-interaction view in Section 6.1.2.

```mermaid
flowchart LR
    subgraph Sources["Upstream Sources - external"]
        BB["Billboard Hot 100<br/>weekly chart page"]
        SP["Spotify Web API<br/>audio features via Spotipy"]
    end

    subgraph Ingest["Weekly Ingestion - out of repository"]
        Pipe["Scrape + enrich + aggregate<br/>pandas to_sql writes"]
    end

    subgraph Store["PostgreSQL database db"]
        T["tracks<br/>song-per-week rows"]
        Y["yearly_avg<br/>per-year feature means"]
    end

    subgraph Read["api service - read path"]
        Q["SQLAlchemy ORM queries<br/>filter_by / like / with_entities"]
        Agg["pandas helpers<br/>get_weekly_data / get_rolling_avg"]
        Ser["Marshmallow dump + jsonify"]
    end

    Client["React SPA<br/>amCharts radar / line"]

    BB --> Pipe
    SP --> Pipe
    Pipe -->|"weekly batch INSERT"| T
    Pipe -->|"recompute rollup"| Y
    T -->|"SELECT by week / artist / spotify_id"| Q
    Y -->|"SELECT year + feature"| Q
    Q --> Agg
    Agg --> Ser
    Q --> Ser
    Ser -->|"HTTP / JSON"| Client
```

**Figure 6.2.2-1: Data Flow Diagram — Write and Read Lifecycle.** The left group is the out-of-repository write path (Billboard + Spotify → weekly pipeline → tables); the right group is this repository's read path (ORM query → optional pandas aggregation → Marshmallow serialization → SPA). The `tracks` and `yearly_avg` tables are the only durable data stores.

#### 6.2.2.5 Caching Policies

There is **no data-caching policy** because there is no cache to govern. The repository configures no cache server or library — no Redis, Memcached, or `Flask-Caching` in `requirements.txt`, and no HTTP `Cache-Control` headers or in-process memoization on any route (Section 3.5.3, Section 4.4.3). Consequently there is **no cached data, and therefore no TTL, no eviction policy, and no invalidation strategy** to define; every request re-queries PostgreSQL.

The system does contain one deliberate **data-modeling** optimization that is easily mistaken for a cache: the `yearly_avg` table is a **persisted pre-aggregation** of per-year feature means, maintained by the upstream pipeline. It reduces per-request work for `GET /api/analysis/<feature>` (the endpoint reads pre-computed yearly rows rather than scanning all of `tracks`), but it is durable modeled data with no expiry semantics — a modeling choice, not a runtime cache (Section 3.5.3). The only incidental caching in the delivery path is browser-side: the Create React App build emits content-hashed static assets that browsers may cache, and amCharts holds the current dataset in memory for the mounted component's lifetime (Section 4.4.3). The performance implications of this cache-free posture are analyzed in Section 6.2.4.2.


### 6.2.3 Compliance Considerations

No regulatory or contractual compliance framework (e.g., GDPR, HIPAA, SOC 2, PCI-DSS) is referenced or configured anywhere in the repository, consistent with the "Compliance Requirements: None defined in the repository" finding recorded for every feature in Section 2.3. The subsections below document the data-governance-relevant characteristics that **are** observable — retention, backup/fault tolerance, privacy, audit, and access control — each grounded in the code and configuration, and each noting where a control is absent.

#### 6.2.3.1 Data Retention Rules

**No formal data-retention rule is defined.** As established in Section 6.2.2.3, the application never deletes or updates data, and there is no TTL, expiry, or purge job; stored data is retained **indefinitely**. The nature of the retained data mitigates the compliance weight of this: the two tables hold **public music-chart data** — song title, artist name, chart rank, chart week, Spotify track identifier, and numeric audio-feature values (`api/models.py`). No end-user records, account data, or behavioral tracking are stored, so there is no personal-data retention clock to manage within this repository. The freshness (not the retention) of the data is governed by the external weekly writer.

#### 6.2.3.2 Backup and Fault-Tolerance Policies

The backup posture is covered in detail in Section 6.2.1.6 and Section 6.1.4.2 and is summarized here from a compliance standpoint: **there are no backups, snapshots, WAL archiving, replication, or defined RPO/RTO**. Fault tolerance is limited to a single container-level restart policy. The database-relevant controls are:

| Control | Status | Evidence |
|---|---|---|
| `api` service auto-restart | Present | `restart: on-failure` (`docker-compose.yml`) |
| `postgres` service auto-restart | **Not set** | No `restart` policy on `postgres` (`docker-compose.yml`) |
| DB readiness gating | Not present | `depends_on` orders startup only (`docker-compose.yml`) |
| Backups / replication / RPO-RTO | Not present | No backup scripts, replica, or targets (repository-wide) |

Because `depends_on: postgres` orders container start but does not wait for the database to accept connections, requests during the warm-up window surface as HTTP 500 (Section 6.1.4.1). The `postgres` service itself carries **no restart policy at all**, so a database process exit is not automatically recovered. Data recovery, in the absence of backups, depends on re-running the external ingestion pipeline (Section 6.2.1.6).

#### 6.2.3.3 Privacy Controls

There are **no privacy-specific controls, and no personal end-user data to protect**. The application implements no user accounts, authentication, sessions, cookies, analytics, or tracking (verified across `api/` and `frontend/src/`), so it neither collects nor stores personal user information; the only "identity-like" values in the database are public artist/track names and Spotify track ids. Correspondingly, the following data-protection mechanisms are absent and recorded as observations rather than deficiencies against any stated requirement:

- **Encryption at rest.** Not configured. The `postgres:15` service uses default settings with no volume-level or column-level encryption (`docker-compose.yml`).
- **Encryption in transit.** The connection DSN `postgresql://postgres:postgres@postgres/db` specifies no `sslmode` and no TLS parameters (`api/__init__.py`); traffic to the database is not explicitly secured by configuration.
- **Secrets management.** Database credentials are **hard-coded** (`postgres`/`postgres`) in both the DSN and the Compose environment, with no vault, secret store, or environment-override mechanism (Section 3.5.4, Section 5.4.4).
- **Data masking / tokenization / field-level redaction.** None; Marshmallow schemas project columns verbatim (`api/models.py`).

#### 6.2.3.4 Audit Mechanisms

**No audit mechanism exists at the database or application layer.** The data model records no audit metadata — there is no `created_at`/`updated_at`, no actor/`created_by` column, and no history/soft-delete table (`api/models.py`) — and there are no database triggers, audit tables, or change-data-capture configured in the repository. At the application layer there is no logging or tracing framework and no `@app.errorhandler`/request logger (Section 5.4.2); the only runtime output is the incidental stderr of the Flask development server and the `postgres` container. Because the application is read-only and unauthenticated, there is likewise no notion of an auditable actor or write event to record.

#### 6.2.3.5 Access Controls

Access control is **effectively open** at every layer relevant to the database. The application exposes all endpoints as public, unauthenticated `GET` routes and enables permissive cross-origin access via `CORS(app)` (Section 5.4.4); the database is reached with a single shared superuser account. The observable controls are enumerated below:

| Layer | Access Control | Evidence |
|---|---|---|
| Application authN/authZ | None — all routes public `GET` | `api/routes.py`; `CORS(app)` in `api/__init__.py` |
| Network exposure | `postgres` port `5432` published to host | `docker-compose.yml` (`5432:5432`) |
| Database authentication | Single shared user `postgres`/`postgres` | `docker-compose.yml` env; DSN in `api/__init__.py` |
| DB roles / least-privilege / RLS | None — app connects as the superuser | No `GRANT`/`REVOKE`/role or row-level-security policy in repo |

The `POSTGRES_USER=postgres` account created by the image is a superuser, and the application connects as that same account, so there is no separation between an administrative role and a least-privileged read-only application role, and no PostgreSQL row-level or column-level security is defined. Publishing `5432` to the host additionally makes the database reachable outside the Compose network with those fixed credentials. These are the same security considerations flagged in Sections 3.5.4, 3.6, and 5.4.4, viewed here through the lens of database access governance.


### 6.2.4 Performance Optimization

This subsection examines database performance at the query, caching, connection, topology, and batch levels. It extends the higher-level performance summary in Section 6.1.3.3 with the specific data-access characteristics of `api/routes.py` and `api/funcs.py`, and — in keeping with the rest of this specification — records optimizations that are present alongside those that are absent.

#### 6.2.4.1 Query Optimization Patterns

The read path exhibits a small number of deliberate optimizations and several characteristics that bound performance under load. The optimizations that **are** present:

- **Parameterized access through the ORM.** Every query is expressed through the SQLAlchemy ORM (`filter_by`, `filter`, `with_entities`, `order_by`), so bound values are parameterized rather than string-concatenated (Section 5.3.5); this is a correctness/safety benefit and enables statement reuse.
- **Read from a pre-aggregated table.** `GET /api/analysis/<feature>` reads the materialized `yearly_avg` summary instead of scanning and grouping `tracks`, and it uses `with_entities(YearlyAvg.year, getattr(YearlyAvg, feature))` to project **only the two columns** it needs, minimizing the row width transferred (Section 6.1.3.3).

The characteristics that **constrain** query performance, all evidenced in `api/routes.py` and Section 6.2.1.3:

| Query Behavior | Performance Characteristic | Location |
|---|---|---|
| No `LIMIT`/`OFFSET`/pagination on any route | Full result set materialized with `.all()`; payload grows with data | `api/routes.py` |
| Artist search uses `LIKE '%<artist>%'` (leading wildcard) | Non-sargable — cannot use a B-tree index even if one existed | `get_tracks_by_artist` |
| Filters on `week`, `spotify_id`, `artist`; sort on `rank`/`week` | No secondary indexes declared → sequential scans within the repo model | `api/models.py` |
| Aggregation performed in pandas, not SQL | Rows shipped to the app for every `week`/`analysis` request; recomputed each time | `api/funcs.py` |

In short, the only query pattern designed for cheap reads is the trend endpoint's use of the precomputed `yearly_avg` projection; the `tracks`-backed endpoints rely on unindexed, unpaginated scans as defined in the repository (any indexes added by the external pipeline are outside this codebase).

#### 6.2.4.2 Caching Strategy

**There is no database or application caching strategy.** As detailed in Section 6.2.2.5 and Section 4.4.3, no cache server, caching library, HTTP `Cache-Control`, or route-level memoization exists, so every `/api/week` and `/api/analysis` request re-executes its SQL query **and** re-runs the pandas aggregation from scratch. The performance benefit that would normally come from a cache is instead approximated — only for the trend endpoint — by the persisted `yearly_avg` pre-aggregation, which is durable modeled data rather than a runtime cache with TTL/invalidation. The only incidental caching on the delivery path (browser-cached content-hashed static assets and in-memory amCharts datasets) is client-side and does not reduce database load. This cache-free design keeps the system simple and always-fresh at the cost of repeated query and CPU work per request (ADR-04, Section 6.1.3.3).

#### 6.2.4.3 Connection Pooling

Connection pooling is **left entirely at framework defaults**. `api/__init__.py` sets only `SQLALCHEMY_DATABASE_URI` and `SQLALCHEMY_TRACK_MODIFICATIONS`; it defines **no `SQLALCHEMY_ENGINE_OPTIONS`, no `create_engine` call, and no pool parameters** (verified by grep — no `pool_size`, `max_overflow`, `pool_pre_ping`, or `pool_recycle`). Flask-SQLAlchemy therefore builds the engine with SQLAlchemy's default pooling for a PostgreSQL/`psycopg2` dialect:

| Pool Parameter | Effective Value | Source |
|---|---|---|
| Pool class | `QueuePool` | SQLAlchemy default (non-SQLite dialect) |
| `pool_size` | 5 | SQLAlchemy default (not overridden) |
| `max_overflow` | 10 | SQLAlchemy default (not overridden) |
| `pool_pre_ping` | Disabled | Not configured in `api/__init__.py` |

Two practical implications follow. First, because `pool_pre_ping` is off and there is no readiness gate (Section 6.2.3.2), a connection that has gone stale — for example, during the database warm-up window — surfaces as an error rather than being transparently recycled. Second, the container's default command runs the **single-process Flask development server** (`CMD python3 app.py`, not the pinned `gunicorn`; ADR-07), so requests are effectively serialized at the process level and the pool's headroom is rarely exercised; the pool is not tuned for a multi-worker deployment. This matches the "no connection-pool tuning beyond SQLAlchemy defaults" observation in Section 5.2.3 and Section 6.1.3.2.

#### 6.2.4.4 Read/Write Splitting

**Read/write splitting is not applicable and not configured.** The system has exactly one database endpoint — the `postgres` host in the single DSN (`api/__init__.py`) — and no read-replica or standby exists to split traffic toward (Section 6.2.1.5). Moreover, the split is moot at the application level because **this repository's code performs only reads**: the entire read/write separation is architectural rather than routed — reads are served by the `api` service against the primary, and writes are performed exclusively by the out-of-repository weekly pipeline against that same primary (Section 6.2.2.4). There is no primary/replica routing layer, connection-role selection, or `Session` binding to distinct engines anywhere in the codebase.

#### 6.2.4.5 Batch Processing Approach

Batch processing exists on the **write side only** and lives outside this repository. Per `README.md`, a separate script runs **weekly** to scrape the Billboard chart, enrich each track with Spotify audio features, and write the rows into PostgreSQL — a scheduled bulk-ingestion batch whose `yearly_avg` output shape is consistent with a pandas `DataFrame.to_sql()` write (Section 6.2.1.2). That producer is not present in the tree; the application only consumes its output.

On the **read side**, there is no server-side batching, job queue, or asynchronous worker (no Celery/RQ/cron in `requirements.txt` or the Compose stack). The nearest analogue is **in-request vectorized computation**: `get_weekly_data` and `get_rolling_avg` load a query's full result set into a pandas `DataFrame` and compute means / a `.rolling(5)` series over the whole set at once, rather than iterating row by row (`api/funcs.py`). This is efficient per call but is recomputed on every request (Section 6.2.4.2) and is bounded by the unpaginated result sizes noted in Section 6.2.4.1.

| Batch Concern | Approach | Evidence |
|---|---|---|
| Bulk data ingestion (writes) | External weekly scheduled batch (out of repo) | `README.md` |
| Server-side batching / async workers | None (synchronous per-request) | No queue/worker in `requirements.txt` |
| In-request aggregation | Vectorized pandas over full result set | `api/funcs.py` |


### 6.2.5 References

**Repository files examined for this section:**

- `api/models.py` - Established the two ORM entities (`Tracks`, `YearlyAvg`), their complete column lists and types, the primary-key-only constraint set (no secondary indexes/FKs/relationships), the `index`/pandas-`to_sql` signature, and the `TrackSchema`/`YearlyAvgSchema` serialization surfaces (including the omitted `loudness` on the yearly table).
- `api/__init__.py` - Established the PostgreSQL DSN (`postgresql://postgres:postgres@postgres/db`), `SQLALCHEMY_TRACK_MODIFICATIONS = False`, the absence of any `SQLALCHEMY_ENGINE_OPTIONS`/pool configuration, and the SQLAlchemy/Marshmallow extension initialization.
- `api/routes.py` - Established the read-only query patterns per endpoint (`filter_by`, `func.lower(...) LIKE`, `with_entities` + `getattr`, `order_by`), the absence of `LIMIT`/pagination, and the read-only transaction behavior (no writes/commits).
- `api/funcs.py` - Established the in-process pandas aggregation (`get_weekly_data` per-feature means; `get_rolling_avg` `.rolling(5)` series) used instead of SQL `GROUP BY`/`AVG`.
- `docker-compose.yml` - Established the `postgres:15` single-instance service, hard-coded credentials, the `./data:/data` bind mount, the unreferenced top-level named volume `data`, the published `5432:5432` port, and the absence of replicas/healthchecks/`restart` on `postgres`.
- `Dockerfile` - Established the container build (`python:3.11-slim-buster`, `libpq-dev`/`gcc` for `psycopg2`) and the runtime command `python3 app.py` (single-process Flask dev server, not the pinned `gunicorn`).
- `requirements.txt` - Established the data-access stack pins (SQLAlchemy 1.4.19, Flask-SQLAlchemy 2.5.1, psycopg2 2.9.6 / psycopg2-binary 2.9.5, Flask-Marshmallow 0.14.0, pandas 2.0.0) and the absence of any migration (Alembic/Flask-Migrate), caching (Redis/Memcached), or queue/worker libraries.
- `README.md` - Established the external weekly ingestion pipeline (Billboard scrape + Spotipy audio-feature enrichment) that owns all DDL and writes, the endpoint contract, and the chart's 1958 origin.
- `frontend/package.json` - Established the declared application version `0.1.0` used in the versioning discussion.
- `frontend/src/components/tracks/DatePicker.js` - Established the client-side selectable date window (`1958-07-27 … 2021-11-13`) referenced under archival policies.

**Repository folders examined:**

- `api/` - The complete four-file Flask backend package; confirmed the entire persistence and data-access layer resides here and that no migration/seed/DDL module exists.

**Cross-referenced Technical Specification sections:**

- `2.3 Functional Requirements` - Confirmed "Compliance Requirements: None defined in the repository" across features.
- `3.4 Third-Party Services` - External weekly pipeline and Spotify audio-feature dependency (write path).
- `3.5 Databases & Storage` - PostgreSQL 15 engine, read-only persistence strategy, absence of a caching tier, and volume/`PGDATA` storage details.
- `3.6 Development & Deployment` - Containerization and the dev-server-vs-`gunicorn` runtime caveat.
- `4.4 State Management and Transaction Boundaries` - Read-only ORM session/transaction boundaries and the no-application-caching finding.
- `4.5 Error Handling and Recovery Flows` - Data-recovery path (re-run external pipeline) referenced under backup/DR.
- `5.2 Component Details` - PostgreSQL component profile (single instance, default pool, no in-repo indexes) and the `yearly_avg` table name in its sequence diagram.
- `5.3 Technical Decisions` - ADR-04 (no cache), ADR-07 (dev server vs. gunicorn), and parameterized-query rationale (5.3.5).
- `5.4 Cross-Cutting Concerns` - Logging/audit absence (5.4.2) and security posture (5.4.4).
- `6.1 Core Services Architecture` - Monolith topology, performance techniques/omissions (6.1.3.3), scalability/resource facilities (6.1.3.2), and data-redundancy/disaster-recovery posture (6.1.4.2).

**Web searches:** None conducted for this section; all findings are grounded in direct repository inspection and cross-referenced Technical Specification sections.


## 6.3 Integration Architecture

### 6.3.1 Integration Architecture Overview and Scope

Integration Architecture **is applicable** to this system, but its runtime integration surface is deliberately small and asymmetric. The deployed application is a **two-tier, single-origin web application** — a monolithic Flask backend (the `api` service) that both serves a compiled React 17 single-page application (SPA) and exposes a small read-only JSON HTTP API, backed by a single PostgreSQL 15 database (the `postgres` service), all coordinated as a Docker Compose stack (`docker-compose.yml`, `Dockerfile`). At runtime the application integrates in only two directions: **inbound** HTTP/JSON from the browser and **southbound** read-only queries to PostgreSQL.

The system's third-party integrations (Spotify and Billboard) are **not performed by the deployed application**. They are executed by an **external, out-of-repository weekly ingestion pipeline** that shares the PostgreSQL database. `README.md` states that "a separate script, running weekly … scrapes the Billboard site page and adds each song into the database," and that the script uses **Spotipy** to fetch **Spotify Audio Features** for each track. That pipeline is described only in `README.md` and mirrored in `frontend/src/components/about/AboutSection.js`; it contains no code in this repository (there is no `spotipy` dependency in `requirements.txt`, and no HTTP-client such as `requests` or scraper module anywhere in `api/`). The Flask application therefore consumes the *results* of those integrations from the database rather than calling Spotify or Billboard itself.

This section documents the API design, message processing, and external-system integration that actually exist in the repository, grounding every claim in observed code and configuration and marking any category that is deliberately absent as such.

#### 6.3.1.1 Applicability and Integration Boundaries

The application presents exactly three integration boundaries, consistent with the high-level architecture (§5.1):

- **Northbound (client boundary).** Browser-initiated HTTP requests reach the six routes declared in `api/routes.py`; JSON is produced through `flask.jsonify` and Marshmallow serialization. The `api` service is published on host port **80 → container port 5000** (`docker-compose.yml`).
- **Southbound (persistence boundary).** The route layer reads from PostgreSQL through the SQLAlchemy ORM over `psycopg2`, using the hard-coded DSN `postgresql://postgres:postgres@postgres/db` (`api/__init__.py`); the `postgres` service publishes port **5432**.
- **Ingestion boundary (shared database).** The external weekly pipeline writes `Tracks` and `YearlyAvg` rows directly into PostgreSQL. It integrates through the database only — there is **no API contract in this repository** for the write path (`README.md`, `api/models.py`).

A defining property of this topology is that the runtime application makes **no outbound third-party API calls** — the Spotify/Billboard references surfaced in the UI are informational hyperlinks, not live service integrations.

#### 6.3.1.2 Integration Landscape

The following diagram shows every integration channel in and around the system, annotated by protocol and integration pattern. Solid edges are integrations exercised by the deployed application; dashed edges are performed by other actors (the browser fetching fonts, and the out-of-repository weekly pipeline).

```mermaid
flowchart LR
    Browser["Web Browser<br/>React 17 SPA (fetch)"]
    Fonts["Google Fonts CDN<br/>fonts.googleapis.com"]
    BB["Billboard Hot 100<br/>chart web page"]
    SP["Spotify Web API<br/>Audio Features"]

    subgraph Deployed["Deployed Docker Compose Stack (this repository)"]
        API["api service<br/>Flask monolith<br/>SPA host + JSON API"]
        PG[("postgres service<br/>PostgreSQL 15 'db'")]
    end

    subgraph ExternalPipe["Weekly Ingestion Pipeline (out of repository)"]
        Pipe["Billboard scraper<br/>+ Spotipy enrichment"]
    end

    Browser -->|"HTTP/1.1 JSON - same-origin fetch (read)"| API
    API -->|"index.html + hashed JS/CSS"| Browser
    Browser -.->|"web fonts over HTTPS"| Fonts
    API -->|"SQLAlchemy / psycopg2 - read-only"| PG
    Pipe -.->|"HTML page scrape (HTTP)"| BB
    Pipe -.->|"Spotipy over HTTPS"| SP
    Pipe -.->|"weekly batch writes (direct SQL)"| PG
```

*Figure 6.3.1-1: Integration landscape and channels. Solid edges are integrations exercised by the deployed `api` service; dashed edges are performed by the browser or the external pipeline.*

The integration points are summarized below. All protocol and pattern facts are drawn directly from the repository; items marked "external pipeline only" are described in `README.md`/`AboutSection.js` but have no implementing code in the tree.

| Integration | Integration Pattern | Protocol & Direction |
|---|---|---|
| Browser SPA ↔ `api` service | Synchronous client-server request/response | HTTP/1.1, JSON; inbound to API |
| `api` service ↔ PostgreSQL | ORM data access (read-only) | PostgreSQL wire via SQLAlchemy/`psycopg2`; southbound |
| External pipeline → PostgreSQL | Shared-database integration (weekly batch) | Direct SQL writes; inbound to DB (out of repo) |
| External pipeline → Spotify Web API | Third-party API client via Spotipy | HTTPS; outbound (external pipeline only) |
| External pipeline → Billboard Hot 100 | Web-page scrape | HTTP(S) page fetch; outbound (external pipeline only) |
| Browser → Google Fonts | Static-asset CDN dependency | HTTPS; outbound from browser |

#### 6.3.1.3 External Dependencies

The complete set of external dependencies — runtime and build-time — is enumerated below. Only the browser, PostgreSQL, and Google Fonts are exercised by the deployed application at runtime; Spotify and Billboard are reached exclusively by the external pipeline.

| Dependency | Purpose | Consumed By |
|---|---|---|
| Spotify Web API (Audio Features) | Per-track audio-feature enrichment (`tempo`, `energy`, `valence`, …) | External weekly pipeline (via Spotipy) |
| Billboard Hot 100 web page | Source of weekly chart rankings | External weekly pipeline (scrape) |
| PostgreSQL 15 (`postgres:15`) | Sole persistent datastore for `Tracks` / `YearlyAvg` | `api` service (read); pipeline (write) |
| Google Fonts (`Jost` family) | Web-font delivery for the SPA | Browser (`frontend/public/index.html`) |
| PyPI packages (`requirements.txt`) | Backend build/runtime libraries (Flask, SQLAlchemy, pandas, …) | Docker image build (`Dockerfile`) |
| npm registry (`package.json` / lockfile) | Frontend build toolchain and libraries | CRA build (`react-scripts build`) |

Two declared frontend dependencies are **not** integration channels and are documented here for completeness: `axios` is declared in `frontend/package.json` but never imported (the SPA uses the browser-native `fetch` API in `TracksSection.js` and `TrendsSection.js`), and `plotly.js`/`react-plotly.js` are declared but unused (charts are rendered with `@amcharts/amcharts4`).

### 6.3.2 API Design

The API is a small, read-only **REST-style HTTP interface** defined entirely in `api/routes.py` and bootstrapped in `api/__init__.py`. It exposes six routes on a single Flask application that also serves the compiled SPA, so the API and the UI share one origin and one deployable process. The diagram below shows the request path from consumers through the ingress, the permissive CORS layer, URL routing, the route-handler families, and JSON serialization.

```mermaid
flowchart TB
    subgraph Consumers["API Consumers"]
        UI["React SPA<br/>native fetch"]
        Direct["Direct HTTP client<br/>(browser URL / curl)"]
    end

    subgraph Ingress["Ingress"]
        Prod["Production: Docker port map<br/>host 80 to container 5000"]
        Dev["Development: CRA dev proxy<br/>localhost:5000"]
    end

    subgraph FlaskApp["Flask 'api' Application"]
        CORSL["CORS middleware<br/>CORS(app) - all origins"]
        Router["URL routing<br/>Werkzeug @app.route"]
        subgraph Handlers["Route Handlers (api/routes.py)"]
            StaticH["index() - serves SPA shell"]
            RedirH["home() - 302 redirect"]
            DataH["4 data routes - ORM query"]
        end
        Serialize["Serialization<br/>Marshmallow + flask.jsonify"]
    end

    PG[("PostgreSQL 15")]

    UI --> Dev
    UI --> Prod
    Direct --> Prod
    Dev --> CORSL
    Prod --> CORSL
    CORSL --> Router
    Router --> StaticH
    Router --> RedirH
    Router --> DataH
    DataH --> Serialize
    DataH --> PG
    Serialize --> UI
```

*Figure 6.3.2-1: API architecture — consumer, ingress, CORS, routing, handler families, and serialization.*

#### 6.3.2.1 Protocol Specifications

The API uses **HTTP/1.1** as its transport and **JSON** as its primary payload format. Responses are produced with `flask.jsonify` (media type `application/json`) after Marshmallow serialization, except for the SPA-shell route (which returns `text/html`) and the current-week route (which returns a `302` redirect). Communication is strictly **synchronous request/response**; there is no gRPC, GraphQL, SOAP, WebSocket, or server-sent-events surface anywhere in the repository (confirmed by the absence of any corresponding library or route).

- **Verbs.** All six routes are declared `GET` (the data routes carry an explicit `methods=['GET']`; `/` uses Flask's default `GET`). No `POST`/`PUT`/`PATCH`/`DELETE` route exists — the API is read-only, consistent with the externalized write path (§6.3.1).
- **Path parameters.** Variable data is carried in the URL path (`<week>`, `<feature>`, `<spotify_id>`, `<artist>`), not query strings or request bodies. `request` is imported in `api/routes.py` but never used, so no query-string or body parsing occurs.
- **Runtime server.** The process is started by `app.py` via `app.run(host='0.0.0.0')` — the Werkzeug development server, bound to all interfaces on port 5000. `gunicorn` 20.1.0 is pinned in `requirements.txt` but is **not** wired into the container command (`Dockerfile` runs `CMD ["python3","app.py"]`).
- **CORS.** `CORS(app)` (`api/__init__.py`) applies Flask-CORS 3.0.10 permissively to all routes and origins; because production serves the SPA same-origin, cross-origin headers are exercised mainly in the proxied development mode.

#### 6.3.2.2 Endpoint Catalog and Contracts

The complete route surface is enumerated below (all methods are `GET`).

| Path | Purpose | Response Body |
|---|---|---|
| `/` | Serve the compiled SPA shell | `index.html` (static, `text/html`) |
| `/api/` | Redirect to the current chart week | `302` → `week/<current-Saturday>` |
| `/api/week/<week>` | Ranked songs + weekly feature means | JSON `{week, songs, averages, avgTempo}` |
| `/api/analysis/<feature>` | Annual + rolling average of a feature | JSON `{feature, data}` |
| `/api/track/<spotify_id>` | All chart appearances of a track | JSON array of track objects |
| `/api/artist/<artist>` | Case-insensitive artist search | JSON array of track objects |

Path-parameter formats and their (server-side) handling are summarized next. There is no allow-list validation: malformed or unknown values raise unhandled exceptions that surface as HTTP 500 (§6.3.3.4, §4.5).

| Path Parameter | Endpoint | Handling |
|---|---|---|
| `<week>` | `/api/week` | Parsed `%Y-%m-%d`, normalized to a Saturday by `get_query_week`; malformed → `ValueError` → 500 |
| `<feature>` | `/api/analysis` | Resolved via `getattr(YearlyAvg, feature)`; unknown column → `AttributeError` → 500 |
| `<spotify_id>` | `/api/track` | Exact equality match on `spotify_id`; no match → empty array |
| `<artist>` | `/api/artist` | Case-insensitive substring `LIKE '%artist%'`; `%`/`_` not escaped |

The two JSON response envelopes consumed by the SPA are fixed contracts: `/api/week` returns an object with `week` (string), `songs` (serialized `TrackSchema` array), `averages` (five `{feature, mean, full}` entries), and `avgTempo` (integer); `/api/analysis` returns `{feature, data}` where `data` is an array of `{year, value, rolling}`. The following sequence shows the transport-level integration mechanics — the development proxy hop, the `/api/` → `/api/week/<current>` redirect chain, and the permissive CORS response header — for a representative consumer flow.

```mermaid
sequenceDiagram
    autonumber
    participant B as Browser (SPA)
    participant P as CRA Dev Proxy
    participant F as Flask api service
    participant DB as PostgreSQL 15

    Note over B,P: Production serves same-origin (host 80), development routes via proxy to port 5000
    B->>P: GET /api/ (current-week redirect route)
    P->>F: forward GET /api/
    F-->>P: 302 redirect to week/current-Saturday
    P-->>B: 302 with permissive CORS header
    B->>P: GET /api/week/current-Saturday
    P->>F: forward GET /api/week/week
    F->>DB: SELECT from tracks where week ordered by rank
    DB-->>F: matching rows
    F-->>P: 200 application/json week songs averages avgTempo
    P-->>B: 200 JSON with permissive CORS header
    Note over B: On HTTP status over 299 the SPA shows statusText and does not retry
```

*Figure 6.3.2-2: API request sequence emphasizing dev-proxy forwarding, the 302 current-week redirect, and CORS headers (distinct from the query/aggregation sequences in §5.2).*

#### 6.3.2.3 Authentication and Authorization

**None.** The API implements no authentication and no authorization. There is no login, session, token, JWT, OAuth, OIDC, or API-key mechanism anywhere in `api/`, and no route in `api/routes.py` performs any identity or permission check (confirmed by the absence of any auth library in `requirements.txt` and any auth code in the tree). `CORS(app)` is applied without an origin allow-list, so all six routes and the SPA are **effectively public and unauthenticated**. The only credentials in the project are the hard-coded PostgreSQL username/password (`postgres`/`postgres`) in the DSN (`api/__init__.py`) and the `postgres` service environment (`docker-compose.yml`); these are database credentials, not an end-user authentication framework. No role-based access control, scopes, or claims model exists.

#### 6.3.2.4 Rate Limiting Strategy

**None.** No rate limiting, throttling, quota, or request-shaping is present. There is no `Flask-Limiter` (or comparable) dependency, no per-client counters, and no reverse proxy or API gateway in front of the application to enforce limits (§6.3.4.3). Requests are served directly by a single Werkzeug development-server process, so the only practical bound on request volume is the capacity of that single process and its default SQLAlchemy connection pool.

#### 6.3.2.5 Versioning Approach

**No explicit API versioning.** The `/api` URL prefix namespaces the JSON routes but carries **no version segment** (there is no `/api/v1/…`), and the API performs no header-based or content-negotiation versioning. Because the backend and the SPA are built and deployed together from one repository (the Flask app serves `frontend/build`), the API contract is coupled to the SPA it ships with and to the database schema written by the external pipeline; there is no independent-version negotiation between client and server. The application itself declares a version only on the frontend package (`"version": "0.1.0"` in `frontend/package.json`); the backend declares none.

#### 6.3.2.6 API Documentation Standards

There is **no machine-readable API description** — no OpenAPI/Swagger document, and no generator such as `flasgger` or `apispec` (all absent from the repository). API documentation is **human-readable and maintained in two places**:

- **`README.md`** lists the four `/api/*` data endpoints with their path formats and semantics.
- **`frontend/src/components/about/AboutSection.js`** reproduces the same endpoint list inside the running application's "About" view and links out to the Billboard site, Wikipedia, the Spotipy documentation (pinned to the 2.18.0 docs URL), and the Spotify Web API audio-features reference.

One documentation/code inconsistency is worth noting for integrators: both `README.md` and the About view describe `/api/analysis` as returning a "3 year rolling average," while `api/funcs.py` (`get_rolling_avg`) computes a **5-period** rolling mean (`.rolling(5)`), and the LineChart legend label likewise reads "3 Year Rolling Average." The wire contract is therefore best confirmed against the code and the live response rather than the prose description.

### 6.3.3 Message Processing

The deployed system employs **no message-oriented middleware**. There is no message broker, event bus, publish/subscribe channel, or stream processor anywhere in the repository (a full search finds no Kafka, RabbitMQ, `pika`, Redis, SQS/Kinesis, Celery, or Socket.IO usage in `api/`, `requirements.txt`, or `frontend/package.json`). All runtime request handling is synchronous. The only processing that resembles messaging is **batch-oriented**: an external, scheduled weekly ingestion pipeline, and the synchronous, in-process aggregation the API performs on query results.

#### 6.3.3.1 Event Processing and Message Queue Architecture

**Not applicable / not present.** The application does not implement event-driven processing and integrates with no message queue. There are no producers or consumers, no topic/queue declarations, no event emitters, and no asynchronous task workers. Every capability is invoked in-process on the request thread: a browser request maps directly to a route handler that queries PostgreSQL and returns a response (§6.3.2). Because no broker exists, none of the associated concerns — partitioning, consumer groups, offset management, acknowledgements — apply here.

#### 6.3.3.2 Stream Processing Design

**Not applicable / not present.** There is no stream-processing framework (no Kafka Streams, Flink, Spark, or Kinesis client) and no continuous or windowed streaming computation. There is likewise no WebSocket or server-sent-events channel for pushing data to clients. Analytical results (weekly feature means and yearly rolling averages) are computed over **bounded, materialized result sets** on demand during a request, not over an unbounded stream. The "rolling average" produced by `/api/analysis` is a pandas windowed calculation on a finite per-request DataFrame (`api/funcs.py`), not a stream-processing operation.

#### 6.3.3.3 Batch Processing Flows

Two batch-flavored flows exist in the architecture, one external and one in-process:

- **External weekly ingestion (out of repository).** `README.md` and `frontend/src/components/about/AboutSection.js` describe "a separate script, running weekly" that scrapes the Billboard Hot 100 page and writes each song into the database, using **Spotipy** to enrich each track with Spotify Audio Features. This is a classic scheduled **extract-enrich-transform-load** batch job. It is **not present in this repository**: there is no scheduler/cron entry, no scraper module, and no `db.create_all()` or `DataFrame.to_sql()` call anywhere in the tree (all confirmed absent). The shape of the `YearlyAvg` model — a primary-key column literally named `index` plus a `year` stored as text — is characteristic of a pandas `DataFrame.to_sql()` export, consistent with a batch job that precomputes yearly aggregates and materializes them into the `yearly_avg` table.
- **In-process aggregation (read path).** During a request, `api/funcs.py` performs vectorized, batch-style computation over the rows returned by a query: `get_weekly_data` builds a pandas DataFrame and computes `int(mean × 100)` for five features plus an integer `avgTempo`, and `get_rolling_avg` computes a `.rolling(5)` mean and drops the leading `NaN` rows. This is synchronous and recomputed on every request (there is no cached or precomputed intermediate at the application layer beyond the externally materialized `YearlyAvg` table).

The end-to-end message/batch flow — from the external pipeline stages through PostgreSQL to the deployed read path — is shown below.

```mermaid
flowchart TD
    subgraph Pipeline["Weekly Batch Ingestion (out of repository)"]
        Sched["Schedule trigger<br/>(weekly)"]
        Scrape["Extract<br/>scrape Billboard chart page"]
        Enrich["Enrich<br/>Spotify Audio Features via Spotipy"]
        Transform["Transform<br/>compute yearly averages"]
        Load["Load<br/>write rows via direct SQL"]
        Sched --> Scrape --> Enrich --> Transform --> Load
    end

    PG[("PostgreSQL 15<br/>tracks + yearly_avg")]

    subgraph ReadPath["Deployed Read Path (this repository)"]
        Query["api service query<br/>SQLAlchemy ORM"]
        Agg["In-process pandas aggregation<br/>get_weekly_data / get_rolling_avg"]
        Resp["Synchronous JSON response<br/>to browser"]
        Query --> Agg --> Resp
    end

    Load -->|"weekly batch writes"| PG
    PG -->|"read-only queries"| Query
```

*Figure 6.3.3-1: Message/batch flow — the external weekly extract-enrich-transform-load pipeline writes to PostgreSQL; the deployed API reads and aggregates synchronously on demand.*

#### 6.3.3.4 Error Handling Strategy

For the flows above there is **no messaging-grade error handling** — no retry with backoff, no dead-letter queue, and no compensation logic (there is no queue to attach them to). The strategy that does exist is minimal and is detailed in §4.5; the message/batch-relevant aspects are summarized here.

| Capability | Status | Detail |
|---|---|---|
| Message queue / broker | Not present | No Kafka/RabbitMQ/SQS/Redis/Celery in any manifest |
| Automated retry / backoff | Not present | No retry loop or library in `api/` or `frontend/src/` |
| Dead-letter queue | Not present | No queue exists, so no DLQ |
| Backend exception handling | Not present | No `try/except` or `@app.errorhandler`; failures → HTTP 500 |
| Client-side handling | UI-only | `statusText` / `'No Data Found'` / loading; `fetch` not wrapped in `try/catch` |
| Process recovery | Container-level | `restart: on-failure` on the `api` service (`docker-compose.yml`) |
| Data recovery | Re-run pipeline | Empty/stale tables are repaired only by re-running the external pipeline |

Because the external pipeline is out of repository, any retry, deduplication, or idempotency it applies during ingestion is not observable here. On the read path, a failed batch aggregation (for example, aggregating an empty song list) raises an unhandled exception that becomes an HTTP 500, and the container's `restart: on-failure` policy protects only against whole-process crashes, not against individual failed requests. Notably, `depends_on: postgres` in `docker-compose.yml` orders container **start** but does not wait for database readiness, so requests issued before PostgreSQL is accepting connections also return 500 without crashing the API process (§4.5.5).

### 6.3.4 External Systems

The system's relationship to external systems follows one governing principle: the **deployed application integrates with third-party systems only indirectly**, through the shared PostgreSQL database that the out-of-repository weekly pipeline populates. Directly and at runtime, the Flask app talks only to the browser (inbound) and the database (southbound); the browser additionally loads web fonts from a CDN. Spotify and Billboard are reached exclusively by the external pipeline.

#### 6.3.4.1 Third-Party Integration Patterns

Four distinct external-integration patterns appear across the system, only one of which (the CDN font load) is exercised by anything shipped in the deployed runtime other than the database:

- **Client-library / SDK integration (Spotify).** The external pipeline uses **Spotipy** — the Spotify Web API Python client — to fetch Spotify Audio Features per track over HTTPS (`README.md`, `AboutSection.js`). This is a credential-bearing REST-API integration, but its implementation is not in this repository (`spotipy` is absent from `requirements.txt`).
- **Web scraping (Billboard).** The pipeline obtains weekly rankings by scraping the Billboard Hot 100 chart page (there is no official Billboard API involved), an implicit, markup-dependent integration described in `README.md`.
- **Shared-database integration (pipeline ↔ application).** The pipeline and the Flask application communicate **only through PostgreSQL** — the pipeline writes `Tracks` and `YearlyAvg` rows and the application reads them; there is no API, message, or file contract between them in this repository (`api/models.py`, `README.md`). This is the primary pattern that binds external data into the running application.
- **CDN static-asset dependency (Google Fonts).** The delivered SPA loads the `Jost` font family from Google Fonts via a `preconnect` to `fonts.gstatic.com` and a stylesheet link to `fonts.googleapis.com` (`frontend/public/index.html`), a client-side integration performed by the browser, not the backend.

The following sequence shows the external ingestion integration end to end and how it is **decoupled in time** from the application's read path (the two halves never share a request; they meet only at the database).

```mermaid
sequenceDiagram
    autonumber
    participant S as Weekly Scheduler (external)
    participant W as Ingestion Script (external)
    participant BB as Billboard Hot 100
    participant SP as Spotify Web API
    participant DB as PostgreSQL 15
    participant API as api service
    participant UI as Browser SPA

    Note over S,DB: All steps left of PostgreSQL are out of repository (described in README)
    S->>W: trigger weekly run
    W->>BB: HTTP GET chart page
    BB-->>W: HTML rankings
    loop for each track
        W->>SP: Spotipy request for audio features
        SP-->>W: audio-feature values
    end
    W->>DB: write tracks + yearly_avg rows (direct SQL)
    Note over DB,API: Later, independently, at request time
    UI->>API: GET /api/week or /api/analysis
    API->>DB: read-only query
    DB-->>API: rows
    API-->>UI: JSON response
```

*Figure 6.3.4-1: External integration sequence — the out-of-repository weekly pipeline integrates Billboard and Spotify and lands data in PostgreSQL; the deployed API consumes it later through a separate read path.*

#### 6.3.4.2 Legacy System Interfaces

**None.** The repository contains no legacy-system integration surface: there is no SOAP/WSDL client, XML-RPC, FTP/SFTP transfer, EDI, fixed-width/COBOL-style record parsing, or mainframe/message-adapter code anywhere in the tree. The only integration that is non-modern in *style* is the Billboard **web scrape** performed by the external pipeline — a brittle, markup-dependent coupling rather than a versioned API — but that code is out of repository and is not a legacy adapter maintained here.

#### 6.3.4.3 API Gateway Configuration

There is **no dedicated API gateway or reverse-proxy product** in the repository — no NGINX, Traefik, Kong, Envoy, or HAProxy configuration exists (the only `default-gateway` reference is a transitive npm build utility, not an API gateway). Ingress is provided by two lightweight mechanisms depending on environment:

| Environment | Ingress Mechanism | Behavior |
|---|---|---|
| Production / container | Docker Compose port mapping `80 → 5000` | The `api` Flask process is the single public entry, serving SPA and `/api/*` same-origin |
| Development | CRA dev-server proxy `http://localhost:5000` | The dev server forwards `/api/*` calls to Flask (`frontend/package.json`) |

In both cases the Flask application itself performs the "gateway" duties that exist — URL routing (`@app.route`) and static-asset serving (`static_folder='../frontend/build'`, `static_url_path='/'`). There is **no gateway-layer authentication, rate limiting, request transformation, caching, or routing to multiple backends**: a single monolithic process receives every request. `app.run(host='0.0.0.0')` binds all interfaces inside the container, and the host publishes it on port 80.

#### 6.3.4.4 External Service Contracts

The application depends on several external contracts, none of which is formally versioned or validated within the repository. They are summarized below and elaborated afterward.

| Contract | Source / Owner | Consumed As |
|---|---|---|
| Audio Features object | Spotify Web API | Audio-feature columns on `Tracks` (populated by pipeline) |
| Spotipy client API (docs 2.18.0) | Spotipy / Spotify | Library used by the external pipeline to call Spotify |
| Hot 100 chart page | Billboard.com | Scraped HTML (implicit, markup-dependent contract) |
| Database schema (`tracks`, `yearly_avg`) | External pipeline DDL | Read by `api/models.py` via SQLAlchemy |

- **Spotify Audio Features.** The nine audio-feature values (`tempo`, `energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `loudness`) modeled on `Tracks` map to Spotify's audio-features object; the About and Trends views link to the Spotify Web API reference for these definitions. The application relies on the pipeline having already mapped this contract into database columns.
- **Shared database schema.** The most consequential runtime contract is implicit: the ORM models in `api/models.py` (`Tracks`, `YearlyAvg`) must match the columns and types the external pipeline actually writes. Because the repository contains **no migrations, no `create_all`, and no foreign keys**, nothing in this codebase enforces or version-controls that alignment — schema drift in the pipeline would surface only at query time (as empty results or HTTP 500). Two consistency observations follow from the code: `YearlyAvg` omits `loudness` (present on `Tracks`), and `Tracks.__init__` omits the `spotify_id` parameter even though the column and its schema field exist.
- **Response-shape contract (internal).** The SPA depends on the JSON envelopes emitted by `api/routes.py` — `{week, songs, averages, avgTempo}` and `{feature, data}` — which are produced by Marshmallow schemas whose `Meta.fields` define the wire surface. This client↔server contract is coupled by shared deployment rather than by a negotiated version (§6.3.2.5).
- **Contract fragility.** The Billboard scrape depends on the chart page's HTML structure and the Spotify call depends on the Spotipy/Spotify API surface; both are external and unversioned from this repository's perspective, so their stability is outside the control of the deployed application.

### 6.3.5 References

**Repository files examined for this section:**

- `app.py` - Entry point; `app.run(host='0.0.0.0')` (Werkzeug dev server, all interfaces, port 5000)
- `api/__init__.py` - Flask bootstrap; `CORS(app)` permissive; `static_folder='../frontend/build'`, `static_url_path='/'`; hard-coded DSN `postgresql://postgres:postgres@postgres/db`
- `api/routes.py` - The six `GET` routes, `flask.jsonify` JSON responses, the `/api/` 302 redirect, and confirmation of no `try/except`, validation, auth, or versioning
- `api/models.py` - `Tracks` and `YearlyAvg` ORM models and Marshmallow schemas (the shared-database contract; `loudness`/`spotify_id` observations)
- `api/funcs.py` - In-process pandas aggregation (`get_query_week`, `get_weekly_data`, `get_rolling_avg` with `.rolling(5)`)
- `requirements.txt` - Backend dependencies; confirms `gunicorn` pinned-but-unwired and the absence of `spotipy`, HTTP clients, auth, rate-limiting, queue/broker, and OpenAPI libraries
- `docker-compose.yml` - `api` service (`80→5000`, `restart: on-failure`, `depends_on: postgres`) and `postgres` service (`5432`); ingress/gateway configuration
- `Dockerfile` - `python:3.11-slim-buster`; `CMD ["python3","app.py"]` (dev server, not gunicorn)
- `README.md` - Description of the external weekly Billboard scraper + Spotipy enrichment and the `/api/*` endpoint list
- `frontend/package.json` - Dev `proxy` to `http://localhost:5000`; `axios`/`plotly.js`/`react-plotly.js` declared-but-unused
- `frontend/public/index.html` - Google Fonts (`Jost`) `preconnect` + stylesheet (client-side CDN dependency)
- `frontend/src/components/about/AboutSection.js` - In-app API documentation and external hyperlinks (Billboard, Wikipedia, Spotipy 2.18.0, Spotify audio-features reference)
- `frontend/src/components/tracks/TracksSection.js` - Native `fetch('/api/week/…')` client integration and UI error handling
- `frontend/src/components/trends/TrendsSection.js` - Native `fetch('/api/analysis/…')` client integration and Spotify docs link
- `frontend/src/components/trends/LineChart.js` - amCharts line-series legend label "3 Year Rolling Average" (documentation/code inconsistency)

**Repository folders examined:**

- `api/` - The monolithic Flask backend package (bootstrap, routes, models/schemas, helpers)
- `frontend/src/components/` - React feature components (tracks, trends, about, navigation) that consume the API
- `frontend/public/` - Source static assets (SPA shell and PWA manifest) including external font links

**Cross-referenced Technical Specification sections:**

- 3.4 Third-Party Services - Confirms no outbound third-party calls at runtime; external Billboard/Spotify pipeline
- 4.5 Error Handling and Recovery Flows - Error classification (HTTP 500), no retry/fallback, `restart: on-failure`, DB-readiness caveat
- 5.1 High-Level Architecture - Two-tier single-origin topology and the three integration boundaries
- 5.2 Component Details - Existing internal query/aggregation sequence diagrams (avoided duplication)

**External sources referenced by the repository (not independently retrieved):**

- [web] Billboard Hot 100 (`billboard.com/charts/hot-100`) - Chart data source scraped by the external pipeline
- [web] Spotipy documentation (`spotipy.readthedocs.io/en/2.18.0/`) - Spotify Web API client library used by the external pipeline
- [web] Spotify Web API audio-features reference (`developer.spotify.com`) - Audio-feature object contract mapped onto `Tracks`
- [web] Google Fonts (`fonts.googleapis.com` / `fonts.gstatic.com`) - `Jost` web-font delivery for the SPA

## 6.4 Security Architecture

### 6.4.1 Security Architecture Approach and Applicability Assessment

This section documents the security posture of the Billboard Hot 100 application ("Hot Stuff") exactly as it exists in the repository. The findings are drawn from a direct review of the Flask backend (`api/`), the React client (`frontend/src/`), the launcher (`app.py`), and the deployment manifests (`Dockerfile`, `docker-compose.yml`, `.flaskenv`), and are cross-referenced with **Section 4.3 (Validation Rules, Authorization, and Compliance Checkpoints)** and **Section 5.4 (Cross-Cutting Concerns)**. Consistent with the documentation approach established in Section 5.4, security concerns that are **not implemented** are recorded as observed absences with their evidence rather than described aspirationally.

#### 6.4.1.1 Applicability Determination

**Detailed Security Architecture is not applicable for this system.** The application implements no dedicated authentication framework, no authorization system, and no bespoke cryptographic data-protection subsystem. This determination rests on three evidence-based observations:

- **No protected resource or user identity exists.** All six routes in `api/routes.py` are public, unauthenticated `GET` endpoints, and a repository-wide search finds no login, session, token, role, or permission logic anywhere in `api/`, `frontend/src/`, or `app.py` (corroborated by Section 4.3.3, "There are no authorization checkpoints in this system").
- **The data domain is entirely public.** The system serves Billboard Hot 100 chart rankings and Spotify audio-feature aggregates (`README.md`, `api/models.py`). There is no personally identifiable information (PII), no user accounts, no end-user credentials, and no financial, health, or otherwise regulated data.
- **The enterprise concerns this section would normally detail have no subject to act upon.** Identity management, multi-factor authentication, role-based access control, and key management all presuppose a user or a secret to protect; neither is present.

Because the system requires no security beyond standard baseline practices, those baseline practices are enumerated in 6.4.1.2. The remaining subsections (6.4.2 through 6.4.5) then document the observed posture of each required security domain — authentication, authorization, and data protection — as *present-or-absent with evidence*, so that the specification remains a complete and honest reference rather than asserting controls that do not exist.

#### 6.4.1.2 Standard Security Practices Relied Upon

In place of a bespoke security architecture, the codebase relies on the following standard, framework-level practices. Each is a control that is genuinely observable in the repository:

| Standard Practice | Evidence | Security Effect |
|---|---|---|
| Parameterized data access via ORM | SQLAlchemy query API in `api/routes.py` (`filter_by`, `filter`, `with_entities`) | Path parameters are bound as query parameters, not string-concatenated, mitigating SQL injection |
| Output field allow-listing | `TrackSchema` / `YearlyAvgSchema` `Meta.fields` in `api/models.py` | Responses expose only enumerated columns; the internal `YearlyAvg.index` primary key is never serialized |
| Same-origin SPA delivery | `static_folder='../frontend/build'` in `api/__init__.py`; relative `/api/` fetches | The browser client needs no cross-origin or credentialed requests |
| Safe external-link handling | `rel='noopener noreferrer'` on every outbound anchor (`AboutSection.js`, `TrendsSection.js`, `App.js`) | Prevents reverse-tabnabbing and referrer leakage |
| Container network segmentation | Two-service Compose network; DB addressed by service name (`docker-compose.yml`, `api/__init__.py`) | API-to-database traffic stays on the private Compose network |
| Dependency version pinning | Exact `==` pins in `requirements.txt`; `package-lock.json` | Reproducible builds and controlled dependency provenance |
| Secret-file hygiene | `.gitignore` ignores `.env.local*`; `.dockerignore` excludes `/venv`, `/data` | Keeps local environment files and data volumes out of VCS and images |

Several of these practices are **partial or undermined**, and those weaknesses are catalogued in the data-protection subsection (6.4.4) and the control matrices (6.4.5). The most significant are that the PostgreSQL credentials are hard-coded in plaintext and committed to version control (`api/__init__.py`, `docker-compose.yml`), the runtime is the Flask development server rather than the pinned `gunicorn`, the container runs as `root`, and cross-origin policy is fully permissive (`CORS(app)`).

#### 6.4.1.3 Security Domain Applicability Matrix

| Security Domain | Applicability | Basis |
|---|---|---|
| Authentication framework | Not applicable | No user accounts or protected resources |
| Authorization system | Not applicable | All resources are public and read-only |
| Data protection (cryptography) | Minimal / standard only | Public data; the only sensitive artifact is an infrastructure credential |
| Secure communication (TLS) | Deferred to environment | No in-repo TLS; would require an external reverse proxy (absent) |
| Compliance controls | None triggered | No PII or regulated data in the domain |
| Audit logging | Not implemented | No logging configuration or statements in `api/` |

#### 6.4.1.4 Security Zones and Trust Boundaries

Although the application enforces no security controls itself, its Docker Compose deployment does establish a small set of implicit **trust zones**. Figure 6.4.1-1 maps these zones and the boundaries between them. The most notable boundary observation is that the `postgres` service publishes port `5432` to the Docker host (`docker-compose.yml`), so the data tier is reachable directly from the host network in addition to being reachable over the private Compose network — widening the data-zone boundary beyond what the application requires.

**Figure 6.4.1-1 — Security Zone and Trust-Boundary Diagram**

```mermaid
flowchart TB
    subgraph Z0["Zone 0 — Untrusted Public Network"]
        Client["Any HTTP client<br/>browser / curl / automated bot<br/>(no credentials required)"]
    end
    subgraph Z1["Zone 1 — Docker Host Published Ports"]
        Ingress["Host port 80"]
        DBPort["Host port 5432<br/>(PostgreSQL published)"]
    end
    subgraph Z2["Zone 2 — Application Container (api service)"]
        Flask["Flask app — python3 app.py<br/>bind 0.0.0.0:5000 as root<br/>CORS all origins, no TLS"]
        SPA["Compiled React SPA<br/>served from static_folder"]
    end
    subgraph Z3["Zone 3 — Data Container (postgres service)"]
        PG[("PostgreSQL 15<br/>database 'db'<br/>user/pw postgres/postgres")]
    end
    subgraph Z4["Zone 4 — External Ingestion Pipeline (out of repository)"]
        Pipe["Weekly script<br/>Billboard scrape + Spotipy"]
    end
    Client -->|"HTTP/JSON"| Ingress
    Client -.->|"exposed DB port"| DBPort
    Ingress --> Flask
    Flask --> SPA
    Flask -->|"SQLAlchemy / psycopg2<br/>on Compose network"| PG
    DBPort --> PG
    Pipe -->|"writes Tracks / YearlyAvg rows"| PG
```

| Zone | Contains | Trust-Boundary Note |
|---|---|---|
| Zone 0 — Public network | Any HTTP client | Fully untrusted; no authentication required to enter |
| Zone 1 — Host ports | `:80` (API), `:5432` (DB) | Publishing `5432` exposes the data tier directly to the host |
| Zone 2 — `api` container | Flask app + compiled SPA | Runs as `root`, development server, permissive CORS, no TLS |
| Zone 3 — `postgres` container | PostgreSQL 15 | Reachable via the Compose network and via published `5432` |
| Zone 4 — External pipeline | Out-of-repo weekly script | Not in this repository; writes into Zone 3 |


### 6.4.2 Authentication Framework

The application has **no authentication framework**. No identity provider, credential store, session, token, or password logic exists in `api/`, `frontend/src/`, or `app.py`; a repository-wide search for `login`, `authenticat`, `session`, `token`, `jwt`, `oauth`, and related markers returns no matches. Every request is processed as an anonymous principal. Each authentication sub-concern is documented below as an observed absence with its evidence.

#### 6.4.2.1 Identity Management

There is no identity management. `api/models.py` defines exactly two ORM entities — `Tracks` and `YearlyAvg` — both of which model public music data; there is no `User`, `Account`, or credential entity, and no identity-provider or directory integration in `requirements.txt`. The only "identity" in the system is the PostgreSQL service account (`postgres`), which authenticates the *application* to the *database* over the DSN in `api/__init__.py`; it is an infrastructure credential, not an end-user identity mechanism.

#### 6.4.2.2 Multi-Factor Authentication

Multi-factor authentication is **not applicable**. MFA is a second factor layered on a primary authentication step, and no primary authentication step exists. There is no MFA, one-time-password, TOTP, WebAuthn, or SMS/email verification library among the dependencies and no such flow in the codebase.

#### 6.4.2.3 Session Management

There is no session management. The backend is stateless: `api/__init__.py` configures only `SQLALCHEMY_DATABASE_URI` and `SQLALCHEMY_TRACK_MODIFICATIONS`, and notably **does not set `SECRET_KEY`**, so Flask's signed-session cookie facility is neither configured nor used. No route sets, reads, or clears a cookie. On the client, the React application holds only ephemeral in-memory UI state (`activeTab`, fetched chart `data`) in `App.js` and the section components — this state is not a security session and is discarded on reload. (See Section 4.4 for the stateless, per-request session-scope handling of the SQLAlchemy connection.)

#### 6.4.2.4 Token Handling

There is no token handling. The system issues, accepts, and verifies no tokens of any kind (no JWT, OAuth access/refresh tokens, or API keys). The two client fetch call sites — `TracksSection.js` and `TrendsSection.js` — invoke `fetch(`/api/${endpoint}/${param}`)` with no options argument, so requests carry no `Authorization` header and no bearer credential. The `itsdangerous` package (a Flask transitive dependency capable of signing tokens) is present in `requirements.txt` but is not used for any signing purpose in the application.

#### 6.4.2.5 Password Policies

Password policies are **not applicable** to end users, because there are no user passwords. The only password in the project is the static database service password (`postgres`), hard-coded in the DSN (`api/__init__.py`) and in `docker-compose.yml`. It has no complexity, rotation, expiry, lockout, or history policy — it is a fixed development credential committed to version control (this is analysed as a data-protection weakness in 6.4.4.2).

#### 6.4.2.6 Authentication Control Summary and Flow

| Authentication Control | Status | Evidence |
|---|---|---|
| Identity management / user store | None | No user entity in `api/models.py`; no IdP dependency |
| Multi-factor authentication | Not applicable | No primary auth factor exists |
| Session management | None | No `SECRET_KEY`; no session cookie in any route |
| Token handling (JWT/OAuth/API key) | None | `fetch` sends no `Authorization` header; no token libraries wired |
| End-user password policy | Not applicable | No user passwords; only a static DB service credential |

Figure 6.4.2-1 traces the request lifecycle through the authentication steps a conventional framework would perform, showing that each step is absent so the request always reaches the handler as an anonymous principal.

**Figure 6.4.2-1 — Authentication Flow (Anonymous Pass-Through)**

```mermaid
flowchart TD
    Start(["HTTP request arrives at Flask app"])
    Start --> B{"Credential collection?<br/>login form / Authorization header"}
    B -->|"Absent in codebase"| C{"Identity verification?<br/>password check / token verify"}
    C -->|"Absent in codebase"| D{"Session or token issuance?<br/>SECRET_KEY / cookie / JWT"}
    D -->|"Absent in codebase"| E["Request proceeds as<br/>ANONYMOUS principal"]
    E --> F["Route handler executes<br/>(api/routes.py)"]
    F --> G(["Public response returned to any caller"])
```


### 6.4.3 Authorization System

The application has **no authorization system**. Because there is no authenticated principal (6.4.2), there is nothing to authorize; every one of the six routes in `api/routes.py` grants full read access to any caller. Section 4.3.3 reaches the same conclusion ("There are no authorization checkpoints in this system"). Each authorization sub-concern is documented below with evidence.

#### 6.4.3.1 Role-Based Access Control

There is no role-based access control. No role or group concept exists in the data model or the code: `api/models.py` contains no role entity, and there are no role assignments, role checks, or `@roles_required`-style decorators. All callers are implicitly equivalent and unprivileged-yet-fully-permitted.

#### 6.4.3.2 Permission Management

There is no permission-management layer. No permission, scope, grant, or capability is defined or evaluated anywhere in `api/`. The system therefore has a single, uniform, implicit permission — "read everything" — that cannot be granted, revoked, or scoped.

#### 6.4.3.3 Resource Authorization

Every resource is world-readable, and no per-resource authorization is performed. The route handlers query and return data based solely on the path parameter (a `spotify_id`, `week`, `artist`, or `feature`) with no ownership, tenancy, or visibility check. The nearest thing to resource authorization is at the **database** layer: the API connects with the single `postgres` account (DSN in `api/__init__.py`), so the database — not the application — governs which tables the connection may read. This is a coarse infrastructure control, not application-level resource authorization.

#### 6.4.3.4 Policy Enforcement Points

There are **no application policy enforcement points (PEPs)**. Examining every layer a request traverses:

- **Ingress layer** (`docker-compose.yml` maps host `80` to container `5000`): performs port forwarding only — no policy decision.
- **Framework layer** (`api/__init__.py`): registers `CORS(app)` with no restrictions. Cross-Origin Resource Sharing is a *browser-advisory* control that a compliant browser honours; it is not a server-side authorization gate, and here it is fully permissive (allows all origins).
- **Route layer** (`api/routes.py`): no route carries an authentication or authorization decorator, and there is no `before_request` hook or `@app.errorhandler` (confirmed by search).
- **Data layer** (SQLAlchemy → PostgreSQL): the connection is authorized by the static DB credential, which is not tied to any end-user request context.

#### 6.4.3.5 Audit Logging

There is no audit logging. Consistent with Section 5.4.2, `api/` contains no `logging` configuration, no logger calls, and no audit trail of access or actions; searches for `logging`, `logger`, `audit`, and `app.logger` return no matches. The only runtime output is the Werkzeug development server's incidental per-request line written to stderr (viewable via `docker logs`), which is not a durable, structured, or security-oriented audit record.

#### 6.4.3.6 Authorization Control Summary and Flow

| Authorization Control | Status | Evidence |
|---|---|---|
| Role-based access control | None | No role entity or role checks in `api/` |
| Permission management | None | No permission/scope/grant logic anywhere |
| Resource authorization | None (app) / DB-credential only | Handlers apply no ownership/visibility check (`api/routes.py`) |
| Policy enforcement points | None | No decorators, `before_request`, or error handlers; CORS is advisory |
| Audit logging | None | No logging/audit statements in `api/` (Section 5.4.2) |

Figure 6.4.3-1 walks the request through each layer that could host a policy enforcement point and shows that every PEP is absent, so full read access is granted unconditionally. This complements the simpler access-summary diagram in Section 4.3.3 by focusing on the per-layer enforcement analysis.

**Figure 6.4.3-1 — Authorization Flow: Policy Enforcement Point Analysis**

```mermaid
flowchart LR
    Req(["Anonymous request<br/>(no principal)"])
    subgraph L1["Ingress layer"]
        PEP1{"Enforcement point?"}
    end
    subgraph L2["Framework layer (Flask + CORS)"]
        PEP2{"Enforcement point?"}
    end
    subgraph L3["Route layer (api/routes.py)"]
        PEP3{"Enforcement point?"}
    end
    subgraph L4["Data layer (SQLAlchemy to PostgreSQL)"]
        PEP4{"Enforcement point?"}
    end
    Req --> PEP1
    PEP1 -->|"None: port forwarding only"| PEP2
    PEP2 -->|"None: CORS advisory, allows all origins"| PEP3
    PEP3 -->|"None: no guard, decorator, or hook"| PEP4
    PEP4 -->|"DB credential authorizes app, not end user"| Grant(["Full read access granted"])
```


### 6.4.4 Data Protection

Data protection in this system is scoped by its data classification: everything the application persists and serves is **public** music-industry reference data (chart rankings and Spotify audio-feature aggregates per `api/models.py` and `README.md`), containing no PII, credentials, or regulated data. Consequently the application applies no cryptographic protection to the *data it serves*. The one sensitive artifact in the project is an *infrastructure* credential (the database password), and its handling is the principal data-protection weakness, documented below.

#### 6.4.4.1 Encryption Standards

No application-level encryption is defined, for data either at rest or in transit:

- **At rest:** the `postgres:15` container uses default storage with no `pgcrypto`, column encryption, or transparent-disk-encryption configuration in `docker-compose.yml`; no `cryptography`, `bcrypt`, or `argon2` library appears in `requirements.txt`.
- **In transit:** `app.py` runs `app.run(host='0.0.0.0')` — the Werkzeug development server over plain HTTP with no certificate; the internal `api`→`postgres` connection uses the default (non-TLS) PostgreSQL wire protocol on the Compose network.

Because the served data is public, confidentiality of *content* is not a stated requirement; the absence of encryption is therefore recorded as an observed characteristic rather than a breach of a defined control.

#### 6.4.4.2 Key Management

There is no key-management system — no keys, key store, KMS, HSM, or secret manager, and no Flask `SECRET_KEY`. Secret material is limited to the PostgreSQL credential `postgres`/`postgres`, which is **hard-coded in plaintext** in two committed locations:

```python
# api/__init__.py

dbURL = f'postgresql://postgres:postgres@postgres/db'
```

```yaml
# docker-compose.yml

POSTGRES_USER: postgres
POSTGRES_PASSWORD: postgres
```

Although `python-dotenv` is a declared dependency and `.gitignore` excludes `.env.local*`, the DSN does **not** read from the environment (`import os` in `api/__init__.py` is unused), so the credential cannot be overridden without editing source. This is the system's most material data-protection finding and is reflected in the control matrices (6.4.5).

#### 6.4.4.3 Data Masking Rules

There are no data-masking or redaction rules, and none are required given the public data domain. The closest mechanism to output minimization is **Marshmallow field allow-listing**: `TrackSchema` and `YearlyAvgSchema` in `api/models.py` declare explicit `Meta.fields` tuples, so serialized responses include only the enumerated columns. A concrete effect is that the internal `YearlyAvg.index` primary key is omitted from `/api/analysis` responses. This is schema-driven field selection rather than masking of sensitive values, but it is the observed control that shapes what leaves the API.

#### 6.4.4.4 Secure Communication

Secure communication is not implemented within the repository and is effectively deferred to the deployment environment:

- **Client ↔ API:** the SPA issues same-origin relative `fetch` calls (`/api/...`), so no cross-origin credentialed traffic occurs; however, the exposed transport is plain HTTP (host `:80` → container `:5000`) with no TLS termination in the repo. As Section 5.4.4 notes, TLS "would require an external proxy" that is absent.
- **API ↔ Database:** unencrypted PostgreSQL protocol over the Compose network.
- **Browser ↔ third parties:** the delivered `index.html` loads the Google Fonts "Jost" family from `fonts.googleapis.com`/`fonts.gstatic.com` over HTTPS, but **without Subresource Integrity** (no `integrity=` attribute on that or the local `/static/js` script tags).
- **Outbound links:** every external hyperlink uses `target='_blank'` with `rel='noopener noreferrer'` (`AboutSection.js`, `TrendsSection.js`, `App.js`), which is the one deliberate secure-communication hardening present on the client.

#### 6.4.4.5 Compliance Controls

No compliance controls are defined in the repository, and the data domain triggers none. There is no consent capture, data-retention enforcement, right-to-erasure handling, or geographic restriction, consistent with Section 4.3.4 ("No regulatory-compliance controls are defined in the repository"). Regulatory obligations that hinge on personal or regulated data (GDPR/CCPA, PCI-DSS, HIPAA) are not engaged because no such data is collected or stored. The applicable considerations are third-party data-usage terms (Billboard and Spotify), which are addressed as compliance *requirements* in 6.4.5.3.

#### 6.4.4.6 Data Protection Summary

| Data-Protection Control | Status | Evidence |
|---|---|---|
| Encryption at rest | None | Default `postgres:15` storage; no crypto library |
| Encryption in transit (TLS) | None in repo | Plain-HTTP dev server; non-TLS DB connection |
| Key / secret management | None (hard-coded) | Plaintext DSN in `api/__init__.py`; creds in `docker-compose.yml` |
| Data masking / redaction | Not required; field allow-list only | `Meta.fields` in `TrackSchema` / `YearlyAvgSchema` |
| Secure outbound linking | Present | `rel='noopener noreferrer'` on all external anchors |


### 6.4.5 Security Control Matrices and Compliance Requirements

This subsection consolidates the preceding findings into control and threat matrices and documents the compliance requirements that apply to the system. All assessments are grounded strictly in observed repository evidence; qualitative exposure ratings describe the *likelihood and impact given the public, read-only data domain* and are not derived from any formal scoring standard.

#### 6.4.5.1 Consolidated Security Control Matrix

| Control Category | Status | Evidence / Note |
|---|---|---|
| Authentication | Not implemented | No login/session/token logic (`api/`, `frontend/src/`) |
| Authorization | Not implemented | No roles, permissions, or route guards (`api/routes.py`) |
| Input validation (server) | Not implemented | `strptime`/`getattr` only; validation is client-side (Section 4.3.2) |
| SQL-injection defense | Present | Parameterized SQLAlchemy ORM queries (`api/routes.py`) |
| Output exposure control | Present | Marshmallow `Meta.fields` allow-list (`api/models.py`) |
| Cross-origin policy | Permissive | `CORS(app)` allows all origins (`api/__init__.py`) |
| Transport encryption (TLS) | Not implemented | Plain-HTTP dev server; no in-repo TLS (`app.py`) |
| Secrets management | Weak (hard-coded) | Plaintext DB creds in `api/__init__.py`, `docker-compose.yml` |
| Security response headers | Not implemented | No CSP/HSTS/X-Frame-Options; no `after_request` |
| Subresource Integrity | Not implemented | No `integrity=` on script/font links (`index.html`) |
| Rate limiting | Not implemented | No limiter dependency or middleware |
| Audit / access logging | Not implemented | No logging in `api/`; incidental stderr only (Section 5.4.2) |
| Safe external linking | Present | `rel='noopener noreferrer'` on all outbound anchors |
| Container privilege | Weak (root) | No non-root `USER` in `Dockerfile` |

#### 6.4.5.2 Threat Exposure and Mitigating Factors

| Threat / Concern | Exposure | Mitigating Factor or Observation |
|---|---|---|
| SQL injection | Low | All queries ORM-bound; params never string-concatenated (`api/routes.py`) |
| Cross-site scripting (XSS) | Low | React JSX auto-escapes rendered values; no `dangerouslySetInnerHTML`/`innerHTML`/`eval` in `frontend/src` |
| Credential disclosure | High | Plaintext `postgres`/`postgres` committed to VCS; no env override |
| Direct database access | Elevated | `postgres` port `5432` published to host (`docker-compose.yml`) |
| Cross-origin data read | Low | `CORS(*)` permits it, but responses carry only public data and no auth cookies |
| Denial of service | Elevated | No rate limiting, no pagination/limits, single dev-server process (Section 5.4.5) |
| Unvalidated input to 500 | Moderate | Bad `date`/`feature` raises unhandled exception → HTTP 500 (Section 4.5); bounded by ORM, no data leak |
| Malicious dependency (supply chain) | Low–Moderate | Exact version pinning (`requirements.txt`, `package-lock.json`); no SRI for CDN font |

#### 6.4.5.3 Compliance Requirements

Because the system stores and serves no personal or regulated data, the major data-privacy and payment regimes impose **no active obligations** on it. The requirements that remain are third-party data-usage terms inherent to the data sources. This subsection documents applicability so the determination is explicit and auditable.

| Compliance Requirement | Applicability | Basis |
|---|---|---|
| GDPR / CCPA (personal data) | Not triggered | No PII, accounts, or tracking collected (Section 4.3.4) |
| PCI-DSS (payment data) | Not triggered | No payment or cardholder data anywhere |
| HIPAA (health data) | Not triggered | No health information in the domain |
| Audit-trail retention | Not applicable | No regulated events; no audit logging implemented |
| Billboard data-usage terms | Applicable (data source) | Chart data scraped by the external pipeline (`README.md`) |
| Spotify Developer terms | Applicable (data source) | Audio features fetched via Spotipy by the external pipeline (`README.md`) |

Two clarifications follow from the evidence. First, the Billboard and Spotify terms bind the **external, out-of-repository ingestion pipeline** that acquires the data, not the read-only Flask API in this repository, which merely serves rows already present in PostgreSQL. Second, should the system's scope ever expand to collect user data, the absence of authentication, authorization, transport encryption, audit logging, and secrets management (documented throughout Section 6.4) would each become a compliance gap requiring remediation before such data could be handled.


### 6.4.6 References

The following repository artifacts and previously written specification sections were examined as evidence for this section.

**Backend source files**

- `app.py` - Established the runtime entry point `app.run(host='0.0.0.0')` (Werkzeug development server bound to all interfaces, plain HTTP, not `gunicorn`).
- `api/__init__.py` - Established the permissive `CORS(app)`, the hard-coded plaintext DSN `postgresql://postgres:postgres@postgres/db`, the absence of `SECRET_KEY`, the unused `import os`, and same-origin static SPA serving (`static_folder='../frontend/build'`).
- `api/routes.py` - Established the six public, unauthenticated `GET` routes, the ORM-parameterized queries, the `getattr(YearlyAvg, feature)` attribute lookup, and the absence of auth decorators, `before_request` hooks, and error handlers.
- `api/models.py` - Established the public data model (`Tracks`, `YearlyAvg` — no user/credential entity) and the Marshmallow `Meta.fields` output allow-list.
- `api/funcs.py` - Established the `strptime`-based week parsing that underlies server-side input handling behavior.

**Frontend source files**

- `frontend/src/App.js` - Established ephemeral in-memory UI state and `rel='noopener noreferrer'` on outbound links.
- `frontend/src/components/tracks/TracksSection.js` - Established the header-less, credential-less `fetch` call site and escaped JSX interpolation of rendered data.
- `frontend/src/components/trends/TrendsSection.js` - Established the second `fetch` call site and a `rel='noopener noreferrer'` external documentation link.
- `frontend/src/components/about/AboutSection.js` - Established `target='_blank'` + `rel='noopener noreferrer'` on all external hyperlinks.
- `frontend/public/index.html` and `frontend/build/index.html` - Established the absence of CSP/security meta tags and Subresource Integrity, and the HTTPS Google Fonts dependency.

**Deployment and configuration files**

- `docker-compose.yml` - Established plaintext database credentials, the published `5432` DB port, the `80:5000` mapping, the repo bind-mount, and the two-service network topology used for the security-zone diagram.
- `Dockerfile` - Established the development-server `CMD` and the absence of a non-root `USER`.
- `requirements.txt` - Established the dependency inventory (no authentication/cryptography libraries; `itsdangerous` and `python-dotenv` present but unused for security; `gunicorn` pinned but not wired).
- `.flaskenv`, `.gitignore`, `.dockerignore` - Established `FLASK_ENV=development`, `.env.local*` exclusion, and volume/dependency exclusion hygiene.
- `README.md` - Established the public data domain (Billboard Hot 100 + Spotify audio features) and the external, out-of-repository weekly ingestion pipeline.

**Folders inspected**

- `api/` - The complete Flask backend package, searched exhaustively for authentication, authorization, session, token, logging, and header logic.
- `frontend/src/` - The React client source, searched for auth/token handling and raw-HTML injection sinks.

**Cross-referenced specification sections**

- **Section 4.3 Validation Rules, Authorization, and Compliance Checkpoints** - Corroborated the no-authorization-checkpoints and no-compliance-controls findings and the client-side-only validation posture.
- **Section 4.4 State Management and Transaction Boundaries** - Corroborated the stateless, per-request session scope.
- **Section 4.5 Error Handling and Recovery Flows** - Corroborated the unhandled-exception-to-HTTP-500 behavior.
- **Section 5.4 Cross-Cutting Concerns** - Corroborated the no-authN/authZ-framework, no-logging, and TLS-not-in-repo findings and supplied consistent terminology.

No external web sources were consulted for this section; all findings are grounded in the repository and the cross-referenced specification sections above.


## 6.5 Monitoring and Observability

### 6.5.1 Monitoring Approach and Applicability

**Detailed Monitoring Architecture is not applicable for this system.** The application is a monolithic, read-only Billboard Hot 100 showcase — a single Flask process that serves a React single-page application over a single PostgreSQL 15 database (Section 6.1.1) — operated as a single-author portfolio project against a frozen historical dataset (Section 1.2.1). It contains no metrics collection, no log aggregation, no distributed tracing, no alert management, no dashboards, and no health-check endpoints. This is not a gap in the present analysis; it is a property of the codebase already established at the cross-cutting level in Section 5.4.1 (Monitoring and Observability) and Section 5.4.2 (Logging and Tracing), and independently corroborated by Section 1.2.3.1, which records that there is no monitoring or analytics instrumentation anywhere in the codebase.

Accordingly — and consistent with the evidence-based, "document observed absences rather than aspirations" convention used throughout Chapter 5 and Section 6.1 — this section (a) states which basic operational-visibility practices the system actually relies on, (b) documents each conventional monitoring pillar as an observed presence or absence with its code evidence, and (c) does **not** fabricate metrics pipelines, service-level agreements, alert thresholds, or dashboards that the repository does not contain.

**Basic monitoring practices followed instead.** The system's entire operational-visibility surface consists of five basic, largely manual mechanisms:

1. **Container-level liveness and auto-recovery.** The `api` service is declared with `restart: on-failure` in `docker-compose.yml`, so the Docker Engine restarts the container if its process exits with a non-zero status. This is the only automated recovery mechanism (Section 5.4.6, Section 6.1.4.1); it reacts to process crashes only, not to per-request HTTP 500s, which do not exit the process.
2. **Standard-stream (stdout/stderr) logging.** The Werkzeug development server prints one request line per HTTP call, and the `postgres:15` container emits its own server log; both are captured by the Docker Engine and constitute the sole runtime log source (Section 5.4.2).
3. **On-demand log inspection.** Operators read those captured streams manually with `docker compose logs` / `docker logs`; there is no log shipping, indexing, or retention beyond Docker's container defaults.
4. **HTTP status codes as implicit health signals.** Each route returns a status code a caller can interpret as a coarse health signal; the React client already inspects `response.status > 299` to switch its views into an error state (`frontend/src/components/tracks/TracksSection.js`, `frontend/src/components/trends/TrendsSection.js`).
5. **Client-side error and loading UI states.** The SPA surfaces failures to the end user (a `. . .` loading indicator and an `<h1 className='error'>` message) but does not report them to any backend or telemetry service (Section 5.4.3).

The table below summarizes the status of each conventional monitoring pillar; Sections 6.5.2 through 6.5.4 expand each one with its evidence.

| Monitoring Pillar | Status in Repository | Primary Evidence |
|---|---|---|
| Metrics collection / APM | Not implemented | No client library in `requirements.txt` or `frontend/package.json` |
| Log aggregation / shipping | Not implemented | No log driver or collector; container-default stderr only |
| Distributed tracing | Not implemented | No tracing library; single-process synchronous flow |
| Alert management / routing | Not implemented | No alerting config; only `restart: on-failure` (`docker-compose.yml`) |
| Dashboards | Not implemented | No Grafana/Kibana/dashboard artifact anywhere in the tree |
| Health / readiness endpoint | Not implemented | No such route among the six in `api/routes.py` |
| Client performance telemetry | Declared but unused | `web-vitals` in `package.json`; no `reportWebVitals` in `frontend/src/` |
| Container liveness / auto-recovery | Present (basic) | `restart: on-failure` on `api` (`docker-compose.yml`) |
| Standard-stream logging | Incidental only | Werkzeug + PostgreSQL logs to stderr, via `docker logs` (Section 5.4.2) |

Figure 6.5.1-1 depicts the system's actual observability data flow: the incidental log streams that exist, the single automated recovery loop, and the conventional pillars absent from the repository.

```mermaid
flowchart TD
    subgraph Client["Web Browser - React SPA"]
        UI["Tracks / Trends / About views"]
        ErrState["Client error/loading state<br/>HTTP status over 299 shows error"]
        WV["web-vitals declared,<br/>reportWebVitals NOT wired"]
    end

    subgraph ApiC["api container - Flask dev server (host 80 to 5000)"]
        Routes["Six GET routes<br/>no logging / metrics / health endpoint"]
        WZ["Werkzeug dev server<br/>one request line per call to stderr"]
    end

    subgraph DbC["postgres container - postgres:15"]
        PG[("PostgreSQL db")]
        PGLog["server log to stderr"]
    end

    subgraph Engine["Docker Engine"]
        Capture["Captures container stdout/stderr"]
        Restart["restart: on-failure policy"]
    end

    Operator["Operator - manual / on demand<br/>docker compose logs, docker ps"]

    subgraph Absent["Conventional monitoring pillars - NOT present in repository"]
        Metrics["Metrics / APM"]
        Aggr["Log aggregation"]
        Trace["Distributed tracing"]
        Alerting["Alert management"]
        Dash["Dashboards"]
        Health["Health / readiness endpoint"]
    end

    UI --> ErrState
    UI -->|"fetch /api/*"| Routes
    Routes --> WZ
    Routes -->|"SQLAlchemy / psycopg2"| PG
    PG --> PGLog
    WZ --> Capture
    PGLog --> Capture
    Capture --> Operator
    Restart -.->|"process exit only"| Routes
```

**Figure 6.5.1-1: Monitoring Architecture — Observable Telemetry Flow and Absent Pillars.** Solid arrows are the runtime request and incidental-log paths that exist today; the dashed arrow is the sole automated recovery loop (`restart: on-failure`, process-exit only); the "Absent" group enumerates the conventional monitoring capabilities the repository does not contain.

### 6.5.2 Monitoring Infrastructure

This subsection examines the five monitoring-infrastructure pillars enumerated by the specification — metrics collection, log aggregation, distributed tracing, alert management, and dashboard design — against the repository. None is present as dedicated infrastructure, so each is documented as an observed absence together with the architectural reason it is absent and the basic mechanism (if any) that stands in for it.

#### 6.5.2.1 Metrics Collection

There is **no metrics collection**. `requirements.txt` contains no metrics or APM client (no `prometheus-client`, `statsd`, OpenTelemetry, `datadog`, or `newrelic`), and `frontend/package.json` contains none either; there is no counter, gauge, histogram, or timer instrumented anywhere in `api/`, and no `/metrics` (or equivalent) scrape endpoint among the six routes in `api/routes.py`. Because the container runs the Flask development server (`CMD ["python3","app.py"]`, Section 3.6.3) with no exporter, there is no metrics source for an external collector to scrape — the same gap Section 6.1.3.2 records when noting there is no metrics source on which auto-scaling could trigger.

The only quantitative signals that exist at all are those a human could derive **by manually parsing** the incidental Werkzeug request lines (Section 5.4.2); nothing is captured, stored, or aggregated automatically. The table below defines those candidate metrics and their (manual-only) provenance.

| Candidate Metric | Nearest Available Source | Automated Collection? |
|---|---|---|
| Request count / throughput | Werkzeug request lines on stderr | No — manual log reading only |
| Per-route request distribution | Werkzeug request lines on stderr | No — manual log reading only |
| HTTP status distribution (2xx/3xx/5xx) | Werkzeug request lines on stderr | No — manual log reading only |
| Request latency | Not emitted by the dev server by default | No — not captured |
| Database query timing | No SQLAlchemy echo/timing configured | No — not captured |

#### 6.5.2.2 Log Aggregation

There is **no log aggregation**. The system performs no structured application logging — `api/__init__.py` configures no `logging` handler and no route in `api/routes.py` emits a log statement (Section 5.4.2) — so the only runtime output is *incidental*: the Werkzeug development server prints one request line per HTTP call, and the `postgres:15` container writes its own server log. Both go to container stderr and are captured by the Docker Engine's default logging driver; `docker-compose.yml` declares no `logging:` driver override, so no forwarder or collector (Fluentd, Filebeat, Vector, Logstash) and no external sink is configured. Retention and rotation are therefore whatever Docker's defaults provide. "Aggregation" across the two services is manual — `docker compose logs` interleaves the `api` and `postgres` streams into one console view. (The `*-debug.log` patterns in `.gitignore` refer to npm/yarn *build-time* logs, not runtime application logs; no runtime log file is produced.)

| Log Source | Format | Aggregation / Shipping |
|---|---|---|
| Werkzeug dev server (`api`) | Plain request line per call | None — container stderr only |
| PostgreSQL (`postgres:15`) | Default `postgres` server log | None — container stderr only |
| Application (structured) | Not produced | Not applicable — no logging configured |

#### 6.5.2.3 Distributed Tracing

There is **no distributed tracing**. No tracing SDK (OpenTelemetry, Jaeger, Zipkin) appears in either dependency manifest, and there is no trace-context, span, or correlation-ID propagation in `api/`. Architecturally there is also nothing to trace *across*: the system is a single synchronous, in-process monolith calling one database (Section 6.1.2.2), so a browser `fetch` maps to one Flask route invoking one SQLAlchemy query and returning a response — there is no second service, message queue, or asynchronous hop that a trace would span. As Section 5.4.2 records, there is not even a request identifier tying a browser action to its server-side handling, so end-to-end correlation is limited to reading a single Werkzeug request line by hand.

#### 6.5.2.4 Alert Management

There is **no alert management**. The repository defines no alerting rules, no Alertmanager/PagerDuty/Opsgenie integration, and no email/Slack/webhook notifier, and there is no threshold configuration anywhere. The only automated signal-to-action mechanism is the Docker `restart: on-failure` policy on the `api` service (`docker-compose.yml`) — but that is a *recovery* action, not an alert: it emits no notification to any human and fires only on a non-zero process exit. No alert is raised on per-request HTTP 500s (which do not exit the process — Section 6.1.4.1), on database unavailability during warm-up, or on data staleness. Consequently, incident *detection* is entirely manual and reactive. The end-to-end alert/response flow, and an alert-threshold matrix that records the (absence of) configured thresholds, are provided in Section 6.5.4.1.

#### 6.5.2.5 Dashboard Design

There is **no operational dashboard**. The repository contains no Grafana, Kibana, or Datadog dashboard artifact, and — following from Section 6.5.2.1 — there is no metrics backend that could power one. The de-facto "operator console" is the terminal: `docker compose ps` reports container state (`Up`, `Restarting`, `Exited`), and `docker compose logs -f` streams the interleaved Werkzeug and PostgreSQL output described in Section 6.5.2.2. The only *graphical* surface in the system is the React SPA itself, but it visualizes chart **data** — the amCharts radar of weekly feature averages and the amCharts line chart of annual/rolling averages (Section 1.2.2) — not operational telemetry. Figure 6.5.2-1 depicts this de-facto inspection layout and distinguishes it from the absent operational dashboard.

```mermaid
flowchart TB
    Operator["Operator"]
    EndUser["End user"]

    subgraph Terminal["De-facto Operator Console - terminal, manual"]
        PsPane["Container status pane<br/>docker compose ps"]
        LogPane["Interleaved log pane<br/>docker compose logs -f"]
    end

    subgraph AppUI["Application UI - data visualization, NOT operational telemetry"]
        Radar["Tracks view: amCharts radar<br/>weekly feature averages"]
        Line["Trends view: amCharts line<br/>annual + rolling average"]
    end

    NoDash["Absent: no metrics/operational dashboard<br/>no Grafana/Kibana, no metrics backend"]

    Operator --> PsPane
    Operator --> LogPane
    EndUser --> Radar
    EndUser --> Line
    Operator -.->|"would require a metrics backend"| NoDash
```

**Figure 6.5.2-1: Dashboard Layout — De-facto Operator Inspection Surface vs. Application Data Visualization.** The two terminal panes are the only operational "dashboard" (manual, on demand); the amCharts views are end-user data visualizations, not telemetry; the dashed node marks the operational dashboard the repository does not contain.

### 6.5.3 Observability Patterns

This subsection maps the five requested observability patterns — health checks, performance metrics, business metrics, SLA monitoring, and capacity tracking — onto the observed system. As with the infrastructure pillars, none is formally implemented; each is documented with the de-facto signal that exists (if any) and its evidence.

#### 6.5.3.1 Health Checks

There is **no health-check or readiness endpoint**. None of the six routes in `api/routes.py` is a health/readiness probe (Section 5.4.1), the `Dockerfile` declares no `HEALTHCHECK` instruction, and `docker-compose.yml` declares no `healthcheck:` block for either service; `depends_on: postgres` orders container *start* but does not gate on the database being ready to accept connections (Section 6.1.4.1). What an operator *can* do manually — grounded in the actual route behavior — is treat existing endpoints as coarse probes: `GET /` returns `index.html` purely from static files (`app.send_static_file`) and therefore succeeds even when the database is down, making it a shallow liveness signal, whereas `GET /api/week/<week>` exercises the full route-to-database path and only returns data when PostgreSQL is reachable and populated, making it a deeper (still manual) readiness signal.

| Manual Probe | What It Exercises | Health Signal |
|---|---|---|
| `GET /` | Static file serving only (no DB) | Shallow liveness — returns 200 even if DB is down |
| `GET /api/week/<week>` | Route + `get_query_week` + DB query + serialize | Deep readiness — succeeds only if DB reachable/populated |
| `docker compose ps` | Container/process state | `Up` / `Restarting` / `Exited` |

#### 6.5.3.2 Performance Metrics

No performance metrics are **collected** (Section 6.5.2.1) and no latency or throughput targets are **defined** (Section 5.4.5), so there is no measured performance signal. What can be stated are the architectural performance *characteristics* observed in the code (Section 5.4.5, Section 6.1.3.3); these bound behavior but are not instrumented or tracked.

| Performance Characteristic | Effect | Evidence |
|---|---|---|
| Precomputed `YearlyAvg` aggregate | Reduces analysis-read cost (no full `Tracks` scan) | `api/models.py`, `api/routes.py` |
| No application caching | Full DB query + pandas recompute per request | Section 5.4.5, Section 6.1.3.3 |
| Single development-server process | No worker pool; limited concurrency | `Dockerfile` `CMD`; Section 3.6.3 |
| No pagination or result limits | Payload and query cost grow with data volume | `api/routes.py` |

#### 6.5.3.3 Business Metrics

No **business or product metrics** are collected. There is no analytics client (no Google Analytics, no product-analytics SDK, and the declared `web-vitals` package is never wired — Section 6.5.2.1), so operational business signals such as request volume per endpoint, most-queried weeks or artists, or unique-visitor counts are neither captured nor tracked (Section 5.4.1). A precise distinction applies here: the application *does* compute domain analytics — weekly per-feature means (`get_weekly_data`) and annual averages with a rolling-average series (`get_rolling_avg`) rendered in the charts — but these are the user-facing data **product** (Section 1.2.2), not operational metrics gathered for monitoring. No consumption of those computations is counted, timed, or persisted for observability.

#### 6.5.3.4 SLA Monitoring

There are **no SLAs to monitor**. Section 5.4.5 and Section 1.2.3.1 establish that no service-level agreements, service-level objectives, key performance indicators, latency budgets, throughput targets, uptime objectives, or error-rate thresholds are defined anywhere in the repository. Because none is defined, none can be monitored — and, per Section 6.5.2.1, no measurement pipeline exists that could evaluate one even if it were defined. The following matrix documents the SLA/SLO requirements dimension by dimension as an observed absence, consistent with Section 5.4.5, which states the absence of defined SLAs rather than inventing them.

| SLA / SLO Dimension | Defined in Repository? | Basis / Evidence |
|---|---|---|
| Availability / uptime target | No | No target stated; only `restart: on-failure` (Section 5.4.6) |
| Latency / response-time budget | No | No timing captured or targeted (Section 5.4.5) |
| Throughput / capacity target | No | No load targets; single dev-server process (Section 6.1.3.2) |
| Error-rate threshold | No | No error-rate metric; 500s surface only at the client (Section 5.4.3) |

#### 6.5.3.5 Capacity Tracking

There is **no capacity tracking**. Section 6.1.3.2 records capacity planning as "None": no resource metrics are collected, `docker-compose.yml` declares no `deploy.resources` CPU/memory limits or reservations, and there is no explicit SQLAlchemy connection-pool sizing (framework defaults apply). The observable capacity ceiling is therefore structural rather than measured — a single development-server process, a single PostgreSQL 15 instance, and unpaginated week/artist queries whose cost grows with data volume (Section 6.1.3.2). Data growth is driven solely by the external weekly ingestion pipeline (out of repository), and the deployed UI targets a frozen historical window through `2021-11-13` (Section 1.2.1), which bounds the working dataset — a property of the data, not a tracking mechanism.

### 6.5.4 Incident Response

No formal incident-response program exists in the repository. This subsection documents the requested incident-response elements — alert routing, escalation procedures, runbooks, post-mortem processes, and improvement tracking — as the de-facto, manual practices they reduce to for a single-author project whose only automated recovery mechanism is a container restart policy.

#### 6.5.4.1 Alert Routing

There is **no alert routing**, because there are no alerts to route (Section 6.5.2.4). The single automated detection-to-action loop is the Docker `restart: on-failure` policy on the `api` service, which reacts to a non-zero process exit and restarts the container without notifying anyone. Every other failure class is detected manually — an operator noticing a broken view or reading `docker compose logs`. Figure 6.5.4-1 traces each observed failure signal to its (mostly manual) response, and the matrix that follows records the configured thresholds — of which there are none.

```mermaid
flowchart TD
    subgraph Signals["Observed failure signals"]
        Crash{{"api process<br/>exits non-zero?"}}
        Http500{{"route exception<br/>or empty result?"}}
        DbWarm{{"request during<br/>DB warm-up / DB down?"}}
        Stale{{"no new weekly<br/>rows ingested?"}}
    end

    Crash -->|"yes"| DockerDetect["Docker Engine detects exit"]
    DockerDetect -->|"restart: on-failure"| Restart["Restart api container"]
    Restart --> Resume["Service resumes<br/>read-only, no state to recover"]

    Http500 -->|"no try/except"| Return500["Werkzeug returns HTTP 500<br/>process stays up"]
    DbWarm -->|"depends_on = start order only"| Return500
    Return500 --> NoAuto["No alert emitted<br/>500 does not exit the process"]
    NoAuto --> ClientUI["Client: setError(statusText)<br/>user-visible only"]
    ClientUI --> ManualR["Manual recovery: user resubmits;<br/>operator inspects docker logs"]

    Stale -->|"external pipeline, out of repo"| NoDetect["Not detected in repository"]
    NoDetect --> ManualR
```

**Figure 6.5.4-1: Alert Flow — Failure Signals and Their (Manual) Responses.** Only the `api` process-crash path has an automated response (`restart: on-failure`); every other path surfaces as an HTTP 500 handled at the client UI or is not detected within the repository at all.

| Signal / Condition | Configured Threshold | Automated Response |
|---|---|---|
| `api` process non-zero exit | None (any exit triggers policy) | `restart: on-failure` restarts container; no notification |
| Per-request HTTP 5xx | None configured | None — surfaces only in the client UI |
| DB unreachable / warm-up window | None configured | None — request returns HTTP 500; manual |
| Elevated latency or error rate | None configured | None — not measured (Section 6.5.2.1) |
| Data staleness (no new weekly rows) | None configured | None — not detected in repository |

#### 6.5.4.2 Escalation Procedures

There are **no escalation procedures**. The repository defines no on-call rotation, escalation policy, paging tier, or ownership/contact metadata, consistent with its nature as a single-author portfolio project (Section 1.2.1). Escalation therefore reduces to the single maintainer responding to a manually observed failure; there is no second tier to escalate to and no time-based escalation trigger, because there is no alerting layer (Section 6.5.4.1) to initiate one.

#### 6.5.4.3 Runbooks

There are **no runbooks** in the repository (no `docs/`, operations guide, or `RUNBOOK` file). The `README.md` documents the system's purpose and endpoints but not its operations. The operational procedures that can nonetheless be derived from the codebase are summarized below; each is a manual action grounded in an observed artifact.

| Situation | De-facto Procedure | Reference |
|---|---|---|
| Build and start the stack | `docker-compose up --build` (manual; no CI/CD) | Section 3.6.4 |
| Recover a crashed `api` process | Automatic via `restart: on-failure`; else re-`up` | `docker-compose.yml`; Section 6.1.4.1 |
| Inspect runtime state / logs | `docker compose ps`; `docker compose logs -f` | Sections 6.5.2.2, 6.5.2.5 |
| Recover / repopulate data | Re-run the external weekly ingestion pipeline | Section 5.4.6, Section 4.5 |

Two evidence-based caveats bound these procedures: the repository contains no schema-creation, migration, seed, or repair routine, so data recovery depends entirely on the out-of-repository pipeline (Section 5.4.6); and `restart: on-failure` recovers only from a process exit, not from per-request HTTP 500s (Section 6.1.4.1).

#### 6.5.4.4 Post-Mortem Processes

There is **no post-mortem process**. The repository contains no incident-record or post-mortem template, no `docs/` directory, and no `.github/` issue templates (the absence of `.github/` is confirmed in Section 3.6.4), and it captures no incident history. Because there is also no alerting, metrics, or log retention beyond Docker defaults (Sections 6.5.2.1, 6.5.2.2, 6.5.2.4), the data that a post-mortem would normally analyze — timelines, error rates, traces — is not collected in the first place.

#### 6.5.4.5 Improvement Tracking

There is **no in-repository improvement-tracking mechanism**. The repository contains no issue-tracker configuration, no `.github/` (so no issue/PR templates and no GitHub Actions — Section 3.6.4), no `CHANGELOG`, and no roadmap or TODO document, and it has no automated tests or CI gate that could catch regressions (Section 3.6.4). The About view links out to an external personal GitHub repository (Section 1.2.1.1), so any defect or enhancement tracking would occur there — outside this repository's boundary. The only in-repo version signal is the frontend application version `0.1.0` in `frontend/package.json`; no backend version is declared.

### 6.5.5 References

**Repository files examined for this section:**

- `requirements.txt` - Confirmed the backend dependency set contains no metrics/APM/tracing/logging client (no `prometheus-client`, `statsd`, OpenTelemetry, `sentry-sdk`, `datadog`, `newrelic`); `gunicorn` is present but not wired.
- `frontend/package.json` - Confirmed `web-vitals` is declared and the application version is `0.1.0`; confirmed the absence of any analytics/telemetry client.
- `frontend/src/index.js` - Established that `reportWebVitals` is never invoked, making the declared `web-vitals` dependency vestigial (no client performance telemetry emitted).
- `api/__init__.py` - Established that the Flask bootstrap configures no `logging` handler, health endpoint, or metrics instrumentation.
- `api/routes.py` - Confirmed the six GET routes contain no `/health`, `/status`, or `/metrics` endpoint, no logging, and no `try/except`; established `GET /` as static-only (shallow liveness) and `GET /api/week/<week>` as the DB-exercising (deep readiness) path.
- `api/funcs.py` - Established the domain-analytics helpers (`get_query_week`, `get_weekly_data`, `get_rolling_avg`) that constitute the user-facing data product rather than operational telemetry.
- `api/models.py` - Established the precomputed `YearlyAvg` aggregate cited as a performance characteristic.
- `app.py` - Established the development-server entry point (`app.run(host='0.0.0.0')`) that exposes no metrics or health surface.
- `Dockerfile` - Confirmed no `HEALTHCHECK` instruction and the `CMD ["python3","app.py"]` development-server runtime.
- `docker-compose.yml` - Established `restart: on-failure` as the sole automated recovery mechanism and the absence of any `healthcheck:`, `logging:` driver, and `deploy.resources` configuration.
- `.flaskenv` - Corroborated the `development` runtime configuration (`FLASK_ENV=development`).
- `.gitignore` - Confirmed the ignored `*-debug.log` patterns are npm/yarn build-time logs, not runtime application logs.
- `README.md` - Confirmed operations/monitoring are undocumented and that data population depends on the external weekly ingestion pipeline.
- `frontend/src/components/tracks/TracksSection.js` - Established the client-side error/loading UI state driven by `response.status > 299`, with no reporting to any service.
- `frontend/src/components/trends/TrendsSection.js` - Corroborated the same client-side error/loading pattern for the Trends view.

**Repository folders examined:**

- `api/` - The complete Flask backend package; confirmed no monitoring, logging, tracing, or health instrumentation anywhere in the four modules.
- `frontend/src/components/` - The React feature components; confirmed observability is limited to user-facing error/loading states.

**Cross-referenced Technical Specification sections:**

- `1.2 System Overview` - Single-author portfolio project and frozen historical dataset (1.2.1); the recorded absence of monitoring/analytics instrumentation and of formal SLAs/KPIs (1.2.3.1).
- `3.6 Development & Deployment` - Development-server runtime (3.6.3) and the absence of any CI/CD pipeline (3.6.4).
- `4.5 Error Handling and Recovery Flows` - Error propagation and the manual/data-repopulation recovery behavior referenced in the incident-response discussion.
- `5.4 Cross-Cutting Concerns` - Monitoring/observability absence (5.4.1), logging and tracing absence (5.4.2), error-handling pattern (5.4.3), SLA absence (5.4.5), and disaster recovery / `restart: on-failure` (5.4.6).
- `6.1 Core Services Architecture` - Synchronous single-process communication (6.1.2.2), capacity/auto-scaling absence and "no metrics source" finding (6.1.3.2), and fault-tolerance/restart behavior (6.1.4.1).

**Web searches:** None conducted for this section; all findings are grounded in direct repository inspection.

## 6.6 Testing Strategy

### 6.6.1 Testing Approach and Applicability Assessment

**Detailed Testing Strategy is not applicable for this system.** The repository at HEAD `2fd0190` implements no automated test suite of any kind: there are no unit tests, no integration tests, and no end-to-end tests anywhere in the codebase. A recursive inspection of the tree (excluding `node_modules/`, `build/`, and `.git/`) returns zero test files — no `*.test.js`/`*.test.jsx`, no `*.spec.js`, no `test_*.py`/`*_test.py`, no `conftest.py`, and no `setupTests.js` — and zero test directories (`__tests__/`, `tests/`, `test/`, `spec/`, `cypress/`, `e2e/`, `__mocks__/` are all absent). The `frontend/src/` tree contains exactly sixteen source files (`App.js`, `index.js`, `styles/index.css`, and thirteen component/data files under `components/` and `trends/`), none of which is a test module.

This determination is consistent with the evidence-based, "document observed absences rather than aspirations" convention used throughout Chapter 5, Section 6.1, and Section 6.5, and it aligns with Section 1.3.2, which already lists "Test suites and CI/CD pipelines" as out-of-scope. The system is a single-author portfolio project — a Billboard Hot 100 data-visualization web application built from a Flask read-only API and a Create React App single-page frontend, operated as a local Docker Compose stack against a frozen historical dataset through 2021-11-13. It is not a simple library or CLI tool; rather, it is a full-stack application for which comprehensive testing *would* be applicable in a production context, but for which no testing has actually been implemented. Accordingly, this section documents the single testing capability that is present in the repository — the default, unexercised Create React App (CRA) Jest + React Testing Library scaffold — and records the remaining test categories as observed absences with their supporting evidence, rather than fabricating a strategy the code does not contain.

The following capability matrix summarizes the observed state of every testing pillar required by this section. No coverage percentages, service-level agreements, latency thresholds, or quality gates are asserted because none are defined in the repository.

| Testing Pillar | Observed Status | Evidence in Repository |
|----------------|-----------------|------------------------|
| Unit testing (frontend) | Capability declared, entirely unused | `react-scripts test` script + `@testing-library/*` deps in `frontend/package.json`; no test files exist |
| Unit testing (backend) | Not present | `requirements.txt` declares no test runner (no `pytest`, `unittest` suite, `nose`, or `tox`) |
| Integration testing | Not present | No API/DB integration tests; no fixtures, mocks, or test database |
| End-to-end / UI automation | Not present | No `cypress`, `playwright`, `selenium`, or `puppeteer` in any manifest |
| Performance / load testing | Not present | No `locust`, `k6`, `jmeter`, `artillery`, or `gatling` in any manifest |
| Test automation (CI/CD) | Not present | No `.github/`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/`, or pipeline config |
| Coverage measurement | Not configured | No `jest` config, `coverageThreshold`, `.coveragerc`, or `codecov.yml` |

The single test-execution path that the repository actually supports is the CRA-provided frontend runner. The diagram below traces that path and contrasts it with the absent backend runner and the absent automation trigger. Solid edges denote the flow that exists today (which currently resolves to "no tests found"); dotted edges denote the behavior that *would* occur if test modules or automation were introduced.

```mermaid
flowchart TD
    Dev["Developer initiates a test run"]

    subgraph FE["Frontend path - capability present but dormant"]
        NpmTest["npm test<br/>(package.json script: react-scripts test)"]
        Jest["Jest runner + jsdom environment<br/>@testing-library/react available"]
        Discover{{"Discover *.test.js or<br/>src/__tests__/* files?"}}
        NoTests["Runner reports<br/>'No tests found'"]
        WouldRun["Would render components and<br/>assert with jest-dom matchers"]
    end

    subgraph BE["Backend path - capability absent"]
        NoPy["No test runner in requirements.txt<br/>(no pytest / unittest suite)"]
    end

    subgraph Trigger["Automation trigger - absent"]
        NoCI["No CI/CD workflow<br/>(no .github, no pipeline)"]
    end

    Dev --> NpmTest
    Dev --> NoPy
    NpmTest --> Jest
    Jest --> Discover
    Discover -->|"none present today"| NoTests
    Discover -.->|"if test files were added"| WouldRun
    NoCI -.->|"nothing invokes the runner automatically"| NpmTest
```

**Figure 6.6.1-1: Test Execution Flow (Observed).** The only wired runner is the frontend `react-scripts test` command; with no test files in the tree it terminates at "No tests found." The backend has no runner declared, and no CI/CD workflow exists to invoke either path automatically.

#### 6.6.1.1 Unit Testing

Unit testing is the sole testing capability materially present in the repository, and it is present only as an unexercised scaffold on the frontend. No unit test has been written or executed against either tier.

**Testing frameworks and tools.** The frontend inherits its test toolchain from Create React App via `react-scripts` 4.0.3, which supplies an out-of-the-box Jest test runner executing in a jsdom (simulated browser) environment. `frontend/package.json` additionally declares the React Testing Library family — `@testing-library/react` ^11.1.0, `@testing-library/jest-dom` ^5.11.4, and `@testing-library/user-event` ^12.1.10 — as runtime dependencies. These packages are installed to support the CRA `test` script, but the project contains no test files, so they are effectively dormant; a grep across `frontend/src/` for `@testing-library`, `describe(`, `it(`, `test(`, `expect(`, or `jest` returns no matches, confirming they are never imported. The backend declares no unit-testing framework at all: `requirements.txt` lists application and data libraries (Flask 2.0.1, Flask-SQLAlchemy 2.5.1, marshmallow, pandas 2.0.0, numpy 1.24.2, psycopg2) but no `pytest`, `nose`, `tox`, or `coverage` package.

| Tier | Runner / Library | Version | Status |
|------|------------------|---------|--------|
| Frontend | Jest (via `react-scripts test`) | `react-scripts` 4.0.3 | Available, no tests written |
| Frontend | `@testing-library/react` | ^11.1.0 | Declared, unused |
| Frontend | `@testing-library/jest-dom` | ^5.11.4 | Declared, unused |
| Backend | (none declared) | n/a | Not present |

**Test organization structure.** No test organization exists because no tests exist. The CRA/Jest defaults inherited through `react-scripts` establish the *conventions* that would apply if tests were added: Jest automatically discovers files matching `*.test.js`/`*.test.jsx` or any file inside a `src/__tests__/` directory, and the CRA idiom co-locates a component's test beside the component (for example, an `App.test.js` next to `App.js`). None of these locations is populated in the current tree.

**Mocking strategy.** No mocking strategy is implemented; there are no `__mocks__/` directories, no `jest.mock(...)` calls, and no HTTP stubbing libraries (`nock`, `msw`, `requests-mock`, `responses`) in either manifest. If the dormant scaffold were exercised, the natural seam to isolate would be the frontend's data-access layer: every component fetches JSON from the Flask API using the browser-native `fetch` API through the CRA dev-server `proxy` (`"proxy": "http://localhost:5000"` in `frontend/package.json`), so unit tests would stub `global.fetch` to return canned endpoint responses. This is a description of the available seam, not an implemented pattern.

**Code coverage requirements.** No coverage requirement is defined anywhere in the repository. `frontend/package.json` contains no `jest` configuration block, no `coverageThreshold`, and no `collectCoverage`/`coverageReporters` settings, so only CRA defaults apply and no coverage gate is enforced. The `.gitignore` file does list a `# testing` / `/coverage` entry and `.env.test.local`, but these are stock CRA conventions marking where `react-scripts test --coverage` *would* write output; no coverage report is generated or committed. On the backend there is no coverage tooling at all. Because no target has been set in the code, this specification does not assert one.

**Test naming conventions.** No naming convention is in effect, as there are no tests. The applicable default — again inherited, not authored — is the Jest/CRA pattern of `<unit>.test.js` filenames with `describe(...)`/`it(...)` (or `test(...)`) blocks whose descriptions read as behavioral sentences.

**Test data management.** No test data or fixtures exist in the repository (no fixture files, factories, or seed scripts). Live application data originates from an external weekly ingestion pipeline that runs outside this repository and populates the PostgreSQL `db` database; the API tier reads that data read-only through six GET endpoints. For unit testing, deterministic pure functions in `api/funcs.py` are the most testable backend units and require no database. For example, `get_query_week(date)` normalizes an input date to its Billboard chart Saturday: calling it with a date that is already a Saturday returns that same date, so `get_query_week('2021-11-13')` returns `'2021-11-13'`. An illustrative (currently non-existent) unit test would assert exactly that:

```python
# Illustrative only - no such test exists in the repository

assert get_query_week('2021-11-13') == '2021-11-13'
```

#### 6.6.1.2 Integration Testing

Integration testing is not present in the repository. No test exercises the interaction between the React frontend, the Flask API, and the PostgreSQL database, and there is no harness to bring those components up together for verification.

**Service integration test approach.** None is implemented. The runtime integration surface is well defined — the frontend calls the API over HTTP (routed through the CRA proxy in development), and the API talks to PostgreSQL via SQLAlchemy — but no automated test validates that path. The `docker-compose.yml` stack defines only two services, `api` (built from the `Dockerfile`, published on `80:5000`) and `postgres` (image `postgres:15`, published on `5432:5432`); there is no third service, stage, or step dedicated to running tests.

**API testing strategy.** None is implemented. The API exposes six read-only GET routes (`/`, `/api/`, `/api/track/<spotify_id>`, `/api/week/<week>`, `/api/artist/<artist>`, `/api/analysis/<feature>`) defined in `api/routes.py`, but no request-level tests exist and no API-testing client is declared (no `pytest-flask`, no Flask test client usage, no `supertest`).

**Database integration testing.** None is implemented. The persistence layer is Flask-SQLAlchemy models in `api/models.py` bound to a hard-coded DSN (`postgresql://postgres:postgres@postgres/db`), but there is no test database, no migration/seed script, no transactional-rollback fixture, and no in-memory database substitution.

**External service mocking.** None is implemented. Notably, the application tier itself contacts no third-party service at request time — the Spotify/Billboard data acquisition is performed by an external weekly ingestion pipeline outside this repository — so there is no outbound integration for a test to mock, and correspondingly no mocking library is declared.

**Test environment management.** No dedicated test environment exists. There is no `.env.test`, no ephemeral test-database provisioning, and no compose override for testing; the only environment configuration present (`.flaskenv`, the compose service variables) targets local development and runtime, not testing.

#### 6.6.1.3 End-to-End Testing

End-to-end testing is not present in the repository, and no UI-automation, performance, or cross-browser tooling is declared in any manifest.

**E2E test scenarios.** None are defined. Although the application has clear user journeys — selecting a chart week via the date picker to drive the track radar chart, and selecting an audio feature to drive the trends line chart — no scenario is encoded as an automated test.

**UI automation approach.** None is implemented. A grep across `frontend/package.json` and `requirements.txt` for `cypress`, `playwright`, `selenium`, `puppeteer`, `webdriver`, `nightwatch`, and `testcafe` returns no matches, so there is no browser-driving harness. The only browser-like execution context available anywhere in the toolchain is the jsdom environment bundled with Jest, which is a unit/component sandbox rather than a real-browser E2E driver.

**Test data setup/teardown.** None exists. Consistent with Sections 6.6.1.1 and 6.6.1.2, there are no fixtures, seed scripts, factories, or teardown hooks; the frontend renders against whatever the live API returns from the frozen historical dataset.

**Performance testing requirements.** No performance or load testing is defined. No load-testing tool (`locust`, `k6`, `jmeter`, `artillery`, `gatling`) is present, and no latency, throughput, or resource threshold is stated in the repository. This specification therefore asserts no performance target.

**Cross-browser testing strategy.** No cross-browser automation is implemented. The repository does contain a CRA `browserslist` configuration in `frontend/package.json` (production and development target lists), which governs how Babel/PostCSS transpile output for a range of browsers, but this is a build-targeting declaration, not an executed cross-browser test matrix.

### 6.6.2 Test Automation

There is no test automation in this repository. Because no automated tests exist (Section 6.6.1) and no continuous-integration service is configured, there is nothing to trigger, parallelize, report on, gate, or de-flake. This subsection documents each automation facet the section prompt requires against the observed repository state, and describes the only host on which tests could run today — a developer workstation.

The following matrix records each automation facet and its supporting evidence. No automation thresholds, retry counts, or reporting SLAs are asserted because none are defined in the repository.

| Automation Facet | Observed Status | Evidence in Repository |
|------------------|-----------------|------------------------|
| CI/CD integration | Not present | No `.github/`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/`, `azure-pipelines.yml`, or `.travis.yml` |
| Automated test triggers | Not present | No pipeline, no Git hooks, no watch/pretest scripts beyond CRA default |
| Parallel test execution | Not configured | No `jest`/`--maxWorkers` config; only implicit CRA/Jest defaults |
| Test reporting | Not configured | No JUnit/HTML/coverage reporter; only Jest's default console output |
| Failed-test handling | Not present | No gate exists to fail a build; `docker-compose.yml` has no test step |
| Flaky-test management | Not present | No retry, quarantine, or `jest.retryTimes` configuration |

#### 6.6.2.1 CI/CD Integration

No CI/CD integration exists. The repository contains no continuous-integration configuration of any kind — there is no `.github/` directory (hence no GitHub Actions workflow), and no `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/`, `azure-pipelines.yml`, `.travis.yml`, or `bitbucket-pipelines.yml`. This is consistent with Section 3.6, which records the CI/CD pipeline as "None," and with Section 1.3.2, which lists CI/CD pipelines as out-of-scope. The only orchestration artifact present is `docker-compose.yml`, which builds and runs the `api` and `postgres` services for local execution; it defines no test service and no test stage, and the `Dockerfile` ends with `CMD ["python3", "app.py"]` (the Flask development server) with no test invocation. There is therefore no pipeline into which a test phase could be inserted without new configuration.

#### 6.6.2.2 Automated Test Triggers

No automated test trigger exists. Nothing in the repository invokes the frontend `react-scripts test` command automatically: there is no CI workflow, no Git hook directory (no `.husky/` and no committed `.git/hooks` automation), and no `pretest`/`posttest` or watch-orchestration script in `frontend/package.json` beyond the CRA-default `test` script. The `test` script must be run manually by a developer, and — as shown in Figure 6.6.1-1 — it currently resolves to "No tests found." The diagram below shows the only environment in which that manual invocation could execute.

```mermaid
flowchart TD
    subgraph WS["Developer workstation - the only test host"]
        direction TB
        NodeTC["Node.js + npm toolchain"]
        JestEnv["Jest + jsdom (in-process)<br/>self-contained: no network, no DB"]
        Venv["Python virtualenv (venv)"]
        NoRunner["No backend test runner installed"]
        NodeTC --> JestEnv
        Venv --> NoRunner
    end

    subgraph NotProv["Not provisioned for testing"]
        direction TB
        NoCIRunner["No CI runner / build agent"]
        NoTestDB["No dedicated or ephemeral test database"]
    end

    subgraph Runtime["Runtime stack (development only, not a test target)"]
        direction TB
        ApiSvc["api service (Flask dev server, 80:5000)"]
        PgSvc["postgres service (postgres:15, 5432:5432)"]
        ApiSvc --> PgSvc
    end

    JestEnv -.->|"would render components locally"| Result["Pass/fail printed to console"]
    NoCIRunner -.->|"absent: no automated host"| WS
    ApiSvc -.->|"serves live frozen data, not test fixtures"| JestEnv
```

**Figure 6.6.2-1: Test Environment Architecture (Observed).** The only host capable of running tests is a developer workstation. The frontend Jest + jsdom environment is self-contained (no network or database), the Python virtualenv has no backend runner installed, and no CI runner or dedicated test database is provisioned. The runtime `api`/`postgres` stack exists for development, not as a test target.

#### 6.6.2.3 Parallel Test Execution

No parallel-execution policy is configured. `frontend/package.json` contains no `jest` configuration block and no `--maxWorkers` argument, so only Jest's implicit CRA defaults would apply if tests existed (Jest parallelizes across worker processes by default and runs in-band in CI mode). Because there are no test files and no CI, no parallelization actually occurs. On the backend there is no test runner, so parallel execution is not applicable.

#### 6.6.2.4 Test Reporting

No test-reporting requirement is defined. There is no JUnit/XML reporter, no HTML report generator, and no coverage reporter configured; `frontend/package.json` declares none of `jest-junit`, `jest-html-reporter`, or custom `reporters`. The only reporting that would occur is Jest's built-in console output (pass/fail summary), and the `.gitignore` `/coverage` entry marks where a `--coverage` text/HTML report *would* be written — but no report is generated or committed. No dashboards or report artifacts are produced anywhere in the stack.

#### 6.6.2.5 Failed-Test and Flaky-Test Handling

No failed-test handling exists because there is no build or deployment gate to fail. `docker-compose.yml` builds and starts the services unconditionally, and there is no pipeline step whose exit status depends on a test result; a failing test today would surface only in the developer's local console. Likewise, no flaky-test management is present: there is no retry mechanism (no `jest.retryTimes`, no CI retry directive), no test-quarantine list, and no flakiness-tracking tooling. These capabilities would require introducing both a test suite and a CI system, neither of which is present in the repository.

### 6.6.3 Quality Metrics

No quality metrics for testing are defined in the repository. There are no coverage targets, no test-success-rate requirements, no performance thresholds, and no automated quality gates that reference tests, because — as established in Sections 6.6.1 and 6.6.2 — no tests and no CI system exist. In keeping with the "document observed absences rather than aspirations" convention, this subsection reports each metric as undefined with its supporting evidence and does not fabricate targets, percentages, or SLAs.

| Quality Metric | Target Defined? | Evidence in Repository |
|----------------|-----------------|------------------------|
| Code coverage target | No | No `jest` config / `coverageThreshold`; no `.coveragerc` |
| Test success-rate requirement | No | No test suite and no CI to measure a pass rate |
| Performance test threshold | No | No load tool; no stated latency/throughput budget |
| Quality gate (test-based) | No | No CI gate; ESLint runs non-blocking in dev/build |
| Test documentation requirement | No | No test plan, `TESTING.md`, or documented conventions |
| Security testing | No | No SAST/DAST/dependency-audit tooling configured |

#### 6.6.3.1 Code Coverage Targets

No code-coverage target is defined. `frontend/package.json` has no `jest` configuration block and therefore no `coverageThreshold` (global or per-path), no `collectCoverageFrom`, and no `coverageReporters`. The `.gitignore` `# testing` / `/coverage` entry only marks the directory where `react-scripts test --coverage` would emit a report; because no tests exist, no coverage is ever collected. The backend has no coverage tooling (`coverage`/`pytest-cov` are absent from `requirements.txt`). Consequently this specification states no coverage percentage.

#### 6.6.3.2 Test Success-Rate Requirements

No test success-rate requirement is defined. With zero tests and no CI system to aggregate results, there is no pass/fail rate to measure or enforce. No `package.json` script, compose step, or configuration references a minimum passing threshold.

#### 6.6.3.3 Performance Test Thresholds

No performance test threshold is defined. No load- or performance-testing tool is declared in any manifest (no `locust`, `k6`, `jmeter`, `artillery`, or `gatling`), and no latency, throughput, error-rate, or resource-utilization budget appears anywhere in the repository. The application's runtime characteristics (a read-only Flask API over a frozen PostgreSQL dataset) are not exercised by any benchmark in the codebase, so no performance target is asserted.

#### 6.6.3.4 Quality Gates

No test-based quality gate exists. Because there is no CI/CD pipeline (Section 6.6.2.1), nothing blocks a merge or deployment on test results. The only automated static check present is the Create React App ESLint integration: `frontend/package.json` sets `eslintConfig` to extend `react-app` and `react-app/jest`, which runs during `react-scripts start` and `react-scripts build` and surfaces lint findings in the console. As documented in Section 3.6.1, this linting is advisory rather than a hard gate — build output is not configured to fail on lint warnings — and there is no separate Python linter or formatter for the backend. No pull-request checks, status checks, or branch-protection rules are present in the repository.

#### 6.6.3.5 Documentation Requirements

No testing-documentation requirement is defined. The repository contains no test plan, no `TESTING.md`, and no documented test conventions; `README.md` describes the application's purpose, endpoints, and run instructions but does not prescribe testing practices. No docstring or comment convention enforces test-related documentation.

#### 6.6.3.6 Security Testing Requirements

No security testing is configured. There is no static application security testing (SAST), no dynamic application security testing (DAST), and no automated dependency-vulnerability scanning (no `npm audit` gate, no `pip-audit`, no `safety`, no Dependabot/Snyk configuration, and no `.github/` to host such a workflow). The relevant security posture is therefore descriptive rather than test-enforced, and is covered in Section 6.4: the API is read-only (six GET routes) and single-origin via Flask-Cors, and the database DSN (`postgresql://postgres:postgres@postgres/db`) is hard-coded with default credentials — a configuration that a security test *would* flag, but which no test in this repository verifies. No penetration-testing scripts or security test cases exist.

#### 6.6.3.7 Test Data Flow

The diagram below illustrates the lineage of test *inputs* — a distinct lens from the execution and environment views above. It contrasts the frontend test-data path that would exist if the dormant scaffold were used (mock payloads feeding a stubbed `fetch`, rendered by React Testing Library into a jsdom virtual DOM and checked with jest-dom assertions) against the absent test-data infrastructure and the runtime data lineage that tests do not consume. All dotted edges are unimplemented.

```mermaid
flowchart LR
    subgraph FETest["Frontend test-data path (dotted = not implemented)"]
        direction TB
        Fixtures["Fixture / mock payloads<br/>(none exist in repo)"]
        MockFetch["Stubbed global.fetch<br/>(not implemented)"]
        Render["RTL render(component)"]
        DOMv["jsdom virtual DOM"]
        Assert["jest-dom assertions<br/>(pass/fail)"]
        Fixtures -.-> MockFetch
        MockFetch -.-> Render
        Render -.-> DOMv
        DOMv -.-> Assert
    end

    subgraph AbsentInfra["Absent test-data infrastructure"]
        direction TB
        NoFix["No fixtures / factories / seed scripts"]
        NoTestDB2["No test database"]
    end

    subgraph RuntimeData["Runtime data lineage (not consumed by tests)"]
        direction TB
        Ingest["External weekly ingestion<br/>(outside repository)"]
        Pg["PostgreSQL db (frozen data<br/>through 2021-11-13)"]
        Api["Flask API (6 read-only GET routes)"]
        Ingest --> Pg --> Api
    end

    Api -.->|"live data, bypassed by mocked fetch"| MockFetch
```

**Figure 6.6.3-1: Test Data Flow (Observed).** No fixtures, factories, seed scripts, or test database exist. If the CRA scaffold were exercised, frontend tests would inject mock payloads into a stubbed `fetch` and assert against a jsdom virtual DOM, deliberately bypassing the live runtime data lineage (external ingestion → PostgreSQL → Flask API) rather than depending on it.

### 6.6.4 References

The following repository files, folders, and previously authored specification sections were examined as evidence for this section. All claims above are grounded in these sources; no external web searches were required.

**Repository files examined**

- `frontend/package.json` - Established the `react-scripts test` script, the `@testing-library/react`/`jest-dom`/`user-event` dependencies (declared, unused), the `eslintConfig` extending `react-app`/`react-app/jest`, the `proxy` and `browserslist` settings, and the absence of any `jest`/`coverageThreshold` configuration or `devDependencies`.
- `requirements.txt` - Confirmed the backend dependency set and the absence of any test runner or coverage tool (no `pytest`, `nose`, `tox`, or `coverage`).
- `.gitignore` - Confirmed the stock CRA `# testing` / `/coverage` and `.env.test.local` entries (path conventions only; unused).
- `docker-compose.yml` - Confirmed the two-service (`api`, `postgres`) stack with no test service or test stage.
- `Dockerfile` - Confirmed the image build and `CMD ["python3", "app.py"]` entrypoint with no test invocation.
- `.flaskenv` - Confirmed the only backend environment configuration targets development/runtime, not testing.
- `api/routes.py` - Confirmed the six read-only GET routes that would be the subject of API/integration tests.
- `api/funcs.py` - Provided the deterministic `get_query_week` pure function used in the illustrative unit-test pattern.
- `api/models.py` - Confirmed the Flask-SQLAlchemy models and hard-coded database DSN referenced under integration and security testing.
- `README.md` - Confirmed the application's purpose and run instructions and the absence of any documented testing practice.

**Repository folders examined**

- `frontend/src/` - Contained exactly sixteen source files (components and data), none of which is a test module.
- `api/` - Backend Flask package (`__init__.py`, `funcs.py`, `models.py`, `routes.py`); contained no tests.
- `frontend/` - Frontend project root; contained no test files or test tooling configuration beyond the CRA defaults in `package.json`.
- Repository root (`/`) - Confirmed the absence of CI/CD directories/files (`.github/`, `.gitlab-ci.yml`, `Jenkinsfile`, `.circleci/`, `azure-pipelines.yml`) and of any coverage/test configuration files.

**Cross-referenced specification sections**

- Section 1.3 Scope - Corroborates that test suites and CI/CD pipelines are out-of-scope.
- Section 3.2 Frameworks & Libraries - Corroborates the "declared, unused" status of the Testing-Library packages.
- Section 3.6 Development & Deployment - Corroborates the "None" CI/CD status and the advisory CRA ESLint linting.
- Section 6.1 Core Services Architecture - Precedent for the applicability-assessment framing.
- Section 6.4 Security Architecture - Source for the read-only, single-origin, hard-coded-DSN security posture referenced under security testing.
- Section 6.5 Monitoring and Observability - Precedent for the evidence-based "document observed absences" house style adopted here.

**Web searches**: None conducted.

# 7. User Interface Design

## 7.1 Core UI Technologies

The user interface is a client-side **single-page application (SPA)** located in `frontend/`, scaffolded with **Create React App (CRA)** and written in JavaScript. It is not an independently hosted front end: the same Flask process that exposes the JSON API also serves the compiled SPA as static assets from `frontend/build`, so the UI and API share one origin in production (`api/__init__.py` sets `static_folder='../frontend/build'`, `static_url_path='/'`; see Feature F-006 in §2.2 and the integration boundaries in §6.3). The table below enumerates the technologies that actually constitute the UI, with the versions declared in `frontend/package.json`.

| Technology | Declared Version | Role in the UI | Primary Evidence |
|---|---|---|---|
| React / ReactDOM | `^17.0.2` | Component model, hooks-based state, DOM rendering | `frontend/package.json`, `src/index.js`, `src/App.js` |
| react-scripts (CRA) | `4.0.3` | Build, dev server, test, and bundling toolchain | `frontend/package.json` (`scripts`) |
| styled-components | `^5.3.0` | Component-scoped CSS for the navigation primitives | `src/components/navigation/{Sidebar,Tab,SmallTab,Section}.js` |
| Global CSS (`index.css`) | n/a | Application-wide theme tokens, layout, and utility classes | `src/styles/index.css` |
| @amcharts/amcharts4 | `^4.10.19` | Radar chart (Tracks) and line chart (Trends) | `src/components/tracks/RadarChart.js`, `src/components/trends/LineChart.js` |
| Browser Fetch API | native | HTTP data access to the backend (no HTTP client library) | `src/components/tracks/TracksSection.js`, `src/components/trends/TrendsSection.js` |
| Jost typeface (Google Fonts) | n/a | Primary UI typography, loaded from a CDN | `frontend/public/index.html` |
| web-vitals | `^1.0.1` | Declared performance-metrics helper (not wired in) | `frontend/package.json`, `src/index.js` |

### 7.1.1 Framework, Language, and Build Toolchain

The UI is built on **React 17** using function components and hooks only — `useState` for local component and shell state and `useEffect` for on-mount data loading. The entry point mounts a single component tree in React Strict Mode into the `#root` element:

```javascript
// src/index.js
ReactDOM.render(<React.StrictMode><App /></React.StrictMode>,
  document.getElementById('root'));
```

The project is authored in **JavaScript, not TypeScript** — every source file uses the `.js` extension and there is no `tsconfig.json` or `@types` dependency. The build/dev toolchain is **Create React App** via `react-scripts@4.0.3`, exposed through the `start`, `build`, `test`, and `eject` scripts in `frontend/package.json`. An additional convenience script, `start-api` (`cd .. && venv/bin/flask run --no-debugger`), boots the Flask backend from the frontend workspace during development. There is **no client-side router** (no `react-router` dependency); view changes are performed entirely through in-memory state (§7.6), so the browser URL does not change as the user moves between views.

### 7.1.2 Styling and Layout System

The UI uses a **two-part styling strategy**. The navigation primitives are implemented as **styled-components** — `Sidebar` (as `StSidebar`), `Tab`, `SmallTab`, and `Section` each wrap a styled element and read React props (`props.nav`, `props.activeTab`) to compute dynamic styles. Everything else (sections, input controls, track rows, footer, chart containers) is styled through **global CSS classes** declared in `src/styles/index.css`, which also defines the shared design tokens as CSS custom properties on `:root` (documented in §7.7). The Google **Jost** font family is preconnected and loaded via a stylesheet `<link>` in `frontend/public/index.html` and applied as the `body` font in `index.css`.

### 7.1.3 Data Visualization

All charts are rendered with **amCharts 4** (`@amcharts/amcharts4`), imported as core, charts, and the animated theme. Two chart types are used:

```javascript
// pattern shared by RadarChart.js and LineChart.js
import * as am4core from '@amcharts/amcharts4/core';
import * as am4charts from '@amcharts/amcharts4/charts';
am4core.useTheme(am4themes_animated);
```

`RadarChart.js` builds an `am4charts.RadarChart` (a partial-ring radar) into a `div` with id `radialChart`, and `LineChart.js` builds an `am4charts.XYChart` with a yearly `DateAxis` into a `div` with id `featureChart`. Both components create their chart instance **during render** and leave `chart.dispose()` commented out, which is the client-side chart-lifecycle characteristic already noted in §5.2.2.

### 7.1.4 Client–Server Communication and Single-Origin Delivery

The UI communicates with the backend exclusively over **HTTP/JSON using the browser-native `fetch` API** — there is no Axios, GraphQL client, or WebSocket usage in the source. Requests are issued to relative `/api/...` paths, which resolve differently by environment:

- **Development:** CRA's dev server proxies `/api/*` calls to the Flask backend via the `"proxy": "http://localhost:5000"` entry in `frontend/package.json`.
- **Production:** the Flask app serves the compiled SPA at the site root, so the same relative paths are **same-origin** requests to the API (§6.3.4.3).

`CORS(app)` is enabled permissively on the backend (`api/__init__.py`), which is exercised mainly in the proxied development mode. The full endpoint catalog and wire contracts are documented in §6.3.2 and §7.3.

### 7.1.5 Progressive-Web-App Shell Assets

The SPA ships a minimal **PWA manifest** (`frontend/public/manifest.json`) declaring `name`/`short_name` "Hot Stuff", `display: standalone`, `start_url: "."`, `theme_color: #000000`, and `background_color: #ffffff`. The HTML shell (`frontend/public/index.html`) sets the document title to "Hot Stuff", declares a mobile-friendly `viewport` meta tag, and provides a `<noscript>` fallback message. Note that the manifest references `logo192.png` and `logo512.png` icons that are not present in the repository (only `favicon.ico` exists in `public/` and `build/`).

### 7.1.6 Declared-but-Unused UI Dependencies

Several dependencies are declared in `frontend/package.json` but are **not imported or wired into any source file**, and therefore do not participate in the running UI:

| Dependency | Declared Version | Status |
|---|---|---|
| axios | `^0.21.1` | Unused — the SPA uses native `fetch` instead |
| plotly.js | `^1.58.4` | Unused — charts are rendered with amCharts 4 |
| react-plotly.js | `^2.5.1` | Unused — no Plotly component is imported |
| @testing-library/{jest-dom,react,user-event} | `^5.11.4` / `^11.1.0` / `^12.1.10` | Declared, but the repository contains no test files |
| web-vitals | `^1.0.1` | Declared, but `reportWebVitals` is never invoked in `src/index.js` |

These absences are consistent with the constraints recorded in §2.5 and the third-party-service analysis in §6.3.

## 7.2 UI Use Cases

The UI serves a single class of user performing read-only, exploratory analysis of Billboard Hot 100 audio-feature data. Every use case below is traceable to a specific view and, where data is involved, to a specific backend endpoint.

### 7.2.1 Primary Actor

There is exactly one actor: an **anonymous web visitor**. The application implements no authentication, authorization, sessions, or user accounts (confirmed in §6.3.2.3), so all capabilities are equally available to every visitor and there are no role-differentiated views. The visitor interacts only through the browser; there are no administrative, editorial, or data-entry surfaces in the UI (the data itself is written by an out-of-repository weekly pipeline, per §6.3).

### 7.2.2 Use-Case Catalog

| ID | Use Case | View (Feature) | Backend Interaction |
|---|---|---|---|
| UC-1 | Browse the ranked Hot 100 for a chosen historical week | Tracks (F-007) | `GET /api/week/<date>` |
| UC-2 | Inspect a week's aggregate audio "fingerprint" via a radar chart | Tracks (F-007) | Uses the `averages` block of the same `/api/week` response |
| UC-3 | Analyze how one audio feature has trended across years | Trends (F-008) | `GET /api/analysis/<feature>` |
| UC-4 | Read plain-language definitions of the audio features | Trends (F-008) | None — bundled locally in `features.json` |
| UC-5 | Learn about the project, its data sources, and the API endpoints | About (F-009) | None — static content with outbound links |
| UC-6 | Move between views and open/close the mobile navigation menu | Navigation shell (F-010) | None — in-memory state only |

The diagram maps the actor to each use case and shows which two use cases reach the backend.

```mermaid
flowchart LR
    Visitor["Anonymous Web Visitor<br/>(no authentication)"]

    subgraph SPA["Hot Stuff SPA (frontend/src)"]
        UC1["UC-1 Browse weekly Hot 100 chart"]
        UC2["UC-2 Inspect weekly audio fingerprint (radar)"]
        UC3["UC-3 Analyze audio-feature trend over years"]
        UC4["UC-4 Read audio-feature glossary"]
        UC5["UC-5 Learn about project, data & API"]
        UC6["UC-6 Navigate views / toggle mobile menu"]
    end

    API["Flask JSON API<br/>(same-origin in production)"]

    Visitor --> UC1
    Visitor --> UC2
    Visitor --> UC3
    Visitor --> UC4
    Visitor --> UC5
    Visitor --> UC6
    UC1 -->|"GET /api/week/:date"| API
    UC3 -->|"GET /api/analysis/:feature"| API
```

*Figure 7.2-1: UI use cases for the single anonymous actor. Only UC-1 and UC-3 issue backend requests; UC-2 reuses the UC-1 response, and UC-4/UC-5/UC-6 require no network calls.*

### 7.2.3 Capabilities Intentionally Not Surfaced in the UI

Two backend capabilities exist as HTTP endpoints but have **no corresponding UI surface**, so they are not exercisable through any screen:

- **Artist search** (`GET /api/artist/<artist>`, Feature F-004) — no component fetches it; it is only *described* textually in the About view.
- **Track history by Spotify ID** (`GET /api/track/<spotify_id>`, Feature F-003) — likewise documented in the About view but never fetched by a component.

Both endpoints are therefore reachable only by a direct HTTP client (browser URL or `curl`), not by any interactive control in the SPA. Additionally, the `avgTempo` value returned by `/api/week` is not rendered anywhere in the Tracks view, and the `valence` and `loudness` audio features stored in the database are not selectable in the Trends feature dropdown (§7.4). These scoping gaps are consistent with the out-of-scope items enumerated in §1.3.

## 7.3 UI / Backend Interaction Boundaries

The UI and backend meet at a single, narrow boundary: the browser issues **synchronous HTTP GET requests** to relative `/api/...` paths and receives JSON, which the components bind into amCharts instances and list markup. This subsection documents that boundary from the UI's perspective; the authoritative, backend-side endpoint catalog and protocol details are in §6.3.2, and the server-side request/aggregation sequences are in §5.2.6.

### 7.3.1 Environment-Dependent Request Routing

Because the SPA always calls **relative** paths (e.g. `fetch('/api/week/2021-11-13')`), the effective destination depends on how the UI is being served:

| Environment | How the UI is served | How `/api/*` resolves |
|---|---|---|
| Development | CRA dev server (`react-scripts start`) | Forwarded to Flask by the `"proxy": "http://localhost:5000"` entry in `frontend/package.json` |
| Production / container | Flask serves the compiled `frontend/build` at `/` | **Same-origin** requests to the Flask process (host port `80` → container `5000`) |

The backend applies `CORS(app)` permissively (`api/__init__.py`), so cross-origin requests are accepted; in practice cross-origin headers matter mainly in the proxied development mode, because production is same-origin (§6.3.4.3).

### 7.3.2 Endpoints Consumed by the UI

Of the six routes exposed by the backend, the UI's interactive components consume only **two**:

| Endpoint | Consuming component | Trigger | Bound into |
|---|---|---|---|
| `GET /api/week/<date>` | `tracks/TracksSection.js` | Mount (`2021-11-13`) and each DatePicker submit | `RadarChart` (`data.averages`) + ranked song list (`data.songs`) |
| `GET /api/analysis/<feature>` | `trends/TrendsSection.js` | Mount (`tempo`) and each FeatureSelect submit | `LineChart` (`data.data`) |

The remaining routes are **outside the UI boundary**: `GET /api/track/<spotify_id>` and `GET /api/artist/<artist>` are never fetched by a component (§7.2.3); `GET /api/` is a redirect helper; and `GET /` is the SPA-shell delivery route that bootstraps the app itself. The About view fetches nothing.

### 7.3.3 Fetch Request / Response Lifecycle

Both data-driven sections implement an identical, self-contained fetch routine (`getData`) with no shared data layer, cache, or retry. The routine resets loading/error state, awaits the response, branches on HTTP status, and then branches on payload:

```javascript
// shared pattern in TracksSection.js / TrendsSection.js
const response = await fetch(`/api/${endpoint}/${param}`);
if (response.status > 299) { setIsLoaded(true); setError(response.statusText); return; }
let data = await response.json();
```

The full client-side lifecycle — including the mount-time load, the loading placeholder, and the two terminal outcomes — is shown below (a complement to the backend-focused sequences in §5.2.6 and §6.3.2.2).

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant C as Section Component
    participant API as Flask API (proxy / same-origin)
    Note over C: Mount useEffect triggers an initial load<br/>(Tracks: 2021-11-13, Trends: tempo)
    U->>C: Submit date / feature (or component mounts)
    C->>C: setIsLoaded(false)#59; setError(false)
    C->>API: fetch('/api/{endpoint}/{param}')
    alt HTTP status > 299
        API-->>C: error status
        C->>C: setError(statusText)#59; setIsLoaded(true)
    else 2xx JSON
        API-->>C: JSON payload
        C->>C: setData(payload)#59; setIsLoaded(true)
    end
    C-->>U: render chart + list, or '. . .' while loading, or error heading
```

*Figure 7.3-1: Client-side fetch lifecycle shared by the Tracks and Trends views.*

### 7.3.4 Error, Loading, and Empty-State Handling

The boundary handling is deliberately minimal and lives entirely in the two section components:

- **Loading:** while `isLoaded` is false, the view renders a `<h1 className='loading'>. . .</h1>` placeholder.
- **HTTP errors:** any response with `status > 299` stores `response.statusText` into `error`, which renders as a `<h1 className='error'>`. The request is **not retried** and the network `fetch` call is not wrapped in `try/catch`, so an outright network rejection is unhandled.
- **Empty results:** the code contains an `if (data.length === 0)` guard intended to show `'No Data Found'`. Because both consumed endpoints return JSON **objects** (`{week, songs, …}` and `{feature, data}`) rather than arrays, `data.length` is `undefined` and this guard does not trigger for them; in practice, a week with no rows surfaces as a backend **HTTP 500** (an empty aggregation raises an unhandled exception, per §5.2.2), which is then reported via `statusText`.

This UI-side behavior is the client half of the error model catalogued in §4.5 and §6.3.3.4.

## 7.4 UI Schemas

The UI works with three categories of schema: the **JSON response envelopes** it fetches from the backend, a **local glossary file** bundled with the build, and the **prop/state schemas** of its React components. The response envelopes are produced by Marshmallow schemas and helper functions on the backend (`api/models.py`, `api/funcs.py`); the shapes below reflect exactly what the components receive and bind.

### 7.4.1 Consumed API Response Schemas

**`GET /api/week/<date>` — Tracks view.** The response is a single object with four keys. Field values below are illustrative, but the keys and structure are exact. Each entry in `songs` carries all 15 fields defined by `TrackSchema.Meta.fields`, while `averages` always contains **exactly five** entries (Energy, Danceability, Speechiness, Acousticness, Instrumentalness) produced by `get_weekly_data`.

```json
{
  "week": "2021-11-13",
  "songs": [
    {
      "id": 1, "week": "2021-11-13", "rank": 1,
      "track": "<track title>", "artist": "<artist name>", "spotify_id": "<spotify id>",
      "energy": 0.62, "danceability": 0.70, "valence": 0.51, "liveness": 0.12,
      "speechiness": 0.08, "acousticness": 0.20, "instrumentalness": 0.0,
      "loudness": -6.2, "tempo": 120.0
    }
  ],
  "averages": [
    { "feature": "Energy", "mean": 62, "full": 100 },
    { "feature": "Danceability", "mean": 70, "full": 100 },
    { "feature": "Speechiness", "mean": 8, "full": 100 },
    { "feature": "Acousticness", "mean": 20, "full": 100 },
    { "feature": "Instrumentalness", "mean": 0, "full": 100 }
  ],
  "avgTempo": 120
}
```

Although 15 fields per song are delivered, the Tracks view **renders only three** — `rank`, `artist`, and `track` — in its scrollable list. The radar chart consumes the `averages` array, mapping `feature` to the category axis, `mean` to the plotted value, and `full` (always `100`) to the background ring on a fixed 0–100 axis. The `avgTempo` value is delivered but not displayed (§7.2.3).

**`GET /api/analysis/<feature>` — Trends view.** The response is an object with the requested feature name and a `data` array. `get_rolling_avg` renames the queried feature column to `value`, appends a `rolling` field (a `.rolling(5)` mean), and **drops the leading rows** whose rolling value is `NaN`.

```json
{
  "feature": "tempo",
  "data": [
    { "year": "1962", "value": 116.4, "rolling": 118.2 },
    { "year": "1963", "value": 119.1, "rolling": 118.9 }
  ]
}
```

The line chart binds `year` to a yearly `DateAxis`, `value` to the "Annual Average" series, and `rolling` to the series labeled "3 Year Rolling Average" — a label that describes a 5-period computation, the documented inconsistency noted in §1.2.3 and §6.3.2.6. Note that only the **seven** features selectable in the UI (§7.4.2) can be requested; `valence` and `loudness` exist in the data model but are not offered by the selector.

### 7.4.2 Local Glossary Schema — `features.json`

The Trends view bundles an audio-feature glossary as a static JSON array required at build time (`frontend/src/components/trends/features.json`). Each element has two keys, and the description key is **misspelled `desctiption`** in both the data file and the component that reads it (they match, so rendering works):

```json
[
  { "title": "Tempo", "desctiption": "The overall estimated tempo of a track in beats per minute (BPM)..." }
]
```

The file contains seven objects — Tempo, Energy, Danceability, Instrumentalness, Liveness, Speechiness, Acousticness — which are exactly the seven options in the `FeatureSelect` dropdown.

### 7.4.3 Component Prop Schemas

Data flows down the component tree as props; callbacks flow up. The observed prop contract for each component is:

| Component | Props (type) | Notes |
|---|---|---|
| `StSidebar` (Sidebar) | `handleClick(fn)`, `activeTab(int)`, `openNav(fn)`, `nav(bool)` | `className` is injected by styled-components |
| `Tab` / `SmallTab` | `onClick(fn)`, `activeTab(bool)`, `id(int)`, `children` | `activeTab` toggles the accent color |
| `Section` | `activeTab(bool)`, `children` | `display:none` when `activeTab` is false |
| `Hamburger` | `showNav(fn)` | Toggles the mobile sidebar |
| `TracksSection` / `TrendsSection` / `AboutSection` | `showNav(fn)` | Forwarded to `Hamburger` |
| `DatePicker` | `initValue(string 'YYYY-MM-DD')`, `submitFunc(fn)` | Controlled input seeded from `initValue` |
| `FeatureSelect` | `submitFunc(fn)`, `initValue(string)` | `initValue` is passed but **not consumed** inside the component |
| `Radar` (RadarChart) | `data` (the `averages` array) | Bound to the amCharts radar |
| `Line` (LineChart) | `data` (the `data.data` array) | Bound to the amCharts XY line chart |

### 7.4.4 Component State Schemas

All UI state is in-memory React state (via `useState`), reset on page reload; there is no client-side persistence, store, or router state.

| Component | State field | Type / Initial value |
|---|---|---|
| `App` | `nav` | `boolean` — `false` (sidebar closed on mobile) |
| `App` | `activeTab` | `integer` — `0` (Tracks) |
| `TracksSection` | `data` | `array`/`object` — `[]`, then the `/api/week` object |
| `TracksSection` | `isLoaded` | `boolean` — `false` |
| `TracksSection` | `error` | `null` \| `string` \| `false` |
| `TrendsSection` | `data`, `isLoaded`, `error` | Same shape as `TracksSection` (default feature `tempo`) |
| `DatePicker` | `inputValue` | `string` — initialized to `initValue` (`'2021-11-13'`) |
| `FeatureSelect` | `inputValue` | `string` \| `undefined` — no initial value; set only on change |

Because `FeatureSelect` initializes `inputValue` with no value and ignores `initValue`, pressing "Go" without changing the dropdown leaves `inputValue` undefined; the parent's `if (inputValue)` guard then suppresses the call (§7.6). The `activeTab` integer notably uses ids `0` (Tracks), `1` (Trends), and `3` (About) — id `2` is intentionally unused (§7.5).

## 7.5 Screens Required

The application is a single HTML document that presents a **persistent shell** (navigation sidebar, mobile title header, and footer) plus **three interchangeable content screens** selected by an in-memory tab index. There is no client-side router: switching screens toggles `display:none` on section wrappers rather than changing the URL (§7.1.1). The screen inventory maps each screen to its tab id, source files, and data source.

| Screen | Tab id | Source files | Data source |
|---|---|---|---|
| Application shell (chrome) | n/a | `src/App.js`, `src/components/navigation/{Sidebar,Tab,SmallTab,Hamburger,Section}.js` | none |
| Tracks (default) | `0` | `src/components/tracks/{TracksSection,DatePicker,RadarChart}.js` | `GET /api/week/<date>` |
| Trends | `1` | `src/components/trends/{TrendsSection,FeatureSelect,LineChart}.js` + `features.json` | `GET /api/analysis/<feature>` |
| About | `3` | `src/components/about/AboutSection.js` | none (static) |

### 7.5.1 Application Shell and Screen-Switching Model

`App.js` composes the shell: a fixed `StSidebar`, a mobile-only title header (`titleContainer mobileHeader`), a content region holding three `Section` wrappers, and a fixed footer showing `AUG | 2021` (a commented-out "Source Code" link sits in the footer markup but is disabled). Each `Section` receives an `activeTab` boolean and hides itself with `display:none` unless it is the selected tab. The composition mirrors the code exactly:

```mermaid
flowchart TB
    App["App shell (div.app)"]
    App --> Sidebar["StSidebar<br/>fixed nav rail / mobile overlay"]
    App --> MobileTitle["Mobile title header 'Hot Stuff'<br/>(hidden at >= 800px)"]
    App --> Content["Content region"]
    App --> Footer["Fixed footer bar: 'AUG | 2021'"]
    Content --> S0["Section activeTab===0 --> TracksSection"]
    Content --> S1["Section activeTab===1 --> TrendsSection"]
    Content --> S3["Section activeTab===3 --> AboutSection"]
```

*Figure 7.5-1: Application shell composition and the three tab-switched content sections (from `App.js`).*

The sidebar (`Sidebar.js`) renders the "Hot Stuff" title and three navigation controls — a `Tab` "Tracks" (id 0), a `Tab` "Trends" (id 1), and a `SmallTab` "About" (id 3). **Tab id 2 is intentionally unused**: there is no control and no `Section` branch for it (consistent with §2.2 F-010 and §5.2.2). On viewports ≥ 800px the sidebar is a persistent 15vw rail; below that it is a 35vw overlay toggled by the hamburger (§7.7).

### 7.5.2 Tracks Screen (Default Landing View)

The Tracks screen is the initial view (`activeTab` defaults to `0`) and is assembled by `TracksSection.js` from three parts inside a `.section` column:

- A `topBar` containing a `DatePicker` (HTML5 `type='date'` input bounded to `min='1958-07-27'` / `max='2021-11-13'`) and a `Hamburger`.
- A **radar chart** (`RadarChart.js`, div `radialChart`, 260px tall) visualizing the week's five feature averages on a 0–100 scale.
- A **scrollable ranked list** (`.scroll`) mapping `data.songs` to `.trackRow` entries that each show `rank`, `artist`, and `track`.

On mount it loads the hard-coded week `2021-11-13` (the dynamic "today" variant is present but commented out), which — together with the DatePicker's `max` bound — fixes the UI to a historical window ending 2021-11-13.

### 7.5.3 Trends Screen

The Trends screen (`activeTab === 1`, `TrendsSection.js`) is assembled from:

- A `topBar` with a `FeatureSelect` dropdown (seven options: tempo, energy, danceability, instrumentalness, liveness, speechiness, acousticness) and a `Hamburger`.
- A **line chart** (`LineChart.js`, div `featureChart`, 260px tall) plotting two series over a yearly `DateAxis`: "Annual Average" and "3 Year Rolling Average".
- An **audio-feature glossary panel** (`.audioFeatures scroll`) that iterates `features.json` and includes an outbound "Source" link to the Spotify Web API audio-features reference.

It loads the `tempo` feature on mount.

### 7.5.4 About Screen

The About screen (`activeTab === 3`, `AboutSection.js`) is a **static, stateless** informational page. Its `topBar` contains only a `Hamburger` (right-aligned via `aboutHeader`). The body describes the Billboard Hot 100, the Flask API and its four `/api/*` endpoints, the React/amCharts front end, and links out to Billboard, Wikipedia, the Spotipy docs, the Spotify audio-features reference, amCharts, and the GitHub source repository. It performs no data fetching and mirrors the content of `README.md` (§6.3.2.6).

## 7.6 User Interactions

All user interactions are client-side and fall into four groups: **navigation**, **data selection** (date/feature submission), **chart inspection**, and **outbound navigation** (external links). The table summarizes every interactive control, its handler, and its effect; the underlying navigation and fetch **state machines** are documented in §4.4 and are not duplicated here.

| Interaction | Control | Handler | Effect |
|---|---|---|---|
| Switch view | `Tab` / `SmallTab` click | `App.handleClick` | Sets `activeTab` to the clicked id if different; also closes the mobile nav |
| Open/close mobile menu | `Hamburger` click | `App.showNav` | Toggles the `nav` boolean (sidebar fades in/out) |
| Choose a week | `DatePicker` date input | `DatePicker.handleChange` | Updates local `inputValue` |
| Load a week | `DatePicker` "Go" submit | `handleSubmit` → `TracksSection.getData` | Fetches `/api/week/<date>` and re-renders radar + list |
| Choose a feature | `FeatureSelect` `<select>` | `FeatureSelect.handleChange` | Updates local `inputValue` |
| Load a feature | `FeatureSelect` "Go" submit | `handleSubmit` → `TrendsSection.getData` | Fetches `/api/analysis/<feature>` and re-renders the line chart |
| Inspect a data point | Hover over a chart | amCharts tooltip / `XYCursor` | Shows the value tooltip / crosshair |
| Open a reference | External hyperlink click | Browser | Opens the target in a new tab (`rel='noopener noreferrer'`) |

### 7.6.1 Navigation and Tab Switching

Clicking a tab invokes `App.handleClick`, which parses the control's numeric `id`, and — only if it differs from the current `activeTab` — updates the active tab and closes the mobile sidebar. The matching `Section` becomes visible while the others remain `display:none`.

```mermaid
flowchart TD
    Click["User clicks a Tab (id 0 / 1 / 3)"] --> Parse["handleClick: index = parseInt(id)"]
    Parse --> Diff{"index !== activeTab?"}
    Diff -->|"yes"| Set["setActiveTab(index); setNav(false)"]
    Diff -->|"no"| Ignore["no state change"]
    Set --> Render["matching Section shows;<br/>other Sections stay display:none"]
```

*Figure 7.6-1: Tab-switch interaction logic in `App.js` (complements the navigation state machine in §4.4).*

### 7.6.2 Mobile Menu Toggle

Each content section renders a `Hamburger` in its top bar and forwards the shared `showNav` callback to it. On narrow viewports the sidebar is hidden (`opacity: 0`) until the hamburger toggles the `nav` state to `true`, fading it in over a 0.5s transition. On viewports ≥ 800px the hamburger is hidden by CSS and the sidebar is always visible, so this toggle is effectively a mobile-only affordance (§7.7).

### 7.6.3 Date Selection (Tracks View)

`DatePicker` is a **controlled** `<input type='date'>` seeded from `initValue` (`'2021-11-13'`). Changing the date updates local state only; pressing **"Go"** calls `handleSubmit`, which prevents the default form submission and — guarded by `if (inputValue)` — invokes the parent's `getData(inputValue)` to fetch that week. The native date picker enforces the `min='1958-07-27'` / `max='2021-11-13'` bounds, so selections are constrained to the supported historical window.

### 7.6.4 Feature Selection (Trends View)

`FeatureSelect` renders a `<select>` of the seven audio features and a "Go" submit button. Changing the selection updates local `inputValue`; submitting invokes the parent's `getData`. Because the component initializes `inputValue` with **no value** and does not read the `initValue` prop it is passed, pressing "Go" *without first changing the dropdown* leaves `inputValue` undefined and the parent's `if (inputValue)` guard suppresses the request. The initial `tempo` chart is therefore driven by `TrendsSection`'s mount-time `getData('tempo')` rather than by the selector (§7.4.4).

### 7.6.5 Chart Inspection

Both charts support hover-based inspection provided by amCharts. In the radar chart, the `mean` series column exposes a tooltip bound to `{mean}`. In the line chart, an `XYCursor` renders dashed X/Y crosshairs that snap to the two series, and a bottom-right `Legend` labels the "Annual Average" and "3 Year Rolling Average" series. These are read-only visual affordances — hovering does not trigger any network activity.

### 7.6.6 Feedback States

During any load the active section shows a `. . .` loading heading; on an HTTP error it shows the response's `statusText` as an error heading. There is no success toast, spinner animation beyond the text placeholder, or retry control. The precise state transitions and the (effectively unreachable) empty-data guard are detailed in §7.3.4.

### 7.6.7 Outbound Navigation

The About view and the Trends glossary contain informational hyperlinks (Billboard, Wikipedia, Spotipy, Spotify audio-features reference, amCharts, GitHub). All open in a new tab and are hardened with `target='_blank'` and `rel='noopener noreferrer'`. These are display-only references; the application makes no runtime API calls to those third parties (§6.3.4).

## 7.7 Visual Design Considerations

The UI applies a **dark, minimalist theme with a single purple accent**, driven by a small set of design tokens centralized as CSS custom properties in `src/styles/index.css`. The tokens are consumed by both the global CSS classes and the styled-components, and the same purple is reused inside the amCharts visualizations, giving the interface a consistent palette across chrome and charts.

### 7.7.1 Color Palette

All colors are defined once on `:root` and referenced through `var(--…)`:

```css
:root { --dark-1:#171717; --dark-2:#262626; --purp:rgb(128,103,220); /* + dark-3, grey, light */ }
```

| Token | Declared Value | Primary Usage |
|---|---|---|
| `--dark-1` | `#171717` | Page/`html` background |
| `--dark-2` | `#262626` | Sidebar background; also the radar "full" background ring (`#262626`) |
| `--dark-3` | `rgba(54,54,54,0.5)` | Input fields, submit buttons, track rows |
| `--grey` | `rgb(189,189,189,0.3)` | Borders and dividers (e.g., title underline) |
| `--light` | `rgb(189,189,189,0.985)` | Primary text and hamburger fill |
| `--purp` | `rgb(128,103,220)` | Accent: active tab, link hover, footer bar, rolling-average line series |

The accent `--purp` (`rgb(128,103,220)`) is the visual signature of the app: it colors the active/hovered tab, the fixed footer bar, link-hover states, and the "3 Year Rolling Average" line in the Trends chart, while the "Annual Average" line uses a darker companion purple (`rgb(68,54,119)`).

### 7.7.2 Typography

The UI loads the Google **Jost** typeface (weights 100–700) via a `preconnect` + stylesheet link in `frontend/public/index.html`, and applies it as the `body` font with `line-height: 1.5` and font smoothing. Type scale (from `index.css`):

- **App/sidebar title "Hot Stuff":** 30px, weight 700, *italic*.
- **Navigation:** `Tab` 25px / `SmallTab` 20px, weight 700, right-aligned.
- **Track rows:** `rank` 25px (weight 500), `artist` 13px (500), `track` 12px (400).
- **Trends glossary:** `featureDescription` 12px.
- **Inputs:** `inputField` 15px (500); `inputBtn` weight 600.

### 7.7.3 Layout and Spatial Structure

The root `.app` container is centered and capped at `max-width: 1200px` across a full `100vw`/`100vh` viewport. Content lives in a `.section` flex column (padded, scrollable) whose height is `calc(85vh - 28px)` on mobile and `calc(100vh - 28px)` on desktop. Two elements are pinned: the **sidebar** (`position: fixed`, `z-index: 2`) and the **footer** (`position: fixed`, bottom, purple bar, `z-index: 2`). Long content regions — the ranked song list, the Trends glossary, and the About body — use the `.scroll` utility (`overflow-y: scroll`) so the shell stays fixed while content scrolls. The charts occupy full-width `div`s fixed at 260px height.

### 7.7.4 Responsive Design

Responsiveness is governed by a **single breakpoint at `min-width: 800px`**, expressed both in `Sidebar.js` (styled-components media query) and in `index.css`:

| Aspect | Mobile (< 800px) | Desktop (≥ 800px) |
|---|---|---|
| Sidebar | 35vw overlay, hidden until toggled (`opacity` 0→1, 0.5s) | Persistent 15vw rail, always visible (`opacity: 1`) |
| Hamburger | Shown (opens the sidebar) | Hidden |
| Title header | Mobile title header shown at top | Hidden (title lives in the sidebar) |
| Content offset | Full width | `margin-left: 15vw` (clears the fixed rail) |
| Section height | `calc(85vh - 28px)` | `calc(100vh - 28px)` |

This yields a persistent-sidebar desktop layout and a hamburger-toggled overlay on narrow screens (§7.6.2), matching Feature F-010 in §2.2.

### 7.7.5 Chart Styling

Both charts use the amCharts **animated theme** and are tuned for the dark background with a light-grey (`rgb(230,230,230)`) applied to axis labels, grids, and cursor lines:

- **Radar (Tracks):** a partial ring (`startAngle -90`, `endAngle 180`, `innerRadius 30%`) with a strict `0–100` value axis; the background "full" columns are `#262626` and the "mean" columns are colored per category index with 5px rounded corners and a `{mean}` tooltip.
- **Line (Trends):** a yearly `DateAxis` (`yyyy`) with smoothed series (`tensionX 0.8`); "Annual Average" is a dashed dark-purple stroke (`rgb(68,54,119)`, `3,3`) and "3 Year Rolling Average" a solid accent-purple stroke (`rgb(128,103,220)`), with a bottom-right legend and dashed `XYCursor` crosshairs.

### 7.7.6 Iconography and Imagery

Iconography is minimal. The only in-app icon is the **hamburger**, drawn inline as an SVG of three rounded rectangles filled with `var(--light)` (`Hamburger.js`). The browser tab icon is `favicon.ico` (present in `public/` and `build/`). The PWA manifest references `logo192.png`/`logo512.png`, but those image assets are **not present** in the repository (§7.1.5), so those manifest icons would not resolve.

### 7.7.7 Accessibility Characteristics (Observed)

The following accessibility-relevant characteristics are observable directly in the source and are reported factually:

- **Present:** the document declares `lang="en"` and a responsive `viewport` meta; a `<noscript>` message is provided for JS-disabled browsers; a `theme-color` meta is set; all external links use `rel="noopener noreferrer"`; inputs and buttons inherit the app font/color.
- **Gaps observed in the code:** the active tab is distinguished by **color alone** (`rgb(128,103,220)`) with no additional state indicator; body text uses a translucent light grey (`rgb(189,189,189,0.985)`) over dark backgrounds; the hamburger is a clickable `<div>`/SVG with **no ARIA role/label** or keyboard handler; there are no custom focus styles beyond browser defaults; and the amCharts visualizations provide no textual data alternative. No automated accessibility testing exists in the repository (there are no tests at all, per §2.5).

## 7.8 References

**Frontend source files examined for this section:**

- `frontend/package.json` - UI dependency versions (React 17, react-scripts 4.0.3, styled-components, @amcharts/amcharts4), scripts, and the dev `proxy`; declared-but-unused axios/plotly/testing-library/web-vitals
- `frontend/public/index.html` - SPA shell, `#root`, title "Hot Stuff", `viewport`/`theme-color` metas, `<noscript>`, and the Google Fonts (Jost) links
- `frontend/public/manifest.json` - PWA manifest (name, standalone display, theme/background colors, icon references)
- `frontend/src/index.js` - React bootstrap (`ReactDOM.render`, `StrictMode`, global CSS import); confirms `reportWebVitals` not wired
- `frontend/src/App.js` - SPA shell, `nav`/`activeTab` state, `handleClick`/`showNav`, three tab-switched `Section`s, footer
- `frontend/src/styles/index.css` - Design tokens (`:root` palette), typography, layout, `.scroll`/`.loading`/`.error` utilities, and the 800px responsive breakpoint
- `frontend/src/components/navigation/Sidebar.js` - Fixed sidebar, tab composition, and the 15vw/35vw responsive media query
- `frontend/src/components/navigation/Tab.js` / `SmallTab.js` - Tab primitives and the `rgb(128,103,220)` active/hover accent
- `frontend/src/components/navigation/Hamburger.js` - SVG hamburger toggle bound to `showNav`
- `frontend/src/components/navigation/Section.js` - `display:none` show/hide wrapper for inactive views
- `frontend/src/components/tracks/TracksSection.js` - Tracks view; `fetch('/api/week/…')`, loading/error handling, radar + ranked list; mount default `2021-11-13`
- `frontend/src/components/tracks/DatePicker.js` - Controlled `type='date'` input bounded `1958-07-27 … 2021-11-13`
- `frontend/src/components/tracks/RadarChart.js` - amCharts `RadarChart` (`radialChart`, 0–100 axis, full/mean series)
- `frontend/src/components/trends/TrendsSection.js` - Trends view; `fetch('/api/analysis/…')`, line chart + glossary; mount default `tempo`
- `frontend/src/components/trends/FeatureSelect.js` - Seven-option feature dropdown; the unconsumed-`initValue` behavior
- `frontend/src/components/trends/LineChart.js` - amCharts `XYChart` (`featureChart`, yearly DateAxis, "Annual Average" + "3 Year Rolling Average" series)
- `frontend/src/components/trends/features.json` - Seven audio-feature definitions; misspelled `desctiption` key
- `frontend/src/components/about/AboutSection.js` - Static About view; endpoint documentation and outbound links

**Backend source files examined (UI data contracts):**

- `api/__init__.py` - `static_folder='../frontend/build'`, `static_url_path='/'`, `CORS(app)`, and the DSN (single-origin delivery + CORS boundary)
- `api/routes.py` - The two UI-consumed routes (`/api/week`, `/api/analysis`) and the endpoint-only/redirect/static routes
- `api/models.py` - `TrackSchema` (15 fields) and `YearlyAvgSchema` that shape the JSON the UI receives
- `api/funcs.py` - `get_weekly_data` (five feature averages + `avgTempo`) and `get_rolling_avg` (`.rolling(5)`) that build the consumed payloads

**Repository folders examined:**

- `frontend/` - The React SPA workspace (manifests, source, public assets, compiled build)
- `frontend/src/` - SPA entry, shell, styles, and components
- `frontend/src/components/navigation/` - Sidebar, Tab, SmallTab, Hamburger, Section
- `frontend/src/components/tracks/` - Tracks view components
- `frontend/src/components/trends/` - Trends view components and glossary
- `frontend/src/components/about/` - About view
- `frontend/public/` - SPA HTML shell, PWA manifest, favicon
- `frontend/build/` - Compiled production assets served by Flask (index.html, hashed JS/CSS chunks)
- `api/` - Flask package producing the JSON the UI consumes

**Cross-referenced Technical Specification sections:**

- 1.2 System Overview - Capabilities and the "3 Year Rolling Average" vs `.rolling(5)` inconsistency
- 1.3 Scope - Out-of-scope UI items (artist/track UI, current-week data, plotly)
- 2.2 Feature Catalog - Features F-006 (SPA delivery), F-007/F-008/F-009/F-010 (UI views + navigation)
- 2.5 Implementation Considerations - Declared-but-unused dependencies; absence of tests
- 4.4 State Management and Transaction Boundaries - Navigation and fetch state machines (not duplicated here)
- 4.5 Error Handling and Recovery Flows - Client/server error model (HTTP 500, statusText)
- 5.2 Component Details - Frontend component responsibilities, chart lifecycle, and backend sequence diagrams
- 6.3 Integration Architecture - Endpoint catalog, protocol, dev-proxy vs same-origin, permissive CORS

**External sources referenced by the repository (not independently retrieved):**

- [web] Google Fonts — `Jost` typeface (`fonts.googleapis.com` / `fonts.gstatic.com`), the UI's primary font (`frontend/public/index.html`)
- [web] Spotify Web API audio-features reference (`developer.spotify.com`) — "Source" link in the Trends glossary and definitions basis for `features.json`
- [web] amCharts (`amcharts.com`) — charting library linked from the About view
- [web] Billboard Hot 100 (`billboard.com/charts/hot-100`), Wikipedia, and Spotipy docs (`spotipy.readthedocs.io/en/2.18.0/`) — informational links in the About view
- [web] GitHub — project source link `github.com/augardiner/hot-100` (About view)

# 8. Infrastructure

## 8.1 Infrastructure Applicability and Overview

### 8.1.1 Applicability Assessment

This system **does require deployment infrastructure**, so the "Detailed Infrastructure Architecture is not applicable" exemption reserved for standalone libraries does not apply here. The repository is a deployable, containerized, two-tier web application — a single Flask process that serves the compiled React single-page application (SPA) and a JSON API, backed by a PostgreSQL 15 database — wired together by a Docker Compose stack (`Dockerfile`, `docker-compose.yml`; consistent with Section 3.6 and Section 6.1.1).

However, the infrastructure that actually exists is deliberately **minimal and single-host**. The repository contains exactly two infrastructure artifacts — a `Dockerfile` and a `docker-compose.yml` — and no cloud provisioning code, no Kubernetes/Helm manifests, no CI/CD pipeline configuration, and no monitoring stack. Accordingly, this section documents the containerization and single-host orchestration that are present in full, and — following the evidence-based "document observed absences rather than aspirations" convention established in Sections 6.1, 6.4, and 6.5 — records the cloud-services, cluster-orchestration, CI/CD, and infrastructure-monitoring capabilities as observed absences with their code evidence rather than fabricating pipelines, providers, or SLAs the repository does not contain.

The table below summarizes the status of each infrastructure area addressed by this section; the referenced subsections expand each with evidence.

| Infrastructure Area | Status in Repository | Primary Evidence |
|---|---|---|
| Containerization | Present | `Dockerfile`, `docker-compose.yml` |
| Orchestration | Docker Compose only (single host) | `docker-compose.yml` (two services) |
| Cloud services | Not used | No cloud SDK/CLI/IaC; local Compose host |
| Infrastructure as Code (host) | Not present | Only `Dockerfile` + `docker-compose.yml` |
| CI/CD pipeline | Not present | No `.github/`, `Jenkinsfile`, or equivalents |
| Infrastructure monitoring | Basic only | `restart: on-failure`; container stderr logs |
| Backup / disaster recovery | Not defined | No backups/RPO/RTO (Section 6.1.4.2) |

### 8.1.2 Infrastructure Architecture

The deployed footprint is a single Docker host running the Docker Engine and Docker Compose, hosting two containers on one Compose-managed network. The `api` container (built from the `Dockerfile`) runs the Flask development server via `python3 app.py`, binding `0.0.0.0:5000` and publishing on host port 80; it serves both the compiled React build at `/` (Flask `static_folder='../frontend/build'`, per `api/__init__.py`) and the `/api/*` routes. The `postgres` container runs the official `postgres:15` image. Two out-of-container actors integrate with the stack: the end-user's browser (which also loads the Google Fonts "Jost" family over HTTPS) and the external, out-of-repository weekly ingestion pipeline that writes chart rows into PostgreSQL (Section 6.1.2.1). Figure 8.1-1 depicts this topology.

```mermaid
flowchart TB
    Browser["Web Browser<br/>React SPA client"]
    Fonts["Google Fonts CDN<br/>fonts.googleapis.com / gstatic.com"]
    Pipeline["External Weekly Ingestion Pipeline<br/>Billboard scrape + Spotipy<br/>(out of repository)"]

    subgraph Host["Single Docker Host — Docker Engine + Docker Compose"]
        direction TB
        RepoMount["Host bind mount .:/app/"]
        DataMount["Host bind mount ./data:/data"]
        subgraph ApiC["api container — built from Dockerfile"]
            Flask["Flask dev server<br/>python3 app.py at 0.0.0.0:5000"]
            SPA["Compiled React build served at /"]
        end
        subgraph DbC["postgres container"]
            PG[("postgres:15<br/>database 'db' on 5432")]
        end
    end

    Browser -->|"HTTP host port 80 to container 5000"| Flask
    Browser -.->|"HTTPS font load, no SRI"| Fonts
    Flask --> SPA
    Flask -->|"SQLAlchemy/psycopg2 via Compose DNS 'postgres'"| PG
    RepoMount -.-> Flask
    DataMount -.-> PG
    Pipeline -->|"weekly batch writes"| PG
```

**Figure 8.1-1: Infrastructure Architecture — Single-Host Docker Compose Topology.** Solid arrows are runtime request/query paths; dashed arrows are the host bind mounts and the browser's third-party font load. The external ingestion pipeline is the only writer to PostgreSQL and is not part of this repository.

### 8.1.3 Scalability, Maintenance, and Security Framing

Three cross-cutting properties bound every choice documented in this section and are stated once here to avoid repetition:

- **Scalability.** The topology is single-instance and scales only vertically (more host CPU/RAM); horizontal scale-out is not configured because the container runs the single-process Flask development server, there is no load balancer, and `docker-compose.yml` declares no replicas (Section 6.1.3).
- **Maintenance.** All lifecycle operations are manual `docker compose` commands (build, up, logs, restart); there is no automation layer beyond the Docker `restart: on-failure` policy on the `api` service (Section 6.5.4.3).
- **Security consistency.** The infrastructure inherits the security posture documented in Section 6.4: hard-coded PostgreSQL credentials committed to version control, a container that runs as `root`, plain-HTTP transport (no TLS in the repository), a fully permissive `CORS(app)`, and a published PostgreSQL port (`5432`) that exposes the data tier to the host. These are referenced — not re-litigated — wherever they intersect an infrastructure choice below.

## 8.2 Deployment Environment

The deployment environment is a single self-hosted Docker host. The repository does not target any specific hosting provider or platform; it defines a portable container stack that can run on any host with the Docker Engine and Docker Compose installed. This subsection assesses that target environment and how it is managed.

### 8.2.1 Target Environment Assessment

**Environment type.** The environment is **environment-agnostic and self-hosted** (neither cloud- nor on-premises-specific). Nothing in the repository binds the stack to a particular cloud, on-premises datacenter, hybrid, or multi-cloud arrangement: there is no cloud provider configuration, and the database DSN targets the local Compose service name `postgres` (`api/__init__.py`). The stack therefore runs identically on a developer workstation, an on-premises virtual machine, or a single cloud VM, but the repository itself specifies none of these. The observed configuration is **development-oriented** — `.flaskenv` sets `FLASK_ENV=development`, and the container `CMD` runs the Flask development server (`python3 app.py`) rather than the pinned `gunicorn` (Section 3.6.3).

**Geographic distribution.** There is **no geographic distribution**. The stack is a single instance on a single host in a single location; there is no multi-region deployment, no content delivery network for application content, no geo-routing, and no edge presence. The only externally hosted asset is the browser-loaded Google Fonts "Jost" family over HTTPS (Section 6.4.4.4), which is incidental to the client, not a distribution strategy for the application.

**Resource requirements.** The repository **declares no resource envelope** — `docker-compose.yml` contains no `deploy.resources` CPU/memory limits or reservations, and there is no worker-count tuning because the runtime is a single-process development server (Section 6.1.3.2). Resource needs are therefore bounded structurally by the observed footprint rather than by declared limits. The table below states each dimension as observed; detailed sizing and cost guidance appear in Section 8.8.

| Resource Dimension | Declared in Repository? | Observed Footprint / Guidance |
|---|---|---|
| Compute (CPU) | No | One dev-server process + one PostgreSQL 15 instance; modest single-host CPU (Section 8.8) |
| Memory | No | In-process pandas aggregation per request; no cache (Section 8.8) |
| Storage | No | Frozen dataset (~1958-07-27 to 2021-11-13), well under 1 GB; images pulled at build (Section 8.8) |
| Network | Ports 80 and 5432 published | Low bandwidth; single host; see Figure 8.2-1 |

**Compliance and regulatory requirements.** **None are triggered.** The system stores and serves only public Billboard/Spotify reference data with no PII, user accounts, credentials, or regulated data, so GDPR/CCPA, PCI-DSS, and HIPAA impose no active obligations (Section 6.4.5.3). The only compliance considerations are the third-party data-usage terms (Billboard and Spotify), which bind the external, out-of-repository ingestion pipeline that acquires the data, not this read-only serving stack.

**Network topology.** Figure 8.2-1 shows the network layout: the browser reaches the `api` service through published host port 80 (forwarded to container port 5000), and the two services communicate over the default Compose bridge network using service-name DNS. Notably, the `postgres` service also publishes port `5432` to the host, exposing the data tier directly to the host network in addition to the private Compose network (a boundary observation carried forward from Section 6.4.1.4).

```mermaid
flowchart TB
    Client["Web Browser / HTTP client<br/>(untrusted network)"]

    subgraph HostNet["Docker Host Network"]
        P80["Published host port 80"]
        P5432["Published host port 5432"]
        subgraph Compose["Default Compose bridge network"]
            Api["api service<br/>listens 0.0.0.0:5000"]
            Db[("postgres service<br/>listens 5432")]
        end
    end

    Client -->|"HTTP port 80"| P80
    Client -.->|"direct DB access, port 5432 exposed"| P5432
    P80 -->|"forwards to container 5000"| Api
    P5432 --> Db
    Api -->|"Compose DNS host 'postgres' 5432"| Db
```

**Figure 8.2-1: Network Architecture — Published Ports and Compose Bridge Network.** The dashed path marks the directly reachable published PostgreSQL port; solid paths are the normal HTTP ingress and the internal service-to-service link.

| Host Port | Container Port | Service | Note |
|---|---|---|---|
| 80 | 5000 | `api` | HTTP ingress serving SPA + `/api/*`; single public entry point |
| 5432 | 5432 | `postgres` | PostgreSQL wire protocol; published to host, exposing the data tier (Section 6.4.1.4) |

### 8.2.2 Environment Management

**Infrastructure as Code (IaC) approach.** The only IaC in the repository is the **container definition itself**: the `Dockerfile` (image build recipe) and `docker-compose.yml` (declarative two-service topology). There is no host- or cloud-provisioning IaC — no Terraform, CloudFormation, Pulumi, Ansible, or equivalent — so provisioning the underlying host (installing Docker, opening ports, attaching storage) is a manual, undocumented prerequisite. Within its scope, Compose provides declarative, reproducible container topology; outside it, there is no codified infrastructure.

**Configuration management strategy.** Configuration is **minimal and largely static**, spread across three locations, and is not managed by any configuration-management tool:

| Configuration Item | Source | Value / Note |
|---|---|---|
| Flask runtime mode | `.flaskenv` | `FLASK_APP=app.py`, `FLASK_ENV=development` (dev mode) |
| Database credentials/name | `docker-compose.yml` env | `POSTGRES_USER/PASSWORD=postgres`, `POSTGRES_DB=db` (plaintext) |
| Database connection string | `api/__init__.py` (hard-coded) | `postgresql://postgres:postgres@postgres/db` — not read from env |
| `api` service env | `docker-compose.yml` | `NODE_OPTIONS=--openssl-legacy-provider` (vestigial Node flag) |

A precise, evidence-based caveat applies: although `python-dotenv` is a declared dependency and `.gitignore` excludes `.env.local*`, the connection string in `api/__init__.py` is a hard-coded literal and `import os` is unused, so the credential cannot be overridden by environment or `.env` file without editing source (Section 6.4.4.2). There is no externalized secrets management (Section 8.1.3).

**Environment promotion strategy (dev/staging/prod).** There is **no environment promotion strategy**. The repository defines a single environment: one `docker-compose.yml` with no environment-specific overrides (no `docker-compose.override.yml`, no `docker-compose.prod.yml`), and `.flaskenv` fixes the runtime to `development`. There is no separate development, staging, and production configuration, and — because there is no CI/CD pipeline (Section 8.6) — no mechanism to promote a build between environments. A deployment is whatever a `docker compose up --build` produces on the target host.

**Backup and disaster recovery plans.** There are **no backup or disaster-recovery plans**, consistent with Section 6.1.4.2 and Section 6.5.4.3. Key evidence-based facts:

- **No backups/snapshots and no defined RPO/RTO** exist anywhere in the repository.
- **Single PostgreSQL instance**, with no replication, standby, or clustering.
- **Volume durability is not guaranteed by the declared mapping**: the `postgres` service bind-mounts `./data:/data`, but the `postgres:15` image stores data in `/var/lib/postgresql/data` by default and no `PGDATA` override is set, so the mount does not map the database's actual data directory. The top-level named volume `data` is declared but referenced by no service.
- **Recovery of data depends entirely on re-running the external, out-of-repository weekly ingestion pipeline** to repopulate the `Tracks` and `YearlyAvg` tables, because the repository contains no schema-creation, migration, seed, or repair routine (Section 6.1.4.2, Section 6.5.4.3).

The only automated resilience mechanism at the environment level is the `restart: on-failure` policy on the `api` service, which recovers from a process crash but performs no data protection (Section 6.1.4.1).

## 8.3 Cloud Services

**Cloud services are not used by this system, and this subsection is therefore not applicable.**

The repository contains no evidence of any cloud provider adoption:

- **No cloud provider configuration or IaC** of any kind is present — there are no Terraform, CloudFormation, Serverless Framework, `.aws/`, `.ebextensions/`, `app.yaml`, `render.yaml`, `fly.toml`, `heroku.yml`, `netlify.toml`, or `vercel.json` files anywhere in the tree.
- **No managed-service SDKs** appear in `requirements.txt` — there is no `boto3` (AWS), `google-cloud-*` (GCP), or `azure-*` (Azure) dependency. The declared dependencies are limited to the Flask/SQLAlchemy web stack and pandas/numpy (Section 3.3).
- **The datastore is self-hosted, not a managed cloud database.** The connection string in `api/__init__.py` targets the local Docker Compose service name `postgres` (`postgresql://postgres:postgres@postgres/db`), and `docker-compose.yml` runs the database from the community `postgres:15` image — not a managed offering such as Amazon RDS, Cloud SQL, or Azure Database.

The only externally hosted network dependencies observed are (1) the browser-side Google Fonts stylesheet/font load over HTTPS (Section 6.4.4.4) and (2) the Spotify Web API consumed by the **external, out-of-repository** weekly ingestion pipeline (Section 3.4). Neither represents cloud infrastructure operated by this system. Because the stack is environment-agnostic and self-hosted (Section 8.2.1), a cloud VM is one *possible* host, but the repository specifies and depends on no cloud service, so provider selection, managed-service versions, high-availability design, cloud cost optimization, and cloud security posture do not apply.

## 8.4 Containerization

Containerization is the core of this system's infrastructure. Both tiers run as containers, defined by a single `Dockerfile` (the `api` image) and a pulled community image (`postgres:15`), wired together by `docker-compose.yml`.

### 8.4.1 Container Platform Selection

The container platform is **Docker Engine** with **Docker Compose** as the composition tool; `docker-compose.yml` declares Compose file format `version: "3"`. Images are built and run through the Docker CLI/daemon and conform to the OCI image format. No alternative container runtime (for example, Podman, containerd directly, or a build tool such as Buildah/Kaniko) is referenced. The selection is appropriate to the observed scope: a two-service stack on a single host (Section 8.2.1).

### 8.4.2 Base Image Strategy

Two base images are used, one per tier:

| Service | Base Image | Role and Notes |
|---|---|---|
| `api` | `python:3.11-slim-buster` | Slim Debian "buster" variant with Python 3.11; build-time `apt-get install libpq-dev gcc` supports compiling `psycopg2` |
| `postgres` | `postgres:15` | Official PostgreSQL 15 image pulled directly; no custom build layer |

The `api` image starts from the **slim** Python variant to reduce base size, and it adds only the toolchain needed to build the PostgreSQL client bindings (`libpq-dev`, `gcc`). An evidence-based caveat: the `-buster` suffix pins the base to Debian 10, an older release line, which is relevant to the supply-chain/security discussion in Section 8.4.5. The database tier performs no image customization — it consumes the upstream `postgres:15` image as-is.

### 8.4.3 Image Versioning Approach

There is **no formal image versioning or distribution scheme**:

- The `api` image is produced by `build: .` in `docker-compose.yml` with **no `image:` name or tag assigned**, so Compose auto-names a local image and no explicit version label is attached.
- There is **no container registry** in use; images are built locally on the target host and are never pushed or pulled from a registry (consistent with the absence of any CI/CD publishing step, Section 8.6).
- **Base-image version pinning is partial**: `postgres:15` pins the major version while floating minor/patch; `python:3.11-slim-buster` pins the Python minor version and the Debian codename while floating the patch level. **No image digests** (`@sha256:...`) are pinned, so builds are not byte-for-byte reproducible.
- **Application versioning** exists only on the frontend (`frontend/package.json` declares `version: 0.1.0`); the `api` image and the API surface carry no version identifier.

### 8.4.4 Build Optimization Techniques

The `Dockerfile` applies one deliberate optimization and exhibits several non-optimizations that are documented here as observed facts:

**Optimization present:**
- **Dependency-layer caching.** `requirements.txt` is copied and `pip3 install`-ed *before* `COPY . .`, so the (expensive) dependency-install layer is cached and reused across application source changes.
- **Reduced build context.** `.dockerignore` excludes `/frontend/node_modules`, `/venv`, and `/data`, trimming the context sent to the daemon.

**Non-optimizations / observed characteristics:**
- **Single-stage build.** There is no multi-stage build; the build toolchain (`gcc`, `libpq-dev`) remains in the final image, enlarging it and widening the attack surface.
- **No layer cleanup.** The `apt-get update && install` step does not remove `/var/lib/apt/lists`, leaving package metadata in the image layer.
- **Runtime source overlay.** `docker-compose.yml` bind-mounts `.:/app/` over the image's copied code, meaning the running container executes the host working tree rather than the immutable image contents — a development convenience, not a production build pattern (Section 3.6.3).
- **Frontend is not built in the image.** The Docker build does not compile the React client; the pre-built SPA under `frontend/build/` is committed to the repository and enters the image via `COPY . .`, then is served by Flask as static files (Section 3.6). Rebuilding the UI is a separate, manual, out-of-container step.

### 8.4.5 Security Scanning Requirements

**No image security scanning is present or required by the repository.** There is no evidence of any vulnerability scanner (for example, Trivy, Grype, Snyk, or Docker Scout), and — because there is no CI/CD pipeline (Section 8.6) — no automated gate that could run such a scan. The container security posture, carried forward from Section 6.4, is:

- **Container runs as root.** The `Dockerfile` sets no `USER`, so the Flask process runs with UID 0 inside the container (Section 6.4.1.3).
- **Aging base layer.** The `python:3.11-slim-buster` base sits on Debian 10 "buster," so unscanned OS-package vulnerabilities are a latent supply-chain risk (Section 8.4.2).
- **Dependency reproducibility without gating.** `requirements.txt` pins exact versions (Section 3.3), which aids reproducibility, but no tool verifies those pins against known-vulnerability databases.

Any image scanning, non-root hardening, or base-image currency policy would need to be introduced as new capability; none exists today.

## 8.5 Orchestration

Orchestration is limited to **Docker Compose on a single host**. A dedicated cluster orchestrator is not used and, at the observed scope, is not required; this subsection documents what Compose provides and the orchestration capabilities that are deliberately absent.

### 8.5.1 Orchestration Platform Selection

The orchestration platform is **Docker Compose** (`docker-compose.yml`, format `version: "3"`). No cluster orchestrator or scheduler is present: there are **no Kubernetes manifests or Helm charts, no Docker Swarm stack, no HashiCorp Nomad, and no cloud scheduler** (for example, ECS/Fargate) anywhere in the repository. Compose is used purely to define and co-launch the two services (`api`, `postgres`) as a local application stack.

### 8.5.2 Cluster Architecture

There is **no cluster**. The architecture is a **single Docker host** running exactly two containers attached to Compose's default bridge network, where service-name DNS (`postgres`) resolves the database for the `api` container (Section 8.2.1, Figure 8.2-1). There is no multi-node topology, no control-plane/worker separation, no scheduling across nodes, and no service mesh. The "topology" is fully described by the two service definitions and their single network.

### 8.5.3 Service Deployment Strategy

Deployment is **manual and recreate-in-place**, driven by the Compose CLI:

| Aspect | Mechanism | Note |
|---|---|---|
| Launch/rebuild | `docker compose up --build` | Manual command; builds `api` and starts both services (Section 3.6.2) |
| Start ordering | `depends_on: [postgres]` on `api` | Controls start *order* only, not database readiness |
| Restart behavior | `restart: on-failure` on `api` | Restarts the app on non-zero exit; no policy set on `postgres` |
| UI coupling | Committed `frontend/build/` served by `api` | No separate frontend deploy step (Section 8.4.4) |

There is **no advanced deployment strategy** — no blue-green, canary, or rolling update, because there is a single replica and no orchestrator to coordinate a phased rollout. Applying a change means recreating the container(s) in place, which implies a brief service interruption. Because `depends_on` waits for the container to start rather than for PostgreSQL to accept connections, first-request timing after a cold start depends on the database being ready (Section 6.1.4.1).

### 8.5.4 Auto-Scaling Configuration

**No auto-scaling is configured, and none is possible with the current definition.** `docker-compose.yml` declares no `deploy.replicas`, there is no horizontal pod/instance autoscaler, and no metric-driven scaling trigger exists. The system scales **vertically only** — by giving the single host more CPU/memory (Section 6.1.3). A structural ceiling reinforces this: the `api` container runs the single-threaded Flask development server (`python3 app.py`) rather than the multi-worker `gunicorn`, so request concurrency is bounded by one process regardless of host size (Section 6.1.3.2, Section 3.6.3).

### 8.5.5 Resource Allocation Policies

**No resource allocation policies are defined.** `docker-compose.yml` sets no `deploy.resources` limits or reservations for either service, so neither container has CPU or memory constraints and both may consume whatever the host makes available; scheduling is simply "run on this host." The `postgres` service runs with the upstream image's default resource behavior and default configuration (no tuned `shared_buffers`, `work_mem`, or connection limits are provided). Consequently, resource governance is entirely a property of the host environment, not of the orchestration definition (Section 6.1.3.2). Guidance for sizing the host appears in Section 8.8.

## 8.6 CI/CD Pipeline

**There is no automated CI/CD pipeline in this repository.** The project is hosted on GitHub (`main` plus several automation branches) but contains **no continuous-integration or continuous-deployment configuration** of any kind — no `.github/workflows/`, GitLab CI, CircleCI, Jenkinsfile, Travis, Azure Pipelines, AWS `buildspec.yml`, or Google `cloudbuild.yaml` (Section 3.6.4). Building and deploying are therefore **manual, operator-driven** activities. This subsection documents the de-facto build and deployment flow that a person performs by hand, since that flow occupies the role a pipeline would otherwise fill.

### 8.6.1 Build Pipeline

The "build pipeline" is a sequence of manual steps rather than an automated system:

| Pipeline Concern | Observed Reality | Evidence |
|---|---|---|
| Source control triggers | None automated; commits/pushes trigger no build | No CI config in repo (Section 3.6.4) |
| Build environment | Local Docker Engine + Compose; Node/npm out-of-band for the UI | `Dockerfile`, `docker-compose.yml`, `frontend/package.json` |
| Dependency management | Pinned `pip` `requirements.txt`; pinned npm `package-lock.json` | Section 3.3 |
| Artifact generation/storage | Local untagged `api` image + git-committed `frontend/build/` | Sections 8.4.3, 8.4.4 |
| Quality gates | None — no lint/test/scan gate is wired | Sections 6.6, 8.4.5 |

Key evidence-based details:

- **Source control triggers.** No event (push, pull request, tag) initiates any build, because no CI runner is configured.
- **Build environment requirements.** The backend image builds inside Docker from `python:3.11-slim-buster`. The frontend is **not** built by Docker; regenerating `frontend/build/` requires a separate Node/npm environment running `react-scripts` `4.0.3` (`npm run build`), performed manually before committing (Section 8.4.4).
- **Dependency management.** Backend dependencies are installed from the exact-pinned `requirements.txt` during the image build (`pip3 install -r requirements.txt`); frontend dependencies are locked by `package-lock.json`. There is no automated dependency update or audit step.
- **Artifact generation and storage.** The build produces a **local, untagged `api` image** that is never pushed to a registry, and the SPA "artifact" is the **`frontend/build/` bundle committed directly to git** (Section 8.4.3). There is no artifact repository, versioned release bundle, or image registry.
- **Quality gates.** No quality gate exists. The frontend toolchain includes a `test` script (React Testing Library via `react-scripts`), but it is not connected to any enforced gate, and the backend has no test suite (Section 6.6).

The following diagram depicts the manual build-to-run workflow:

```mermaid
flowchart TD
    Dev["Developer workstation"]

    subgraph Local["Manual local steps"]
        FE["npm run build<br/>React to frontend/build/"]
        Commit["git commit and push<br/>build artifacts included"]
    end

    Host["Target Docker host"]

    subgraph Runtime["docker compose up --build"]
        BuildApi["Build api image<br/>python:3.11-slim-buster"]
        PullDb["Pull postgres:15"]
        Run["Start api + postgres containers"]
    end

    Dev --> FE
    FE --> Commit
    Commit --> Host
    Host --> BuildApi
    Host --> PullDb
    BuildApi --> Run
    PullDb --> Run
```

**Figure 8.6-1: Manual Build and Deployment Workflow.** No automated trigger connects the commit to the host; an operator performs each transition by hand.

### 8.6.2 Deployment Pipeline

Deployment is equally manual and mirrors the orchestration behavior described in Section 8.5.3:

- **Deployment strategy.** A single **recreate-in-place** deployment via `docker compose up --build`; there is no blue-green, canary, or rolling strategy, and no load balancer or second replica to enable one (Section 8.5.3).
- **Environment promotion workflow.** None. There is a single environment fixed to `FLASK_ENV=development`, with no dev→staging→prod promotion path and no environment-specific Compose overrides (Section 8.2.2).
- **Rollback procedures.** There is no automated rollback and no versioned artifact to roll back to. In practice, reverting means checking out an earlier git commit and rebuilding by hand (the git history — initial commit → About/readme → mobile responsiveness → "Make Run in 2023" — is the only version record).
- **Post-deployment validation.** None automated. There is no health-check, readiness probe, or smoke test; the `api` service has no `healthcheck` block, and `depends_on` only orders container start (Sections 6.5, 8.5.3).
- **Release management process.** No formal release process, versioning scheme, or changelog exists; a "release" is simply the current state of `main` running on the host.

Because the system collapses dev, staging, and production into one manually-run environment, the "environment promotion flow" is effectively a single node with no downstream promotion targets, as shown below:

```mermaid
flowchart LR
    Code["Source commit<br/>main branch"]
    Single["Single environment<br/>docker compose up --build<br/>FLASK_ENV=development"]
    NoStaging["Staging environment<br/>not defined"]
    NoProd["Production environment<br/>not defined"]

    Code --> Single
    Single -.->|"no promotion path"| NoStaging
    Single -.->|"no promotion path"| NoProd
```

**Figure 8.6-2: Environment Promotion Flow.** Solid path is the only realized deployment; dashed paths mark promotion targets that the repository does not define.

## 8.7 Infrastructure Monitoring

**Dedicated infrastructure monitoring is not implemented.** Consistent with Section 6.5 (which concludes that "Detailed Monitoring Architecture is not applicable" for this system), the repository contains no monitoring, metrics, tracing, alerting, or dashboard tooling. The only observability affordances are the Docker restart policy and the container's incidental standard-error logs. The table summarizes each monitoring dimension the prompt requires; the paragraphs that follow give the evidence.

| Monitoring Dimension | Status | Mechanism / Note |
|---|---|---|
| Resource monitoring | Not implemented | Ad hoc `docker stats` / `docker logs` only; `restart: on-failure` reaction |
| Performance metrics | Not implemented | No metrics endpoint or APM; `web-vitals` declared but unused |
| Cost monitoring | Not applicable | Self-hosted; no cloud billing (see Section 8.8) |
| Security monitoring | Not implemented | No audit/IDS; no auth events exist (Section 6.4) |
| Compliance auditing | Not required / not implemented | Public data, no PII (Section 6.4.5.3) |

**Resource monitoring approach.** There is no resource-monitoring stack — no metrics agent, exporter, `cAdvisor`, or time-series database, and no `docker-compose.yml` healthcheck. An operator's only visibility is ad hoc use of Docker's built-in commands (`docker stats`, `docker logs`) against the host. The single automated reaction to failure is `restart: on-failure` on the `api` service, which restarts the process on a non-zero exit but observes nothing else and does not cover the `postgres` service (Sections 6.5.4.1, 8.5.3).

**Performance metrics collection.** No performance metrics are collected. The backend exposes no metrics or profiling endpoint and records no request latency or throughput; the routes contain no timing instrumentation (Section 6.5). On the client, `web-vitals` is a declared dependency in `frontend/package.json`, but it is not wired to any reporting sink, so no Core Web Vitals data is gathered (Section 6.5).

**Cost monitoring and optimization.** Cloud-style cost monitoring is **not applicable** because the system is self-hosted and incurs no cloud billing to observe (Section 8.3). The economic footprint is the fixed cost of one host plus operator time; there is no cost-management tool, budget alert, or rightsizing automation. Cost estimates and sizing guidance are consolidated in Section 8.8.

**Security monitoring.** There is no security monitoring — no audit logging, intrusion detection, access logging, or anomaly alerting. This aligns with the security posture in Section 6.4: the application has no authentication or authorization, so there are no auth or access-control events to record in the first place. The only security-relevant signal is whatever appears incidentally in the container's standard-error stream, retrievable via `docker logs` (Section 6.5.4.2).

**Compliance auditing.** Compliance auditing is **neither required nor implemented**. Because the system handles only public reference data with no PII (Section 6.4.5.3), no regulatory audit trail is mandated, and none is produced — there is no immutable audit log, change-tracking, or evidence-collection mechanism in the repository.

Introducing any of these capabilities — metrics/exporters, an APM, alerting, audit logging, or a healthcheck — would require net-new components; none is present today.

## 8.8 Infrastructure Cost Estimates, Resource Sizing, and External Dependencies

Because the repository declares no resource envelope (Section 8.2.1) and specifies no host or provider (Section 8.3), this subsection consolidates **guidance-level** sizing and **evidence-based** cost and dependency facts. Sizing values are derived from the observed workload — a single-process web tier and a small, frozen dataset — and are explicitly labeled as guidance rather than values found in the code.

### 8.8.1 Resource Sizing Guidelines

The workload is bounded by two observed facts. First, the dataset is **frozen** to the historical Billboard window `1958-07-27` through `2021-11-13` (`frontend/src/components/tracks/DatePicker.js`), which is roughly 63 years, i.e. on the order of ~3,300 weekly charts of up to 100 songs each — approximately **~330,000 `Tracks` rows** and only **~64 `YearlyAvg` rows** (Section 6.5). Second, the `api` tier is a **single-process Flask development server** (Section 8.5.4), and per-request work is small: weekly reads return ~100 rows, artist search is an `ILIKE` scan, and analysis reads the ~64-row `YearlyAvg` table (`api/routes.py`).

The following minimums are guidance for a single host that runs both containers comfortably; none of these values appears in the repository:

| Resource | Suggested Minimum (Guidance) | Rationale |
|---|---|---|
| CPU | 1–2 vCPU | Single-threaded dev server; light per-request pandas/SQL work |
| Memory | 2 GB host (≈512 MB–1 GB `api`, ≈256–512 MB `postgres`) | Flask + SQLAlchemy + pandas/numpy in-process; small DB working set |
| Storage | ~5–10 GB disk | Base images + `<1 GB` dataset + committed `frontend/build/` |
| Network | 1 published HTTP port (80); low bandwidth | Small JSON payloads; single host (Figure 8.2-1) |

Because scaling is vertical-only (Section 8.5.4), growth is served by giving the single host more CPU/RAM rather than by adding instances; the single-process server remains the concurrency ceiling regardless of host size.

### 8.8.2 Infrastructure Cost Estimates

The repository fixes **no cloud spend**: every managed cost category is `$0` because the corresponding capability is absent, which is an evidence-based conclusion rather than an estimate.

| Cost Element | Repository-Determined Cost | Basis |
|---|---|---|
| Cloud managed services | $0 | No cloud usage (Section 8.3) |
| Container registry | $0 | No registry; local images only (Section 8.4.3) |
| CI/CD compute | $0 | No pipeline (Section 8.6) |
| Monitoring / observability | $0 | No tooling (Section 8.7) |
| TLS certificate / domain | $0 | Plain HTTP; none configured (Section 6.4) |
| Database hosting | $0 incremental | Self-hosted `postgres:15` container on the same host |
| Compute host | Not specified by repository | Single small host; see illustrative note below |

The only real cost driver is the **single compute host** plus operator time. Since the repository names no provider, no exact figure can be grounded in the code; as an *illustrative order of magnitude* (not from the repository), the sizing in Section 8.8.1 corresponds to a small single VM at the low end of common cloud instance pricing, or effectively `$0` incremental if run on existing developer hardware. Cost optimization is therefore trivial and structural: the design already avoids managed-service, registry, pipeline, and monitoring charges by not using any of them.

### 8.8.3 External Dependencies

The stack depends on the following external artifacts and services, separated by whether they are consumed by *this* system or by the out-of-repository ingestion pipeline:

| Dependency | Category | Consumption Note |
|---|---|---|
| Docker Engine + Compose | Host runtime prerequisite | Not provisioned by the repo (Section 8.2.2) |
| `python:3.11-slim-buster` | Base image (build-time) | Pulled from public registry (Section 8.4.2) |
| `postgres:15` | Base image (runtime) | Pulled from public registry (Section 8.4.2) |
| Debian apt packages (`libpq-dev`, `gcc`) | OS packages (build-time) | Installed during `api` image build |
| PyPI packages | Backend libraries (build-time) | Exact-pinned in `requirements.txt` (Section 3.3) |
| npm packages | Frontend libraries (build, out-of-container) | Locked by `package-lock.json` (Section 8.4.4) |
| Google Fonts ("Jost") | Runtime, browser-side | HTTPS from Google CDN (Section 6.4.4.4) |
| Spotify Web API | External ingestion only | Out-of-repo pipeline via Spotipy; not this stack (Section 3.4) |
| Billboard chart data | External ingestion only | Out-of-repo pipeline; not this stack (Section 3.4) |

An important boundary: the Spotify and Billboard dependencies are **not** runtime dependencies of the deployed stack. The repository serves a pre-populated database, and the acquisition of that data is performed by a separate, out-of-repository weekly pipeline (Section 3.4); a running instance functions with no network access to those providers.

### 8.8.4 Maintenance Procedures

All maintenance is manual and host-local, consistent with the absence of CI/CD (Section 8.6) and monitoring (Section 8.7):

- **Data refresh.** Updating chart data requires running the external ingestion pipeline to repopulate `Tracks`/`YearlyAvg`, then restarting the stack; the repository contains no in-app data-load or migration routine (Section 8.2.2).
- **Dependency and base-image updates.** Bumping a Python package (`requirements.txt`), a base image (`Dockerfile`), or a frontend package (`package.json`) is a manual edit followed by `docker compose up --build`; there is no automated patching, and the `-buster` base is on an aging Debian line (Section 8.4.5).
- **Log inspection and recovery.** Operational visibility is limited to `docker logs`/`docker stats` (Section 8.7). There are no backups, so data recovery depends on re-running the external pipeline (Section 8.2.2).
- **Downtime expectation.** Because deployment is recreate-in-place with a single replica (Section 8.5.3), routine maintenance implies a brief service interruption during rebuild/restart.

## 8.9 References

The following repository artifacts and technical-specification sections were examined as evidence for Section 8.

**Files examined**

- `Dockerfile` - Single-stage `api` image build (`python:3.11-slim-buster`, `libpq-dev`/`gcc`, `EXPOSE 5000`, `CMD python3 app.py`); grounds base-image strategy, build optimization, root-user, and dev-server findings.
- `docker-compose.yml` - Two-service topology (`api`, `postgres:15`), port publishing (`80:5000`, `5432:5432`), `restart: on-failure`, `depends_on`, bind mounts, and the unused named volume; grounds orchestration, network, and backup/DR findings.
- `.dockerignore` - Build-context exclusions (`/frontend/node_modules`, `/venv`, `/data`); grounds build optimization.
- `.flaskenv` - `FLASK_APP=app.py`, `FLASK_ENV=development`; grounds environment-type and configuration-management findings.
- `.gitignore` - Confirms `frontend/build/` is committed (build ignores commented out); grounds artifact-storage findings.
- `app.py` - Flask entry point (`app.run(host='0.0.0.0')`); grounds the dev-server runtime.
- `requirements.txt` - Exact-pinned backend dependencies (including `gunicorn` and `python-dotenv`); grounds dependency management and the dev-server-vs-gunicorn note.
- `README.md` - Project purpose and the external weekly ingestion pipeline; grounds external-dependency boundaries.
- `api/__init__.py` - Hard-coded DSN, `static_folder='../frontend/build'`, permissive `CORS`; grounds configuration-management and security-posture references.
- `api/routes.py` - Six read-oriented routes; grounds per-request workload for sizing.
- `frontend/package.json` - `top-100` v0.1.0, `react-scripts` build/test scripts, `web-vitals`; grounds frontend build and monitoring references.
- `frontend/src/components/tracks/DatePicker.js` - Date bounds `1958-07-27`–`2021-11-13`; grounds the frozen-dataset scale used for sizing.

**Folders examined**

- `api/` - Flask backend package (bootstrap, models, routes, helpers).
- `frontend/` - React client (manifests, source, public assets, committed build output).
- `frontend/build/` - Pre-built SPA artifacts committed to the repository and served by Flask.

**Cross-referenced specification sections**

- `3.3 Open Source Dependencies` - Pinned PyPI/npm dependency set.
- `3.4 Third-Party Services` - Spotify/Billboard as external-ingestion dependencies.
- `3.6 Development & Deployment` - Docker Compose stack, absence of CI/CD, committed frontend build, dev-server CMD.
- `6.1 Core Services Architecture` - Vertical-scaling-only, single Postgres, PGDATA mismatch, no backups/RPO/RTO.
- `6.4 Security Architecture` - Hard-coded credentials, root container, plain HTTP, permissive CORS, exposed `5432`, no PII/regulatory triggers.
- `6.5 Monitoring and Observability` - "Not applicable" monitoring posture, `restart: on-failure`, unused `web-vitals`, frozen dataset.
- `6.6 Testing Strategy` - Absence of a backend test suite and enforced quality gates.

# 9. Appendices

## 9.1 Additional Technical Information

Sections 1 through 8 document this system's requirements, technology stack, workflows, architecture, backend/data design, UI, and infrastructure in depth. This appendix does not introduce new architecture; it **consolidates supplementary reference material** (a single repository map, a unified configuration/runtime reference, and an audio-feature coverage matrix) and records a small number of **residual technical details** — grounded in direct inspection of the repository — that complement the earlier sections. All findings are consistent with the technology choices already established: a **Flask** backend, a **Create React App (React 17)** single-page application, **PostgreSQL 15**, and a two-service **Docker Compose** stack.

### 9.1.1 Repository Directory Inventory

The repository is small and is organized into three parts: a set of root-level launcher/manifest/configuration files, the `api/` Flask backend package (four modules), and the `frontend/` Create React App workspace. The complete source layout (excluding `.git/`, `frontend/node_modules/`, and the compiled `static/` asset bundle within `build/`) is shown below.

```text
hot-stuff/
├── app.py                     # Flask launcher: app.run(host='0.0.0.0')
├── requirements.txt           # 23 pinned Python dependencies
├── Dockerfile                 # python:3.11-slim-buster image build
├── docker-compose.yml         # api + postgres:15 services (Compose v3)
├── .dockerignore              # excludes /frontend/node_modules, /venv, /data
├── .flaskenv                  # FLASK_APP, FLASK_ENV
├── .gitignore                 # VCS ignore rules (frontend/build NOT ignored)
├── README.md                  # project overview + endpoint summary
├── api/                       # Flask backend package
│   ├── __init__.py            # app bootstrap, CORS, DSN, SQLAlchemy/Marshmallow
│   ├── models.py              # Tracks, YearlyAvg ORM models + Marshmallow schemas
│   ├── routes.py              # six HTTP GET routes
│   └── funcs.py               # date normalization + pandas aggregation helpers
└── frontend/                  # React (CRA) client workspace
    ├── package.json           # dependencies, scripts, dev proxy
    ├── package-lock.json      # locked dependency graph
    ├── public/                # index.html, manifest.json, favicon.ico
    ├── src/                   # application source
    │   ├── index.js           # React bootstrap (React.StrictMode)
    │   ├── App.js             # SPA shell + navigation state (useState)
    │   ├── styles/index.css   # global theme, layout, responsive rules
    │   └── components/
    │       ├── navigation/    # Sidebar, Tab, SmallTab, Section, Hamburger
    │       ├── tracks/        # TracksSection, DatePicker, RadarChart
    │       ├── trends/        # TrendsSection, FeatureSelect, LineChart, features.json
    │       └── about/         # AboutSection
    └── build/                 # committed, pre-built SPA (index.html,
                               # manifest.json, asset-manifest.json, static/)
```

Two inventory characteristics are worth highlighting because they affect how the project is built and served:

- **The compiled frontend build is committed to the repository.** `.gitignore` leaves the `frontend/build` entry commented out, so the pre-built SPA (`frontend/build/index.html`, `manifest.json`, `asset-manifest.json`, and the hashed `static/css` and `static/js` bundles) is checked in and is what Flask serves in a container run — the image build does not rebuild the frontend.
- **The bundled `static/js` set includes an `xlsx` chunk.** The committed build contains an `xlsx*.chunk.js` bundle pulled in transitively by `@amcharts/amcharts4` (its export/data-processing capability), even though no application source file under `frontend/src/` imports `xlsx` directly.

### 9.1.2 Consolidated Configuration and Runtime Reference

This subsection gathers, in one place, the environment variables, network bindings, and runtime configuration that are otherwise distributed across the deployment manifests and the backend bootstrap. The environment variables actually declared in the repository are:

| Variable | Value | Source File | Purpose |
|---|---|---|---|
| `FLASK_APP` | `app.py` | `.flaskenv` | Entry module for the `flask` CLI |
| `FLASK_ENV` | `development` | `.flaskenv` | Selects Flask development mode |
| `NODE_OPTIONS` | `--openssl-legacy-provider` | `docker-compose.yml` (`api`) | Node/OpenSSL compatibility flag required by `react-scripts` 4 builds on modern Node |
| `POSTGRES_USER` | `postgres` | `docker-compose.yml` (`postgres`) | Database superuser account created by the image |
| `POSTGRES_PASSWORD` | `postgres` | `docker-compose.yml` (`postgres`) | Database password (hard-coded) |
| `POSTGRES_DB` | `db` | `docker-compose.yml` (`postgres`) | Name of the initial database |

Database connectivity is **not** read from the environment: `api/__init__.py` hard-codes the connection string `postgresql://postgres:postgres@postgres/db` into `SQLALCHEMY_DATABASE_URI`, sets `SQLALCHEMY_TRACK_MODIFICATIONS = False`, and — although it imports `os` and `python-dotenv` is installed — never resolves the credentials or host from a variable, so the DSN can only be changed by editing source.

The network bindings exposed by the Compose stack are:

| Service | Host Port | Container Port | Notes |
|---|---|---|---|
| `api` | 80 | 5000 | Flask dev server binds `0.0.0.0:5000` (`app.run`); `Dockerfile` declares `EXPOSE 5000` |
| `postgres` | 5432 | 5432 | PostgreSQL published directly to the Docker host |

During local development the Create React App dev server proxies unmatched `/api/*` requests to `http://localhost:5000` via the `"proxy"` entry in `frontend/package.json`; in a container run the same relative paths are served same-origin because Flask hosts the compiled SPA from `static_folder='../frontend/build'` at `static_url_path='/'`.

### 9.1.3 In-App Audio-Feature Description Source and Coverage

The Trends view's "Audio Features" explanatory panel is driven by a small data file, `frontend/src/components/trends/features.json`, which the `TrendsSection` component imports and renders. This file is the repository's own in-application glossary of the Spotify audio features (its definitions are the authoritative source used verbatim in Section 9.2). Two implementation details are relevant:

- **Key spelling.** Every object in `features.json` uses the keys `"title"` and `"desctiption"` — the second is a consistent misspelling of "description." Because the component reads that exact key, the text renders correctly; the typo is a code-level naming quirk rather than a runtime defect.
- **Partial coverage.** `features.json` describes only **seven** features — Tempo, Energy, Danceability, Instrumentalness, Liveness, Speechiness, and Acousticness — and the Trends feature-selector dropdown (`FeatureSelect`) offers exactly this same seven-item set. The `Tracks` model, however, stores **nine** audio features. The two that have neither an in-app definition nor a UI selector are **valence** and **loudness**.

The matrix below reconciles where each of the nine audio features appears across the persistence layer and the UI, consolidating facts otherwise spread across the data-design and UI sections:

| Audio Feature | In `tracks` Model | In `yearly_avg` Model | Selectable in Trends UI |
|---|---|---|---|
| tempo | Yes | Yes | Yes |
| energy | Yes | Yes | Yes |
| danceability | Yes | Yes | Yes |
| valence | Yes | Yes | No |
| liveness | Yes | Yes | Yes |
| speechiness | Yes | Yes | Yes |
| acousticness | Yes | Yes | Yes |
| instrumentalness | Yes | Yes | Yes |
| loudness | Yes | No | No |

Two consequences follow directly from the matrix. First, **`valence` is fully trend-able** (it is stored in both models and `YearlyAvgSchema` serializes it), yet the UI never exposes it because it is absent from both `features.json` and the dropdown. Second, **`loudness` cannot be trended at all**: it exists only on `tracks`, is omitted from `yearly_avg`/`YearlyAvgSchema`, and is not offered in the UI. Separately, the weekly radar chart aggregates a still-narrower set — the `get_weekly_data` helper computes means for only **five** features (energy, danceability, speechiness, acousticness, instrumentalness) plus a separate average tempo, so valence, liveness, and loudness are excluded from the weekly radar view.

### 9.1.4 Supplementary Build and Tooling Configuration

The following build/tooling details from `frontend/package.json` and the ignore files complete the reference and were not enumerated verbatim elsewhere.

**npm scripts** (Create React App plus one convenience script):

| Script | Command | Purpose |
|---|---|---|
| `start` | `react-scripts start` | Launches the CRA development server |
| `start-api` | `cd .. && venv/bin/flask run --no-debugger` | Boots the Flask backend from the repository root |
| `build` | `react-scripts build` | Produces the optimized production bundle |
| `test` | `react-scripts test` | Jest test runner (no test files exist in the repository) |
| `eject` | `react-scripts eject` | Ejects the CRA build configuration |

**Browser support targets** (`browserslist`): the production query is `>0.2%`, `not dead`, `not op_mini all`; the development query is `last 1 chrome version`, `last 1 firefox version`, `last 1 safari version`. **Linting** is delegated to CRA via the `eslintConfig` block, which extends `react-app` and `react-app/jest`.

**Ignore rules** governing image builds and version control:

- `.dockerignore` excludes `/frontend/node_modules`, `/venv`, and `/data` from the Docker build context.
- `.gitignore` excludes `node_modules`, `/.pnp`, `/coverage`, `.DS_Store`, the `.env.local` family of dotenv files, npm/yarn debug logs, `*_old.*`, `__pycache__`, `venv`, and `/data`. Notably, its `frontend/build` rule is commented out, which is why the compiled SPA (Section 9.1.1) is version-controlled.

## 9.2 Glossary

This glossary defines the domain and technical terms used throughout the specification. Definitions are grounded in repository evidence: the audio-feature meanings are taken from the application's own in-app catalog (`frontend/src/components/trends/features.json`), and the remaining terms reflect the concrete usage observed in the code and configuration.

**Domain and Music-Data Terms**

| Term | Definition |
|---|---|
| Acousticness | An audio feature expressed as a 0.0–1.0 confidence measure of whether a track is acoustic (1.0 = high confidence acoustic), per `features.json`. |
| amCharts (amCharts 4) | The JavaScript charting library (`@amcharts/amcharts4`) used to render both the Tracks radar chart and the Trends line chart. |
| Audio feature | A numeric attribute describing the sound or character of a track (originally from Spotify), stored per song on the `Tracks` model and pre-aggregated per year on `YearlyAvg`; the schema holds nine such features. |
| Billboard Hot 100 | The United States music-industry standard weekly record chart for songs, published by Billboard; rankings derive from sales (physical and digital), radio play, and online streaming (`README.md`). |
| Chart week | The Saturday-aligned week label (in `YYYY-MM-DD` form) that identifies a weekly chart; the `get_query_week` helper normalizes any input date to the applicable Saturday. |
| Danceability | An audio feature (0.0–1.0) describing how suitable a track is for dancing, derived from tempo, rhythm stability, beat strength, and regularity, per `features.json`. |
| Energy | An audio feature (0.0–1.0) representing a perceptual measure of intensity and activity — energetic tracks feel fast, loud, and noisy — per `features.json`. |
| External ingestion pipeline | The out-of-repository weekly script (a Billboard scrape enriched with Spotify audio features) that populates the database; described in `README.md` but not present in this repository. |
| Instrumentalness | An audio feature predicting whether a track contains no vocals; values approaching 1.0 indicate greater likelihood of no vocal content (values above 0.5 are treated as instrumental), per `features.json`. |
| Line chart | The amCharts XY chart on the Trends view that plots a feature's annual average and rolling-average series over time (`LineChart.js`). |
| Liveness | An audio feature detecting the presence of an audience in the recording; higher values indicate a greater probability the track was performed live (above 0.8 = strongly live), per `features.json`. |
| Loudness | An audio-feature column stored on `Tracks` only (absent from `YearlyAvg` and from the Trends UI); it has no definition in `features.json`. Per Spotify's audio-feature model it represents a track's overall loudness in decibels. |
| Radar chart | The partial-ring amCharts visualization on the Tracks view that plots the week's mean audio-feature values against a fixed 0–100 baseline (`RadarChart.js`). |
| Rank | A song's chart position for a given week (stored as `Tracks.rank`), used as the default ascending sort key for weekly and per-track queries. |
| Rolling average | A moving mean over a sliding window of consecutive yearly values; `get_rolling_avg` computes a five-period window (`.rolling(5)`), although the README and the Trends legend label the series a "3 Year Rolling Average" — a documented naming inconsistency. |
| Speechiness | An audio feature detecting the presence of spoken words; higher values indicate more speech-like content (above 0.66 ≈ all speech; 0.33–0.66 ≈ mixed, including rap), per `features.json`. |
| Spotify Web API | The external service from which audio features originate; consumed only by the external ingestion pipeline and never called at runtime by this application. |
| Spotipy | A Python client library for the Spotify Web API, cited in `README.md` as the tool the external weekly script uses to fetch audio features; it is not a dependency of this repository. |
| Tempo | An audio feature giving the overall estimated tempo (speed/pace) of a track in beats per minute (BPM), per `features.json`. |
| Valence | An audio-feature column stored on both `Tracks` and `YearlyAvg` but absent from `features.json` and from the Trends selector; per Spotify's audio-feature model it describes the musical positiveness a track conveys. |
| Yearly average (pre-aggregation) | A per-year mean of each audio feature stored in the `YearlyAvg` table by the external pipeline, letting the analysis endpoint read pre-computed rows instead of scanning all of `tracks`. |

**Technical and Architectural Terms**

| Term | Definition |
|---|---|
| Architecture Decision Record (ADR) | A concise record of an architectural decision, its supporting evidence, and its consequences; the specification catalogs ADR-01 through ADR-08 in Section 5.3. |
| Bind mount | A host directory mapped directly into a container; the whole repository is bind-mounted at `.:/app/` on the `api` service and `./data:/data` on the `postgres` service. |
| Cross-Origin Resource Sharing (CORS) | The browser-advisory access policy enabled permissively via `CORS(app)` in `api/__init__.py`, exercised chiefly by the development proxy. |
| Create React App (CRA) | The React application toolchain (`react-scripts` 4.0.3) that scaffolds, runs, tests, and builds the frontend. |
| Data Source Name (DSN) | The database connection string `postgresql://postgres:postgres@postgres/db` configured as `SQLALCHEMY_DATABASE_URI` in `api/__init__.py`. |
| Denormalized / pre-aggregated table | A summary table (`YearlyAvg`) holding per-year means, trading extra storage for cheap trend reads; it is logically derived from `Tracks` with no enforced foreign key. |
| Development proxy | The CRA `"proxy": "http://localhost:5000"` setting in `frontend/package.json` that forwards unmatched `/api/*` requests to the Flask backend during development. |
| Docker Compose | The Compose v3 orchestration file (`docker-compose.yml`) that defines and runs the `api` and `postgres` services together on a single host. |
| Fetch API | The browser-native HTTP client the SPA uses to call the backend (`fetch('/api/...')`); the declared `axios` dependency is unused. |
| Flask development server | The single-process Werkzeug server started by `app.run(host='0.0.0.0')`, which is the container's actual runtime (the pinned `gunicorn` is not wired in). |
| Marshmallow schema | A serialization definition (`TrackSchema`, `YearlyAvgSchema`) whose `Meta.fields` tuple controls exactly which model columns are emitted as JSON. |
| Named volume | A Docker-managed storage volume; a top-level `data` volume is declared in `docker-compose.yml` but is not referenced by any service. |
| Object-Relational Mapping (ORM) | The SQLAlchemy layer that maps the `Tracks` and `YearlyAvg` Python classes to PostgreSQL tables and generates SQL from query expressions. |
| Progressive Web App (PWA) | An installable web-app experience described by `frontend/public/manifest.json` (name "Hot Stuff", `display: standalone`). |
| React hooks | The `useState` and `useEffect` functions the React components use for local state management and on-mount data fetching. |
| React StrictMode | The development-time wrapper applied in `frontend/src/index.js` that enables additional runtime checks across the component tree. |
| Same-origin delivery | The pattern in which one Flask process serves both the JSON API (`/api/*`) and the compiled SPA (`/`) from a single origin, via `static_folder='../frontend/build'`. |
| Sargable query | A query predicate capable of using an index; the artist search uses a leading-wildcard `LIKE '%...%'`, which is non-sargable. |
| Single-page application (SPA) | The React client that renders all views (Tracks, Trends, About) in the browser without full-page reloads, served from Flask's static folder. |
| styled-components | The CSS-in-JS library used to style the navigation primitives (`Sidebar`, `Tab`, `SmallTab`, `Section`). |
| WSGI server | A production-grade Python Web Server Gateway Interface server; `gunicorn` is pinned in `requirements.txt` for this role but is not invoked by the container command. |

## 9.3 Acronyms

The following table expands the acronyms and initialisms that appear across this specification. Terms drawn from the implemented system (for example, `CORS`, `CRA`, `DSN`, `ORM`, `SPA`, `WSGI`) sit alongside terms that appear in the comparative and cross-cutting discussions of the Security, Database, and Infrastructure sections (for example, the compliance and transport-security initialisms), even where the corresponding capability is documented as not implemented in this repository.

| Acronym | Expanded Form |
|---|---|
| ADR | Architecture Decision Record |
| API | Application Programming Interface |
| BPM | Beats Per Minute |
| CCPA | California Consumer Privacy Act |
| CDN | Content Delivery Network |
| CI/CD | Continuous Integration / Continuous Deployment |
| CORS | Cross-Origin Resource Sharing |
| CPU | Central Processing Unit |
| CRA | Create React App |
| CSP | Content Security Policy |
| CSS | Cascading Style Sheets |
| DB | Database |
| DDL | Data Definition Language |
| DNS | Domain Name System |
| DOM | Document Object Model |
| DSN | Data Source Name |
| GDPR | General Data Protection Regulation |
| HA | High Availability |
| HIPAA | Health Insurance Portability and Accountability Act |
| HSM | Hardware Security Module |
| HSTS | HTTP Strict Transport Security |
| HTTP | Hypertext Transfer Protocol |
| HTTPS | Hypertext Transfer Protocol Secure |
| IaC | Infrastructure as Code |
| IdP | Identity Provider |
| JS | JavaScript |
| JSON | JavaScript Object Notation |
| JWT | JSON Web Token |
| KMS | Key Management Service |
| KPI | Key Performance Indicator |
| LTS | Long-Term Support |
| MFA | Multi-Factor Authentication |
| OAuth | Open Authorization |
| ORM | Object-Relational Mapping |
| PCI-DSS | Payment Card Industry Data Security Standard |
| PEP | Policy Enforcement Point |
| PII | Personally Identifiable Information |
| PWA | Progressive Web App |
| RAM | Random-Access Memory |
| RBAC | Role-Based Access Control |
| REST | Representational State Transfer |
| RLS | Row-Level Security |
| RPC | Remote Procedure Call |
| RPO | Recovery Point Objective |
| RTO | Recovery Time Objective |
| SLA | Service-Level Agreement |
| SOC | Service Organization Control |
| SPA | Single-Page Application |
| SQL | Structured Query Language |
| SRI | Subresource Integrity |
| SSL | Secure Sockets Layer |
| TLS | Transport Layer Security |
| TOTP | Time-based One-Time Password |
| TTL | Time To Live |
| URL | Uniform Resource Locator |
| VCS | Version Control System |
| WAL | Write-Ahead Logging |
| WSGI | Web Server Gateway Interface |
| XSS | Cross-Site Scripting |

## 9.4 References

The following repository artifacts and previously written specification sections were examined as direct evidence for the content of this Appendices section.

**Repository Files**

- `README.md` - Established the Billboard Hot 100 domain description, the external weekly ingestion narrative (Billboard scrape enriched via Spotipy), and the "3 Year Rolling Average" wording.
- `requirements.txt` - Confirmed the pinned Python dependencies, including the presence of `gunicorn` and the absence of `spotipy` and any scraping libraries.
- `Dockerfile` - Confirmed the container build steps referenced in the configuration and tooling summary.
- `docker-compose.yml` - Established the `api` and `postgres` service definitions, port mappings, environment variables, bind mounts, the unused named `data` volume, and the hardcoded DSN.
- `.dockerignore` - Established build-context exclusion rules cited in the supplementary tooling subsection.
- `.flaskenv` - Established `FLASK_APP=app.py` and `FLASK_ENV=development`.
- `app.py` - Confirmed the `app.run(host='0.0.0.0')` development-server entrypoint.
- `api/__init__.py` - Established `CORS(app)`, the `SQLALCHEMY_DATABASE_URI` DSN, and the `static_folder='../frontend/build'` same-origin delivery.
- `api/models.py` - Established the `Tracks` and `YearlyAvg` ORM models and the audio-feature column coverage (including valence on both tables and loudness on `Tracks` only).
- `api/routes.py` - Established the six Flask endpoints and which are consumed by the UI.
- `api/funcs.py` - Established `get_query_week` (Saturday alignment), `get_rolling_avg` (`.rolling(5)`), and `get_weekly_data` feature scaling.
- `frontend/package.json` - Established the JavaScript dependency versions, the `"proxy"` development setting, the npm scripts, browserslist targets, and the `top-100` / `0.1.0` identity.
- `frontend/public/manifest.json` - Established the PWA manifest (name "Hot Stuff", `display: standalone`, theme/background colors).
- `frontend/src/index.js` - Established the `React.StrictMode` wrapper.
- `frontend/src/components/trends/features.json` - Authoritative source for the seven in-app audio-feature definitions and the `desctiption` key spelling.
- `frontend/src/components/trends/LineChart.js` - Established the Trends line chart and its `featureChart` container.
- `frontend/src/components/tracks/RadarChart.js` - Established the Tracks radar chart and its `radialChart` container.

**Repository Folders**

- `api/` - The Flask backend package (application factory, models, routes, helpers).
- `frontend/` - The Create React App workspace (client source, public assets, committed build).
- `frontend/src/components/` - The React component tree (navigation, tracks, trends, about).
- `frontend/build/` - The committed production build served as static content by Flask.

**Cross-Referenced Technical Specification Sections**

- `1.2 System Overview` - Corroborated the two-tier single-origin web-application framing and domain scope.
- `3.2 Frameworks & Libraries` - Aligned framework/library terminology (Flask, React, SQLAlchemy, amCharts, styled-components).
- `5.1 High-Level Architecture` - Aligned architectural terminology used in the glossary.
- `5.3 Technical Decisions` - Source of the ADR concept (ADR-01 through ADR-08) referenced in the glossary and acronyms.
- `6.2 Database Design` - Source of database terminology (DDL, WAL, denormalization, sargability) used in the glossary and acronyms.
- `6.4 Security Architecture` - Source of the security and compliance acronyms enumerated in Section 9.3, including capabilities documented as not implemented.
- `7.1 Core UI Technologies` - Aligned UI terminology (SPA, CRA, hooks, StrictMode, charting).
- `8.1 Infrastructure Applicability and Overview` - Aligned infrastructure and orchestration terminology and the source of several infrastructure acronyms.

