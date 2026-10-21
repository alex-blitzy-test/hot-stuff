# Technical Specification

# 1. Introduction

## 1.1 EXECUTIVE SUMMARY

### 1.1.1 Project Overview

Hot Stuff (repository identifier `hot-stuff`, frontend package identifier `top-100`) is a single-page web application that visualizes the Billboard Hot 100 weekly singles chart enriched with Spotify Audio Features. The system pairs a Python/Flask REST API with a React 17 single-page application (SPA), backed by a PostgreSQL 15 database, and is delivered as a two-service Docker Compose deployment. The application surfaces three primary user experiences—weekly track inspection, longitudinal feature trend analysis, and an in-application documentation page—through a sidebar-driven tab navigation model.

### 1.1.2 Core Business Problem

Raw Billboard Hot 100 rankings, while authoritative as a popularity signal, expose neither the musicological characteristics of charting tracks nor how those characteristics evolve over decades of recorded popular music. Hot Stuff addresses this gap by joining weekly chart positions with quantitative audio features (tempo, energy, danceability, valence, liveness, speechiness, acousticness, instrumentalness, and loudness) and presenting them through interactive visualizations. The system answers questions such as "what does this week's chart sound like?" and "how has danceability or tempo trended across the entire history of the Hot 100?"—analytical questions that the Billboard chart alone cannot satisfy.

### 1.1.3 Key Stakeholders and Users

The application is configured as a public, unauthenticated web property. No authentication module, role-based access control, multi-tenancy boundary, or rate-limiting middleware is present in the codebase, and CORS is enabled globally without origin restrictions in `api/__init__.py`. The user surface is therefore homogeneous, with every visitor receiving identical capabilities.

| Stakeholder Group | Interaction Mode | Primary Interface |
|---|---|---|
| End users (music enthusiasts, listeners, researchers) | Browse chart data and visualizations | React SPA (Tracks, Trends, About tabs) |
| Project maintainer | Operates the deployment and external ingestion | Docker Compose stack and external scraper script |
| Read-only data consumers | Direct API calls | Flask JSON endpoints under `/api/` |

### 1.1.4 Value Proposition

The expected business value is delivered along three dimensions: (1) **discoverability**—users can browse any historical chart week through a date picker and inspect the audio fingerprint of that week; (2) **insight**—users can isolate a single audio feature and observe both its annual mean and a multi-year rolling average across the chart's full history; and (3) **education**—the in-application About section explains the methodology, reproducing the project's data lineage and visualization rationale.

---

## 1.2 SYSTEM OVERVIEW

### 1.2.1 Project Context

#### Business and Market Positioning

Hot Stuff is a domain-specific data-visualization application positioned at the intersection of music journalism, music information retrieval, and chart analytics. It is a single-purpose product (no companion mobile app, no white-label SDK, no B2B integration surface) whose footer copyright marker reads `AUG | 2021`, indicating a project authored and published in mid-2021. The source repository is referenced from within the application at `https://github.com/augardiner/hot-100`.

#### Current System Limitations

This codebase does not replace a predecessor system; it is greenfield within its repository. However, several internal limitations are visible in the retrieved code and should inform any future evolution:

| Limitation | Location | Implication |
|---|---|---|
| Database credentials hardcoded | `api/__init__.py` (`postgresql://postgres:postgres@postgres/db`) | No environment-variable override; deployment-time secrets are not externalized |
| Database hostname coupled to Compose | `api/__init__.py` (host `postgres`) | Non-Docker execution requires source modification |
| Tracks view fixed to a hardcoded date | `frontend/src/components/tracks/TracksSection.js` line 37 (`getData('2021-11-13')`) | The dynamic `new Date()` call exists but is commented out |
| Documentation discrepancies | README and About tab cite "3-year" rolling average, but `api/funcs.py` uses `.rolling(5)` | Five-year window is the actual behavior |
| WSGI server discrepancy | `gunicorn` declared in `requirements.txt`; `Dockerfile` runs `python3 app.py` | Production traffic is served by Flask's development server |

#### Integration with the Existing Enterprise Landscape

The system has two implicit external dependencies that are referenced in the in-application About section and the README, but whose code is **not present in this repository**:

1. **A weekly Billboard Hot 100 scraper** that ingests chart data and persists rows to the `Tracks` table.
2. **A Spotify API client (referenced as Spotipy)** that enriches each track with audio features using the track's `spotify_id`.

The repository therefore represents the *read-side* of a pipeline; the *write-side* (ETL) is operated externally and is assumed to populate the `Tracks` and `YearlyAvg` tables out of band.

### 1.2.2 High-Level Description

#### Primary System Capabilities

| Capability | Surface | Backing Logic |
|---|---|---|
| Weekly chart inspection with audio-feature radar | Tracks tab (amCharts radar) | `GET /api/week/<YYYY-MM-DD>` returning entries plus computed averages |
| Single-track historical lookup | Tracks tab detail | `GET /api/track/<spotify_id>` returning all chart appearances |
| Longitudinal feature trend with rolling average | Trends tab (amCharts line) | `GET /api/analysis/<feature>` returning yearly mean and 5-year rolling mean |
| Artist search (case-insensitive partial match) | API consumer | `GET /api/artist/<artist>` |
| Default route redirect to current chart week | API entry | `GET /api/` redirecting to the computed current week |
| Static SPA delivery | Browser | `GET /` serving `frontend/build/index.html` |

#### Major System Components

```mermaid
graph TB
    User[End User Browser]

    subgraph DockerHost["Docker Compose Host"]
        subgraph ApiContainer["api service (port 80:5000)"]
            Flask[Flask 2.0.1 Application<br/>app.py / api/__init__.py]
            Routes[Routes Module<br/>api/routes.py]
            Models[ORM Models<br/>api/models.py]
            Funcs[Helper Functions<br/>api/funcs.py]
            StaticAssets[React Production Build<br/>frontend/build/]
            Flask --> Routes
            Routes --> Models
            Routes --> Funcs
            Flask --> StaticAssets
        end

        subgraph DbContainer["postgres service (port 5432:5432)"]
            DB[(PostgreSQL 15<br/>db: tracks, yearly_avg)]
        end

        Models -- SQLAlchemy 1.4.19 --> DB
    end

    subgraph External["External / Out of Repository Scope"]
        Scraper[Weekly Billboard Scraper<br/>not in repo]
        Spotify[Spotify Web API<br/>via Spotipy, not in repo]
    end

    User -- HTTP / fetch --> Flask
    Scraper -- writes weekly rows --> DB
    Scraper -- reads audio features --> Spotify
```

#### Core Technical Approach

The backend is bootstrapped in `api/__init__.py`, which constructs a Flask application configured with `static_folder='../frontend/build'` and `static_url_path='/'`. This single-process model means the same Flask instance both serves the compiled React assets and answers JSON API requests under `/api/`. Three Flask extensions are wired during initialization: `Flask-SQLAlchemy` (as `db`), `flask-marshmallow` (as `ma`), and `Flask-Cors` (as `CORS(app)` with no origin restriction). `SQLALCHEMY_TRACK_MODIFICATIONS` is explicitly set to `False`.

The data model is intentionally minimal:

| Table | Role | Cardinality |
|---|---|---|
| `Tracks` | One row per (week, rank) chart entry, enriched with Spotify audio features | High volume; weekly-growing |
| `YearlyAvg` | Pre-aggregated annual average for each audio feature | One row per year |

Marshmallow schemas (`TrackSchema`, `YearlyAvgSchema`) define API response shapes, decoupling JSON serialization from ORM definitions.

Helper functions in `api/funcs.py` provide:

- `get_query_week(date)` — Normalizes any date input to its corresponding chart week boundary (Saturday), with a 10:00 AM cutoff branch on Wednesdays.
- `get_rolling_avg(data)` — Computes a 5-year rolling mean using `pandas.DataFrame.rolling(5).mean()`.
- `get_weekly_data(data)` — Computes per-week averages, scaling proportional features (energy, danceability, speechiness, acousticness, instrumentalness) by 100 and casting tempo to integer.

The frontend is a Create React App project (`react-scripts` 4.0.3) using React 17.0.2. Charting is handled by `@amcharts/amcharts4` (radar chart on the Tracks tab, line chart on the Trends tab). Navigation primitives in `frontend/src/components/navigation/` (Sidebar, Tab, SmallTab, Hamburger, Section) are styled with `styled-components`. The development build proxies API requests to `http://localhost:5000`; the production build is emitted to `frontend/build/` and served directly by Flask.

### 1.2.3 Success Criteria

#### Measurable Objectives

| Objective | Indicator | Source of Truth |
|---|---|---|
| Render any valid chart week's top entries on demand | `/api/week/<YYYY-MM-DD>` returns serialized track list and computed averages | `api/routes.py` lines 35–45 |
| Surface audio feature trends across the chart's history | `/api/analysis/<feature>` returns annual mean and rolling mean | `api/routes.py` lines 60–69 |
| Deliver a navigable SPA with at least three sections | `App.js` mounts Tracks, Trends, About tabs | `frontend/src/App.js` |
| Run as a self-contained two-container stack | `docker compose up` starts `api` and `postgres` services | `docker-compose.yml` |

#### Critical Success Factors

1. **Data freshness depends on the external scraper**, which must run on a weekly cadence to keep the `Tracks` table current.
2. **Spotify enrichment must be performed prior to insertion** because the API surface presents audio features as first-class fields and the frontend visualizations assume their presence.
3. **The compiled React build must exist at `frontend/build/`** at container start time, otherwise the `/` route will fail to serve `index.html`.

#### Key Performance Indicators

The repository does not include observability instrumentation (no `web-vitals` reporting wiring, no APM agent, no logging framework configuration). The `web-vitals` 1.0.1 dependency is declared in `frontend/package.json` from the CRA template but is not actively reported. Therefore, KPIs in scope for this specification are functional rather than runtime metrics:

| KPI Category | Metric | Target Behavior |
|---|---|---|
| Functional correctness | All six routes return 2xx for valid inputs | Verified via manual testing |
| Visual fidelity | Radar and line charts render without error in modern browsers | Verified via Tracks and Trends tabs |
| Deployability | `docker compose up` produces a working stack | Verified via the documented Compose file |

---

## 1.3 SCOPE

### 1.3.1 In-Scope Elements

#### Core Features and Functionalities

The following capabilities are present in the repository and constitute the must-have set delivered by this specification:

| Capability Group | Specific Features |
|---|---|
| API endpoints | Static SPA serving (`/`), current-week redirect (`/api/`), track lookup (`/api/track/<id>`), weekly view (`/api/week/<date>`), artist search (`/api/artist/<name>`), feature analysis (`/api/analysis/<feature>`) |
| Frontend tabs | Tracks (date-driven weekly view with radar chart), Trends (feature-driven line chart with rolling average), About (static methodology page) |
| Data analytics | Pandas-based weekly aggregation, 5-year rolling mean over annual averages, scaled integer casting for proportional features |
| Container delivery | Python 3.11-slim-buster base image, two-service Compose orchestration, host port mapping (80→5000 for API, 5432→5432 for PostgreSQL) |

#### Primary User Workflows

| Workflow | Steps | Components Involved |
|---|---|---|
| Inspect a specific chart week | Open Tracks tab → choose date in DatePicker → view ranked list and radar chart | `TracksSection.js`, `DatePicker.js`, `RadarChart.js` |
| Compare a feature across years | Open Trends tab → select feature in `FeatureSelect` → view annual + rolling line chart | `TrendsSection.js`, `FeatureSelect.js`, `LineChart.js`, `features.json` |
| Read project methodology | Open About tab → scroll through static content | `AboutSection.js` |

#### Essential Integrations

The repository assumes (but does not implement) a weekly write path that populates the `Tracks` and `YearlyAvg` tables. The read path consumed by this codebase is fully self-contained.

| Integration | Direction | Status |
|---|---|---|
| PostgreSQL 15 | API ↔ DB | In-scope (Docker Compose service) |
| React production build | Flask → static asset | In-scope (served from `frontend/build/`) |

#### Key Technical Requirements

| Requirement | Source | Implementation |
|---|---|---|
| Python 3.11 runtime | `Dockerfile` (`python:3.11-slim-buster`) | Container base image |
| PostgreSQL 15 | `docker-compose.yml` (`postgres:15`) | Compose service |
| Pinned Python dependencies | `requirements.txt` (23 packages) | `pip3 install -r requirements.txt` |
| Pinned JavaScript dependencies | `frontend/package.json` | CRA build pipeline |
| Bind-mount development workflow | `docker-compose.yml` (`.:/app/`) | Live code reload via mount |

### 1.3.2 Implementation Boundaries

#### System Boundaries

The repository's executable surface is bounded by the two Docker Compose services. Any process that does not run inside the `api` or `postgres` container at runtime—including the weekly scraper and the Spotify enrichment job—is outside the deployed system, even where it is referenced in user-facing documentation.

#### User Groups Covered

| Group | Coverage |
|---|---|
| Anonymous public web users | Full coverage (all features) |
| Authenticated users | Not applicable (no authentication exists) |
| Administrators | Not applicable (no admin surface exists) |

#### Geographic and Market Coverage

The Billboard Hot 100 itself is a United States chart, with chart positions derived from U.S. sales, radio play, and online streaming. The application makes no geographic gating decisions; the same content is served to all visitors regardless of locale.

#### Data Domains Included

| Domain | Tables / Schemas | Status |
|---|---|---|
| Weekly chart entries | `Tracks` (with audio features) | Read-only consumption in scope |
| Annual feature aggregates | `YearlyAvg` | Read-only consumption in scope |
| User accounts, sessions, preferences | None | Not in repository |
| Editorial/curatorial content | Static About page only | In scope as static content |

### 1.3.3 Out-of-Scope Elements

The following items are referenced by the project's documentation, implied by its dependencies, or commonly expected of a production web application but are **explicitly not implemented** in the codebase covered by this specification.

#### Excluded Features and Capabilities

| Excluded Item | Evidence of Exclusion |
|---|---|
| Weekly Billboard scraper | Referenced in `README.md` and `AboutSection.js`; no scraper code in `api/`, root, or any retrieved folder |
| Spotipy / Spotify API client code | No `spotipy` entry in `requirements.txt`; no Python source uses Spotify SDK |
| Authentication and authorization | No auth middleware, login route, or session handling in `api/routes.py` |
| Rate limiting | No `flask-limiter` or equivalent in `requirements.txt` |
| Automated tests | No `tests/` directory, no `pytest` configuration, no test files in retrieved folders |
| CI/CD pipelines | No `.github/`, `.gitlab-ci.yml`, or equivalent configuration files |
| Observability (logging, metrics, tracing) | No structured logging, no metrics endpoint, no APM agent |
| Production WSGI deployment | `gunicorn` declared in `requirements.txt` but not invoked; `Dockerfile` runs the Flask development server |
| Multi-environment configuration management | DB URL is hardcoded; no `config.py` or environment-driven settings |

#### Future Phase Considerations

The retrieved code surfaces several seams that suggest natural future-phase work, none of which are committed in this specification:

1. **Externalizing database credentials** to environment variables (currently hardcoded in `api/__init__.py`).
2. **Restoring dynamic current-week behavior** in `TracksSection.js` (the `new Date()` call exists but is commented out in favor of the literal `'2021-11-13'`).
3. **Reconciling documentation with implementation** for the rolling-average window (5-year in code, "3 year" in user-facing copy).
4. **Switching from the Flask development server to gunicorn** for production deployments.
5. **Removing or activating unused dependencies** such as `axios`, `plotly.js`, and `react-plotly.js`, which are declared but not imported by retrieved frontend source.

#### Integration Points Not Covered

| Integration | Reason for Exclusion |
|---|---|
| Spotify Web API (live calls) | Performed by an external enrichment job; the repository consumes only stored audio features |
| Billboard chart pages | Performed by the external scraper; the repository consumes only stored chart entries |
| Email, notifications, webhooks | No such surfaces exist in the codebase |
| Third-party analytics (e.g., Google Analytics, Segment) | No tracking snippets in `frontend/public/index.html` |

#### Unsupported Use Cases

| Use Case | Reason Unsupported |
|---|---|
| Personalized recommendations | No user accounts, no preference storage |
| Chart data outside the Billboard Hot 100 | Schema and routes are specific to Hot 100 weekly entries |
| Real-time chart updates | Data is refreshed weekly by an external scraper |
| Mobile-native experience | Delivered as a responsive web SPA only; the `manifest.json` enables PWA install but no native binary exists |
| Multi-region or localized chart data | Hot 100 is U.S.-only by definition; no localization layer exists |

---

## 1.4 References

### 1.4.1 Files Examined

- `README.md` — Project overview, Hot 100 explanation, API endpoint summary, frontend stack description
- `app.py` — Backend entry point that imports `app` from `api` and binds to `0.0.0.0`
- `Dockerfile` — Python 3.11-slim-buster build recipe with `libpq-dev` and `gcc` build dependencies
- `docker-compose.yml` — Two-service orchestration (`api` built from local context, `postgres:15`)
- `requirements.txt` — Pinned Python dependency list (23 packages including Flask 2.0.1, SQLAlchemy 1.4.19, pandas 2.0.0)
- `.dockerignore` — Excludes `frontend/node_modules`, `venv`, and `data` from build context
- `api/__init__.py` — Flask application factory, CORS configuration, hardcoded database URL, static folder pointer to `frontend/build`
- `api/models.py` — `Tracks` and `YearlyAvg` SQLAlchemy models and their Marshmallow schemas
- `api/routes.py` — Six HTTP route handlers including `/`, `/api/`, `/api/track/<id>`, `/api/week/<date>`, `/api/artist/<artist>`, `/api/analysis/<feature>`
- `api/funcs.py` — Date normalization (`get_query_week`), 5-year rolling average (`get_rolling_avg`), weekly aggregation (`get_weekly_data`)
- `frontend/package.json` — React 17.0.2, react-scripts 4.0.3, amCharts 4, dev proxy to `localhost:5000`
- `frontend/public/index.html` — HTML shell with `#root` mount, Jost font preconnect, page title "Hot Stuff"
- `frontend/public/manifest.json` — PWA metadata with standalone display mode and `#000000` theme color
- `frontend/src/App.js` — Top-level UI composition with three tabs at indices 0, 1, and 3
- `frontend/src/components/about/AboutSection.js` — In-application methodology documentation
- `frontend/src/components/tracks/TracksSection.js` — Date-driven fetch with hardcoded `2021-11-13` literal
- `frontend/src/components/tracks/DatePicker.js` — Week selection UI
- `frontend/src/components/tracks/RadarChart.js` — amCharts radar visualization
- `frontend/src/components/trends/TrendsSection.js` — Feature-driven fetch initialized with `tempo`
- `frontend/src/components/trends/FeatureSelect.js` — Feature selector UI
- `frontend/src/components/trends/LineChart.js` — amCharts line visualization
- `frontend/src/components/trends/features.json` — Seven audio-feature definitions and descriptions
- `frontend/src/components/navigation/Sidebar.js` — Sidebar component with three tabs and `nav` visibility prop
- `frontend/src/components/navigation/Hamburger.js`, `Tab.js`, `SmallTab.js`, `Section.js` — Navigation primitives styled with `styled-components`
- `frontend/src/styles/index.css` — Global theme styles

### 1.4.2 Folders Explored

- `/` (repository root) — Identified Docker, Compose, Python dependencies, README, root entry point, and the `api/` and `frontend/` subtrees
- `api/` — Contained the four backend Python source files (flat structure, no subfolders)
- `frontend/` — Contained `package.json`, lockfile, `src/`, `public/`, `build/`
- `frontend/src/` — Contained `App.js`, `index.js`, `components/`, `styles/`
- `frontend/src/components/` — Contained four feature folders (about, tracks, trends, navigation)
- `frontend/src/components/about/` — Contained the `AboutSection.js` component
- `frontend/src/components/tracks/` — Contained Tracks tab components (Section, DatePicker, RadarChart)
- `frontend/src/components/trends/` — Contained Trends tab components plus `features.json`
- `frontend/src/components/navigation/` — Contained five navigation primitives
- `frontend/src/styles/` — Contained the global stylesheet
- `frontend/public/` — Contained `index.html` and `manifest.json`
- `frontend/build/` — Contained the production output (asset manifest, HTML, manifest, static assets)

# 2. Product Requirements

This section enumerates the discrete, testable features that comprise the Hot Stuff application. Features are grouped into layered categories—API, Frontend, Visualization, Data and Logic, and Infrastructure—so that requirements can be traced to concrete source artifacts in the repository. Every feature listed below is observably implemented in the codebase as of the version examined for this specification; aspirational or out-of-scope capabilities are intentionally excluded and are documented separately in section 1.3.3.

## 2.1 FEATURE CATALOG

### 2.1.1 Feature Categorization Overview

The seventeen features documented in this catalog fall into five layered categories that align with the system's component boundaries described in section 1.2.

| Category | Feature ID Range | Primary Source Tree |
|---|---|---|
| API Layer (HTTP routes) | F-001 through F-006 | `api/routes.py` |
| Frontend Layer (tabs and shell) | F-007 through F-010 | `frontend/src/App.js`, `frontend/src/components/` |
| Visualization Layer (charts) | F-011, F-012 | `frontend/src/components/tracks/RadarChart.js`, `frontend/src/components/trends/LineChart.js` |
| Data and Logic Layer | F-013 through F-015 | `api/funcs.py`, `api/models.py` |
| Infrastructure | F-016, F-017 | `docker-compose.yml`, `Dockerfile`, `api/__init__.py` |

All features carry a status of **Completed** because they are observably implemented in the repository. No feature is in a Proposed or In Development state; the codebase represents a finished release artifact authored in mid-2021.

---

### 2.1.2 API Layer Features

#### 2.1.2.1 F-001: Static SPA Asset Delivery

| Attribute | Value |
|---|---|
| Unique ID | F-001 |
| Feature Name | Static SPA Asset Delivery |
| Feature Category | API Layer / Static Hosting |
| Priority Level | Critical |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The root path `GET /` returns the production React build's `index.html`, anchoring the single-page application served at the same origin as the JSON API |
| Business Value | Eliminates the need for a separate static-hosting tier (e.g., Nginx, S3, CloudFront), reducing deployment complexity to a single container |
| User Benefits | Users access the entire application from one URL with no cross-origin handshakes for the SPA shell |
| Technical Context | Implemented in `api/routes.py` lines 13-15 via `app.send_static_file('index.html')`, with `static_folder='../frontend/build'` and `static_url_path='/'` configured in `api/__init__.py` |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-016 (Docker Compose orchestration must mount or copy the build directory) |
| System Dependencies | Compiled React production build present at `frontend/build/index.html` |
| External Dependencies | None at runtime |
| Integration Requirements | The build artifact must be produced by `react-scripts build` prior to container start |

#### 2.1.2.2 F-002: Current Week Default Redirect

| Attribute | Value |
|---|---|
| Unique ID | F-002 |
| Feature Name | Current Week Default Redirect |
| Feature Category | API Layer / Convenience Routing |
| Priority Level | Medium |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The endpoint `GET /api/` computes the current chart week using `get_query_week(None)` and returns an HTTP redirect to `/api/week/{currentWeek}` |
| Business Value | Provides a stable, dated default endpoint for API explorers and integrations without requiring callers to compute the chart-week boundary themselves |
| User Benefits | Programmatic clients can rely on a single canonical URL to retrieve "this week" data |
| Technical Context | Implemented in `api/routes.py` lines 19-22 using `redirect()` from Flask; date normalization delegated to F-013 |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-013 (Chart Week Date Normalization), F-004 (Weekly Chart Data Retrieval, the redirect target) |
| System Dependencies | Server clock used by `datetime.today()` inside `get_query_week` |
| External Dependencies | None |
| Integration Requirements | None |

#### 2.1.2.3 F-003: Track Historical Lookup by Spotify ID

| Attribute | Value |
|---|---|
| Unique ID | F-003 |
| Feature Name | Track Historical Lookup by Spotify ID |
| Feature Category | API Layer / Track Detail |
| Priority Level | Medium |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The endpoint `GET /api/track/<spotify_id>` returns every chart appearance for the supplied Spotify track identifier, ordered by chart rank ascending |
| Business Value | Supports per-track analyses (debut week, peak position, longevity) for downstream consumers |
| User Benefits | API consumers can reconstruct a track's complete chart trajectory from a single call |
| Technical Context | Implemented in `api/routes.py` lines 26-31 using `Tracks.query.filter_by(spotify_id=spotify_id).order_by(Tracks.rank).all()` and serialized via `TrackSchema(many=True)` |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-015 (Persistence Models and JSON Serialization) |
| System Dependencies | PostgreSQL `tracks` table populated with non-null `spotify_id` values |
| External Dependencies | Out-of-repository scraper performs the initial Spotify ID enrichment |
| Integration Requirements | Consuming clients must supply a valid Spotify track ID string |

#### 2.1.2.4 F-004: Weekly Chart Snapshot Retrieval

| Attribute | Value |
|---|---|
| Unique ID | F-004 |
| Feature Name | Weekly Chart Snapshot Retrieval |
| Feature Category | API Layer / Chart Data |
| Priority Level | Critical |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The endpoint `GET /api/week/<week>` returns the full ranked song list for a given chart week along with computed per-week averages and an integer `avgTempo` |
| Business Value | Powers the primary visual experience (radar chart) on the Tracks tab and is the most frequently invoked endpoint |
| User Benefits | Users see a complete weekly chart with its quantified audio "fingerprint" in a single response |
| Technical Context | Implemented in `api/routes.py` lines 35-45; queries `Tracks.query.filter_by(week=week).order_by(Tracks.rank).all()` and computes averages via `get_weekly_data` |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-013 (Date Normalization), F-015 (Persistence Models) |
| System Dependencies | PostgreSQL `tracks` table indexed on `week` |
| External Dependencies | None at runtime |
| Integration Requirements | Date string must be parseable by SQLAlchemy `Date` column comparison |

#### 2.1.2.5 F-005: Case-Insensitive Artist Search

| Attribute | Value |
|---|---|
| Unique ID | F-005 |
| Feature Name | Case-Insensitive Artist Search |
| Feature Category | API Layer / Search |
| Priority Level | Medium |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The endpoint `GET /api/artist/<artist>` returns chart appearances whose `artist` column matches the supplied substring (case-insensitive), ordered by week descending |
| Business Value | Enables artist-centric exploration without requiring exact spelling or capitalization |
| User Benefits | Consumers can locate an artist's chart history with a partial name |
| Technical Context | Implemented in `api/routes.py` lines 49-55 using `func.lower(Tracks.artist).like(func.lower(f'%{artist}%'))`, ordered by `Tracks.week.desc()` |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-015 (Persistence Models) |
| System Dependencies | PostgreSQL function support for `LOWER` and `LIKE` |
| External Dependencies | None |
| Integration Requirements | Caller is responsible for URL-encoding artist names containing spaces or special characters |

#### 2.1.2.6 F-006: Annual Feature Trend Analysis

| Attribute | Value |
|---|---|
| Unique ID | F-006 |
| Feature Name | Annual Feature Trend Analysis |
| Feature Category | API Layer / Analytics |
| Priority Level | Critical |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The endpoint `GET /api/analysis/<feature>` returns the annual mean and a multi-year rolling mean for any audio feature stored in the `YearlyAvg` table, with HTTP status 200 |
| Business Value | Powers the longitudinal analytics surface on the Trends tab, the application's primary insight feature |
| User Benefits | Users can compare year-over-year evolution of a single audio characteristic across the chart's full history |
| Technical Context | Implemented in `api/routes.py` lines 60-69; uses `YearlyAvg.query.with_entities(YearlyAvg.year, getattr(YearlyAvg, feature))` and delegates rolling computation to F-014 |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-014 (Rolling Average Computation), F-015 (Persistence Models) |
| System Dependencies | PostgreSQL `yearly_avg` table populated with one row per year |
| External Dependencies | `pandas` rolling window machinery |
| Integration Requirements | Feature name parameter must match a `YearlyAvg` column attribute |

---

### 2.1.3 Frontend Layer Features

#### 2.1.3.1 F-007: Tab-Based Navigation Shell

| Attribute | Value |
|---|---|
| Unique ID | F-007 |
| Feature Name | Tab-Based Navigation Shell |
| Feature Category | Frontend / Navigation |
| Priority Level | Critical |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The application provides three tabs (Tracks, Trends, About) reachable through a sidebar; `App.js` maintains an `activeTab` state initialized to 0 and a `nav` boolean to toggle sidebar visibility on small viewports |
| Business Value | Organizes the application's three core experiences into discoverable, predictable surfaces |
| User Benefits | Users navigate without page reloads; the sidebar collapses on viewports below 800px to preserve content space |
| Technical Context | `frontend/src/App.js` orchestrates `Sidebar`, three `Section` containers, and a footer; tab indices are 0 (Tracks), 1 (Trends), and 3 (About)—index 2 is intentionally unused |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-008, F-009, F-010 (the three tab content surfaces) |
| System Dependencies | `react`, `react-dom`, `styled-components` |
| External Dependencies | None |
| Integration Requirements | All three section components must accept an `activeTab` boolean prop |

#### 2.1.3.2 F-008: Weekly Track Inspection View (Tracks Tab)

| Attribute | Value |
|---|---|
| Unique ID | F-008 |
| Feature Name | Weekly Track Inspection View |
| Feature Category | Frontend / Tracks Tab |
| Priority Level | Critical |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The Tracks tab combines a `DatePicker`, a scrollable ranked list of chart entries, and a `RadarChart`; on mount it triggers a fetch against `/api/week/2021-11-13` (a hardcoded date literal in `TracksSection.js` line 37) |
| Business Value | Delivers the primary "what does this week sound like?" experience that anchors the application |
| User Benefits | Users can pick any chart week between 1958-07-27 and 2021-11-13 to view the ranked chart and a feature radar chart |
| Technical Context | `TracksSection.js` manages `data`, `isLoaded`, and `error` states; renders the radar chart from `data.averages` and the song list from `data.songs` |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-004 (weekly endpoint), F-011 (radar chart), F-007 (navigation shell) |
| System Dependencies | `fetch` API in modern browsers |
| External Dependencies | None |
| Integration Requirements | Backend `/api/week/<date>` must return `{week, songs, averages, avgTempo}` JSON shape |

#### 2.1.3.3 F-009: Feature Trend Visualization View (Trends Tab)

| Attribute | Value |
|---|---|
| Unique ID | F-009 |
| Feature Name | Feature Trend Visualization View |
| Feature Category | Frontend / Trends Tab |
| Priority Level | Critical |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The Trends tab provides a `FeatureSelect` dropdown (seven hardcoded options), a `LineChart` rendering both annual mean and rolling mean, and a documentation list rendered from `features.json` |
| Business Value | Surfaces the application's longitudinal analytics differentiator |
| User Benefits | Users compare feature evolution across decades and read concise definitions of each feature in the same view |
| Technical Context | `TrendsSection.js` triggers an initial fetch with feature `tempo` on mount; consumes `feature.desctiption` (sic) from `features.json` line 4 et al |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-006 (analysis endpoint), F-012 (line chart), F-007 (navigation shell) |
| System Dependencies | `fetch` API; bundled `features.json` static asset |
| External Dependencies | None |
| Integration Requirements | The `FeatureSelect` option values must match `YearlyAvg` column names supported by F-006 |

#### 2.1.3.4 F-010: Methodology Documentation View (About Tab)

| Attribute | Value |
|---|---|
| Unique ID | F-010 |
| Feature Name | Methodology Documentation View |
| Feature Category | Frontend / About Tab |
| Priority Level | Low |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | A static page that explains the project methodology in three sections (Billboard Hot 100, API endpoint catalog, Front End), with external links to Billboard, Wikipedia, Spotipy, Spotify Audio Features documentation, amCharts, and the public source repository |
| Business Value | Builds user trust by transparently documenting data lineage and visualization choices |
| User Benefits | Users understand the data sources and analytical decisions behind every chart they see |
| Technical Context | `AboutSection.js` is a pure presentational component with no fetch lifecycle; uses tab index 3 in `App.js` and `Sidebar.js` |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-007 (navigation shell) |
| System Dependencies | None beyond React rendering |
| External Dependencies | Live external URLs in anchor tags (Billboard, Wikipedia, Spotipy docs, Spotify docs, amCharts, GitHub) |
| Integration Requirements | None |

---

### 2.1.4 Visualization Features

#### 2.1.4.1 F-011: Audio Feature Radar Chart

| Attribute | Value |
|---|---|
| Unique ID | F-011 |
| Feature Name | Audio Feature Radar Chart |
| Feature Category | Visualization / Radar |
| Priority Level | Critical |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | A semi-circular amCharts 4 `RadarChart` rendered into the `#radialChart` DOM element, displaying two `RadarColumnSeries`: a `full` baseline at 100 and a `mean` series populated from the weekly averages |
| Business Value | Provides at-a-glance comparison of five proportional audio features for any chart week |
| User Benefits | Users perceive the "shape" of a week's sound rather than reading numeric tables |
| Technical Context | `RadarChart.js` configures `startAngle=-90`, `endAngle=180`, `innerRadius='30%'`, and a fixed value-axis range of 0–100 |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-008 (consumer view) |
| System Dependencies | `@amcharts/amcharts4` (^4.10.19) |
| External Dependencies | None |
| Integration Requirements | Accepts an array of `{feature, full, mean}` records from F-004's averages payload |

#### 2.1.4.2 F-012: Audio Feature Trend Line Chart

| Attribute | Value |
|---|---|
| Unique ID | F-012 |
| Feature Name | Audio Feature Trend Line Chart |
| Feature Category | Visualization / Line Chart |
| Priority Level | Critical |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | An amCharts 4 `XYChart` rendered into the `#featureChart` DOM element with a `DateAxis` (year granularity) and a `ValueAxis`; renders two `LineSeries` labeled "Annual Average" (purple dashed) and "3 Year Rolling Average" (purple solid) with an `XYCursor` and bottom legend |
| Business Value | Visualizes long-term trends and smooths year-to-year noise via the rolling mean |
| User Benefits | Users distinguish secular trends from short-term volatility in a single chart |
| Technical Context | `LineChart.js` consumes a JSON payload from F-006 and binds both series to the same dataset |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-009 (consumer view), F-014 (rolling average computation supplies the second series) |
| System Dependencies | `@amcharts/amcharts4` (^4.10.19) |
| External Dependencies | None |
| Integration Requirements | Accepts an array of `{year, value, rollingAvg}` records derived from F-006 |

---

### 2.1.5 Data and Logic Layer Features

#### 2.1.5.1 F-013: Chart Week Date Normalization

| Attribute | Value |
|---|---|
| Unique ID | F-013 |
| Feature Name | Chart Week Date Normalization |
| Feature Category | Data Logic / Date Handling |
| Priority Level | High |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The helper `get_query_week(date)` normalizes any date to the corresponding chart-week Saturday boundary; if the supplied weekday is in {6, 0, 1} (or Wednesday before 10:00 AM) it returns the previous Saturday, otherwise the next |
| Business Value | Ensures consistent chart-week alignment regardless of when callers provide a date |
| User Benefits | Users get correct chart data whether they enter a Sunday, a Tuesday, or a mid-week query |
| Technical Context | Implemented in `api/funcs.py` lines 5-24; consumed by both F-002 (current week redirect) and F-004 (weekly retrieval) |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | None |
| System Dependencies | Python `datetime` and `dateutil.relativedelta` |
| External Dependencies | None |
| Integration Requirements | None |

#### 2.1.5.2 F-014: Multi-Year Rolling Average Computation

| Attribute | Value |
|---|---|
| Unique ID | F-014 |
| Feature Name | Multi-Year Rolling Average Computation |
| Feature Category | Data Logic / Aggregation |
| Priority Level | High |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | The helper `get_rolling_avg(data)` computes a rolling mean using `pandas.DataFrame.rolling(5).mean()`, drops NaN-only windows, and renames the feature column to `value` for client consumption |
| Business Value | Reveals long-term feature trends by smoothing out year-to-year noise |
| User Benefits | Users see the underlying secular trend separated from annual variance |
| Technical Context | Implemented in `api/funcs.py` lines 27-37; the source code uses a 5-year window despite documentation references to "3 year" rolling average in `README.md`, `AboutSection.js`, and the `LineChart.js` series label |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-015 (Persistence Models for `YearlyAvg`) |
| System Dependencies | `pandas` (2.0.0), `numpy` (1.24.2) |
| External Dependencies | None |
| Integration Requirements | Caller must provide a tabular structure with at least one numeric feature column and a year column |

#### 2.1.5.3 F-015: Persistence Models and JSON Serialization

| Attribute | Value |
|---|---|
| Unique ID | F-015 |
| Feature Name | Persistence Models and JSON Serialization |
| Feature Category | Data Layer / ORM |
| Priority Level | Critical |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | Two SQLAlchemy models—`Tracks` (one row per chart entry, ten audio-feature columns) and `YearlyAvg` (pre-aggregated annual averages for eight features)—paired with Marshmallow `TrackSchema` and `YearlyAvgSchema` JSON serializers |
| Business Value | Decouples database storage from API response shape, enabling schema evolution without changing route handlers |
| User Benefits | API consumers receive stable, well-typed JSON regardless of underlying ORM changes |
| Technical Context | Defined in `api/models.py`; `Tracks` includes `valence` and `loudness` columns that are not exposed in the Trends UI; the `Tracks.__init__` constructor omits `spotify_id` despite the column being defined and serialized |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | F-016 (PostgreSQL service availability) |
| System Dependencies | `Flask-SQLAlchemy` 2.5.1, `flask-marshmallow` 0.14.0, `marshmallow-sqlalchemy` 0.26.1, `SQLAlchemy` 1.4.19 |
| External Dependencies | PostgreSQL 15 service from Docker Compose |
| Integration Requirements | Out-of-repository scraper must populate both tables on a weekly cadence |

---

### 2.1.6 Infrastructure Features

#### 2.1.6.1 F-016: Docker Compose Two-Service Orchestration

| Attribute | Value |
|---|---|
| Unique ID | F-016 |
| Feature Name | Docker Compose Two-Service Orchestration |
| Feature Category | Infrastructure / Deployment |
| Priority Level | Critical |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | A `docker-compose.yml` defining an `api` service (built from local `Dockerfile`, port `80:5000`, `restart: on-failure`, `NODE_OPTIONS=--openssl-legacy-provider`, bind-mount `.:/app/`) and a `postgres` service (`postgres:15`, port `5432:5432`, mount `./data:/data`) |
| Business Value | Single-command deployment (`docker compose up`) for the entire stack |
| User Benefits | Developers and operators provision a working environment without complex setup |
| Technical Context | The API container builds from `python:3.11-slim-buster`, installs `libpq-dev` and `gcc`, runs `pip3 install -r requirements.txt`, exposes port 5000, and starts via `CMD ["python3", "app.py"]` |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | None |
| System Dependencies | Docker Engine, Docker Compose |
| External Dependencies | Docker Hub access for `python:3.11-slim-buster` and `postgres:15` base images |
| Integration Requirements | Host port 80 and 5432 must be available |

#### 2.1.6.2 F-017: Open Cross-Origin Resource Sharing

| Attribute | Value |
|---|---|
| Unique ID | F-017 |
| Feature Name | Open Cross-Origin Resource Sharing |
| Feature Category | Infrastructure / Security Posture |
| Priority Level | Medium |
| Status | Completed |

**Description**

| Aspect | Detail |
|---|---|
| Overview | `CORS(app)` is registered globally in `api/__init__.py` without any origin allow-list, exposing every endpoint to any browser-originated cross-origin caller |
| Business Value | Allows direct API consumption by any client without browser-imposed CORS friction |
| User Benefits | Third-party consumers can call the API from any origin without proxy infrastructure |
| Technical Context | Implemented via `Flask-Cors` 3.0.10; no environment-driven origin configuration exists |

**Dependencies**

| Dependency Type | Detail |
|---|---|
| Prerequisite Features | None |
| System Dependencies | `Flask-Cors` 3.0.10 |
| External Dependencies | None |
| Integration Requirements | None |

---

## 2.2 FUNCTIONAL REQUIREMENTS TABLES

This section decomposes each feature into testable requirements. Every requirement is uniquely identified using the format `F-XXX-RQ-YYY`. Requirements are organized into three companion tables per feature: requirement details (identifier, description, priority, complexity), technical specifications (input, output, performance), and validation rules (business rules, security/compliance).

### 2.2.1 F-001 Static SPA Asset Delivery Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-001-RQ-001 | The system SHALL respond to `GET /` with the contents of `frontend/build/index.html` | Must-Have | Low |
| F-001-RQ-002 | The system SHALL serve static assets (JS, CSS, fonts) referenced from `index.html` from the same `frontend/build/` directory | Must-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-001-RQ-001 | A `curl http://host/` call returns HTTP 200 with the React shell HTML; navigating in a browser to the root URL renders the SPA |
| F-001-RQ-002 | All `<script>` and `<link>` URLs referenced in `index.html` resolve to 200 responses |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-001-RQ-001 | None | HTTP 200 with `text/html` body | `frontend/build/index.html` exists at startup |
| F-001-RQ-002 | Asset URI relative to root | HTTP 200 with the asset content type | All compiled assets present under `frontend/build/` |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-001-RQ-001 | No authentication required (public asset) |
| F-001-RQ-002 | Subject to F-017 (open CORS) |

### 2.2.2 F-002 Current Week Default Redirect Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-002-RQ-001 | The system SHALL respond to `GET /api/` with an HTTP redirect to `/api/week/{currentWeek}` where `{currentWeek}` is computed via `get_query_week(None)` | Must-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-002-RQ-001 | The response status indicates a redirect (3xx) and the `Location` header points to a valid `/api/week/<YYYY-MM-DD>` URL where the date is a Saturday boundary |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-002-RQ-001 | None | HTTP redirect to weekly endpoint | Server clock available |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-002-RQ-001 | Computed week MUST be a Saturday per F-013 normalization rules |

### 2.2.3 F-003 Track Historical Lookup Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-003-RQ-001 | The system SHALL respond to `GET /api/track/<spotify_id>` with a JSON array of every `Tracks` row matching the supplied identifier, ordered by `rank` ascending | Must-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-003-RQ-001 | Response is a JSON array; each element conforms to `TrackSchema`; results are sorted by `rank` ascending; an unknown `spotify_id` returns an empty array |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-003-RQ-001 | `spotify_id` (path string) | `application/json` array of `TrackSchema` objects | `tracks.spotify_id` populated for queryable rows |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-003-RQ-001 | No authentication; no input sanitation needed because SQLAlchemy parameterizes `filter_by` |

### 2.2.4 F-004 Weekly Chart Snapshot Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-004-RQ-001 | The system SHALL respond to `GET /api/week/<week>` with `{week, songs, averages, avgTempo}` JSON | Must-Have | Medium |
| F-004-RQ-002 | The `averages` array SHALL include records for `energy`, `danceability`, `speechiness`, `acousticness`, `instrumentalness` scaled by 100 with a `full` baseline of 100 | Must-Have | Medium |
| F-004-RQ-003 | The `avgTempo` value SHALL be the integer-cast mean tempo of all returned songs | Must-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-004-RQ-001 | Response is JSON with the four documented top-level keys; `songs` is ordered by `rank` ascending |
| F-004-RQ-002 | Each averages record has `feature`, `mean` (0–100), and `full` (=100) keys |
| F-004-RQ-003 | `avgTempo` is an integer suitable for direct rendering |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-004-RQ-001 | `week` (path, ISO date) | `application/json` with `week`, `songs`, `averages`, `avgTempo` | `tracks.week` indexed |
| F-004-RQ-002 | None | Five-element averages array | All five feature columns populated |
| F-004-RQ-003 | None | Integer scalar | `tracks.tempo` populated |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-004-RQ-001 | Date input MUST be parseable as a SQL `DATE` |
| F-004-RQ-002 | Scaling factor of 100 reflects display semantics for proportional features |
| F-004-RQ-003 | Tempo is intentionally integer-cast for display economy |

### 2.2.5 F-005 Artist Search Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-005-RQ-001 | The system SHALL respond to `GET /api/artist/<artist>` with a JSON array of `Tracks` rows whose `artist` column contains the supplied substring (case-insensitive), ordered by `week` descending | Should-Have | Medium |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-005-RQ-001 | Response is a `TrackSchema` JSON array; lowercase, uppercase, and mixed-case inputs return the same result set; ordering is by `week` descending |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-005-RQ-001 | `artist` (path string) | `application/json` array | `tracks.artist` populated |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-005-RQ-001 | SQL `%pattern%` LIKE prevents index use; performance degrades with large datasets |

### 2.2.6 F-006 Annual Feature Trend Analysis Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-006-RQ-001 | The system SHALL respond to `GET /api/analysis/<feature>` with `{feature, data}` JSON and HTTP 200 | Must-Have | Medium |
| F-006-RQ-002 | The `data` payload SHALL include the per-year mean for the supplied feature and the multi-year rolling mean computed by F-014 | Must-Have | Medium |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-006-RQ-001 | Status code is 200; body is JSON with `feature` (echoed parameter) and `data` (records) |
| F-006-RQ-002 | Each record has `year`, the feature's annual mean, and the rolling mean (named `value` per F-014) |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-006-RQ-001 | `feature` (path string matching a `YearlyAvg` column) | `application/json` with status 200 | `yearly_avg` table populated |
| F-006-RQ-002 | None | Records aligned by year | At least 5 years of data for non-empty rolling output |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-006-RQ-001 | Feature name uses Python `getattr`; supplying an unknown attribute raises an exception |
| F-006-RQ-002 | First (window-1) years produce NaN windows that F-014 drops |

### 2.2.7 F-007 Tab-Based Navigation Shell Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-007-RQ-001 | The shell SHALL render a `Sidebar` with three tabs (Tracks, Trends, About) | Must-Have | Low |
| F-007-RQ-002 | Tab indices SHALL be 0 for Tracks, 1 for Trends, and 3 for About | Should-Have | Low |
| F-007-RQ-003 | The shell SHALL toggle sidebar visibility via a `nav` boolean controlled by a `Hamburger` icon on small viewports (under 800px) | Must-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-007-RQ-001 | All three tabs are reachable via a single click; the active tab visually highlights with `rgb(128, 103, 220)` |
| F-007-RQ-002 | `App.js` `Section` components and `Sidebar` `Tab` IDs use indices 0, 1, 3 (no 2); index 2 remains intentionally unassigned |
| F-007-RQ-003 | At viewports below 800px the sidebar collapses; clicking the hamburger reveals it via opacity transition |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-007-RQ-001 | None | Three rendered tabs | None |
| F-007-RQ-002 | None | Three `Section` containers with matching IDs | None |
| F-007-RQ-003 | Viewport width via CSS media query | Conditional layout | None |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-007-RQ-001 | Active highlight color is consumed from the global theme tokens in `frontend/src/styles/index.css` |
| F-007-RQ-003 | Responsive breakpoint MUST match `min-width: 800px` defined in `Sidebar.js` |

### 2.2.8 F-008 Weekly Track Inspection View Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-008-RQ-001 | On mount, the Tracks tab SHALL fetch `/api/week/2021-11-13` (literal date) | Must-Have | Low |
| F-008-RQ-002 | The view SHALL render a `DatePicker` constrained to the range 1958-07-27 to 2021-11-13 | Must-Have | Low |
| F-008-RQ-003 | The view SHALL render a scrollable list of songs showing rank, artist, and track title | Must-Have | Low |
| F-008-RQ-004 | The view SHALL display a `RadarChart` populated from the response `averages` payload | Must-Have | Medium |
| F-008-RQ-005 | The view SHALL display loading and error states using `isLoaded` and `error` flags, with status > 299 producing `error = response.statusText` and an empty payload producing `error = "No Data Found"` | Should-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-008-RQ-001 | Initial render fires exactly one fetch to the literal date URL |
| F-008-RQ-002 | The HTML date input refuses dates outside the configured range |
| F-008-RQ-003 | The list scrolls when overflowing the viewport; ranks display in ascending order |
| F-008-RQ-004 | The radar updates whenever `data.averages` changes |
| F-008-RQ-005 | A loading indicator (`. . .`) appears until data resolves; errors render in an `h1.error` element |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-008-RQ-001 | None at mount | Network request | F-004 must be available |
| F-008-RQ-002 | User-selected ISO date | `submitFunc` callback invocation | None |
| F-008-RQ-003 | `data.songs` array | Rendered list items | Each song has `rank`, `artist`, `track` |
| F-008-RQ-004 | `data.averages` | Updated radar series | Five proportional features and a baseline |
| F-008-RQ-005 | HTTP status / data length | Conditional UI render | None |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-008-RQ-001 | The hardcoded literal `2021-11-13` is documented as a known limitation; the dynamic alternative `new Date()` exists as a commented-out line in `TracksSection.js` line 36 |
| F-008-RQ-002 | Range bounds reflect the historical chart period covered by the dataset |

### 2.2.9 F-009 Feature Trend Visualization View Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-009-RQ-001 | On mount, the Trends tab SHALL fetch `/api/analysis/tempo` | Must-Have | Low |
| F-009-RQ-002 | The view SHALL render a `FeatureSelect` dropdown with seven options: tempo, energy, danceability, instrumentalness, liveness, speechiness, acousticness | Must-Have | Low |
| F-009-RQ-003 | The view SHALL render a `LineChart` displaying both annual and rolling means | Must-Have | Medium |
| F-009-RQ-004 | The view SHALL render seven feature description entries from `features.json`, each consumed via the key `desctiption` (sic) | Must-Have | Low |
| F-009-RQ-005 | The view SHALL implement loading and error states identical in semantics to F-008-RQ-005 | Should-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-009-RQ-001 | Initial render fires exactly one fetch with feature `tempo` |
| F-009-RQ-002 | Dropdown lists seven options; `valence` is intentionally excluded |
| F-009-RQ-003 | Two series render: a dashed "Annual Average" and a solid "3 Year Rolling Average" (per the in-code label) |
| F-009-RQ-004 | Documentation list contains seven items mirroring the dropdown options |
| F-009-RQ-005 | Loading and error states render exactly as in F-008 |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-009-RQ-001 | None at mount | Network request | F-006 must be available |
| F-009-RQ-002 | User selection | Triggers re-fetch | Hardcoded option list |
| F-009-RQ-003 | F-006 response | Rendered chart | Two-series dataset |
| F-009-RQ-004 | `features.json` | Rendered description list | Seven entries with `desctiption` key |
| F-009-RQ-005 | HTTP status / data length | Conditional UI render | None |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-009-RQ-002 | Dropdown options MUST correspond to columns in `YearlyAvg` (which excludes `valence` and `loudness`) |
| F-009-RQ-003 | The "3 Year" label is the displayed string; F-014's actual window is 5 years (a known documentation discrepancy) |
| F-009-RQ-004 | The `desctiption` typo is consumed verbatim and MUST be preserved unless the data file is corrected in tandem |

### 2.2.10 F-010 Methodology Documentation Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-010-RQ-001 | The About tab SHALL display three sections: Billboard Hot 100, API (with endpoint catalog), and Front End | Should-Have | Low |
| F-010-RQ-002 | The About tab SHALL link to the public source repository at `https://github.com/augardiner/hot-100` | Could-Have | Low |
| F-010-RQ-003 | The About tab SHALL link to Billboard, Wikipedia, Spotipy documentation, Spotify Audio Features documentation, and amCharts | Could-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-010-RQ-001 | All three sections render with their headings and prose; the API section enumerates the available endpoints |
| F-010-RQ-002 | The "Source Code" link opens the documented GitHub URL |
| F-010-RQ-003 | All five external links are present and clickable |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-010-RQ-001 | None | Static markup | None |
| F-010-RQ-002 | None | `<a>` element with `href` | None |
| F-010-RQ-003 | None | Five `<a>` elements | None |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-010-RQ-001 | Content is static; updates require a redeployment |

### 2.2.11 F-011 Audio Feature Radar Chart Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-011-RQ-001 | The radar SHALL be rendered into a DOM element with id `radialChart` using amCharts 4 | Must-Have | Medium |
| F-011-RQ-002 | The chart SHALL be semi-circular with `startAngle=-90`, `endAngle=180`, and `innerRadius=30%` | Should-Have | Low |
| F-011-RQ-003 | The chart SHALL render two `RadarColumnSeries`: a `full` baseline and a `mean` data series, both bound to the same value axis with range 0–100 | Must-Have | Medium |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-011-RQ-001 | Inspecting the DOM after render shows a populated `<div id="radialChart">` |
| F-011-RQ-002 | Visual layout matches the described angles |
| F-011-RQ-003 | Both series render simultaneously; the `full` baseline always reaches 100 |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-011-RQ-001 | `data.averages` from F-004 | Rendered chart | amCharts 4 loaded |
| F-011-RQ-002 | None | Semi-circular geometry | None |
| F-011-RQ-003 | `data.averages` records | Two visible series | Each record has `feature`, `mean`, `full` |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-011-RQ-003 | Value axis range MUST be fixed 0–100 to match F-004's scaling |

### 2.2.12 F-012 Audio Feature Trend Line Chart Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-012-RQ-001 | The chart SHALL render into a DOM element with id `featureChart` using amCharts 4 `XYChart` with a `DateAxis` and a `ValueAxis` | Must-Have | Medium |
| F-012-RQ-002 | The chart SHALL render two `LineSeries`: one labeled "Annual Average" (purple dashed) and one labeled "3 Year Rolling Average" (purple solid) | Must-Have | Medium |
| F-012-RQ-003 | The chart SHALL display an `XYCursor` and a bottom `Legend` | Should-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-012-RQ-001 | DOM contains a populated `<div id="featureChart">` |
| F-012-RQ-002 | Both labeled series render with the documented styling |
| F-012-RQ-003 | Hovering the chart shows a tooltip; legend appears below the plot area |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-012-RQ-001 | F-006 response data | Rendered chart | amCharts 4 loaded |
| F-012-RQ-002 | Year and value pairs | Two visible series | Records produced by F-014 |
| F-012-RQ-003 | User mouse interaction | Tooltip and legend | None |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-012-RQ-002 | Series labels are display strings; the "3 Year" string is a known mismatch with F-014's 5-year computation |

### 2.2.13 F-013 Chart Week Date Normalization Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-013-RQ-001 | `get_query_week(date)` SHALL return a `date` object aligned to a Saturday boundary | Must-Have | Medium |
| F-013-RQ-002 | When the input weekday is in {6 (Sun), 0 (Mon), 1 (Tue)}, or it is Wednesday before 10:00 AM, the function SHALL return the previous Saturday; otherwise the next Saturday | Must-Have | Medium |
| F-013-RQ-003 | When `date` is `None`, the function SHALL operate on `datetime.today()` | Must-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-013-RQ-001 | Output is always `date.weekday() == 5` (Saturday) |
| F-013-RQ-002 | Boundary cases (Wed 9:59 vs 10:01) produce different output Saturdays |
| F-013-RQ-003 | Calling with `None` returns the current chart week |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-013-RQ-001 | `date` (date or `None`) | `date` (Saturday) | None |
| F-013-RQ-002 | Same | Same | Server timezone affects "today" |
| F-013-RQ-003 | None | Current chart week | Server clock |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-013-RQ-002 | The 10:00 AM Wednesday cutoff aligns with Billboard's mid-week chart finalization cadence |

### 2.2.14 F-014 Multi-Year Rolling Average Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-014-RQ-001 | `get_rolling_avg(data)` SHALL apply `pandas.DataFrame.rolling(5).mean()` to the supplied tabular data | Must-Have | Low |
| F-014-RQ-002 | The function SHALL drop rows whose rolling window has fewer than 5 observations (i.e., NaN windows) | Must-Have | Low |
| F-014-RQ-003 | The function SHALL rename the feature column to `value` in the returned structure | Should-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-014-RQ-001 | Output rolling mean for year `Y` equals the arithmetic mean of years `Y-4` through `Y` |
| F-014-RQ-002 | First four years are absent from the output |
| F-014-RQ-003 | Returned structure contains a `value` field rather than the original feature column name |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-014-RQ-001 | DataFrame with year and feature columns | DataFrame with rolling mean | None |
| F-014-RQ-002 | Same | Reduced row count | At least 5 input rows for any output |
| F-014-RQ-003 | Same | Renamed column | None |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-014-RQ-001 | The 5-row window is the source of truth; UI labels stating "3 Year" are a documentation mismatch |

### 2.2.15 F-015 Persistence and Serialization Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-015-RQ-001 | The `Tracks` model SHALL define columns: `id` (PK), `week`, `rank`, `track`, `artist`, `spotify_id`, plus float audio features `tempo`, `energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `loudness` | Must-Have | Medium |
| F-015-RQ-002 | The `YearlyAvg` model SHALL define columns: `index` (PK), `year`, plus float aggregates `energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `tempo` | Must-Have | Medium |
| F-015-RQ-003 | `TrackSchema` SHALL serialize fields: `id`, `week`, `rank`, `track`, `artist`, `spotify_id`, `energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `loudness`, `tempo` | Must-Have | Low |
| F-015-RQ-004 | `YearlyAvgSchema` SHALL serialize fields: `year`, `energy`, `valence`, `liveness`, `speechiness`, `acousticness`, `danceability`, `instrumentalness`, `tempo` (note: schema field list is the source of truth even though `valence` is omitted in the Trends UI) | Should-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-015-RQ-001 | Inserting and reading a `Tracks` row roundtrips all listed columns |
| F-015-RQ-002 | Inserting and reading a `YearlyAvg` row roundtrips all listed columns |
| F-015-RQ-003 | `TrackSchema().dump()` produces a dict containing exactly the listed fields |
| F-015-RQ-004 | `YearlyAvgSchema().dump()` produces a dict containing exactly the listed fields |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-015-RQ-001 | ORM kwargs | Persisted row | PostgreSQL connection |
| F-015-RQ-002 | ORM kwargs | Persisted row | PostgreSQL connection |
| F-015-RQ-003 | `Tracks` instance | JSON-ready dict | Marshmallow runtime |
| F-015-RQ-004 | `YearlyAvg` instance | JSON-ready dict | Marshmallow runtime |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-015-RQ-001 | Constructor `__init__` does not assign `spotify_id`; ETL must set it via direct attribute assignment after construction (a known code shape) |
| F-015-RQ-003 | Field list is consumed by F-003, F-004, F-005 |

### 2.2.16 F-016 Docker Compose Orchestration Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-016-RQ-001 | Compose SHALL define an `api` service built from the local `Dockerfile`, mapping host port 80 to container port 5000, with `restart: on-failure` and `NODE_OPTIONS=--openssl-legacy-provider` | Must-Have | Medium |
| F-016-RQ-002 | Compose SHALL define a `postgres` service using image `postgres:15`, mapping host port 5432 to container port 5432, with environment `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`, `POSTGRES_DB=db` | Must-Have | Medium |
| F-016-RQ-003 | The `api` service SHALL declare `depends_on: postgres` and bind-mount `.:/app/` for development | Must-Have | Low |
| F-016-RQ-004 | The `Dockerfile` SHALL use base image `python:3.11-slim-buster`, install `libpq-dev` and `gcc`, run `pip3 install -r requirements.txt`, expose port 5000, and execute `CMD ["python3", "app.py"]` | Must-Have | Medium |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-016-RQ-001 | `docker compose up` produces an `api` container reachable on host port 80 |
| F-016-RQ-002 | The `postgres` container exposes the database on host port 5432 with the documented credentials |
| F-016-RQ-003 | The `api` container starts only after `postgres` is up; source changes on the host appear in the container |
| F-016-RQ-004 | The container starts the Flask development server, not gunicorn |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-016-RQ-001 | `docker-compose.yml` | Running container | Docker Engine |
| F-016-RQ-002 | Same | Running container | Docker Engine |
| F-016-RQ-003 | Same | Ordered startup | Volume mount support |
| F-016-RQ-004 | `Dockerfile` | Built image | Internet access for base image |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-016-RQ-002 | Default credentials (`postgres:postgres`) are unsuitable for production deployments |
| F-016-RQ-004 | Use of the Flask development server is a known production-readiness gap; `gunicorn` is declared in `requirements.txt` but not invoked |

### 2.2.17 F-017 Open Cross-Origin Resource Sharing Requirements

**Requirement Details**

| Requirement ID | Description | Priority | Complexity |
|---|---|---|---|
| F-017-RQ-001 | The application SHALL register `CORS(app)` globally without an origin allow-list | Should-Have | Low |

**Acceptance Criteria**

| Requirement ID | Acceptance Criteria |
|---|---|
| F-017-RQ-001 | All API responses include a permissive `Access-Control-Allow-Origin` header |

**Technical Specifications**

| Requirement ID | Input Parameters | Output / Response | Data Requirements |
|---|---|---|---|
| F-017-RQ-001 | None | Permissive CORS headers on every response | None |

**Validation Rules**

| Requirement ID | Business / Security / Compliance Rule |
|---|---|
| F-017-RQ-001 | Open CORS is a deliberate posture for this read-only public dataset; it is unsuitable for any future authenticated endpoints |

---

## 2.3 FEATURE RELATIONSHIPS

### 2.3.1 Feature Dependency Map

The following diagram captures the directed dependency graph among all seventeen features. Each arrow indicates "depends on": the source feature requires the target feature to function.

```mermaid
graph TD
    subgraph InfrastructureLayer["Infrastructure"]
        F016[F-016 Docker Compose Orchestration]
        F017[F-017 Open CORS]
    end

    subgraph DataLayer["Data and Logic Layer"]
        F013[F-013 Date Normalization]
        F014[F-014 Rolling Average]
        F015[F-015 Persistence Models]
    end

    subgraph APILayer["API Layer"]
        F001[F-001 Static SPA Delivery]
        F002[F-002 Current Week Redirect]
        F003[F-003 Track Lookup]
        F004[F-004 Weekly Snapshot]
        F005[F-005 Artist Search]
        F006[F-006 Feature Trend Analysis]
    end

    subgraph FrontendLayer["Frontend Layer"]
        F007[F-007 Navigation Shell]
        F008[F-008 Tracks View]
        F009[F-009 Trends View]
        F010[F-010 About View]
    end

    subgraph VisualizationLayer["Visualization"]
        F011[F-011 Radar Chart]
        F012[F-012 Line Chart]
    end

    F015 --> F016
    F014 --> F015
    F002 --> F013
    F002 --> F004
    F003 --> F015
    F004 --> F013
    F004 --> F015
    F005 --> F015
    F006 --> F014
    F006 --> F015
    F008 --> F004
    F008 --> F011
    F008 --> F007
    F009 --> F006
    F009 --> F012
    F009 --> F007
    F010 --> F007
    F011 --> F008
    F012 --> F009
    F012 --> F014
    F001 --> F016
```

### 2.3.2 Integration Points

| Integration Point | Producer | Consumer |
|---|---|---|
| `/api/week/<date>` JSON contract | F-004 | F-002 (redirect target), F-008 (Tracks view) |
| `/api/analysis/<feature>` JSON contract | F-006 | F-009 (Trends view) |
| `/api/track/<id>` JSON contract | F-003 | External API consumers (no in-app consumer) |
| `/api/artist/<name>` JSON contract | F-005 | External API consumers (no in-app consumer) |
| `frontend/build/index.html` | CRA build output | F-001 (Flask `send_static_file`) |
| `features.json` static asset | Bundled data | F-009 (Trends view documentation list) |

### 2.3.3 Shared Components

| Shared Component | Used By | Purpose |
|---|---|---|
| `Hamburger.js` | F-008, F-009, F-010 | Mobile sidebar toggle on each tab |
| `Section.js` | F-008, F-009, F-010 (via F-007) | Conditional `display:none` wrapper for tab visibility |
| `Tab.js` / `SmallTab.js` | F-007 | Sidebar tab primitives |
| `Tracks` ORM model | F-003, F-004, F-005 | Single chart-row entity reused across three endpoints |
| `YearlyAvg` ORM model | F-006 | Pre-aggregated annual feature averages |
| `pandas` runtime | F-006 (via F-014), F-004 (via `get_weekly_data`) | Tabular aggregation primitives |
| `@amcharts/amcharts4` | F-011, F-012 | Charting runtime shared across both visualization features |
| `get_query_week()` helper | F-002, F-004 | Saturday-boundary date normalization |

### 2.3.4 Common Services

| Service | Provided By | Consumed By |
|---|---|---|
| HTTP server and routing | Flask 2.0.1 application object in `api/__init__.py` | F-001 through F-006 |
| ORM persistence | `Flask-SQLAlchemy` via `db` instance | F-015 (and transitively F-003, F-004, F-005, F-006) |
| JSON serialization | `flask-marshmallow` via `ma` instance | F-015 |
| Cross-origin policy | F-017 | F-001 through F-006 |
| Container runtime | F-016 | All backend features |

### 2.3.5 Workflow Reference

The following sequence diagram references the primary user workflows (also described in section 1.2). It documents how the catalog features interact during the Tracks-tab and Trends-tab user journeys.

```mermaid
sequenceDiagram
    participant User as Browser
    participant SPA as React SPA (F-007/F-008/F-009)
    participant API as Flask API
    participant DB as PostgreSQL

    User->>SPA: Load application root
    SPA->>API: GET /
    API-->>SPA: index.html (F-001)
    Note over SPA: Default tab = Tracks (F-008)
    SPA->>API: GET /api/week/2021-11-13 (F-004)
    API->>DB: SELECT * FROM tracks WHERE week=...
    DB-->>API: Rows
    API-->>SPA: {week, songs, averages, avgTempo}
    SPA->>SPA: Render list + RadarChart (F-011)

    User->>SPA: Click Trends tab
    SPA->>API: GET /api/analysis/tempo (F-006)
    API->>DB: SELECT year, tempo FROM yearly_avg
    DB-->>API: Rows
    API->>API: get_rolling_avg(data) (F-014)
    API-->>SPA: {feature, data}
    SPA->>SPA: Render LineChart (F-012)
```

---

## 2.4 IMPLEMENTATION CONSIDERATIONS

This subsection documents the cross-cutting concerns that affect every feature and the specific constraints that apply to individual features.

### 2.4.1 Technical Constraints

| Constraint | Affected Features | Source |
|---|---|---|
| Hardcoded database URI `postgresql://postgres:postgres@postgres/db` | F-015, F-016 | `api/__init__.py` line 12 |
| Flask development server (not gunicorn) | F-016 | `Dockerfile` `CMD ["python3", "app.py"]` |
| Hardcoded literal date `2021-11-13` for Tracks initial fetch | F-008 | `TracksSection.js` line 37 |
| `DatePicker` range bounded by `1958-07-27` and `2021-11-13` | F-008 | `DatePicker.js` |
| Five-year rolling window vs. "3 Year" UI label | F-014, F-012, F-009 | `api/funcs.py` line 32 vs. `LineChart.js` line 47, `AboutSection.js` line 84 |
| `valence` column exists but is excluded from `FeatureSelect` and `YearlyAvgSchema` field list | F-009, F-015 | `FeatureSelect.js` lines 19-25 |
| Misspelled JSON key `desctiption` (sic) consumed verbatim by Trends view | F-009 | `features.json` line 4 et al; `TrendsSection.js` line 69 |
| `Tracks.__init__` constructor omits `spotify_id` despite the column existing | F-015 | `api/models.py` lines 21-37 |
| Tab indices skip 2 (using 0, 1, 3) | F-007 | `App.js`, `Sidebar.js` |

### 2.4.2 Performance Requirements

| Feature | Performance Consideration |
|---|---|
| F-004 Weekly Snapshot | Aggregation runs in-memory on a single-week slice (≤100 rows); response time dominated by network overhead |
| F-005 Artist Search | Uses SQL `LOWER(...) LIKE '%pattern%'`, which prevents index use; performance scales with table size |
| F-006 Feature Trend Analysis | Reads from pre-aggregated `YearlyAvg` (≤~70 rows); rolling computation is constant-time relative to dataset size |
| F-011 Radar Chart, F-012 Line Chart | amCharts charts are created without explicit `chart.dispose()` (commented out in `RadarChart.js` line 66 and `LineChart.js` line 70); repeated tab switches risk client-side memory growth |
| F-016 Docker Compose | Flask development server is single-threaded and not optimized for concurrent traffic |

### 2.4.3 Scalability Considerations

| Concern | Implication |
|---|---|
| Single-process Flask development server | Concurrent request throughput is limited; horizontal scaling would require switching to gunicorn or another WSGI server |
| No connection pooling configured beyond Flask-SQLAlchemy defaults | Database concurrency limited to default pool size |
| `/api/artist/<name>` `LIKE '%pattern%'` query | Cannot use B-tree indexes; full-table scan as the dataset grows |
| Two-service Compose stack with no orchestration metadata | Production scaling would require migration to Kubernetes, ECS, or an equivalent orchestrator |
| In-process aggregation (`get_weekly_data`) | Fine at chart-week scale (≤100 rows); not designed for whole-table aggregation |

### 2.4.4 Security Implications

| Concern | Affected Features | Mitigation Status |
|---|---|---|
| No authentication or authorization | All features | Acceptable for the public-read use case; explicit non-goal |
| CORS open to all origins | F-017, transitively all API features | Acceptable for the public-read use case |
| Hardcoded database credentials (`postgres:postgres`) | F-015, F-016 | Known limitation; must not be reused in production |
| PostgreSQL port `5432:5432` exposed to the host | F-016 | Convenient for development; should be removed in production |
| No CSRF protection | All features | No state-changing endpoints exist; CSRF risk is low |
| No HTTPS termination | All features | Must be added at a reverse-proxy layer in production |
| No rate limiting (no `flask-limiter`) | All API features | Public dataset; mitigation depends on operator policy |
| `getattr(YearlyAvg, feature)` accepts arbitrary attribute names | F-006 | An invalid attribute name raises an exception rather than returning a 400; input validation is currently absent |

### 2.4.5 Maintenance Requirements

| Maintenance Task | Frequency | Owner |
|---|---|---|
| Run the external Billboard scraper to populate `Tracks` | Weekly | Project maintainer (out of repo) |
| Recompute `YearlyAvg` rows | Annually (or on backfill) | Project maintainer (out of repo) |
| Rebuild the React production bundle when frontend code changes | On change | Build pipeline (`react-scripts build`) |
| Reconcile documentation discrepancies (e.g., "3 Year" label, `2021-11-13` literal, `desctiption` typo) | One-time correction | Maintainer |
| Refresh container base images and pinned dependencies | As security advisories require | Maintainer |
| Externalize secrets to environment variables | Future-phase work | Maintainer |

---

## 2.5 TRACEABILITY MATRIX

The traceability matrix maps every feature to its primary source artifact, allowing reviewers and testers to navigate from a requirement to its implementation in a single hop.

### 2.5.1 Feature-to-Source Traceability

| Feature ID | Primary Source File(s) | Key Lines / Symbols |
|---|---|---|
| F-001 | `api/routes.py`, `api/__init__.py` | Lines 13-15; `static_folder='../frontend/build'` |
| F-002 | `api/routes.py` | Lines 19-22; `redirect()` |
| F-003 | `api/routes.py`, `api/models.py` | Lines 26-31; `Tracks.query.filter_by(spotify_id=...)` |
| F-004 | `api/routes.py`, `api/funcs.py` | Lines 35-45; `get_weekly_data` |
| F-005 | `api/routes.py` | Lines 49-55; `func.lower(...).like(...)` |
| F-006 | `api/routes.py`, `api/funcs.py` | Lines 60-69; `get_rolling_avg` |
| F-007 | `frontend/src/App.js`, `frontend/src/components/navigation/Sidebar.js` | `activeTab` state; tab IDs 0, 1, 3 |
| F-008 | `frontend/src/components/tracks/TracksSection.js` | Line 37 (`getData('2021-11-13')`); lines 56-68 |
| F-009 | `frontend/src/components/trends/TrendsSection.js` | Line 38 (`getData('tempo')`); line 69 (`feature.desctiption`) |
| F-010 | `frontend/src/components/about/AboutSection.js` | Static methodology |
| F-011 | `frontend/src/components/tracks/RadarChart.js` | `#radialChart`; `RadarColumnSeries` |
| F-012 | `frontend/src/components/trends/LineChart.js` | `#featureChart`; `LineSeries` labels |
| F-013 | `api/funcs.py` | Lines 5-24; weekday cutoff logic |
| F-014 | `api/funcs.py` | Lines 27-37; `.rolling(5).mean()` |
| F-015 | `api/models.py` | Lines 4-37 (`Tracks`), 48-58 (`YearlyAvg`), 40-45 (`TrackSchema`), 61-64 (`YearlyAvgSchema`) |
| F-016 | `docker-compose.yml`, `Dockerfile` | Lines 3-13 and 15-24; whole `Dockerfile` |
| F-017 | `api/__init__.py` | `CORS(app)` |

### 2.5.2 Requirement-to-Acceptance Traceability

| Requirement ID Range | Total Requirements | Test Strategy |
|---|---|---|
| F-001-RQ-001 to F-001-RQ-002 | 2 | Manual HTTP probes |
| F-002-RQ-001 | 1 | Manual HTTP probe with redirect-follow disabled |
| F-003-RQ-001 | 1 | Manual HTTP probe; JSON shape validation |
| F-004-RQ-001 to F-004-RQ-003 | 3 | Manual HTTP probe; JSON shape validation |
| F-005-RQ-001 | 1 | Manual HTTP probe with mixed-case input |
| F-006-RQ-001 to F-006-RQ-002 | 2 | Manual HTTP probe |
| F-007-RQ-001 to F-007-RQ-003 | 3 | Manual UI inspection at multiple viewport widths |
| F-008-RQ-001 to F-008-RQ-005 | 5 | Manual UI inspection; network panel verification |
| F-009-RQ-001 to F-009-RQ-005 | 5 | Manual UI inspection; network panel verification |
| F-010-RQ-001 to F-010-RQ-003 | 3 | Manual UI inspection |
| F-011-RQ-001 to F-011-RQ-003 | 3 | Manual UI inspection of DOM and chart |
| F-012-RQ-001 to F-012-RQ-003 | 3 | Manual UI inspection of DOM and chart |
| F-013-RQ-001 to F-013-RQ-003 | 3 | Function-level invocation with date inputs |
| F-014-RQ-001 to F-014-RQ-003 | 3 | Function-level invocation with synthetic DataFrames |
| F-015-RQ-001 to F-015-RQ-004 | 4 | Database-level CRUD probe; `dump()` invocation |
| F-016-RQ-001 to F-016-RQ-004 | 4 | `docker compose up` smoke test |
| F-017-RQ-001 | 1 | HTTP `OPTIONS` preflight inspection |

The repository does not include automated tests (no `tests/` directory, no `pytest` configuration). All test strategies above are therefore manual; introducing automated tests would be a future-phase undertaking and is documented as out-of-scope in section 1.3.3.

### 2.5.3 Documentation Discrepancy Register

The following table records every observed mismatch between code and user-facing documentation. Each discrepancy is anchored to the affected requirement(s) so that future remediation has a clear traceability target.

| Discrepancy | Affected Requirements | Source of Truth |
|---|---|---|
| "3 Year Rolling Average" label vs. `.rolling(5)` window | F-014-RQ-001, F-009-RQ-003, F-012-RQ-002 | Code: 5-year window |
| Hardcoded `'2021-11-13'` vs. commented-out `new Date()` | F-008-RQ-001 | Code: literal date |
| `gunicorn` declared but `python3 app.py` invoked | F-016-RQ-004 | Code: Flask development server |
| `python-dotenv` declared but no `.env` consumed | F-016-RQ-001 | Code: hardcoded URI |
| Tab indices 0, 1, 3 (no 2) | F-007-RQ-002 | Code: skipped index |
| Misspelled `desctiption` key consumed verbatim | F-009-RQ-004 | Code: typo preserved |
| `spotify_id` column not assigned in `Tracks.__init__` | F-015-RQ-001 | Code: omission documented |
| `valence` excluded from Trends UI but present in `Tracks` model | F-009-RQ-002, F-015-RQ-001 | Code: dropdown is the user-facing surface |

---

## 2.6 References

### 2.6.1 Files Examined

- `README.md` — Source of the API endpoint summary and the documented "3 year rolling average" claim referenced in F-014's discrepancy
- `app.py` — Backend launcher establishing the Flask `app.run(host='0.0.0.0')` invocation referenced in F-016
- `Dockerfile` — Source of the container build recipe and the `python3 app.py` start command referenced in F-016
- `docker-compose.yml` — Source of the two-service stack definition for F-016
- `requirements.txt` — Pinned Python dependencies including the unused `gunicorn` declaration referenced in F-016
- `.dockerignore` — Source of build-context exclusions referenced by F-016
- `api/__init__.py` — Flask factory, hardcoded DB URI (F-015, F-016), and `CORS(app)` registration (F-017)
- `api/models.py` — `Tracks` and `YearlyAvg` ORM models plus `TrackSchema` and `YearlyAvgSchema` for F-015
- `api/routes.py` — Six route handlers backing F-001 through F-006
- `api/funcs.py` — `get_query_week`, `get_rolling_avg`, and `get_weekly_data` helpers backing F-013 and F-014
- `frontend/package.json` — JavaScript dependency manifest referenced by F-007 through F-012
- `frontend/public/index.html` — HTML shell that mounts the React tree on which F-007 builds
- `frontend/public/manifest.json` — PWA metadata documented by F-007's containing application
- `frontend/src/App.js` — Tab orchestration with indices 0, 1, 3 backing F-007
- `frontend/src/index.js` — React entry point delivered by F-001
- `frontend/src/styles/index.css` — Theme tokens consumed by F-007
- `frontend/src/components/about/AboutSection.js` — Static methodology view backing F-010
- `frontend/src/components/tracks/TracksSection.js` — Tracks view backing F-008 with the hardcoded date literal
- `frontend/src/components/tracks/DatePicker.js` — Date selector backing F-008
- `frontend/src/components/tracks/RadarChart.js` — Radar visualization backing F-011
- `frontend/src/components/trends/TrendsSection.js` — Trends view backing F-009 with the `desctiption` (sic) consumer
- `frontend/src/components/trends/FeatureSelect.js` — Seven-option dropdown backing F-009
- `frontend/src/components/trends/LineChart.js` — Line visualization backing F-012 with the "3 Year Rolling Average" label
- `frontend/src/components/trends/features.json` — Audio feature descriptions consumed by F-009
- `frontend/src/components/navigation/Sidebar.js` — Sidebar with tabs at IDs 0, 1, 3 for F-007
- `frontend/src/components/navigation/Hamburger.js` — Mobile sidebar toggle shared by F-008, F-009, F-010
- `frontend/src/components/navigation/Tab.js`, `SmallTab.js`, `Section.js` — Navigation primitives for F-007

### 2.6.2 Folders Explored

- `/` — Root directory containing Docker, Compose, dependency files, and the `api/` and `frontend/` subtrees
- `api/` — Flat backend Python package containing the four files implementing F-001 through F-006, F-013, F-014, F-015, and F-017
- `frontend/` — Frontend project root containing the React source, public assets, and production build directory
- `frontend/src/` — React source root containing `App.js`, `index.js`, and the `components/` and `styles/` subtrees
- `frontend/src/components/` — Component tree partitioned by feature (about, tracks, trends, navigation)
- `frontend/src/components/tracks/` — Components backing F-008 and F-011
- `frontend/src/components/trends/` — Components backing F-009 and F-012, plus `features.json`
- `frontend/src/components/about/` — Components backing F-010
- `frontend/src/components/navigation/` — Components backing F-007
- `frontend/src/styles/` — Global stylesheet consumed by F-007
- `frontend/public/` — HTML shell and PWA manifest delivered by F-001
- `frontend/build/` — Production build output served as static assets by F-001

### 2.6.3 Cross-References to Other Specification Sections

- **Section 1.1 EXECUTIVE SUMMARY** — Establishes the project identity, business problem, stakeholders, and value proposition that the F-001 through F-017 catalog operationalizes
- **Section 1.2 SYSTEM OVERVIEW** — Documents the high-level capabilities, component diagram, and data model that the Functional Requirements Tables in section 2.2 elaborate
- **Section 1.3 SCOPE** — Defines in-scope and out-of-scope items; the feature catalog in section 2.1 includes only the in-scope items, and the Implementation Considerations in section 2.4 reference the documented exclusions
- **Section 1.4 References** — Provides the specification-wide source inventory; section 2.6 expands on it with feature-level traceability

# 3. Technology Stack

This section documents the complete technology stack of the Hot Stuff Billboard Hot 100 visualization application, as observed in the repository's source files, Dockerfile, Compose manifest, and package manifests. The stack is intentionally narrow: a two-service Docker Compose deployment consisting of a Python/Flask REST API backed by PostgreSQL and a Create React App single-page frontend. Every choice documented below is grounded in code observed in the repository; technology selections that might be expected from common templates (AWS, Auth0, MongoDB, Langchain, TypeScript, TailwindCSS, React-Native, native mobile binaries) are explicitly **not present** in this codebase and are documented as such where relevant.

## 3.1 PROGRAMMING LANGUAGES

### 3.1.1 Languages by Platform / Component

| Component | Language | Version | Source of Truth |
|---|---|---|---|
| Backend service (`api/`) | Python | 3.11 (slim-buster variant) | `Dockerfile` line 1 (`FROM python:3.11-slim-buster`) |
| Frontend SPA (`frontend/src/`) | JavaScript (ES2017+) with JSX | Targeted by `react-scripts` 4.0.3 | `frontend/package.json` |
| Database query layer | SQL (PostgreSQL dialect, generated via SQLAlchemy) | PostgreSQL 15 dialect | `api/routes.py`, `api/models.py` |
| Frontend styling | CSS (global) + CSS-in-JS (component) | n/a | `frontend/src/styles/index.css`, `styled-components` 5.3.0 |
| Static shell and configuration | HTML5 + JSON | n/a | `frontend/public/index.html`, `frontend/public/manifest.json`, `frontend/src/components/trends/features.json` |

### 3.1.2 Selection Justification

#### Python 3.11 for the Backend

Python 3.11 was selected for the backend tier and is locked at the container level via the official `python:3.11-slim-buster` image. The slim-buster variant minimizes the production image surface while still allowing the apt-installable native dependencies required by `psycopg2` (the PostgreSQL driver). Python is a natural fit for this application because:

- The data-analytics core relies on `pandas` for weekly aggregation, rolling averages, and proportional feature scaling (see `api/funcs.py`).
- Flask provides a minimal, low-ceremony HTTP layer that aligns with the small number of read-only endpoints (`/`, `/api/`, `/api/track/<id>`, `/api/week/<date>`, `/api/artist/<name>`, `/api/analysis/<feature>`).
- SQLAlchemy + Marshmallow give a clean, declarative ORM-to-JSON pipeline appropriate for a read-only analytics surface.

#### JavaScript (Plain JS, no TypeScript) for the Frontend

The frontend is implemented in plain JavaScript with JSX. All component files in `frontend/src/components/` use the `.js` extension; there are no `.ts` or `.tsx` files in the repository. This is an explicit deviation from the TypeScript default and is consistent with the Create React App 4.0.3 JavaScript template. The choice keeps the toolchain light and avoids type-system overhead for a UI of modest size.

#### SQL via SQLAlchemy

No raw SQL files exist in the repository. All SQL is generated by SQLAlchemy 1.4.19 in `api/routes.py` and `api/models.py`. A notable PostgreSQL-dialect-specific pattern is the case-insensitive partial-match artist search, which uses `func.lower(...)` combined with `LIKE '%pattern%'` semantics in `api/routes.py`.

#### CSS and Styled-Components, No Utility Framework

Styling is delivered through two complementary mechanisms: a global `frontend/src/styles/index.css` stylesheet and component-scoped CSS-in-JS via `styled-components` 5.3.0 for the navigation primitives (`Sidebar`, `Tab`, `SmallTab`, `Hamburger`, `Section`). **No utility-first or component CSS framework is present**: TailwindCSS, Bootstrap, Material UI, and Chakra UI are all absent from `frontend/package.json`. This is a deliberate deviation from any TailwindCSS default.

### 3.1.3 Constraints and Dependencies

| Constraint | Reason | Affected Behavior |
|---|---|---|
| Python pinned at 3.11 | Image-level pin in `Dockerfile` | Local-dev `venv` (referenced by `start-api` script) should match this major.minor for parity |
| `psycopg2` requires `libpq-dev` and `gcc` at build time | Native compilation against PostgreSQL client library | `Dockerfile` installs these via `apt-get install` before `pip3 install` |
| `NODE_OPTIONS=--openssl-legacy-provider` set in Compose | Webpack 4 (bundled inside `react-scripts` 4.0.3) is incompatible with OpenSSL 3 defaults in Node 17+ | Required for the Compose-level Node runtime; documented in `docker-compose.yml` |
| Browserslist target | Production: `>0.2%`, `not dead`, `not op_mini all`; Development: last Chrome / Firefox / Safari | Defines the JavaScript transpilation floor enforced by `react-scripts` |

---

## 3.2 FRAMEWORKS & LIBRARIES

### 3.2.1 Backend Python Frameworks

The backend is a single Flask process bootstrapped in `api/__init__.py`. All Python dependencies are exact-pinned via the `==` operator in `requirements.txt`, which improves reproducibility but requires manual maintenance for security advisories.

#### Core Web Stack

| Package | Version | Role | Justification |
|---|---|---|---|
| `Flask` | 2.0.1 | HTTP application object, routing, static-file serving | Minimal microframework appropriate for a six-endpoint read-only API |
| `Flask-Cors` | 3.0.10 | CORS handling | Registered as `CORS(app)` with no origin allow-list (open CORS), suitable for public-read content |
| `Flask-SQLAlchemy` | 2.5.1 | Flask integration for SQLAlchemy | Provides the `db` object and request-scoped session lifecycle |
| `flask-marshmallow` | 0.14.0 | Flask integration for Marshmallow | Provides the `ma` object and SQLAlchemy schema base classes |

#### ORM and Serialization

| Package | Version | Role |
|---|---|---|
| `SQLAlchemy` | 1.4.19 | ORM core; defines `Tracks` and `YearlyAvg` models in `api/models.py` |
| `marshmallow` | 3.12.1 | Schema-based JSON serialization |
| `marshmallow-sqlalchemy` | 0.26.1 | Bridges SQLAlchemy models to Marshmallow schemas |
| `psycopg2` | 2.9.6 | PostgreSQL DB-API driver (compiled) |
| `psycopg2-binary` | 2.9.5 | Binary fallback distribution of the same driver |

The duplicate inclusion of both `psycopg2` and `psycopg2-binary` is unusual; in practice the binary distribution is sufficient for most environments, while the source distribution is preferred for performance-critical deployments. The Dockerfile installs `libpq-dev` and `gcc` to support compilation of the source distribution.

#### Data Analytics Stack

| Package | Version | Role |
|---|---|---|
| `pandas` | 2.0.0 | Used by `api/funcs.py` for weekly aggregation (`get_weekly_data`) and 5-year rolling means (`get_rolling_avg`) |
| `numpy` | 1.24.2 | Numerical foundation required by pandas |
| `python-dateutil` | 2.8.2 | Date parsing in `api/funcs.py` and `api/routes.py` |
| `pytz` | 2021.1 | Timezone handling support for date normalization |
| `tzdata` | 2023.3 | IANA timezone database |

#### Flask Transitive Dependencies (Pinned)

| Package | Version | Role |
|---|---|---|
| `Jinja2` | 3.0.1 | Template engine (Flask transitive; not actively used since responses are JSON) |
| `Werkzeug` | 2.2.3 | WSGI utilities underlying Flask |
| `MarkupSafe` | 2.1.2 | HTML escaping for Jinja2 |
| `itsdangerous` | 2.0.1 | Cryptographic signing (Flask transitive) |
| `click` | 8.1.3 | CLI utilities used by `flask` command |
| `six` | 1.16.0 | Python 2/3 compatibility shim (transitive) |
| `greenlet` | 2.0.2 | Concurrency primitive used by SQLAlchemy |

#### Declared but Unused or Inactive

| Package | Version | Status |
|---|---|---|
| `gunicorn` | 20.1.0 | Declared in `requirements.txt` but **never invoked**; `Dockerfile` runs `python3 app.py` (Flask's development server). This is documented in section 2.4.1 as a known production-readiness gap. |
| `python-dotenv` | 0.18.0 | Declared but `api/__init__.py` performs no `dotenv.load_dotenv()` call and the database URL is hardcoded |

### 3.2.2 Frontend JavaScript Frameworks

The frontend is a Create React App project with React 17 as the UI runtime. Declared dependencies use caret (`^`) ranges with the exception of `react-scripts`, which is exact-pinned at `4.0.3`.

#### Core React Stack

| Package | Version Range | Role | Justification |
|---|---|---|---|
| `react` | ^17.0.2 | UI runtime | Industry-standard library for interactive SPAs |
| `react-dom` | ^17.0.2 | DOM bindings for React | Required peer of `react` |
| `react-scripts` | 4.0.3 (exact) | CRA build pipeline (Webpack 4, Babel, Jest, ESLint, Workbox) | Hides build complexity behind a curated default |

The exact pin on `react-scripts` is significant: Webpack 4 (bundled inside CRA 4) is the version that requires `NODE_OPTIONS=--openssl-legacy-provider` on Node 17+, which is supplied through the Compose file.

#### Visualization

| Package | Version Range | Role | Justification |
|---|---|---|---|
| `@amcharts/amcharts4` | ^4.10.19 | Radar chart (Tracks tab) and XY line chart (Trends tab) | Single charting runtime shared across both visualization features (F-011, F-012). The animated theme is applied globally via `am4core.useTheme(am4themes_animated)` in both `RadarChart.js` and `LineChart.js`. |

#### Styling

| Package | Version Range | Role |
|---|---|---|
| `styled-components` | ^5.3.0 | CSS-in-JS for navigation primitives in `frontend/src/components/navigation/` |

#### Test Tooling (Declared, No Tests Present)

| Package | Version Range | Role |
|---|---|---|
| `@testing-library/jest-dom` | ^5.11.4 | Jest DOM matchers (CRA template default) |
| `@testing-library/react` | ^11.1.0 | React component testing (CRA template default) |
| `@testing-library/user-event` | ^12.1.10 | User-interaction simulation (CRA template default) |

Although these libraries are declared, no test files exist anywhere in `frontend/src/`. Section 1.3.3 (Out-of-Scope Elements) confirms that automated tests are explicitly out of scope.

#### Declared but Unused (Verified by Source Search)

| Package | Version Range | Status |
|---|---|---|
| `axios` | ^0.21.1 | **Not imported**; the application uses native `fetch()` instead |
| `plotly.js` | ^1.58.4 | **Not imported**; charting is delivered exclusively by amCharts4 |
| `react-plotly.js` | ^2.5.1 | **Not imported**; counterpart to `plotly.js` |
| `web-vitals` | ^1.0.1 | Declared from CRA template; no `reportWebVitals()` reporting is wired in `frontend/src/index.js` |

These unused dependencies inflate the `node_modules` tree and the production bundle (where they are tree-shaken to varying degrees). Section 1.3.3 lists their removal as a future-phase consideration.

### 3.2.3 Build and Dev Configuration

`frontend/package.json` declares the following scripts and configuration that govern the development and build experience:

- **`start`** — Runs the CRA development server (`react-scripts start`) on port 3000.
- **`start-api`** — Boots the Flask development server outside Docker via `cd .. && venv/bin/flask run --no-debugger`, assuming a sibling Python virtualenv at `../venv/`.
- **`build`** — Emits a production bundle to `frontend/build/` using `react-scripts build`.
- **`test`** — Invokes `react-scripts test`; no test files exist for it to discover.
- **`eject`** — Standard CRA eject (not used).
- **`proxy`** — `"http://localhost:5000"`; during `npm start`, browser fetches to relative API paths are forwarded to the Flask backend, eliminating CORS concerns during development.
- **`browserslist`** — Production targets `>0.2%`, `not dead`, `not op_mini all`; development targets the last version of Chrome, Firefox, and Safari.
- **`eslintConfig`** — Extends `react-app` and `react-app/jest`, the CRA-standard ESLint preset.

### 3.2.4 Frameworks Explicitly Not Present

To remove ambiguity, the following technology choices that appear in common defaults are **not** part of this stack and have no presence in the repository:

| Absent Technology | Verification |
|---|---|
| AI / LLM frameworks (Langchain, LlamaIndex, etc.) | Not in `requirements.txt`; no AI features in scope |
| Auth0 or any authentication library | No `flask-login`, no JWT library, no OAuth client; no login routes in `api/routes.py` |
| TypeScript | No `.ts`/`.tsx` files; no `typescript` in `frontend/package.json` |
| TailwindCSS / Bootstrap / Material UI | Not in `frontend/package.json`; no `tailwind.config.js` |
| React-Native | Not in `frontend/package.json`; no native shells in repository |
| Native mobile / desktop runtimes (Swift, Kotlin, Objective-C, Electron) | No platform projects exist |

---

## 3.3 OPEN SOURCE DEPENDENCIES

### 3.3.1 Package Registries

| Registry | Manifest | Lockfile | Count |
|---|---|---|---|
| PyPI | `requirements.txt` | None (pinned via `==`) | 23 packages |
| npm | `frontend/package.json` | `frontend/package-lock.json` | 12 declared dependencies plus locked transitive tree |

Python dependencies are installed at image build time via `pip3 install -r requirements.txt` in the `Dockerfile`. JavaScript dependencies are resolved at frontend build time via the npm-managed lockfile.

### 3.3.2 Lockfile Discipline

#### Python — Exact Pinning

Every entry in `requirements.txt` uses the `==` exact-version operator. This delivers reproducible builds without a separate lockfile but requires explicit maintenance to absorb security patches in transitive dependencies (e.g., `Werkzeug`, `Jinja2`, `MarkupSafe`).

#### JavaScript — Caret Ranges with Lockfile

Declared dependencies in `frontend/package.json` use caret (`^`) ranges, allowing minor and patch updates within the same major version on a fresh `npm install`. Reproducibility is maintained via `package-lock.json`. The single exception is `react-scripts`, which is exact-pinned to `4.0.3` to avoid accidental upgrades into incompatible CRA major versions.

### 3.3.3 Native Build Dependencies

The backend container build (per `Dockerfile`) requires two apt-installable system packages:

| Package | Purpose |
|---|---|
| `libpq-dev` | PostgreSQL client library headers required to compile `psycopg2` from source |
| `gcc` | C compiler used during the `psycopg2` build |

These dependencies are installed before `pip3 install` and remain in the final image (the Dockerfile does not implement a multi-stage build).

### 3.3.4 Compiled Frontend Asset Inventory

The `frontend/build/asset-manifest.json` file enumerates all compiled assets emitted by `react-scripts build`. Notable observations:

- A `xlsx.<hash>.chunk.js` chunk appears in the manifest. No `xlsx` package is declared in `frontend/package.json`, indicating it is pulled in transitively through one of the declared dependencies (most likely a chart library or its dependency tree).
- License sidecar files (`*.LICENSE.txt`) accompany three of the larger chunks (4, 5, and 6), preserving third-party attribution emitted by Webpack's `TerserPlugin` extraction step.

---

## 3.4 THIRD-PARTY SERVICES

### 3.4.1 External APIs (Out-of-Repository Pipeline)

Per the system overview in section 1.2.1, this repository represents the **read-side** of a two-stage pipeline. The write-side — which calls external services — is **not implemented** in this repository.

| Service | Status in Repository | Evidence |
|---|---|---|
| **Spotify Web API** | Referenced only in documentation | Mentioned in `README.md` and `frontend/src/components/about/AboutSection.js`. No `spotipy` package in `requirements.txt`; no Python source uses any Spotify SDK. Audio features arrive in the database pre-enriched by an external job. |
| **Billboard.com Hot 100 chart pages** | Referenced only in documentation | Mentioned in `README.md`. No scraper code exists in `api/` or anywhere else in the repository. |

The application consumes only the persisted `Tracks` and `YearlyAvg` rows produced by these out-of-repo processes; it does not initiate any outbound HTTP traffic to Spotify or Billboard.

### 3.4.2 External Resources Loaded at Runtime by the Browser

| Resource | Source | Loading Pattern |
|---|---|---|
| **Google Fonts** (Jost family) | `fonts.googleapis.com` / `fonts.gstatic.com` | Preconnect hints + `<link>` tag with `display=swap` in `frontend/public/index.html` |

This is the only third-party resource loaded by the SPA at runtime. There are **no analytics tags** (Google Analytics, Segment, Mixpanel), no advertising tags, and no third-party social scripts in `index.html`.

### 3.4.3 Authentication and Authorization Services

**None.** The application is configured as a public, unauthenticated read-only web property.

| Capability | Status |
|---|---|
| OAuth / OIDC client | Not present |
| Session middleware (Flask-Login, Flask-Session) | Not present |
| JWT issuance or verification | Not present |
| Login or logout routes | Not present in `api/routes.py` |
| Auth0 / Cognito / Okta integration | Not present |

Section 2.4.4 (Security Implications) classifies the absence of authentication as an explicit non-goal acceptable for a public-read use case.

### 3.4.4 Monitoring and Observability Tools

**None.** The repository contains no observability instrumentation:

| Concern | Status |
|---|---|
| Structured logging (e.g., `structlog`, `loguru`) | Not present |
| Metrics endpoint (Prometheus, statsd) | Not present |
| APM agent (DataDog, New Relic, AppDynamics) | Not present |
| Error reporting (Sentry, Rollbar, Bugsnag) | Not present |
| RUM / web vitals reporting | `web-vitals` 1.0.1 is declared in `package.json` but never wired into a `reportWebVitals()` callback |

### 3.4.5 Cloud Services

**None.** The repository targets a generic Docker host as its sole deployment substrate.

| Cloud Concern | Status |
|---|---|
| AWS / Azure / GCP SDK | Not present |
| Terraform / CloudFormation / Pulumi / CDK | No IaC files in repository |
| S3 / Azure Blob / GCS object storage | Not present |
| Managed databases (RDS, CloudSQL) | Not configured; PostgreSQL runs as a Compose service |
| Serverless / FaaS | Not present |

---

## 3.5 DATABASES & STORAGE

### 3.5.1 Primary Database — PostgreSQL 15

The database tier is a single PostgreSQL 15 instance defined in `docker-compose.yml`:

| Property | Value | Source |
|---|---|---|
| Image | `postgres:15` (official Docker Hub image) | `docker-compose.yml` |
| Connection string | `postgresql://postgres:postgres@postgres/db` (hardcoded) | `api/__init__.py` |
| User | `postgres` | `docker-compose.yml` (`POSTGRES_USER`) |
| Password | `postgres` | `docker-compose.yml` (`POSTGRES_PASSWORD`) |
| Database | `db` | `docker-compose.yml` (`POSTGRES_DB`) |
| Host port mapping | `5432:5432` | `docker-compose.yml` |
| Volume | `./data:/data` (host bind-mount) | `docker-compose.yml` |

PostgreSQL was selected over the user-supplied default of MongoDB because the underlying data model is intrinsically relational: `Tracks` rows are normalized weekly chart entries, and `YearlyAvg` rows are pre-aggregated annual rollups joined logically by year. Section 2.4.4 documents that the hardcoded credentials are a known development-only limitation that must not be reused in production.

### 3.5.2 ORM Layer

The ORM is `SQLAlchemy 1.4.19` accessed via `Flask-SQLAlchemy 2.5.1`. The bootstrap in `api/__init__.py` performs three things relevant to persistence:

- Constructs the `Flask` app with `static_folder='../frontend/build'` and `static_url_path='/'`.
- Sets `SQLALCHEMY_DATABASE_URI` to the hardcoded URL above.
- Sets `SQLALCHEMY_TRACK_MODIFICATIONS = False` to suppress Flask-SQLAlchemy's deprecation warning and avoid the associated event-tracking overhead.

Two ORM models are defined in `api/models.py`:

#### `Tracks` Model

Represents one chart entry per (week, rank) tuple, enriched with Spotify audio features.

| Column | Type | Purpose |
|---|---|---|
| `id` | Integer | Primary key |
| `week` | Date | Saturday-boundary chart week |
| `rank` | Integer | Chart position (1–100) |
| `track` | String | Track title |
| `artist` | String | Artist name |
| `spotify_id` | String | Spotify track identifier |
| `tempo` | Float | Beats per minute |
| `energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `loudness` | Float | Spotify audio features |

Section 2.4.1 notes that `Tracks.__init__` omits `spotify_id` despite the column existing — a known constructor-vs-schema discrepancy.

#### `YearlyAvg` Model

Pre-aggregated annual feature averages keyed by year string.

| Column | Type | Purpose |
|---|---|---|
| `index` | Integer | Primary key |
| `year` | String | Year (stored as string) |
| `energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `tempo` | Float | Pre-aggregated annual averages (no `loudness`) |

### 3.5.3 Database Drivers

Both `psycopg2` 2.9.6 (compiled) and `psycopg2-binary` 2.9.5 (binary) are pinned in `requirements.txt`. Compilation is supported by `libpq-dev` and `gcc` installed in the Dockerfile.

### 3.5.4 Serialization Layer

JSON response shapes are defined by Marshmallow schemas, decoupling wire format from ORM definitions.

| Component | Version | Role |
|---|---|---|
| `marshmallow` | 3.12.1 | Schema base classes |
| `flask-marshmallow` | 0.14.0 | Flask integration; provides the `ma` instance |
| `marshmallow-sqlalchemy` | 0.26.1 | Auto-generation of schemas from SQLAlchemy models |

Two schemas are defined in `api/models.py` — `TrackSchema` and `YearlyAvgSchema` — and both are used as either single-instance or `many=True` serializers in `api/routes.py`.

### 3.5.5 Caching Layer

**None.** No caching layer is present in the repository:

- No Redis or Memcached service in `docker-compose.yml`
- No `Flask-Caching`, `redis`, or `pymemcache` in `requirements.txt`
- No in-process LRU caches applied to route handlers
- No HTTP cache headers explicitly set by route handlers
- No CDN configuration

Given that the data is updated weekly and the dataset is small (≤100 rows per week, ≤~70 annual aggregate rows), caching has been left as a future-phase concern.

### 3.5.6 Storage Services

The repository's only persistent storage is PostgreSQL itself, backed by the host bind-mount at `./data`. There are no object stores (S3, Azure Blob, GCS), no file-upload endpoints, and no blob columns in either model. The static React build at `frontend/build/` is shipped as immutable filesystem content inside the `api` container.

### 3.5.7 Connection Pooling

The application relies on Flask-SQLAlchemy's default connection-pool configuration. `api/__init__.py` does not set any of the following:

- `SQLALCHEMY_POOL_SIZE`
- `SQLALCHEMY_MAX_OVERFLOW`
- `SQLALCHEMY_POOL_RECYCLE`
- `SQLALCHEMY_POOL_TIMEOUT`

Section 2.4.3 (Scalability Considerations) notes that database concurrency is therefore bounded by SQLAlchemy's default pool, which is acceptable for the single-process Flask development server but would require revisiting under a multi-worker WSGI deployment.

---

## 3.6 DEVELOPMENT & DEPLOYMENT

### 3.6.1 Development Tools

| Tool | Version / Source | Role |
|---|---|---|
| Python | 3.11 (image-pinned) | Backend runtime |
| Node.js | Implicitly via `react-scripts` 4.0.3 (Node 14+ supported, `--openssl-legacy-provider` required on Node 17+) | Frontend build runtime |
| pip | `pip3` from the slim-buster image | Python package install |
| npm | Bundled with Node | JavaScript package install |
| ESLint | Bundled inside `react-scripts` 4.0.3 with `eslintConfig` extending `react-app`, `react-app/jest` | Static analysis for the SPA |
| Docker Compose | File schema version `"3"` | Local orchestration |

### 3.6.2 Build System

#### Backend Container Build

The `Dockerfile` orchestrates a single-stage image build:

1. `FROM python:3.11-slim-buster` — base image.
2. `WORKDIR /app` — working directory for subsequent instructions.
3. `apt-get update && apt-get install -y libpq-dev gcc` — native dependencies for `psycopg2`.
4. `COPY requirements.txt requirements.txt` — copy manifest first to maximize layer caching.
5. `pip3 install -r requirements.txt` — install Python dependencies.
6. `COPY . .` — copy the entire repository (subject to `.dockerignore`).
7. `EXPOSE 5000` — declare the Flask port.
8. `CMD ["python3", "app.py"]` — start the application.

The `.dockerignore` file excludes three entries from the build context to keep the image lean and avoid leaking host artifacts:

- `/frontend/node_modules` — npm dependency tree (rebuilt elsewhere)
- `/venv` — local Python virtualenv
- `/data` — the PostgreSQL data directory bind-mount

#### Frontend Production Build

The `react-scripts build` command produces hashed assets in `frontend/build/`:

- `index.html` — SPA shell loaded by Flask at the `/` route.
- `asset-manifest.json` — manifest mapping logical names to hashed chunk filenames.
- `manifest.json` — PWA web app manifest.
- `static/css/` and `static/js/` — hashed CSS and JS chunks (with sourcemaps and `*.LICENSE.txt` sidecars where applicable).

This build must exist at container start time because the Flask app is configured with `static_folder='../frontend/build'` and the `/` route serves `index.html` from that directory.

### 3.6.3 Containerization

The deployment unit is a Docker Compose stack (file schema version `"3"`) defining two services and one named volume.

```mermaid
graph LR
    Browser["Web Browser"]

    subgraph ComposeStack["Docker Compose Stack"]
        subgraph ApiService["api service"]
            Flask["Flask 2.0.1<br/>python:3.11-slim-buster<br/>CMD: python3 app.py"]
            BuildOutput["frontend/build/<br/>(static SPA assets)"]
            Flask --- BuildOutput
        end

        subgraph PgService["postgres service"]
            Postgres[("PostgreSQL 15<br/>postgres:15<br/>db: db")]
        end

        DataVolume[("./data host bind-mount")]
    end

    Browser -- "HTTP :80" --> Flask
    Flask -- "psycopg2 / SQLAlchemy 1.4.19" --> Postgres
    Postgres -- "persistence" --> DataVolume
    Browser -. "exposed :5432" .-> Postgres
```

Service-by-service summary:

| Property | `api` Service | `postgres` Service |
|---|---|---|
| Build / Image | `build: .` (uses repo `Dockerfile`) | `image: postgres:15` |
| Restart Policy | `on-failure` | (default) |
| Depends On | `postgres` | n/a |
| Environment | `NODE_OPTIONS=--openssl-legacy-provider` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| Ports | `80:5000` (host:container) | `5432:5432` |
| Volumes | `.:/app/` (live-reload bind-mount) | `./data:/data` |

Notable behaviors of the Compose configuration:

- The `.:/app/` bind-mount on the `api` service enables live source reload during development (any host file edit is visible inside the container).
- The `5432:5432` mapping exposes the database port directly to the host. Section 2.4.4 flags this as a development convenience that should be removed in production.
- The `NODE_OPTIONS` environment variable accommodates the OpenSSL 3 incompatibility in Webpack 4 when a development workflow is run inside a Node 17+ environment.

### 3.6.4 Local Development Workflow

Two workflows are supported by `frontend/package.json`:

1. **Containerized** — `docker compose up` builds the image, starts both services, and serves the API (which itself serves the React build) at `http://localhost`.
2. **Hybrid** — `npm start` inside `frontend/` runs the CRA dev server with hot reload, while `npm run start-api` (`cd .. && venv/bin/flask run --no-debugger`) runs Flask outside Docker. The CRA `proxy: "http://localhost:5000"` forwards API calls during this mode.

### 3.6.5 CI / CD

**Not present.** The repository contains no CI/CD configuration files:

| Provider | Expected Path | Status |
|---|---|---|
| GitHub Actions | `.github/workflows/` | Not present |
| GitLab CI | `.gitlab-ci.yml` | Not present |
| Travis CI | `.travis.yml` | Not present |
| CircleCI | `.circleci/config.yml` | Not present |
| Jenkins | `Jenkinsfile` | Not present |

Section 1.3.3 (Out-of-Scope Elements) lists CI/CD pipelines as an explicit non-goal of this specification. Deployment is therefore performed manually via `docker compose up` against a target host.

### 3.6.6 WSGI Server Posture

`gunicorn` 20.1.0 is declared in `requirements.txt`, but the `Dockerfile` `CMD` invokes `python3 app.py`, and `app.py` calls `app.run(host='0.0.0.0')`. The Flask development server is therefore the WSGI runtime in all environments served by this Dockerfile. Section 1.2.1 documents this as a known production-readiness gap, and section 1.3.3 lists migration to gunicorn as a future-phase consideration.

### 3.6.7 Testing

**Not present.** The frontend declares the CRA-default Jest + Testing Library stack in `frontend/package.json` (`@testing-library/jest-dom`, `@testing-library/react`, `@testing-library/user-event`), but no test files exist anywhere in `frontend/src/`. The backend has no test framework declared (no `pytest`, no `unittest` configuration, no `tests/` directory). Section 1.3.3 lists automated tests as out of scope.

---

## 3.7 STACK INTEGRATION OVERVIEW

The following diagram consolidates the Technology Stack into a single end-to-end view, showing how each layer's chosen technologies integrate with the layers above and below.

```mermaid
flowchart TB
    subgraph ClientTier["Client Tier - Browser"]
        SPA["React 17.0.2 SPA<br/>JavaScript + JSX"]
        StyledC["styled-components 5.3.0<br/>+ index.css"]
        AmCharts["@amcharts/amcharts4<br/>Radar + Line"]
        Fonts["Google Fonts<br/>Jost family"]
        SPA --- StyledC
        SPA --- AmCharts
        SPA --- Fonts
    end

    subgraph BuildTier["Build Tier"]
        CRA["react-scripts 4.0.3<br/>Webpack 4 + Babel"]
        BuildArtifact["frontend/build/<br/>asset-manifest.json"]
        CRA -- "react-scripts build" --> BuildArtifact
    end

    subgraph BackendTier["Backend Tier - api container"]
        BaseImg["python:3.11-slim-buster"]
        FlaskApp["Flask 2.0.1<br/>+ Flask-Cors 3.0.10"]
        ORM["SQLAlchemy 1.4.19<br/>Flask-SQLAlchemy 2.5.1"]
        Schemas["Marshmallow 3.12.1<br/>+ marshmallow-sqlalchemy 0.26.1"]
        Analytics["pandas 2.0.0 + numpy 1.24.2<br/>python-dateutil 2.8.2"]
        Driver["psycopg2 2.9.6 / psycopg2-binary 2.9.5"]
        BaseImg --> FlaskApp
        FlaskApp --> ORM
        ORM --> Schemas
        FlaskApp --> Analytics
        ORM --> Driver
    end

    subgraph DataTier["Data Tier - postgres container"]
        PG[("PostgreSQL 15<br/>db: tracks, yearly_avg")]
        Volume[("./data bind-mount")]
        PG --- Volume
    end

    subgraph ExternalPipeline["External Out-of-Repo Pipeline"]
        Scraper["Weekly Billboard Scraper"]
        Spotipy["Spotify Web API client"]
        Scraper -. "enriches with" .-> Spotipy
    end

    SPA -- "fetch (native)" --> FlaskApp
    BuildArtifact -- "served as static_folder" --> FlaskApp
    Driver -- "TCP 5432" --> PG
    Scraper -- "weekly INSERT" --> PG
    Spotipy -- "audio features" --> Scraper
```

The diagram makes three integration points explicit:

1. **Frontend ↔ Backend**: The browser uses native `fetch()` (not `axios`) to call JSON routes under `/api/*`. In production the SPA is served from the same Flask process, eliminating cross-origin concerns; `Flask-Cors` is registered globally with no allow-list as a defense-in-depth measure.
2. **Backend ↔ Database**: A single SQLAlchemy connection (with Flask-SQLAlchemy default pooling) speaks the PostgreSQL wire protocol over TCP 5432 inside the Compose network. `marshmallow-sqlalchemy` projects ORM rows directly into JSON.
3. **External Pipeline ↔ Database**: The weekly scraper and Spotify enrichment job (both out of repository) write into the same PostgreSQL instance that the backend reads from, completing the data lifecycle without introducing additional service boundaries within this codebase.

---

## 3.8 References

#### Files Examined

- `Dockerfile` — Container build recipe; locks Python 3.11-slim-buster, installs `libpq-dev`/`gcc`, runs `python3 app.py`
- `docker-compose.yml` — Two-service orchestration (`api` + `postgres:15`); environment variables, port mappings, volumes
- `requirements.txt` — 23 exact-pinned Python dependencies (Flask 2.0.1, SQLAlchemy 1.4.19, pandas 2.0.0, gunicorn 20.1.0, etc.)
- `.dockerignore` — Excludes `frontend/node_modules`, `venv`, and `data` from build context
- `app.py` — Backend entrypoint; runs Flask on `0.0.0.0`
- `api/__init__.py` — Flask bootstrap; CORS, hardcoded DB URL, `db`/`ma` initialization, static folder pointer to `../frontend/build`
- `api/models.py` — `Tracks` and `YearlyAvg` SQLAlchemy models plus their Marshmallow schemas
- `api/routes.py` — Six HTTP handlers including the `func.lower(...) LIKE` pattern for artist search
- `api/funcs.py` — pandas-based weekly aggregation and 5-year rolling-mean helpers
- `frontend/package.json` — React 17.0.2 / `react-scripts` 4.0.3 / amCharts4 manifest; declares unused `axios`, `plotly.js`, `react-plotly.js`, `web-vitals`
- `frontend/package-lock.json` — Locked transitive npm dependency tree
- `frontend/public/index.html` — SPA shell with Google Fonts preconnect/load
- `frontend/public/manifest.json` — PWA web app manifest
- `frontend/src/index.js` — React DOM bootstrap with `StrictMode`
- `frontend/src/App.js` — Top-level UI composition and tab indices (0/1/3)
- `frontend/src/components/trends/LineChart.js` — amCharts4 import pattern (`am4core`, `am4charts`, animated theme)
- `frontend/src/components/tracks/RadarChart.js` — amCharts4 radar chart import pattern
- `frontend/src/components/trends/features.json` — Static feature descriptions
- `frontend/src/styles/index.css` — Global stylesheet
- `frontend/build/asset-manifest.json` — Hashed asset registry including transitive `xlsx` chunk
- `README.md` — References to Spotipy and Billboard scraping (out-of-repo)

#### Folders Explored

- `/` — Root repository structure (Docker, Compose, dependency manifests, README, `app.py`, `api/`, `frontend/`)
- `/api/` — Backend Python source (4 files, flat structure)
- `/frontend/` — React workspace (`package.json`, lockfile, `src/`, `public/`, `build/`)
- `/frontend/src/` — App composition, entrypoint, components, styles
- `/frontend/public/` — SPA shell and PWA manifest
- `/frontend/build/` — Production build output
- `/frontend/src/components/` — Feature folders (`about`, `tracks`, `trends`, `navigation`)
- `/frontend/src/components/trends/` — `TrendsSection`, `FeatureSelect`, `LineChart`, `features.json`
- `/frontend/src/components/tracks/` — `TracksSection`, `DatePicker`, `RadarChart`
- `/frontend/src/components/navigation/` — `Hamburger`, `Sidebar`, `Tab`, `SmallTab`, `Section`

#### Technical Specification Sections Cross-Referenced

- `1.2 SYSTEM OVERVIEW` — Project context, system topology diagram, technical approach narrative
- `1.3 SCOPE` — In-scope/out-of-scope elements; confirms absence of CI/CD, tests, observability, authentication
- `2.3 FEATURE RELATIONSHIPS` — Shared components (pandas, amCharts4, ORM models) and integration points
- `2.4 IMPLEMENTATION CONSIDERATIONS` — Technical constraints, performance, scalability, security implications, maintenance requirements

# 4. Process Flowchart

This section consolidates the runtime behavior of the Hot Stuff system into a sequence of process diagrams and state machines. It traces every user journey from browser entry to chart rendering, documents the integration paths between the React SPA, the Flask API, and the PostgreSQL data store, and explicitly catalogs the validation, state-management, and error-handling postures that are present (and absent) in the codebase. Where behavior diverges from documentation (e.g., the "3 Year" rolling-average label vs. the actual five-year window), this section uses the code as the source of truth.

## 4.1 SYSTEM WORKFLOWS

The application exposes four user-facing workflows (one per navigable tab plus the bootstrap journey) and two programmatic-only API endpoints. The dependency relationships between these workflows and their backing features are catalogued in section 2.3. The following subsections describe each workflow at the granularity required to operate, debug, or extend it.

### 4.1.1 Workflow Inventory and High-Level System View

The diagram below shows the end-to-end flow across all actors: the End User in the browser, the React SPA, the Flask API, the PostgreSQL database, and the External Pipeline that populates the database out-of-band.

```mermaid
flowchart LR
    subgraph BrowserLane["End User Browser"]
        UStart([User navigates to host])
        UClick[/User clicks Sidebar tab/]
        USubmit[/User submits date or feature/]
        UDone([View rendered])
    end

    subgraph SPALane["React SPA frontend/build"]
        Boot[App.js mounts<br/>activeTab=0, nav=false]
        TabRouter{Active Tab?}
        Fetch[fetch /api/week or /api/analysis]
        ResponseHandler{HTTP status &gt; 299?}
        EmptyHandler{data.length === 0?}
        Renderer[Render list + amCharts component]
        ErrorRenderer[Render h1.error]
    end

    subgraph FlaskLane["Flask API api container port 5000"]
        Route{Route match?}
        QueryWeek[get_query_week]
        OrmRead[SQLAlchemy filter and order_by]
        Aggregate[get_weekly_data or get_rolling_avg]
        Serialize[Marshmallow dump]
        Jsonify[flask.jsonify]
    end

    subgraph DBLane["PostgreSQL 15 postgres container"]
        TracksTbl[(tracks table)]
        YearlyTbl[(yearly_avg table)]
    end

    subgraph ExtLane["External Pipeline NOT in repo"]
        Scraper[Weekly Billboard Scraper]
        Spotipy[Spotipy client]
        SpotifyAPI[Spotify Web API]
    end

    UStart --> Boot
    Boot --> TabRouter
    UClick --> TabRouter
    USubmit --> Fetch
    TabRouter -->|Tracks default| Fetch
    Fetch --> Route
    Route -->|/api/week/&lt;date&gt;| QueryWeek
    Route -->|/api/analysis/&lt;feature&gt;| OrmRead
    QueryWeek --> OrmRead
    OrmRead --> TracksTbl
    OrmRead --> YearlyTbl
    TracksTbl --> Aggregate
    YearlyTbl --> Aggregate
    Aggregate --> Serialize
    Serialize --> Jsonify
    Jsonify --> ResponseHandler
    ResponseHandler -->|Yes| ErrorRenderer
    ResponseHandler -->|No| EmptyHandler
    EmptyHandler -->|Yes| ErrorRenderer
    EmptyHandler -->|No| Renderer
    ErrorRenderer --> UDone
    Renderer --> UDone

    Spotipy --> SpotifyAPI
    Scraper --> Spotipy
    Scraper -. weekly INSERT .-> TracksTbl
    Scraper -. annual aggregation .-> YearlyTbl
```

### 4.1.2 Application Bootstrap and Initial Page Load

The bootstrap sequence is identical regardless of which tab the user ultimately interacts with. It is responsible for delivering the React production bundle, hydrating the SPA, and triggering the default Tracks-tab data fetch.

```mermaid
flowchart TD
    A([User navigates to http://host/]) --> B[Browser issues GET /]
    B --> C[Flask matches route '/' in api/routes.py]
    C --> D[index returns app.send_static_file 'index.html']
    D --> E[Browser parses index.html and loads /static/ bundle]
    E --> F[index.js calls ReactDOM.render App into root]
    F --> G[App.js initializes state nav=false, activeTab=0]
    G --> H[Three Section wrappers render]
    H --> I{activeTab prop truthy?}
    I -->|Tracks tab activeTab===0| J[Tracks Section visible<br/>display:block]
    I -->|Trends/About not active| K[Sections hidden via display:none in Section.js]
    J --> L[TracksSection useEffect fires once]
    L --> M[getData '2021-11-13' invoked]
    M --> N([Workflow B: Tracks Tab])
```

Salient details:

- The Flask app is configured in `api/__init__.py` with `static_folder='../frontend/build'` and `static_url_path='/'`, so the same Flask process serves the SPA assets and the JSON API.
- The initial fetch parameter is the hardcoded literal `'2021-11-13'` (see `frontend/src/components/tracks/TracksSection.js` line 37). The dynamic `new Date().toISOString().slice(0, 10)` alternative exists as a commented-out line directly above.
- The bootstrap path performs no authentication, no session creation, and no cookie issuance.

### 4.1.3 Tracks Tab User Journey (Weekly Chart Inspection)

This is the system's primary workflow and the only one auto-triggered on page load. It implements feature F-008 (Tracks View), backed by F-004 (Weekly Snapshot endpoint), F-011 (Radar Chart), and F-013 (Date Normalization).

```mermaid
flowchart TD
    Start([Tracks tab visible OR DatePicker submit]) --> Trigger{Source?}
    Trigger -->|Mount| InitDate[date = '2021-11-13' literal]
    Trigger -->|DatePicker submit| GuardDP{inputValue truthy?}
    GuardDP -->|No| NoOp([No-op])
    GuardDP -->|Yes| InitDate2[date = inputValue]
    InitDate --> SetLoading[setIsLoaded false<br/>setError false]
    InitDate2 --> SetLoading
    SetLoading --> DoFetch[await fetch /api/week/&lt;date&gt;]

    DoFetch --> BackendStart{{Flask /api/week/&lt;week&gt;}}
    BackendStart --> NormDate[week = get_query_week week]
    NormDate --> Query[Tracks.query filter_by week order_by rank all]
    Query --> Dump[songs = tracks_schema.dump rows]
    Dump --> WeeklyAgg[weeklyData = get_weekly_data songs]
    WeeklyAgg --> ResponseObj[Compose week, songs, averages, avgTempo]
    ResponseObj --> ReturnJson[jsonify returnObj]
    ReturnJson --> StatusCheck{HTTP status &gt; 299?}

    StatusCheck -->|Yes| ErrPath[setError statusText<br/>setIsLoaded true]
    StatusCheck -->|No| ParseJson[await response.json]
    ParseJson --> EmptyCheck{data.length === 0?}
    EmptyCheck -->|Yes| ErrEmpty[setError 'No Data Found'<br/>setIsLoaded true]
    EmptyCheck -->|No| Success[setData data<br/>setIsLoaded true]

    ErrPath --> RenderError[Render h1 className=error]
    ErrEmpty --> RenderError
    Success --> RenderList[Render scrollable rank/artist/track list]
    RenderList --> RenderRadar[Render Radar with averages]
    RenderRadar --> EndOk([User sees chart])
    RenderError --> EndErr([User sees error message])
```

The `get_weekly_data` helper in `api/funcs.py` aggregates the five proportional audio features (`energy`, `danceability`, `speechiness`, `acousticness`, `instrumentalness`) by computing `int(series.mean() * 100)` per feature and producing one record per feature with shape `{feature, mean, full=100}`. It additionally computes `avgTempo = int(df['tempo'].mean())`. The `full=100` field exists to render the radar baseline.

### 4.1.4 Trends Tab User Journey (Feature Trend Analysis)

This workflow implements feature F-009 (Trends View), backed by F-006 (Feature Trend Analysis endpoint), F-012 (Line Chart), and F-014 (Rolling Average). Tab activation is mediated by the `App.js` `handleClick` handler.

```mermaid
flowchart TD
    Start([User clicks Trends in Sidebar id=1]) --> Parse[index = parseInt e.target.id 0]
    Parse --> Compare{index !== activeTab?}
    Compare -->|No| Same([No-op])
    Compare -->|Yes| Update[setActiveTab index<br/>setNav false]
    Update --> SectionVisible[Trends Section becomes visible]
    SectionVisible --> Mount{First mount?}
    Mount -->|Yes| InitFeature[useEffect getData 'tempo']
    Mount -->|No, FeatureSelect submit| GuardFS{inputValue truthy?}
    GuardFS -->|No| NoOp([No-op])
    GuardFS -->|Yes| InitFeature2[getData inputValue]

    InitFeature --> SetLoading[setIsLoaded false<br/>setError false]
    InitFeature2 --> SetLoading
    SetLoading --> DoFetch[await fetch /api/analysis/&lt;feature&gt;]

    DoFetch --> BackendStart{{Flask /api/analysis/&lt;feature&gt;}}
    BackendStart --> Query[YearlyAvg.query.with_entities year, getattr feature]
    Query --> Dump[data = yearly_schema.dump rows]
    Dump --> Rolling[dataDict = get_rolling_avg data]
    Rolling --> ReturnJson[jsonify feature, data]
    ReturnJson --> StatusCheck{HTTP status &gt; 299?}

    StatusCheck -->|Yes| ErrPath[setError statusText<br/>setIsLoaded true]
    StatusCheck -->|No| ParseJson[await response.json]
    ParseJson --> EmptyCheck{data.length === 0?}
    EmptyCheck -->|Yes| ErrEmpty[setError 'No Data Found'<br/>setIsLoaded true]
    EmptyCheck -->|No| Success[setData data<br/>setIsLoaded true]

    ErrPath --> RenderError[Render h1 className=error]
    ErrEmpty --> RenderError
    Success --> RenderLine[Render LineChart Annual + Rolling]
    RenderLine --> RenderFeatures[Render features.json descriptions]
    RenderFeatures --> EndOk([User sees trend])
    RenderError --> EndErr([User sees error message])
```

The `get_rolling_avg` helper builds a pandas DataFrame, computes `df['rolling'] = df[feature].rolling(5).mean()` (a five-year window despite the UI label "3 Year Rolling Average"), sanitizes NaN values via `df.where(pd.notnull(df), None)`, renames the feature column to `'value'`, and returns dictionary records while filtering out the first four rows whose rolling value remains NaN.

### 4.1.5 About Tab User Journey

This is the only navigable view that is purely presentational. It implements feature F-010 (About View) and serves as the in-app documentation page.

```mermaid
flowchart TD
    A([User clicks About in Sidebar id=3]) --> B[handleClick parses id=3]
    B --> C{index !== activeTab?}
    C -->|No| NoOp([No-op])
    C -->|Yes| D[setActiveTab 3<br/>setNav false]
    D --> E[About Section activeTab===3 becomes visible]
    E --> F[AboutSection renders static markup]
    F --> G[No fetch, no state, no useEffect]
    G --> H[Three info blocks render:<br/>Billboard Hot 100, API, Front End]
    H --> I[External anchor links rendered:<br/>billboard.com, wikipedia, spotipy, spotify, amcharts, github]
    I --> End([User reads documentation])
```

### 4.1.6 API-Only Endpoints (Programmatic Consumers)

Two endpoints have no in-app consumer and are reachable only by direct HTTP clients. They are listed in the About tab for discoverability.

```mermaid
flowchart TD
    subgraph DefaultRedirect["GET /api/"]
        DA[Client GET /api/] --> DB[currentWeek = get_query_week None]
        DB --> DC[redirect 'week/' + currentWeek]
        DC --> DD([302 to /api/week/&lt;currentSaturday&gt;])
    end

    subgraph TrackLookup["GET /api/track/&lt;spotify_id&gt;"]
        TA[Client GET /api/track/&lt;id&gt;] --> TB[Tracks.query.filter_by spotify_id order_by rank all]
        TB --> TC[tracks_schema.dump rows]
        TC --> TD([jsonify list - empty array if no match])
    end

    subgraph ArtistSearch["GET /api/artist/&lt;artist&gt;"]
        AA[Client GET /api/artist/&lt;name&gt;] --> AB[Tracks.query.filter LOWER artist LIKE LOWER %name%]
        AB --> AC[order_by week DESC all]
        AC --> AD[tracks_schema.dump rows]
        AD --> AE([jsonify list - empty array if no match])
    end
```

The `LIKE '%pattern%'` form used by `/api/artist` cannot leverage a B-tree index, resulting in a full-table scan as documented in section 2.4.3.

## 4.2 INTEGRATION WORKFLOWS

The system integrates exactly three pairs of components (Browser ↔ Flask, Flask ↔ PostgreSQL, External Pipeline ↔ PostgreSQL) plus a fourth orchestration pathway (Docker Compose ↔ both containers). Each is described below.

### 4.2.1 Browser-to-Backend Integration

The SPA uses the browser's native `fetch()` API. Although `axios` is declared in `frontend/package.json`, it is not imported anywhere in the source tree.

```mermaid
sequenceDiagram
    participant Browser as Browser (fetch native)
    participant Flask as Flask 2.0.1 (port 5000)
    participant CORS as Flask-Cors 3.0.10
    
    Note over Browser,Flask: Production: same-origin (port 80 → 5000)<br/>Development: CRA proxy 'http://localhost:5000'
    Browser->>Flask: fetch /api/week/2021-11-13
    Flask->>CORS: CORS(app) wildcard preflight
    CORS-->>Flask: Headers Access-Control-Allow-Origin '*'
    Flask-->>Browser: 200 application/json
    Note over Browser,Flask: No auth headers, no cookies, no CSRF token
```

Key facts:

- The CRA dev proxy is configured by the single line `"proxy": "http://localhost:5000"` in `frontend/package.json`.
- In production, Flask serves both the SPA (from `frontend/build/`) and the API on the same origin, so CORS is not strictly required. It is registered globally as defense-in-depth.
- No request body is ever sent (all routes are `GET`); no authentication tokens, no CSRF tokens, no cookies are exchanged.

### 4.2.2 Backend-to-Database Integration

The Flask process opens a SQLAlchemy connection from the default Flask-SQLAlchemy pool and executes parameterized queries via the `psycopg2` driver. Connection metadata is hardcoded.

```mermaid
sequenceDiagram
    participant Route as routes.py handler
    participant ORM as Flask-SQLAlchemy 2.5.1
    participant Driver as psycopg2 2.9.6
    participant DB as PostgreSQL 15

    Note over Route,DB: Connection: postgresql://postgres:postgres@postgres/db<br/>Hardcoded in api/__init__.py line 12
    Route->>ORM: Tracks.query.filter_by week=...
    ORM->>Driver: SELECT * FROM tracks WHERE week=$1
    Driver->>DB: TCP 5432 wire protocol
    DB-->>Driver: Row stream
    Driver-->>ORM: Hydrate ORM objects
    ORM-->>Route: List of Tracks instances
    Route->>Route: tracks_schema.dump (Marshmallow)
    Note over Route: No explicit transaction;<br/>read-only routes use implicit autocommit
```

The connection pool size, overflow, and timeout values are not configured anywhere; the application relies on Flask-SQLAlchemy's defaults.

### 4.2.3 External Pipeline Integration (Out-of-Repository)

The Billboard scraper and Spotipy enrichment client are not present in this repository. They are referenced in the About tab and `README.md` only. The following sequence reconstructs the assumed flow as a contract for future maintainers; it is **not** implemented within this codebase.

```mermaid
sequenceDiagram
    participant Scheduler as External Scheduler (out of repo)
    participant Scraper as Billboard Scraper (out of repo)
    participant Billboard as billboard.com
    participant Spotipy as Spotipy client (out of repo)
    participant Spotify as Spotify Web API
    participant DB as PostgreSQL (this repo)

    Note over Scheduler,DB: Cadence: weekly
    Scheduler->>Scraper: Trigger weekly run
    Scraper->>Billboard: GET Hot 100 for current week
    Billboard-->>Scraper: HTML chart page
    Scraper->>Scraper: Parse rank/artist/track per row
    Scraper->>Spotipy: For each track lookup spotify_id
    Spotipy->>Spotify: GET /v1/search and /v1/audio-features
    Spotify-->>Spotipy: Audio features payload
    Spotipy-->>Scraper: Enriched rows
    Scraper->>DB: INSERT INTO tracks ...
    Note over DB: Annually: external job recomputes yearly_avg
```

The Flask application performs **no outbound HTTP** to either Billboard or Spotify. All data freshness depends on this external job running on its weekly cadence.

### 4.2.4 Container Orchestration Sequence

The two-service stack defined in `docker-compose.yml` is bootstrapped in a deterministic order because the `api` service declares `depends_on: postgres`.

```mermaid
sequenceDiagram
    participant Op as Operator
    participant Compose as Docker Compose
    participant PG as postgres container (postgres:15)
    participant Build as Image Builder
    participant API as api container (python:3.11-slim-buster)
    participant Flask as Flask app (app.py)

    Op->>Compose: docker compose up
    Compose->>PG: pull postgres:15
    PG->>PG: Initialize POSTGRES_DB=db<br/>POSTGRES_USER=postgres<br/>POSTGRES_PASSWORD=postgres
    PG->>PG: Bind volume ./data:/data
    PG-->>Compose: Listening on 5432:5432
    Compose->>Build: docker build (api)
    Build->>Build: FROM python:3.11-slim-buster
    Build->>Build: apt-get install libpq-dev gcc
    Build->>Build: COPY requirements.txt + pip3 install
    Build->>Build: COPY . .
    Build->>Build: EXPOSE 5000
    Build-->>Compose: Image ready
    Compose->>API: Run CMD ["python3", "app.py"]
    API->>Flask: from api import app (api/__init__.py)
    Note over Flask: Flask app, CORS(app), db=SQLAlchemy(app),<br/>ma=Marshmallow(app), then 'from api import routes'
    Flask->>Flask: app.run(host='0.0.0.0')
    Flask-->>API: Dev server listening on 0.0.0.0:5000
    Note over Compose,API: Host port 80 → container 5000<br/>restart: on-failure<br/>NODE_OPTIONS=--openssl-legacy-provider<br/>Bind-mount .:/app/
```

Important: the production launcher is `python3 app.py`, which invokes Flask's built-in development server. Although `gunicorn==20.1.0` is declared in `requirements.txt`, it is never invoked. This is documented as a known discrepancy in section 2.4.1.

## 4.3 DECISION LOGIC AND VALIDATION RULES

This subsection consolidates every decision point and validation rule across the system. The validation surface is intentionally minimal: most validation is concentrated at the frontend HTML-input level, with limited backend protection.

### 4.3.1 Date Normalization Decision Tree

`get_query_week` in `api/funcs.py` is the system's only non-trivial business-rule decision logic. It maps any input date (or `None`) onto the appropriate Saturday boundary, accommodating Billboard's mid-week chart finalization at 10:00 AM Wednesdays.

```mermaid
flowchart TD
    Start([get_query_week date called]) --> Provided{date provided?}
    Provided -->|Yes| Parse[date = strptime YYYY-MM-DD]
    Provided -->|No| Today[date = datetime.today]
    Parse --> Compute[date_weekday = date.weekday<br/>0=Mon ... 6=Sun]
    Today --> Compute
    Compute --> NextSat[next_sat = date + 12-weekday %% 7 days]
    NextSat --> LastSat[last_sat = next_sat - 7 days]
    LastSat --> WeekdayCheck{weekday in Sun, Mon, Tue?}
    WeekdayCheck -->|Yes| ReturnLast([Return last_sat YYYY-MM-DD])
    WeekdayCheck -->|No| WedCheck{weekday == Wed?}
    WedCheck -->|Yes| TimeCheck{time before 10:00 AM?}
    TimeCheck -->|Yes| ReturnLast
    TimeCheck -->|No| ReturnNext([Return next_sat YYYY-MM-DD])
    WedCheck -->|No| ReturnNext
```

The mapping table:

| Day of Week | Time | Returned Saturday |
|---|---|---|
| Sunday | any | Previous |
| Monday | any | Previous |
| Tuesday | any | Previous |
| Wednesday | < 10:00 AM | Previous |
| Wednesday | ≥ 10:00 AM | Next |
| Thursday | any | Next |
| Friday | any | Next |
| Saturday | any | Next (i.e., that day) |

### 4.3.2 Frontend Input Validation

Validation at the SPA layer is shallow but consistent across the two interactive forms.

| Component | Source File | Validation Behavior |
|---|---|---|
| `DatePicker` | `frontend/src/components/tracks/DatePicker.js` | HTML `<input type='date'>` with `min='1958-07-27'` and `max='2021-11-13'`; browser-enforced |
| `DatePicker.handleSubmit` | same | `e.preventDefault()`; truthy check `if (inputValue)` before invoking `submitFunc` |
| `FeatureSelect` | `frontend/src/components/trends/FeatureSelect.js` | Hardcoded `<select>` with seven options: `tempo`, `energy`, `danceability`, `instrumentalness`, `liveness`, `speechiness`, `acousticness` |
| `FeatureSelect.handleSubmit` | same | `e.preventDefault()`; truthy check before invoking `submitFunc` |

Notably, `valence` and `loudness` are columns present in the `YearlyAvg` model but are intentionally excluded from the `FeatureSelect` dropdown.

### 4.3.3 Backend Validation Posture

The Flask route handlers perform **no explicit input validation**. The behavior under invalid input is summarized below.

| Endpoint | Invalid Input Class | Effective Behavior |
|---|---|---|
| `/api/week/<week>` | Non-ISO date string | SQLAlchemy/PostgreSQL coercion error → Flask 500 |
| `/api/week/<week>` | Date with no rows | 200 OK with `songs:[]`, `averages:[]`, `avgTempo: NaN` |
| `/api/track/<id>` | Unknown `spotify_id` | 200 OK with empty array `[]` |
| `/api/artist/<name>` | No matches | 200 OK with empty array `[]` |
| `/api/analysis/<feature>` | Attribute not on `YearlyAvg` | `getattr` raises `AttributeError` → Flask 500 |
| `/api/analysis/<feature>` | Empty result set | `data[0].keys()` raises `IndexError` → Flask 500 |

There is no schema validation library (no `pydantic`, no `marshmallow.load`). Marshmallow is used in the dump direction only.

### 4.3.4 Authorization and Regulatory Compliance

The application has **no authorization checkpoints whatsoever**:

- No authentication middleware is registered on the Flask app.
- No `@login_required`, `@roles_required`, or equivalent decorators are present.
- No API keys, JWT validation, or session cookies are issued or required.
- All six routes are publicly accessible.

Compliance posture:

- No personal data is collected; there are no user accounts or sign-up flows.
- No GDPR/CCPA cookie banners are present (none are needed because no cookies are set).
- No audit logging or access logs are configured beyond Flask's default request logging.
- No data retention or deletion mechanisms exist within the read-side application.

This posture is appropriate for the public-read-only nature of the dataset and is documented as an explicit non-goal in section 2.4.4.

## 4.4 STATE MANAGEMENT

The system has no global state container. Frontend state is local to each component (React `useState` hooks); backend state is the database; there are no in-memory caches, no Redis, and no client-side persistence.

### 4.4.1 React Component State Inventory

| Component | State Variables | Initial Values | Source File |
|---|---|---|---|
| `App` | `nav`, `activeTab` | `false`, `0` | `frontend/src/App.js` |
| `TracksSection` | `data`, `isLoaded`, `error` | `[]`, `false`, `null` | `frontend/src/components/tracks/TracksSection.js` |
| `TrendsSection` | `data`, `isLoaded`, `error` | `[]`, `false`, `null` | `frontend/src/components/trends/TrendsSection.js` |
| `DatePicker` | `inputValue` | `initValue` prop (`'2021-11-13'`) | `frontend/src/components/tracks/DatePicker.js` |
| `FeatureSelect` | `inputValue` | `undefined` | `frontend/src/components/trends/FeatureSelect.js` |
| `AboutSection` | none | n/a | `frontend/src/components/about/AboutSection.js` |

There is no Redux, no Zustand, no Context API usage, and no shared store. State communication between siblings is mediated entirely through `App.js` (for tab navigation) and through callback props (for date and feature submission).

### 4.4.2 Fetch Lifecycle State Transitions

Both `TracksSection` and `TrendsSection` implement an identical fetch lifecycle state machine. The diagram below applies to both with `data` referring to the section-specific payload shape.

```mermaid
stateDiagram-v2
    [*] --> Initial: Component mounts
    Initial: data=[]<br/>isLoaded=false<br/>error=null
    Initial --> Loading: useEffect fires getData
    Loading: data=prev<br/>isLoaded=false<br/>error=false
    Loading --> HttpError: response.status &gt; 299
    Loading --> EmptyData: data.length === 0
    Loading --> Success: data.length &gt; 0
    HttpError: data=prev<br/>isLoaded=true<br/>error=statusText
    EmptyData: data=prev<br/>isLoaded=true<br/>error='No Data Found'
    Success: data=new<br/>isLoaded=true<br/>error=false
    HttpError --> Loading: User submits new query
    EmptyData --> Loading: User submits new query
    Success --> Loading: User submits new query
```

The render output is a function of these three state values:

- `error` truthy → renders `<h1 className='error'>{error}</h1>`.
- `!isLoaded` → renders `<h1 className='loading'>. . .</h1>`.
- `isLoaded && !error` → renders the success view (list + chart).

### 4.4.3 Tab Navigation State Machine

The application's tab indices skip 2 — `0` is Tracks, `1` is Trends, `3` is About. This non-contiguous numbering is consistent across `App.js` (the comparison) and `Sidebar.js` (the tab IDs).

```mermaid
stateDiagram-v2
    [*] --> Tracks: activeTab=0 default
    Tracks --> Trends: Click Trends id=1
    Tracks --> About: Click About id=3
    Trends --> Tracks: Click Tracks id=0
    Trends --> About: Click About id=3
    About --> Tracks: Click Tracks id=0
    About --> Trends: Click Trends id=1
    Tracks --> Tracks: Click same tab no-op
    Trends --> Trends: Click same tab no-op
    About --> About: Click same tab no-op
    note right of Tracks
      nav state auto-collapses
      to false on every tab change
    end note
```

The `handleClick` guard `if (index !== activeTab)` prevents unnecessary re-renders when a user clicks the already-active tab. The `nav` state (mobile sidebar toggle) is implicitly reset to `false` on every successful tab change.

### 4.4.4 Data Persistence and Transaction Boundaries

Persistence is exclusively in the PostgreSQL `tracks` and `yearly_avg` tables, both written by the external pipeline.

| Persistence Surface | Used By This Repo | Status |
|---|---|---|
| `tracks` table | Read | Read by `/api/track`, `/api/week`, `/api/artist`, plus `/api/` redirect |
| `yearly_avg` table | Read | Read by `/api/analysis` |
| `localStorage` / `sessionStorage` | Not used | No frontend persistence |
| Cookies | Not used | No session, no analytics, no consent banner |
| Server-side session store | Not used | No `flask-session`, no Redis, no signed cookies |

Transaction semantics: all six route handlers issue **read-only queries**. There are no `db.session.commit()` calls, no `db.session.rollback()` calls, and no explicit transaction blocks. The application implicitly relies on PostgreSQL's autocommit-equivalent behavior for read transactions through SQLAlchemy.

### 4.4.5 Caching Posture

The system has **no caching layer at any tier**:

- No Redis, Memcached, or any caching service in `docker-compose.yml`.
- No `Flask-Caching`, `redis-py`, or `pymemcache` in `requirements.txt`.
- No HTTP `Cache-Control`, `ETag`, or `Last-Modified` headers set by route handlers.
- No in-process LRU caches (`functools.lru_cache` is not used in routes or helpers).
- No CDN configuration, no Service Worker, no `precache.js`.
- No browser-side caching beyond what the browser applies to static assets by default.

Each request to `/api/week`, `/api/analysis`, or any other route results in a fresh database query and a fresh aggregation pass.

## 4.5 ERROR HANDLING FLOWS

The error handling posture is intentionally minimal and consistent across the codebase. There is no retry logic, no exponential backoff, no circuit breaker, and no alerting pipeline.

### 4.5.1 Frontend Error State Machine

```mermaid
flowchart TD
    A[fetch /api/&lt;route&gt;/&lt;param&gt;] --> B{Network error or<br/>fetch promise rejection?}
    B -->|Yes| C[Unhandled promise rejection<br/>no try/catch in TracksSection or TrendsSection]
    B -->|No| D{response.status &gt; 299?}
    D -->|Yes| E[setIsLoaded true<br/>setError response.statusText<br/>return]
    D -->|No| F[await response.json]
    F --> G{data.length === 0?}
    G -->|Yes| H[setError 'No Data Found'<br/>setIsLoaded true]
    G -->|No| I[setData data<br/>setIsLoaded true]
    E --> J[Render h1.error]
    H --> J
    I --> K[Render success view]
    J --> EndErr([User sees error message])
    K --> EndOk([User sees data])
    C --> EndUnhandled([Browser console only])
```

A critical gap: neither `TracksSection.getData` nor `TrendsSection.getData` wraps the `await fetch(...)` in a try/catch. A network-level failure (DNS resolution failure, connection refused, CORS rejection) results in an unhandled promise rejection visible only in the browser console. The UI remains in its previous state with `isLoaded=false`, leaving the loading indicator displayed indefinitely.

### 4.5.2 Backend Error Behaviors

```mermaid
flowchart TD
    A[Inbound HTTP request] --> B{Route matched?}
    B -->|No| C[Flask default 404 Not Found]
    B -->|Yes| D[Handler executes]
    D --> E{Exception raised?}
    E -->|No| F[Return jsonify response code 200]
    E -->|Yes| G{Exception type?}
    G -->|AttributeError invalid feature| H[Flask default 500 Internal Server Error]
    G -->|IndexError empty data 0| H
    G -->|psycopg2 error invalid date format| H
    G -->|SQLAlchemy connection error| H
    H --> I[No structured error response body<br/>HTML stack trace in debug mode only]
```

| Endpoint | Error Class | Backend Status Code | Frontend Handling |
|---|---|---|---|
| `/api/week/<week>` | Invalid date string | 500 | `setError(statusText)` |
| `/api/week/<week>` | No matching rows | 200 with empty arrays | Renders zero-state list + radar with NaN avgTempo |
| `/api/analysis/<feature>` | Invalid feature attr | 500 | `setError(statusText)` |
| `/api/analysis/<feature>` | Empty `YearlyAvg` table | 500 (`IndexError`) | `setError(statusText)` |
| `/api/track/<id>` | Unknown ID | 200 with `[]` | Treated as "No Data Found" |
| `/api/artist/<name>` | No match | 200 with `[]` | Treated as "No Data Found" |

### 4.5.3 Retry, Fallback, Notification, and Recovery Posture

The codebase contains **none** of the following:

| Capability | Status | Evidence |
|---|---|---|
| HTTP retry on frontend | Absent | No `axios-retry`, no `p-retry`, no manual retry loop |
| Backend retry on transient DB errors | Absent | No `tenacity`, no `backoff`, no connection retry policy |
| Circuit breaker | Absent | No `pybreaker` or equivalent |
| Fallback responses | Absent | No `try/except` in route handlers |
| Structured logging | Absent | No `structlog`, no `loguru`, no `logging.config` |
| Error reporting | Absent | No Sentry, Rollbar, or Bugsnag SDK |
| Metrics endpoint | Absent | No Prometheus client, no statsd |
| APM agent | Absent | No DataDog, New Relic, or AppDynamics SDK |
| Frontend error boundary | Absent | No `componentDidCatch`, no `<ErrorBoundary>` wrapper |
| `web-vitals` reporting | Declared but unwired | `web-vitals` 1.0.1 in `package.json`, no `reportWebVitals()` call |

Recovery for the user is manual: re-submit the form (via DatePicker or FeatureSelect) or reload the page.

### 4.5.4 Container-Level Recovery

The only automated recovery mechanism is at the container orchestration tier.

```mermaid
flowchart TD
    A[api container running app.py] --> B{Process exits?}
    B -->|Yes non-zero| C[Docker Compose restart: on-failure]
    C --> D[Compose relaunches CMD python3 app.py]
    D --> E[Re-import api package<br/>Re-register routes]
    E --> A
    B -->|No| F[Continue serving]
    F --> A
    A --> G{postgres container down?}
    G -->|Yes| H[Next DB query raises psycopg2 OperationalError]
    H --> I[Flask returns 500]
    I --> J[Frontend setError]
```

Notable: there is no `restart` policy declared on the `postgres` service, only on `api` (`restart: on-failure`). A PostgreSQL crash will remain down until manually restarted; the `api` container will restart-loop if it depends on a connection at boot, although the current bootstrap defers connection until the first request.

## 4.6 TIMING AND SLA CONSIDERATIONS

### 4.6.1 Performance Boundaries

Performance characteristics inherited from data shape and code structure (cross-referenced from section 2.4.2):

| Workflow | Bound | Detail |
|---|---|---|
| F-004 Weekly Snapshot (`/api/week`) | ≤ 100 rows per response | Aggregation runtime dominated by network overhead |
| F-005 Artist Search (`/api/artist`) | Full-table scan | `LOWER(...) LIKE '%pattern%'` cannot use B-tree indexes |
| F-006 Feature Trend (`/api/analysis`) | ≤ ~70 rows | Rolling computation O(n) over `YearlyAvg` |
| F-016 Flask Dev Server | Single-threaded | Not optimized for concurrent traffic; one inflight request at a time |
| F-011/F-012 amCharts | No `chart.dispose()` | Repeated tab switches risk client-side memory growth (`RadarChart.js` line 66, `LineChart.js` line 70 — both commented out) |

### 4.6.2 Codified SLAs

There are **no SLAs codified anywhere in the repository**:

- No latency targets in code or configuration.
- No timeout values set on Flask routes (`@app.route` decorators have no timeout parameter, and Flask itself has no per-route timeout).
- No `signal.alarm` or asyncio timeout wrappers in route handlers.
- No timeout on the frontend `fetch()` calls (no `AbortController` usage).
- No rate limiting (`flask-limiter` not installed).
- No request body size limits (`MAX_CONTENT_LENGTH` not set).
- No deadline propagation through helper functions.

### 4.6.3 Operational Cadence

The system depends on cadenced external operations that are out-of-repository:

| Operation | Cadence | Owner | Status |
|---|---|---|---|
| Billboard chart scrape + Spotipy enrichment | Weekly | External maintainer | Out of repo |
| `YearlyAvg` recomputation | Annual or backfill | External maintainer | Out of repo |
| React production build (`react-scripts build`) | On frontend code change | Build pipeline | In repo (manual) |
| Container image rebuild | On dependency change | Operator | Manual |
| Secret rotation | N/A | Operator | Hardcoded in `api/__init__.py` line 12 |

The chart-week boundary at 10:00 AM Wednesday in `get_query_week` aligns with Billboard's mid-week chart finalization cadence, which is the only timing constraint observable in the code.

## 4.7 REFERENCES

### 4.7.1 Source Files Examined

- `app.py` — Root entrypoint invoking `app.run(host='0.0.0.0')`; verified the Flask development server is the production launcher.
- `api/__init__.py` — Flask bootstrap, `static_folder`/`static_url_path` configuration, hardcoded database URI, CORS registration, `db`/`ma` initialization, and circular `from api import routes` import.
- `api/routes.py` — All six route handlers (`/`, `/api/`, `/api/track/<id>`, `/api/week/<week>`, `/api/artist/<artist>`, `/api/analysis/<feature>`); source of truth for request/response shapes and decision branches.
- `api/funcs.py` — `get_query_week` (date normalization with weekday and 10:00 AM Wednesday cutoff), `get_rolling_avg` (5-year `pandas.rolling(5).mean()`), `get_weekly_data` (per-week feature aggregation).
- `api/models.py` — `Tracks` and `YearlyAvg` SQLAlchemy models; `TrackSchema` and `YearlyAvgSchema` Marshmallow schemas.
- `requirements.txt` — Pinned Python dependencies; verified absence of caching, retry, observability, and rate-limit libraries.
- `docker-compose.yml` — Two-service orchestration (`api`, `postgres`), port mappings, `depends_on`, environment variables, volume mounts, `restart: on-failure` policy.
- `Dockerfile` — Build steps for the api image (`python:3.11-slim-buster`, `libpq-dev`, `gcc`, `pip3 install`, `CMD ["python3", "app.py"]`).
- `README.md` — Documentation references for the external scraper and Spotipy enrichment; "3 Year" rolling-average label discrepancy.
- `frontend/package.json` — React 17.0.2, `@amcharts/amcharts4`, `axios` (declared but unused), `web-vitals` (unwired), CRA proxy `http://localhost:5000`.
- `frontend/src/index.js` — `ReactDOM.render` bootstrap into `#root` with `<React.StrictMode>`.
- `frontend/src/App.js` — Tab orchestrator; `activeTab` and `nav` state; `handleClick` with `parseInt(e.target.id, 0)` and `if (index !== activeTab)` guard; tab indices 0, 1, 3.
- `frontend/src/components/tracks/TracksSection.js` — `getData` async fetch flow, error state machine, hardcoded `'2021-11-13'` initial parameter.
- `frontend/src/components/tracks/DatePicker.js` — Controlled date input with `min='1958-07-27'` and `max='2021-11-13'`; `handleSubmit` truthy guard.
- `frontend/src/components/tracks/RadarChart.js` — amCharts 4 RadarChart imperative setup; `chart.dispose()` commented out.
- `frontend/src/components/trends/TrendsSection.js` — Trends mount with `'tempo'`; identical fetch state machine to Tracks; consumes `feature.desctiption` (sic).
- `frontend/src/components/trends/FeatureSelect.js` — Hardcoded 7-option dropdown (no `valence`, no `loudness`); truthy submit guard.
- `frontend/src/components/trends/LineChart.js` — amCharts 4 XYChart with two LineSeries; "Annual Average" dashed, "3 Year Rolling Average" solid label.
- `frontend/src/components/trends/features.json` — 7-entry array with intentionally misspelled `desctiption` key.
- `frontend/src/components/about/AboutSection.js` — Static documentation page; no fetch, no state, no `useEffect`.
- `frontend/src/components/navigation/Sidebar.js` — Sidebar composition with tab IDs 0, 1, 3; styled-components media query at `min-width: 800px`.
- `frontend/src/components/navigation/Section.js` — Styled wrapper with `display:none` when `activeTab` prop is falsy.
- `frontend/src/components/navigation/Hamburger.js`, `Tab.js`, `SmallTab.js` — Sidebar primitives shared across all three tab sections.

### 4.7.2 Folders Explored

- `/` (repo root) — Top-level structure: `api/`, `frontend/`, `docker-compose.yml`, `Dockerfile`, `requirements.txt`, `README.md`, `app.py`.
- `api/` — Backend Python module: `__init__.py`, `routes.py`, `funcs.py`, `models.py`.
- `frontend/` — CRA project root.
- `frontend/src/` — React source: `App.js`, `index.js`, `components/`, `styles/`.
- `frontend/src/components/` — Component tree: `navigation/`, `trends/`, `about/`, `tracks/`.
- `frontend/src/components/tracks/` — Tracks tab implementation.
- `frontend/src/components/trends/` — Trends tab implementation.
- `frontend/src/components/navigation/` — Navigation primitives.
- `frontend/src/components/about/` — About tab implementation.

### 4.7.3 Cross-Referenced Technical Specification Sections

- **1.2 SYSTEM OVERVIEW** — Major system components diagram, hardcoded-credential limitation, "3 Year" vs. five-year discrepancy, gunicorn-vs-Flask-dev-server discrepancy, external pipeline scope.
- **2.3 FEATURE RELATIONSHIPS** — Feature dependency graph (F-001 through F-017), integration points table, shared component inventory, primary user-journey sequence diagram.
- **2.4 IMPLEMENTATION CONSIDERATIONS** — Technical constraints (hardcoded URI, hardcoded literal date, five-year vs. three-year label, valence exclusion, `desctiption` typo, tab-index 2 skip), performance requirements per feature, scalability and security implications.
- **3.7 STACK INTEGRATION OVERVIEW** — End-to-end stack diagram, three explicit integration points (Frontend↔Backend, Backend↔Database, External Pipeline↔Database), CRA build artifact pathway.

# 5. System Architecture

## 5.1 HIGH-LEVEL ARCHITECTURE

### 5.1.1 System Overview

#### Architectural Style and Rationale

Hot Stuff is implemented as a **two-tier monolithic web application** delivered through a **two-container Docker Compose stack**. The architecture is intentionally minimal: a single Flask process hosts both the JSON API surface and the compiled React Single-Page Application (SPA) static assets, while a sibling PostgreSQL 15 container provides durable storage for the chart-row entities and pre-aggregated yearly statistics.

This style was selected for the following pragmatic reasons:

- **Single-domain bounded context**: The product has exactly one cohesive concern — visualizing Billboard Hot 100 chart history with Spotify-derived audio features — which does not benefit from cross-service boundaries.
- **Read-heavy, public-access workload**: Every endpoint in `api/routes.py` is a `GET`. There are no write paths from the user-facing tier, so the operational burden of distributed coordination would be unjustified.
- **Solo-maintainer operational model**: The footer marker `AUG | 2021` and the absence of CI/CD configuration, IaC files, or orchestrator manifests indicate a project sized for a single contributor. A monolith minimizes the deployment, observability, and on-call surface area.
- **Separation by tier rather than by service**: The browser↔API↔database split is implemented as logical tiers within a single repository, not as independent services. The "write-side" of the data lifecycle (the Billboard scraper and Spotipy-based enrichment job) lives outside this repository and writes directly to the same PostgreSQL instance.

#### Key Architectural Principles and Patterns

- **Same-origin SPA delivery**: The Flask application is configured with `static_folder='../frontend/build'` and `static_url_path='/'`, which causes the same process to serve `index.html`, the hashed bundle, and the JSON API. This eliminates cross-origin overhead in production while still permitting CRA's development proxy at `http://localhost:5000` for local iteration.
- **Read-only relational projection**: The two ORM tables (`Tracks`, `YearlyAvg`) are projected into JSON exclusively via Marshmallow `dump()` calls. No `load()` (deserialization) is performed anywhere, codifying the read-only contract at the schema layer.
- **Pre-aggregation of expensive computations**: Annual feature averages are stored in `YearlyAvg`, computed by an out-of-repo job. The application performs only a constant-time rolling window pass at request time.
- **In-process tabular aggregation**: Pandas DataFrames are used as the per-request aggregation primitive (`get_weekly_data`, `get_rolling_avg`), keeping computation logic colocated with the route handler.
- **Local-state, controlled-component frontend**: Every React state value is owned by the closest containing component (`App`, `TracksSection`, `TrendsSection`, `DatePicker`, `FeatureSelect`); there is no global store, no reducer, and no Context provider.
- **Defense-in-depth CORS**: `Flask-Cors` is registered with no allow-list as a permissive default. Because production traffic is same-origin, this primarily exists to keep the development proxy uncontested.

#### System Boundaries and Major Interfaces

The system boundary encompasses exactly two containers — the `api` service and the `postgres` service — connected over the Compose-managed Docker network. The interface surface visible to the outside world is:

- **Browser → `api`**: HTTP on port `80` (mapped to container port `5000`), serving both the SPA at `/` and the JSON API at `/api/*`.
- **External Pipeline → `postgres`**: TCP `5432` (also exposed to the host), used by an out-of-repository scraper to insert weekly chart rows and to recompute annual averages.
- **Browser → Google Fonts CDN**: Loaded via `<link>` preconnect hints in `frontend/public/index.html`, the only third-party browser-loaded resource.

The HTTP API consists of six routes:

- `GET /` — serves the React `index.html` from the static folder.
- `GET /api/` — `302` redirect to the current chart week.
- `GET /api/track/<spotify_id>` — historical chart appearances for a single track.
- `GET /api/week/<week>` — weekly chart snapshot with computed averages.
- `GET /api/artist/<artist>` — case-insensitive partial-match artist search.
- `GET /api/analysis/<feature>` — yearly mean and 5-year rolling mean for a feature.

#### Logical System Topology

```mermaid
flowchart TB
    User([End User Browser])

    subgraph DockerHost["Docker Compose Host"]
        subgraph ApiContainer["api service - port 80 to 5000"]
            FlaskCore[Flask 2.0.1 App<br/>app.py, api/__init__.py]
            RoutesMod[Routes Module<br/>api/routes.py]
            HelpersMod[Helper Module<br/>api/funcs.py]
            ModelsMod[ORM and Schemas<br/>api/models.py]
            StaticFiles[React Build Artifact<br/>frontend/build/]
        end

        subgraph PgContainer["postgres service - port 5432 to 5432"]
            TracksTbl[(tracks table)]
            YearlyTbl[(yearly_avg table)]
        end
    end

    subgraph External["Out-of-Repository"]
        Scraper[Billboard Scraper +<br/>Spotipy Enrichment]
        Fonts[Google Fonts CDN<br/>Jost family]
    end

    User -- HTTP fetch --> FlaskCore
    User -- preconnect --> Fonts
    FlaskCore --> StaticFiles
    FlaskCore --> RoutesMod
    RoutesMod --> HelpersMod
    RoutesMod --> ModelsMod
    ModelsMod -- SQLAlchemy psycopg2 --> TracksTbl
    ModelsMod -- SQLAlchemy psycopg2 --> YearlyTbl
    Scraper -. weekly INSERT .-> TracksTbl
    Scraper -. annual rebuild .-> YearlyTbl
```

### 5.1.2 Core Components

The system is composed of nine logical components grouped into three tiers. Because the table contract limits each table to four columns, the inventory is partitioned by tier with separate columns for "Primary Responsibility" and "Critical Considerations" presented in the prose that follows.

#### Backend Tier Components

| Component Name | Primary Responsibility | Key Dependencies | Integration Points |
|---|---|---|---|
| Flask Application Bootstrap (`api/__init__.py`, `app.py`) | Construct the Flask object, wire SQLAlchemy/Marshmallow/CORS, register the static folder, and bind to `0.0.0.0:5000` | Flask 2.0.1, Flask-SQLAlchemy 2.5.1, flask-marshmallow 0.14.0, Flask-Cors 3.0.10 | Browser via HTTP; PostgreSQL via SQLAlchemy URI |
| HTTP Routing Module (`api/routes.py`) | Implement six route handlers covering the entire API surface | Flask app object; `Tracks`, `YearlyAvg` ORM models; helpers in `funcs.py` | `/`, `/api/`, `/api/track/<id>`, `/api/week/<week>`, `/api/artist/<name>`, `/api/analysis/<feature>` |
| ORM Models and Schemas (`api/models.py`) | Define `Tracks` and `YearlyAvg` table mappings and corresponding `TrackSchema`/`YearlyAvgSchema` | SQLAlchemy 1.4.19, marshmallow 3.12.1, marshmallow-sqlalchemy 0.26.1 | PostgreSQL `tracks` and `yearly_avg` tables; consumed by all routes |
| Aggregation Helpers (`api/funcs.py`) | Provide `get_query_week`, `get_weekly_data`, and `get_rolling_avg` for date normalization and tabular aggregation | pandas 2.0.0, numpy 1.24.2, python-dateutil 2.8.2 | Called from `/api/`, `/api/week`, `/api/analysis` handlers |

**Critical considerations for the backend tier:**

- The `Flask Application Bootstrap` hardcodes the connection string `postgresql://postgres:postgres@postgres/db`. There is no environment-variable override path, so any deployment outside the Compose network requires a source modification.
- The `HTTP Routing Module` performs no input validation. `getattr(YearlyAvg, feature)` will raise `AttributeError` on an unknown feature, and `data[0].keys()` will raise `IndexError` on an empty result set — both becoming a generic Flask 500.
- The `ORM Models and Schemas` file omits `spotify_id` from the `Tracks.__init__` constructor parameter list even though the column is part of the schema. This is a documented discrepancy that primarily affects programmatic ingestion paths.
- The `Aggregation Helpers` module's `get_rolling_avg` uses `df[feature].rolling(5).mean()` — a five-year window — despite UI labels declaring "3 Year Rolling Average".

#### Frontend Tier Components

| Component Name | Primary Responsibility | Key Dependencies | Integration Points |
|---|---|---|---|
| Application Shell (`frontend/src/App.js`, `index.js`) | Mount React, manage `nav` and `activeTab` state, render Sidebar and three Section containers | React 17.0.2, react-dom 17.0.2 | Renders Sidebar; passes `activeTab`, `handleClick`, and `setNav` down |
| Navigation Primitives (`navigation/Sidebar.js`, `Tab.js`, `SmallTab.js`, `Hamburger.js`, `Section.js`) | Render the responsive tab strip, the mobile hamburger toggle, and the conditional `display:none` Section wrappers | styled-components 5.3.0 | 800px responsive breakpoint; tab IDs `0`, `1`, `3` (intentionally skips `2`) |
| Tracks View (`tracks/TracksSection.js`, `DatePicker.js`, `RadarChart.js`) | Fetch `/api/week/<date>`, render scrollable rank/artist/track list, and draw the radar of average audio features | React, @amcharts/amcharts4 4.10.19 | Native `fetch()` to backend; `<input type='date'>` bounded to 1958-07-27 → 2021-11-13 |
| Trends View (`trends/TrendsSection.js`, `FeatureSelect.js`, `LineChart.js`, `features.json`) | Fetch `/api/analysis/<feature>`, render two-series line chart (annual + rolling), and display feature descriptions | React, @amcharts/amcharts4 4.10.19 | Native `fetch()` to backend; hardcoded 7-option `<select>` excluding `valence` and `loudness` |
| About View (`about/AboutSection.js`) | Static presentational page describing the data sources, API endpoints, and frontend stack | React only | Anchor links to billboard.com, wikipedia, spotipy, spotify, amcharts, github |

**Critical considerations for the frontend tier:**

- The `Application Shell` uses `useState` exclusively. There is no Redux, Zustand, or React Context, so cross-tab state communication is mediated purely through `App.js`'s tab-change handler.
- The `Tracks View` calls `getData('2021-11-13')` with a hardcoded literal in its `useEffect`; the dynamic `new Date()` alternative exists in the file as a commented-out line directly above.
- Both the `Tracks View` and `Trends View` consume `feature.desctiption` (sic — the misspelled key from `features.json` is preserved verbatim in the component code).
- `RadarChart.js` and `LineChart.js` both contain a commented-out `chart.dispose()` call, meaning amCharts instances accumulate across tab switches and risk client-side memory growth on long sessions.

#### Infrastructure Tier Components

| Component Name | Primary Responsibility | Key Dependencies | Integration Points |
|---|---|---|---|
| Container Image Build (`Dockerfile`) | Produce the `api` image atop `python:3.11-slim-buster` with `libpq-dev` and `gcc`, install pinned Python dependencies, and run `python3 app.py` | Docker, Python 3.11, requirements.txt | `EXPOSE 5000`; consumed by Compose |
| Compose Orchestration (`docker-compose.yml`) | Define the two-service stack with port mappings, environment variables, restart policy, and bind-mounts | Docker Compose, postgres:15 image | `api` (`80:5000`, `restart: on-failure`, bind `.:/app/`); `postgres` (`5432:5432`, bind `./data:/data`) |
| Persistence Volume (`./data` bind-mount) | Host-side directory that backs PostgreSQL data files for cross-restart durability | Filesystem | Mounted into the `postgres` container at `/data` |

**Critical considerations for the infrastructure tier:**

- The `Container Image Build` invokes `python3 app.py`, which starts Flask's built-in development server. `gunicorn==20.1.0` is pinned in `requirements.txt` but never invoked, so production traffic is served by a single-threaded development WSGI server.
- The `Compose Orchestration` declares `restart: on-failure` on the `api` service but no restart policy on `postgres`. A PostgreSQL crash will not auto-recover.
- The `./data:/data` bind-mount provides simple local durability but is not a backup strategy — there is no snapshot, off-host replication, or point-in-time recovery configured anywhere in the repository.

### 5.1.3 Data Flow Description

#### Primary Data Flows

The application supports two fetch-driven user workflows and one zero-fetch presentational workflow. All flows follow the same skeleton: SPA renders → `useEffect` fires → native `fetch()` issued → Flask handler runs → SQLAlchemy reads → Marshmallow dumps → optional in-process aggregation → `jsonify` → React state update → amCharts render.

The **Tracks workflow** is the only auto-triggered flow on application load. The browser issues `GET /` to receive `index.html`, mounts React with `activeTab=0`, and the `TracksSection` `useEffect` immediately calls `getData('2021-11-13')`. Flask matches `/api/week/<week>`, pipes the input through `get_query_week()` for Saturday-boundary normalization, queries `Tracks.query.filter_by(week=week).order_by(Tracks.rank).all()`, dumps via `tracks_schema.dump()`, runs `get_weekly_data()` to produce per-feature integer averages plus an `avgTempo`, and returns a JSON object containing `week`, `songs`, `averages`, and `avgTempo`. The SPA renders the rank/artist/track list and a radar chart whose five axes consume the proportional features and whose `full=100` baseline produces the radar's outer hull.

The **Trends workflow** activates when the user clicks the Trends sidebar tab (id `1`). `App.handleClick` updates `activeTab` to `1`, the `TrendsSection` mounts and fires `getData('tempo')` on first activation. Flask matches `/api/analysis/<feature>`, performs `YearlyAvg.query.with_entities(YearlyAvg.year, getattr(YearlyAvg, feature))`, dumps via `yearly_schema.dump()`, and pipes the result through `get_rolling_avg()`. The helper builds a Pandas DataFrame, computes a five-row rolling mean, sanitizes NaN to `None`, renames the dynamic feature column to `value`, and drops the first four NaN-rolling rows. The SPA renders a two-series line chart ("Annual Average" dashed, "3 Year Rolling Average" solid — the latter label is a known UI/code discrepancy with the five-year window).

The **About workflow** is a pure presentational tab activation. There is no fetch, no `useEffect`, and no state in `AboutSection.js`; selecting tab `3` simply unhides the corresponding `Section` wrapper.

#### Integration Patterns and Protocols

- **Browser ↔ Backend**: Native `fetch()` over HTTP/1.1 with `application/json` request/response. No request bodies are sent (all routes are `GET`). No authentication tokens, no cookies, no CSRF tokens. Although `axios` is declared in `frontend/package.json`, it is not imported anywhere.
- **Backend ↔ Database**: SQLAlchemy 1.4.19 over `psycopg2` 2.9.6 binary driver, parameterized via the ORM API, on TCP `5432` inside the Compose network. Read-only routes rely on PostgreSQL's autocommit-equivalent behavior; no explicit `db.session.commit()` or `db.session.rollback()` is invoked.
- **External Pipeline ↔ Database**: Out-of-repository job that writes `tracks` rows weekly and refreshes `yearly_avg` annually. The Flask process performs no outbound HTTP to Billboard or Spotify; data freshness depends entirely on this external cadence.
- **Compose internal**: DNS-based service discovery — the Flask connection string references the host `postgres`, which Compose resolves to the `postgres` service on the same bridge network.

#### Data Transformation Points

- **`get_query_week(date)`** in `api/funcs.py`: Maps any date input (or `None`) to the appropriate Billboard chart Saturday. The branch logic returns the previous Saturday for Sunday/Monday/Tuesday and Wednesdays before 10:00 AM, otherwise returns the next Saturday. Used by `/api/` (the redirect target) and `/api/week/<week>`.
- **`get_weekly_data(data)`**: Computes per-feature averages with `int(series.mean() * 100)` for the proportional features (`energy`, `danceability`, `speechiness`, `acousticness`, `instrumentalness`) plus `int(df['tempo'].mean())` for tempo. Output is shaped as records of `{feature, mean, full=100}` to feed the radar baseline.
- **`get_rolling_avg(data)`**: Computes `df[feature].rolling(5).mean()`, sanitizes NaN via `df.where(pd.notnull(df), None)`, renames the feature column to `value`, and filters out the first four NaN-rolling rows.
- **Marshmallow `dump()`**: Projects ORM rows into JSON-safe dicts; never `load()`. The serialization layer is one-way.

#### Key Data Stores and Caches

- **PostgreSQL `tracks` table** — One row per `(week, rank)` chart entry, enriched with Spotify audio features. Read by four endpoints (`/api/track`, `/api/week`, `/api/artist`, plus the `/api/` redirect through `/api/week`).
- **PostgreSQL `yearly_avg` table** — One row per year holding pre-aggregated annual feature averages. Read by `/api/analysis`.
- **Caches**: The system has **no caching layer at any tier**. There is no Redis, no Memcached, no `Flask-Caching`, no `functools.lru_cache` in routes/helpers, no HTTP `Cache-Control`/`ETag`/`Last-Modified` headers set by any handler, no Service Worker, and no `localStorage`/`sessionStorage`/cookie persistence on the client. Every request results in a fresh database query and a fresh aggregation pass.

### 5.1.4 External Integration Points

| System Name | Integration Type | Data Exchange Pattern | Protocol/Format |
|---|---|---|---|
| PostgreSQL 15 (`postgres` service) | In-stack database | Synchronous request/response per Flask request | TCP `5432`, PostgreSQL wire protocol via `psycopg2` |
| React Production Build (`frontend/build/`) | Filesystem static assets | Static file delivery via `static_folder` | HTTP `200` with `text/html`, `text/javascript`, `text/css` |
| Spotify Web API (out-of-repo) | External enrichment (write-side only) | Batch enrichment by external scraper | HTTPS / JSON (executed outside this repository) |
| Billboard Hot 100 chart pages (out-of-repo) | External data source (write-side only) | Weekly scrape by external scraper | HTTPS / HTML (executed outside this repository) |
| Google Fonts (Jost family) | Third-party browser CDN | Page-load font fetch with preconnect hints | HTTPS / WOFF2 |

**SLA requirements**: No Service Level Agreement is codified anywhere in the repository for any of these integrations. There are no latency targets, no timeout values configured on Flask routes, no `AbortController` on frontend fetches, no rate limits, no `MAX_CONTENT_LENGTH`, and no deadline propagation through helper functions. Operationally, the only timing-sensitive constraint observable in the code is the chart-week boundary at 10:00 AM Wednesday inside `get_query_week`, which aligns with Billboard's mid-week chart finalization cadence. The external pipeline is expected to run weekly (for `tracks`) and annually or on backfill (for `yearly_avg`).

---

## 5.2 COMPONENT DETAILS

### 5.2.1 Backend Application Bootstrap

**Purpose and responsibilities.** The bootstrap component (`api/__init__.py` plus the thin entry point `app.py`) constructs the Flask application object, configures it for SPA delivery, and wires three Flask extensions. It is responsible for ensuring that a single Flask instance can serve both the React production build and the JSON API on the same origin.

**Technologies and frameworks used.** Flask 2.0.1 is the HTTP framework; Flask-SQLAlchemy 2.5.1 provides the ORM integration as the `db` instance; flask-marshmallow 0.14.0 provides serialization integration as the `ma` instance; Flask-Cors 3.0.10 registers permissive CORS as defense-in-depth. `SQLALCHEMY_TRACK_MODIFICATIONS` is explicitly set to `False` to suppress the deprecation warning.

**Key interfaces and APIs.** The constructed app exposes `app.run(host='0.0.0.0')` to the entry point, accepts incoming HTTP traffic on container port `5000`, and imports `api.routes` at the bottom of `__init__.py` to register the route handlers via Flask's decorator pattern.

**Data persistence requirements.** The component hardcodes the connection string `postgresql://postgres:postgres@postgres/db` and relies entirely on Flask-SQLAlchemy's default connection pool; no pool size, overflow, recycle, or timeout values are configured.

**Scaling considerations.** Bootstrap is invoked once per container start; since the production launcher is `python3 app.py`, the resulting Flask development server is single-threaded and processes one in-flight request at a time. Horizontal scaling would require switching to gunicorn (already pinned in `requirements.txt`) or another WSGI server, plus externalizing the connection string to environment variables.

### 5.2.2 HTTP Routing Module

**Purpose and responsibilities.** `api/routes.py` defines the six handlers that constitute the entire API surface — one static-asset handler at `/` and five JSON handlers under `/api/*`. Each handler issues a SQLAlchemy query, optionally invokes a helper from `api/funcs.py`, dumps the result via Marshmallow, and returns a `flask.jsonify` response.

**Technologies and frameworks used.** Flask routing decorators, the `db` and `ma` instances from the bootstrap module, the `Tracks` and `YearlyAvg` ORM models, and the helper functions in `funcs.py`. No request-validation framework is used.

**Key interfaces and APIs.** The complete contract is enumerated in section 5.1.1; each handler maps a URL pattern to a deterministic SQL query plus an optional aggregation step.

**Data persistence requirements.** All routes are `GET`-only and read-only. No `db.session.commit()` or `db.session.rollback()` calls exist in the module.

**Scaling considerations.** The `LOWER(...) LIKE '%pattern%'` form in `/api/artist/<name>` cannot exploit B-tree indexes and degrades to a full-table scan as `tracks` grows. The `/api/week/<week>` response is bounded by ≤100 rows per week (the chart size), and the `/api/analysis/<feature>` response is bounded by ~70 rows (one per year of chart history). No route caches its result.

### 5.2.3 Persistence Models and Schemas

**Purpose and responsibilities.** `api/models.py` defines two ORM tables and their Marshmallow projections. `Tracks` is the granular entity (one row per `(week, rank)` with embedded Spotify audio features); `YearlyAvg` is a pre-aggregated annual roll-up of eight feature averages. `TrackSchema` and `YearlyAvgSchema` define the JSON shape the API emits.

**Technologies and frameworks used.** SQLAlchemy 1.4.19 declarative models, marshmallow 3.12.1 schemas, marshmallow-sqlalchemy 0.26.1 as the ORM-to-schema adapter.

**Key interfaces and APIs.** The models expose query methods such as `Tracks.query.filter_by(week=...)` and `YearlyAvg.query.with_entities(...)` consumed by the routes module. The schemas expose `dump()` (used) and `load()` (not used anywhere — codifying the read-only contract).

**Data persistence requirements.** Both tables are populated externally; the application does not own their schema migration story. The `valence` and `loudness` columns exist on `Tracks` but are intentionally excluded from the `FeatureSelect` dropdown on the frontend; the `Tracks.__init__` constructor omits the `spotify_id` parameter despite the column existing on the table.

**Scaling considerations.** Cardinality for `tracks` grows weekly (~100 rows/week × decades of history). Cardinality for `yearly_avg` grows by one row per year. Neither table is partitioned in the schema declaration, and no explicit indexes beyond the primary key are visible in the model definitions.

### 5.2.4 Aggregation Helper Module

**Purpose and responsibilities.** `api/funcs.py` provides three pure functions that encapsulate the system's only non-trivial data transformations: date normalization to chart-week boundaries (`get_query_week`), per-week feature averaging (`get_weekly_data`), and longitudinal rolling means (`get_rolling_avg`).

**Technologies and frameworks used.** pandas 2.0.0 DataFrames for tabular aggregation, numpy 1.24.2 as Pandas' computational backbone, python-dateutil 2.8.2 for date arithmetic.

**Key interfaces and APIs.** The functions are called from the routes module synchronously inside the request thread; none of them open external connections, perform I/O, or maintain state between calls.

**Data persistence requirements.** None — these are stateless transformation functions whose lifecycle is tied to the request that invokes them.

**Scaling considerations.** `get_weekly_data` runs on ≤100-row inputs; `get_rolling_avg` runs on ~70-row inputs; both are constant-time relative to dataset size at the per-request granularity. Memory pressure is negligible. The amCharts client-side memory question (no `chart.dispose()`) is upstream of this module.

### 5.2.5 Frontend Application Shell

**Purpose and responsibilities.** `frontend/src/App.js` and `index.js` are the React entry point and the top-level container. The shell mounts `<App/>` into `#root`, owns the `nav` (mobile sidebar toggle) and `activeTab` (current view) state, and renders the persistent `<StSidebar>` plus three `<Section>` wrappers (one each for Tracks, Trends, About). The `handleClick` callback parses the clicked tab's numeric `id`, guards against the no-op case, updates `activeTab`, and resets `nav` to `false`.

**Technologies and frameworks used.** React 17.0.2, react-dom 17.0.2, styled-components 5.3.0 (for the navigation primitives in `frontend/src/components/navigation/`), and CRA 4.0.3 (`react-scripts`) as the build toolchain. Plain JavaScript is used — no TypeScript, no Babel plugins beyond the CRA defaults.

**Key interfaces and APIs.** The shell renders the Sidebar, three Section containers, and a footer. It passes `activeTab`, `handleClick`, `nav`, and `setNav` down via props. There is no React Context, no Redux store, and no router (the SPA is single-screen with tabs, not URL-routed).

**Data persistence requirements.** None at the client tier — no `localStorage`, no `sessionStorage`, no cookies, no IndexedDB, no Service Worker cache. Every page reload starts from the default state.

**Scaling considerations.** The shell is rendered exactly once per session. The non-contiguous tab indices (`0`, `1`, `3` — index `2` is intentionally skipped) are consistent across `App.js` and `Sidebar.js`, but any future tab insertion must continue to honor this convention or refactor both files.

### 5.2.6 Tracks Visualization Pipeline

**Purpose and responsibilities.** The pipeline (`tracks/TracksSection.js`, `tracks/DatePicker.js`, `tracks/RadarChart.js`) presents the Weekly Snapshot view. `TracksSection` orchestrates the fetch lifecycle (`data`, `isLoaded`, `error` state), `DatePicker` collects user input, and `RadarChart` renders an amCharts4 `RadarChart` into the `#radialChart` DOM node with `startAngle=-90, endAngle=180` (a semi-circular layout).

**Technologies and frameworks used.** React 17.0.2 with `useState`/`useEffect`, the browser's native `fetch()` API, `@amcharts/amcharts4` 4.10.19 for charting. The `<input type='date'>` is browser-native HTML with `min='1958-07-27'` and `max='2021-11-13'`.

**Key interfaces and APIs.** Consumes `GET /api/week/<date>`. The initial mount calls `getData('2021-11-13')` with a hardcoded date literal (the `new Date()` alternative is commented out on the line above). User submissions flow through `DatePicker.handleSubmit`, which calls `e.preventDefault()` and a truthy guard before invoking `submitFunc`.

**Data persistence requirements.** None.

**Scaling considerations.** The amCharts instance is created per render but never disposed (`chart.dispose()` is commented out at `RadarChart.js` line 66). Long-lived sessions that traverse many weeks will accumulate chart instances until the SPA is reloaded.

### 5.2.7 Trends Visualization Pipeline

**Purpose and responsibilities.** The pipeline (`trends/TrendsSection.js`, `trends/FeatureSelect.js`, `trends/LineChart.js`, `trends/features.json`) presents the longitudinal Feature Trend view. `TrendsSection` orchestrates the fetch, `FeatureSelect` provides a hardcoded seven-option dropdown (`tempo`, `energy`, `danceability`, `instrumentalness`, `liveness`, `speechiness`, `acousticness` — `valence` and `loudness` are excluded), and `LineChart` renders an amCharts4 `XYChart` into `#featureChart` with two `LineSeries`: "Annual Average" (dashed) and "3 Year Rolling Average" (solid).

**Technologies and frameworks used.** Same React/fetch/amCharts stack as the Tracks pipeline. `features.json` is a static JSON asset bundled by Webpack.

**Key interfaces and APIs.** Consumes `GET /api/analysis/<feature>`. The initial mount calls `getData('tempo')`. The component renders feature descriptions sourced from `features.json` via the typo'd key `feature.desctiption` (preserved verbatim from the JSON).

**Data persistence requirements.** None.

**Scaling considerations.** The "3 Year Rolling Average" UI label is a known mismatch with the backend's five-row pandas window; future maintainers should reconcile either the label or the helper. The same `chart.dispose()` omission applies as in `RadarChart.js` (commented out at `LineChart.js` line 70).

### 5.2.8 About Documentation View

**Purpose and responsibilities.** `about/AboutSection.js` is a purely presentational static component documenting the data sources, the API endpoints, and the frontend stack. It has no `useEffect`, no state, no fetch, and no callbacks.

**Technologies and frameworks used.** React 17.0.2 only. No charting, no async behavior.

**Key interfaces and APIs.** Outbound anchor links to billboard.com, Wikipedia (Hot 100), Spotipy documentation, the Spotify developer site, the amCharts site, and the project's GitHub repository.

**Data persistence requirements.** None.

**Scaling considerations.** Zero runtime cost beyond the initial JSX render.

### 5.2.9 Container Orchestration

**Purpose and responsibilities.** `Dockerfile` and `docker-compose.yml` together define how the system is built and run. The Dockerfile produces the `api` image atop `python:3.11-slim-buster`, installs `libpq-dev` and `gcc` (required for `psycopg2` compilation), runs `pip3 install -r requirements.txt`, exposes port `5000`, and sets `CMD ["python3", "app.py"]` as the entrypoint. Compose declares two services with port mappings, environment variables, and bind-mount volumes.

**Technologies and frameworks used.** Docker, Docker Compose, the `postgres:15` official image, `python:3.11-slim-buster` base image. The `.dockerignore` excludes `frontend/node_modules`, `venv`, and `data` from the build context.

**Key interfaces and APIs.** The `api` service publishes `80:5000`; the `postgres` service publishes `5432:5432`. Environment variables on the `api` service include `NODE_OPTIONS=--openssl-legacy-provider` (to permit `react-scripts build` on newer Node releases). The `api` service declares `depends_on: postgres` for ordering and `restart: on-failure` for crash recovery; `postgres` declares no restart policy.

**Data persistence requirements.** The `postgres` service mounts `./data:/data` from the host, providing local-filesystem durability across container restarts.

**Scaling considerations.** The Compose model targets a single host. There is no orchestration metadata for Kubernetes, ECS, or Nomad. Horizontal scaling beyond a single `api` replica would require introducing a reverse proxy and replacing the development server with gunicorn.

### 5.2.10 Component Interaction Diagram

The following diagram shows the steady-state runtime interactions among the nine logical components. Edges are labeled with the dominant communication mechanism.

```mermaid
flowchart LR
    subgraph BrowserEnv["Browser Environment"]
        Shell[App Shell<br/>App.js]
        Tracks[Tracks Pipeline<br/>TracksSection + DatePicker + RadarChart]
        Trends[Trends Pipeline<br/>TrendsSection + FeatureSelect + LineChart]
        About[About View<br/>AboutSection.js]
        Nav[Navigation Primitives<br/>Sidebar + Tab + Hamburger + Section]
    end

    subgraph ApiEnv["api container"]
        Boot[Bootstrap<br/>api/__init__.py + app.py]
        RoutesC[Routes Module<br/>api/routes.py]
        Helpers[Aggregation Helpers<br/>api/funcs.py]
        Models[Models and Schemas<br/>api/models.py]
        BuildAssets[Static Assets<br/>frontend/build/]
    end

    subgraph DataEnv["postgres container"]
        DB[(PostgreSQL 15<br/>tracks + yearly_avg)]
    end

    subgraph Infra["Compose Orchestration"]
        Image[api Image<br/>Dockerfile]
        Volume[(./data bind-mount)]
    end

    Shell -- props --> Nav
    Shell -- props --> Tracks
    Shell -- props --> Trends
    Shell -- props --> About
    Tracks -- fetch /api/week --> RoutesC
    Trends -- fetch /api/analysis --> RoutesC
    Shell -- GET / --> Boot
    Boot -- send_static_file --> BuildAssets
    Boot --> RoutesC
    RoutesC -- helpers call --> Helpers
    RoutesC -- ORM query --> Models
    Models -- SQLAlchemy --> DB
    DB --- Volume
    Image -- builds --> Boot
```

### 5.2.11 Application State Transitions

The shell's `activeTab` state machine drives which `Section` wrapper is visible. The state space is non-contiguous — index `2` is intentionally absent — and re-clicking the active tab is a guarded no-op.

```mermaid
stateDiagram-v2
    [*] --> Tracks: activeTab=0 default on mount
    Tracks --> Trends: Sidebar tab id=1 clicked
    Tracks --> About: Sidebar tab id=3 clicked
    Trends --> Tracks: Sidebar tab id=0 clicked
    Trends --> About: Sidebar tab id=3 clicked
    About --> Tracks: Sidebar tab id=0 clicked
    About --> Trends: Sidebar tab id=1 clicked
    Tracks --> Tracks: Same tab guarded no-op
    Trends --> Trends: Same tab guarded no-op
    About --> About: Same tab guarded no-op
```

The fetch lifecycle inside `TracksSection` and `TrendsSection` is identical and follows the four-state machine below.

```mermaid
stateDiagram-v2
    [*] --> Initial: Component mounts
    Initial --> Loading: useEffect fires getData
    Loading --> Success: data length greater than 0
    Loading --> HttpError: response status greater than 299
    Loading --> EmptyData: data length equals 0
    Success --> Loading: User submits new query
    HttpError --> Loading: User submits new query
    EmptyData --> Loading: User submits new query
```

### 5.2.12 Sequence Diagram for the Tracks Workflow

The diagram below traces a representative request from the moment the SPA mounts to the moment the radar chart becomes visible.

```mermaid
sequenceDiagram
    participant User as Browser
    participant Shell as App Shell
    participant TS as TracksSection
    participant API as Flask Routes
    participant H as Helpers
    participant ORM as SQLAlchemy
    participant DB as PostgreSQL
    participant Chart as RadarChart

    User->>Shell: GET / (HTML + JS)
    Shell->>Shell: Mount with activeTab=0
    Shell->>TS: Render Section
    TS->>API: fetch /api/week/2021-11-13
    API->>H: get_query_week(week)
    H-->>API: Saturday boundary
    API->>ORM: Tracks.query.filter_by.order_by.all
    ORM->>DB: SELECT * FROM tracks WHERE week=$1
    DB-->>ORM: Row stream
    ORM-->>API: List of Tracks instances
    API->>API: tracks_schema.dump
    API->>H: get_weekly_data(songs)
    H-->>API: averages + avgTempo
    API-->>TS: 200 application/json
    TS->>TS: setData / setIsLoaded
    TS->>Chart: Pass averages prop
    Chart->>User: Render radar
```

---

## 5.3 TECHNICAL DECISIONS

### 5.3.1 Architecture Style Decisions

The decision to adopt a **two-tier monolith** rather than a microservice or serverless decomposition is driven by the matrix below. The system has a single bounded context, a solo maintainer, and a read-heavy public-access workload — a profile for which a monolith is the lowest-friction option.

| Style Considered | Pros for This System | Cons for This System | Outcome |
|---|---|---|---|
| Two-tier monolith (selected) | Simple deploy via `docker compose up`; no inter-service network; same-origin SPA + API | Single failure domain; one process serves SPA + API | Selected |
| Microservices | Independent scaling per concern | No bounded contexts to split; would multiply ops surface | Rejected |
| Serverless / FaaS | No long-lived processes to manage | No cloud SDK present; cold-start would harm chart-render UX | Rejected |
| Static SPA + BaaS (Firebase/Supabase) | Eliminates backend code | Aggregation helpers (`get_weekly_data`, `get_rolling_avg`) need server-side Pandas | Rejected |

```mermaid
flowchart TD
    Start[Architecture Style Decision] --> Q1{Multiple bounded<br/>contexts?}
    Q1 -->|No - single domain| Q2{Independent scaling<br/>per concern needed?}
    Q1 -->|Yes| Micro[Microservices]
    Q2 -->|No - uniform load| Q3{Server-side<br/>aggregation needed?}
    Q2 -->|Yes| Micro
    Q3 -->|Yes - Pandas helpers| Q4{Solo maintainer?}
    Q3 -->|No| Static[Static SPA + BaaS]
    Q4 -->|Yes| Mono[Two-tier monolith]
    Q4 -->|No - large team| Micro
    Mono --> Selected([Selected])
    Micro --> Rejected([Rejected])
    Static --> Rejected
```

### 5.3.2 Communication Pattern Choices

| Decision | Selected Pattern | Alternative Considered | Rationale |
|---|---|---|---|
| Browser↔Backend transport | Native browser `fetch()` | `axios` (declared but never imported) | Reduces bundle size; browser fetch has been universal since IE was deprecated; `axios` was retained as a dependency by oversight |
| Request idempotency | All `GET`, no body | `POST` with JSON body for date/feature submission | The query is fully expressible as a path parameter; `GET` permits browser caching and simpler URL sharing |
| Cross-origin policy | Permissive `CORS(app)` | Strict allow-list | Production traffic is same-origin (SPA served by the same Flask process); permissive CORS only matters for the development proxy |
| Inter-tier protocol | PostgreSQL wire over `psycopg2` | HTTP REST to a separate API service | Direct SQL is the simplest path for read-only aggregation queries; an intermediate service would add latency without value |

### 5.3.3 Data Storage Solution Rationale

| Decision | Choice | Rationale |
|---|---|---|
| Database engine | PostgreSQL 15 | Strong relational primitives for chart-row joins; mature `psycopg2` ecosystem; `LOWER(...) LIKE` works without extension |
| Schema shape | Two tables: granular `tracks` + pre-aggregated `yearly_avg` | Avoids running annual aggregation on every `/api/analysis` request; keeps weekly snapshot queries simple |
| Migration strategy | None in repo | The write-side pipeline (out-of-repo) owns DDL; the read-side application is a consumer |
| Connection pooling | Flask-SQLAlchemy defaults | No tuned configuration is justified given the single-threaded development server upstream |
| Persistence durability | `./data:/data` bind-mount | Trivial local durability; not a backup strategy |

The two-table model balances query simplicity against precomputation. Aggregating yearly means at request time would scan tens of thousands of `tracks` rows per call; the `yearly_avg` table reduces this to ~70 rows per call.

### 5.3.4 Caching Strategy Justification

The system implements **no caching** at any tier. The decision matrix below explains why each commonly considered cache layer was deferred.

| Cache Tier | Implementation Status | Rationale |
|---|---|---|
| HTTP response cache (`Cache-Control`/`ETag`) | Absent | No `flask-caching`; no headers set by handlers; data freshness assumptions are weekly, not real-time, but no operator has codified that constraint |
| In-process LRU (`functools.lru_cache`) | Absent | Each request reaches the database; throughput requirements have not justified the memory cost |
| Distributed cache (Redis/Memcached) | Absent | No cache service in `docker-compose.yml`; would require operational ownership not aligned with the solo-maintainer model |
| Browser persistence (`localStorage`/Service Worker) | Absent | No frontend persistence layer; reload always re-fetches |
| CDN | Absent | Static assets are served directly by Flask; suitable for low-traffic public access |

The acceptable-as-is rationale is that the read-side workload is bounded: `/api/week` returns ≤100 rows, `/api/analysis` returns ≤~70 rows, and the dataset itself updates only weekly. Introducing a cache would add operational complexity disproportionate to its benefit at current traffic levels. The artist search (`LIKE '%pattern%'`) is the most expensive query and would be the first candidate for caching if traffic grew.

### 5.3.5 Security Mechanism Selection

| Concern | Selected Mechanism | Rationale |
|---|---|---|
| Authentication | None | Public-read dataset; explicit non-goal |
| Authorization | None | No state-changing endpoints exist |
| CSRF | None | No state-changing endpoints exist; CSRF risk is structurally absent |
| Input validation | HTML-input bounds (frontend); none on backend | Adequate for HTML form clients; backend validation is a documented improvement opportunity |
| CORS | Permissive (`CORS(app)` no allow-list) | Same-origin in production; permissive defaults preserve dev-proxy ergonomics |
| Transport | Plaintext HTTP | TLS termination is delegated to a future reverse-proxy layer |
| Secrets management | Hardcoded in `api/__init__.py` | Documented limitation; not suitable for production reuse |

The security posture is intentionally minimal because there is no user-identifiable data, no payment data, and no PII in the system. The dataset is a public chart; the audio features are a public-API derivative. The most material exposure is the host-published `5432:5432` port mapping with default credentials, which is acceptable for development hosts but must be removed before any internet-facing deployment.

### 5.3.6 Architecture Decision Records

Each ADR below captures a key decision in compressed form: context, decision, status, and consequence.

```mermaid
flowchart TD
    subgraph ADR1["ADR-001 Single-Process SPA + API"]
        A1Ctx[Context: Solo maintainer<br/>same-origin OK]
        A1Dec[Decision: static_folder='../frontend/build'<br/>static_url_path='/']
        A1Con[Consequence: One container serves<br/>both; simplifies CORS]
        A1Ctx --> A1Dec --> A1Con
    end

    subgraph ADR2["ADR-002 Pre-Aggregated YearlyAvg"]
        A2Ctx[Context: Annual means<br/>are stable]
        A2Dec[Decision: Persist yearly_avg;<br/>compute rolling at request time]
        A2Con[Consequence: O 70 rows<br/>per analysis call]
        A2Ctx --> A2Dec --> A2Con
    end

    subgraph ADR3["ADR-003 Native fetch over axios"]
        A3Ctx[Context: Modern browsers<br/>have universal fetch]
        A3Dec[Decision: Use native fetch;<br/>leave axios unimported]
        A3Con[Consequence: Smaller bundle;<br/>axios is dead dependency]
        A3Ctx --> A3Dec --> A3Con
    end

    subgraph ADR4["ADR-004 No Caching Tier"]
        A4Ctx[Context: Bounded result sizes<br/>weekly update cadence]
        A4Dec[Decision: Defer all caching;<br/>no Redis no ETag]
        A4Con[Consequence: Every request<br/>hits Postgres]
        A4Ctx --> A4Dec --> A4Con
    end

    subgraph ADR5["ADR-005 Local React State Only"]
        A5Ctx[Context: Three independent<br/>tabs no shared state]
        A5Dec[Decision: useState per Section;<br/>no Redux no Context]
        A5Con[Consequence: Zero<br/>state-management overhead]
        A5Ctx --> A5Dec --> A5Con
    end

    subgraph ADR6["ADR-006 Flask Dev Server in Production"]
        A6Ctx[Context: Low traffic<br/>solo maintainer]
        A6Dec[Decision: CMD python3 app.py<br/>despite gunicorn being installed]
        A6Con[Consequence: Single-threaded;<br/>not suitable for high concurrency]
        A6Ctx --> A6Dec --> A6Con
    end
```

| ADR | Status | Revisit Trigger |
|---|---|---|
| ADR-001 Single-Process SPA + API | Accepted | If teams split or independent SPA deploy is required |
| ADR-002 Pre-Aggregated `YearlyAvg` | Accepted | If feature dimensionality grows beyond the YearlyAvg schema |
| ADR-003 Native `fetch` | Accepted | If retry/interceptor/cancellation logic becomes pervasive |
| ADR-004 No Caching Tier | Accepted (provisional) | If `/api/artist` traffic grows or DB load rises |
| ADR-005 Local React State Only | Accepted | If cross-tab state sharing becomes necessary |
| ADR-006 Flask Dev Server | Accepted (provisional) | Before any internet-facing production deployment |

---

## 5.4 CROSS-CUTTING CONCERNS

### 5.4.1 Monitoring and Observability Approach

The repository contains **no observability instrumentation of any kind**. The monitoring posture is summarized below:

| Concern | Status | Notes |
|---|---|---|
| Application Performance Monitoring (APM) | Absent | No DataDog, New Relic, or AppDynamics SDK |
| Error reporting | Absent | No Sentry, Rollbar, or Bugsnag SDK |
| Metrics endpoint | Absent | No Prometheus client, no statsd |
| Real-User Monitoring (RUM) | Declared but unwired | `web-vitals` 1.0.1 is in `package.json` but has no `reportWebVitals()` call |
| Health check endpoints | Absent | No `/healthz`, `/readyz`, or equivalent in `api/routes.py` |
| Distributed tracing | Absent | No OpenTelemetry or Zipkin/Jaeger client |

Operationally, the only observation surface is Flask's default request logging on stdout (captured by the Docker engine's logging driver) and PostgreSQL's stdout from the `postgres:15` image. Any production hardening will need to introduce, at minimum, a `/healthz` endpoint, structured request logging, and an error-reporting SDK.

### 5.4.2 Logging and Tracing Strategy

The current strategy is the **Flask default**: each request is logged to stdout in Werkzeug's default format, and exceptions are dumped as Python tracebacks to stderr. There is no:

- Structured logger (`structlog`, `loguru`) — log entries are unstructured strings.
- `logging.config` configuration — no per-module log levels, no formatters, no handlers beyond the default.
- Correlation IDs — no per-request UUID, no `X-Request-ID` echoed back to clients.
- Log shipping — no Fluent Bit, Logstash, Vector, or cloud-native agent in either container.
- Trace propagation — no `traceparent` or B3 headers set or honored.

For development this is sufficient. For production it would require, at minimum, JSON-formatted logs with timestamps and request correlation IDs, plus a forwarder to a central aggregation store.

### 5.4.3 Error Handling Patterns

Error handling is intentionally minimal and consistent. The model below shows the architectural-level error flow combining the frontend and backend halves.

```mermaid
flowchart TD
    Req[Browser fetch] --> NetCheck{Network<br/>error?}
    NetCheck -->|Yes| Unhandled[Unhandled promise rejection<br/>browser console only]
    NetCheck -->|No| HttpCheck{HTTP status<br/>greater than 299?}
    HttpCheck -->|Yes| FrontErr[setError statusText<br/>setIsLoaded true]
    HttpCheck -->|No| ParseJson[await response.json]
    ParseJson --> Empty{data length<br/>equals 0?}
    Empty -->|Yes| FrontEmpty[setError 'No Data Found'<br/>setIsLoaded true]
    Empty -->|No| Success[setData<br/>setIsLoaded true]
    FrontErr --> RenderErr[Render h1.error]
    FrontEmpty --> RenderErr
    Success --> RenderOk[Render success view]
    Unhandled --> Stuck[isLoaded stays false<br/>loading spinner forever]

    Req2[Flask handler executes] --> ExcCheck{Exception<br/>raised?}
    ExcCheck -->|No| Ok200[200 OK with JSON]
    ExcCheck -->|Yes| ExcType{Class?}
    ExcType -->|AttributeError invalid feature| Five[Flask default 500]
    ExcType -->|IndexError empty data| Five
    ExcType -->|psycopg2 invalid date| Five
    ExcType -->|psycopg2 connection lost| Five
    Five --> NoBody[No structured error body<br/>HTML stack trace if debug]
```

**Critical gaps documented in section 4.5:**

- Neither `TracksSection.getData` nor `TrendsSection.getData` wraps `await fetch(...)` in a `try/catch`. A network-level failure produces an unhandled promise rejection visible only in the browser console; the UI remains stuck at `isLoaded=false` indefinitely.
- No backend route handler uses `try/except`. All exceptions bubble up to Flask's default 500 response.
- No frontend `ErrorBoundary` component is registered.
- No retry logic exists at any tier (no `axios-retry`, `p-retry`, `tenacity`, or `backoff`).
- No circuit breaker is configured (no `pybreaker`).
- User-side recovery is manual: re-submit the form via DatePicker/FeatureSelect, or reload the page.

The endpoint-by-endpoint error matrix is:

| Endpoint | Failure Class | HTTP Outcome | Frontend Treatment |
|---|---|---|---|
| `/api/week/<week>` | Invalid date string | 500 | `setError(statusText)` |
| `/api/week/<week>` | No matching rows | 200 with empty arrays | Renders empty list + radar with `NaN` `avgTempo` |
| `/api/track/<id>` | Unknown ID | 200 with `[]` | Treated as "No Data Found" |
| `/api/artist/<name>` | No match | 200 with `[]` | Treated as "No Data Found" |
| `/api/analysis/<feature>` | Invalid feature | 500 (`AttributeError`) | `setError(statusText)` |
| `/api/analysis/<feature>` | Empty `YearlyAvg` | 500 (`IndexError`) | `setError(statusText)` |

### 5.4.4 Authentication and Authorization Framework

The system has **no authentication and no authorization**. Every route in `api/routes.py` is publicly accessible. There is:

- No OAuth/OIDC client.
- No session middleware (`Flask-Login`, `Flask-Session`).
- No JWT issuance or verification.
- No login or logout routes.
- No `@login_required`, `@roles_required`, or equivalent decorators.
- No API keys or bearer tokens required by any handler.
- No CSRF protection (acceptable because no state-changing endpoints exist).

This posture is appropriate for the public-read-only nature of the chart dataset and is documented as an explicit non-goal in section 2.4.4. Compliance considerations:

- No personal data is collected; no user accounts or sign-up flows exist.
- No GDPR/CCPA cookie banners are required because no cookies are set.
- No audit logging or access logs are configured beyond Flask's default request logging.

### 5.4.5 Performance Requirements and SLAs

**No SLAs are codified anywhere in the repository.** Concretely, the application does not declare:

- Latency targets in code or configuration.
- Timeout values on Flask routes (`@app.route` decorators have no timeout parameter, and Flask itself has no per-route timeout).
- `signal.alarm` or asyncio timeout wrappers in route handlers.
- `AbortController` usage on the frontend `fetch()` calls.
- Rate limits (`flask-limiter` is not installed).
- Request body size limits (`MAX_CONTENT_LENGTH` is not set).
- Deadline propagation through the helper functions.

The performance characteristics that *are* observable from the code are:

| Workflow | Bound | Detail |
|---|---|---|
| `/api/week/<week>` | ≤100 rows per response | Aggregation runtime dominated by network overhead |
| `/api/artist/<name>` | Full-table scan | `LOWER(...) LIKE '%pattern%'` cannot use B-tree indexes |
| `/api/analysis/<feature>` | ≤~70 rows | Rolling computation O(n) over `YearlyAvg` |
| Flask development server | Single-threaded | One in-flight request at a time; not optimized for concurrency |
| amCharts charts | Client-side memory growth | `chart.dispose()` is commented out in both `RadarChart.js` and `LineChart.js` |

Operational cadence (the only observable timing constraint):

- The chart-week boundary at 10:00 AM Wednesday in `get_query_week` aligns with Billboard's mid-week chart finalization.
- The external scraper runs weekly; `yearly_avg` is recomputed annually or on backfill.
- The React production bundle is rebuilt manually (`react-scripts build`) on frontend code changes.
- Container images are rebuilt manually on dependency changes.

### 5.4.6 Disaster Recovery Procedures

The repository's DR posture is summarized below. No multi-region, no replica, and no formal backup schedule is configured.

| Concern | Implementation | Recovery Time |
|---|---|---|
| `api` container crash | `restart: on-failure` policy in `docker-compose.yml` | Bounded by Docker's default backoff; typically seconds |
| `postgres` container crash | **No** restart policy declared | Manual intervention required |
| Data file corruption on `./data` bind-mount | No backup configured | Unrecoverable without external backup process |
| Host failure | None | Full re-provisioning required |
| Failed deploy | Manual rollback by re-running an older image | Operator-dependent |

Practical recovery flow on `api` crash:

```mermaid
flowchart TD
    Start[api container running app.py] --> Crash{Process exits<br/>non-zero?}
    Crash -->|Yes| Policy[Compose restart on-failure<br/>triggers]
    Policy --> Relaunch[Compose runs CMD<br/>python3 app.py]
    Relaunch --> Reimport[api package re-imports<br/>routes re-register]
    Reimport --> Start
    Crash -->|No| Continue[Continue serving]
    Continue --> Start
    Start --> PgCheck{postgres<br/>down?}
    PgCheck -->|Yes| ConnErr[Next DB query raises<br/>psycopg2 OperationalError]
    ConnErr --> Five[Flask returns 500]
    Five --> FrontErr[Frontend setError]
    PgCheck -->|No| Continue
```

The `api` container's bootstrap defers DB connection until the first request, so an `api`-restart-after-`postgres`-crash sequence will succeed at boot time and then begin failing at first request until `postgres` is manually restarted.

Recommended improvements (not present, but warranted for any production deployment):

- Add `restart: on-failure` to the `postgres` service.
- Introduce a periodic `pg_dump` or PostgreSQL streaming replication to an off-host target.
- Externalize the database credentials via environment variables to permit rotation.
- Add a `/healthz` endpoint and configure a Compose `healthcheck` block on the `api` service so Docker can detect zombie processes that have not crashed but have stopped serving.

---

## 5.5 References

### 5.5.1 Repository Files Examined

- `app.py` — Root entry point that imports the Flask app and runs it on `0.0.0.0`.
- `Dockerfile` — Image build recipe for the `api` service (python:3.11-slim-buster, libpq-dev, gcc, `CMD ["python3", "app.py"]`).
- `docker-compose.yml` — Two-service stack with port mappings, environment variables, volumes, and the `api` `restart: on-failure` policy.
- `requirements.txt` — Pinned Python dependencies (Flask 2.0.1, SQLAlchemy 1.4.19, marshmallow 3.12.1, pandas 2.0.0, psycopg2 2.9.6, gunicorn 20.1.0 declared but unused).
- `README.md` — Project documentation referencing Billboard, Spotipy, and the API endpoints.
- `.dockerignore` — Excludes `frontend/node_modules`, `venv`, `data` from the build context.
- `api/__init__.py` — Flask app bootstrap with hardcoded DB URL, `static_folder='../frontend/build'`, `CORS(app)`, `db`, `ma`.
- `api/routes.py` — All six HTTP route handlers.
- `api/models.py` — `Tracks` and `YearlyAvg` ORM models plus `TrackSchema` and `YearlyAvgSchema`.
- `api/funcs.py` — `get_query_week`, `get_weekly_data`, `get_rolling_avg`.
- `frontend/package.json` — npm dependencies, scripts, and the `"proxy": "http://localhost:5000"` field.
- `frontend/src/index.js` — React DOM mounting into `#root`.
- `frontend/src/App.js` — App shell with `nav`/`activeTab` state and `handleClick` tab dispatcher.
- `frontend/src/components/navigation/Sidebar.js` — Sidebar with tab IDs `0`/`1`/`3`.
- `frontend/src/components/navigation/Hamburger.js` — SVG hamburger button.
- `frontend/src/components/navigation/Tab.js`, `SmallTab.js`, `Section.js` — styled-components navigation primitives.
- `frontend/src/components/tracks/TracksSection.js` — Tracks tab orchestrator with the hardcoded `'2021-11-13'` initial fetch.
- `frontend/src/components/tracks/DatePicker.js` — Controlled `<input type='date'>` with `min='1958-07-27'` and `max='2021-11-13'`.
- `frontend/src/components/tracks/RadarChart.js` — amCharts4 RadarChart (semi-circular, `chart.dispose()` commented out).
- `frontend/src/components/trends/TrendsSection.js` — Trends tab fetch flow with `'tempo'` initial fetch.
- `frontend/src/components/trends/FeatureSelect.js` — Hardcoded 7-option dropdown excluding `valence` and `loudness`.
- `frontend/src/components/trends/LineChart.js` — amCharts4 XYChart with two LineSeries.
- `frontend/src/components/trends/features.json` — Static JSON with the `desctiption` (sic) key consumed verbatim.
- `frontend/src/components/about/AboutSection.js` — Static About view.
- `frontend/public/index.html` — Google Fonts `<link>` preconnect hints.

### 5.5.2 Repository Folders Examined

- `/` (root) — Repository root containing `Dockerfile`, `docker-compose.yml`, `app.py`, `README.md`, `requirements.txt`.
- `api/` — Backend Python package (4 modules).
- `frontend/` — React workspace with `package.json`, `src/`, `public/`, `build/`.
- `frontend/src/` — React source root (`App.js`, `index.js`, `components/`, `styles/`).
- `frontend/src/components/` — Subfolder root for `navigation/`, `tracks/`, `trends/`, `about/`.
- `frontend/src/components/navigation/` — 5 navigation primitive files.
- `frontend/src/components/tracks/` — 3 Tracks-tier files.
- `frontend/src/components/trends/` — 4 Trends-tier files including `features.json`.
- `frontend/src/components/about/` — Single `AboutSection.js` file.

### 5.5.3 Technical Specification Sections Cross-Referenced

- `1.2 SYSTEM OVERVIEW` — Project context, primary capabilities, success criteria.
- `2.3 FEATURE RELATIONSHIPS` — Feature dependency graph, integration points, shared components.
- `2.4 IMPLEMENTATION CONSIDERATIONS` — Constraints, performance, scalability, security, maintenance posture.
- `3.4 THIRD-PARTY SERVICES` — External APIs status, monitoring tools status, cloud services status.
- `3.7 STACK INTEGRATION OVERVIEW` — Cross-tier integration diagram and integration-point summary.
- `4.1 SYSTEM WORKFLOWS` — Bootstrap, Tracks, Trends, About workflows plus API-only endpoints.
- `4.2 INTEGRATION WORKFLOWS` — Browser↔Backend, Backend↔DB, External Pipeline, Compose orchestration sequences.
- `4.3 DECISION LOGIC AND VALIDATION RULES` — Date normalization tree, frontend/backend validation rules.
- `4.4 STATE MANAGEMENT` — React state inventory, fetch lifecycle, caching posture.
- `4.5 ERROR HANDLING FLOWS` — Frontend/backend error machines, retry/fallback gaps, container-level recovery.
- `4.6 TIMING AND SLA CONSIDERATIONS` — Performance bounds, codified SLAs, operational cadence.

# 6. SYSTEM COMPONENTS DESIGN

## 6.1 Core Services Architecture

### 6.1.1 Applicability Assessment

**Core Services Architecture is not applicable for this system in the conventional microservices/distributed-systems sense.**

Hot Stuff is implemented as a **two-tier monolithic web application** delivered through a **two-container Docker Compose stack**. Per Section 5.1.1, "a single Flask process hosts both the JSON API surface and the compiled React Single-Page Application (SPA) static assets, while a sibling PostgreSQL 15 container provides durable storage." There are no independently deployable services, no service mesh, no service registry, no inter-service RPC, and no distributed coordination primitives anywhere in the codebase.

This section nevertheless provides a complete treatment of the topic by:

1. Documenting **why** a service-oriented decomposition was deliberately rejected (with reference to ADR-001 in Section 5.3.6).
2. Mapping each requested concern (service boundaries, discovery, load balancing, circuit breakers, retry/fallback, scaling triggers, redundancy, failover) to its actual posture in this codebase — which in nearly every case is "absent by design."
3. Documenting the minimal **two-tier topology** that does exist, including its only inter-tier communication path (Flask → PostgreSQL via the `psycopg2` driver) and its only resilience primitive (Compose `restart: on-failure`).

#### 6.1.1.1 Rationale for the Monolithic Architecture

Section 5.3.1's architecture-style decision matrix explicitly considered and rejected three alternative styles. The drivers behind the monolith selection are:

| Driver | Evidence | Implication for Service Decomposition |
|---|---|---|
| Single bounded context | Section 5.1.1: "exactly one cohesive concern — visualizing Billboard Hot 100 chart history with Spotify-derived audio features" | No natural seams along which to split services |
| Read-heavy public-access workload | All six routes in `api/routes.py` are `GET`; no write paths from the user-facing tier | Distributed coordination cost would not be recovered |
| Solo-maintainer operational model | Footer marker `AUG | 2021`, no CI/CD, no IaC, no orchestrator manifests | A monolith minimizes deployment, observability, and on-call surface |
| Same-origin SPA + API delivery | `static_folder='../frontend/build'`, `static_url_path='/'` in `api/__init__.py` | One process eliminates cross-origin overhead and CORS complexity |

#### 6.1.1.2 Architecture Style Decision Matrix

The styles considered and the disposition of each (reproduced from Section 5.3.1):

| Style Considered | Outcome | Reason |
|---|---|---|
| Two-tier monolith | **Selected** | Simple deploy via `docker compose up`; no inter-service network; same-origin SPA + API |
| Microservices | **Rejected** | No bounded contexts to split; would multiply operations surface |
| Serverless / FaaS | **Rejected** | No cloud SDK present; cold-start would harm chart-render UX |
| Static SPA + BaaS | **Rejected** | Aggregation helpers (`get_weekly_data`, `get_rolling_avg`) require server-side Pandas |

The decision is captured as **ADR-001 (Single-Process SPA + API)** in Section 5.3.6 with status "Accepted" and the revisit trigger "If teams split or independent SPA deploy is required."

#### 6.1.1.3 Two-Tier Topology Reference

```mermaid
flowchart TB
    User([End User Browser])

    subgraph Compose["Docker Compose Host (single network namespace)"]
        subgraph ApiSvc["api service - port 80 to 5000"]
            Flask["Flask 2.0.1 process<br/>app.py + api package<br/>serves SPA + JSON API"]
            Static["frontend/build/<br/>hashed React bundle"]
            Flask -.serves.-> Static
        end
        subgraph PgSvc["postgres service - port 5432 to 5432"]
            DB[("PostgreSQL 15<br/>tracks + yearly_avg")]
        end
        Flask -- "psycopg2 over TCP 5432<br/>postgresql://postgres:postgres@postgres/db" --> DB
    end

    subgraph External["Out-of-Repository Pipeline"]
        Scraper["Billboard scraper +<br/>Spotipy enrichment"]
    end

    User -- "HTTP 80<br/>SPA + /api/*" --> Flask
    Scraper -. "weekly INSERT to tracks<br/>annual rebuild of yearly_avg" .-> DB
```

The dashed line emphasizes that the external pipeline is **out of this repository**; it writes directly to PostgreSQL and does not pass through the `api` container.

---

### 6.1.2 Service Components

For a microservices system this subsection would catalog services, their boundaries, and their inter-service contracts. For the two-tier monolith the analogous catalog is the **three-tier component inventory** of Section 5.1.2 (backend modules, frontend modules, infrastructure modules), all of which run inside one of two containers. The microservices-specific concerns below are addressed by indicating their non-applicability and the file-level evidence supporting that designation.

#### 6.1.2.1 Service Boundaries and Responsibilities

The system has exactly two container-level boundaries, which are **architectural tiers, not independent services**:

| Container | Responsibility | Independently Deployable? | Owns Persistent State? |
|---|---|---|---|
| `api` | Serves SPA static assets and six JSON `GET` routes; performs in-process Pandas aggregation | Yes (rebuild image) | No |
| `postgres` | Provides durable storage for `tracks` and `yearly_avg` | Yes (image swap) | Yes (`./data` bind-mount) |

Within the `api` container, the codebase is organized into four cohesive Python modules whose responsibilities are described in Section 5.1.2:

- **Flask Application Bootstrap** (`api/__init__.py`, `app.py`) — constructs the Flask object, wires `SQLAlchemy`, `Marshmallow`, and `CORS`, and binds to `0.0.0.0:5000`.
- **HTTP Routing Module** (`api/routes.py`) — six route handlers covering the entire API surface.
- **ORM Models and Schemas** (`api/models.py`) — `Tracks`, `YearlyAvg`, `TrackSchema`, `YearlyAvgSchema`.
- **Aggregation Helpers** (`api/funcs.py`) — `get_query_week`, `get_weekly_data`, `get_rolling_avg`.

These modules **share a single Python process and a single SQLAlchemy session**. They are not separately deployable, do not communicate over a network, and have no independent failure domains — i.e., they are not "services" in the architectural sense.

#### 6.1.2.2 Inter-Service Communication Patterns

**Not applicable: no inter-service communication exists.** The only network communication that occurs within this system is a single client-server protocol pair:

| Hop | Protocol | Driver | Evidence |
|---|---|---|---|
| Browser → `api` | HTTP/1.1 with `application/json` | Native `fetch()` | Section 3.7 integration overview; `axios` declared in `frontend/package.json` but never imported |
| `api` → `postgres` | PostgreSQL wire protocol | `psycopg2` 2.9.6 over TCP 5432 | Connection string `postgresql://postgres:postgres@postgres/db` in `api/__init__.py` |

There are **no service-to-service** HTTP, gRPC, GraphQL, message-bus, event-stream, or webhook channels because there are no services to communicate. Per Section 5.1.3, "Read-only routes rely on PostgreSQL's autocommit-equivalent behavior; no explicit `db.session.commit()` or `db.session.rollback()` is invoked."

#### 6.1.2.3 Service Discovery Mechanisms

**Not applicable in the service-mesh sense.** The only "discovery" mechanism present is **Docker Compose's built-in DNS-based service-name resolution**:

- The connection string in `api/__init__.py` references the host `postgres` (the literal service name).
- Compose's default bridge network resolves `postgres` to the `postgres` container's IP address.
- No external service registry (Consul, etcd, ZooKeeper, Eureka), no service mesh control plane (Istio, Linkerd), and no client-side discovery library is present.

Per Section 5.1.3's "Compose internal" pattern: "DNS-based service discovery — the Flask connection string references the host `postgres`, which Compose resolves to the `postgres` service on the same bridge network."

#### 6.1.2.4 Load Balancing Strategy

**Not applicable: no load balancer exists.** The relevant evidence:

| Concern | Status | Evidence |
|---|---|---|
| Replica count for `api` | 1 (no replicas declared) | `docker-compose.yml` has no `deploy.replicas`, no `deploy.mode: replicated` |
| Reverse proxy in stack | Absent | No nginx/HAProxy/Traefik/Envoy service in `docker-compose.yml` |
| Production WSGI server | **Not used** | `Dockerfile` runs `CMD ["python3", "app.py"]` (Flask dev server); `gunicorn==20.1.0` is pinned in `requirements.txt` but never invoked |
| Ingress controller | Absent | Direct port mapping `80:5000` from host to single container |

Per Section 5.4.5, "Flask development server is single-threaded — one in-flight request at a time; not optimized for concurrency." This is captured as **ADR-006 (Flask Dev Server in Production)** in Section 5.3.6 with status "Accepted (provisional)" and revisit trigger "Before any internet-facing production deployment."

#### 6.1.2.5 Circuit Breaker Patterns

**Not applicable: no circuit breaker is configured.** Per Section 4.5.3's "Retry, Fallback, Notification, and Recovery Posture" matrix, the circuit-breaker capability is documented as "Absent — No `pybreaker` or equivalent." The codebase contains no circuit-breaker library, no half-open/open/closed state machine, and no failure-counter middleware. When PostgreSQL is unavailable, every subsequent request raises `psycopg2.OperationalError` and returns Flask's default 500 — there is no fast-fail short-circuit between the Flask handler and the database.

#### 6.1.2.6 Retry and Fallback Mechanisms

**Not applicable: no retry, fallback, or compensation logic exists at any tier.** Per Section 4.5.3:

| Capability | Status | Evidence |
|---|---|---|
| HTTP retry on frontend | Absent | No `axios-retry`, no `p-retry`, no manual retry loop |
| Backend retry on transient DB errors | Absent | No `tenacity`, no `backoff`, no connection retry policy |
| Fallback responses | Absent | No `try/except` in any route handler in `api/routes.py` |
| Frontend error boundary | Absent | No `componentDidCatch`, no `<ErrorBoundary>` wrapper |
| Idempotency keys | Absent | All routes are `GET`; idempotency is structural |

The only "retry-like" behavior in the entire stack is Docker Compose's `restart: on-failure` policy on the `api` service, which restarts the entire container after the Flask process exits non-zero. Recovery for the user is manual: "re-submit the form (via DatePicker or FeatureSelect) or reload the page" (Section 4.5.3).

#### 6.1.2.7 Service Interaction Diagram (Two-Tier Reality)

```mermaid
sequenceDiagram
    autonumber
    participant U as Browser (User)
    participant F as Flask api container<br/>single process, single thread
    participant P as PostgreSQL postgres container

    Note over U,P: Tracks workflow (auto-fired on app load)
    U->>F: GET / (HTTP/1.1)
    F-->>U: 200 index.html (from frontend/build)
    U->>F: fetch /api/week/2021-11-13
    F->>F: get_query_week(date) - Saturday boundary
    F->>P: SELECT * FROM tracks WHERE week=? ORDER BY rank<br/>(SQLAlchemy + psycopg2 over TCP 5432)
    P-->>F: ≤100 rows
    F->>F: tracks_schema.dump() + get_weekly_data()
    F-->>U: 200 JSON {week, songs, averages, avgTempo}
    U->>U: amCharts radar render (no chart.dispose)

    Note over U,P: Trends workflow (on Trends tab activation)
    U->>F: fetch /api/analysis/tempo
    F->>P: SELECT year, tempo FROM yearly_avg
    P-->>F: ~70 rows
    F->>F: yearly_schema.dump() + get_rolling_avg() (5-row rolling)
    F-->>U: 200 JSON [{year, value, rolling_avg}, ...]

    Note over U,P: Failure path (no retry, no circuit breaker)
    U->>F: fetch /api/analysis/<invalid>
    F->>F: getattr(YearlyAvg, feature) raises AttributeError
    F-->>U: 500 (Flask default body, no structured error)
    U->>U: setError(statusText) - manual user retry only
```

---

### 6.1.3 Scalability Design

The system is **not designed for horizontal scaling** and contains no auto-scaling primitives. This subsection documents that posture, the few performance optimizations that *are* present in the code, and the boundaries that bound when the current design will need to change.

#### 6.1.3.1 Horizontal and Vertical Scaling Approach

**Horizontal scaling: not implemented.** Vertical scaling is the only mechanism currently available, and it is bounded by the Flask development server's single-threaded request handling. Per Section 2.4.3:

| Concern | Implication |
|---|---|
| Single-process Flask development server | Concurrent request throughput is limited; horizontal scaling would require switching to gunicorn or another WSGI server |
| No connection pooling configured beyond Flask-SQLAlchemy defaults | Database concurrency limited to default pool size |
| `/api/artist/<name>` `LIKE '%pattern%'` query | Cannot use B-tree indexes; full-table scan as the dataset grows |
| Two-service Compose stack with no orchestration metadata | Production scaling would require migration to Kubernetes, ECS, or an equivalent orchestrator |

The most concrete blocker is the choice of WSGI server: `gunicorn==20.1.0` is pinned in `requirements.txt` but `Dockerfile` invokes `python3 app.py`, which starts Flask's built-in single-threaded development server. To enable even basic worker-based concurrency, the `CMD` would need to be changed to invoke gunicorn (e.g., `gunicorn -w N -b 0.0.0.0:5000 app:app`).

#### 6.1.3.2 Auto-Scaling Triggers and Rules

**Not applicable: no auto-scaling exists.** The relevant absences:

| Auto-Scaling Primitive | Status | Evidence |
|---|---|---|
| Kubernetes HorizontalPodAutoscaler | Absent | No `k8s/`, no Helm chart, no `Chart.yaml`, no manifests |
| ECS / Fargate target tracking | Absent | No AWS SDK, no `task-definition.json` |
| Compose replica scaling | Absent | No `deploy.replicas` in `docker-compose.yml` |
| Metrics-driven triggers | Absent | No `/healthz`, no `/metrics`, no Prometheus client (Section 5.4.1) |
| Custom scaling controller | Absent | No process supervisor beyond Docker daemon |

Without a metrics endpoint or a `/healthz` probe (Section 5.4.1: "no `/healthz`, `/readyz`, or equivalent in `api/routes.py`"), no orchestrator could make a scaling decision even if one were attached.

#### 6.1.3.3 Resource Allocation Strategy

**Not applicable: no resource constraints are declared.** `docker-compose.yml` contains no `mem_limit`, `cpus`, `deploy.resources`, or ulimits on either service. Both containers are subject to the host's defaults. Within the application:

| Resource | Configuration | Default Behavior |
|---|---|---|
| SQLAlchemy connection pool size, overflow, recycle, timeout | Not configured (Section 5.3.3) | Flask-SQLAlchemy defaults apply |
| Python process memory | Unbounded | Limited only by host |
| Container CPU shares | Unbounded | Default CFS shares |
| Database `shared_buffers`, `work_mem`, `max_connections` | Unconfigured | `postgres:15` image defaults |

#### 6.1.3.4 Performance Optimization Techniques

The optimizations actually present in the codebase are modest but deliberate:

| Optimization | Location | Effect |
|---|---|---|
| Pre-aggregation of yearly averages | `YearlyAvg` table (Section 5.3.3) | Reduces `/api/analysis` from a tens-of-thousands-row scan to a ≤~70-row read |
| Hashed asset filenames | `frontend/build/` produced by `react-scripts build` | Long-lived browser caching of bundles via content-hash filenames |
| Layer-cached pip install | `Dockerfile` copies `requirements.txt` before source | Minimizes rebuild time on source-only changes |
| `.dockerignore` excludes `node_modules`, `venv`, `data` | `.dockerignore` | Reduces build-context size |

What is **deliberately absent** (per ADR-004 No Caching Tier in Section 5.3.6):

- No HTTP response cache (no `Cache-Control`, `ETag`, `Last-Modified` headers; no `flask-caching`).
- No in-process LRU (`functools.lru_cache`) on routes or helpers.
- No distributed cache (Redis, Memcached) in `docker-compose.yml`.
- No CDN for static asset delivery.
- No browser-side persistence (`localStorage`, Service Worker).

#### 6.1.3.5 Capacity Planning Guidelines

**No formal capacity plan is codified anywhere in the repository.** Per Section 5.4.5, "**No SLAs are codified anywhere in the repository.**" There are no load-test artifacts, no benchmark results, and no CI performance gates. The performance bounds that *are* observable from the code (per Section 5.4.5 and Section 2.4.2) provide a practical envelope:

| Workflow | Observable Bound | Source |
|---|---|---|
| `/api/week/<week>` | ≤100 rows per response | Billboard Hot 100 has 100 entries by definition |
| `/api/artist/<name>` | Full-table scan | `LOWER(...) LIKE '%pattern%'` cannot use B-tree indexes |
| `/api/analysis/<feature>` | ≤~70 rows | `YearlyAvg` is one row per year (1958–present) |
| Flask dev server | Single-threaded, one in-flight request | `Dockerfile` `CMD ["python3", "app.py"]` |
| amCharts client | Memory grows across tab switches | `chart.dispose()` commented out in `RadarChart.js` and `LineChart.js` |

The only timing-sensitive constraint codified in code is the **chart-week boundary at 10:00 AM Wednesday** inside `get_query_week`, which aligns with Billboard's mid-week chart finalization cadence (Section 5.4.5). The first endpoint expected to require attention as traffic grows is `/api/artist/<name>`; per Section 5.3.4 it "is the most expensive query and would be the first candidate for caching if traffic grew."

#### 6.1.3.6 Scalability Architecture (Current vs. Future-Phase)

```mermaid
flowchart LR
    subgraph Current["Current State - Two-Container Monolith"]
        C1["Single api container<br/>Flask dev server<br/>1 thread, 1 process"]
        C2["Single postgres container<br/>default pool size<br/>no replicas"]
        C1 -- "TCP 5432" --> C2
    end

    subgraph Future["Future-Phase Scaling Path - not implemented"]
        F1["Reverse proxy<br/>nginx or Traefik"]
        F2["api replicas<br/>gunicorn -w N"]
        F3["Tuned SQLAlchemy<br/>pool_size, max_overflow"]
        F4["postgres primary<br/>+ read replica or PgBouncer"]
        F5["Cache tier<br/>Redis or HTTP ETag"]
        F1 --> F2
        F2 --> F3
        F3 --> F4
        F2 -.- F5
    end

    Current -- "Migration trigger:<br/>artist search load,<br/>concurrent users greater than 1,<br/>internet exposure" --> Future
```

The dashed migration arrow lists the conditions documented in Sections 5.3.4, 5.3.6 (ADR-004, ADR-006), and 2.4.3 that would justify a transition out of the current architecture.

---

### 6.1.4 Resilience Patterns

The resilience posture is **deliberately minimal**: a single Compose-level restart policy on the `api` service is the only automated recovery mechanism in the system. This subsection documents what exists and — equally important — what does not, with file-level evidence.

#### 6.1.4.1 Fault Tolerance Mechanisms

The system's only automated fault-tolerance primitive is captured in Section 5.4.6's DR matrix:

| Concern | Implementation | Recovery Time |
|---|---|---|
| `api` container crash | `restart: on-failure` policy in `docker-compose.yml` | Bounded by Docker's default backoff; typically seconds |
| `postgres` container crash | **No** restart policy declared | Manual intervention required |
| Data file corruption on `./data` bind-mount | No backup configured | Unrecoverable without external backup process |
| Host failure | None | Full re-provisioning required |

Notably, there is **no health check** on either container. Per Section 5.4.6's recommended improvements: "Add a `/healthz` endpoint and configure a Compose `healthcheck` block on the `api` service so Docker can detect zombie processes that have not crashed but have stopped serving." Until that is added, the `restart: on-failure` policy only triggers on hard process exit, not on hung-but-running states.

#### 6.1.4.2 Disaster Recovery Procedures

**No disaster recovery procedures are configured.** Per Section 5.4.6, the repository contains "no multi-region, no replica, and no formal backup schedule." Key absences:

| DR Capability | Status | Evidence |
|---|---|---|
| Multi-region deployment | Absent | Single Compose host, no orchestrator manifests |
| Database replicas (streaming or logical) | Absent | Single `postgres:15` container, no replication config |
| Scheduled `pg_dump` | Absent | No cron, systemd timer, or Compose backup service |
| Continuous WAL archiving | Absent | No `archive_command` configured |
| Off-host snapshot of `./data` | Absent | The bind-mount is local-only durability per Section 5.3.3 ("Trivial local durability; not a backup strategy") |
| Point-in-time recovery | Absent | Requires WAL archiving, which is not configured |

#### 6.1.4.3 Data Redundancy Approach

**No data redundancy is configured.** The persistent state is held in a single PostgreSQL instance backed by the `./data` bind-mount on the host filesystem. The data tier has no streaming replication, no logical replication, no read replicas, no SAN, and no clustered storage. The `volumes: data:` declaration at the bottom of `docker-compose.yml` is a top-level Compose volume *name reservation* and does not provide redundancy of any kind — the actual mount used by the `postgres` service is the bind-mount `./data:/data`.

#### 6.1.4.4 Failover Configurations

**Not applicable: no failover targets exist.** There is no standby database, no active/passive pair, no leader election, and no DNS-based failover. The only "failover" semantic in the system is the `api` service's `restart: on-failure` policy, which restarts the same container on the same host — i.e., it is **process recovery**, not failover.

#### 6.1.4.5 Service Degradation Policies

**Not applicable: no graceful degradation is configured.** Per Section 4.5.3, when downstream dependencies fail the failure surface is uniform across all endpoints and uniformly unhelpful:

| Failure Mode | System Response | User Experience |
|---|---|---|
| PostgreSQL unreachable | Every route raises `psycopg2.OperationalError` → Flask default 500 | Frontend `setError(statusText)` |
| Network failure on `fetch()` | Unhandled promise rejection (no `try/catch`) | UI stuck at `isLoaded=false` indefinitely |
| Invalid feature in `/api/analysis/<feature>` | `AttributeError` → 500 | `setError(statusText)` |
| Empty `YearlyAvg` table | `IndexError` on `data[0].keys()` → 500 | `setError(statusText)` |
| Invalid date in `/api/week/<week>` | `psycopg2` parse error → 500 | `setError(statusText)` |

There is **no feature flag system**, **no bulkhead pattern**, **no fallback response cache**, **no maintenance-mode page**, and **no read-only mode** for partial functionality. Per Section 4.5.3: "Recovery for the user is manual: re-submit the form (via DatePicker or FeatureSelect) or reload the page."

#### 6.1.4.6 Per-Endpoint Failure Behavior

The endpoint-level failure matrix (consolidated from Sections 4.5.2 and 5.4.3):

| Endpoint | Failure Class | HTTP Outcome |
|---|---|---|
| `/api/week/<week>` | Invalid date string | 500 |
| `/api/week/<week>` | No matching rows | 200 with empty arrays |
| `/api/track/<id>` | Unknown ID | 200 with `[]` |
| `/api/artist/<name>` | No match | 200 with `[]` |
| `/api/analysis/<feature>` | Invalid feature | 500 (`AttributeError`) |
| `/api/analysis/<feature>` | Empty `YearlyAvg` | 500 (`IndexError`) |

Two endpoints (`/api/track`, `/api/artist`) treat "no result" as a 200 with an empty array; the others propagate exceptions as 500. The frontend reconciles these into one of two display states ("error message" vs. "No Data Found") via the logic in `TracksSection.getData` and `TrendsSection.getData`.

#### 6.1.4.7 Resilience Pattern Implementation Diagram

```mermaid
flowchart TD
    Start([Failure occurs]) --> Class{Failure type?}

    Class -->|Flask process exits non-zero| Restart["Compose restart on-failure<br/>relaunches CMD python3 app.py"]
    Class -->|Flask process hung but running| NoCheck["No healthcheck configured<br/>no automated recovery"]
    Class -->|postgres process exits| NoPolicy["No restart policy on postgres<br/>manual docker compose start"]
    Class -->|Data file corruption| NoBackup["No backup configured<br/>data loss"]
    Class -->|Host failure| NoHA["No HA<br/>full re-provisioning"]
    Class -->|Network error in browser| Stuck["Unhandled promise rejection<br/>UI stuck at isLoaded=false"]
    Class -->|HTTP greater than 299| FrontError["setError statusText<br/>Render h1.error"]
    Class -->|Backend exception| Five["Flask default 500<br/>no structured body"]

    Restart --> Reimport["api package re-imports<br/>routes re-register"]
    Reimport --> Defer{"Defer DB connect<br/>until first request"}
    Defer -->|postgres up| Recovered([Service restored])
    Defer -->|postgres down| FirstReq500["First request raises<br/>OperationalError, returns 500"]
    FirstReq500 --> ManualPg["Manual postgres restart required"]
    ManualPg --> Recovered

    NoCheck --> Manual1[Operator detects + restarts]
    NoPolicy --> Manual1
    NoBackup --> Lost([Data loss])
    NoHA --> Reprov([Re-provision host])
    Stuck --> Reload["User reloads page"]
    FrontError --> Resubmit["User resubmits form"]
    Five --> Resubmit

    Manual1 --> Recovered
    Reload --> Recovered
    Resubmit --> Recovered
```

The diagram makes explicit that **every failure class except pure `api` process exit terminates in a manual recovery step** — operator restart, user reload, or user form resubmission. There is no automated remediation path for hangs, database crashes, data corruption, or transient backend exceptions.

#### 6.1.4.8 Recommended Hardening (Not Implemented)

Per Section 5.4.6, the documented improvement set required for any production deployment includes:

| Improvement | Purpose |
|---|---|
| Add `restart: on-failure` to the `postgres` service | Symmetric process recovery for the data tier |
| Introduce periodic `pg_dump` or streaming replication to an off-host target | Foundational backup / DR posture |
| Externalize database credentials via environment variables | Enable rotation; remove hardcoded `postgres:postgres` from `api/__init__.py` |
| Add a `/healthz` endpoint and a Compose `healthcheck` block on `api` | Detect hung-but-running states; enable orchestrator integration |
| Switch `Dockerfile` `CMD` to `gunicorn` (already in `requirements.txt`) | Multi-worker concurrency; production-grade WSGI |
| Wrap frontend `fetch()` calls in `try/catch` and add an `<ErrorBoundary>` | Prevent indefinite `isLoaded=false` UI states |

---

### 6.1.5 Summary of Non-Applicability

The microservices/distributed-architecture concerns enumerated in this section's prompt map to the actual codebase as follows:

| Prompt Concern | Status in This System | Driving Reason |
|---|---|---|
| Service boundaries and responsibilities | Two-tier boundaries only (`api`, `postgres`) | ADR-001; single bounded context |
| Inter-service communication patterns | None (single Flask↔Postgres link) | No services to interconnect |
| Service discovery mechanisms | Compose DNS only (resolves `postgres`) | No registry needed for one consumer |
| Load balancing strategy | None (single replica, single thread) | ADR-006; bounded traffic |
| Circuit breaker patterns | Absent | No `pybreaker`; no transient-failure category large enough to justify |
| Retry and fallback mechanisms | Absent | Manual user retry is the only recovery |
| Horizontal/vertical scaling | Not implemented | Flask dev server, single replica |
| Auto-scaling triggers and rules | Absent | No metrics, no orchestrator |
| Resource allocation strategy | Host defaults only | No `mem_limit`/`cpus` declared |
| Performance optimization | Pre-aggregated `YearlyAvg`; hashed assets | ADR-002; build-system defaults |
| Capacity planning | Undocumented | No SLAs codified (Section 5.4.5) |
| Fault tolerance | `api` `restart: on-failure` only | Compose-native primitive |
| Disaster recovery procedures | None (bind-mount only) | Solo-maintainer / non-production scope |
| Data redundancy | None | Single PostgreSQL instance |
| Failover configurations | None | No standby database |
| Service degradation policies | None | Uniform 500 on backend failure |

Where this section identifies an absence as a **deliberate decision** (e.g., no caching, no microservices, no auth), the rationale and revisit trigger are recorded in the corresponding ADR in Section 5.3.6. Where the absence is a **known limitation** not yet remediated (e.g., `gunicorn` declared but not invoked, `axios` declared but not imported, `web-vitals` declared but not wired), it is recorded in the discrepancy listings of Sections 2.4.1 and 3.6.

---

### 6.1.6 References

#### Files Examined

- `docker-compose.yml` — Two-service Compose definition; verified absence of `replicas`, `healthcheck`, resource limits, and a restart policy on the `postgres` service.
- `Dockerfile` — Single-stage image build; confirmed `CMD ["python3", "app.py"]` (Flask dev server) rather than `gunicorn`; no `HEALTHCHECK` instruction.
- `app.py` — Trivial entry point; `app.run(host='0.0.0.0')` invocation.
- `requirements.txt` — Pinned Python dependencies; confirmed presence of `gunicorn==20.1.0` (unused) and absence of retry/circuit-breaker libraries (`tenacity`, `backoff`, `pybreaker`, `flask-limiter`, `flask-caching`).
- `.dockerignore` — Build-context exclusions (`frontend/node_modules`, `venv`, `data`).
- `api/__init__.py` — Flask construction; hardcoded connection string `postgresql://postgres:postgres@postgres/db`; permissive `CORS(app)`; no SQLAlchemy pool tuning.
- `api/routes.py` — Six-route API surface; verified absence of `try/except`, retry, and rate-limiting; all endpoints `GET`-only.
- `api/models.py` — `Tracks` and `YearlyAvg` ORM models plus Marshmallow schemas.
- `api/funcs.py` — `get_query_week`, `get_weekly_data`, `get_rolling_avg` aggregation helpers.
- `frontend/package.json` — Frontend dependency manifest; verified `axios` declared but unused, `web-vitals` declared but unwired.
- `README.md` — Project documentation; confirms read-side scope and out-of-repo scraper.

#### Folders Explored

- `/` (root) — Top-level Compose, Dockerfile, app.py, README, requirements.txt, .dockerignore, api/, frontend/.
- `api/` — Backend Flask package (`__init__.py`, `routes.py`, `models.py`, `funcs.py`).
- `frontend/` — Frontend root (`package.json`, `package-lock.json`, `src/`, `public/`, `build/`).
- `frontend/src/` — React source (`App.js`, `index.js`, `components/`, `styles/`).

#### Cross-Referenced Technical Specification Sections

- **Section 2.4 IMPLEMENTATION CONSIDERATIONS** — Technical constraints, performance considerations (2.4.2), scalability considerations (2.4.3), security implications (2.4.4).
- **Section 3.7 STACK INTEGRATION OVERVIEW** — Three integration points (Frontend↔Backend, Backend↔DB, External Pipeline↔DB).
- **Section 4.5 ERROR HANDLING FLOWS** — Frontend error state machine, backend error behaviors, retry/fallback posture, container-level recovery.
- **Section 5.1 HIGH-LEVEL ARCHITECTURE** — Two-tier monolith characterization, component inventory, data flows, external integration points.
- **Section 5.3 TECHNICAL DECISIONS** — Architecture style decision matrix (5.3.1), communication patterns (5.3.2), data storage rationale (5.3.3), caching justification (5.3.4), security mechanism selection (5.3.5), ADRs (5.3.6).
- **Section 5.4 CROSS-CUTTING CONCERNS** — Monitoring/observability (5.4.1), logging (5.4.2), error handling patterns (5.4.3), authN/authZ (5.4.4), performance/SLA posture (5.4.5), disaster recovery (5.4.6).

## 6.2 Database Design

Database Design **is applicable** to this system. The application is the read-side consumer of a single-instance PostgreSQL 15 deployment that persists Billboard Hot 100 chart entries enriched with Spotify audio features. While Section 3.5 (Databases & Storage) and Section 5.3 (Technical Decisions) introduced the technology stack and rationale, this section provides the canonical structural reference for the schema, the indexing posture, the data lifecycle, and the operational characteristics that govern persistent storage.

A defining architectural property of this system is its **strict read-side contract at the application tier**: every route handler in `api/routes.py` is a `GET` issuing read-only queries; no `db.session.commit()`, `db.session.rollback()`, or `INSERT/UPDATE/DELETE` calls exist anywhere in the repository. The write side — schema creation, weekly inserts into `tracks`, and annual aggregation into `yearly_avg` — is owned by an out-of-repository pipeline (Billboard scraper plus Spotipy enrichment). All design choices below should be read in light of that division of responsibility.

### 6.2.1 Schema Design

#### 6.2.1.1 Entity Relationship Overview

The schema consists of exactly **two tables** declared in `api/models.py`: `Tracks` (granular per-week chart entries) and `YearlyAvg` (pre-aggregated annual feature roll-ups). The two tables are **logically related** — `YearlyAvg` rows are derived by averaging `Tracks` rows grouped by year — but **no foreign-key constraint, no SQLAlchemy `relationship()`, no `backref`, and no JOIN** is declared in the ORM. This intentional decoupling reflects ADR-002 (Pre-Aggregated `YearlyAvg`): yearly aggregation is performed once per year by the external pipeline, materialized into `YearlyAvg`, and read independently by `/api/analysis/<feature>` without ever joining back to `Tracks` at request time.

The ERD below uses a dashed conceptual link to indicate the logical (non-enforced, non-materialized at query time) derivation relationship.

```mermaid
erDiagram
    TRACKS ||..o{ YEARLY_AVG : "logically aggregated by year (no FK)"
    TRACKS {
        Integer id PK "surrogate key"
        Date week "Saturday boundary 1958 to present"
        Integer rank "chart position 1 to 100"
        String track "track title"
        String artist "artist name"
        String spotify_id "Spotify track identifier"
        Float tempo "BPM"
        Float energy "audio feature"
        Float danceability "audio feature"
        Float valence "audio feature"
        Float liveness "audio feature"
        Float speechiness "audio feature"
        Float acousticness "audio feature"
        Float instrumentalness "audio feature"
        Float loudness "audio feature"
    }
    YEARLY_AVG {
        Integer index PK "surrogate key"
        String year "year stored as String not Date"
        Float energy "annual mean"
        Float danceability "annual mean"
        Float valence "annual mean"
        Float liveness "annual mean"
        Float speechiness "annual mean"
        Float acousticness "annual mean"
        Float instrumentalness "annual mean"
        Float tempo "annual mean"
    }
```

Two structural asymmetries between the tables are documented as known limitations:

| Asymmetry | Detail | Reference |
|---|---|---|
| `loudness` exists on `Tracks` but not on `YearlyAvg` | The annual roll-up tracks 8 features; the granular table tracks 9 features | `api/models.py` |
| `year` is stored as `String`, not `Integer` or `Date` | Constrains date arithmetic; sorting depends on lexicographic equivalence to numeric ordering | `api/models.py` |

#### 6.2.1.2 Tracks Table Data Model

The `Tracks` table represents one row per `(week, rank)` chart entry. Its column inventory is enumerated below; column types are SQLAlchemy declarative types defined in `api/models.py`.

| Column | SQLAlchemy Type | Role |
|---|---|---|
| `id` | `Integer` | Primary key, surrogate |
| `week` | `Date` | Saturday-boundary chart week |
| `rank` | `Integer` | Chart position 1 to 100 |
| `track` | `String` | Track title text |

| Column | SQLAlchemy Type | Role |
|---|---|---|
| `artist` | `String` | Artist name text |
| `spotify_id` | `String` | Spotify track identifier |
| `tempo` | `Float` | Beats per minute (BPM) |
| `energy` | `Float` | Spotify audio feature |

| Column | SQLAlchemy Type | Role |
|---|---|---|
| `danceability` | `Float` | Spotify audio feature |
| `valence` | `Float` | Spotify audio feature (excluded from frontend dropdown) |
| `liveness` | `Float` | Spotify audio feature |
| `speechiness` | `Float` | Spotify audio feature |

| Column | SQLAlchemy Type | Role |
|---|---|---|
| `acousticness` | `Float` | Spotify audio feature |
| `instrumentalness` | `Float` | Spotify audio feature |
| `loudness` | `Float` | Spotify audio feature (excluded from frontend dropdown) |

**Cardinality and growth profile.** The chart contains ≤100 entries per Saturday × decades of history (the `DatePicker` admits dates between `1958-07-27` and `2021-11-13`). With approximately 67 years × 52 weeks × 100 rows, the steady-state population is on the order of 350,000 rows, growing by ~100 rows per week as the external scraper runs.

**Known constructor discrepancy.** `Tracks.__init__` (lines 21–37 of `api/models.py`) omits `spotify_id` from its parameter list despite the column existing on the table. Programmatic ingestion via the constructor cannot populate `spotify_id`; the external pipeline must use bulk-insert mechanisms (e.g., `pandas.to_sql`, `INSERT ... SELECT`, or direct `psycopg2.execute`) that bypass the constructor.

#### 6.2.1.3 YearlyAvg Table Data Model

The `YearlyAvg` table represents one row per chart year and is the sole source for `/api/analysis/<feature>`. Its column inventory follows.

| Column | SQLAlchemy Type | Role |
|---|---|---|
| `index` | `Integer` | Primary key, surrogate |
| `year` | `String` | Calendar year (string) |
| `energy` | `Float` | Annual mean of `Tracks.energy` |
| `danceability` | `Float` | Annual mean of `Tracks.danceability` |

| Column | SQLAlchemy Type | Role |
|---|---|---|
| `valence` | `Float` | Annual mean of `Tracks.valence` |
| `liveness` | `Float` | Annual mean of `Tracks.liveness` |
| `speechiness` | `Float` | Annual mean of `Tracks.speechiness` |
| `acousticness` | `Float` | Annual mean of `Tracks.acousticness` |

| Column | SQLAlchemy Type | Role |
|---|---|---|
| `instrumentalness` | `Float` | Annual mean of `Tracks.instrumentalness` |
| `tempo` | `Float` | Annual mean of `Tracks.tempo` |

**Cardinality and growth profile.** Approximately 70 rows total (one per chart year). Growth is one row per year and is driven by the external aggregation job, not by request-time computation.

#### 6.2.1.4 Marshmallow Serialization Schemas

Two Marshmallow schemas in `api/models.py` govern the JSON wire format for read responses. They define the projection from ORM rows to the API contract; neither schema is used for deserialization.

| Schema | Source Model | Field Order |
|---|---|---|
| `TrackSchema` | `Tracks` | `id`, `week`, `rank`, `track`, `artist`, `spotify_id`, `energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `loudness`, `tempo` |
| `YearlyAvgSchema` | `YearlyAvg` | `year`, `energy`, `valence`, `liveness`, `speechiness`, `acousticness`, `danceability`, `instrumentalness`, `tempo` |

**Read-only schema contract.** The codebase invokes `dump()` and `dump(..., many=True)` only — there is no `load()` call, no `@validates` decorator, no `@pre_load` or `@post_load` hook. This codifies the read-only application-tier contract at the serialization layer.

#### 6.2.1.5 Indexing Strategy

The repository's index strategy is **minimalist**: only the implicit primary-key indexes on `Tracks.id` and `YearlyAvg.index` exist. No `index=True` flag, no `db.Index(...)`, no `__table_args__` index declarations, and no composite indexes are present in `api/models.py`.

| Table | Index | Type | Coverage |
|---|---|---|---|
| `Tracks` | `tracks_pkey` | B-tree (PK) | `id` |
| `YearlyAvg` | `yearly_avg_pkey` | B-tree (PK) | `index` |

**Query patterns that would benefit from secondary indexes** but currently rely on full or sequential scans:

| Query Pattern | Endpoint | Source | Recommended Index (not implemented) |
|---|---|---|---|
| `WHERE week = $1` | `/api/week/<week>` | `api/routes.py` | B-tree on `Tracks.week` |
| `WHERE spotify_id = $1` | `/api/track/<id>` | `api/routes.py` | B-tree on `Tracks.spotify_id` |
| `WHERE LOWER(artist) LIKE LOWER('%pat%')` | `/api/artist/<name>` | `api/routes.py` | Cannot use B-tree; trigram (`pg_trgm`) GIN candidate |
| `ORDER BY rank` / `ORDER BY week DESC` | Multiple | `api/routes.py` | Composite `(week, rank)` candidate |

The artist-search query intentionally cannot exploit a B-tree index because of its leading-wildcard `LIKE '%...%'` form; performance therefore scales linearly with table size as documented in Section 2.4.3 and Section 5.4.5. The pre-aggregation pattern of `YearlyAvg` (ADR-002) is the system's principal substitute for missing secondary indexes on the analysis path.

#### 6.2.1.6 Constraints Inventory

The ORM declarations contain no constraints beyond the implicit primary keys. Specifically the following are **not** declared:

| Constraint Class | Declared? | Notes |
|---|---|---|
| `PRIMARY KEY` | Yes | `Tracks.id`, `YearlyAvg.index` |
| `FOREIGN KEY` | No | The two tables are physically independent |
| `UNIQUE` | No | No declared natural key on `(week, rank)` or `spotify_id` |
| `NOT NULL` | No | All non-PK columns are nullable |
| `CHECK` | No | No domain checks (e.g., `rank BETWEEN 1 AND 100`) |
| `DEFAULT` | No | No server-side defaults |

The absence of a `(week, rank)` uniqueness constraint on `Tracks` means duplicate weekly entries are not blocked at the database tier and must be prevented by the external pipeline. The absence of `NOT NULL` is consistent with the application's defensive posture (`get_rolling_avg` calls `df.where(pd.notnull(df), None)` to sanitize NaN values to JSON-serializable `null`).

#### 6.2.1.7 Partitioning Approach

**No partitioning is configured.** The `Tracks` and `YearlyAvg` declarations contain no `__table_args__` partition specification, no `PARTITION BY` clause, and no inheritance-based partition setup. Both tables are unpartitioned heap tables.

A future partitioning strategy, if traffic warrants it, would naturally partition `Tracks` by `week` (range partitioning by year, weekly sub-partitions, or quarter ranges). At the current cardinality (≤350,000 rows for the granular table; ~70 rows for the aggregate) partitioning would add operational overhead disproportionate to the benefit.

#### 6.2.1.8 Replication Configuration

**No replication is configured at any level.** The deployment is a single PostgreSQL container instance:

| Replication Mechanism | Status | Notes |
|---|---|---|
| Streaming replication (physical) | Absent | No `primary_conninfo`, no `standby.signal` |
| Logical replication (publication/subscription) | Absent | No `CREATE PUBLICATION`, no replication slots |
| Read replicas | Absent | Only one `postgres` service in `docker-compose.yml` |
| Multi-region failover | Absent | Single-host Compose deployment |
| Synchronous commit topology | N/A | No replicas to be synchronous with |

This posture is aligned with the two-tier monolith architecture described in Section 5.3.1 and the absence of read/write splitting concerns in the application tier (every query is a read against the same instance).

#### 6.2.1.9 Backup Architecture

**No backup is configured in the repository.** The persistence-durability surface is limited to a single host bind-mount declared in `docker-compose.yml`:

| Concern | Configuration | Recovery Posture |
|---|---|---|
| Host bind-mount | `./data:/data` on the `postgres` service | Survives container restarts; not a backup |
| `pg_dump` schedule | Not configured | No periodic logical dumps |
| WAL archiving | Not configured | `archive_command` not set |
| Point-in-time recovery (PITR) | Not configured | No base backups, no WAL archive |
| Off-host snapshot | Not configured | `./data` lives on the same host as the container |
| Object-store backup | Not configured | No S3/GCS/Azure Blob target |

Section 5.3.3 explicitly characterizes the bind-mount as "trivial local durability; not a backup strategy." Section 5.4.6 lists "introduce a periodic `pg_dump` or PostgreSQL streaming replication to an off-host target" as a recommended improvement that has not been implemented. Recovery from `./data` corruption is therefore unavailable through repository-defined mechanisms; recovery would require re-execution of the external scraper pipeline to repopulate both tables from source.

### 6.2.2 Data Management

#### 6.2.2.1 Migration Procedures

**No migration framework is present in this repository.** The dependency manifest (`requirements.txt`) declares neither `alembic` nor `Flask-Migrate`; no `migrations/` directory, no `alembic.ini`, and no `versions/` tree exist anywhere in the project.

Schema creation is the responsibility of the **external write-side pipeline**, which is documented in Section 5.3.3 ("Migration strategy: None in repo — the write-side pipeline owns DDL; the read-side application is a consumer"). Practically, `Tracks` and `YearlyAvg` are pre-populated tables that the application binds to at runtime via the SQLAlchemy declarative base.

| Migration Concern | Disposition |
|---|---|
| Forward migration | External pipeline; not in repo |
| Backward migration / rollback | External pipeline; not in repo |
| Schema version tracking | Not codified — no `alembic_version` table |
| Idempotency | Pipeline-defined; not enforced by this repo |
| DDL drift detection | None |

#### 6.2.2.2 Versioning Strategy

There is **no codified schema-versioning strategy** in this repository. Without Alembic or Flask-Migrate, the application has no mechanism to assert that the database schema matches its expectations at startup; a schema drift (e.g., a renamed column on `Tracks`) would manifest only at first request as a `psycopg2` `UndefinedColumn` error surfacing through Flask's default 500 handler (see Section 5.4.3).

| Versioning Surface | Mechanism |
|---|---|
| ORM model schema | Source-controlled in `api/models.py` |
| Database schema | External pipeline; no version table |
| API contract version | None — no `Accept-Version` header, no `/v1/` URL prefix |
| Marshmallow schema version | None — schemas are mutated in place |

#### 6.2.2.3 Archival Policies

**No archival policy is configured.** The full historical chart corpus from the earliest weekly entry forward is permanently retained in the same `Tracks` table; there is no:

- Cold-storage tier (no second table, no parquet/columnar export, no S3 archive).
- Time-based partition drop (no partitions exist).
- Tiered retention by recency (no `archived_at` column, no soft-delete column).
- Compression of older rows (no `pg_columnar` extension; PostgreSQL's standard TOAST compression applies uniformly).

The decision to retain all historical data uncompressed is driven by the analytical use case: `/api/analysis/<feature>` and `/api/artist/<name>` both rely on access to the full historical span.

#### 6.2.2.4 Data Storage and Retrieval Mechanisms

The application's read-path retrieval is implemented entirely via SQLAlchemy ORM `query` expressions in `api/routes.py`. The four data-bound endpoints map to the following query patterns.

| Endpoint | ORM Expression | Result Bound |
|---|---|---|
| `GET /api/track/<spotify_id>` | `Tracks.query.filter_by(spotify_id=spotify_id).order_by(Tracks.rank).all()` | Variable (≥0 rows) |
| `GET /api/week/<week>` | `Tracks.query.filter_by(week=week).order_by(Tracks.rank).all()` | ≤100 rows |
| `GET /api/artist/<artist>` | `Tracks.query.filter(func.lower(Tracks.artist).like(func.lower(f'%{artist}%'))).order_by(Tracks.week.desc()).all()` | Variable (≥0 rows) |
| `GET /api/analysis/<feature>` | `YearlyAvg.query.with_entities(YearlyAvg.year, getattr(YearlyAvg, feature))` | ~70 rows |

**Storage substrate.** The `postgres` service mounts `./data:/data` from the host; this is the sole persistence surface. The `volumes: data:` declaration in `docker-compose.yml` is a Compose volume *name reservation* and is not the active mount point used by the service. The `.dockerignore` file excludes `/data` from the build context, ensuring that data files are never copied into the image layer.

**Retrieval mechanics.** SQLAlchemy emits parameterized SQL through `psycopg2`. The `with_entities()` projection on `/api/analysis/<feature>` limits the returned column set to `(year, <feature>)` rather than fetching the full 9-column `YearlyAvg` row, reducing wire transfer between the database and the application.

**Data freshness.** New rows enter `Tracks` weekly (per the external Billboard scraper); `YearlyAvg` is updated annually or on full backfill (per the external aggregation job). The application performs no outbound HTTP to Billboard or Spotify and does not refresh data in-process.

#### 6.2.2.5 Caching Policies

The system implements **no caching at any tier**. This is documented as ADR-004 ("No Caching Tier") in Section 5.3.6 with status "Accepted (provisional)." The full caching matrix is reproduced below as it pertains to database access:

| Cache Layer | Implementation |
|---|---|
| Query-result cache (in-process) | Absent — no `functools.lru_cache`, no `@cached_property` on routes |
| Connection-level prepared-statement cache | psycopg2 default (no explicit `prepare_threshold` tuning) |
| HTTP response cache | Absent — no `Cache-Control`, `ETag`, or `Last-Modified` headers set |
| Distributed cache | Absent — no Redis or Memcached service in `docker-compose.yml` |
| Browser persistence | Absent — no `localStorage`, no Service Worker |
| CDN | Absent |

Each request results in a fresh `SELECT` against PostgreSQL and a fresh aggregation pass through `get_weekly_data`, `get_rolling_avg`, or `get_query_week` as applicable. ADR-004's revisit trigger is "if `/api/artist` traffic grows or DB load rises," because the artist-search query is the only handler whose runtime is unbounded by chart-week cardinality.

### 6.2.3 Data Flow Architecture

#### 6.2.3.1 Read Path

The application-tier read path is fully synchronous and traverses six logical layers from the browser to the database and back. No queue, no async workers, no message bus, and no streaming layer is involved.

```mermaid
flowchart LR
    Browser[Browser SPA]
    Routes[api/routes.py<br/>Flask handler]
    ORM[SQLAlchemy 1.4.19<br/>db.session.query]
    Driver[psycopg2 2.9.6<br/>libpq client]
    DB[(PostgreSQL 15<br/>tracks + yearly_avg)]
    Schemas[Marshmallow<br/>TrackSchema / YearlyAvgSchema]
    Helpers[api/funcs.py<br/>Pandas helpers]

    Browser -->|HTTP GET /api/...| Routes
    Routes -->|query expression| ORM
    ORM -->|parameterized SQL| Driver
    Driver -->|TCP 5432| DB
    DB -->|rows| Driver
    Driver -->|tuples| ORM
    ORM -->|model instances| Routes
    Routes -->|dump / dump many=True| Schemas
    Schemas -->|JSON-ready dict| Routes
    Routes -.->|optional| Helpers
    Helpers -.->|aggregated dict| Routes
    Routes -->|flask.jsonify| Browser
```

The optional `Helpers` invocation applies only to `/api/week/<week>` (calls `get_weekly_data`) and `/api/analysis/<feature>` (calls `get_rolling_avg`); `/api/track/<id>` and `/api/artist/<name>` return Marshmallow output directly without further aggregation.

#### 6.2.3.2 Write Path

The write path is **fully external to this repository**. The Flask application performs no inserts, updates, or deletes. The conceptual pipeline that owns the write side is summarized below.

```mermaid
flowchart LR
    subgraph External["External Write Pipeline (out of repo)"]
        Scraper[Billboard.com<br/>Hot 100 scraper]
        SpotifyAPI[Spotify Web API<br/>via Spotipy]
        WeeklyJob[Weekly Ingestion Job]
        AnnualJob[Annual / Backfill<br/>Aggregation Job]
    end

    subgraph DB["postgres container"]
        TracksT[(tracks<br/>granular)]
        YearlyT[(yearly_avg<br/>aggregated)]
    end

    Scraper -->|chart entries| WeeklyJob
    SpotifyAPI -->|audio features| WeeklyJob
    WeeklyJob -->|INSERT batch| TracksT
    TracksT -->|SELECT GROUP BY year| AnnualJob
    AnnualJob -->|INSERT or UPSERT| YearlyT
```

**Write cadence:**

| Operation | Cadence | Volume |
|---|---|---|
| `INSERT INTO tracks` | Weekly | ~100 rows per run |
| `INSERT/UPDATE INTO yearly_avg` | Annually or on backfill | 1 row per year per run |
| Schema migration | On schema change (manual) | DDL only |

#### 6.2.3.3 End-to-End Combined Data Flow

Combining the read and write paths, the end-to-end flow shows the clean separation between the in-repo read-side and the out-of-repo write-side, with no caching or queuing layer between them.

```mermaid
flowchart TB
    subgraph Client["Client Tier"]
        UI[React SPA]
    end

    subgraph App["Application Tier (in repo)"]
        Flask[Flask + SQLAlchemy<br/>read-only handlers]
    end

    subgraph Data["Data Tier"]
        PG[(PostgreSQL 15<br/>tracks, yearly_avg)]
        Mount[(./data bind-mount)]
    end

    subgraph Pipeline["External Write Pipeline (out of repo)"]
        BB[Billboard scraper]
        SP[Spotipy enrichment]
        AGG[Yearly aggregator]
    end

    UI -->|GET /api/...| Flask
    Flask -->|SELECT| PG
    PG -->|rows| Flask
    Flask -->|JSON| UI

    BB --> SP
    SP -->|weekly INSERT| PG
    AGG -->|annual INSERT| PG
    PG -.->|persistence| Mount

    classDef external fill:#fff5e6,stroke:#cc9900,stroke-dasharray: 4 2;
    class Pipeline,BB,SP,AGG external
```

### 6.2.4 Compliance Considerations

#### 6.2.4.1 Data Retention Rules

**No formal retention rules are codified.** All chart entries and yearly aggregates are retained indefinitely; no `purge`, `truncate`, `DELETE`, or row-rotation logic exists in the repository. Because the dataset comprises only public-domain chart positions and Spotify-derived audio features (no personal data, no user-generated content), there is no statutory retention obligation against which to measure compliance.

| Data Class | Retention | Justification |
|---|---|---|
| `Tracks` rows (1958 → present) | Indefinite | Required for `/api/artist` historical search |
| `YearlyAvg` rows | Indefinite | Required for `/api/analysis` longitudinal trend |
| Application logs (Flask default stdout) | Container lifetime | No persistence configured |
| Database server logs | Container lifetime | No log shipping configured |

#### 6.2.4.2 Backup and Fault Tolerance Policies

The fault-tolerance posture at the data tier is summarized below; the absence of backups is the dominant exposure.

| Policy Surface | Status | Reference |
|---|---|---|
| Backup schedule | Not configured | Section 5.4.6 |
| Restore procedure | Not codified | Section 5.4.6 |
| Recovery Time Objective (RTO) | Not declared | Section 5.4.5 |
| Recovery Point Objective (RPO) | Not declared | Section 5.4.5 |
| `postgres` restart policy | **Not declared** in `docker-compose.yml` — manual intervention required on crash | Section 5.4.6 |
| `api` restart policy | `restart: on-failure` | Section 5.2.9 |
| Health check on `postgres` service | Not configured | Section 5.4.1 |

The asymmetry in restart policies is operationally significant: a `postgres` container exit (e.g., from an OOM-kill) requires a human operator to issue `docker compose up -d postgres`; the `api` container will continue to attempt connections and return 500s in the meantime (see Section 5.4.6's recovery flow).

#### 6.2.4.3 Privacy Controls

The system handles **no personal data** and therefore implements no privacy controls beyond the absence of collection itself.

| Privacy Concern | Disposition |
|---|---|
| Personal Identifiable Information (PII) | None collected or stored |
| User accounts | None — no sign-up, no login, no profile |
| Cookies | None set |
| Tracking pixels / analytics | None |
| GDPR / CCPA cookie banner | Not required (no cookies) |
| Right-to-erasure workflow | Not required (no personal data) |
| Data Processor Agreement scope | Not applicable |
| Cross-border data transfer concerns | None — data is public-domain Billboard + Spotify-derived |

This posture aligns with Section 5.4.4: "No personal data is collected; no user accounts or sign-up flows exist."

#### 6.2.4.4 Audit Mechanisms

**No database-level audit mechanism is configured.** The repository does not enable PostgreSQL's built-in audit facilities or layer any audit framework on top:

| Audit Surface | Status |
|---|---|
| `pgaudit` extension | Not enabled |
| Per-table change-tracking triggers | Not declared |
| `audit_log` table | Does not exist |
| Application-level audit decorator | Not implemented |
| Read-access logging | Limited to Flask default request logging (Werkzeug) on stdout |
| `log_statement = 'all'` in postgresql.conf | Not configured (image default applies) |

The single observable audit trail is Flask's default per-request log line on stdout, which records HTTP method, path, status code, and timestamp; it does not record query parameters bound to SQL or the rows returned. This is consistent with the public-read profile of the dataset (Section 5.4.4).

#### 6.2.4.5 Access Controls

The access-control posture spans two layers — database role-level and application-route-level — and is intentionally minimal at both.

**Database tier:**

| Control | Configuration |
|---|---|
| Role | Single `postgres` superuser (image default) |
| Password | `postgres` (hardcoded in `docker-compose.yml` and `api/__init__.py`) |
| Network exposure | `5432:5432` published to host |
| Row-level security (RLS) | Not enabled |
| Per-table `GRANT`/`REVOKE` | Not configured (superuser bypasses ACLs) |
| TLS for client connections | Not enabled (`sslmode` not set) |

**Application tier:**

| Control | Configuration |
|---|---|
| Authentication on routes | None |
| Authorization on routes | None |
| Rate limiting | None (`flask-limiter` not installed) |
| CORS allow-list | Permissive (`CORS(app)` with no origin filter) |
| Input validation on path parameters | None — `getattr(YearlyAvg, feature)` accepts arbitrary attribute names |

Section 2.4.4 documents the hardcoded credentials and exposed `5432:5432` port as known limitations: "Convenient for development; should be removed in production." Production hardening would require, at minimum, separating an application-scoped read-only role from the superuser, removing the host port mapping, externalizing credentials to environment variables, and enabling TLS termination at the database listener or upstream proxy.

### 6.2.5 Performance Optimization

#### 6.2.5.1 Query Optimization Patterns

The dominant optimization in the system is the **pre-aggregation pattern** captured in ADR-002: `YearlyAvg` is materialized once per year by the external pipeline so that `/api/analysis/<feature>` can serve trend queries from ~70 rows rather than scanning hundreds of thousands of `Tracks` rows. This reduces analysis-query cost from O(years × ~5,200) to O(years).

| Optimization | Mechanism | Source |
|---|---|---|
| Pre-aggregation | `YearlyAvg` materialized table | ADR-002, Section 5.3.3 |
| Column projection | `Tracks.query.with_entities(...)` on `/api/analysis` | `api/routes.py` |
| Parameterized SQL | Native SQLAlchemy `filter_by` / `filter` | `api/routes.py` |
| Result-set bounding | Logical limits per endpoint (≤100 weekly, ≤~70 yearly) | `api/routes.py` |

**Known anti-patterns** that limit query performance and represent the primary tuning candidates:

| Anti-Pattern | Endpoint | Impact |
|---|---|---|
| `LOWER(...) LIKE '%pat%'` (leading wildcard) | `/api/artist/<name>` | Cannot use B-tree index; full-table scan |
| No secondary index on `Tracks.week` | `/api/week/<week>` | Sequential scan scales with table growth |
| No secondary index on `Tracks.spotify_id` | `/api/track/<id>` | Sequential scan scales with table growth |
| No input validation on `getattr(YearlyAvg, feature)` | `/api/analysis/<feature>` | Invalid feature → `AttributeError` → 500 |
| No `.first()` / `.limit()` on cardinality-bounded queries | All | Always materializes full result list |

#### 6.2.5.2 Caching Strategy

There is **no caching strategy** at the data tier (see Section 6.2.2.5). Every request originates a fresh `SELECT`. The architectural rationale is captured in ADR-004:

- `/api/week` returns ≤100 rows — payload is small enough to make caching's marginal benefit modest.
- `/api/analysis` returns ≤~70 rows — same.
- The dataset itself updates only weekly; in principle a cache TTL of one day would yield near-zero staleness, but no operator has codified that constraint.
- The artist-search endpoint is the strongest cache candidate (full-table scan on every call), but its result set is unbounded and parameterized over user-supplied free text, which complicates cache-key design.

#### 6.2.5.3 Connection Pooling

Connection pooling relies entirely on **Flask-SQLAlchemy's default configuration**. None of the four tunable parameters are set in `api/__init__.py`:

| Parameter | Set? | Effective Value |
|---|---|---|
| `SQLALCHEMY_POOL_SIZE` | No | Flask-SQLAlchemy default |
| `SQLALCHEMY_MAX_OVERFLOW` | No | Flask-SQLAlchemy default |
| `SQLALCHEMY_POOL_RECYCLE` | No | Flask-SQLAlchemy default |
| `SQLALCHEMY_POOL_TIMEOUT` | No | Flask-SQLAlchemy default |

Only two SQLAlchemy-related configuration items are explicitly set:

1. `SQLALCHEMY_DATABASE_URI` = `postgresql://postgres:postgres@postgres/db`
2. `SQLALCHEMY_TRACK_MODIFICATIONS` = `False`

Because the production launcher is `python3 app.py` (the Flask development server, single-threaded), connection-pool tuning would have negligible impact: there is at most one in-flight request at a time, and therefore at most one borrowed connection at any moment. Connection-pool tuning becomes meaningful only after migrating to a multi-worker WSGI server (e.g., gunicorn, which is already pinned in `requirements.txt` but unused).

#### 6.2.5.4 Read/Write Splitting

Read/write splitting is **not applicable** to this system in two complementary senses:

1. **The application performs no writes.** All six route handlers in `api/routes.py` are `GET`-only and read-only. There is therefore no write traffic at the application tier to split.
2. **There are no replicas.** The deployment is a single PostgreSQL instance; there is no read replica to direct read traffic toward.

Should the system later acquire either a write workload (e.g., user comments, ratings) or a streaming replica (e.g., for analytical isolation), read/write splitting could be introduced via SQLAlchemy's `binds` mechanism. None of that infrastructure is present today.

#### 6.2.5.5 Batch Processing Approach

The application tier performs **no batch operations**. Every query returns a single bounded result set processed in-memory by Pandas helpers (`get_weekly_data` on ≤100 rows, `get_rolling_avg` on ~70 rows, `get_query_week` on a single date input). There is no `executemany`, no `COPY`, no bulk-loader, and no chunked iteration.

External pipeline batch operations (out-of-repo, included for completeness):

| Operation | Mechanism | Volume |
|---|---|---|
| Weekly chart ingestion | Bulk `INSERT` (mechanism not in repo) | ~100 rows |
| Yearly aggregation refresh | `INSERT ... SELECT GROUP BY year` (or equivalent) | 1 row per year |
| Backfill | One-shot rebuild (mechanism not in repo) | Full table |

### 6.2.6 Replication and Durability Architecture

The diagram below depicts the actual deployed topology alongside the durability and replication mechanisms that are **not** implemented. Items shown with dashed borders / dashed edges are explicitly absent from the repository and would be required for any production-grade deployment.

```mermaid
flowchart TB
    subgraph Host["Single Docker Host"]
        subgraph Compose["docker-compose stack"]
            APP[api container<br/>restart: on-failure]
            PG[(postgres:15<br/>no restart policy)]
        end
        BindMount[(./data<br/>host bind-mount)]
    end

    APP -->|TCP 5432<br/>psycopg2 wire| PG
    PG -->|local fs writes| BindMount

    subgraph NotImpl["Not Implemented in Repo"]
        Standby[(Streaming Replica<br/>standby)]
        WAL[(WAL Archive<br/>archive_command)]
        OffHost[(Off-host Backup<br/>pg_dump or snapshot)]
        Health[Healthcheck<br/>/healthz]
    end

    PG -.->|no walsender| Standby
    PG -.->|no archive_command| WAL
    PG -.->|no pg_dump cron| OffHost
    APP -.->|no readiness probe| Health

    classDef absent stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class Standby,WAL,OffHost,Health,NotImpl absent
```

**Durability summary:**

| Layer | Mechanism Present | Risk Profile |
|---|---|---|
| Container restart | `api` only (`on-failure`) | `postgres` crash requires manual recovery |
| Local filesystem persistence | `./data` bind-mount | Survives container restart; not host failure |
| Off-host durability | None | Host loss = total data loss (recoverable only via external pipeline re-run) |
| In-flight transaction durability | PostgreSQL fsync defaults from `postgres:15` image | No `synchronous_commit` tuning |

### 6.2.7 Summary of Database Design Posture

The database design is intentionally minimalist and tightly scoped to a public, read-only dataset served by a single-host Compose deployment. The design strengths are the clean separation between the in-repo read-side and the out-of-repo write-side, the materialization of `YearlyAvg` to keep analysis queries cheap, and the read-only application contract that eliminates entire classes of transactional bugs (no commit/rollback paths means no commit/rollback bugs). The design weaknesses — absence of secondary indexes, absence of backups, absence of replication, hardcoded credentials, no migration framework, no audit trail, no caching — are all consequences of the same minimalism and are documented as known limitations across Sections 2.4, 5.3, and 5.4. The next maturation step for any production-bound deployment is the introduction of (in priority order): scheduled `pg_dump` to off-host storage, a `restart: on-failure` policy on the `postgres` service, externalized credentials, secondary indexes on `Tracks.week` and `Tracks.spotify_id`, and a `pg_trgm` GIN index to rescue `/api/artist`.

### 6.2.8 References

#### Files Examined

- `api/__init__.py` — Flask application bootstrap; SQLAlchemy `db` instance; hardcoded `SQLALCHEMY_DATABASE_URI`; `SQLALCHEMY_TRACK_MODIFICATIONS = False`; absence of pool tuning.
- `api/models.py` — Declarative ORM definitions for `Tracks` and `YearlyAvg`; `TrackSchema` and `YearlyAvgSchema` Marshmallow schemas; column inventory; constructor signatures (including the `spotify_id` omission); absence of indexes, FKs, and constraints beyond primary keys.
- `api/routes.py` — All six `GET` route handlers; query patterns including `filter_by`, `filter(... LIKE ...)`, `with_entities`, `order_by`; absence of write operations; absence of `try/except` blocks.
- `api/funcs.py` — `get_query_week` (Saturday-boundary normalization), `get_weekly_data` (per-feature averaging), `get_rolling_avg` (5-row Pandas rolling window with NaN sanitization).
- `app.py` — Trivial entry point invoking `app.run(host='0.0.0.0')`.
- `docker-compose.yml` — Two-service Compose definition (`api`, `postgres`); `postgres:15` image; `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` environment variables; `5432:5432` host port mapping; `./data:/data` bind-mount; `restart: on-failure` on `api` only.
- `Dockerfile` — `python:3.11-slim-buster` base image; `libpq-dev` and `gcc` for `psycopg2` compilation; `pip3 install -r requirements.txt`; `CMD ["python3", "app.py"]`.
- `requirements.txt` — Pinned versions: SQLAlchemy 1.4.19, Flask-SQLAlchemy 2.5.1, psycopg2 2.9.6, psycopg2-binary 2.9.5, marshmallow 3.12.1, flask-marshmallow 0.14.0, marshmallow-sqlalchemy 0.26.1; absence of Alembic and Flask-Migrate.
- `.dockerignore` — Excludes `frontend/node_modules`, `venv`, `data` from the build context.
- `README.md` — Project description, references to external Billboard scraper and Spotipy enrichment pipeline.

#### Folders Examined

- `/` (repository root) — Top-level Compose, Dockerfile, application entry point, requirements, README.
- `/api/` — Backend Flask package containing bootstrap, routes, models/schemas, and aggregation helpers.

#### Cross-Referenced Technical Specification Sections

- Section 1.2 SYSTEM OVERVIEW — Project context and table cardinality bounds.
- Section 2.4 IMPLEMENTATION CONSIDERATIONS — Hardcoded credentials, performance constraints, scalability limits, security implications.
- Section 3.5 DATABASES & STORAGE — PostgreSQL 15 details, ORM stack, driver versions, serialization layer, caching absence, connection-pool defaults.
- Section 4.4 STATE MANAGEMENT — Persistence and transaction-boundary inventory, caching posture.
- Section 5.2 COMPONENT DETAILS — Component breakdown including Persistence Models and Schemas (5.2.3) and Aggregation Helper Module (5.2.4).
- Section 5.3 TECHNICAL DECISIONS — Data storage solution rationale, caching justification, security mechanism selection, ADR-002 (Pre-Aggregated `YearlyAvg`), ADR-004 (No Caching Tier).
- Section 5.4 CROSS-CUTTING CONCERNS — Logging strategy, error-handling matrix, authentication/authorization absence, performance characteristics, disaster recovery procedures.
- Section 6.1 Core Services Architecture — Two-tier monolith characterization (referenced for replication/sharding non-applicability).

## 6.3 Integration Architecture

### 6.3.1 Applicability Assessment

**Integration Architecture is applicable for this system, but at a deliberately minimal scope.** Hot Stuff is a two-tier monolithic web application — per Section 6.1.1, "Core Services Architecture is not applicable for this system in the conventional microservices/distributed-systems sense" — yet it nevertheless exposes a well-defined client-server contract, integrates with a single in-stack data tier, and depends on two clearly identified out-of-repository pipelines. This section catalogs every integration point that exists, documents the requested concerns that are non-applicable with file-level evidence, and records the integration contracts on which the application's correctness depends.

#### 6.3.1.1 Integration Surface Inventory

The complete integration surface consists of the four interaction pairs enumerated in Section 4.2 plus one runtime browser-loaded asset:

| Integration Pair | Direction | Protocol | Implementation Status |
|---|---|---|---|
| Browser → Flask `api` | Synchronous request/response | HTTP/1.1 + JSON | Implemented (six routes in `api/routes.py`) |
| Flask `api` → PostgreSQL | Synchronous query | PostgreSQL wire over `psycopg2` | Implemented (`api/__init__.py`, `api/models.py`) |
| External Pipeline → PostgreSQL | Batch INSERT (weekly/yearly) | PostgreSQL wire | **Out of repository**; contract-only |
| Docker Compose → both containers | Orchestration / DNS resolution | Compose bridge network | Implemented (`docker-compose.yml`) |
| Browser → Google Fonts CDN | Stylesheet load on page bootstrap | HTTPS preconnect + `<link rel="stylesheet">` | Implemented (`frontend/public/index.html` lines 7–10) |

#### 6.3.1.2 Top-Level Integration Topology

```mermaid
flowchart LR
    User([End-User Browser])
    Fonts["fonts.googleapis.com<br/>fonts.gstatic.com<br/>(Jost typeface)"]

    subgraph Compose["Docker Compose Stack (single bridge network)"]
        Flask["api container<br/>Flask 2.0.1 + Flask-Cors 3.0.10<br/>port 80 → 5000"]
        Static["frontend/build/<br/>(SPA static assets)"]
        DB[("postgres container<br/>PostgreSQL 15<br/>port 5432")]
        Flask -.serves.-> Static
        Flask -- "psycopg2 2.9.6 over TCP 5432<br/>postgresql://postgres:postgres@postgres/db" --> DB
    end

    subgraph External["Out-of-Repository Pipeline"]
        Scraper["Billboard scraper +<br/>Spotipy enrichment<br/>(weekly job)"]
    end

    User -- "HTTP/1.1 GET<br/>SPA + /api/*" --> Flask
    User -. "preconnect + stylesheet<br/>display=swap" .-> Fonts
    Scraper -. "INSERT INTO tracks (~100 rows/week)<br/>REBUILD yearly_avg (annual)" .-> DB
```

The dashed lines mark connections that are either out of the application's runtime control (the external pipeline) or that bypass the Flask process entirely (the browser's direct fetch of Google Fonts). The solid lines mark the synchronous request paths that the application is responsible for serving.

#### 6.3.1.3 What This Section Does **Not** Cover

The "Required Diagrams" prompt requests integration flow, API architecture, and message flow diagrams. The first two are populated below with concrete designs. The "message flow" diagram is included specifically to make explicit the **absence** of asynchronous messaging infrastructure, because the system has none (Section 6.3.4). The following concerns are documented as non-applicable with file-level evidence rather than fabricated:

- Authentication / Authorization frameworks (Section 6.3.2.4 / 6.3.2.5)
- Rate limiting and API versioning (Section 6.3.2.6 / 6.3.2.7)
- Event processing, message queues, and stream processing (Section 6.3.4.1 / 6.3.4.2 / 6.3.4.3)
- API gateway and legacy system interfaces (Section 6.3.5.4 / 6.3.5.3)

---

### 6.3.2 API Design

#### 6.3.2.1 Protocol Specifications

The Flask `api` service exposes a **single HTTP/1.1 protocol surface** with `application/json` responses for the API namespace and a static SPA bundle on the root path. Per Section 4.2.1, the same Flask process serves both the SPA and the API surface on the same origin in production via the configuration `static_folder='../frontend/build'`, `static_url_path='/'` in `api/__init__.py`.

| Aspect | Specification | Source |
|---|---|---|
| Transport | HTTP/1.1 plaintext | `app.run(host='0.0.0.0')` in `app.py`; no TLS layer |
| Container port | 5000 (Flask) | `Dockerfile` `EXPOSE 5000` |
| Host port | 80 | `docker-compose.yml` line 11: `"80:5000"` |
| Verb scope | `GET`-only across all routes | `api/routes.py` — every `@app.route` decorator |
| Request body | None (parameters embedded in path) | All routes use URL path variables |
| Response body | `application/json` (set by `flask.jsonify`) | All handlers return `jsonify(...)` |
| Content-Type validation | None | Server does not enforce client `Content-Type` |

The `gunicorn==20.1.0` dependency is pinned in `requirements.txt` but is **never invoked**; the production launcher remains the Flask development server (`Dockerfile` `CMD ["python3", "app.py"]`). This is recorded as ADR-006 (Flask Dev Server in Production) in Section 5.3.6 with revisit trigger "Before any internet-facing production deployment."

#### 6.3.2.2 Complete API Surface

The entire API surface — six endpoints, all `GET` — is implemented in `api/routes.py`. The frontend documents these endpoints redundantly in `README.md` (lines 19–24) and in `frontend/src/components/about/AboutSection.js` (lines 69–86); both inventories are consistent with the implementation except for the rolling-window discrepancy noted in Section 6.3.2.7.

| Endpoint | Handler | Backing Logic |
|---|---|---|
| `GET /` | `index()` | `app.send_static_file('index.html')` from `../frontend/build` |
| `GET /api/` | `home()` | `redirect(f'week/{currentWeek}')` (HTTP 302) |
| `GET /api/track/<spotify_id>` | `get_track_by_id` | `Tracks.query.filter_by(spotify_id=...).order_by(Tracks.rank).all()` |
| `GET /api/week/<week>` | `get_tracks_by_week` | `get_query_week()` + `Tracks.query.filter_by(week=...)` + `get_weekly_data()` |
| `GET /api/artist/<artist>` | `get_tracks_by_artist` | `Tracks.query.filter(func.lower(Tracks.artist).like(func.lower('%...%')))` |
| `GET /api/analysis/<feature>` | `get_avg_feature` | `YearlyAvg.query.with_entities(YearlyAvg.year, getattr(YearlyAvg, feature))` + `get_rolling_avg()` |

Two response semantics deserve note for integrators consuming these endpoints:

- `/api/track/<id>` and `/api/artist/<name>` return **200 with an empty array** when no rows match.
- `/api/week/<week>` and `/api/analysis/<feature>` propagate exceptions on bad inputs as **Flask default 500** (no structured error body). The full failure matrix is in Section 6.1.4.6.

#### 6.3.2.3 API Architecture Diagram

```mermaid
flowchart TB
    Client["Browser<br/>native fetch()"]
    Router{"Flask Router<br/>api/routes.py"}

    Client -->|"HTTP/1.1 GET"| Router

    Router -->|"GET /"| H0["index()<br/>send_static_file('index.html')"]
    Router -->|"GET /api/"| H1["home()<br/>302 redirect to /api/week/{currentWeek}"]
    Router -->|"GET /api/track/&lt;spotify_id&gt;"| H2["get_track_by_id"]
    Router -->|"GET /api/week/&lt;week&gt;"| H3["get_tracks_by_week"]
    Router -->|"GET /api/artist/&lt;artist&gt;"| H4["get_tracks_by_artist"]
    Router -->|"GET /api/analysis/&lt;feature&gt;"| H5["get_avg_feature"]

    H0 -.serves.-> SPA["frontend/build/<br/>index.html + bundle"]

    H2 --> ORM[("SQLAlchemy ORM<br/>Tracks model")]
    H3 --> ORM
    H4 --> ORM
    H5 --> ORM2[("SQLAlchemy ORM<br/>YearlyAvg model")]

    ORM --> Helper["api/funcs.py<br/>get_weekly_data"]
    ORM2 --> Helper2["api/funcs.py<br/>get_rolling_avg"]

    Helper --> Schema["Marshmallow<br/>tracks_schema.dump"]
    Helper2 --> Schema2["Marshmallow<br/>yearly_schema.dump"]

    Schema --> Resp["jsonify()<br/>application/json"]
    Schema2 --> Resp

    Resp --> Client
```

#### 6.3.2.4 Authentication Methods

**No authentication mechanism exists.** Per Section 3.4.3, this is an explicit non-goal for a public-read use case. The absences verified by repository inspection are:

| Mechanism | Status |
|---|---|
| OAuth / OIDC client | Not present (no `authlib`, no `flask-oauthlib`, no client config) |
| Session middleware | Not present (no `Flask-Login`, no `Flask-Session`) |
| JWT issuance / verification | Not present (no `pyjwt`, no `flask-jwt-extended`) |
| Login / logout routes | Not present in `api/routes.py` |
| API keys or bearer tokens | Not required by any route |
| Cookies | Not set by any handler |

Section 5.3.5 records the decision: "Authentication: None — Public-read dataset; explicit non-goal." Section 5.4.4 confirms the same posture from the cross-cutting perspective.

#### 6.3.2.5 Authorization Framework

**No authorization framework exists.** Every route is publicly accessible. Per Section 5.3.5: "Authorization: None — No state-changing endpoints exist." The verified absences:

| Mechanism | Status |
|---|---|
| `@login_required` / `@roles_required` decorators | Not used |
| Role-based access control (RBAC) | Not configured |
| Attribute-based access control (ABAC) | Not configured |
| CSRF protection | Not configured (acceptable because there are no state-changing endpoints) |
| Per-route permission checks | Not present |

The CSRF non-applicability is structural: with no `POST`/`PUT`/`PATCH`/`DELETE` routes, there is no state-mutation surface for CSRF to attack.

#### 6.3.2.6 Rate Limiting Strategy

**No rate limiting is configured.** Verified absences:

| Capability | Status | Evidence |
|---|---|---|
| `flask-limiter` | Not installed | Absent from `requirements.txt` |
| Reverse-proxy rate limit (nginx `limit_req`, etc.) | Not present | No reverse proxy in `docker-compose.yml` |
| Application-level token bucket / leaky bucket | Not implemented | No middleware wrapping route handlers |
| `MAX_CONTENT_LENGTH` body size cap | Not set | No Flask config keys assigned beyond DB URI and `SQLALCHEMY_TRACK_MODIFICATIONS` |
| Per-route timeout | Not configured | Flask `@app.route` decorators have no timeout parameter |

The system relies on the bounded result-set sizes (≤100 rows for `/api/week`, ≤~70 rows for `/api/analysis`) and the Flask development server's single-threaded request handling as natural — but unintentional — throughput limiters. Per Section 6.1.2.5, no circuit breaker exists either.

#### 6.3.2.7 Versioning Approach

**No API versioning is codified.** The verified absences:

| Versioning Strategy | Status |
|---|---|
| URL prefix (`/v1/`, `/v2/`) | Not used; routes live directly under `/api/` |
| `Accept-Version` / `X-API-Version` header negotiation | Not implemented |
| Custom media type versioning (`application/vnd.hot-stuff.v1+json`) | Not implemented |
| Marshmallow schema versioning | Schemas in `api/models.py` are mutated in place |

Per Section 6.2.2.2 (Database Design), the schema migration story is also absent: "no Alembic, no Flask-Migrate." Any breaking change to the API contract would require a coordinated update to the SPA build that ships from the same container — so versioning is structurally unnecessary at the current single-deployable-unit posture.

#### 6.3.2.8 Documentation Standards

**Informal documentation only; no OpenAPI/Swagger.** The endpoints are documented in two human-readable surfaces:

| Source | Content | Discrepancy |
|---|---|---|
| `README.md` lines 19–24 | Plain-markdown enumeration of the five `/api/*` endpoints | Line 24 says "3 year rolling average" but `api/funcs.py` line 32 implements `df[feature].rolling(5).mean()` (5-row window) |
| `frontend/src/components/about/AboutSection.js` lines 69–86 | JSX list of endpoints rendered in the About tab | Line 84 echoes the same "3 year rolling average" inaccuracy |

Verified absences in the documentation toolchain:

- No `flask-restx`, no `flasgger`, no `apispec` in `requirements.txt`.
- No `openapi.yaml`, no `openapi.json`, no `swagger.json` in the repository.
- No Sphinx, no MkDocs, no Redoc configuration.
- No request/response example fixtures committed.

#### 6.3.2.9 CORS Configuration

CORS is registered globally with permissive defaults via `Flask-Cors 3.0.10` in `api/__init__.py` line 9: `CORS(app)`. The implications, per Section 5.3.5, are:

- In **production**, the Flask process serves both the SPA (from `frontend/build/`) and the API on the same origin (port 80 → 5000), so CORS is not strictly required. It is registered as defense-in-depth.
- In **development**, the Create-React-App development server runs on port 3000 and proxies `/api/*` to `http://localhost:5000` via the single declaration `"proxy": "http://localhost:5000"` in `frontend/package.json` line 44. This proxy is a **build-tool dev-server affordance, not a production gateway** (Section 6.3.5.4).
- No `origins` allow-list, no `allow_headers` restriction, no `expose_headers` configuration, and no `supports_credentials` flag is passed to `CORS()`.

---

### 6.3.3 Message Processing

#### 6.3.3.1 Applicability Assessment

**The system has no message-processing infrastructure of any kind.** All inter-component communication is synchronous request/response. Per Section 6.1.2.2: "There are **no service-to-service** HTTP, gRPC, GraphQL, message-bus, event-stream, or webhook channels because there are no services to communicate." The four message-processing concerns enumerated in the section prompt — event processing patterns, message queue architecture, stream processing design, and batch processing flows — are addressed individually below with file-level evidence of non-applicability. Error handling is the only sub-concern that has a meaningful (non-empty) implementation, and it is documented in Section 6.3.3.6.

#### 6.3.3.2 Event Processing Patterns

**Not applicable.** No event-driven architecture exists.

| Pattern | Status | Evidence |
|---|---|---|
| Event bus / domain events | Absent | No `pubsub`, no event store, no `dispatch` calls |
| Event sourcing | Absent | The `tracks` and `yearly_avg` tables are state, not event logs (Section 6.2) |
| CQRS | Absent | Read and write paths share the same schema; the write path is out-of-repo |
| Webhooks (inbound or outbound) | Absent | No webhook receiver routes; no outbound HTTP client |
| Observer pattern (server-side) | Absent | No SQLAlchemy event listeners registered |

The only "event-like" interaction in the codebase is React's prop-callback pattern between `DatePicker → TracksSection` and `FeatureSelect → TrendsSection`, which is in-process React state propagation, not an inter-system event channel.

#### 6.3.3.3 Message Queue Architecture

**Not applicable.** No message queue technology is present.

| Queue Technology | Status |
|---|---|
| Redis / Redis Streams | Absent (no `redis` in `requirements.txt`; no Redis service in `docker-compose.yml`) |
| RabbitMQ / AMQP | Absent (no `pika`, no `kombu`) |
| Apache Kafka | Absent (no `kafka-python`, no `confluent-kafka`) |
| AWS SQS / GCP Pub/Sub / Azure Service Bus | Absent (no cloud SDK present) |
| Celery / RQ / Dramatiq / Huey task queues | Absent (none in `requirements.txt`) |

`docker-compose.yml` declares only two services — `api` and `postgres` — confirming that no broker is co-deployed.

#### 6.3.3.4 Stream Processing Design

**Not applicable.** No streaming infrastructure exists.

| Streaming Capability | Status |
|---|---|
| Kafka Streams / Flink / Spark Streaming | Absent (no Java/Scala stack; no Python streaming libraries) |
| Server-Sent Events (SSE) | Absent (no `text/event-stream` content type emitted) |
| WebSockets | Absent (no `flask-socketio`, no `websockets`) |
| Chunked / streaming HTTP responses | Absent (every handler returns a complete `jsonify(...)` document) |
| GraphQL subscriptions | Absent (no GraphQL layer) |

All API responses are bounded JSON documents serialized in a single Marshmallow `dump()` call.

#### 6.3.3.5 Batch Processing Flows

The system has **no batch processing at the application tier**. Per Section 6.2.5.5, "no `executemany`, no `COPY`, no bulk loaders" exist in the `api/` package; every query in `api/routes.py` returns a bounded result set processed in-memory by Pandas helpers in `api/funcs.py`.

The only batch operations that exist anywhere in the data lifecycle are performed by the **out-of-repository pipeline** described in Section 4.2.3 and Section 6.3.4.1. Their cadence and shape are recorded as a contract — not implemented in this codebase:

| Out-of-Repo Batch Operation | Cadence | Approximate Volume |
|---|---|---|
| Weekly chart ingestion → `tracks` | Weekly (post Wednesday 10:00 AM chart finalization) | ~100 rows per run |
| Yearly aggregate refresh → `yearly_avg` | Annual rebuild | 1 row per year per run |

#### 6.3.3.6 Error Handling Strategy

Error handling is the one message-processing concern with a meaningful — though uniformly minimal — implementation across both tiers. Per Sections 4.5 and 5.4.3:

#### Frontend Error Handling

`frontend/src/components/tracks/TracksSection.js` (lines 12–33) and `frontend/src/components/trends/TrendsSection.js` (lines 14–35) implement an identical pattern:

- The fetch call awaits a response and inspects `response.status > 299` to set an `error` state.
- Empty result arrays are surfaced as a `'No Data Found'` banner.
- The `await fetch(...)` invocation is **not wrapped in `try/catch`**, so network-layer failures (DNS, connection reset, abort) produce an unhandled promise rejection and leave the UI stuck at `isLoaded=false` indefinitely.
- There is no `<ErrorBoundary>` wrapper anywhere in the React tree.
- No retry library is installed (`axios-retry`, `p-retry`) and no manual retry loop exists. Recovery requires the user to re-submit the form (`DatePicker` or `FeatureSelect`) or reload the page.

#### Backend Error Handling

`api/routes.py` contains **no `try/except` blocks** in any of its six handlers. All exceptions propagate as Flask's default 500 response with no structured body. No retry / resilience libraries are present (`tenacity`, `backoff`, `pybreaker` are absent from `requirements.txt`). Per Section 4.5 and Section 6.1.4.6, the failure-class-to-HTTP mapping is uniform — there is no graded degradation, no fallback response, and no circuit breaker between the handler and the database.

#### 6.3.3.7 Synchronous Request/Response Lifecycle Diagram

The diagram below makes explicit that **the entire integration model is synchronous**: each user action becomes exactly one HTTP request, one SQL query, and one JSON response, with no intermediate broker, queue, event, or asynchronous confirmation step.

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant B as Browser SPA
    participant F as Flask api container
    participant D as PostgreSQL

    Note over B,F: No queue, no broker, no event bus, no stream

    U->>B: Pick date / select feature
    B->>F: fetch /api/week/2021-11-13<br/>(or /api/analysis/tempo)
    Note right of B: await fetch — no try/catch wrapper<br/>no AbortController, no retry
    F->>D: SQLAlchemy query via psycopg2<br/>over TCP 5432
    Note right of F: No try/except in handler<br/>no circuit breaker, no backoff
    D-->>F: Bounded result set (≤100 or ≤~70 rows)
    F->>F: Marshmallow dump + Pandas helper
    F-->>B: 200 application/json (single document)
    B->>U: Render charts (amCharts)

    Note over U,D: Failure paths terminate in:<br/>frontend setError(statusText) +<br/>manual user re-submit / reload
```

---

### 6.3.4 External Systems

#### 6.3.4.1 Third-Party Integration Patterns

Per Section 3.4.1, **the application performs no outbound HTTP traffic to any external service.** The repository represents the **read-side** of a two-stage pipeline; the write-side that integrates with Spotify and Billboard is implemented outside this repository and is not present in any source file under `api/` or `frontend/`.

#### Out-of-Repository External Pipelines (Contract-Only)

| Service | Repository Status | Integration Pattern (Out-of-Repo) |
|---|---|---|
| **Spotify Web API** | Documented in `README.md` line 17 and `AboutSection.js` lines 56–63 | External weekly job uses Spotipy to enrich tracks with audio features (tempo, energy, danceability, instrumentalness, liveness, speechiness, acousticness, valence, loudness) |
| **Billboard.com Hot 100** | Documented in `README.md` line 15 and `AboutSection.js` lines 14–37, 43–46 | External weekly scraper extracts rank/artist/track from chart pages and persists to the `tracks` table |

#### Evidence of Non-Integration in This Repository

| Indicator | Verification |
|---|---|
| `spotipy` Python package | **Not in `requirements.txt`** |
| Generic HTTP client (`requests`, `httpx`, `aiohttp`) | **None present** |
| Outbound HTTP call in any `.py` file | **None found** |
| Spotify or Billboard credential / config | **None present** |
| Scheduler (cron, APScheduler, Celery beat) | **None present** |

The Flask process never reaches Spotify or Billboard at runtime. All data freshness depends on the out-of-repo job running on its weekly cadence and writing to PostgreSQL directly. The chart-week boundary at 10:00 AM Wednesday encoded in `get_query_week` (`api/funcs.py`) is the only timing dependency on the upstream pipeline that is visible in this codebase.

#### 6.3.4.2 Browser-Loaded External Resources

Per Section 3.4.2, exactly **one** external runtime resource is loaded by the SPA, and it is loaded by the browser directly — not proxied through Flask:

| Resource | Origin | Loading Pattern | Source |
|---|---|---|---|
| Google Fonts (Jost typeface) | `fonts.googleapis.com` / `fonts.gstatic.com` | `<link rel="preconnect">` hints + `<link rel="stylesheet">` with `display=swap` | `frontend/public/index.html` lines 7–10 |

The repository contains **no** analytics tags (Google Analytics, Segment, Mixpanel), **no** advertising scripts, and **no** third-party social-media integrations. The Google Fonts link is the totality of the third-party browser surface.

#### 6.3.4.3 Legacy System Interfaces

**Not applicable.** No legacy systems are integrated. The repository is a greenfield project (footer marker `AUG | 2021` in the SPA shell; no predecessor system referenced in `README.md` or any source file). There are no legacy file-format adapters, ESB endpoints, EDI/XML translators, SOAP clients, or mainframe connectors anywhere in the codebase.

#### 6.3.4.4 API Gateway Configuration

**No API gateway is deployed.** Per Section 6.1.2.4:

| Gateway Concern | Status | Evidence |
|---|---|---|
| Reverse proxy in stack | Absent | `docker-compose.yml` declares only `api` and `postgres` — no nginx/HAProxy/Traefik/Envoy service |
| Ingress controller | Absent | No Kubernetes manifests; deployment substrate is a generic Docker host |
| TLS termination | Absent | Plaintext HTTP only; TLS is a future reverse-proxy concern (Section 5.3.5) |
| Centralized rate limiting | Absent | Section 6.3.2.6 |
| Centralized authentication | Absent | Section 6.3.2.4 |
| Request routing across services | Not needed | Single `api` container handles all requests |

The Create-React-App proxy declaration `"proxy": "http://localhost:5000"` in `frontend/package.json` line 44 is sometimes mistaken for a gateway. It is **not** — it is a CRA dev-server affordance that intercepts XHR/fetch requests during local development (port 3000 → port 5000) and is not present in production. In production, the SPA bundle is served by Flask itself from `frontend/build/`, eliminating the cross-origin scenario entirely.

#### 6.3.4.5 External Service Contracts

The application has **no outbound service contracts**. The contracts that **govern** the system's correctness are three inbound or peer contracts:

#### Contract 1: PostgreSQL Wire Protocol (In-Stack)

| Attribute | Value |
|---|---|
| Connection string | `postgresql://postgres:postgres@postgres/db` (hardcoded in `api/__init__.py` line 12) |
| Driver | `psycopg2` 2.9.6 / `psycopg2-binary` 2.9.5 |
| Transport | TCP 5432 inside Compose bridge network |
| Service discovery | DNS resolution of host `postgres` via Compose (Section 6.1.2.3) |
| Pool tuning | None — Flask-SQLAlchemy defaults (Section 5.3.3) |

#### Contract 2: External Pipeline → PostgreSQL (Out-of-Repo)

| Attribute | Value |
|---|---|
| Owner | Out-of-repository pipeline |
| Tables written | `tracks` (weekly INSERT, ~100 rows), `yearly_avg` (annual rebuild, 1 row/year) |
| Schema ownership | Pipeline (no Alembic, no Flask-Migrate per Section 6.2.2.1) |
| Coordination | None (no advisory locks, no schema-version handshake) |

#### Contract 3: Browser → Flask (Public)

| Attribute | Value |
|---|---|
| Verb | `GET`-only across six routes |
| Body | None (URL path parameters only) |
| Response codec | `application/json` (or `text/html` on `/`) |
| Authentication | None (Section 6.3.2.4) |
| HTTP client in browser | Native `fetch()` (`TracksSection.js` line 19, `TrendsSection.js` line 21); `axios` is declared in `frontend/package.json` line 10 but never imported anywhere — captured as ADR-003 |

#### 6.3.4.6 External Integration Sequence (Read Side)

The sequence below traces a full request lifecycle that involves all external dependencies the running Flask container actually has:

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant B as Browser SPA
    participant CDN as fonts.googleapis.com<br/>fonts.gstatic.com
    participant F as Flask api container
    participant DB as PostgreSQL

    Note over U,CDN: Page bootstrap (independent of API)
    U->>B: Navigate to host:80
    B->>F: GET / (SPA bundle)
    F-->>B: 200 index.html + hashed JS/CSS
    B->>CDN: <link rel='stylesheet'> Jost (display=swap)
    CDN-->>B: Font face files (no app traffic)

    Note over U,DB: User interaction (synchronous read)
    U->>B: Pick date in DatePicker
    B->>F: fetch /api/week/2021-11-13
    F->>DB: SELECT * FROM tracks WHERE week=$1
    DB-->>F: ≤100 rows
    F-->>B: 200 application/json
    B->>U: amCharts radar render

    Note over U,DB: External pipeline (out of repo,<br/>does not pass through Flask)
```

The diagram emphasizes two operational facts: (1) the Google Fonts CDN request never traverses the Flask container, so a CDN outage degrades typography only; and (2) the external Billboard/Spotify pipeline writes directly to the database and is invisible to the running Flask process — a database that has not been refreshed will simply return stale weeks.

#### 6.3.4.7 External Pipeline Reference Sequence (Out-of-Repository)

For completeness, the contract that the application depends on for data freshness — though it lives outside this repository — is reproduced from Section 4.2.3 below:

```mermaid
sequenceDiagram
    participant Sched as External Scheduler
    participant Scrape as Billboard Scraper
    participant BB as billboard.com
    participant Sp as Spotipy Client
    participant SpAPI as Spotify Web API
    participant DB as PostgreSQL (this repo)

    Note over Sched,DB: Cadence: weekly (post-Wednesday 10:00 AM)
    Sched->>Scrape: Trigger weekly run
    Scrape->>BB: GET Hot 100 chart page
    BB-->>Scrape: HTML
    Scrape->>Scrape: Parse rank/artist/track
    Scrape->>Sp: Lookup spotify_id per track
    Sp->>SpAPI: GET /v1/search and /v1/audio-features
    SpAPI-->>Sp: Audio features payload
    Sp-->>Scrape: Enriched rows
    Scrape->>DB: INSERT INTO tracks ...
    Note over DB: Annually: external job rebuilds yearly_avg
```

This sequence is **not implemented in this repository**; it is included as a maintainer-facing contract describing the upstream dependency.

---

### 6.3.5 Integration Sequence Diagrams (Implemented Paths)

#### 6.3.5.1 Browser-to-Backend Integration

```mermaid
sequenceDiagram
    autonumber
    participant Browser as Browser (native fetch)
    participant CRA as CRA Dev Proxy<br/>(development only)
    participant Flask as Flask api 5000
    participant CORS as Flask-Cors 3.0.10

    Note over Browser,Flask: PRODUCTION (same-origin port 80 → 5000)
    Browser->>Flask: fetch /api/week/2021-11-13
    Flask->>CORS: Apply permissive CORS headers
    CORS-->>Flask: Access-Control-Allow-Origin: *
    Flask-->>Browser: 200 application/json
    Note right of Browser: No auth headers,<br/>no cookies, no CSRF token

    Note over Browser,Flask: DEVELOPMENT (port 3000 → CRA proxy → 5000)
    Browser->>CRA: fetch /api/week/2021-11-13
    CRA->>Flask: Forward to localhost:5000<br/>(per package.json "proxy")
    Flask-->>CRA: 200 application/json
    CRA-->>Browser: Pass-through response
```

#### 6.3.5.2 Backend-to-Database Integration

```mermaid
sequenceDiagram
    autonumber
    participant Route as routes.py handler
    participant ORM as Flask-SQLAlchemy 2.5.1
    participant Driver as psycopg2 2.9.6
    participant DB as PostgreSQL 15

    Note over Route,DB: Connection: postgresql://postgres:postgres@postgres/db<br/>Hardcoded in api/__init__.py line 12
    Route->>ORM: Tracks.query.filter_by(week=...)
    ORM->>Driver: Parameterized SQL bind
    Driver->>DB: TCP 5432 wire protocol
    DB-->>Driver: Row stream
    Driver-->>ORM: Hydrate ORM objects
    ORM-->>Route: List of Tracks instances
    Route->>Route: tracks_schema.dump (Marshmallow)
    Route->>Route: get_weekly_data (Pandas aggregation)
    Note over Route: Read-only — no explicit transaction;<br/>relies on autocommit-equivalent behavior
```

#### 6.3.5.3 Container Orchestration Integration Sequence

```mermaid
sequenceDiagram
    participant Op as Operator
    participant Compose as Docker Compose
    participant PG as postgres:15 container
    participant API as api container (Flask)

    Op->>Compose: docker compose up
    Compose->>PG: Pull postgres:15
    PG->>PG: Init POSTGRES_USER/PASSWORD/DB<br/>Bind ./data:/data
    PG-->>Compose: Listen 5432
    Compose->>API: Build (depends_on: postgres) + run<br/>CMD ["python3", "app.py"]
    API->>API: Construct Flask app, register CORS,<br/>SQLAlchemy, Marshmallow
    API->>API: app.run(host='0.0.0.0', port=5000)
    Note over Compose,API: Host port 80 → container 5000<br/>restart: on-failure on api only<br/>postgres has NO restart policy
```

The asymmetric restart policy (`api` has `restart: on-failure`; `postgres` does not) is documented in Section 6.1.4.1 as a known limitation requiring symmetric configuration before any production deployment.

---

### 6.3.6 Summary of Integration Posture

The integration concerns enumerated in the section prompt map to the actual codebase as follows. This summary cross-references each prompt concern with its disposition and the section in which evidence is recorded.

| Prompt Concern | Status | Reference |
|---|---|---|
| Protocol specifications | HTTP/1.1, JSON, GET-only | §6.3.2.1 |
| Authentication methods | None (explicit non-goal) | §6.3.2.4, §3.4.3 |
| Authorization framework | None (no state-changing endpoints) | §6.3.2.5, §5.3.5 |
| Rate limiting strategy | None (no `flask-limiter`, no proxy limits) | §6.3.2.6 |
| Versioning approach | None (no URL prefix, no header negotiation) | §6.3.2.7 |
| Documentation standards | Informal (README + AboutSection.js); no OpenAPI | §6.3.2.8 |
| Event processing patterns | Not applicable (no event bus) | §6.3.3.2 |
| Message queue architecture | Not applicable (no broker) | §6.3.3.3 |
| Stream processing design | Not applicable (no streaming) | §6.3.3.4 |
| Batch processing flows | None in-app; out-of-repo pipeline only | §6.3.3.5 |
| Error handling strategy | Minimal (frontend status check, default Flask 500) | §6.3.3.6 |
| Third-party integration patterns | None outbound from Flask; out-of-repo pipeline | §6.3.4.1 |
| Legacy system interfaces | Not applicable (greenfield) | §6.3.4.3 |
| API gateway configuration | None (no reverse proxy, no ingress) | §6.3.4.4 |
| External service contracts | Three contracts (Postgres in-stack, pipeline→DB, browser→Flask) | §6.3.4.5 |

Where this section identifies an absence as a **deliberate decision**, the rationale and revisit trigger are recorded in the corresponding ADR in Section 5.3.6 (specifically ADR-001 same-origin SPA+API, ADR-003 native `fetch`, ADR-004 no caching tier, ADR-006 Flask dev server). Where the absence is a **known limitation** awaiting remediation, it is recorded in the discrepancy listings of Sections 2.4.1 and 3.6 (notably: `gunicorn` declared but not invoked, `axios` declared but not imported, `web-vitals` declared but not wired, "3-year rolling average" labeling vs. 5-row implementation).

---

### 6.3.7 References

#### Files Examined

- `api/__init__.py` — Flask app construction; permissive `CORS(app)`; hardcoded PostgreSQL connection string; static_folder/static_url_path configuration enabling same-origin SPA serving.
- `api/routes.py` — Complete API surface (six `GET` routes); verified absence of `try/except`, retry, rate limiting, authentication decorators, and versioning.
- `api/funcs.py` — Aggregation helpers (`get_query_week`, `get_weekly_data`, `get_rolling_avg`); confirmed 5-row rolling-mean window contradicting "3 year rolling average" documentation.
- `api/models.py` — `Tracks` and `YearlyAvg` ORM models plus Marshmallow schemas; confirmed schemas are not versioned.
- `app.py` — Trivial entry point; `app.run(host='0.0.0.0')` invocation (Flask dev server, not gunicorn).
- `requirements.txt` — Pinned Python dependencies; confirmed absence of `requests`, `httpx`, `aiohttp`, `spotipy`, `celery`, `redis`, `pika`, `kombu`, `tenacity`, `backoff`, `pybreaker`, `flask-limiter`, `flask-caching`, `alembic`, and `Flask-Migrate`.
- `Dockerfile` — Single-stage image build; `CMD ["python3", "app.py"]` confirms Flask dev server in production despite `gunicorn==20.1.0` being installed.
- `docker-compose.yml` — Two-service stack (`api`, `postgres`); port mapping `80:5000`; asymmetric restart policy (`api: on-failure`; no policy on `postgres`); no API gateway, message broker, or cache service.
- `.dockerignore` — Excludes `frontend/node_modules`, `venv`, `data`.
- `README.md` — Plain-markdown enumeration of API endpoints (lines 19–24); references to out-of-repo Billboard scraper and Spotipy enrichment.
- `frontend/package.json` — Frontend dependency manifest; CRA proxy line `"proxy": "http://localhost:5000"`; verified `axios` declared but unused, `web-vitals` declared but unwired.
- `frontend/public/index.html` — Google Fonts integration via preconnect + stylesheet links (lines 7–10); confirmed absence of analytics, advertising, and social tags.
- `frontend/src/App.js` — Tab routing logic and component composition.
- `frontend/src/components/tracks/TracksSection.js` — `fetch()` to `/api/week/<date>`; verified absence of `try/catch`, retry, AbortController.
- `frontend/src/components/trends/TrendsSection.js` — `fetch()` to `/api/analysis/<feature>`; identical error-handling pattern.
- `frontend/src/components/about/AboutSection.js` — In-UI API documentation (lines 69–86); confirmed "3 year rolling average" labeling discrepancy with 5-row implementation.
- `frontend/src/components/tracks/DatePicker.js` — HTML `<input type='date'>` bounds (`min='1958-07-27'`, `max='2021-11-13'`).
- `frontend/src/components/trends/FeatureSelect.js` — Hardcoded 7-feature dropdown.

#### Folders Explored

- `/` (root) — Top-level Compose, Dockerfile, README, app.py, requirements.txt, .dockerignore.
- `api/` — Backend Flask package.
- `frontend/` — Frontend root.
- `frontend/src/` — React source tree.
- `frontend/src/components/` — Feature-area component subtrees (`navigation/`, `tracks/`, `trends/`, `about/`).
- `frontend/public/` — SPA shell and static manifest.

#### Cross-Referenced Technical Specification Sections

- **Section 1.2 SYSTEM OVERVIEW** — Project context as the read-side of a two-stage pipeline.
- **Section 2.4 IMPLEMENTATION CONSIDERATIONS** — Performance, scalability, and security non-goals; documented discrepancies (gunicorn, axios, web-vitals).
- **Section 3.4 THIRD-PARTY SERVICES** — External services audit (Spotify, Billboard, Google Fonts); confirmed absence of authentication, observability, and cloud SDKs.
- **Section 3.7 STACK INTEGRATION OVERVIEW** — End-to-end stack diagram with three integration points.
- **Section 4.2 INTEGRATION WORKFLOWS** — Browser-to-Backend, Backend-to-DB, External Pipeline, Container Orchestration sequences.
- **Section 4.5 ERROR HANDLING FLOWS** — Frontend/backend error patterns; retry/fallback absence matrix.
- **Section 5.1 HIGH-LEVEL ARCHITECTURE** — Two-tier monolith characterization; component inventory; data flows.
- **Section 5.3 TECHNICAL DECISIONS** — Architecture style decision matrix (5.3.1); communication patterns (5.3.2); caching justification (5.3.4); security mechanism selection (5.3.5); ADRs (5.3.6).
- **Section 5.4 CROSS-CUTTING CONCERNS** — AuthN/AuthZ posture (5.4.4); performance/SLA absence (5.4.5).
- **Section 6.1 Core Services Architecture** — Two-tier monolith applicability assessment; non-applicability of microservices concerns.
- **Section 6.2 Database Design** — Schema ownership boundary; absence of migration tooling.

## 6.4 Security Architecture

### 6.4.1 Applicability Assessment

#### 6.4.1.1 Non-Applicability Statement

**Detailed Security Architecture is not applicable for this system.**

Hot Stuff is a deliberately minimalist, public-read-only Billboard Hot 100 visualization service. There is no authentication, no authorization, no session management, no token handling, no password store, no encryption-at-rest configuration, no encryption-in-transit, no role-based access control, and no policy enforcement points anywhere in the codebase. The absence of these mechanisms is **not an oversight** — it is documented as an explicit non-goal across multiple sections of this specification:

| Concern | Documented Disposition | Reference |
|---|---|---|
| Authentication | "None — Public-read dataset; explicit non-goal" | Section 5.3.5 |
| Authorization | "None — No state-changing endpoints exist" | Section 5.3.5 |
| CSRF protection | "None — CSRF risk is structurally absent" | Section 6.3.2.5 |
| HTTPS termination | "Plaintext HTTP only; TLS is a future reverse-proxy concern" | Section 5.3.5, 6.3.4.4 |
| Rate limiting | "No `flask-limiter`; no proxy limits" | Section 6.3.2.6 |
| Personal data | "No personal data is collected; no user accounts" | Section 5.4.4, 6.2.4.3 |

This section therefore (a) records the **rationale** for the minimal posture, (b) catalogs the **standard security practices that ARE applied** despite the absence of a formal framework, (c) provides the required Mermaid diagrams to make the trust boundaries and request flows explicit, and (d) documents the **known security limitations** that must be remediated before any production-grade deployment.

#### 6.4.1.2 Justification for the Minimal Posture

Five structural properties of the system make a comprehensive security framework unnecessary at the current scope:

| Property | Implication for Security Posture |
|---|---|
| Single bounded context (public Billboard chart visualization) | No multi-tenant isolation surface |
| All six routes are HTTP `GET` only | No state-mutation surface; CSRF is structurally inapplicable |
| No PII, no user accounts, no payment data | No data-classification or access-control hierarchy needed |
| Public-domain dataset (Billboard chart positions + Spotify-derived audio features) | No confidentiality requirements on the data itself |

The application architecture reinforces these properties. Per Section 6.2 (Database Design), "every route handler in `api/routes.py` is a `GET` issuing read-only queries; no `db.session.commit()`, `db.session.rollback()`, or `INSERT/UPDATE/DELETE` calls exist anywhere in the repository." The write side of the data lifecycle — Billboard scraper plus Spotipy enrichment — is owned by an out-of-repository pipeline that writes directly to PostgreSQL and does not pass through the Flask process.

#### 6.4.1.3 Scope of This Section

```mermaid
flowchart TD
    Start([Security Architecture Scope]) --> Q1{Authentication<br/>required?}
    Q1 -->|No - public read| Q2{Authorization<br/>required?}
    Q1 -->|Yes| Full[Full Security Framework]
    Q2 -->|No - all GET| Q3{PII or<br/>regulated data?}
    Q2 -->|Yes| Full
    Q3 -->|No - public domain| Q4{State-changing<br/>endpoints?}
    Q3 -->|Yes| Full
    Q4 -->|No - read-only| Min[Minimal Posture<br/>+ Standard Practices]
    Q4 -->|Yes| Full
    Min --> Doc[Document non-applicability<br/>+ standard practices<br/>+ known limitations<br/>+ trust-boundary diagrams]
    Full --> NotInScope([Not applicable<br/>to this codebase])
    Doc --> Selected([Approach for<br/>Section 6.4])
```

The decision tree above captures the gating logic: because every branch leads to "Minimal Posture + Standard Practices," the section is structured around documenting **what exists**, **what is intentionally absent**, and **why**.

---

### 6.4.2 Authentication and Authorization Posture

#### 6.4.2.1 Authentication Framework Disposition

**No authentication framework exists.** The Flask application bootstrap in `api/__init__.py` imports only `Flask`, `flask_sqlalchemy`, `flask_marshmallow`, `flask_cors`, and `os`; no authentication library is imported anywhere in the codebase. The repository-wide absence is verifiable from the dependency manifest in `requirements.txt`:

| Identity / AuthN Capability | Status | Verification Evidence |
|---|---|---|
| OAuth 2.0 / OIDC client | Absent | No `authlib`, no `flask-oauthlib`, no `requests-oauthlib` in `requirements.txt` |
| JWT issuance / verification | Absent | No `pyjwt`, no `flask-jwt-extended`, no `python-jose` |
| Session middleware | Absent | No `flask-login`, no `flask-session`, no `flask-principal` |
| Password hashing | Absent | No `bcrypt`, no `passlib`, no `argon2-cffi` |

**Multi-factor authentication, password policies, and identity management** are non-applicable concerns because there is no primary authentication factor to extend, no password store to govern, and no identity to manage. There is no `/login`, no `/logout`, no `/register`, no `/forgot-password`, and no `/auth/*` namespace anywhere in `api/routes.py`.

#### 6.4.2.2 Authorization System Disposition

**No authorization framework exists.** Every route in `api/routes.py` is publicly accessible with no precondition checks. The verified absences:

| Authorization Capability | Status | Verification Evidence |
|---|---|---|
| `@login_required` / `@roles_required` decorators | Not used | No decorators on any handler in `api/routes.py` |
| Role-based access control (RBAC) | Not configured | No role table, no role-to-permission mapping |
| Attribute-based access control (ABAC) | Not configured | No policy engine, no `casbin`, no Open Policy Agent |
| Policy enforcement points | Not present | No middleware wrapping route handlers |
| Resource-level authorization | Not applicable | All resources are public chart data |

Per Section 6.3.2.5: "with no `POST`/`PUT`/`PATCH`/`DELETE` routes, there is no state-mutation surface for CSRF to attack." The same structural property eliminates the need for resource-level authorization: every read is a read of public Billboard chart positions or Spotify-derived audio features.

#### 6.4.2.3 Session, Token, and Credential Handling

The system holds no session state for clients, issues no tokens, and never sets cookies. Per Section 5.4.4: "No personal data is collected; no user accounts or sign-up flows exist."

| Session / Token Concern | Status |
|---|---|
| Session cookies | Not set by any handler |
| `Set-Cookie` response headers | Never emitted |
| Bearer / API-key tokens | Not required by any route |
| CSRF tokens | Not issued (no `flask-wtf`, no `csrf_token()`) |

The frontend's `fetch()` calls in `TracksSection.js` and `TrendsSection.js` are issued without `credentials: 'include'`; per Section 5.1.3, "No authentication tokens, no cookies, no CSRF tokens" are exchanged on the browser↔backend hop.

#### 6.4.2.4 Authentication and Authorization Flow (Empty Path)

The diagram below makes explicit that **no authentication or authorization step exists between the browser and the protected resource**. The user request flows directly from browser → Flask → PostgreSQL without any guard, decorator, middleware, or policy check.

```mermaid
sequenceDiagram
    autonumber
    participant U as Anonymous Browser
    participant F as Flask api container
    participant Auth as Authentication Layer
    participant Authz as Authorization Layer
    participant D as PostgreSQL

    Note over U,D: Trust boundary at the host port; no auth boundary exists

    U->>F: GET /api/week/2021-11-13<br/>(no Authorization header,<br/>no cookie, no token)
    F-->>Auth: NOT INVOKED<br/>(no middleware registered)
    F-->>Authz: NOT INVOKED<br/>(no decorator, no policy check)
    F->>D: SELECT FROM tracks WHERE week=$1<br/>(parameterized via SQLAlchemy ORM)
    D-->>F: ≤100 rows
    F-->>U: 200 application/json<br/>(no Set-Cookie, no security headers beyond CORS)

    Note over Auth,Authz: Empty boxes are documented<br/>as deliberate non-goals<br/>(Section 5.3.5 and 5.4.4)
```

The two "NOT INVOKED" interactions are the architectural marker for the absent layers: every request reaches the database with the same effective privilege, and no per-user, per-role, or per-resource policy is consulted.

---

### 6.4.3 Data Protection Posture

#### 6.4.3.1 Encryption Standards

The system applies **no encryption at any tier**. The full inventory of encryption gaps is documented below as a baseline for any future hardening effort.

| Layer | Status | Source of Evidence |
|---|---|---|
| Encryption at rest (database) | Not configured | `postgres:15` image defaults; no `pgcrypto` extension calls in `api/models.py` |
| Encryption at rest (filesystem) | Not configured | `./data:/data` bind-mount uses host filesystem defaults |
| Encryption in transit (browser ↔ Flask) | Plaintext HTTP only | `app.py` invokes `app.run(host='0.0.0.0')`; `Dockerfile` `EXPOSE 5000`; `docker-compose.yml` maps `80:5000` (no port 443) |
| Encryption in transit (Flask ↔ PostgreSQL) | Plaintext within Compose network | Connection string `postgresql://postgres:postgres@postgres/db` has no `sslmode` parameter |

There is no reverse proxy in the Compose stack to perform TLS termination. Per Section 6.3.4.4: "Reverse proxy in stack: Absent — `docker-compose.yml` declares only `api` and `postgres`; no nginx/HAProxy/Traefik/Envoy service." The single external resource that **does** travel over TLS is the browser's load of Google Fonts (Jost typeface) from `fonts.googleapis.com` and `fonts.gstatic.com`, but that traffic never traverses the Flask container.

#### 6.4.3.2 Key and Secret Management

**Secrets are hardcoded; no key management infrastructure exists.** The single material secret in the system — the PostgreSQL password — is duplicated in two source-controlled locations:

| Secret Location | Value | Risk Posture |
|---|---|---|
| `api/__init__.py` line 12 | `postgresql://postgres:postgres@postgres/db` | Source-controlled; visible in repository |
| `docker-compose.yml` (env block) | `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`, `POSTGRES_DB=db` | Source-controlled; visible in repository |

There is no `.env` file referenced at runtime, no secrets manager integration (AWS Secrets Manager, HashiCorp Vault, Azure Key Vault), and no key derivation or rotation procedure. The `python-dotenv` package is declared in `requirements.txt` but is **never imported** anywhere in the codebase — making it a dead dependency rather than a config loader.

`api/__init__.py` also imports the `os` module but does not invoke any `os.environ.get(...)` lookups, so no environment variable currently overrides the hardcoded URI. This is recorded in Section 1.2.1 as a known limitation: "Database credentials hardcoded — No environment-variable override; deployment-time secrets are not externalized."

#### 6.4.3.3 Data Classification and Masking

Per Section 6.2.4.3, the system handles **no personal data**:

| Data Class | Present in System? | Masking / Tokenization |
|---|---|---|
| Personal Identifiable Information (PII) | None collected | Not applicable |
| Authentication credentials (user-facing) | None (no user accounts) | Not applicable |
| Payment / financial data | None | Not applicable |
| Public chart data (artist, track title, rank, week) | Yes — public-domain | Not required |
| Spotify audio features (tempo, energy, etc.) | Yes — public-API derivative | Not required |

There are no data-masking rules, no row-level redaction policies, and no field-level tokenization layers. The Marshmallow schemas in `api/models.py` (`TrackSchema`, `YearlyAvgSchema`) project all model columns directly into the JSON response without filtering — which is acceptable because every column is non-sensitive.

#### 6.4.3.4 Input Validation and SQL Injection Prevention

Backend input validation is absent, but the parameterized-query pattern enforced by SQLAlchemy ORM provides structural SQL-injection prevention:

| Validation / Sanitization Surface | Status | Evidence |
|---|---|---|
| Backend input validation | None | `getattr(YearlyAvg, feature)` accepts arbitrary attribute names; invalid inputs become `AttributeError` → HTTP 500 |
| SQL injection prevention | Structural via ORM | All queries use `Tracks.query.filter_by(...)` or `Tracks.query.filter(func.lower(Tracks.artist).like(...))`; parameterized via SQLAlchemy + psycopg2 |
| Frontend HTML-input bounds | Limited | `DatePicker` `min='1958-07-27'`, `max='2021-11-13'`; `FeatureSelect` constrained to a 7-option `<select>` |
| Request body size limit | Not configured | `MAX_CONTENT_LENGTH` not set on Flask app |

Per Section 5.3.5: "Input validation: HTML-input bounds (frontend); none on backend — Adequate for HTML form clients; backend validation is a documented improvement opportunity." The principal gap is `getattr(YearlyAvg, feature)` on `/api/analysis/<feature>`, which exposes any column on the `YearlyAvg` model to retrieval; mitigation is a future-phase enhancement (Section 2.4.4).

---

### 6.4.4 Security Zones and Trust Boundaries

#### 6.4.4.1 Zone Inventory

The deployment topology comprises **a single Docker Compose bridge network** with one public ingress point and one host-published database port. There is no DMZ, no internal/external network split, and no segmentation between the application tier and the data tier.

| Zone | Composition | Trust Level |
|---|---|---|
| Public Internet | All anonymous browser clients | Untrusted |
| Docker Host | Operator-administered virtual machine | Trusted (depends on host hygiene) |
| Compose Bridge Network | `api` + `postgres` services | Implicitly trusted (intra-network) |
| External CDN (Google Fonts) | `fonts.googleapis.com`, `fonts.gstatic.com` | Trusted third-party (browser-direct) |

#### 6.4.4.2 Network Exposure Surface

Two host ports are published to the underlying machine:

| Host Port | Container Mapping | Exposure | Severity Note |
|---|---|---|---|
| `80` | `api:5000` | Public ingress for SPA + JSON API | Intended exposure |
| `5432` | `postgres:5432` | Direct database port to host | Development convenience; **must be removed** in production per Section 2.4.4 |

The `5432:5432` mapping is the most material exposure in the system: it allows any client that can reach the host to attempt direct PostgreSQL authentication using the hardcoded `postgres:postgres` credentials. Section 5.3.5 records: "The most material exposure is the host-published `5432:5432` port mapping with default credentials, which is acceptable for development hosts but must be removed before any internet-facing deployment."

The `Dockerfile` does not declare a `USER` directive, so the Flask process runs as `root` inside the container — adding privilege-escalation impact to any successful application-tier compromise. The base image `python:3.11-slim-buster` is built on Debian Buster, which has reached its standard support end-of-life and should be updated to a current Debian release before production deployment.

#### 6.4.4.3 Security Zone Diagram

The diagram below depicts the actual zone topology, the trust boundaries that exist, and the request flows between zones. Items shown with dashed borders are the **intentional non-applicability surfaces** documented in Section 6.4.2.

```mermaid
flowchart TB
    subgraph Internet["Public Internet (Untrusted Zone)"]
        Browser["Anonymous Browser<br/>no auth credentials,<br/>no cookies, no tokens"]
        ExtCDN["Google Fonts CDN<br/>fonts.googleapis.com<br/>fonts.gstatic.com"]
    end

    subgraph Host["Docker Host (Trusted Zone)"]
        subgraph Compose["Compose Bridge Network (Implicitly Trusted)"]
            subgraph ApiSvc["api service"]
                Flask["Flask 2.0.1 dev server<br/>runs as root<br/>plaintext HTTP only"]
                Static["frontend/build/<br/>SPA assets"]
                CorsLayer["Flask-Cors 3.0.10<br/>CORS app no allow-list"]
                AuthLayer["Authentication Layer<br/>NOT PRESENT"]
                AuthzLayer["Authorization Layer<br/>NOT PRESENT"]
                Flask -.serves.-> Static
                Flask --> CorsLayer
            end
            subgraph DbSvc["postgres service"]
                PG[("PostgreSQL 15<br/>user: postgres / pwd: postgres<br/>no TLS, no RLS, no GRANTs")]
                BindMount[("./data bind-mount<br/>host filesystem")]
                PG --- BindMount
            end
            Flask -- "psycopg2 over TCP 5432<br/>plaintext, no sslmode" --> PG
        end
        HostPort80["Host port 80"]
        HostPort5432["Host port 5432<br/>direct DB exposure"]
    end

    Browser -- "HTTP/1.1 plaintext<br/>port 80" --> HostPort80
    HostPort80 --> Flask
    Browser -. "HTTPS preconnect + stylesheet<br/>display=swap" .-> ExtCDN
    PG --> HostPort5432

    classDef absent stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class AuthLayer,AuthzLayer absent
```

The diagram's principal observations:

- **Trust boundaries**: One genuine boundary exists — between the public Internet and the Docker host at port 80. There is no second boundary inside the Compose bridge network, so any process inside `api` can speak to PostgreSQL without authentication challenge beyond the hardcoded credentials.
- **Empty layers**: The Authentication and Authorization layers are dashed because they are deliberately absent (Section 5.3.5).
- **Direct database port**: The `5432:5432` line bypasses Flask entirely; a network-reachable attacker can attempt DB auth without any application-tier mediation.
- **External CDN**: Google Fonts traffic never enters the Docker host; it is browser-direct over HTTPS, so a CDN compromise affects typography only, never application data.

---

### 6.4.5 Compliance and Audit Posture

#### 6.4.5.1 Privacy Compliance

Per Section 6.2.4.3, no privacy framework applies because the system collects no personal data:

| Privacy Concern | Disposition |
|---|---|
| Personal Identifiable Information (PII) | None collected or stored |
| User accounts / sign-up flows | None |
| Cookies / tracking pixels / analytics | None set; verified in `frontend/public/index.html` |
| GDPR / CCPA cookie banner | Not required (no cookies) |
| Right-to-erasure workflow | Not required (no personal data) |
| Data Processor Agreement scope | Not applicable |
| Cross-border data transfer concerns | None (data is public-domain Billboard + Spotify-derived) |

Per Section 1.3.3, third-party analytics surfaces are explicitly not present: "No tracking snippets in `frontend/public/index.html`." The only third-party browser-loaded resource is Google Fonts (Jost typeface), which loads font face files and does not transmit user data back to the application.

#### 6.4.5.2 Audit Logging

Per Section 6.2.4.4, no formal audit framework is configured. The single observable audit trail is **Flask's default Werkzeug request log on stdout**, captured by the Docker engine's logging driver:

| Audit Surface | Status | Notes |
|---|---|---|
| `pgaudit` extension | Not enabled | `postgres:15` image default |
| Per-table change-tracking triggers | Not declared | None in `api/models.py` |
| `audit_log` table | Does not exist | Schema is two tables only |
| Application-level audit decorator | Not implemented | No middleware wrapping handlers |
| Read-access logging | Werkzeug default on stdout | Records method, path, status, timestamp |
| Correlation IDs / request IDs | Not generated | No `X-Request-ID` issued or echoed |
| Structured log aggregation | Absent | No `structlog`, no `loguru`, no log shipper |

The default request log records HTTP method, path, status code, and timestamp — but does **not** record SQL bind parameters, returned row counts, or client-identifying metadata beyond the source IP. This is consistent with the public-read profile of the dataset (Section 5.4.4): there is no privileged action to audit because every action is a public read.

#### 6.4.5.3 Compliance Control Matrix

| Compliance Domain | Applicable to System? | Disposition |
|---|---|---|
| GDPR (EU data subjects) | Not applicable | No personal data collected |
| CCPA (California consumers) | Not applicable | No personal data collected |
| HIPAA (protected health information) | Not applicable | No health data |
| PCI-DSS (cardholder data) | Not applicable | No payment surface |
| SOC 2 (operational controls) | Not in scope | Solo-maintainer, non-commercial scope |
| Cookie-consent regulations | Not applicable | No cookies set |

The compliance posture should be re-assessed if any of the following architectural changes occur: introduction of user accounts, integration of analytics SDKs, addition of payment processing, expansion to cross-region deployment, or deployment under a regulated organizational umbrella.

---

### 6.4.6 Security Control Matrices

#### 6.4.6.1 Implemented Standard Practices

Despite the absence of a formal security framework, the codebase does apply several standard practices that reduce its baseline attack surface. These are the **standard security practices that ARE followed** in lieu of a comprehensive framework:

| Practice | Implementation | Source |
|---|---|---|
| Parameterized SQL queries | All ORM expressions use `filter_by(...)`, `filter(...)`, and `with_entities(...)` | `api/routes.py` |
| Read-only application contract | No `INSERT`/`UPDATE`/`DELETE`, no `db.session.commit()`/`rollback()` | `api/routes.py` (Section 6.2) |
| One-way serialization | Marshmallow `dump()` only; no `load()`, no `@validates`, no `@post_load` | `api/models.py` (Section 6.2.1.4) |
| Pinned dependencies | 23 packages with exact versions in `requirements.txt`; pinned `frontend/package.json` | `requirements.txt`, `frontend/package.json` |
| Build-context exclusion | `.dockerignore` excludes `frontend/node_modules`, `venv`, `data` | `.dockerignore` |
| Same-origin SPA delivery | `static_folder='../frontend/build'`, `static_url_path='/'` removes cross-origin attack surface in production | `api/__init__.py` |
| SQLAlchemy event-tracking disabled | `SQLALCHEMY_TRACK_MODIFICATIONS = False` reduces overhead and side-channel surface | `api/__init__.py` |
| Defense-in-depth CORS | `CORS(app)` registered globally so production same-origin traffic still receives consistent headers | `api/__init__.py`, Section 5.3.5 |
| HTTPS to third-party CDN | Google Fonts loaded via `https://fonts.googleapis.com` + `https://fonts.gstatic.com` | `frontend/public/index.html` |
| Structural CSRF immunity | All routes are `GET`; no state-mutation surface for CSRF to attack | `api/routes.py` (Section 6.3.2.5) |

The combination of read-only contract + parameterized ORM queries + one-way Marshmallow serialization eliminates the three highest-impact application-tier risk classes by construction: SQL injection, server-side request-mutation, and deserialization-of-untrusted-input attacks.

#### 6.4.6.2 Non-Applicable / Deferred Controls

The following controls are documented as **not applicable** or **deferred** with file-level evidence supporting each disposition:

| Control | Disposition | Rationale |
|---|---|---|
| OAuth / OIDC client | Not applicable | No user accounts; public-read dataset |
| Multi-factor authentication | Not applicable | No primary authentication factor exists |
| Password policy | Not applicable | No user-facing password store |
| Session timeout / rotation | Not applicable | No sessions established |
| JWT token lifetime / refresh | Not applicable | No tokens issued |
| Role-based access control (RBAC) | Not applicable | All data is public; no role hierarchy |
| Policy enforcement points (PEPs) | Not applicable | No state-changing endpoints to enforce against |
| Data-masking rules | Not applicable | No sensitive data fields |
| Field-level tokenization | Not applicable | No PII or financial data |
| TLS at application port | Deferred | Future reverse-proxy concern (Section 5.3.5) |
| Rate limiting | Deferred | `flask-limiter` not installed; bounded result sizes provide natural throttle |
| Web Application Firewall (WAF) | Deferred | No upstream proxy in stack |
| Web vulnerability scanner integration | Deferred | No CI/CD pipeline (Section 1.3.3) |

#### 6.4.6.3 Known Security Limitations and Hardening Path

The limitations below are documented across Sections 1.2.1, 2.4.4, 5.3.5, and 6.2.4.5. They are reproduced here as a single security-focused inventory with file-level evidence and a recommended hardening sequence.

| Limitation | Evidence | Severity | Recommended Remediation |
|---|---|---|---|
| Hardcoded DB credentials | `api/__init__.py` line 12; `docker-compose.yml` env block | High | Externalize via environment variables; activate `python-dotenv` (already declared) |
| Database port `5432:5432` published to host | `docker-compose.yml` | High | Remove host port mapping; rely on Compose-internal DNS only |
| No HTTPS termination | `app.py`; `Dockerfile` `EXPOSE 5000`; no reverse proxy | High | Front Flask with nginx/Traefik for TLS |
| Container runs as `root` | `Dockerfile` (no `USER` directive) | Medium | Add non-root `USER` in `Dockerfile`; chown app directory |
| Flask development server in production | `Dockerfile` `CMD ["python3", "app.py"]` (Section 5.3.6 ADR-006) | Medium | Switch to `gunicorn` (already in `requirements.txt`) |
| No input validation on `/api/analysis/<feature>` | `getattr(YearlyAvg, feature)` in `api/routes.py` | Medium | Validate `feature` against an allow-list of column names |
| Permissive CORS (no allow-list) | `CORS(app)` in `api/__init__.py` | Low (same-origin in prod) | Tighten to explicit origin allow-list |
| No rate limiting | `flask-limiter` absent from `requirements.txt` | Low | Install `flask-limiter` and apply per-route quotas |
| Base image `python:3.11-slim-buster` | `Dockerfile` | Medium | Migrate to a current Debian release |
| `python-dotenv` declared but unused | `requirements.txt` | Cosmetic / future-readiness | Activate to load `.env` for externalized config |
| No structured logging or correlation IDs | `api/__init__.py`; Section 5.4.2 | Low | Adopt `structlog`; emit `X-Request-ID` |
| `postgres` service has no restart policy | `docker-compose.yml` | Medium | Add `restart: on-failure` on `postgres` (Section 5.4.6) |

The recommended hardening sequence — ordered by the cumulative reduction in attack surface — is:

```mermaid
flowchart LR
    Start([Current Posture<br/>development-grade]) --> H1["1: Externalize<br/>DB credentials"]
    H1 --> H2["2: Remove<br/>5432:5432 mapping"]
    H2 --> H3["3: Front Flask<br/>with TLS reverse proxy"]
    H3 --> H4["4: Switch to<br/>gunicorn WSGI"]
    H4 --> H5["5: Add input<br/>allow-list validation"]
    H5 --> H6["6: Run as<br/>non-root USER"]
    H6 --> H7["7: Tighten CORS<br/>+ add rate limiting"]
    H7 --> H8["8: Add structured<br/>logging + audit"]
    H8 --> Production([Production-grade<br/>posture])
```

Each hardening step is referenced to the corresponding section of the specification: steps 1 and 5 to Section 6.2.4.5 (Access Controls), step 2 to Section 2.4.4 (Security Implications), steps 3 and 4 to Section 5.3.5 (Security Mechanism Selection) and Section 5.3.6 (ADR-006), step 6 to Section 6.4.4.2 above, step 7 to Section 6.3.2.6 (Rate Limiting Strategy) and Section 6.3.2.9 (CORS Configuration), and step 8 to Section 5.4.2 (Logging and Tracing Strategy).

---

### 6.4.7 Summary

The Hot Stuff system's security posture is intentionally minimal because the system is **a single-bounded-context, read-only, public-data visualization** with no user accounts, no PII, no payment data, and no state-changing endpoints. A comprehensive Authentication / Authorization / Data Protection framework is therefore not applicable to the codebase as it stands. In its place, the codebase applies a small set of **standard security practices** — parameterized ORM queries, read-only application contract, one-way Marshmallow serialization, pinned dependencies, `.dockerignore` exclusions, and same-origin SPA delivery — that together eliminate the most material application-tier attack classes by construction.

The known security limitations — hardcoded credentials, exposed `5432:5432` port, plaintext HTTP, root container user, Flask development server, missing input allow-list, permissive CORS — are all documented as **acceptable for development** and **mandatory remediations before production exposure**. The hardening sequence in Section 6.4.6.3 sketches the order in which these gaps should be closed when the system's deployment context evolves beyond solo-maintainer development hosts.

---

### 6.4.8 References

#### Files Examined

- `api/__init__.py` — Flask application bootstrap; permissive `CORS(app)`; hardcoded PostgreSQL connection string; `SQLALCHEMY_TRACK_MODIFICATIONS = False`; verified absence of authentication middleware, `SECRET_KEY`, and environment-variable-driven configuration.
- `api/routes.py` — Six `GET`-only route handlers; verified absence of `@login_required` / `@roles_required` decorators, login/logout routes, cookie operations, and CSRF token issuance.
- `api/models.py` — `Tracks` and `YearlyAvg` ORM models plus `TrackSchema` and `YearlyAvgSchema` Marshmallow schemas; verified `dump()`-only usage with no `load()` calls; primary-key-only indexing.
- `api/funcs.py` — Aggregation helpers; verified absence of credential handling or encryption operations.
- `app.py` — Trivial entry point; `app.run(host='0.0.0.0')` confirms Flask development server with no TLS layer.
- `Dockerfile` — Single-stage image build on `python:3.11-slim-buster`; `EXPOSE 5000` only; `CMD ["python3", "app.py"]`; verified absence of `USER` directive (runs as root) and `HEALTHCHECK` instruction.
- `docker-compose.yml` — Two-service stack; hardcoded `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB`; `5432:5432` host port mapping; asymmetric restart policy; verified absence of TLS service or reverse proxy.
- `requirements.txt` — 23 pinned Python dependencies; verified absence of `pyjwt`, `authlib`, `flask-login`, `flask-jwt-extended`, `flask-session`, `flask-principal`, `python-jose`, `cryptography`, `bcrypt`, `passlib`, `flask-limiter`, `flask-wtf`; `python-dotenv` declared but never imported.
- `.dockerignore` — Build-context exclusions for `frontend/node_modules`, `venv`, `data`.
- `frontend/package.json` — Frontend dependency manifest; CRA dev-proxy declaration; verified absence of authentication libraries.
- `frontend/public/index.html` — SPA shell; Google Fonts as the only third-party resource (loaded over HTTPS); verified absence of analytics, advertising, and social tags.
- `README.md` — Project description; references to out-of-repository Billboard scraper and Spotipy enrichment.

#### Folders Examined

- `/` (repository root) — Top-level Compose, Dockerfile, app.py, README, requirements.txt, .dockerignore.
- `api/` — Backend Flask package (`__init__.py`, `routes.py`, `models.py`, `funcs.py`).
- `frontend/` — Frontend root (`package.json`, `package-lock.json`, `src/`, `public/`, `build/`).
- `frontend/src/` — React source tree.
- `frontend/public/` — SPA shell and static manifest.

#### Cross-Referenced Technical Specification Sections

- **Section 1.2 SYSTEM OVERVIEW** — Project context as the read-side of a two-stage pipeline; hardcoded-credentials limitation.
- **Section 1.3 SCOPE** — Authentication and authorization explicitly listed in Out-of-Scope Elements.
- **Section 2.4 IMPLEMENTATION CONSIDERATIONS** — Section 2.4.4 Security Implications matrix (primary security source).
- **Section 3.4 THIRD-PARTY SERVICES** — Section 3.4.3 Authentication and Authorization Services confirms "None"; Section 3.4.5 confirms no cloud SDKs.
- **Section 3.5 DATABASES & STORAGE** — Hardcoded credentials, default Flask-SQLAlchemy connection pool, no caching layer.
- **Section 3.7 STACK INTEGRATION OVERVIEW** — Permissive CORS as defense-in-depth.
- **Section 5.1 HIGH-LEVEL ARCHITECTURE** — Two-tier monolith characterization; same-origin SPA delivery.
- **Section 5.3 TECHNICAL DECISIONS** — Section 5.3.5 Security Mechanism Selection (primary decision matrix); ADR-006 Flask Dev Server in Production.
- **Section 5.4 CROSS-CUTTING CONCERNS** — Section 5.4.2 Logging and Tracing Strategy; Section 5.4.4 Authentication and Authorization Framework (primary cross-cutting source); Section 5.4.6 Disaster Recovery Procedures.
- **Section 6.1 Core Services Architecture** — Two-tier monolith confirmation; resilience patterns.
- **Section 6.2 Database Design** — Section 6.2.4 Compliance Considerations (privacy, audit, access controls).
- **Section 6.3 INTEGRATION ARCHITECTURE** — Sections 6.3.2.4 (Authentication Methods), 6.3.2.5 (Authorization Framework), 6.3.2.6 (Rate Limiting Strategy), 6.3.2.9 (CORS Configuration), 6.3.4.4 (API Gateway Configuration).

## 6.5 Monitoring and Observability

### 6.5.1 Applicability Assessment

#### 6.5.1.1 Non-Applicability Statement

**Detailed Monitoring Architecture is not applicable for this system.**

Hot Stuff is a deliberately minimal, two-tier monolithic web application — a single Flask process serving a compiled React Single-Page Application alongside a sibling PostgreSQL 15 container. The repository contains **no observability instrumentation of any kind**: no Application Performance Monitoring (APM) agent, no error-reporting SDK, no metrics endpoint, no health-check endpoints, no distributed tracing client, no structured logger, and no log-aggregation forwarder. Section 1.3.3 (Out-of-Scope Elements) explicitly catalogs **"Observability (logging, metrics, tracing)"** as an excluded capability, with the supporting evidence "No structured logging, no metrics endpoint, no APM agent." Section 3.4.4 (Monitoring and Observability Tools) summarizes the tooling posture in a single word: **"None."**

This section therefore (a) records the **rationale** for the minimal posture, (b) catalogs the **basic monitoring practices that ARE in effect** despite the absence of a formal framework, (c) documents each prompt sub-area as non-applicable with file-level evidence, (d) provides the three required Mermaid diagrams to make the absent layers explicit, and (e) documents the **recommended hardening path** for any future production-grade deployment.

#### 6.5.1.2 Justification for the Minimal Posture

Five structural properties of the system make a comprehensive monitoring framework unnecessary at the current scope:

| Property | Implication for Monitoring Posture |
|---|---|
| Solo-maintainer operational model (footer marker `AUG | 2021`) | No on-call rotation, no PagerDuty/OpsGenie, no SRE practice to consume telemetry |
| Public-read-only dataset (Billboard chart positions + Spotify-derived audio features) | No SLOs around availability of personalized content; no business KPIs to track |
| Two-tier monolithic architecture (one `api` container + one `postgres` container) | No inter-service spans to trace; no service-mesh observability surface |
| Read-only HTTP `GET` API with bounded result sizes (≤100 rows for `/api/week`, ≤~70 rows for `/api/analysis`) | Performance envelope is structurally bounded; capacity planning is trivial |
| No SLAs codified anywhere in the repository (per Section 5.4.5) | Nothing to alert against; no error budget to consume |

ADR-001 (Single-Process SPA + API), ADR-004 (No Caching Tier), and ADR-006 (Flask Dev Server in Production) — all recorded in Section 5.3.6 — collectively establish the system as a development-grade deployment whose operational sophistication is intentionally bounded. The absence of monitoring is a downstream consequence of these decisions, not an oversight.

#### 6.5.1.3 Basic Monitoring Practices Currently In Effect

The deployed system does have a small set of observation surfaces that arise from default behaviors of Flask, PostgreSQL, and the Docker engine. These are the **only** monitoring practices currently followed:

| Practice | Implementation | Captured Information |
|---|---|---|
| Flask request logging | Werkzeug's default per-request stdout line | HTTP method, path, status code, timestamp |
| PostgreSQL stdout | `postgres:15` image's default logging configuration | Server lifecycle messages, connection events |
| Docker engine logging driver | Default driver captures both containers' stdout/stderr | Per-container log streams on host log storage |
| Compose process recovery | `restart: on-failure` on the `api` service only | Automatic relaunch after non-zero exit |
| Flask exception traceback dumps | Python tracebacks printed to stderr on uncaught exception | Exception class, traceback, source line (HTML stack trace only in debug mode) |

The default Werkzeug request log records the HTTP method, the path, the status code, and the timestamp. It does **not** record SQL bind parameters, returned row counts, or client-identifying metadata beyond the source IP, consistent with the system's public-read profile (Section 6.4.5.2). The Docker engine's logging driver retention is governed by the host's `docker` daemon defaults; the application does not configure log rotation, log shipping, or any agent.

---

### 6.5.2 Monitoring Infrastructure

Each sub-area below corresponds to one of the prompt's Monitoring Infrastructure concerns. In every case, the disposition is **non-applicable** for the current deployment, with file-level evidence supporting that designation. The "Recommended Future-Phase Tool" column documents the artifact that would close the gap if a production-grade hardening were undertaken.

#### 6.5.2.1 Metrics Collection

**Not applicable.** No metrics emitter is registered in the application, no metrics endpoint is exposed, and no scrape target is configured at any tier.

| Capability | Status | Verification Evidence | Recommended Future-Phase Tool |
|---|---|---|---|
| Prometheus client library | Absent | `prometheus-client` not in `requirements.txt` (23 pinned packages) | `prometheus-client` Python package |
| `/metrics` route | Absent | Six `GET` routes in `api/routes.py`; none expose metrics | Add `/metrics` exposing process and HTTP histograms |
| StatsD / DogStatsD client | Absent | No `statsd` package in `requirements.txt` | DogStatsD-Python or `statsd` |
| Pull-based exporters | Absent | No `node_exporter` / `postgres_exporter` services in `docker-compose.yml` | Add as sidecar Compose services |
| Application counters / histograms | Absent | No instrumentation in `api/routes.py` or helpers in `api/funcs.py` | Decorate handlers with histogram timers |

#### 6.5.2.2 Log Aggregation

**Not applicable.** The system does not produce structured logs and does not forward logs anywhere beyond the Docker engine's local logging driver.

| Capability | Status | Verification Evidence | Recommended Future-Phase Tool |
|---|---|---|---|
| Structured logger | Absent | No `structlog`, `loguru`, or `python-json-logger` in `requirements.txt` | `structlog` with JSON renderer |
| `logging.config` configuration | Absent | No `import logging`, no `app.logger`, no `getLogger` calls in any Python source | `dictConfig` with stdout JSON handler |
| Correlation IDs | Absent | No per-request UUID issued; no `X-Request-ID` echoed back to clients | `flask-request-id` or middleware |
| Log shipper | Absent | No Fluent Bit, Logstash, Vector, or cloud-native agent in either container | Fluent Bit sidecar or DaemonSet |
| Central log store | Absent | No Loki, Elasticsearch, or cloud log aggregator referenced in repo | Loki / OpenSearch / cloud-native |

#### 6.5.2.3 Distributed Tracing

**Not applicable.** This is a two-container monolith with exactly one inter-tier hop (Flask → PostgreSQL via `psycopg2`); there are no microservice spans to correlate. Even so, intra-process tracing of route → helper → ORM call would aid diagnostics and is also absent.

| Capability | Status | Verification Evidence | Recommended Future-Phase Tool |
|---|---|---|---|
| OpenTelemetry SDK | Absent | No `opentelemetry-*` packages in `requirements.txt` | OpenTelemetry Python auto-instrumentation |
| Jaeger / Zipkin client | Absent | No `jaeger-client`, no `py-zipkin` in `requirements.txt` | Jaeger or Tempo backend |
| W3C trace propagation | Absent | No `traceparent` headers set or honored on any route | Auto-configured by OTel instrumentation |
| Frontend trace SDK | Absent | No `@opentelemetry/sdk-trace-web` in `frontend/package.json` | OpenTelemetry browser SDK |
| Span exporter | Absent | No exporter endpoint configured | OTLP HTTP exporter to a collector |

#### 6.5.2.4 Alert Management

**Not applicable.** No alerting pipeline exists; there are no alert rules, no notification channels, and no on-call routing.

| Capability | Status | Verification Evidence | Recommended Future-Phase Tool |
|---|---|---|---|
| Alert rule engine (Alertmanager, Grafana Alerts) | Absent | No alerting service in `docker-compose.yml` | Prometheus Alertmanager |
| Notification channel (PagerDuty, OpsGenie, Slack) | Absent | No webhook URL or token in any config; no `slack-sdk`-style package | PagerDuty / OpsGenie / Slack webhook |
| Synthetic / blackbox monitoring | Absent | No external probe; no `blackbox_exporter` | Pingdom / UptimeRobot / blackbox_exporter |
| Error-reporting SDK alerts | Absent | No Sentry / Rollbar / Bugsnag in `requirements.txt` or `frontend/package.json` | Sentry SDK with alert rules |
| Container-exit notification | Absent | Compose `restart: on-failure` is silent — no notification emitted | Docker event listener sidecar |

#### 6.5.2.5 Dashboard Design

**Not applicable.** No dashboards are configured. The only operator-visible surface for live state is `docker logs <container>` and `docker compose ps` on the host shell.

| Capability | Status | Verification Evidence | Recommended Future-Phase Tool |
|---|---|---|---|
| Grafana dashboards | Absent | No Grafana service in `docker-compose.yml`; no JSON dashboard files in repo | Grafana with provisioned dashboards |
| Kibana / OpenSearch Dashboards | Absent | No Elasticsearch backend; no Kibana service | OpenSearch Dashboards |
| Vendor APM UI (Datadog, New Relic) | Absent | No vendor SDK in dependency manifests | Datadog / New Relic agent |
| Custom status page | Absent | No `/status`, `/healthz`, or operator-facing UI route in `api/routes.py` | Static `statuspage.io` or self-hosted |
| Alert-history view | Absent | No alert engine to feed history from | Alertmanager UI / Grafana Alerting |

#### 6.5.2.6 Current Monitoring Architecture (Minimal State)

The diagram below depicts the **actual** observability topology — request paths through the system and the only logs that are emitted. Items shown with dashed borders are the **deliberately absent** monitoring layers documented in Sections 6.5.2.1 through 6.5.2.5.

```mermaid
flowchart TB
    User([Anonymous Browser])

    subgraph Host["Docker Host"]
        subgraph Compose["Compose Bridge Network"]
            subgraph ApiSvc["api service - port 80 to 5000"]
                Flask["Flask 2.0.1 dev server<br/>single-threaded<br/>no instrumentation"]
                Werkzeug["Werkzeug default<br/>request logger<br/>method, path, status, ts"]
                Tracebacks["Python exception<br/>tracebacks to stderr"]
                Flask --> Werkzeug
                Flask --> Tracebacks
            end
            subgraph DbSvc["postgres service"]
                PG["PostgreSQL 15<br/>image default logs"]
            end
            Flask -- "psycopg2 TCP 5432" --> PG
        end

        DockerLog["Docker engine logging driver<br/>captures stdout / stderr<br/>(default driver)"]
        HostStore[("Host log storage<br/>retention per Docker daemon defaults")]

        Werkzeug --> DockerLog
        Tracebacks --> DockerLog
        PG --> DockerLog
        DockerLog --> HostStore
    end

    subgraph Absent["Deliberately Absent Layers (per Section 3.4.4)"]
        APM["APM Agent<br/>Datadog / New Relic"]
        Sentry["Error Reporting<br/>Sentry / Rollbar"]
        Prom["Metrics Endpoint<br/>Prometheus / statsd"]
        OTel["Distributed Tracing<br/>OpenTelemetry / Jaeger"]
        Aggr["Log Aggregation<br/>Fluent Bit / Loki"]
        Dash["Dashboards<br/>Grafana / Kibana"]
        Alert["Alert Manager<br/>PagerDuty / Slack"]
    end

    User -- "HTTP/1.1 plaintext" --> Flask
    Flask -. "no agent in path" .-> APM
    Flask -. "no SDK init" .-> Sentry
    Flask -. "no /metrics route" .-> Prom
    Flask -. "no traceparent" .-> OTel
    DockerLog -. "no shipper" .-> Aggr
    Aggr -. "no source" .-> Dash
    Prom -. "no rules" .-> Alert

    classDef absent stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class APM,Sentry,Prom,OTel,Aggr,Dash,Alert absent
```

The principal architectural observations:

- The **only** path from application to observable artifact is Werkzeug stdout → Docker logging driver → host log storage.
- The seven dashed layers correspond exactly to the absences enumerated in Section 5.4.1's monitoring posture matrix.
- The diagram contains **no feedback edge** from observability back to operations — there is no alert path, no dashboard, no operator notification surface.

---

### 6.5.3 Observability Patterns

#### 6.5.3.1 Health Checks

**Not implemented.** No health-check endpoints exist in `api/routes.py`, and no container-level health probe is declared. This is the single most frequently called-out gap across multiple sections of this specification (5.4.1, 5.4.6, 6.1.4.1, 6.1.4.8).

| Health Check Surface | Status | Verification Evidence |
|---|---|---|
| Flask `/healthz` endpoint | Absent | No such route in `api/routes.py` (six `GET` routes only) |
| Flask `/readyz` endpoint | Absent | No readiness probe distinguishing DB-connected state |
| Flask `/health` or `/ping` endpoint | Absent | No equivalent route in `api/routes.py` |
| Docker `HEALTHCHECK` instruction | Absent | `Dockerfile` (15 lines) declares no `HEALTHCHECK` directive |
| Docker Compose `healthcheck:` block | Absent | `docker-compose.yml` declares no `healthcheck:` for either service |
| Synthetic probe / external check | Absent | No external monitoring service configured |

The operational consequence of this absence — documented in Section 6.1.4.1 — is that **the `restart: on-failure` policy on the `api` service only triggers on hard process exit, not on hung-but-running states**. A Flask process that has stopped serving (e.g., due to a deadlocked request, an event-loop hang, or a `psycopg2` connection that never returns) will continue to run from Docker's perspective, will pass any liveness check that does not actually probe the HTTP surface, and will be missed by the current restart policy.

A minimal `/healthz` endpoint returning `200 OK` after a trivial `SELECT 1` against the database, paired with a Compose `healthcheck:` block on `api`, is the highest-leverage single hardening step recommended in Section 5.4.6 and Section 6.1.4.8.

#### 6.5.3.2 Performance Metrics

**No performance metrics are emitted.** The codebase contains no histogram timers, no request-counter middleware, no per-route latency capture, and no Real-User Monitoring (RUM) on the frontend. The bounds documented below are **observable from the code structure** but are **not measured** at runtime.

| Workflow | Observable Performance Bound | Source of Bound |
|---|---|---|
| `/api/week/<week>` | ≤100 rows per response | Billboard Hot 100 has 100 entries by definition |
| `/api/artist/<name>` | Full-table scan | `LOWER(...) LIKE '%pattern%'` cannot use B-tree indexes |
| `/api/analysis/<feature>` | ≤~70 rows | `YearlyAvg` is one row per year (1958–present) |
| `/api/track/<id>` | Single-row primary key lookup | `Tracks.query.filter_by(id=...)` |
| Flask development server | Single-threaded; one in-flight request | `Dockerfile` `CMD ["python3", "app.py"]` |
| amCharts client memory | Grows across tab switches | `chart.dispose()` commented out in `RadarChart.js` line 66 and `LineChart.js` line 70 |

A notable RUM-related discrepancy exists in the frontend: the `web-vitals` package version 1.0.1 is declared in `frontend/package.json` line 17, but `frontend/src/index.js` (a 12-line file) does **not** call `reportWebVitals()`, leaving the dependency unwired. Activating the existing dependency is documented in Section 5.4.6 as a near-zero-cost frontend observability win.

#### 6.5.3.3 Business Metrics

**Not applicable.** This system has no business KPIs to track. The application has no user accounts, no conversion funnel, no revenue events, no engagement metrics, and no editorial content with consumption analytics.

| Business Metric Class | Applicability | Reason |
|---|---|---|
| Daily Active Users (DAU) / MAU | Not applicable | No user identity; no session tracking |
| Conversion / signup rate | Not applicable | No account creation flow |
| Revenue / payment events | Not applicable | No payment surface |
| Feature engagement | Not measured | No analytics SDK; `frontend/public/index.html` contains no tracking snippets |
| Search-query distribution | Not measured | `/api/artist/<name>` queries are not aggregated |
| Chart-week popularity | Not measured | `/api/week/<week>` queries are not aggregated |

Section 3.4.2 confirms that the only third-party browser-loaded resource is Google Fonts; **no analytics tags** (Google Analytics, Segment, Mixpanel) are present in the SPA shell. Were business metrics ever required, the natural seam for capture would be a query-counter against `/api/week`, `/api/analysis`, and `/api/artist`, emitted to a metrics backend through the future-state instrumentation outlined in Section 6.5.2.1.

#### 6.5.3.4 SLA Monitoring

**No SLAs are codified anywhere in the repository** (Section 4.6.2, Section 5.4.5). Without codified SLAs there is nothing to monitor against. The matrix below documents the SLA-relevant primitives and their disposition.

| SLA Primitive | Codified? | Evidence |
|---|---|---|
| Latency targets (p50, p95, p99) | No | No latency targets declared in code or configuration |
| Per-route timeouts | No | `@app.route` decorators have no timeout parameter; Flask itself has no per-route timeout |
| `signal.alarm` / asyncio timeouts in handlers | No | None used in `api/routes.py` or `api/funcs.py` |
| Frontend `AbortController` on `fetch()` | No | Not used in `TracksSection.js` or `TrendsSection.js` |
| Rate limits | No | `flask-limiter` not installed |
| Request body size limits | No | `MAX_CONTENT_LENGTH` not set in `api/__init__.py` |
| Recovery Time Objective (RTO) | No | Not documented in any spec section |
| Recovery Point Objective (RPO) | No | No backup configured (Section 5.4.6) |
| Availability target (e.g., 99.9%) | No | Not documented |
| Error budget | No | No SLO from which to derive a budget |

#### Suggested SLA Baseline (Not Codified, For Future Adoption)

If SLAs were to be introduced as part of a production hardening effort, the matrix below sketches a plausible baseline derived from the observable performance bounds in Section 6.5.3.2. **None of these targets are currently codified** — they are presented solely to give shape to the future-state monitoring path described in Section 6.5.6.

| Indicator | Suggested Target | Rationale |
|---|---|---|
| `/api/week` p95 latency | ≤ 500 ms | ≤100-row response dominated by network overhead |
| `/api/analysis` p95 latency | ≤ 750 ms | ≤~70 rows + Pandas rolling-mean computation |
| `/api/artist` p95 latency | ≤ 2 s | Full-table scan; bound by dataset growth |
| `/api/track/<id>` p95 latency | ≤ 250 ms | Primary-key lookup |
| Availability (monthly) | 99.0% | Single-replica monolith on solo-maintainer host |
| Error rate (5xx / total) | ≤ 1% | Bounded by the six error classes in Section 4.5.2 |

#### 6.5.3.5 Capacity Tracking

**No capacity-tracking instrumentation is configured.** Per Section 6.1.3.5, "no formal capacity plan is codified anywhere in the repository." The capacity envelope is bounded structurally — by the data shape of the Hot 100, by the row counts of `Tracks` and `YearlyAvg`, and by the single-threaded Flask development server — rather than by any dynamic capacity-aware policy.

| Capacity Dimension | Tracked? | Bounding Constraint |
|---|---|---|
| Concurrent in-flight requests | No | Flask dev server admits one at a time |
| SQLAlchemy connection pool utilization | No | Flask-SQLAlchemy defaults; no tuning in `api/__init__.py` |
| PostgreSQL connection count | No | `postgres:15` defaults; `max_connections` unconfigured |
| Container CPU / memory pressure | No | No `mem_limit` / `cpus` / `deploy.resources` in `docker-compose.yml` |
| `./data` bind-mount disk usage | No | No disk-fill alarm; no rotation |
| Frontend heap (amCharts) | No | `chart.dispose()` commented out in both chart components |

The first endpoint expected to require capacity attention as traffic grows is `/api/artist/<name>` — per Section 6.1.3.5, it "is the most expensive query and would be the first candidate for caching if traffic grew."

---

### 6.5.4 Incident Response

#### 6.5.4.1 Alert Routing

**Not applicable: no alert routing exists.** No alerts are generated by the system, so there is no routing to perform. The matrix below documents the disposition of each routing surface.

| Routing Surface | Status | Reason |
|---|---|---|
| Email channel | Not configured | No SMTP client; no recipient list |
| SMS / phone channel | Not configured | No telephony integration |
| Chat channel (Slack, Teams) | Not configured | No webhook URL anywhere in repo |
| Ticketing integration (Jira, ServiceNow) | Not configured | No ticketing client |
| On-call rotation (PagerDuty, OpsGenie, VictorOps) | Not configured | Solo-maintainer model; no rotation |
| Routing rules / silences | Not configured | No alert engine to host the rules |

#### 6.5.4.2 Escalation Procedures

**Not applicable: no escalation procedures are documented.** With a solo-maintainer model and no on-call rotation, there is no second tier to escalate to. Manual operator detection — typically by a user reporting a broken page or by the maintainer noticing during routine checks — is the only path from incident to remediation.

| Escalation Tier | Status | Notes |
|---|---|---|
| L1 (initial responder) | Solo maintainer | No formal acknowledgment SLA |
| L2 (subject-matter expert) | Same person | No separation of duties |
| L3 (engineering owner) | Same person | No separation of duties |
| Executive escalation | Not applicable | No business stakeholder hierarchy |
| Vendor escalation | Not applicable | No managed-service contracts |

#### 6.5.4.3 Runbooks

**No runbooks are checked into the repository.** There is no `runbooks/`, `docs/operations/`, or equivalent folder. Operator knowledge lives implicitly in the README, the Compose file, and the Dockerfile. The implicit recovery procedures derivable from the codebase are listed below as documentation of current operator-known behavior, not as a formal runbook.

| Failure Scenario | Implicit Recovery Procedure | Reference |
|---|---|---|
| `api` container exits non-zero | Compose `restart: on-failure` relaunches automatically | Section 5.4.6 |
| `api` container hung but running | Manual `docker compose restart api` (no healthcheck to detect) | Section 6.1.4.1 |
| `postgres` container exits | Manual `docker compose start postgres` (no restart policy) | Section 5.4.6 |
| `./data` bind-mount corruption | Unrecoverable without external backup; no backup is configured | Section 5.4.6 |
| Host failure | Full re-provisioning; redeploy via `docker compose up` | Section 5.4.6 |
| Database connection lost mid-flight | Next request returns 500; user retries via form re-submit | Section 4.5.4 |
| Invalid feature on `/api/analysis/<feature>` | Frontend `setError(statusText)`; user re-selects via `FeatureSelect` | Section 4.5.2 |

#### 6.5.4.4 Post-Mortem Processes

**Not applicable: no post-mortem process is established.** A post-mortem framework presumes (a) detection of incidents through alerting, (b) a multi-person team to participate in retrospectives, and (c) a tracking system for action items. None of these preconditions are present:

| Post-Mortem Element | Status |
|---|---|
| Incident-tracking system (Jira, Linear) | Not present in repo |
| Post-mortem template | Not present in repo |
| Five-whys / blameless retro practice | Not documented |
| Action-item tracker | Not present |
| Incident timeline reconstruction tooling | Not applicable (no structured logs to reconstruct from) |

#### 6.5.4.5 Improvement Tracking

**Not applicable in operational form**, but the specification itself acts as the improvement backlog. The hardening recommendations enumerated across Sections 5.4.6, 6.1.4.8, and 6.4.6.3 — and reproduced in Section 6.5.6 below — are the closest analog to a tracked improvement queue. No issue tracker, no Kanban board, and no roadmap document is committed to the repository.

#### 6.5.4.6 Incident and Alert Flow Diagram

The diagram below depicts the **actual** incident-flow topology as it exists today, with all dashed paths representing **deliberately absent** alerting capabilities. The diagram makes visible that every failure class except pure `api` process exit terminates in a manual recovery step performed by either the operator or the user.

```mermaid
flowchart TD
    Start([Failure occurs]) --> Class{Failure type?}

    Class -->|api process<br/>exits non-zero| Auto[Compose restart on-failure<br/>relaunches container]
    Class -->|api process hung<br/>but running| NoCheck[No healthcheck configured<br/>no automated recovery]
    Class -->|postgres process exits| NoPolicy[No restart policy<br/>on postgres service]
    Class -->|Backend exception<br/>raised in handler| Five[Flask default 500<br/>no structured body]
    Class -->|Network error<br/>at browser fetch| Stuck[Unhandled promise rejection<br/>UI stuck at isLoaded false]
    Class -->|Data file corruption| NoBackup[No backup configured<br/>data loss]
    Class -->|Host failure| NoHA[No HA<br/>full re-provisioning]

    Auto --> Recovered([Service restored])
    NoCheck --> ManualOp[Operator detects via<br/>user complaint or<br/>routine docker logs]
    NoPolicy --> ManualOp
    NoBackup --> Lost([Data loss])
    NoHA --> Reprov([Re-provision host])
    Stuck --> UserReload[User reloads page]
    Five --> FrontErr[Frontend setError statusText]
    FrontErr --> UserResubmit[User resubmits form]

    ManualOp --> Recovered
    UserReload --> Recovered
    UserResubmit --> Recovered
    Reprov --> Recovered

    subgraph Absent["Deliberately Absent Alert Pipeline"]
        AlertRule[Alert Rule Engine<br/>Alertmanager / Grafana]
        Notify[Notification Channel<br/>PagerDuty / Slack / Email]
        OnCall[On-Call Rotation<br/>L1 / L2 / L3 escalation]
        Postmortem[Post-Mortem Process<br/>blameless retro<br/>action-item tracker]
    end

    Class -. "no rule fires" .-> AlertRule
    AlertRule -. "no channel" .-> Notify
    Notify -. "no rotation" .-> OnCall
    Recovered -. "no retro" .-> Postmortem

    classDef absent stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class AlertRule,Notify,OnCall,Postmortem absent
```

The diagram's principal observations:

- **Auto-recovery is one class of failure only**: the `api` container's `restart: on-failure` policy. Every other failure mode terminates in a manual step.
- **No telemetry feedback edge** exists from any failure class into an alert engine; the failure-to-detection path runs entirely through user complaints or operator habit.
- **Frontend failure modes** — particularly the unhandled promise rejection on network error — leave the UI in an indefinite loading state with no operator-visible indication that anything has gone wrong.

#### Alert Threshold Matrix (Current vs. Suggested Baseline)

The matrix below documents the current state (no thresholds configured) alongside a suggested baseline that would apply if the future-state monitoring path in Section 6.5.6 were implemented. **The "Suggested Threshold" column is not codified in the repository** — it is presented as a forward-looking reference only.

| Indicator | Current Threshold | Suggested Threshold |
|---|---|---|
| `api` container exit (1-min window) | None — silent restart | Page on >1 exit per 5 minutes |
| `postgres` container exit | None — manual recovery | Page on any exit |
| `/healthz` failures (when added) | Endpoint not implemented | Page on 3 consecutive failures (30s interval) |
| HTTP 5xx error rate | Not measured | Warn at >1%, page at >5% over 5 min |
| `/api/artist` p95 latency | Not measured | Warn at >2s, page at >5s over 5 min |
| `/api/week` p95 latency | Not measured | Warn at >500ms, page at >2s over 5 min |
| `./data` bind-mount fill rate | Not measured | Warn at 80%, page at 95% |
| PostgreSQL connection count | Not measured | Warn at 80% of `max_connections` |
| Werkzeug exception traceback rate | Not measured | Warn on any traceback to stderr |

---

### 6.5.5 Operator Surfaces and Dashboards

#### 6.5.5.1 Available Operator Surfaces

The complete inventory of operator-visible state surfaces is shown below. This list is exhaustive — there are no additional dashboards, no hidden management UIs, and no cloud-console views applicable to the deployed system.

| Surface | Access Method | Information Available |
|---|---|---|
| `docker compose ps` | Host shell on the deployment host | Service names, container IDs, port mappings, current state (Up / Exit) |
| `docker logs api` | Host shell | Werkzeug request log + Python tracebacks |
| `docker logs postgres` | Host shell | PostgreSQL server lifecycle and connection events |
| `docker stats` | Host shell | Live CPU / memory / I/O per container (no historical view) |
| Browser DevTools Network tab | Per-user browser | Per-fetch HTTP method, status, response body, timing |
| Browser DevTools Console tab | Per-user browser | Unhandled promise rejections from `fetch()` failures |

Note that the Browser DevTools entries are **per-user surfaces** — each user sees only their own session's requests. There is no operator view that aggregates across all users.

#### 6.5.5.2 Dashboard Layout (Current vs. Recommended)

Because no dashboard infrastructure is configured, the diagram below contrasts the current operator surface (left) with the **recommended future-phase dashboard layout** (right) that would emerge from implementing the hardening sequence in Section 6.5.6. The right-hand panel is **aspirational** — none of its widgets exist today.

```mermaid
flowchart LR
    subgraph Current["Current Operator Surface (Implemented)"]
        T1["Terminal: docker compose ps<br/>service / container / state"]
        T2["Terminal: docker logs api<br/>Werkzeug request lines<br/>Python tracebacks"]
        T3["Terminal: docker logs postgres<br/>server lifecycle messages"]
        T4["Terminal: docker stats<br/>live CPU / memory / IO"]
        T5["Browser DevTools<br/>per-user only<br/>Network + Console"]
    end

    subgraph Future["Recommended Future-Phase Dashboard (Not Implemented)"]
        subgraph Overview["Overview Panel"]
            O1["Service Up/Down<br/>api + postgres"]
            O2["Request Rate<br/>req/s by route"]
            O3["Error Rate<br/>5xx / total"]
        end
        subgraph Latency["Latency Panel"]
            L1["p50 / p95 / p99<br/>per route"]
            L2["DB Query Time<br/>by query class"]
        end
        subgraph Resource["Resource Panel"]
            R1["Container CPU<br/>and Memory"]
            R2["postgres Connections<br/>used / max"]
            R3["./data disk fill"]
        end
        subgraph Frontend["Frontend Panel"]
            F1["web-vitals: LCP / FID / CLS"]
            F2["JS Errors via<br/>error reporting SDK"]
        end
        subgraph Logs["Log Search Panel"]
            G1["Structured log search<br/>by request ID"]
        end
    end

    Current -- "Migration trigger:<br/>internet-facing deployment" --> Future

    classDef future stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class O1,O2,O3,L1,L2,R1,R2,R3,F1,F2,G1 future
```

The recommended layout maps directly to the metrics, logs, and traces produced by the future-state instrumentation in Section 6.5.6: an **Overview Panel** for high-level service health, a **Latency Panel** for the four routes, a **Resource Panel** for capacity tracking, a **Frontend Panel** for activated `web-vitals` and error-reporting telemetry, and a **Log Search Panel** for structured log queries by request correlation ID.

---

### 6.5.6 Recommended Hardening Path

The recommendations below consolidate the monitoring-and-observability hardening callouts from Sections 5.4.6, 6.1.4.8, and 6.4.6.3 into a single sequence ordered by leverage. **None of these items are implemented**; they are reproduced here as the future-state vision for any production-grade deployment of Hot Stuff.

#### 6.5.6.1 Hardening Inventory

| Improvement | Cross-Reference |
|---|---|
| Add `restart: on-failure` to the `postgres` service to symmetrize the recovery policy | Section 5.4.6 |
| Add a `/healthz` endpoint to `api/routes.py` and a Compose `healthcheck:` block on `api` so Docker can detect zombie processes | Section 5.4.6, Section 6.1.4.1 |
| Switch `Dockerfile` `CMD` from `python3 app.py` to `gunicorn` (already pinned in `requirements.txt`) | Section 6.1.2.4 (ADR-006) |
| Adopt JSON-formatted structured logs (e.g., `structlog`) with timestamps and per-request correlation IDs | Section 5.4.2 |
| Forward logs to a central aggregation store (e.g., Fluent Bit → Loki, Vector → cloud sink) | Section 5.4.2 |
| Wire the existing `web-vitals` 1.0.1 dependency by adding a `reportWebVitals(...)` call in `frontend/src/index.js` | Section 6.5.3.2 |
| Wrap frontend `fetch()` calls in `try/catch` and add an `<ErrorBoundary>` to prevent indefinite `isLoaded=false` states | Section 4.5.1, Section 5.4.6 |
| Wire an error-reporting SDK (Sentry / Rollbar / Bugsnag) to capture both backend exceptions and frontend errors | Section 4.5.3 |
| Adopt a Prometheus metrics endpoint (`prometheus-client` + `/metrics` route) once traffic warrants | Section 6.5.2.1 |
| Introduce periodic `pg_dump` or PostgreSQL streaming replication for backup observability | Section 5.4.6 |
| Externalize database credentials via environment variables to permit rotation and enable per-environment routing | Section 6.4.3.2 |

#### 6.5.6.2 Recommended Hardening Sequence

The sequence below is ordered by the cumulative reduction in mean time to detection (MTTD) and mean time to recovery (MTTR). Each step assumes the prior steps are complete.

```mermaid
flowchart LR
    Start([Current Posture<br/>Werkzeug stdout only]) --> H1["1: Add /healthz<br/>plus Compose healthcheck"]
    H1 --> H2["2: Symmetrize postgres<br/>restart: on-failure"]
    H2 --> H3["3: Switch CMD<br/>to gunicorn"]
    H3 --> H4["4: Adopt structlog<br/>plus correlation IDs"]
    H4 --> H5["5: Wire web-vitals<br/>reportWebVitals"]
    H5 --> H6["6: Frontend try/catch<br/>plus ErrorBoundary"]
    H6 --> H7["7: Error reporting SDK<br/>Sentry / Rollbar"]
    H7 --> H8["8: Log shipper<br/>Fluent Bit / Vector"]
    H8 --> H9["9: Prometheus<br/>/metrics endpoint"]
    H9 --> H10["10: Dashboards<br/>plus alert rules"]
    H10 --> H11["11: pg_dump<br/>or replication"]
    H11 --> Production([Production-grade<br/>observability posture])
```

The first four steps (H1 through H4) collectively raise observability from **zero structured signal** to **per-request correlated structured logs with container-level health probes** — a posture sufficient for low-traffic internet-facing deployment. Steps H5 through H8 close the frontend observability gap. Steps H9 and H10 add metrics-driven alerting. Step H11 closes the disaster-recovery loop documented in Section 5.4.6.

---

### 6.5.7 Summary of Non-Applicability

The Monitoring and Observability concerns enumerated in this section's prompt map to the actual codebase as follows:

| Prompt Concern | Status in This System | Driving Reason |
|---|---|---|
| Metrics collection | Absent | No `prometheus-client`; no `/metrics` route |
| Log aggregation | Absent | Docker logging driver default only |
| Distributed tracing | Absent | No OpenTelemetry / Jaeger / Zipkin client |
| Alert management | Absent | No alert engine, no notification channel |
| Dashboard design | Absent | No Grafana / Kibana / vendor UI |
| Health checks | Not implemented | No `/healthz`, no Compose `healthcheck:`, no `HEALTHCHECK` |
| Performance metrics | Not measured | Bounds observable from code structure only |
| Business metrics | Not applicable | No KPIs; no analytics SDK |
| SLA monitoring | No SLAs codified | Solo-maintainer; no error budget |
| Capacity tracking | Not measured | Structural bounds only |
| Alert routing | Absent | No alert source to route |
| Escalation procedures | Not documented | Solo-maintainer; no rotation |
| Runbooks | Not committed | Operator knowledge implicit in README + Compose |
| Post-mortem processes | Not established | Preconditions absent |
| Improvement tracking | Specification serves as backlog | No issue tracker in repo |

The system instead relies on a small set of **basic monitoring practices** — Werkzeug's default request log on stdout, PostgreSQL's image-default logs, the Docker engine's default logging driver, Compose's `restart: on-failure` policy on the `api` service, and Python tracebacks to stderr — that together provide a development-grade visibility floor sufficient for the system's actual deployment context. The full hardening path required for production-grade observability is sketched in Section 6.5.6 and cross-referenced to the originating recommendations in Sections 5.4.6, 6.1.4.8, and 6.4.6.3.

---

### 6.5.8 References

#### Files Examined

- `docker-compose.yml` — Two-service Compose definition; verified absence of `healthcheck:` blocks on either service; verified `restart: on-failure` on `api` only (no policy on `postgres`); verified absence of monitoring services (Prometheus, Grafana, Loki, Fluent Bit).
- `Dockerfile` — Single-stage image build; verified `CMD ["python3", "app.py"]` (Flask dev server, not `gunicorn`); verified absence of `HEALTHCHECK` instruction.
- `requirements.txt` — 23 pinned Python dependencies; verified absence of `prometheus-client`, `opentelemetry-*`, `sentry-sdk`, `structlog`, `loguru`, `python-json-logger`, `flask-limiter`, `tenacity`, `backoff`, `pybreaker`, and `flask-caching`.
- `app.py` — Trivial entry point invoking `app.run(host='0.0.0.0')`; no monitoring instrumentation.
- `api/__init__.py` — 22-line Flask bootstrap; verified absence of `import logging`, `app.logger`, `getLogger`, or `setLevel` calls; verified no `os.environ` usage.
- `api/routes.py` — 70-line module with six `GET` route handlers; verified absence of `try/except`, logging calls, `/healthz`, `/readyz`, `/health`, `/status`, `/ping`, and `/metrics` endpoints.
- `api/funcs.py` — Aggregation helpers; verified absence of monitoring-related instrumentation; contains the only timing-sensitive constraint codified in code (chart-week boundary at 10:00 AM Wednesday in `get_query_week`).
- `api/models.py` — `Tracks` and `YearlyAvg` ORM models plus Marshmallow schemas; no audit columns, no `audit_log` table.
- `frontend/package.json` — Frontend dependency manifest; verified `web-vitals: ^1.0.1` declared on line 17 but never imported; verified absence of Sentry browser SDK, analytics packages, and OpenTelemetry browser SDK.
- `frontend/src/index.js` — 12-line React entry; verified absence of `reportWebVitals(...)` call despite the package being available.
- `frontend/src/App.js` — 67-line tab-based UI shell; verified absence of monitoring instrumentation, `componentDidCatch`, and `<ErrorBoundary>` wrapper.
- `frontend/public/index.html` — 17-line SPA shell; verified absence of analytics tags, Sentry init script, and any monitoring snippets; only third-party resource is Google Fonts.
- `.dockerignore` — Build-context exclusions; relevant to verifying that no monitoring config files were excluded by accident.
- `.flaskenv` — Flask environment settings (`FLASK_APP=app.py`, `FLASK_ENV=development`); no monitoring-related variables.
- `README.md` — Project documentation; verified absence of monitoring or observability references.

#### Folders Examined

- `/` (repository root) — Top-level Compose, Dockerfile, `app.py`, `requirements.txt`, `README.md`, `.dockerignore`, `.flaskenv`, `.gitignore`, `api/`, `frontend/`.
- `api/` — Backend Flask package (`__init__.py`, `routes.py`, `models.py`, `funcs.py`); no `monitoring/`, `instrumentation/`, or equivalent submodules.
- `frontend/` — Frontend root (`package.json`, `package-lock.json`, `src/`, `public/`, `build/`); no `analytics/`, `monitoring/`, or telemetry subdirectories.
- `frontend/src/` — React source (`App.js`, `index.js`, `components/`, `styles/`); no monitoring wrappers or error boundaries.
- `frontend/public/` — SPA shell (`index.html`, `manifest.json`); no analytics or monitoring snippets.

#### Cross-Referenced Technical Specification Sections

- **Section 1.3 SCOPE** — Section 1.3.3 explicitly lists "Observability (logging, metrics, tracing)" in the Out-of-Scope Elements with the evidence "No structured logging, no metrics endpoint, no APM agent."
- **Section 3.4 THIRD-PARTY SERVICES** — Section 3.4.4 (Monitoring and Observability Tools) confirms the disposition is "None" and enumerates absences of structured logging, metrics, APM, error reporting, and RUM wiring.
- **Section 4.5 ERROR HANDLING FLOWS** — Frontend error state machine (4.5.1), backend error behaviors (4.5.2), retry/fallback posture (4.5.3), and container-level recovery (4.5.4) — all of which inform the absent alerting flow.
- **Section 4.6 TIMING AND SLA CONSIDERATIONS** — Section 4.6.2 confirms "No SLAs are codified anywhere in the repository," directly motivating the SLA Monitoring sub-area's non-applicability.
- **Section 5.3 TECHNICAL DECISIONS** — ADR-001 (Single-Process SPA + API), ADR-004 (No Caching Tier), and ADR-006 (Flask Dev Server in Production) collectively establish the development-grade operational posture.
- **Section 5.4 CROSS-CUTTING CONCERNS** — Section 5.4.1 (Monitoring and Observability Approach), Section 5.4.2 (Logging and Tracing Strategy), Section 5.4.5 (Performance Requirements and SLAs), and Section 5.4.6 (Disaster Recovery Procedures) are the primary upstream sources for this section.
- **Section 6.1 Core Services Architecture** — Section 6.1.3.5 (Capacity Planning Guidelines), Section 6.1.4.1 (Fault Tolerance Mechanisms), and Section 6.1.4.8 (Recommended Hardening) supply the resilience-pattern context underlying the alert flow and capacity-tracking discussions.
- **Section 6.2 Database Design** — Section 6.2.4.4 (Audit Mechanisms) confirms the absence of `pgaudit`, change-tracking triggers, and `audit_log` tables.
- **Section 6.4 Security Architecture** — Section 6.4.5.2 (Audit Logging) confirms the only audit trail is the Werkzeug stdout request log; Section 6.4.6.3 (Known Security Limitations) supplies the structured-logging hardening recommendation cross-referenced here.

## 6.6 Testing Strategy

### 6.6.1 Applicability Assessment

#### 6.6.1.1 Non-Applicability Statement

**Detailed Testing Strategy is not applicable for this system.**

Hot Stuff is a deliberately minimal, two-tier monolithic web application — a single Flask process serving a compiled React Single-Page Application alongside a sibling PostgreSQL 15 container. The repository contains **no automated tests of any kind**: no `tests/` directory, no `pytest` configuration, no `conftest.py`, no `*.test.js` or `*.spec.js` files, no CI/CD pipeline to execute tests against, and no test fixtures or factories. Section 1.3.3 (Out-of-Scope Elements) explicitly catalogs **"Automated tests"** as an excluded capability, with the supporting evidence "No `tests/` directory, no `pytest` configuration, no test files in retrieved folders." Section 3.6.7 (Testing) confirms the disposition in a single phrase: **"Not present."** Section 2.5.2 (Requirement-to-Acceptance Traceability) records that "the repository does not include automated tests" and that "all test strategies above are therefore manual; introducing automated tests would be a future-phase undertaking."

This section therefore (a) records the **rationale** for the absent posture, (b) catalogs the **basic verification practices that ARE in effect** despite the absence of a test framework, (c) documents each prompt sub-area as non-applicable with file-level evidence, (d) provides the three required Mermaid diagrams to make the absent layers explicit, and (e) documents the **recommended future-phase testing path** for any production-grade hardening of the codebase.

#### 6.6.1.2 Justification for the Minimal Posture

Eight structural properties of the system make a comprehensive automated testing framework unnecessary at the current scope. These properties are direct downstream consequences of the architecture decisions recorded as ADR-001 through ADR-006 in Section 5.3.6.

| Property | Implication for Testing Posture |
|---|---|
| Solo-maintainer operational model (footer marker `AUG \| 2021`) | No team-coordination cost from broken builds; manual verification by the maintainer suffices |
| Public-read-only dataset (Billboard chart positions + Spotify-derived audio features) | No correctness invariants tied to user state; no transactional integrity to verify; no PII-driven privacy testing |
| Two-tier monolithic architecture (one `api` container + one `postgres` container) | No service-contract testing across boundaries; no integration-test orchestration is needed |
| Read-only HTTP `GET` API with bounded result sizes | No mutation-test surface; no idempotency tests; no concurrency tests required |
| Uniform 500 on backend exception (no graceful degradation, no retry, no circuit breaker) | No retry/fallback to verify; no resilience assertions to author |
| No SLAs codified anywhere in the repository (per Section 4.6.2) | No performance-test thresholds to enforce |
| No CI/CD pipeline (per Section 3.6.5) | No infrastructure to host or trigger automated tests |
| No production deployment (Flask dev server in all environments per ADR-006) | Test maturity is appropriately matched to deployment maturity |

The non-applicability is **deliberate**, not an oversight. ADR-001 (Single-Process SPA + API), ADR-004 (No Caching Tier), and ADR-006 (Flask Dev Server in Production) — all recorded in Section 5.3.6 — collectively establish the system as a development-grade deployment whose operational sophistication is intentionally bounded. The absence of automated testing is a downstream consequence of these decisions.

#### 6.6.1.3 Basic Verification Practices Currently In Effect

The deployed system does have a small set of verification surfaces that arise from default behaviors of the toolchain plus deliberate maintainer choices. These are the **only** quality-assurance practices currently followed, and they form the de facto testing strategy of the codebase:

| Practice | Implementation | Captured Information |
|---|---|---|
| Static analysis (frontend) | ESLint via `react-scripts` 4.0.3 with `eslintConfig` extending `react-app`, `react-app/jest` | Lint findings surface during `react-scripts start` and `react-scripts build` |
| Dependency pinning (backend) | All 23 entries in `requirements.txt` use `==` exact pinning | Eliminates "works on my machine" drift; provides build reproducibility |
| Dependency pinning (frontend) | `react-scripts` exact-pinned at `4.0.3`; other packages use caret `^` ranges with `package-lock.json` | Reproducible install tree for the SPA build |
| Build-time gating | `react-scripts build` fails the build on ESLint errors and TypeScript-style import errors | Compile-time verification before image promotion |
| Container smoke test | `docker compose up` is the operator's first verification step (per Section 2.5.2 F-016) | Confirms both services start and the SPA loads |
| Manual HTTP probes | `curl` against the six routes in `api/routes.py` (per Section 2.5.2 F-001 to F-006, F-017) | Confirms request/response shape per requirement |
| Manual UI inspection | Browser DevTools Network and Console tabs (per Section 6.5.5.1) | Confirms front-end renders, fetches succeed, no unhandled rejections |

These surfaces collectively constitute the system's **manual verification floor**. They are sufficient for the actual deployment context (a single maintainer, no CI/CD, no production exposure) but provide no automated regression detection if the maintainer omits a verification step.

---

### 6.6.2 Testing Approach

Each sub-area below corresponds to one of the prompt's Testing Approach concerns. In every case, the disposition is **non-applicable** for the current codebase, with file-level evidence supporting that designation.

#### 6.6.2.1 Unit Testing

**Not applicable.** No unit tests exist in the repository. Although the frontend declares the Create React App default Testing Library stack, no test files have ever been authored to consume those libraries.

#### Backend Unit Test Disposition

| Capability | Status | Verification Evidence |
|---|---|---|
| Test framework | Absent | No `pytest`, `unittest2`, `nose`, or `tox` in `requirements.txt` (23 packages) |
| Test runner configuration | Absent | No `pytest.ini`, `setup.cfg`, `tox.ini`, or `pyproject.toml` test section |
| Test discovery directory | Absent | No `tests/`, `test/`, or `api/tests/` folders |
| Fixture / factory libraries | Absent | No `factory_boy`, `faker`, `freezegun`, `responses`, `vcr.py`, or `pytest-mock` |
| Coverage tool | Absent | No `pytest-cov` or `coverage.py` in `requirements.txt` |
| Mocking strategy | None codified | No `unittest.mock` usage anywhere; no mock objects in source tree |

Per Section 3.6.7: "The backend has no test framework declared (no `pytest`, no `unittest` configuration, no `tests/` directory)."

#### Frontend Unit Test Disposition

| Capability | Status | Verification Evidence |
|---|---|---|
| `@testing-library/jest-dom` | Declared but unused | Listed in `frontend/package.json` at `^5.11.4`; no source file imports it |
| `@testing-library/react` | Declared but unused | Listed in `frontend/package.json` at `^11.1.0`; no source file imports it |
| `@testing-library/user-event` | Declared but unused | Listed in `frontend/package.json` at `^12.1.10`; no source file imports it |
| Jest (transitive via `react-scripts`) | Declared but unused | Bundled inside CRA 4.0.3; no Jest configuration override exists |
| Test files | Absent | No `__tests__/` directories, no `*.test.js`, no `*.test.jsx`, no `*.spec.js`, no `*.spec.jsx` files anywhere in `frontend/src/` |
| Test setup | Absent | No `setupTests.js`, no `jest.config.js`, no `setupFilesAfterEach.js` |
| `test` script behavior | Configured but empty | `"test": "react-scripts test"` invokes Jest, which finds no test files to execute |

Per Section 3.2.2 (Test Tooling — Declared, No Tests Present): "Although these libraries are declared, no test files exist anywhere in `frontend/src/`."

#### Test Organization, Naming, Coverage, and Data Management

Because no tests exist, none of the prompt's structural concerns are codified:

| Concern | Status | Notes |
|---|---|---|
| Test organization structure | Not codified | No directory layout, no module-mirror convention |
| Test naming conventions | Not codified | No `test_<thing>.py` or `<Component>.test.js` pattern in use |
| Code coverage requirements | Not codified | No coverage tool installed; no threshold target |
| Test data management | Not codified | No fixtures directory, no JSON snapshots, no test database seeders |
| Mocking strategy | Not codified | No `mock`, `responses`, `nock`, `MSW`, or `jest.fn()` usage |

#### 6.6.2.2 Integration Testing

**Not applicable.** No integration tests exist. The system is a two-container monolith with exactly one inter-tier hop (Flask → PostgreSQL via `psycopg2`); per Section 6.1.2.2, "no inter-service communication exists" beyond that single boundary, so the conventional notion of service-integration testing has nothing to integrate.

| Capability | Status | Verification Evidence |
|---|---|---|
| API testing harness | Absent | No `pytest-flask`, no `requests`-based test module, no `httpx` test client |
| Database integration tests | Absent | No SQLite-in-memory fixture; no `pytest` PostgreSQL container fixture |
| Service mocking | Absent | No mock for `psycopg2`, no in-memory Flask test client invocations |
| External service mocking | Not applicable | No external services to mock — Section 3.4 confirms zero third-party SDKs in `requirements.txt` |
| Contract / schema tests | Absent | No JSON Schema validation, no Schemathesis, no Pact harness |
| Test environment management | Not codified | The "test environment" is the same `docker compose up` stack as production |

The only integration-style activity currently performed is the **container smoke test** documented in Section 2.5.2 for requirement F-016: an operator runs `docker compose up`, observes both services reach `Up` state, and probes `http://localhost:80/`. This is performed manually with no scripting and no automated assertion.

#### 6.6.2.3 End-to-End Testing

**Not applicable.** No E2E test infrastructure exists in the repository.

| Capability | Status | Verification Evidence |
|---|---|---|
| Cypress | Absent | Not declared in `frontend/package.json`; no `cypress.json` or `cypress/` directory |
| Playwright | Absent | Not declared in `frontend/package.json`; no `playwright.config.js` |
| Selenium / WebDriverIO | Absent | Not declared anywhere |
| Puppeteer / TestCafe | Absent | Not declared anywhere |
| E2E test directories | Absent | No `e2e/`, `integration/`, or `acceptance/` folders at any depth |
| UI automation scripts | Absent | No headless-browser scripts in root, `frontend/`, or `frontend/src/` |
| Test data setup / teardown | Not applicable | No automation harness to host setup/teardown hooks |
| Performance testing | Not applicable | No SLAs codified (Section 4.6.2); no `k6`, `locust`, `JMeter`, or `wrk` artifacts |
| Cross-browser testing | Not codified | `frontend/package.json` `browserslist` declares production targets (`>0.2%, not dead, not op_mini all`), but no automated cross-browser harness consumes that list |
| Accessibility testing | Not codified | No `axe-core`, no `pa11y`, no `eslint-plugin-jsx-a11y` overrides beyond CRA defaults |

The only E2E-style activity currently performed is the **manual UI inspection** documented in Section 2.5.2 for requirements F-007 through F-012: an operator opens the SPA in a browser, exercises the three tabs (Tracks / Trends / About), and visually confirms that the radar chart, line chart, and tab navigation render as expected. This is performed manually with no scripting and no screenshot-comparison assertion.

#### 6.6.2.4 Current Testing Architecture Diagram

The diagram below depicts the **actual** testing topology — verification paths through the system and the only automated quality-assurance signal that is emitted (ESLint at build time). Items shown with dashed borders are the **deliberately absent** testing layers documented in Sections 6.6.2.1 through 6.6.2.3.

```mermaid
flowchart TB
    Maintainer([Solo Maintainer])

    subgraph Workflow["Current Verification Workflow"]
        Edit["Source Edit<br/>api/ or frontend/src/"]
        Build["react-scripts build<br/>ESLint + bundle"]
        Compose["docker compose up<br/>both services"]
        Probe["Manual HTTP curl<br/>+ browser inspection"]

        Edit --> Build
        Build --> Compose
        Compose --> Probe
    end

    subgraph Signals["Automated Signals Emitted"]
        Lint["ESLint findings<br/>react-app + react-app/jest preset<br/>build-time only"]
        Pip["pip3 install -r requirements.txt<br/>resolution success<br/>build-time only"]
        Werk["Werkzeug request log<br/>per HTTP probe<br/>method, path, status"]
        Trace["Python traceback to stderr<br/>on uncaught exception"]
    end

    Build --> Lint
    Build --> Pip
    Probe --> Werk
    Probe --> Trace

    subgraph Absent["Deliberately Absent Test Layers (per Sections 1.3.3, 3.6.7)"]
        Pytest["Backend Unit Tests<br/>pytest / pytest-flask<br/>pytest-cov"]
        Jest["Frontend Unit Tests<br/>Jest + Testing Library<br/>declared but unused"]
        Integ["Integration Tests<br/>API + DB harness"]
        E2E["E2E Tests<br/>Cypress / Playwright"]
        Perf["Performance Tests<br/>k6 / locust / JMeter"]
        CI["CI Runner<br/>GitHub Actions / etc."]
        Cov["Coverage Report<br/>HTML / Codecov"]
        Reg["Regression Detection<br/>baseline + diff"]
    end

    Edit -. "no pre-commit hook" .-> Pytest
    Edit -. "no test discovery" .-> Jest
    Build -. "no test stage" .-> Integ
    Build -. "no test stage" .-> E2E
    Compose -. "no load harness" .-> Perf
    Workflow -. "no pipeline" .-> CI
    Pytest -. "no instrumentation" .-> Cov
    Jest -. "no instrumentation" .-> Cov
    Maintainer -. "no automated alarm" .-> Reg

    Maintainer --> Edit
    Werk --> Maintainer
    Trace --> Maintainer
    Lint --> Maintainer

    classDef absent stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class Pytest,Jest,Integ,E2E,Perf,CI,Cov,Reg absent
```

The principal architectural observations:

- The **only** automated quality signal emitted at build time is ESLint output from `react-scripts build`. There is no equivalent backend gate (no `flake8`, no `pylint`, no `mypy`, no `ruff` is declared in `requirements.txt`).
- The eight dashed layers correspond to the absences enumerated in Sections 6.6.2.1 through 6.6.2.3 and Section 6.6.3.
- The diagram contains **no feedback edge** from a test pass/fail signal back to the workflow — there is no regression alarm, no failing-build gate, and no mandatory verification step before deployment.

---

### 6.6.3 Test Automation

Each sub-area below documents the disposition of an automation concern. Because no tests exist, every concern is either **non-applicable** or **not codified**, with file-level evidence supporting each designation.

#### 6.6.3.1 CI/CD Integration

**Not applicable.** No CI/CD provider configuration exists in the repository. Per Section 3.6.5:

| CI/CD Provider | Expected Path | Status |
|---|---|---|
| GitHub Actions | `.github/workflows/` | Not present |
| GitLab CI | `.gitlab-ci.yml` | Not present |
| Travis CI | `.travis.yml` | Not present |
| CircleCI | `.circleci/config.yml` | Not present |
| Jenkins | `Jenkinsfile` | Not present |

Section 1.3.3 explicitly lists "CI/CD pipelines" as an out-of-scope item with the evidence "No `.github/`, `.gitlab-ci.yml`, or equivalent configuration files." Deployment is performed manually via `docker compose up` against a target host.

#### 6.6.3.2 Automated Test Triggers

**Not applicable: no triggers exist because no tests exist.** The matrix below documents the trigger surfaces that would normally apply and their current disposition.

| Trigger Surface | Status | Evidence |
|---|---|---|
| `pre-commit` hooks | Not configured | No `.pre-commit-config.yaml`; `pre-commit` not declared as a dependency |
| `pre-push` hooks | Not configured | No `.husky/`, no `husky` declared in `frontend/package.json` |
| Push-to-branch trigger | Not configured | No CI provider to host the trigger (Section 3.6.5) |
| Pull-request trigger | Not configured | No CI provider to host the trigger |
| Scheduled (cron) test runs | Not configured | No CI provider to host scheduling |
| Tag / release trigger | Not configured | No CI provider; no release process documented |

#### 6.6.3.3 Parallel Test Execution

**Not applicable.** With zero tests in the repository, parallelization is not a meaningful concern. The matrix below documents the absent primitives for completeness.

| Capability | Status | Notes |
|---|---|---|
| `pytest-xdist` | Absent | Not declared in `requirements.txt` |
| Jest `--maxWorkers` | Default if invoked | `react-scripts test` defaults to `os.cpus().length - 1`, but finds no tests to execute |
| Sharding strategy | Not applicable | No CI runner; no shard partitioning mechanism |
| Test isolation primitives | Not applicable | No tests; no shared-state contention to manage |

#### 6.6.3.4 Test Reporting Requirements

**Not applicable.** No test reporting infrastructure exists, and no reporting requirement is codified.

| Reporting Surface | Status | Evidence |
|---|---|---|
| JUnit XML output | Not produced | No `pytest --junitxml`; no `jest --reporters=jest-junit` |
| HTML coverage report | Not produced | No `pytest-cov`, no `--coverage` invocation |
| Coverage upload (Codecov, Coveralls) | Not configured | No CI provider to perform upload; no coverage badge in `README.md` |
| Test result dashboards | Not configured | No CI provider to host result history |
| Console / TTY output | Default if invoked | `react-scripts test` would print the standard Jest banner with zero tests collected |

#### 6.6.3.5 Failed Test Handling

**Not applicable.** With no tests to fail, no failure-handling policy is codified. The matrix below documents the analogous concerns and their disposition.

| Concern | Status | Notes |
|---|---|---|
| Build-fail-on-test-failure gate | Not applicable | No tests; build does fail on ESLint errors during `react-scripts build` |
| Notification on failure (Slack, email) | Not configured | No CI provider to host notifications; no webhook URL in repo |
| Auto-retry on transient failure | Not applicable | No test framework to retry |
| Failure quarantine workflow | Not applicable | No tests to quarantine |
| Bisect / blame tooling | Not applicable | No CI history to bisect across |

#### 6.6.3.6 Flaky Test Management

**Not applicable.** With no tests in the repository, there are no flaky tests to manage. Per the "Solo-maintainer operational model" property in Section 6.6.1.2, even if tests existed, no team-coordination cost from flake-induced false alarms would apply. The matrix below documents the standard primitives for completeness.

| Primitive | Status |
|---|---|
| Test retry strategy (`pytest-rerunfailures`, `jest.retryTimes`) | Not configured |
| Flake-detection tooling | Not configured |
| Quarantine / skip mechanism | Not applicable |
| Determinism enforcement (frozen time, seeded RNG) | Not applicable |

---

### 6.6.4 Quality Metrics

#### 6.6.4.1 Code Coverage Targets

**No coverage targets are codified.** No coverage tool is installed, and no coverage threshold is asserted anywhere in the repository.

| Coverage Dimension | Status | Evidence |
|---|---|---|
| Backend statement coverage | Not measured | `pytest-cov` / `coverage.py` not in `requirements.txt` |
| Backend branch coverage | Not measured | Same as above |
| Frontend line coverage | Not measured | No Jest `--coverage` invocation; `react-scripts test --coverage` never run as part of any documented workflow |
| Frontend branch coverage | Not measured | Same as above |
| Coverage delta gate | Not configured | No CI provider; no codecov / coveralls configuration |
| Per-file coverage threshold | Not configured | No `.coveragerc`; no `coverageThreshold` in any Jest config |

#### 6.6.4.2 Test Success Rate Requirements

**Not applicable.** With zero tests, there is no success rate to compute. No quality bar of the form "tests must pass at X%" is codified anywhere in the repository.

#### 6.6.4.3 Performance Test Thresholds

**Not applicable.** Per Section 4.6.2: "There are **no SLAs codified anywhere in the repository**" — no latency targets in code or configuration, no timeout values on Flask routes, no `signal.alarm` or asyncio timeouts, no `AbortController` on frontend fetches, no rate limits, and no `MAX_CONTENT_LENGTH` body-size limit. Without codified SLAs, there are no thresholds against which a performance test could assert pass/fail. The performance bounds documented in Section 6.5.3.2 are **observable from the code structure** but are **not measured** at runtime.

#### 6.6.4.4 Quality Gates

The matrix below documents every gating mechanism currently in effect across the repository. Note that all gates are **build-time** rather than test-time, and only one of them — ESLint — performs any form of behavioral analysis.

| Gate | Trigger | Failure Behavior |
|---|---|---|
| Pip dependency resolution | `pip3 install -r requirements.txt` during `docker build` | Image build fails if any `==` pin cannot be satisfied |
| Webpack production build | `react-scripts build` | Build fails on syntax errors or unresolved imports |
| ESLint (frontend) | Implicit during `react-scripts start` and `react-scripts build` | Build fails on ESLint errors; warnings are non-blocking |
| Container smoke (manual) | `docker compose up` by operator | Operator-visible if either service exits |
| HTTP probe (manual) | `curl` by operator | Operator-visible status code mismatch |

Critically absent gating mechanisms — none of which are configured — include: type checking (no `mypy`, no TypeScript), backend linting (no `flake8`, no `pylint`, no `ruff`), security scanning (no `bandit`, no `safety`, no `npm audit` enforcement, no Dependabot configuration), and license compliance scanning (no `pip-licenses`, no `license-checker`).

#### 6.6.4.5 Documentation Requirements

**No test documentation requirements are codified.** Because no tests exist, there is no test-documentation convention to enforce. The closest existing artifact is the **manual test strategy column** in Section 2.5.2's Requirement-to-Acceptance Traceability table, which documents the manual verification approach for each of the 17 features (F-001 through F-017). That table — reproduced as the Manual Verification Reference in Section 6.6.6 — is the de facto test plan for the system.

---

### 6.6.5 Test Environment Architecture and Data Flow

#### 6.6.5.1 Test Environment Topology

There is no separate test environment in the repository. The diagram below depicts the **single-environment reality** — the `docker compose up` stack used for development is identical to the stack an operator would manually verify against, and (per ADR-006 Flask Dev Server in Production) is also the same stack used in any deployed instance.

```mermaid
flowchart TB
    subgraph Single["Single Environment Reality (Current State)"]
        subgraph Host["Docker Host"]
            subgraph Compose["Compose Bridge Network"]
                Api["api service<br/>port 80 to 5000<br/>Flask 2.0.1 dev server<br/>build context: . (live bind-mount)"]
                Pg["postgres service<br/>port 5432 to 5432<br/>postgres:15<br/>./data bind-mount"]
                Api -- "psycopg2 over TCP 5432" --> Pg
            end
        end
        Operator([Solo Maintainer]) -- "docker compose up<br/>curl probes<br/>browser inspection" --> Api
    end

    subgraph Future["Recommended Future-Phase Environments (Not Implemented)"]
        subgraph DevEnv["Development Environment"]
            DevApi["api: live-reload"]
            DevPg["postgres: ephemeral"]
        end
        subgraph CIEnv["CI Test Environment"]
            CIApi["api: pytest harness"]
            CIPg["postgres: test DB<br/>fixtures + seeders"]
            CIRunner["Test runner<br/>GitHub Actions"]
        end
        subgraph StagingEnv["Staging Environment"]
            StagingApi["api: gunicorn"]
            StagingPg["postgres: snapshot from prod"]
        end
        subgraph ProdEnv["Production Environment"]
            ProdApi["api: gunicorn behind TLS proxy"]
            ProdPg["postgres: with backups"]
        end
    end

    Single -- "Migration trigger:<br/>introduction of automated tests<br/>+ adoption of CI provider" --> Future

    classDef future stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class DevApi,DevPg,CIApi,CIPg,CIRunner,StagingApi,StagingPg,ProdApi,ProdPg future
```

The critical observations:

- The current single-environment topology has no test isolation, no test fixtures, no seeded test database, and no environment-variable distinction between dev/test/staging/prod — the connection string `postgresql://postgres:postgres@postgres/db` is hardcoded in `api/__init__.py` per Section 6.4.3.2.
- The `./data:/data` bind-mount is the **single source of database state**; any test that mutated rows would mutate the same data the operator probes manually. This structurally precludes destructive testing without a separate test database.
- The right-hand panel sketches the future-state environment topology that would emerge from implementing the hardening sequence in Section 6.6.7.

#### 6.6.5.2 Test Data Flow

The diagram below depicts the **actual** test data flow — which is identical to the production data flow, because no test data exists. The single source of data is the real PostgreSQL database populated by the out-of-repository scraper described in Section 1.3.1.

```mermaid
flowchart LR
    subgraph External["Out-of-Repository Pipeline"]
        Scraper["Billboard scraper +<br/>Spotipy enrichment<br/>(weekly cadence)"]
    end

    subgraph Real["Real Data Path (Current State - Only Path)"]
        DB[("PostgreSQL 15<br/>tracks + yearly_avg<br/>real data")]
        Flask["Flask api process<br/>routes.py + funcs.py"]
        Browser["Browser DevTools<br/>+ curl"]
        Operator([Maintainer<br/>manual inspection])

        Scraper -. "INSERT to tracks<br/>rebuild yearly_avg" .-> DB
        DB -- "SELECT via SQLAlchemy<br/>parameterized queries" --> Flask
        Flask -- "JSON response<br/>via Marshmallow dump" --> Browser
        Browser --> Operator
    end

    subgraph Synthetic["Synthetic Test Data Path (Not Implemented)"]
        Fixtures["Test Fixtures<br/>JSON / SQL seeders"]
        Factories["Factory Boy /<br/>faker generators"]
        TestDB[("Test PostgreSQL<br/>or SQLite in-memory")]
        Mock["fetch mocks<br/>MSW / jest.fn()"]
        Assert["pytest assertions<br/>+ Jest matchers"]

        Fixtures -.-> TestDB
        Factories -.-> TestDB
        TestDB -.-> Flask
        Mock -.-> Browser
        Browser -.-> Assert
    end

    classDef absent stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class Fixtures,Factories,TestDB,Mock,Assert absent
```

The critical observations:

- There is **no synthetic test data**: no `conftest.py` factory fixtures, no JSON snapshots in a `fixtures/` folder, no SQL seed files, no Marshmallow `load()` paths that would consume test payloads (per Section 6.4.6.1, Marshmallow is used in `dump()`-only mode).
- There is **no test database**: the system uses the same PostgreSQL instance for all activities, and the `./data` bind-mount makes that state durable across container restarts.
- There is **no fetch mocking on the frontend**: the `fetch()` calls in `TracksSection.js` and `TrendsSection.js` always go to the real backend, and the only way to exercise their behavior is to point them at a real (or stubbed) Flask process.
- The right-hand panel sketches the synthetic test-data infrastructure that would emerge from implementing the future-phase testing path in Section 6.6.7.

---

### 6.6.6 Manual Verification Reference

The following matrices reproduce — and operationalize — the manual test strategies recorded in Section 2.5.2. They serve as the **de facto test plan** for the system in the absence of automated tests.

#### 6.6.6.1 Backend Manual Verification Patterns

The six routes in `api/routes.py` are verified by direct HTTP probes against a running `docker compose up` stack on the operator's host. Each pattern below corresponds to one or more requirements from Section 2.5.1.

| Feature | Probe Target | Expected Outcome |
|---|---|---|
| F-001 SPA delivery | `GET http://localhost:80/` | 200 with `index.html` from `frontend/build/` |
| F-002 API root redirect | `GET http://localhost:80/api/` (redirect-follow disabled) | 302 to current-week URL |
| F-003 Track lookup | `GET http://localhost:80/api/track/<spotify_id>` | 200 with JSON track object or `[]` for unknown ID |
| F-004 Weekly snapshot | `GET http://localhost:80/api/week/2021-11-13` | 200 with `{week, songs, averages, avgTempo}` |
| F-005 Artist search | `GET http://localhost:80/api/artist/elvis` (mixed-case input) | 200 with case-insensitive matching results |
| F-006 Feature analysis | `GET http://localhost:80/api/analysis/tempo` | 200 with annual + rolling-mean array |
| F-017 CORS | `OPTIONS http://localhost:80/api/week/2021-11-13` | Permissive CORS headers per `CORS(app)` registration |

#### 6.6.6.2 Frontend Manual Verification Patterns

The frontend features are verified by manual UI inspection against the SPA delivered at `http://localhost:80/`, with cross-checks performed in the browser DevTools panes.

| Feature | Verification Step | Expected Outcome |
|---|---|---|
| F-007 Tab navigation | Click each of three tabs (Tracks, Trends, About) | Section content swaps; `activeTab` state updates |
| F-008 Tracks UI | Open Tracks tab; verify ranked list and DatePicker | Rendered list of ≤100 entries; date input bounded `1958-07-27` to `2021-11-13` |
| F-009 Trends UI | Open Trends tab; select feature in `FeatureSelect` | Line chart renders with annual values + rolling mean |
| F-010 About page | Open About tab | Static methodology content renders |
| F-011 Radar chart | Open Tracks tab; inspect `#radialChart` DOM node | Five-axis radar chart populated by `RadarColumnSeries` |
| F-012 Line chart | Open Trends tab; inspect `#featureChart` DOM node | XY line chart with `LineSeries` for raw + rolling values |

#### 6.6.6.3 Function-Level Backend Verification Patterns

The three pure-function helpers in `api/funcs.py` are the strongest candidates for future-phase unit testing because they are deterministic and have no I/O dependencies. They are currently verified informally during interactive Python REPL sessions.

| Feature | Helper | Manual Verification Approach |
|---|---|---|
| F-013 Date normalization | `get_query_week(date)` | Invoke with date inputs spanning the 10:00 AM Wednesday boundary; verify Saturday alignment |
| F-014 Rolling average | `get_rolling_avg(df, feature)` | Invoke with synthetic Pandas DataFrames; verify `.rolling(5).mean()` semantics |
| F-015 ORM models | `Tracks` / `YearlyAvg` `dump()` | Database-level CRUD probe via SQLAlchemy session; invoke `tracks_schema.dump()` |

#### 6.6.6.4 Container Smoke Test Pattern

Per Section 2.5.2 F-016, the deployment unit is verified end-to-end by:

| Step | Command | Verification Criterion |
|---|---|---|
| 1. Stack startup | `docker compose up` | Both services reach `Up` state without errors |
| 2. Service inventory | `docker compose ps` | `api` and `postgres` listed as running |
| 3. SPA reachability | `curl -i http://localhost:80/` | 200 response with HTML body |
| 4. API reachability | `curl -i http://localhost:80/api/week/2021-11-13` | 200 JSON response |

#### 6.6.6.5 Operator Verification Surfaces

The exhaustive set of operator-visible state surfaces — reproduced from Section 6.5.5.1 — that may be consulted during manual verification:

| Surface | Purpose During Verification |
|---|---|
| `docker compose ps` | Confirm both services are `Up` |
| `docker logs api` | Inspect Werkzeug request log + Python tracebacks |
| `docker logs postgres` | Inspect PostgreSQL server lifecycle and connection events |
| `docker stats` | Live CPU/memory/IO per container (no historical view) |
| Browser DevTools Network tab | Per-fetch HTTP method, status, response body, timing |
| Browser DevTools Console tab | Unhandled promise rejections from `fetch()` failures |

---

### 6.6.7 Recommended Future-Phase Testing Path

The recommendations below are the future-state vision for any production-grade hardening of the codebase. **None of these items are implemented**; they are presented to give the testing strategy a forward-looking shape and to enumerate the natural starting points already latent in the dependency manifests. They are ordered to maximize incremental value at each step.

#### 6.6.7.1 Backend Testing Path

| Capability | Recommended Tool | Natural Starting Point |
|---|---|---|
| Pure-function unit tests for `api/funcs.py` | `pytest` | Three deterministic helpers (`get_query_week`, `get_weekly_data`, `get_rolling_avg`) with bounded input domains |
| Route handler tests for `api/routes.py` | `pytest-flask` test client | Six `GET` routes; happy path + 1-2 failure paths each |
| ORM smoke tests for `api/models.py` | `pytest` + SQLite in-memory or test PostgreSQL | Schema dump verification; Marshmallow `dump()` round-trip |
| Coverage measurement | `pytest-cov` | Per-module HTML report; baseline coverage to inform future thresholds |

The three helpers in `api/funcs.py` are explicitly identified as the highest-leverage starting point because they have no I/O dependencies and deterministic input/output relationships — making them the textbook case for unit testing. The chart-week boundary at 10:00 AM Wednesday inside `get_query_week` (per Section 6.1.3.5) is the single most testable timing constraint in the codebase.

#### 6.6.7.2 Frontend Testing Path

The Create React App-installed Testing Library stack documented in Section 3.2.2 is the natural starting point — these libraries are **already declared** in `frontend/package.json` and require no additional installation:

| Capability | Available Tool (Already Declared) | Natural Starting Point |
|---|---|---|
| Component unit tests | `@testing-library/react` + Jest (transitive via `react-scripts`) | Section components (`TracksSection`, `TrendsSection`, `AboutSection`) plus primitives (`DatePicker`, `FeatureSelect`) |
| User interaction tests | `@testing-library/user-event` | Date submit, feature selection, tab navigation |
| DOM assertion matchers | `@testing-library/jest-dom` | Render output verification of `#radialChart` and `#featureChart` host nodes |
| Fetch mocking | `jest.fn()` (built-in) or MSW (Mock Service Worker, would require addition) | Stub `/api/week`, `/api/analysis`, `/api/artist`, `/api/track` responses |

Activating the existing Testing Library stack is the lowest-cost frontend testing investment; it requires only the authoring of `*.test.js` companion files for existing components and the addition of a `setupTests.js` shim.

#### 6.6.7.3 Integration and End-to-End Testing Path

| Capability | Recommended Approach | Notes |
|---|---|---|
| End-to-end smoke probes | Shell script wrapping `curl` against all six routes | Codifies the manual procedure already documented in Section 6.6.6.1 |
| Full-stack browser tests | Cypress or Playwright against `docker compose up` stack | Should target the three primary user workflows from Section 1.3.1 |
| API contract tests | Schemathesis (would require authoring an OpenAPI document) | Would close the schema-validation gap noted in Section 6.4.3.4 |
| Cross-browser verification | The existing `browserslist` declaration in `frontend/package.json` would inform the matrix | Targets `>0.2%, not dead, not op_mini all` |

#### 6.6.7.4 CI/CD Integration Path

Per Section 3.6.5, no CI/CD provider is present. The natural starting point would be **GitHub Actions** because it is the most common provider for repositories of this size and requires no additional infrastructure beyond a `.github/workflows/` directory:

| Capability | Recommended Configuration | Trigger |
|---|---|---|
| Backend test job | `.github/workflows/test.yml` running `pytest` + `pytest-cov` | Push and pull request |
| Frontend test job | Same workflow running `npm test -- --watchAll=false --coverage` | Push and pull request |
| Integration smoke job | Workflow step running `docker compose up -d` + the shell-script smoke probe | Push and pull request |
| Pre-commit hooks | `pre-commit` framework with `black`, `flake8`, `eslint` hooks | Local commit |
| Coverage upload | Codecov action integrated with the test workflows | After successful test run |

#### 6.6.7.5 Hardening Sequence

The sequence below is ordered by the cumulative reduction in regression risk per unit of effort. Each step assumes the prior steps are complete. This sequence mirrors the structure of the security hardening sequence in Section 6.4.6.3 and the observability hardening sequence in Section 6.5.6.

```mermaid
flowchart LR
    Start([Current Posture<br/>manual verification only]) --> H1["1: Author pytest tests<br/>for api/funcs.py helpers"]
    H1 --> H2["2: Author pytest-flask tests<br/>for api/routes.py routes"]
    H2 --> H3["3: Wire @testing-library/react<br/>tests for Section components"]
    H3 --> H4["4: Add pytest-cov<br/>+ Jest --coverage"]
    H4 --> H5["5: Codify GitHub Actions<br/>.github/workflows/test.yml"]
    H5 --> H6["6: Add pre-commit hooks<br/>black + flake8 + eslint"]
    H6 --> H7["7: Author shell-script<br/>integration smoke probes"]
    H7 --> H8["8: Adopt Cypress or Playwright<br/>for E2E workflows"]
    H8 --> H9["9: Add Schemathesis contract tests<br/>+ author OpenAPI doc"]
    H9 --> H10["10: Codify performance baselines<br/>once SLAs are agreed"]
    H10 --> Production([Production-grade<br/>testing posture])
```

The first four steps (H1 through H4) collectively raise testing from **zero automated signal** to **per-component coverage with measurable instrumentation** — a posture sufficient for confident refactoring of the existing codebase. Steps H5 and H6 add the CI infrastructure to enforce those gates. Steps H7 through H9 close the integration and contract-testing gaps. Step H10 depends on the prerequisite SLA codification documented in Sections 4.6.2, 5.4.5, and 6.5.3.4 — performance test thresholds cannot meaningfully precede the targets they enforce.

---

### 6.6.8 Summary of Non-Applicability

The Testing Strategy concerns enumerated in this section's prompt map to the actual codebase as follows:

| Prompt Concern | Status in This System | Driving Reason |
|---|---|---|
| Unit testing — backend | Absent | No `pytest`; no `tests/` directory in `api/` |
| Unit testing — frontend | Tools declared, no tests | `@testing-library/*` in `frontend/package.json`; no `*.test.js` files |
| Test organization structure | Not codified | No tests; no convention in use |
| Mocking strategy | Not codified | No mock libraries imported |
| Code coverage requirements | Not codified | No coverage tool installed |
| Test naming conventions | Not codified | No tests authored |
| Test data management | Not codified | No fixtures, factories, or seeders |
| Service integration tests | Absent | No services to integrate; one Flask↔Postgres link |
| API testing strategy | Manual `curl` only | Section 2.5.2 documents manual probes per route |
| Database integration testing | Absent | Single PostgreSQL instance; no test database |
| External service mocking | Not applicable | No external services to mock (Section 3.4) |
| Test environment management | Single environment | Same `docker compose up` stack for dev, test, prod |
| E2E test scenarios | Absent | No Cypress / Playwright / Selenium in dependencies |
| UI automation approach | Manual inspection only | Browser DevTools is the only verification surface |
| Test data setup / teardown | Not applicable | No automation harness to host hooks |
| Performance testing requirements | Not applicable | No SLAs codified (Section 4.6.2) |
| Cross-browser testing strategy | Not codified | `browserslist` declared but no automated matrix |
| CI/CD integration | Absent | No CI provider configured (Section 3.6.5) |
| Automated test triggers | Absent | No CI provider; no commit hooks |
| Parallel test execution | Not applicable | No tests; no runner |
| Test reporting requirements | Not codified | No reporting infrastructure |
| Failed test handling | Not applicable | No tests to fail |
| Flaky test management | Not applicable | No tests; solo-maintainer model |
| Code coverage targets | Not codified | No coverage tool installed |
| Test success rate requirements | Not applicable | No tests; no success rate to compute |
| Performance test thresholds | Not applicable | No SLAs to enforce |
| Quality gates | ESLint at build time only | Frontend lint via `react-app/jest` preset |
| Documentation requirements | Section 2.5.2 manual matrix is de facto plan | No formal test-doc convention |
| Security testing requirements | Absent | No `bandit`, no `safety`, no `npm audit` enforcement; mitigations documented in Section 6.4.6.3 |

The system instead relies on a small set of **basic verification practices** — ESLint static analysis at build time, dependency pinning for reproducibility, container smoke tests via `docker compose up`, manual HTTP probes via `curl`, and manual UI inspection via browser DevTools — that together provide a development-grade quality floor sufficient for the system's actual deployment context. The full hardening path required for production-grade test coverage is sketched in Section 6.6.7 and cross-referenced to the originating recommendations in Sections 1.3.3, 3.6.5, 3.6.7, and 5.3.6.

---

### 6.6.9 References

#### Files Examined

- `requirements.txt` — 23 pinned Python dependencies; verified absence of `pytest`, `pytest-flask`, `pytest-cov`, `unittest2`, `nose`, `tox`, `factory_boy`, `faker`, `responses`, `vcr.py`, `freezegun`, `mock`, `pytest-mock`, `pytest-rerunfailures`, `pytest-xdist`, `bandit`, and `safety`.
- `frontend/package.json` — Frontend dependency manifest; verified declaration of `@testing-library/jest-dom` (^5.11.4), `@testing-library/react` (^11.1.0), and `@testing-library/user-event` (^12.1.10) as CRA-default dependencies; verified `"test": "react-scripts test"` script; verified `eslintConfig` extending `react-app` and `react-app/jest`; verified absence of Cypress, Playwright, Selenium, Puppeteer, TestCafe, MSW, jest-junit, and any custom Jest configuration.
- `frontend/package-lock.json` — Locked dependency tree; verified Jest is present transitively under `react-scripts` 4.0.3 with no override.
- `api/__init__.py` — 22-line Flask bootstrap; verified absence of test app factory, no `create_app(testing=True)` pattern, no environment-based configuration switching.
- `api/routes.py` — 70-line module with six `GET` route handlers; verified absence of `try/except`, no test client setup, no helper functions for assertion.
- `api/funcs.py` — 59-line module with three pure functions (`get_query_week`, `get_weekly_data`, `get_rolling_avg`); identified as the strongest candidates for future unit-testing investment.
- `api/models.py` — `Tracks` and `YearlyAvg` ORM models plus `TrackSchema` and `YearlyAvgSchema` Marshmallow schemas; no test fixtures.
- `app.py` — 4-line entry point invoking `app.run(host='0.0.0.0')`; no test bootstrap.
- `Dockerfile` — Single-stage build with `CMD ["python3", "app.py"]`; no test stage; no `HEALTHCHECK` directive.
- `docker-compose.yml` — Two-service stack (`api` and `postgres`); no test service, no test-isolated profile.
- `.dockerignore` — Build-context exclusions for `frontend/node_modules`, `venv`, `data`; no test artifacts excluded by accident.
- `frontend/src/index.js` — 12-line React entry; verified absence of `setupTests.js` import.
- `frontend/src/App.js` — 67-line top-level component; verified absence of `App.test.js` companion file.
- `frontend/public/index.html` — SPA shell; verified absence of test instrumentation snippets.
- `README.md` — Project documentation; no testing section.

#### Folders Examined

- `/` (repository root) — Top-level files; verified absence of `tests/`, `test/`, `e2e/`, `integration/`, `acceptance/`, `.github/`, `.gitlab/`, and `.circleci/` directories.
- `api/` — Backend Flask package; only `__init__.py`, `routes.py`, `models.py`, `funcs.py`; no `tests/` subdirectory; no `conftest.py`.
- `frontend/` — Frontend root; only `package.json`, `package-lock.json`, `src/`, `public/`, `build/`; no `cypress/`, `e2e/`, `tests/`, or `__mocks__/` directories.
- `frontend/src/` — React source; only `App.js`, `index.js`, `components/`, `styles/`; no `__tests__/`, no `*.test.js`, no `setupTests.js`.
- `frontend/src/components/` — Four feature folders (`tracks/`, `trends/`, `about/`, `navigation/`); no test files in any folder.
- `frontend/public/` — SPA shell artifacts (`index.html`, `manifest.json`); no test instrumentation.

#### Cross-Referenced Technical Specification Sections

- **Section 1.3 SCOPE** — Section 1.3.3 explicitly lists "Automated tests" and "CI/CD pipelines" in the Out-of-Scope Elements with file-level evidence; Section 1.3.3 lists test-tool removal/activation as a future-phase consideration.
- **Section 2.5 TRACEABILITY MATRIX** — Section 2.5.2 enumerates the manual test strategy for all 17 features (F-001 through F-017) and explicitly states that "all test strategies above are therefore manual; introducing automated tests would be a future-phase undertaking and is documented as out-of-scope."
- **Section 3.2 FRAMEWORKS & LIBRARIES** — Section 3.2.2 documents the Testing Library packages under "Test Tooling (Declared, No Tests Present)" with the verification "Although these libraries are declared, no test files exist anywhere in `frontend/src/`."
- **Section 3.6 DEVELOPMENT & DEPLOYMENT** — Section 3.6.5 confirms no CI/CD providers; Section 3.6.7 explicitly states "Testing — Not present" with file-level evidence.
- **Section 4.6 TIMING AND SLA CONSIDERATIONS** — Section 4.6.2 confirms "no SLAs are codified anywhere in the repository," directly justifying the Performance Test Thresholds non-applicability.
- **Section 5.3 TECHNICAL DECISIONS** — ADR-001 (Single-Process SPA + API), ADR-004 (No Caching Tier), and ADR-006 (Flask Dev Server in Production) collectively establish the development-grade operational posture that bounds the testing investment.
- **Section 5.4 CROSS-CUTTING CONCERNS** — Section 5.4.5 (Performance Requirements and SLAs) and Section 5.4.6 (Disaster Recovery Procedures) supply the SLA-absence and recovery-posture context.
- **Section 6.1 Core Services Architecture** — Section 6.1.2.2 confirms "no inter-service communication exists" beyond the single Flask↔Postgres link, eliminating the integration-test surface.
- **Section 6.4 Security Architecture** — Section 6.4.3.4 (Input Validation) and Section 6.4.6.3 (Known Security Limitations) supply the security-testing context absent from this section.
- **Section 6.5 MONITORING AND OBSERVABILITY** — Section 6.5.1.3 (Basic Monitoring Practices), Section 6.5.5.1 (Available Operator Surfaces), and Section 6.5.6 (Recommended Hardening Path) provide the analogous template for the non-applicability assessment, the operator-surface inventory, and the future-phase hardening sequence reproduced in this section.

# 7. User Interface Design

The Hot Stuff application requires a user interface. This section documents the React 17 Single-Page Application (SPA) located in `frontend/`, its three-tab navigation shell, the two amCharts visualizations that anchor the experience, and the boundaries through which the SPA communicates with the Flask backend documented in sections 4.2 and 5.2.

The UI is the **primary surface** of the product. It is built as a Create React App project, compiled to static assets in `frontend/build/`, and served same-origin by the Flask process described in sections 1.2.2 and 5.1.1. There is no separate static-hosting tier, no native mobile shell, and no companion application.

## 7.1 OVERVIEW AND CORE UI TECHNOLOGIES

### 7.1.1 Frontend Stack Composition

The UI runtime is a small, deliberately curated stack declared in `frontend/package.json`. Every dependency is either actively used or a documented CRA-template residue (see section 3.2.2 for the full inventory).

| Technology | Declared Version | Role | Verified Usage |
|---|---|---|---|
| `react` | `^17.0.2` | UI runtime | All component files |
| `react-dom` | `^17.0.2` | DOM rendering | `frontend/src/index.js` |
| `react-scripts` | `4.0.3` (exact pin) | CRA build pipeline (Webpack 4, Babel, Jest, ESLint) | Build/dev tooling |
| `@amcharts/amcharts4` | `^4.10.19` | Charting (radar + line) | `RadarChart.js`, `LineChart.js` |
| `styled-components` | `^5.3.0` | CSS-in-JS for navigation primitives | `Sidebar.js`, `Tab.js`, `SmallTab.js`, `Section.js` |

The exact pin on `react-scripts` is significant — Webpack 4 (bundled inside CRA 4) requires the `NODE_OPTIONS=--openssl-legacy-provider` environment variable on Node 17+, which Compose supplies on the `api` service. CRA also handles transpilation, bundling, source maps, and PWA scaffolding without additional configuration files in this repository.

#### Declared but Unused Dependencies

The following dependencies appear in `package.json` but are not imported anywhere in the source tree:

| Dependency | Status |
|---|---|
| `axios` (`^0.21.1`) | Replaced by native `fetch()` in both fetch-driven components |
| `plotly.js` (`^1.58.4`) | Charting is delivered exclusively via amCharts4 |
| `react-plotly.js` (`^2.5.1`) | Counterpart to `plotly.js`, never imported |
| `web-vitals` (`^1.0.1`) | CRA template default; `reportWebVitals()` is not wired in `index.js` |
| `@testing-library/jest-dom`, `@testing-library/react`, `@testing-library/user-event` | Declared but no test files exist anywhere in `frontend/src/` |

These do not affect runtime behavior but inflate the `node_modules` tree.

### 7.1.2 External Browser-Loaded Resources

The only third-party browser-loaded resource is the **Jost** typeface family from Google Fonts, declared in `frontend/public/index.html` via a `<link rel="preconnect">` hint and a `<link rel="stylesheet">` directive. The font is loaded with weights `100` through `700` (both italic and roman) and `display=swap` to prevent invisible text during webfont load. No other CDNs, analytics scripts, tag managers, or third-party tracking pixels are referenced anywhere in the HTML shell.

### 7.1.3 Build and Runtime Configuration

| Concern | Configuration | Source |
|---|---|---|
| Dev server | `react-scripts start` on port `3000` | `package.json` `scripts.start` |
| Dev API proxy | `"proxy": "http://localhost:5000"` | `package.json` |
| Production output | `frontend/build/` directory (static HTML/JS/CSS) | `react-scripts build` |
| Production hosting | Flask `static_folder='../frontend/build'`, `static_url_path='/'` | `api/__init__.py` |
| Production browser targets | `>0.2%`, `not dead`, `not op_mini all` | `package.json` `browserslist.production` |
| Development browser targets | last Chrome / Firefox / Safari | `package.json` `browserslist.development` |
| ESLint preset | `react-app`, `react-app/jest` | `package.json` `eslintConfig` |

The CRA dev proxy eliminates CORS concerns during local iteration; in production the SPA and the API share the same origin (port 80 → container 5000), so no cross-origin handshake occurs there either. CORS handling at the backend is documented in section 4.2.1 as defense-in-depth.

### 7.1.4 Application Mount and Bootstrap

The HTML shell at `frontend/public/index.html` declares an empty `<div id="root"></div>` mount node, a `<noscript>` fallback message, and a `<title>Hot Stuff</title>`. Viewport meta is `width=device-width, initial-scale=1` (responsive) and `theme-color` is `#000000`.

`frontend/src/index.js` mounts `<App />` into `#root` wrapped in `<React.StrictMode>` and imports the global stylesheet `./styles/index.css`. As noted above, `reportWebVitals()` is not invoked even though `web-vitals` is installed.

```mermaid
flowchart TB
    HTML[frontend/public/index.html<br/>div id=root, font preconnect, manifest link]
    Bootstrap[frontend/src/index.js<br/>ReactDOM.render with StrictMode<br/>imports styles/index.css]
    AppShell[frontend/src/App.js<br/>state: nav, activeTab]
    Sidebar[StSidebar<br/>nav prop]
    SecTracks[Section activeTab=index 0]
    SecTrends[Section activeTab=index 1]
    SecAbout[Section activeTab=index 3]
    Footer[footer<br/>AUG | 2021]

    HTML --> Bootstrap
    Bootstrap --> AppShell
    AppShell --> Sidebar
    AppShell --> SecTracks
    AppShell --> SecTrends
    AppShell --> SecAbout
    AppShell --> Footer
    SecTracks --> TracksSection
    SecTrends --> TrendsSection
    SecAbout --> AboutSection
```

---

## 7.2 USE CASES AND SCREEN INVENTORY

The SPA is composed of **three top-level screens** rendered as conditional `<Section>` wrappers inside `App.js`. Each tab represents a distinct use case anchored on a single Sidebar tab ID. Tab indices are non-contiguous: `0` (Tracks), `1` (Trends), `3` (About) — index `2` is intentionally absent (a convention that must be preserved on any future tab insertion).

| Tab Index | Screen | Source File | Use Case |
|---|---|---|---|
| `0` (default) | Tracks | `frontend/src/components/tracks/TracksSection.js` | Inspect a single chart week's ranked entries and audio-feature radar |
| `1` | Trends | `frontend/src/components/trends/TrendsSection.js` | Examine the longitudinal evolution of one audio feature with a smoothed rolling average |
| `3` | About | `frontend/src/components/about/AboutSection.js` | Read methodology, data sources, and external references |

### 7.2.1 Screen 1 — Tracks Tab (Weekly Chart Inspection)

This is the **default and primary screen** of the application; it is mounted with `activeTab=0` on every page load.

#### Layout (top to bottom)

1. **Top bar** (`<div className='topBar'>`) — A flex row containing the `<DatePicker>` form on the left and the `<Hamburger>` menu trigger on the right (the hamburger is hidden on viewports ≥800px).
2. **Radar chart** — A semi-circular amCharts4 `RadarChart` mounted into the `#radialChart` DOM node (height 260px, full width), fed from `data.averages`.
3. **Scrollable ranked list** (`<div className='scroll'>`) — Each chart entry from `data.songs` rendered as a `trackRow` flex item displaying rank, artist, and track name.

#### State Machine

| Variable | Initial | Purpose |
|---|---|---|
| `data` | `[]` | Backend response payload (`{week, songs, averages, avgTempo}`) |
| `isLoaded` | `false` | Drives loading indicator and success render |
| `error` | `null` | Drives error message render |

#### Initial Fetch

On component mount, `useEffect` calls `getData('2021-11-13')` — a hardcoded date literal. Directly above it sits the dynamic alternative `getData(new Date().toISOString().slice(0, 10))`, which is **commented out**. The `DatePicker`'s `initValue` prop is also `'2021-11-13'`, keeping the form input synchronized with the initial fetch parameter. This hardcoded freeze-date is documented as a known limitation in section 1.2.1.

#### Visual States

| State | Output |
|---|---|
| Loading | `<h1 className='loading'>. . .</h1>` |
| HTTP error | `<h1 className='error'>{statusText}</h1>` |
| Empty result | `<h1 className='error'>No Data Found</h1>` |
| Success | Top bar + radar + scrollable list |

### 7.2.2 Screen 2 — Trends Tab (Longitudinal Feature Analysis)

This screen surfaces the application's analytics differentiator — the year-over-year evolution of a single audio feature plus a smoothed rolling mean.

#### Layout (top to bottom)

1. **Top bar** — `<FeatureSelect>` form on the left, `<Hamburger>` on the right.
2. **Loading/error indicator** — `<h1 className='error'>` or `<h1 className='loading'>` rendered conditionally.
3. **Line chart** — An amCharts4 `XYChart` mounted into `#featureChart` (height 260px, with `marginTop:10px` and `marginRight:20px`).
4. **Audio Features documentation block** (`<div className='audioFeatures scroll'>`) — Iterates over `features.json` to render seven `<p className='featureDescription'>` entries, one per available feature.

#### State Machine

| Variable | Initial | Purpose |
|---|---|---|
| `data` | `[]` | Backend response (`{feature, data}`) |
| `isLoaded` | `false` | Drives loading indicator |
| `error` | `null` | Drives error message |

#### Initial Fetch

On mount, `useEffect` calls `getData('tempo')`. Subsequent fetches are triggered by `FeatureSelect` form submissions.

#### Feature Documentation Rendering

The documentation list iterates over the static `features.json` array bundled by Webpack:

```jsx
{features.map((feature, i) => (
  <p key={i} className='featureDescription'>
    <b>{feature.title}: </b>
    {feature.desctiption}   // sic — typo preserved verbatim
  </p>
))}
```

The misspelled property key `desctiption` is preserved verbatim from `features.json` because the JSON file uses the same misspelling (also documented in section 5.1.2).

### 7.2.3 Screen 3 — About Tab (Methodology Documentation)

This screen is **purely presentational** — it has no `useState`, no `useEffect`, no fetch, and no callbacks. It receives only the `showNav` prop forwarded to `<Hamburger>`.

#### Layout

1. **Top bar** (`<div className='topBar aboutHeader'>`) — Contains only the `<Hamburger>` (the `aboutHeader` class right-aligns it via `justify-content: flex-end`).
2. **Scrollable content** (`<div className='aboutContent scroll'>`) consisting of three documentation sections:
   - **The Billboard Hot 100** — Explains the chart, cites the first #1 song "Poor Little Fool" by Ricky Nelson on August 4, 1958, and provides anchor links to billboard.com and Wikipedia.
   - **API** — Documents the Flask backend; lists all four backend endpoints (`/api/week/<week>`, `/api/artist/<artist>`, `/api/track/<spotify_id>`, `/api/analysis/<feature>`); links to the Spotipy and Spotify Audio Features documentation.
   - **Front End** — Documents the React + amCharts stack and links to amcharts.com.
3. **Source Code link** — Anchor to `https://github.com/augardiner/hot-100`.

All external links use `target='_blank'` paired with `rel='noopener noreferrer'` for safe new-tab navigation.

---

## 7.3 APPLICATION SHELL AND NAVIGATION ARCHITECTURE

### 7.3.1 Composition of the Shell

`frontend/src/App.js` is the top-level container. It owns two pieces of state and renders five child elements:

| State | Type | Default | Purpose |
|---|---|---|---|
| `nav` | boolean | `false` | Toggles mobile sidebar visibility (opacity transition) |
| `activeTab` | number | `0` | Currently displayed `<Section>` wrapper |

The `handleClick` callback parses the clicked tab's numeric `id`, guards against the no-op case (`if (index !== activeTab)`), updates `activeTab`, and resets `nav` to `false` so that any open mobile sidebar collapses on navigation.

```javascript
const handleClick = (e) => {
  const index = parseInt(e.target.id, 0);
  if (index !== activeTab) {
    setActiveTab(index);
    setNav(false);
  }
};
```

The shell's render output, in source order:

1. `<StSidebar nav={nav} activeTab={activeTab} handleClick={handleClick} />`
2. A mobile-only header (`<div className='titleContainer mobileHeader'>` with the text "Hot Stuff")
3. `<Section activeTab={activeTab === 0}>` wrapping `<TracksSection>`
4. `<Section activeTab={activeTab === 1}>` wrapping `<TrendsSection>`
5. `<Section activeTab={activeTab === 3}>` wrapping `<AboutSection>`
6. A footer `<div className='footer'>` containing `<p>AUG | 2021</p>`

### 7.3.2 Navigation Primitives

All navigation primitives are styled-components-based and live under `frontend/src/components/navigation/`.

| File | Type | Responsibility |
|---|---|---|
| `Sidebar.js` | Styled functional component | Renders the title, two large `<Tab>` items (Tracks, Trends), and one `<SmallTab>` item (About). Mobile: opacity-toggled overlay at `width: 35vw`; desktop (≥800px): always visible at `width: 15vw` |
| `Tab.js` | Styled `div` | Large tab primitive (font-size 25px, weight 700, right-aligned). Active state applies color `rgb(128, 103, 220)`; hover applies the same color only when inactive |
| `SmallTab.js` | Styled `div` | Compact counterpart for the About tab (font-size 20px); same active/hover logic as `Tab.js` |
| `Section.js` | Styled `div` | Conditionally hides content via `${(props) => (props.activeTab ? '' : 'display:none')}` |
| `Hamburger.js` | Functional component | SVG icon — three rounded `<rect>` bars (75×10 each) within a 40×40 viewport — fires the `showNav` callback on click |

The sidebar's mobile-vs-desktop transition is handled inside the styled-component definition itself:

```javascript
const StSidebar = styled(Sidebar)`
  position: fixed;
  height: calc(100vh - 25px);
  width: 35vw;             /* mobile */
  left: 0;
  display: flex;
  flex-direction: column;
  background-color: var(--dark-2);
  z-index: 2;
  transition: opacity 0.5s;
  ${(props) => (props.nav ? 'opacity: 1;' : 'opacity: 0;')};

  @media only screen and (min-width: 800px) {
    opacity: 1;            /* always visible on desktop */
    width: 15vw;           /* narrower fixed column */
  }
`;
```

### 7.3.3 Tab Navigation State Machine

The shell's `activeTab` state machine drives which `<Section>` is visible. Transitions happen through Sidebar tab clicks; the same-tab no-op is a guarded short-circuit. The non-contiguous index space (no `2`) is consistent across `App.js` and `Sidebar.js`.

```mermaid
stateDiagram-v2
    [*] --> Tracks: activeTab=0 default on mount
    Tracks --> Trends: Sidebar tab id=1 clicked
    Tracks --> About: Sidebar tab id=3 clicked
    Trends --> Tracks: Sidebar tab id=0 clicked
    Trends --> About: Sidebar tab id=3 clicked
    About --> Tracks: Sidebar tab id=0 clicked
    About --> Trends: Sidebar tab id=1 clicked
    Tracks --> Tracks: Same tab guarded no-op
    Trends --> Trends: Same tab guarded no-op
    About --> About: Same tab guarded no-op
```

---

## 7.4 UI ↔ BACKEND INTERACTION BOUNDARIES

### 7.4.1 Endpoint Surface Consumed by the UI

Although the backend exposes six routes (see section 5.1.1), the UI directly invokes only **two** of them. The remaining four are documented on the About tab but are not consumed by any frontend component.

| Endpoint | UI Consumer | Trigger |
|---|---|---|
| `GET /api/week/<date>` | `TracksSection.getData()` | Mount + `DatePicker` submit |
| `GET /api/analysis/<feature>` | `TrendsSection.getData()` | Mount + `FeatureSelect` submit |

### 7.4.2 Communication Mechanism

| Concern | Implementation |
|---|---|
| HTTP client | Browser-native `fetch()` API |
| Method | `GET` only; no request bodies |
| Authentication | None — no headers, no cookies, no CSRF tokens, no JWT |
| Origin (production) | Same-origin (Flask serves SPA at `/` and API at `/api/*`) |
| Origin (development) | CRA dev proxy `"proxy": "http://localhost:5000"` forwards relative paths |
| Caching | None on either tier (no `Cache-Control`, `ETag`, or Service Worker — see section 4.4.5) |

The boundary diagram below summarizes the same-origin production flow alongside the CRA proxy used during development:

```mermaid
sequenceDiagram
    participant Browser as Browser fetch native
    participant Flask as Flask 2.0.1 port 5000
    participant CORS as Flask-Cors 3.0.10

    Note over Browser,Flask: Production same-origin port 80 to 5000<br/>Development CRA proxy localhost:5000
    Browser->>Flask: fetch /api/week/2021-11-13
    Flask->>CORS: CORS app permissive
    CORS-->>Flask: Access-Control-Allow-Origin star
    Flask-->>Browser: 200 application/json
    Note over Browser,Flask: No auth headers, no cookies, no CSRF token
```

### 7.4.3 Fetch Lifecycle State Transitions

Both `TracksSection.getData()` and `TrendsSection.getData()` implement the **identical** fetch lifecycle state machine. Each call follows the four-state machine below, and the render output is a deterministic function of the resulting `(data, isLoaded, error)` triple.

```mermaid
stateDiagram-v2
    [*] --> Initial: Component mounts
    Initial --> Loading: useEffect fires getData
    Loading --> Success: data length greater than 0
    Loading --> HttpError: response status greater than 299
    Loading --> EmptyData: data length equals 0
    Success --> Loading: User submits new query
    HttpError --> Loading: User submits new query
    EmptyData --> Loading: User submits new query
```

The handler shape (identical in both sections, parameterized by endpoint and parameter):

```javascript
const getData = async (input) => {
  setIsLoaded(false);
  setError(false);
  const response = await fetch(`/api/${endpoint}/${param}`);
  if (response.status > 299) {
    setIsLoaded(true);
    setError(response.statusText);
    return;
  }
  let data = await response.json();
  if (data.length === 0) {
    setError('No Data Found');
    setIsLoaded(true);
  } else {
    setData(data);
    setIsLoaded(true);
  }
};
```

### 7.4.4 Error and Loading State Visuals

| State | Render Output | CSS Class |
|---|---|---|
| Loading | `<h1 className='loading'>. . .</h1>` | `.loading` (centered, color `--light`) |
| HTTP error | `<h1 className='error'>{error}</h1>` | `.error h1` (centered, color `--light`) |
| Empty data | `<h1 className='error'>No Data Found</h1>` | Same as above |
| Network error (fetch rejection) | **No UI feedback** — loading indicator persists indefinitely | n/a — see section 4.5.1 |

A critical gap discussed in section 4.5.1 is that neither `TracksSection.getData` nor `TrendsSection.getData` wraps its `await fetch(...)` call in a try/catch. Network-level failures (DNS resolution failure, connection refused) result in unhandled promise rejections visible only in the browser console, while the UI remains stuck on the loading indicator.

---

## 7.5 UI DATA SCHEMAS

The UI consumes two JSON response shapes and one bundled static JSON asset. The contracts are documented below from the consumer perspective; the producing route handlers are documented in section 5.1.3.

### 7.5.1 Weekly Snapshot Response (consumed by Tracks Tab)

Returned by `GET /api/week/<date>`:

```json
{
  "week": "<YYYY-MM-DD>",
  "songs": [
    {
      "id": <int>,
      "week": "<YYYY-MM-DD>",
      "rank": <int>,
      "track": "<string>",
      "artist": "<string>",
      "spotify_id": "<string>",
      "tempo": <float>,
      "energy": <float>,
      "danceability": <float>,
      "valence": <float>,
      "liveness": <float>,
      "speechiness": <float>,
      "acousticness": <float>,
      "instrumentalness": <float>,
      "loudness": <float>
    }
  ],
  "averages": [
    { "feature": "<string>", "mean": <int>, "full": 100 }
  ],
  "avgTempo": <int>
}
```

| Field | Bound To |
|---|---|
| `data.songs` | The scrollable `trackRow` list (rank, artist, track) |
| `data.averages` | The radar chart's `mean` and `full` series |
| `data.week`, `data.avgTempo` | Currently not bound to any visual element |

### 7.5.2 Feature Trend Response (consumed by Trends Tab)

Returned by `GET /api/analysis/<feature>`:

```json
{
  "feature": "<string>",
  "data": [
    { "year": "<string>", "value": <float>, "rolling": <float> }
  ]
}
```

| Field | Bound To |
|---|---|
| `data.data` (array) | `LineChart` `chart.data` |
| `year` | X-axis (DateAxis) `dateX='year'` |
| `value` | Series 1 ("Annual Average") `valueY='value'` |
| `rolling` | Series 2 ("3 Year Rolling Average") `valueY='rolling'` |

### 7.5.3 Static Feature Documentation Schema

`frontend/src/components/trends/features.json` is a static array of seven objects bundled by Webpack and consumed verbatim by `TrendsSection.js`:

```json
[
  { "title": "Tempo", "desctiption": "..." },
  { "title": "Energy", "desctiption": "..." },
  { "title": "Danceability", "desctiption": "..." },
  { "title": "Instrumentalness", "desctiption": "..." },
  { "title": "Liveness", "desctiption": "..." },
  { "title": "Speechiness", "desctiption": "..." },
  { "title": "Acousticness", "desctiption": "..." }
]
```

The misspelled key `desctiption` (sic) is the schema contract — both producer and consumer agree on the typo, so the rendering works correctly. Renaming requires coordinated changes in both `features.json` and `TrendsSection.js`.

---

## 7.6 USER INTERACTIONS

### 7.6.1 Interaction Catalog

| # | Interaction | Trigger | Code Path | Result |
|---|---|---|---|---|
| 1 | Open mobile sidebar | Click `<Hamburger>` (any tab) | `showNav` → `setNav(!nav)` in `App.js` | Sidebar fades from opacity 0 to 1 |
| 2 | Switch to Tracks | Click "Tracks" tab in sidebar (`id=0`) | `handleClick` → `setActiveTab(0)` + `setNav(false)` | Tracks `<Section>` unhides; mobile sidebar collapses |
| 3 | Switch to Trends | Click "Trends" tab (`id=1`) | `handleClick` → `setActiveTab(1)` + `setNav(false)` | Trends `<Section>` unhides |
| 4 | Switch to About | Click "About" `<SmallTab>` (`id=3`) | `handleClick` → `setActiveTab(3)` + `setNav(false)` | About `<Section>` unhides |
| 5 | Re-click active tab | Click already-active tab | Guarded no-op via `if (index !== activeTab)` | No state mutation, no re-render |
| 6 | Pick a date | Use `<input type='date'>` | `handleChange` → `setInputValue(e.target.value)` | Local DatePicker state updates |
| 7 | Submit date | Click "Go" or press Enter | `handleSubmit` → truthy guard → `submitFunc(inputValue)` | Triggers `getData(input)` on Tracks; fetches `/api/week/<date>` |
| 8 | Pick a feature | Use `<select>` dropdown | `handleChange` → `setInputValue(e.target.value)` | Local FeatureSelect state updates |
| 9 | Submit feature | Click "Go" or press Enter | `handleSubmit` → truthy guard → `submitFunc(inputValue)` | Triggers `getData(input)` on Trends; fetches `/api/analysis/<feature>` |
| 10 | Hover chart point (Trends) | Mouse over series | amCharts `XYCursor` + tooltip | Tooltip shows year + value snapped to series |
| 11 | Hover chart segment (Tracks) | Mouse over radar series | amCharts `tooltipText='{mean}'` | Tooltip shows the feature's mean value |
| 12 | Click external link | Click `<a target='_blank'>` in About | Browser navigates in new tab with `rel='noopener noreferrer'` | New browser tab opens at the target URL |

### 7.6.2 DatePicker Interaction (Tracks Tab)

`frontend/src/components/tracks/DatePicker.js` is a controlled-component form bounded to the chart's full historical range:

```jsx
<form onSubmit={handleSubmit}>
  <input
    className='inputField'
    type='date'
    value={inputValue}
    onChange={handleChange}
    min='1958-07-27'
    max='2021-11-13'
  />
  <input className='inputBtn' type='submit' value='Go' />
</form>
```

| Property | Value | Rationale |
|---|---|---|
| Input type | `date` (HTML5) | Browser-native picker; no third-party calendar widget |
| `min` | `1958-07-27` | Date of the first published Billboard Hot 100 |
| `max` | `2021-11-13` | Frozen upper bound matching the hardcoded initial fetch |
| `initValue` prop | `'2021-11-13'` | Synchronizes the input's display state with the initial fetch |
| Submit guard | Truthy check on `inputValue` before invoking `submitFunc` | Prevents empty-string submission |
| Page reload prevention | `e.preventDefault()` in `handleSubmit` | Standard SPA form pattern |

### 7.6.3 FeatureSelect Interaction (Trends Tab)

`frontend/src/components/trends/FeatureSelect.js` exposes seven hardcoded `<option>` values inside a `<select>`. Initial state is `useState()` with no argument (i.e., `undefined`); the field becomes defined on first user change.

```jsx
<select name='feature' className='inputField' onChange={handleChange}>
  <option value='tempo'>Tempo</option>
  <option value='energy'>Energy</option>
  <option value='danceability'>Danceability</option>
  <option value='instrumentalness'>Instrumentalness</option>
  <option value='liveness'>Liveness</option>
  <option value='speechiness'>Speechiness</option>
  <option value='acousticness'>Acousticness</option>
</select>
<input className='inputBtn' type='submit' value='Go' />
```

The option values must match `YearlyAvg` column attribute names accepted by the `/api/analysis/<feature>` route. Note that the `Tracks` table also exposes `valence` and `loudness` columns, but these are intentionally excluded from this dropdown (also documented in section 5.2.7).

---

## 7.7 VISUAL DESIGN SYSTEM

### 7.7.1 Theme Tokens

All theme values are declared as CSS custom properties on `:root` in `frontend/src/styles/index.css`. The palette is dark-mode-first with a single purple accent color.

```css
:root {
  /* colors */
  --dark-1: #171717;                   /* page background */
  --dark-2: #262626;                   /* sidebar background */
  --dark-3: rgba(54, 54, 54, 0.5);     /* surfaces (input, button, track row) */
  --grey: rgb(189, 189, 189, 0.3);     /* muted borders */
  --light: rgb(189, 189, 189, 0.985);  /* foreground text */
  --purp: rgb(128, 103, 220);          /* accent (active tab, footer, hover) */
}
```

The accent `--purp` is reused as:
- The active-tab text color in `Tab.js` and `SmallTab.js`
- The hover color for inactive tabs
- The footer background color
- The solid-line series color in `LineChart.js`

### 7.7.2 Typography

| Token | Family | Loaded Via |
|---|---|---|
| Body font | `'Jost', sans-serif` | Google Fonts `<link>` in `index.html` |
| Code font | `source-code-pro, Menlo, Monaco, Consolas, 'Courier New', monospace` | Local fallback chain |

Body text uses `line-height: 1.5` with `-webkit-font-smoothing: antialiased` and `text-rendering: optimizeSpeed`. The application title (in the sidebar and mobile header) is `font-size: 30px; font-weight: 700; font-style: italic; text-align: center`.

### 7.7.3 Layout Structure and Component Styling

The body is set to `overflow: hidden` so that no page-level scrollbar appears; scrolling is delegated to designated `.scroll` containers within each section. The application container (`.app`) is `min-height: 100vh; width: 100vw; max-width: 1200px` and is centered horizontally.

| Element | Key Properties |
|---|---|
| `.titleContainer` | flex column, `border-bottom: 1px var(--grey)`, padding `10px 0` |
| `.titleContent` | text-align center, font-size 30px, weight 700, italic |
| `.tabContainer` | flex column, `justify-content: space-between`, max-height 790px, margin-top 70px (mobile) / 0 (desktop) |
| `.lowerTabs` | text-align right, font-size 12px (houses the SmallTab) |
| `.section` | flex column, `height: calc(85vh - 28px)` (mobile), `min-width: 50vw`, padding `0 10px` |
| `.topBar` | flex row, `justify-content: space-between`, padding `15px 0` |
| `.hamburger` | `display: flex` (mobile only), `fill: var(--light)` |
| `.inputField` | height 40px, width 160px, no border, border-radius 3px, background `--dark-3`, padding-left 10px, font-size 15px, weight 500 |
| `.inputBtn` | height 40px, padding `0 15px`, no border, border-radius 3px, background `--dark-3`, weight 600, cursor pointer, margin-left 5px |
| `.trackRow` | flex row, align-items center, margin `5px 0`, border-radius 3px, background `--dark-3`, color `--light` |
| `.rank` | width 15%, max-width 50px, margin `0 5px`, text-align center, font-size 25px, weight 500 |
| `.artist` | font-size 13px, weight 500 |
| `.track` | font-size 12px, weight 400 |
| `.audioFeatures` | padding `10px 5px` |
| `.featureDescription` | margin `5px 0`, font-size 12px |
| `.aboutHeader` | flex row, `justify-content: flex-end` |
| `.aboutContent h2` | margin `10px 0` |
| `.aboutContent p` | margin-top 10px, margin-bottom 5px |
| `.footer` | `position: fixed`, bottom 0, full-width, background `--purp`, border-radius 2px, padding `2px 0`, z-index 2 |
| `.footerContainer` | max-width 1000px (mobile) / 1200px (desktop), `justify-content: flex-end`, color `--dark-1`, font-size 15px, weight 500 |
| `.scroll` | `overflow-y: scroll` |
| `.loading`, `.error h1` | text-align center, color `--light` |

### 7.7.4 Responsive Behavior

A single `@media only screen and (min-width: 800px)` breakpoint divides the responsive design into two visual treatments. The breakpoint also changes the navigation paradigm — below 800px the sidebar is an opacity-toggled overlay, above 800px it is a permanent fixed column.

| Concern | < 800px (Mobile) | ≥ 800px (Desktop) |
|---|---|---|
| `.sidebarHeader` | `display: none` | `display: block` |
| `.mobileHeader` | visible | `display: none` |
| `.hamburger` | `display: flex` | `display: none` |
| `.tabContainer` margin-top | 70px | 0 |
| `.section` height | `calc(85vh - 28px)` | `calc(100vh - 28px)` |
| `.section` margin-left | 0 | 15vw (offset for fixed sidebar) |
| `.footerContainer` max-width | 1000px | 1200px |
| `.aboutHeader` height | unset | 50px |
| Sidebar width | 35vw (overlay) | 15vw (column) |
| Sidebar opacity | toggled by `nav` boolean | always 1 |

```mermaid
flowchart LR
    Viewport{Viewport width}
    Viewport -- less than 800px --> Mobile[Mobile mode]
    Viewport -- 800px or more --> Desktop[Desktop mode]

    Mobile --> M1[Sidebar opacity toggled by nav]
    Mobile --> M2[Hamburger visible]
    Mobile --> M3[Mobile header Hot Stuff visible]
    Mobile --> M4[Sidebar width 35vw overlay]

    Desktop --> D1[Sidebar always opacity 1]
    Desktop --> D2[Hamburger display none]
    Desktop --> D3[Mobile header display none]
    Desktop --> D4[Sidebar width 15vw fixed column]
    Desktop --> D5[Section margin-left 15vw]
```

### 7.7.5 PWA Manifest

`frontend/public/manifest.json` declares Hot Stuff as a Progressive Web App with standalone display:

```json
{
  "short_name": "Hot Stuff",
  "name": "Hot Stuff",
  "icons": [
    { "src": "favicon.ico", "sizes": "64x64 32x32 24x24 16x16", "type": "image/x-icon" },
    { "src": "logo192.png", "type": "image/png", "sizes": "192x192" },
    { "src": "logo512.png", "type": "image/png", "sizes": "512x512" }
  ],
  "start_url": ".",
  "display": "standalone",
  "theme_color": "#000000",
  "background_color": "#ffffff"
}
```

The `display: "standalone"` mode causes the application to render without browser chrome when installed. The `theme_color` matches the `<meta name="theme-color">` declaration in `index.html`.

---

## 7.8 VISUALIZATION COMPONENT CONFIGURATION

The two amCharts4 components are the visual centerpiece of the UI. Both apply the `am4themes_animated` theme at module load via `am4core.useTheme(am4themes_animated)`, and both **omit `chart.dispose()`** (the call exists but is commented out), causing chart instances to accumulate across re-renders — see section 7.10 and section 5.2.6/5.2.7.

### 7.8.1 RadarChart (Tracks Tab)

| Property | Value |
|---|---|
| DOM container ID | `radialChart` |
| Container size | width 100%, height 260px |
| Chart class | `am4charts.RadarChart` |
| Layout | Semi-circular: `startAngle = -90`, `endAngle = 180` |
| Inner radius | `am4core.percent(30)` |
| Number format | `'###'` (integer, no decimals) |
| Y-axis (categoryAxis) | Bound to `feature`; labels right-aligned, font-size 16, color matched to series via adapter |
| X-axis (valueAxis) | Range `[0, 100]`, `strictMinMax = true`, labels font-size 11, color `rgb(230, 230, 230)`, opacity 0.8 |
| Series 1 (`RadarColumnSeries`) | Bound to `full=100` baseline; fill `#262626`, rounded corners 5 |
| Series 2 (`RadarColumnSeries`) | Bound to `mean`; fill via `chart.colors.getIndex(target.dataItem.index)`; `tooltipText='{mean}'`; rounded corners 5 |
| Theme | `am4themes_animated` |

The semi-circular geometry, paired with the rounded corner style, creates the "audio fingerprint" appearance for each chart week.

### 7.8.2 LineChart (Trends Tab)

| Property | Value |
|---|---|
| DOM container ID | `featureChart` |
| Container size | width 100%, height 260px, marginTop 10px, marginRight 20px |
| Chart class | `am4charts.XYChart` |
| Date format | `'yyyy'` |
| X-axis (`DateAxis`) | Grid intervals `{1 year, 5 years, 10 years}`; grid stroke and labels `rgb(230, 230, 230)` opacity 0.9, font-size 12 |
| Y-axis (`ValueAxis`) | Matching style; font-size 11 |
| Series 1 ("Annual Average") | `LineSeries`, `valueY='value'`, `dateX='year'`, stroke `rgb(68, 54, 119)`, dashed pattern `'3,3'`, strokeWidth 2, tensionX 0.8 |
| Series 2 ("3 Year Rolling Average") | `LineSeries`, `valueY='rolling'`, stroke `rgb(128,103,220)` (the `--purp` accent), strokeWidth 2, tensionX 0.8 — solid line |
| Cursor | `XYCursor` with both axes, dashed pattern `'2,2'`, snap to both series |
| Legend | Bottom position, right-aligned, font-size 14, weight 300 |
| Theme | `am4themes_animated` |

The series 2 label "3 Year Rolling Average" is a known mismatch with the backend's five-row Pandas window (`get_rolling_avg` uses `.rolling(5).mean()` per `api/funcs.py`); reconciling either the label or the helper is a future-maintenance task documented in sections 1.2.1, 5.1.2, and 5.2.7.

---

## 7.9 STATE MANAGEMENT

The UI uses **only React local component state** (`useState` hooks). There is no Redux, no Zustand, no React Context, and no shared store. Browser storage is also unused — no `localStorage`, `sessionStorage`, cookies, IndexedDB, or Service Worker cache.

| Component | State Variables | Initial Values | File |
|---|---|---|---|
| `App` | `nav`, `activeTab` | `false`, `0` | `frontend/src/App.js` |
| `TracksSection` | `data`, `isLoaded`, `error` | `[]`, `false`, `null` | `tracks/TracksSection.js` |
| `TrendsSection` | `data`, `isLoaded`, `error` | `[]`, `false`, `null` | `trends/TrendsSection.js` |
| `DatePicker` | `inputValue` | `initValue` prop (`'2021-11-13'`) | `tracks/DatePicker.js` |
| `FeatureSelect` | `inputValue` | `undefined` (no argument to `useState()`) | `trends/FeatureSelect.js` |
| `AboutSection` | none | n/a | `about/AboutSection.js` |

State communication patterns:

- **Downward (parent → child)**: Props (`activeTab`, `nav`, callbacks).
- **Upward (child → parent)**: Callback props (`handleClick`, `submitFunc`, `showNav`).
- **Sibling-to-sibling**: Mediated through `App.js` for tab navigation; no direct sibling communication exists.

Because no client-side persistence is in place, every page reload resets to the default state (`activeTab=0`, mobile sidebar closed, Tracks tab fetching `/api/week/2021-11-13`).

---

## 7.10 KNOWN UI LIMITATIONS

The following UI behaviors are documented elsewhere in the specification (sections 1.2.1, 4.5, 5.1.2, 5.2.6, 5.2.7) and are reproduced here for completeness from a UI-implementation perspective. They do not block functional usage but should inform any future maintenance.

| # | Limitation | Location | Impact |
|---|---|---|---|
| 1 | Hardcoded initial fetch date | `tracks/TracksSection.js` line 37 (`getData('2021-11-13')`) | Initial render does not reflect the server's current date; dynamic alternative is commented out one line above |
| 2 | DatePicker max date frozen | `tracks/DatePicker.js` (`max='2021-11-13'`) | Users cannot select dates after Nov 13, 2021 even if the database contains newer data |
| 3 | Misspelled property key | `trends/features.json` and `TrendsSection.js` use `desctiption` (sic) | Renaming requires coordinated changes in both files |
| 4 | Series label / window mismatch | `LineChart.js` labels series 2 "3 Year Rolling Average" but `api/funcs.py` uses `.rolling(5)` | Visual labeling disagrees with computed window length |
| 5 | amCharts memory growth | `chart.dispose()` is commented out at `RadarChart.js` line 66 and `LineChart.js` line 70 | Chart instances accumulate across re-renders during long sessions |
| 6 | Non-contiguous tab indices | `App.js` and `Sidebar.js` use IDs `0`, `1`, `3` (no `2`) | Future tab insertion must preserve or refactor the convention |
| 7 | No React Error Boundary | No `<ErrorBoundary>` or `componentDidCatch` anywhere in `frontend/src/` | Unhandled component exceptions crash the entire SPA tree |
| 8 | Network errors invisible | No try/catch around `await fetch()` in either fetch-driven section | Network rejections appear only in the browser console; UI remains stuck on the loading indicator |
| 9 | No automated tests | All `@testing-library/*` packages declared but no test files exist | Regressions are caught only through manual exploratory testing |
| 10 | `web-vitals` declared but inert | `web-vitals` 1.0.1 in `package.json`; `reportWebVitals()` not invoked in `index.js` | No client-side performance metrics are emitted |

---

## 7.11 References

#### Files Examined

#### Application Shell and Mount Point

- `frontend/public/index.html` — HTML mount shell, `<div id="root">`, viewport meta, theme-color, Google Fonts preconnect, `<title>Hot Stuff</title>`
- `frontend/public/manifest.json` — PWA manifest (icons, `start_url`, `display: standalone`, theme/background colors)
- `frontend/src/index.js` — React bootstrap into `#root` with `StrictMode`; imports `./styles/index.css`
- `frontend/src/App.js` — Top-level shell; `nav` and `activeTab` state; renders Sidebar, three Section wrappers, footer

#### Navigation Primitives (`frontend/src/components/navigation/`)

- `Sidebar.js` — Styled sidebar; mobile overlay (35vw, opacity-toggled) vs desktop column (15vw, always visible)
- `Tab.js` — Large tab styled component (font-size 25px, weight 700, active/hover color logic)
- `SmallTab.js` — Compact tab variant (font-size 20px) used for the About link
- `Section.js` — Conditional `display: none` wrapper driven by the `activeTab` boolean prop
- `Hamburger.js` — SVG mobile menu trigger (40×40 viewport, three rounded `<rect>` bars)

#### Tracks Tab (`frontend/src/components/tracks/`)

- `TracksSection.js` — Tracks orchestration; `data`, `isLoaded`, `error` state; hardcoded `getData('2021-11-13')` initial fetch; renders DatePicker, RadarChart, scrollable trackRow list
- `DatePicker.js` — Native `<input type='date'>` form with `min='1958-07-27'` and `max='2021-11-13'`; truthy submit guard
- `RadarChart.js` — amCharts4 `RadarChart` configuration (semi-circular, 0–100 axis, two `RadarColumnSeries`); `chart.dispose()` commented out at line 66

#### Trends Tab (`frontend/src/components/trends/`)

- `TrendsSection.js` — Trends orchestration; `getData('tempo')` initial fetch; renders FeatureSelect, LineChart, and feature description list using the `desctiption` (sic) key
- `FeatureSelect.js` — Hardcoded 7-option `<select>` (excludes `valence` and `loudness`); `useState()` initialized to `undefined`
- `LineChart.js` — amCharts4 `XYChart` with two `LineSeries` ("Annual Average" dashed, "3 Year Rolling Average" solid); `chart.dispose()` commented out at line 70
- `features.json` — Static array of 7 `{title, desctiption}` objects bundled by Webpack

#### About Tab (`frontend/src/components/about/`)

- `AboutSection.js` — Pure presentational component; three documentation sections; external links to billboard.com, Wikipedia, Spotipy, Spotify, amCharts, GitHub

#### Styling and Configuration

- `frontend/src/styles/index.css` — CSS custom properties (`--dark-1`, `--dark-2`, `--dark-3`, `--grey`, `--light`, `--purp`); typography, layout, component styles, 800px responsive breakpoint
- `frontend/package.json` — Dependencies, scripts, `proxy: http://localhost:5000`, browserslist, `eslintConfig`

#### Backend Surface Consumed by UI

- `api/routes.py` — Source of truth for `/api/week/<date>` and `/api/analysis/<feature>` JSON shapes consumed by the SPA
- `api/__init__.py` — Flask `static_folder='../frontend/build'` and `static_url_path='/'` configuration enabling same-origin SPA delivery

#### Folders Explored

- `frontend/` — Top-level frontend project root
- `frontend/public/` — HTML shell, manifest, favicon
- `frontend/src/` — React source tree
- `frontend/src/components/` — Component subfolders (`navigation/`, `tracks/`, `trends/`, `about/`)
- `frontend/src/styles/` — Global stylesheet
- `frontend/build/` — Production bundle output (HTML, manifest, asset-manifest, static/)

#### Cross-Referenced Specification Sections

- **1.2 SYSTEM OVERVIEW** — Project context, primary capabilities, hardcoded date discrepancy
- **2.1 FEATURE CATALOG** — Features F-007 through F-012 covering navigation shell, tab views, and visualization components
- **3.2 FRAMEWORKS & LIBRARIES** — Frontend dependency analysis and CRA configuration
- **4.2 INTEGRATION WORKFLOWS** — Browser-to-Backend integration sequence and CRA proxy
- **4.4 STATE MANAGEMENT** — Component state inventory, fetch lifecycle, tab navigation state machine
- **4.5 ERROR HANDLING FLOWS** — Frontend error state machine and missing recovery features
- **5.1 HIGH-LEVEL ARCHITECTURE** — Frontend tier components, data flows, integration points
- **5.2 COMPONENT DETAILS** — Tracks/Trends/About pipelines, application state transitions, sequence diagram

# 8. Infrastructure

## 8.1 INFRASTRUCTURE OVERVIEW

### 8.1.1 Applicability Assessment

The Hot Stuff repository is a **two-tier monolithic web application** delivered as a **two-container Docker Compose stack** consisting of a Flask `api` service and a sibling PostgreSQL `postgres` service. The infrastructure footprint is deliberately minimal and development-grade: there is no Continuous Integration/Continuous Deployment pipeline, no cloud-provider integration, no Infrastructure-as-Code (IaC) tooling, no container orchestration platform, and no observability framework. Multiple sections of this technical specification (1.3.3, 3.4.4, 3.6.5, 5.4.1, 6.5.1) explicitly classify these absences as out-of-scope for the current solo-maintainer, public-read-only operating model.

This section provides a comprehensive treatment of the topic by:

1. Documenting the **deployment environment** as it actually exists (a generic Docker host).
2. Recording each prompt sub-area (Cloud Services, Orchestration, CI/CD) as **non-applicable where appropriate**, with file-level evidence.
3. Documenting the **containerization configuration** — the only infrastructure layer that *is* applicable — in exhaustive detail.
4. Cataloguing the **monitoring practices** that are currently in effect alongside the deliberate absences.
5. Providing the required Mermaid diagrams (infrastructure architecture, deployment workflow, environment promotion flow, network architecture).
6. Sketching a **production-readiness hardening roadmap** for any future internet-facing deployment.

### 8.1.2 Infrastructure Posture Summary

| Concern | Disposition | Evidence |
|---|---|---|
| Cloud provider integration | Not applicable | No AWS/Azure/GCP SDKs; no managed-service references |
| Infrastructure-as-Code | Not applicable | No Terraform, CloudFormation, Pulumi, or CDK files in repository |
| Container engine | Applicable | `Dockerfile` (15 lines) + `docker-compose.yml` (26 lines) |
| Orchestration platform | Not applicable | No Kubernetes manifests, no Helm chart, no ECS task definitions |
| CI/CD automation | Not applicable | No `.github/workflows/`, `.gitlab-ci.yml`, `.travis.yml`, `Jenkinsfile`, or `.circleci/` |
| Observability framework | Not applicable | No APM, metrics endpoint, structured logger, or error-reporting SDK |
| Backup / Disaster Recovery | Not applicable | No `pg_dump`, no replication, no off-host snapshot |
| Compliance regime | Not applicable | No personal data; GDPR, CCPA, HIPAA, PCI-DSS, SOC 2 all out of scope |

### 8.1.3 Infrastructure Architecture Diagram

The diagram below depicts the **complete infrastructure topology** as it exists in the repository. Items shown with dashed borders represent deliberately absent layers documented elsewhere in this section.

```mermaid
flowchart TB
    User([Anonymous Browser])
    Fonts["Google Fonts CDN<br/>fonts.googleapis.com<br/>fonts.gstatic.com"]

    subgraph Host["Generic Docker Host (on-premises or single-VM)"]
        subgraph Compose["Docker Compose Stack (schema v3)"]
            subgraph ApiSvc["api service (build: .)"]
                Flask["Flask 2.0.1 dev server<br/>python:3.11-slim-buster<br/>CMD: python3 app.py<br/>EXPOSE 5000"]
                Build["frontend/build/<br/>(static SPA assets)"]
                Flask --- Build
            end

            subgraph PgSvc["postgres service (image: postgres:15)"]
                PG[("PostgreSQL 15<br/>db: db<br/>user: postgres")]
            end

            DataMount[("./data host bind-mount<br/>(local-only durability)"]
            BridgeNet["Compose default bridge network<br/>DNS-based service resolution"]

            Flask -- "psycopg2 over TCP 5432<br/>via service name 'postgres'" --> PG
            PG -- "data files" --> DataMount
        end

        DockerLog["Docker engine logging driver<br/>captures stdout/stderr<br/>(default driver)"]
        HostFs[("Host filesystem<br/>./data, image cache")]

        Flask --> DockerLog
        PG --> DockerLog
    end

    subgraph Absent["Deliberately Absent Infrastructure Layers"]
        IaC["Infrastructure-as-Code<br/>Terraform / Pulumi / CDK"]
        CICD["CI/CD Pipeline<br/>GitHub Actions / GitLab / Jenkins"]
        K8s["Orchestrator<br/>Kubernetes / ECS / Nomad"]
        APM["Observability Stack<br/>Prometheus / Grafana / Loki"]
        LB["Reverse Proxy / Load Balancer<br/>nginx / Traefik / Envoy"]
        Backup["Backup System<br/>pg_dump / replication / WAL archive"]
    end

    User -- "HTTP/1.1 plaintext :80<br/>(host port 80 to container 5000)" --> Flask
    User -. "Direct host port 5432:5432<br/>(known security gap)" .-> PG
    User -. "preconnect + stylesheet" .-> Fonts

    classDef absent stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class IaC,CICD,K8s,APM,LB,Backup absent
```

The principal architectural observations:

- The **only inbound network path** is host port 80 → container port 5000 on the `api` service. The `5432:5432` host mapping on the `postgres` service is a development convenience that should be removed before any internet-facing deployment.
- The **only path from application to observable artifact** is `stdout/stderr` → Docker engine logging driver → host log storage.
- **Six categories of production-grade infrastructure** (IaC, CI/CD, orchestration, observability, reverse proxy, and backup) are deliberately absent and depicted as dashed.

---

## 8.2 DEPLOYMENT ENVIRONMENT

### 8.2.1 Target Environment Assessment

#### 8.2.1.1 Environment Type

The system targets a **generic Docker host as its sole deployment substrate**. This is explicitly neither cloud-native nor multi-cloud nor hybrid — it is a single-host Docker Engine deployment that can run on any environment satisfying the minimum requirements (a Docker Engine + Docker Compose plugin combination).

The same `docker-compose.yml` file functions identically across the following deployment substrates without modification:

| Substrate | Suitability | Notes |
|---|---|---|
| Local developer workstation | Primary | The hybrid local-dev workflow uses CRA dev server + Flask outside Docker |
| On-premises Linux VM | Production-feasible | Requires manual hardening per Section 8.12 |
| Single-VM cloud instance (e.g., EC2 t3.small, GCE e2-small, Azure B1s) | Production-feasible | No cloud-native services consumed |
| Container-as-a-Service (e.g., Fly.io, Render) | Adaptable | Database service must be reconfigured |

#### 8.2.1.2 Geographic Distribution Requirements

**No geographic distribution is required.** The Billboard Hot 100 dataset is a United States-published chart, and the application makes no geographic gating decisions; the same content is served to all visitors regardless of locale. There is no multi-region deployment, no edge presence, no Content Delivery Network configuration for application assets, and no geo-routing logic anywhere in the codebase. The single browser-direct external resource (Google Fonts) is itself globally CDN-distributed but served by a third party that does not traverse the application's own infrastructure.

#### 8.2.1.3 Compliance and Regulatory Requirements

The application has no compliance burden because it collects no personal data and has no state-changing operations. Each major regulatory regime is evaluated below:

| Regulation | Applicability | Justification |
|---|---|---|
| GDPR | Not applicable | No personal data collected; no EU-resident data subjects |
| CCPA | Not applicable | No personal data collected; no California-resident profiles |
| HIPAA | Not applicable | No protected health information |
| PCI-DSS | Not applicable | No payment surface; no cardholder data |
| SOC 2 | Out of scope | Solo-maintainer non-commercial scope |
| Cookie-consent regulations | Not applicable | No cookies set by application |

This non-applicability is reinforced by the security architecture: every route in `api/routes.py` is publicly accessible HTTP `GET`, no audit logging exists beyond Werkzeug's default request log, and no user-tracking analytics SDK is installed.

### 8.2.2 Resource Requirements

The Compose configuration declares **no formal resource constraints on either service**. Both containers run subject to the host's defaults. The matrix below catalogs every resource dimension and its current configuration:

| Resource Dimension | Configured Value | Effective Default |
|---|---|---|
| `api` container memory limit | Not declared | Host defaults (cgroup unbounded) |
| `api` container CPU limit | Not declared | Default CFS shares |
| `api` container ulimits | Not declared | Host defaults |
| `postgres` container memory limit | Not declared | Host defaults |
| `postgres` container CPU limit | Not declared | Default CFS shares |
| SQLAlchemy `pool_size` | Not declared | Flask-SQLAlchemy default |
| SQLAlchemy `max_overflow` | Not declared | Flask-SQLAlchemy default |
| SQLAlchemy `pool_recycle` | Not declared | Flask-SQLAlchemy default |
| SQLAlchemy `pool_timeout` | Not declared | Flask-SQLAlchemy default |
| PostgreSQL `shared_buffers` | Not overridden | `postgres:15` image default |
| PostgreSQL `work_mem` | Not overridden | `postgres:15` image default |
| PostgreSQL `max_connections` | Not overridden | `postgres:15` image default (typically 100) |
| Python process memory ceiling | Not enforced | Limited only by host |

**Network Resource Allocation**:

| Mapping | Direction | Purpose |
|---|---|---|
| Host `:80` → `api:5000` | Inbound | Only intended public surface |
| Host `:5432` → `postgres:5432` | Inbound | Development convenience; security gap in production |
| Compose default bridge network | Internal | Service-to-service DNS resolution |

### 8.2.3 Environment Management

#### 8.2.3.1 Infrastructure-as-Code Approach

**No Infrastructure-as-Code tooling is used.** The repository contains no Terraform, CloudFormation, Pulumi, AWS CDK, Bicep, or Ansible artifacts. The closest analog is the pair of files:

- `Dockerfile` — declarative image definition (15 lines)
- `docker-compose.yml` — declarative service composition (26 lines)

These serve as IaC-equivalent at the local Compose level only. Provisioning of the underlying host (operating system, Docker Engine, networking, firewall, TLS termination) is **operator-manual** and not codified anywhere in the repository.

#### 8.2.3.2 Configuration Management Strategy

Configuration is **hardcoded** at multiple layers, which is documented as a known limitation requiring remediation before production deployment:

| Configuration Surface | Location | Current Value |
|---|---|---|
| Database connection URL | `api/__init__.py` line 12 | `postgresql://postgres:postgres@postgres/db` (no env-var fallback) |
| PostgreSQL superuser | `docker-compose.yml` env block | `POSTGRES_USER=postgres` |
| PostgreSQL password | `docker-compose.yml` env block | `POSTGRES_PASSWORD=postgres` |
| PostgreSQL database name | `docker-compose.yml` env block | `POSTGRES_DB=db` |
| Flask host binding | `app.py` | `app.run(host='0.0.0.0')` (port defaults to 5000) |
| Frontend Node options | `docker-compose.yml` | `NODE_OPTIONS=--openssl-legacy-provider` |

Notable discrepancies:

- `python-dotenv==0.18.0` is declared in `requirements.txt` but is **never imported anywhere** in the Python source. The repository contains no `.env` file.
- A `.flaskenv` file exists at the repository root containing only `FLASK_APP=app.py` and `FLASK_ENV=development`. It is consumed only by the `flask run` command in the hybrid local-dev workflow, **not by Docker**.
- The `import os` in `api/__init__.py` is unused — there is no `os.environ.get(...)` call on any configuration variable.

The recommended remediation (per Section 6.4.6.3) is to externalize all credentials via environment variables and to introduce a `config.py` module supporting per-environment configuration.

#### 8.2.3.3 Environment Promotion Strategy

**No multi-environment promotion strategy exists.** The repository supports exactly two interchangeable workflows:

1. **Containerized**: `docker compose up` builds the `api` image, starts both services, and serves the API (which itself serves the React build) at `http://localhost:80`.
2. **Hybrid**: `npm start` inside `frontend/` runs the CRA dev server with hot reload (port 3000), while `npm run start-api` runs Flask outside Docker (port 5000). The CRA `proxy: "http://localhost:5000"` declaration in `frontend/package.json` line 44 forwards API calls during this mode.

Because the database URL is hardcoded and there is no `config.py` or environment-driven settings, **the same configuration is used regardless of which "environment" the stack is deployed to**. There is no semantic distinction between development, staging, and production at the configuration layer.

The Environment Promotion Flow diagram below makes this explicit:

```mermaid
flowchart LR
    Dev[("Developer Workstation<br/>localhost:80<br/>or hybrid 3000+5000")]

    subgraph CurrentReality["Current Repository Reality"]
        SingleEnv[("Single 'environment'<br/>same docker-compose.yml<br/>same hardcoded credentials<br/>no config.py")]
    end

    subgraph FutureState["Recommended Future Promotion Flow (Not Implemented)"]
        DevEnv[("dev environment<br/>env-specific .env<br/>relaxed validation")]
        StagingEnv[("staging environment<br/>env-specific .env<br/>production-like config")]
        ProdEnv[("prod environment<br/>secrets via vault<br/>strict config")]
        DevEnv -->|promote artifact| StagingEnv
        StagingEnv -->|promote artifact| ProdEnv
    end

    Dev -- "docker compose up" --> SingleEnv
    SingleEnv -. "Migration trigger:<br/>multi-stakeholder deployment" .-> DevEnv

    classDef future stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class DevEnv,StagingEnv,ProdEnv future
```

#### 8.2.3.4 Backup and Disaster Recovery Plans

The repository's disaster recovery posture is **deliberately minimal**, with a single resilience primitive (the `restart: on-failure` policy on the `api` service). The matrix below documents each failure class:

| Failure Class | Implementation | Recovery Time | Recovery Type |
|---|---|---|---|
| `api` container exits non-zero | Compose `restart: on-failure` | Seconds (Docker backoff) | Automatic |
| `api` container hung but running | None (no healthcheck) | Indefinite | Manual operator detection |
| `postgres` container exits | None (no restart policy) | Indefinite | Manual `docker compose start postgres` |
| `./data` bind-mount corruption | None (no backup) | Unrecoverable | Data loss |
| Host failure | None (no HA) | Hours-to-days | Full re-provisioning |
| Failed deploy | None (no automated rollback) | Operator-dependent | Manual re-run of older image |

Critical infrastructure-level absences:

- **No `pg_dump` schedule** — no cron, systemd timer, or Compose backup service.
- **No streaming replication** — no `recovery.conf`, no replica `postgres` container.
- **No continuous WAL archiving** — no `archive_command` configured.
- **No off-host snapshot** of `./data` — the bind-mount is local-only durability.
- **No point-in-time recovery** — requires WAL archiving.
- **No `volumes:` named volume use** — the `volumes: data:` declaration on lines 25-26 of `docker-compose.yml` is a top-level name reservation that is **not consumed** by either service. The actual mount is the bind-mount `./data:/data` on the `postgres` service.

The `api` container's bootstrap defers DB connection until the first request, so an `api`-restart-after-`postgres`-crash sequence will succeed at boot time and then begin failing at first request until `postgres` is manually restarted.

---

## 8.3 CLOUD SERVICES

### 8.3.1 Non-Applicability Statement

**Cloud Services are not applicable for this system.**

Section 3.4.5 of this specification explicitly states that the repository targets a generic Docker host as its sole deployment substrate. The selection of a single-host monolith deployment (ADR-001) was driven by the solo-maintainer operational model, the read-only public dataset, and the absence of bounded contexts to split — none of which warrant cloud-managed infrastructure.

### 8.3.2 Cloud Service Verification Matrix

The matrix below documents the absence of cloud-provider integration, with the verification evidence supporting each "Not Present" designation:

| Cloud Service Class | Status | Verification Evidence |
|---|---|---|
| AWS SDK (`boto3`, `aws-sdk`) | Not present | Absent from `requirements.txt` and `frontend/package.json` |
| Azure SDK (`azure-*`) | Not present | Absent from both dependency manifests |
| GCP SDK (`google-cloud-*`) | Not present | Absent from both dependency manifests |
| Terraform / CloudFormation / Pulumi / CDK | Not present | No `*.tf`, `*.yaml` (CFN), or CDK files in repository |
| Object storage (S3, Azure Blob, GCS) | Not present | No object-store SDKs; static assets served from Flask |
| Managed databases (RDS, CloudSQL, Cosmos DB) | Not configured | PostgreSQL runs as a Compose service |
| Serverless / FaaS (Lambda, Cloud Functions) | Not present | No serverless framework or handlers |
| Container registries (ECR, ACR, GCR) | Not configured | `build: .` rebuilds locally; no registry push |
| Managed Kubernetes (EKS, AKS, GKE) | Not configured | No `k8s/` directory; no manifests |
| Cloud monitoring (CloudWatch, Stackdriver, App Insights) | Not configured | No vendor SDKs |

### 8.3.3 Browser-Loaded External Resources (CDN-Adjacent)

The single external resource consumed by the deployed application at runtime is **Google Fonts** (the Jost typeface), loaded directly by the browser via `<link rel="preconnect">` and a stylesheet from `fonts.googleapis.com` and `fonts.gstatic.com`. This traffic is browser-direct and **never traverses the Flask container or any infrastructure controlled by this repository**. It is mentioned here for completeness but does not constitute a cloud-service dependency in the architectural sense.

---

## 8.4 CONTAINERIZATION

### 8.4.1 Container Platform Selection

The system uses **Docker** for image construction and **Docker Compose** for local orchestration. The Compose file declares schema version `"3"` (the historical Compose v3 schema, rather than the modern Compose Specification format). Both selections are operationally minimal and require no platform licenses or cloud-specific extensions.

| Component | Selection | Rationale |
|---|---|---|
| Image build engine | Docker Engine | Industry-standard; no proprietary alternative considered |
| Stack composition | Docker Compose (schema v3) | Single-file declarative two-service stack; `depends_on` enforces start order |
| Image registry | None (local build only) | `build: .` rebuilds image on each `docker compose up`; no registry push |
| Runtime networking | Compose default bridge | Provides DNS-based service-name resolution |

### 8.4.2 Base Image Strategy

The repository pins both base images to specific tags (no `latest` references), establishing reproducibility while currently lagging behind upstream support windows.

#### 8.4.2.1 Backend `api` Service Base Image

The Dockerfile declares `FROM python:3.11-slim-buster` on line 1. This pins:

- **Python interpreter**: 3.11 (the minor version of the official `python` image at the time the tag was published).
- **Operating system**: Debian 10 ("Buster"), slimmed variant with reduced default-installed packages.

Native build dependencies are installed via `apt-get install -y libpq-dev gcc` to support compilation of the `psycopg2` Python driver from source.

**Known limitation**: Section 6.4.4.2 documents that "The base image `python:3.11-slim-buster` is built on Debian Buster, which has reached its standard support end-of-life and should be updated to a current Debian release before production deployment." A migration to `python:3.11-slim-bookworm` (Debian 12) or `python:3.12-slim-bookworm` is the recommended hardening step.

#### 8.4.2.2 Database `postgres` Service Image

The `postgres` service uses `image: postgres:15` (line 16 of `docker-compose.yml`), pulling the official `postgres` image from Docker Hub. This is a major-version pin — Docker Hub will resolve `postgres:15` to the most recent 15.x patch release at pull time, which is appropriate for the data tier.

### 8.4.3 Image Versioning Approach

The repository pins **all dependency layers** but does **not version the built application image**:

| Layer | Pinning Mechanism | Pinning Type |
|---|---|---|
| Backend base image | `python:3.11-slim-buster` | Major.minor + OS pin |
| Database image | `postgres:15` | Major-version pin |
| Python packages | `requirements.txt` (23 packages with `==` constraints) | Exact version pin |
| JavaScript packages | `frontend/package.json` + `package-lock.json` | Reproducible install |
| Built `api` image | None | `build: .` rebuilds locally; no tag |

The absence of registry-pushed image tags means there is **no immutable artifact** that can be rolled back to. A "rollback" today consists of checking out an older Git commit and re-running `docker compose up --build`, which depends on the historical state of base images and PyPI/npm registries remaining available.

### 8.4.4 Build Optimization Techniques

The `Dockerfile` employs two layer-caching optimizations that are appropriate for a single-stage development build:

#### 8.4.4.1 Layer Cache Optimization Sequence

The build sequence is structured to maximize Docker layer cache hits on source-only changes:

```mermaid
flowchart TD
    L1["Layer 1: FROM python:3.11-slim-buster<br/>(cached unless base image changes)"]
    L2["Layer 2: WORKDIR /app<br/>(metadata only)"]
    L3["Layer 3: apt-get install libpq-dev gcc<br/>(cached unless base changes)"]
    L4["Layer 4: COPY requirements.txt<br/>(cached unless dependencies change)"]
    L5["Layer 5: pip3 install -r requirements.txt<br/>(cached unless requirements.txt changes)"]
    L6["Layer 6: COPY . .<br/>(invalidated on any source change)"]
    L7["Layer 7: EXPOSE 5000<br/>(metadata only)"]
    L8["Layer 8: CMD python3 app.py<br/>(metadata only)"]

    L1 --> L2 --> L3 --> L4 --> L5 --> L6 --> L7 --> L8
```

The critical optimization is the placement of `COPY requirements.txt requirements.txt` **before** `COPY . .`, ensuring that source-only changes do not invalidate the expensive `pip3 install` layer. Section 6.1.3.4 lists this layer-cached pip install pattern as one of the few performance optimizations actively present in the codebase.

#### 8.4.4.2 Build Context Exclusions

The `.dockerignore` file at the repository root contains three entries that reduce build-context size and prevent host artifacts from leaking into images:

| Excluded Path | Purpose |
|---|---|
| `/frontend/node_modules` | Excludes the npm dependency tree (rebuilt elsewhere) |
| `/venv` | Excludes any local Python virtualenv |
| `/data` | Excludes the PostgreSQL data directory bind-mount |

### 8.4.5 Service Configuration Reference

The Compose stack defines two services, summarized below:

| Property | `api` Service | `postgres` Service |
|---|---|---|
| Build / Image source | `build: .` (uses repo `Dockerfile`) | `image: postgres:15` |
| Restart Policy | `on-failure` | (none — known limitation) |
| Depends On | `postgres` | n/a |
| Environment Variables | `NODE_OPTIONS=--openssl-legacy-provider` | `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` |
| Published Ports | `80:5000` (host:container) | `5432:5432` (host:container) |
| Volumes | `.:/app/` (live-reload bind-mount) | `./data:/data` (data persistence) |

Notable behaviors:

- The `.:/app/` bind-mount on the `api` service enables live source reload during development — any host file edit is visible inside the container, but it also means that **the running container reflects whatever is in the host working directory**, not necessarily the contents of the built image.
- The `5432:5432` mapping exposes the database port directly to the host. Section 2.4.4 flags this as a development convenience that should be removed in production.
- The `NODE_OPTIONS=--openssl-legacy-provider` value accommodates an OpenSSL 3 incompatibility in Webpack 4 when the CRA dev server is run inside a Node 17+ environment.

### 8.4.6 Security Scanning and Hardening Gaps

The container layer has several documented security gaps that are out-of-scope for the current deployment but require remediation before any internet-facing production use:

| Hardening Gap | Status | Severity | Reference |
|---|---|---|---|
| Image vulnerability scanning (Trivy, Grype, Snyk) | Not implemented | Medium | Section 6.4.6.2 (deferred — no CI/CD) |
| Software Bill of Materials (SBOM) generation | Not implemented | Low | Not required at current scope |
| Non-root `USER` directive in Dockerfile | Not present | Medium | Section 6.4.4.2 (Flask runs as `root` inside container) |
| `HEALTHCHECK` instruction in Dockerfile | Not present | Medium | Sections 5.4.6, 6.1.4.1 |
| Compose `healthcheck:` block | Not present | Medium | Section 5.4.6 |
| Multi-stage build to reduce image surface | Not used | Low | Single-stage build; `gcc` and `libpq-dev` remain in image |
| Read-only root filesystem (`read_only: true`) | Not configured | Low | Default writable rootfs |
| Capability drop (`cap_drop: ALL`) | Not configured | Low | Default capability set |
| `seccomp` / `apparmor` profiles | Not configured | Low | Docker defaults apply |

The complete `Dockerfile` content is reproduced below for reference:

```
FROM python:3.11-slim-buster
WORKDIR /app
RUN apt-get update \
    && apt-get -y install libpq-dev gcc
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .
EXPOSE 5000
CMD [ "python3", "app.py"]
```

The complete `docker-compose.yml` content is reproduced below for reference:

```yaml
version: "3"
services:
  api:
    restart: on-failure
    build: .
    depends_on:
      - postgres
    environment:
      - NODE_OPTIONS=--openssl-legacy-provider
    ports:
      - "80:5000"
    volumes:
      - .:/app/

  postgres:
    image: postgres:15
    ports:
      - "5432:5432"
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: db
    volumes:
      - ./data:/data
volumes:
  data:
```

---

## 8.5 ORCHESTRATION

### 8.5.1 Non-Applicability Statement

**Container Orchestration is not applicable for this system.**

The decision to operate the application as a single-replica two-tier monolith on a Docker Compose host (ADR-001 in Section 5.3.6) explicitly rejects the introduction of an orchestrator at the current scope. Per Section 5.3.1's architecture-style decision matrix, microservices were rejected because there are "no bounded contexts to split; would multiply ops surface."

### 8.5.2 Orchestration Verification Matrix

| Orchestration Primitive | Status | Verification Evidence |
|---|---|---|
| Kubernetes manifests | Absent | No `k8s/`, `manifests/`, or `deploy/` directory |
| Helm chart | Absent | No `Chart.yaml`, no `values.yaml`, no `templates/` |
| Kustomize overlays | Absent | No `kustomization.yaml` |
| ECS / Fargate task definitions | Absent | No `task-definition.json`; no AWS SDK |
| Nomad job specifications | Absent | No `*.nomad` HCL files |
| Docker Swarm mode | Not used | No `deploy:` blocks in `docker-compose.yml` |
| Compose replica scaling | Absent | No `deploy.replicas` in `docker-compose.yml` |
| HorizontalPodAutoscaler | Absent | No K8s artifacts to define HPA against |
| Service mesh (Istio, Linkerd) | Absent | No mesh control plane; no sidecar injection |
| Ingress controller | Absent | Direct host port mapping `80:5000` |

### 8.5.3 Compose-Native Service Discovery

The closest "orchestration" primitive present in the system is **Docker Compose's built-in DNS-based service-name resolution**:

- The connection string in `api/__init__.py` line 12 references the literal hostname `postgres` (the Compose service name).
- Compose's default bridge network resolves `postgres` to the IP address of the `postgres` container.
- No external service registry (Consul, etcd, ZooKeeper, Eureka), no service mesh control plane, and no client-side discovery library is present or required.

The `depends_on: - postgres` directive on the `api` service ensures that the `postgres` container is started first, but it does **not wait for PostgreSQL to be ready to accept connections** — Compose v3 `depends_on` is start-order-only without a `condition: service_healthy` clause (which itself requires a `healthcheck:` block that is also absent). The `api` container's bootstrap defers database connection until the first request, which masks this limitation in practice.

### 8.5.4 Migration Trigger to a Real Orchestrator

Per ADR-006 in Section 5.3.6, the revisit trigger for this decision is "Before any internet-facing production deployment." Migration would require:

1. Switching the `Dockerfile` `CMD` from `python3 app.py` to `gunicorn` to enable multi-worker concurrency.
2. Adding `/healthz` and `/readyz` endpoints to support orchestrator probes.
3. Externalizing all configuration via environment variables to support per-environment routing.
4. Authoring Kubernetes manifests, an ECS task definition, or equivalent — none of which currently exist.

---

## 8.6 CI/CD PIPELINE

### 8.6.1 Pipeline Status Assessment

**No CI/CD pipeline is implemented.** Section 1.3.3 lists CI/CD pipelines as an explicit non-goal of this specification. The repository contains no automation configuration files for any major CI/CD provider:

| Provider | Expected Path | Status |
|---|---|---|
| GitHub Actions | `.github/workflows/` | Not present |
| GitLab CI | `.gitlab-ci.yml` | Not present |
| Travis CI | `.travis.yml` | Not present |
| CircleCI | `.circleci/config.yml` | Not present |
| Jenkins | `Jenkinsfile` | Not present |
| Azure DevOps | `azure-pipelines.yml` | Not present |
| Bitbucket Pipelines | `bitbucket-pipelines.yml` | Not present |

The only YAML file present in the repository (excluding `node_modules` and `.git` internals) is `docker-compose.yml`. All build, test, and deployment activity is therefore **manual operator-driven**.

### 8.6.2 Build Pipeline (Manual)

The manual build workflow is documented below for completeness, even though no automation triggers it.

#### 8.6.2.1 Source Control Triggers

**None.** No push, pull-request, tag, or scheduled triggers exist. Source control is `git` (per the presence of `.git/` and `.gitignore` at the repository root), but no Git hooks, no `pre-commit` framework, and no branch-protection rules are codified in the repository.

#### 8.6.2.2 Build Environment Requirements

The build environment is implicit in the `Dockerfile` and `frontend/package.json`:

| Build Tier | Tool | Version |
|---|---|---|
| Backend container | Python | 3.11 (via `python:3.11-slim-buster`) |
| Backend container | `pip3` | bundled with the slim-buster image |
| Backend container native deps | `libpq-dev`, `gcc` | apt installed during build |
| Frontend production build | Node.js | 14+ (with `--openssl-legacy-provider` on Node 17+) |
| Frontend production build | `npm` | bundled with Node |
| Frontend lint | ESLint | bundled inside `react-scripts` 4.0.3 |

#### 8.6.2.3 Dependency Management

| Tier | Manifest | Lock File | Pinning Strategy |
|---|---|---|---|
| Python | `requirements.txt` | None (no `requirements.lock`, no Poetry/PDM) | 23 packages with exact `==` versions |
| JavaScript | `frontend/package.json` | `frontend/package-lock.json` | Semver ranges in manifest; exact versions in lock |

Notable cosmetic discrepancies in the dependency manifests:

- `gunicorn==20.1.0` is declared in `requirements.txt` but never invoked by the `Dockerfile` `CMD` (ADR-006).
- `python-dotenv==0.18.0` is declared but never imported anywhere in the Python source.
- `axios` is declared in `frontend/package.json` but never imported anywhere in the JavaScript source (ADR-003).
- `web-vitals: ^1.0.1` is declared in `frontend/package.json` but never wired into a `reportWebVitals()` callback.
- `plotly.js` and `react-plotly.js` are declared but never imported (amCharts is used instead).

#### 8.6.2.4 Artifact Generation

Two distinct artifact production processes occur:

**Backend artifact**: A Docker image is built **locally** via `build: .` in `docker-compose.yml`. There is no image registry push, no image signing, and no image tagging strategy. Each `docker compose up` invocation rebuilds the image against the current state of the repository (subject to `.dockerignore`).

**Frontend artifact**: The `react-scripts build` command emits production assets to `frontend/build/`:

| Artifact | Purpose |
|---|---|
| `index.html` | SPA shell loaded by Flask at the `/` route |
| `asset-manifest.json` | Maps logical asset names to hashed chunk filenames |
| `manifest.json` | PWA web app manifest |
| `static/css/*.css` | Hashed CSS chunks with sourcemaps |
| `static/js/*.js` | Hashed JavaScript chunks with sourcemaps and `*.LICENSE.txt` sidecars |

The frontend build **must exist at container start time** because the Flask app is configured with `static_folder='../frontend/build'` in `api/__init__.py`. This creates a build-order coupling that is not enforced by the Dockerfile or Compose configuration.

#### 8.6.2.5 Quality Gates

**No quality gates exist.** Specifically:

| Gate | Status | Evidence |
|---|---|---|
| Unit test execution | Not configured | No test files in `frontend/src/`; no Python test framework declared |
| Coverage threshold | Not configured | No coverage tooling |
| Static analysis (linting) | Frontend ESLint declared, not enforced | No `npm run lint` script invocation in any build path |
| Type checking | Not applicable | Project is JavaScript/Python without explicit type-checking tooling |
| Security scanning | Not configured | No SAST, no dependency-scan, no image-scan |
| License compliance | Not configured | No license-check tooling |

Section 3.6.7 confirms that no automated tests exist, despite the CRA-default Jest + Testing Library stack (`@testing-library/jest-dom`, `@testing-library/react`, `@testing-library/user-event`) being declared in `frontend/package.json`.

### 8.6.3 Deployment Pipeline (Manual)

#### 8.6.3.1 Deployment Strategy

The deployment strategy is **manual `docker compose up` against a target host**. There is no blue-green deployment, no canary release, no rolling deployment, no traffic shifting, and no progressive delivery framework. A deployment is performed by:

```mermaid
flowchart TD
    Start([Code Change]) --> Pull["Operator: git pull on target host"]
    Pull --> Stop["Operator: docker compose down<br/>(brief downtime begins)"]
    Stop --> Build["Operator: docker compose up --build -d<br/>(image rebuild + container restart)"]
    Build --> StartPg["postgres container starts<br/>(no readiness check)"]
    StartPg --> StartApi["api container starts<br/>(depends_on satisfied at start-order only)"]
    StartApi --> Verify["Operator: manual smoke test<br/>(curl localhost / and /api/week/<week>)"]
    Verify --> OkBranch{Smoke<br/>OK?}
    OkBranch -->|Yes| Done([Deployment complete])
    OkBranch -->|No| Rollback["Operator: git checkout older commit<br/>+ docker compose up --build -d"]
    Rollback --> Verify
```

#### 8.6.3.2 Environment Promotion Workflow

**No environment promotion workflow exists** — there is exactly one deployable target. Per Section 8.2.3.3, the database URL is hardcoded and the same configuration is used regardless of the deployment substrate.

#### 8.6.3.3 Rollback Procedures

Per Section 5.4.6: "Manual rollback by re-running an older image; Operator-dependent." The practical rollback procedure is:

1. Operator identifies a known-good Git commit (e.g., the previous deployment's commit hash).
2. Operator runs `git checkout <commit>` on the target host.
3. Operator runs `docker compose down` followed by `docker compose up --build -d`.
4. Operator manually verifies the rollback was successful by hitting the application surface.

**No rollback automation, no rollback testing, and no rollback time-bounding** is configured. There is no immutable image artifact preserved in a registry to roll back to — each rebuild is fresh.

#### 8.6.3.4 Post-Deployment Validation

**No post-deployment validation is codified.** Specifically:

| Validation Surface | Status | Note |
|---|---|---|
| `/healthz` or `/readyz` endpoint | Not implemented | No such route in `api/routes.py` |
| Smoke test suite | Not present | No `tests/smoke/` or equivalent |
| Synthetic transaction probe | Not configured | No external check |
| Deployment success telemetry | Not emitted | No CI/CD pipeline to receive |
| Rollback decision threshold | Not codified | Manual operator judgment only |

#### 8.6.3.5 Release Management Process

**No formal release management process is documented.** There is no `CHANGELOG.md`, no Git tagging convention, no release-notes template, and no semantic-versioning practice codified in the repository. The footer marker `AUG | 2021` in the SPA suggests a single-point-in-time release.

### 8.6.4 Deployment Workflow Diagram

```mermaid
flowchart TB
    subgraph Dev["Developer Workstation"]
        Code["Source code change"]
        Commit["git commit"]
        Push["git push origin"]
        Code --> Commit --> Push
    end

    subgraph CICDAbsent["Deliberately Absent CI/CD Layers"]
        Trigger["CI Trigger<br/>(no .github/workflows/)"]
        TestStage["Test Stage<br/>(no test files)"]
        BuildStage["Build Stage<br/>(no automated image build)"]
        Registry["Image Registry<br/>(no registry push)"]
        Promotion["Environment Promotion<br/>(no staging environment)"]
    end

    subgraph Target["Target Docker Host"]
        OpPull["Operator: git pull"]
        OpDown["Operator: docker compose down"]
        OpUp["Operator: docker compose up --build -d"]
        ApiContainer["api container"]
        PgContainer["postgres container"]
        DataDir["./data bind-mount"]

        OpPull --> OpDown --> OpUp
        OpUp --> ApiContainer
        OpUp --> PgContainer
        PgContainer --> DataDir
    end

    Push -. "no webhook" .-> Trigger
    Trigger -. "no test exec" .-> TestStage
    TestStage -. "no build" .-> BuildStage
    BuildStage -. "no push" .-> Registry
    Registry -. "no promotion" .-> Promotion

    Push -- "operator notices push<br/>and SSH-es to host" --> OpPull

    classDef absent stroke-dasharray: 5 5,fill:#f9f9f9,stroke:#999,color:#666;
    class Trigger,TestStage,BuildStage,Registry,Promotion absent
```

---

## 8.7 INFRASTRUCTURE MONITORING

### 8.7.1 Resource Monitoring

**No resource monitoring infrastructure is configured.** Per Section 6.5.1.1, the repository contains no observability instrumentation of any kind: no APM agent, no error-reporting SDK, no metrics endpoint, no health-check endpoints, no distributed tracing client, no structured logger, and no log-aggregation forwarder.

| Monitoring Concern | Status | Verification Evidence |
|---|---|---|
| Structured logging library (`structlog`, `loguru`) | Not present | Absent from `requirements.txt` |
| Metrics endpoint (Prometheus, statsd) | Not present | No `prometheus-client`; no `/metrics` route in `api/routes.py` |
| APM agent (DataDog, New Relic, AppDynamics) | Not present | No vendor SDKs in dependency manifests |
| Error reporting (Sentry, Rollbar, Bugsnag) | Not present | No SDK in `requirements.txt` or `frontend/package.json` |
| Real-User Monitoring (web-vitals reporting) | Declared but unwired | `web-vitals: ^1.0.1` in `package.json` line 17; no `reportWebVitals()` call in `frontend/src/index.js` |
| Container resource exporter (`cadvisor`) | Not configured | No service in `docker-compose.yml` |
| Database exporter (`postgres_exporter`) | Not configured | No service in `docker-compose.yml` |

### 8.7.2 Performance Metrics Collection

**No performance metrics are emitted.** Per Section 6.5.3.2, the codebase contains no histogram timers, no request-counter middleware, no per-route latency capture, and no Real-User Monitoring on the frontend. The performance bounds documented elsewhere in this specification are observable from code structure, not measured at runtime.

### 8.7.3 Cost Monitoring

**Cost monitoring is not applicable.** The single-host Docker deployment model has no cloud-provider billing API to integrate with. Operating costs are limited to the host's infrastructure cost (see Section 8.8) and are constant rather than usage-driven.

### 8.7.4 Security Monitoring

**No formal security monitoring is configured.** Per Section 6.4.5.2, "the single observable audit trail is Flask's default Werkzeug request log on stdout, captured by the Docker engine's logging driver." Specifically:

| Security Monitoring Surface | Status |
|---|---|
| `pgaudit` extension on PostgreSQL | Not enabled |
| Per-table change-tracking triggers | Not declared |
| Application-level `audit_log` table | Does not exist (per Section 6.2.4.4) |
| Web Application Firewall (WAF) | Not deployed |
| Intrusion Detection System (IDS) | Not deployed |
| File-integrity monitoring | Not configured |
| Failed-authentication tracking | Not applicable (no authentication) |

### 8.7.5 Compliance Auditing

**Compliance auditing is not applicable** because no compliance regime applies to this system (per Section 8.2.1.3). No audit framework, no compliance dashboard, and no evidence-collection automation is configured.

### 8.7.6 Currently Effective Monitoring Practices

Despite the absence of a formal monitoring framework, a small set of observation surfaces arises from default behaviors of Flask, PostgreSQL, and the Docker engine. These are the **only** monitoring practices currently in effect:

| Practice | Implementation | Captured Information |
|---|---|---|
| Flask request logging | Werkzeug's default per-request stdout line | HTTP method, path, status code, timestamp |
| PostgreSQL stdout | `postgres:15` image's default logging configuration | Server lifecycle messages, connection events |
| Docker engine logging driver | Default driver captures both containers' stdout/stderr | Per-container log streams on host log storage |
| Compose process recovery | `restart: on-failure` on the `api` service only | Automatic relaunch after non-zero exit |
| Flask exception traceback dumps | Python tracebacks printed to stderr on uncaught exception | Exception class, traceback, source line |

The complete inventory of operator-visible state surfaces:

| Surface | Access Method | Information Available |
|---|---|---|
| `docker compose ps` | Host shell | Service names, container IDs, port mappings, current state |
| `docker logs api` | Host shell | Werkzeug request log + Python tracebacks |
| `docker logs postgres` | Host shell | PostgreSQL server lifecycle and connection events |
| `docker stats` | Host shell | Live CPU / memory / I/O per container (no historical view) |
| Browser DevTools Network tab | Per-user browser | Per-fetch HTTP method, status, timing |
| Browser DevTools Console tab | Per-user browser | Unhandled promise rejections from `fetch()` failures |

The Browser DevTools entries are **per-user surfaces** — there is no operator view aggregating across all users.

---

## 8.8 INFRASTRUCTURE COST ANALYSIS

### 8.8.1 Current Cost Profile

The current deployment model has a **flat, low-bound cost envelope** because no usage-based cloud services are consumed. The operating cost is dominated by the host's infrastructure cost.

#### 8.8.1.1 Local Workstation Deployment (Development)

| Cost Component | Estimated Monthly Cost |
|---|---|
| Workstation infrastructure | $0 (already owned) |
| Docker Desktop / Docker Engine | $0 (free for personal/small business) |
| Software licenses | $0 (all stack components are open source) |
| **Total** | **$0/month** |

#### 8.8.1.2 Single-VM Cloud Deployment (Hypothetical Internet-Facing)

A single-VM cloud deployment of the current Compose stack — **not currently configured**, but representative of the minimum-viable production posture — would incur the following approximate cost (based on small-instance public cloud pricing as of the specification date):

| Cost Component | Sizing Recommendation | Approximate Monthly Cost (USD) |
|---|---|---|
| Compute (Linux VM) | 1 vCPU, 2 GB RAM (e.g., AWS t3.small, GCE e2-small, Azure B1ms) | $15 – $20 |
| Block storage for `./data` | 20 GB SSD | $2 – $3 |
| Outbound network egress | <10 GB/month at low traffic | $1 (often free under provider allowance) |
| Public IPv4 address | 1 static IP | $3 – $4 |
| Domain name (optional) | 1 domain | $1 (annualized) |
| TLS certificate (Let's Encrypt) | n/a | $0 |
| **Total** | — | **~$22 – $28/month** |

This estimate assumes no managed-database upgrade, no CDN, no observability stack, and no backup-target storage — all of which are part of the recommended hardening sequence in Section 8.12 and would add incremental cost.

### 8.8.2 Future-State Cost Estimates (Production Hardening)

Should the hardening recommendations in Section 8.12 be implemented, the following incremental costs would apply:

| Hardening Step | Estimated Additional Monthly Cost |
|---|---|
| Managed PostgreSQL (e.g., AWS RDS db.t3.micro) | $15 – $25 |
| Off-host backup storage (S3 / equivalent for `pg_dump` output) | $1 – $5 |
| Container registry (private images) | $0 – $5 (often free tier) |
| Observability stack (self-hosted Loki + Grafana on same VM) | $0 (CPU/RAM headroom) |
| Observability stack (managed e.g., Datadog, Grafana Cloud) | $15 – $50 (free tier may suffice) |
| Error reporting (Sentry free tier, ≤5K events/month) | $0 |
| TLS termination via Let's Encrypt + reverse proxy | $0 |
| **Total** (self-hosted observability) | **~$40 – $60/month all-in** |
| **Total** (managed observability) | **~$55 – $110/month all-in** |

### 8.8.3 Cost Optimization Strategy

Cost optimization is largely tautological at the current scope — there are no cloud services consumed, so there is nothing to optimize. For the future-state production posture, the relevant cost-control levers are:

- **Single-VM deployment** (rather than multi-VM HA pair) until traffic warrants horizontal scaling.
- **Self-hosted observability** (Loki + Grafana on the same VM) in lieu of managed APM until query volume justifies migration.
- **Free-tier services** for non-critical paths (Let's Encrypt for TLS, Sentry free tier for errors).
- **PostgreSQL on the same VM** rather than managed RDS until the operational cost of self-managed exceeds the price gap.
- **Container image rebuild on deploy** rather than registry-tagged images, accepting the rollback-fidelity tradeoff at low scope.

---

## 8.9 EXTERNAL DEPENDENCIES

### 8.9.1 Runtime External Dependencies

The system has **one external runtime dependency**: Google Fonts, loaded directly by the browser.

| Dependency | Type | Required by |
|---|---|---|
| Google Fonts (Jost typeface) | Browser-loaded HTTPS resource | SPA stylesheet (`<link rel="preconnect">` + stylesheet) |

This dependency is browser-direct — the Flask container has no outbound dependency on Google Fonts and would continue to serve the SPA correctly even if Google Fonts were unreachable (the browser would fall back to system fonts).

### 8.9.2 Build-Time External Dependencies

| Dependency | Type | Frequency of Access |
|---|---|---|
| Docker Hub | Image registry (pull) | On `docker compose up --build` |
| `python:3.11-slim-buster` base image | Container base | On image build |
| `postgres:15` image | Container image | On `docker compose up` |
| Debian Buster apt repositories | Package source | During `apt-get install libpq-dev gcc` |
| PyPI (pypi.org) | Python package source | During `pip3 install -r requirements.txt` |
| npm registry (registry.npmjs.org) | JavaScript package source | During frontend build |

### 8.9.3 Out-of-Repository Pipeline Dependencies

Section 5.1.1 documents that an external scraper pipeline (Billboard scraper + Spotipy enrichment) writes directly to the PostgreSQL database, bypassing the `api` container. This pipeline is **out of this repository's scope** but is a logical infrastructure dependency for the read-side of the application: without it, the `tracks` and `yearly_avg` tables would be empty and the API would return 200 responses with empty arrays (or 500s for `/api/analysis/<feature>` due to the `IndexError` documented in Section 5.4.3).

---

## 8.10 RESOURCE SIZING GUIDELINES

The system's resource envelope is structurally bounded by the data shape of the Hot 100 chart and the single-threaded Flask development server. The matrix below provides sizing guidance for current and near-term deployment scenarios.

### 8.10.1 Compute Sizing Recommendations

| Deployment Scenario | vCPU | RAM | Justification |
|---|---|---|---|
| Local development workstation | 2+ vCPU | 4 GB+ | Hosts Docker Desktop + IDE + browser concurrently |
| Single-user production demo | 1 vCPU | 1 GB | Single-threaded Flask + small PostgreSQL footprint |
| Low-traffic internet-facing (< 10 concurrent users) | 1 vCPU | 2 GB | Provides headroom for amCharts-induced PostgreSQL CPU spikes |
| Moderate-traffic internet-facing (10-100 concurrent users) | 2 vCPU | 4 GB | Requires migration to gunicorn (per ADR-006) before this scale matters |
| High-traffic internet-facing (> 100 concurrent users) | Out of scope | Out of scope | Requires architecture change per Section 6.1.3.6 |

### 8.10.2 Storage Sizing Recommendations

| Storage Tier | Recommendation | Rationale |
|---|---|---|
| `./data` PostgreSQL bind-mount | 20 GB SSD | Tracks table grows ≤100 rows × ~1 row/week × decades; well under 1 GB realistically |
| Image cache | 5 GB | `python:3.11-slim-buster` (~150 MB) + `postgres:15` (~370 MB) + build layers |
| Log retention (host) | 1 GB / month at low traffic | Werkzeug per-request logs at default verbosity |
| Backup target (recommended) | 5 GB / year | Daily `pg_dump` compressed; growth bounded by the row counts above |

### 8.10.3 Network Sizing Recommendations

The application's network footprint is dominated by the React bundle and amCharts chart payloads. Approximate per-request sizes:

| Request | Approximate Payload Size |
|---|---|
| Initial SPA load (`/` → `index.html` + bundles) | ~500 KB – 1 MB (compressed) |
| `GET /api/week/<week>` response | ~10 – 30 KB JSON (≤100 rows) |
| `GET /api/analysis/<feature>` response | ~3 – 8 KB JSON (≤~70 rows) |
| `GET /api/track/<id>` response | <1 KB JSON |
| `GET /api/artist/<name>` response | Variable, typically <50 KB |

For a low-traffic deployment (~100 unique visitors/day), monthly egress is well under 10 GB and falls within the typical free-tier allowance of major cloud providers.

---

## 8.11 MAINTENANCE PROCEDURES

### 8.11.1 Routine Maintenance

The repository does not codify a formal maintenance schedule, but the following operator-driven activities are implicit:

| Maintenance Activity | Recommended Frequency | Procedure |
|---|---|---|
| Base image refresh (`python:3.11-slim-buster` → newer Debian) | Quarterly | Update `Dockerfile` `FROM` directive; rebuild and redeploy |
| Python dependency updates | Quarterly | Update `requirements.txt`; manual smoke test |
| Frontend dependency updates | Quarterly | `npm update` inside `frontend/`; manual smoke test |
| PostgreSQL major version upgrade | As-needed (15 → 16) | Update `image:` tag; backup `./data`; manual migration |
| Disk-space audit on `./data` | Monthly | `du -sh data/` on host |
| Container log review | As-needed | `docker logs --since 24h api` for recent errors |
| Manual backup of `./data` | Weekly (recommended) | `pg_dump` from inside `postgres` container, stored off-host |

### 8.11.2 Incident Response Procedures (Implicit Runbook)

The repository contains no `runbooks/` or `docs/operations/` folder; operator knowledge lives implicitly in the README, the Compose file, and the Dockerfile. The implicit recovery procedures derivable from the codebase (per Section 6.5.4.3) are:

| Failure Scenario | Implicit Recovery Procedure |
|---|---|
| `api` container exits non-zero | Compose `restart: on-failure` relaunches automatically |
| `api` container hung but running | Manual `docker compose restart api` (no healthcheck to detect) |
| `postgres` container exits | Manual `docker compose start postgres` (no restart policy) |
| `./data` bind-mount corruption | Unrecoverable without external backup |
| Host failure | Full re-provisioning; redeploy via `docker compose up` |
| Database connection lost mid-flight | Next request returns 500; user retries via form re-submit |
| Invalid feature on `/api/analysis/<feature>` | Frontend `setError(statusText)`; user re-selects via FeatureSelect |

---

## 8.12 PRODUCTION READINESS GAPS AND HARDENING ROADMAP

This subsection consolidates the production-readiness gaps documented across the specification (Sections 1.2.1, 2.4.4, 5.3.6, 5.4.6, 6.1.4.8, 6.4.6.3, 6.5.6) into a single ordered hardening sequence.

### 8.12.1 Known Production-Readiness Gaps

| Gap | Severity | Reference |
|---|---|---|
| Hardcoded DB credentials (`postgres:postgres`) | High | Section 6.4.6.3 |
| Database port `5432:5432` published to host | High | Section 6.4.6.3 |
| No HTTPS termination (plaintext HTTP) | High | Section 6.4.6.3 |
| Container runs as `root` (no `USER` directive) | Medium | Section 6.4.4.2 |
| Flask development server in production (gunicorn declared but unused) | Medium | ADR-006 |
| No `/healthz` endpoint or Compose `healthcheck:` block | Medium | Section 5.4.6 |
| No restart policy on `postgres` service | Medium | Section 5.4.6 |
| Base image `python:3.11-slim-buster` (Buster EOL) | Medium | Section 6.4.4.2 |
| No backup / DR (no `pg_dump`, no replication) | Medium | Section 5.4.6 |
| `python-dotenv` declared but unused | Cosmetic | Section 6.4.3.2 |
| No structured logging or correlation IDs | Low | Section 5.4.2 |
| `axios` declared but never imported | Cosmetic | ADR-003 |
| `web-vitals` declared but never wired | Low | Section 6.5.3.2 |

### 8.12.2 Recommended Hardening Sequence

The sequence below is ordered by leverage on mean-time-to-detection (MTTD) and mean-time-to-recovery (MTTR), with each step assuming the prior steps are complete:

```mermaid
flowchart LR
    Start([Current Posture<br/>Werkzeug stdout only]) --> H1["1: Add /healthz<br/>plus Compose healthcheck"]
    H1 --> H2["2: Symmetrize postgres<br/>restart: on-failure"]
    H2 --> H3["3: Switch CMD<br/>to gunicorn"]
    H3 --> H4["4: Adopt structlog<br/>plus correlation IDs"]
    H4 --> H5["5: Wire web-vitals<br/>reportWebVitals"]
    H5 --> H6["6: Frontend try/catch<br/>plus ErrorBoundary"]
    H6 --> H7["7: Error reporting SDK<br/>Sentry / Rollbar"]
    H7 --> H8["8: Log shipper<br/>Fluent Bit / Vector"]
    H8 --> H9["9: Prometheus<br/>/metrics endpoint"]
    H9 --> H10["10: Dashboards<br/>plus alert rules"]
    H10 --> H11["11: pg_dump<br/>or replication"]
    H11 --> H12["12: Externalize<br/>credentials via env"]
    H12 --> H13["13: TLS termination<br/>via reverse proxy"]
    H13 --> H14["14: Remove 5432 port<br/>publish from host"]
    H14 --> Production([Production-grade<br/>infrastructure posture])
```

The first four steps (H1–H4) collectively raise observability from zero structured signal to per-request correlated structured logs with container-level health probes. Steps H5–H8 close the frontend observability gap. Steps H9–H10 add metrics-driven alerting. Step H11 closes the disaster-recovery loop. Steps H12–H14 close the security-posture gaps documented in Section 6.4.6.3.

---

## 8.13 NETWORK ARCHITECTURE

The network topology of the deployed system is intentionally minimal — a single Docker Compose bridge network plus two host port mappings.

```mermaid
flowchart TB
    Internet([Internet / LAN])

    subgraph HostMachine["Docker Host (single OS instance)"]
        HostNet["Host network namespace<br/>(eth0, lo, etc.)"]
        Port80["Host TCP :80<br/>(intended public surface)"]
        Port5432["Host TCP :5432<br/>(SECURITY GAP)"]

        subgraph DockerEngine["Docker Engine"]
            subgraph ComposeBridge["Compose default bridge network<br/>(internal subnet, e.g., 172.x.x.x/16)"]
                ApiNet["api container<br/>internal IP, port 5000"]
                PgNet["postgres container<br/>internal IP, port 5432"]
                DnsResolver["Compose DNS resolver<br/>(service-name to IP)"]

                ApiNet -- "tcp 5432<br/>via DNS name 'postgres'" --> PgNet
                ApiNet -.- DnsResolver
                PgNet -.- DnsResolver
            end
        end

        HostNet --- Port80
        HostNet --- Port5432
        Port80 -- "DNAT 80 to 5000" --> ApiNet
        Port5432 -- "DNAT 5432 to 5432" --> PgNet
    end

    Internet -- "HTTP/1.1 plaintext :80" --> Port80
    Internet -. "direct tcp :5432<br/>(should be removed in production)" .-> Port5432
```

### 8.13.1 Network Boundaries

| Boundary | Type | Trust Posture |
|---|---|---|
| Internet → Host `:80` | Trust boundary | Untrusted ingress; no WAF; no rate limiting |
| Internet → Host `:5432` | Trust boundary (UNINTENDED) | Direct database exposure with default credentials |
| Compose bridge → `api` container `:5000` | Internal | Same-host bridge network |
| Compose bridge → `postgres` container `:5432` | Internal | Same-host bridge network |
| `api` → `postgres` (intra-bridge) | Internal | Trusted; resolved via Compose DNS |

### 8.13.2 Critical Security Note

The `5432:5432` host-to-container port publish in `docker-compose.yml` exposes the PostgreSQL service directly to whatever network the host is connected to. Combined with the hardcoded credentials (`postgres:postgres`), this constitutes the highest-severity security gap documented in Section 6.4.6.3. For any deployment beyond a fully-private development workstation, **this mapping must be removed** by deleting the `ports:` block on the `postgres` service (intra-Compose communication continues to function via the bridge network and DNS resolution).

---

## 8.14 SUMMARY OF NON-APPLICABILITY AND APPLICABILITY

The Infrastructure concerns enumerated in this section's prompt map to the actual codebase as follows:

| Prompt Concern | Status in This System | Driving Reason |
|---|---|---|
| Cloud provider selection | Not applicable | No cloud services consumed; ADR-001 |
| Infrastructure-as-Code | Not applicable | No IaC tooling; Compose serves analogous role at local scope |
| Container platform | Applicable | Docker + Compose v3 schema |
| Base image strategy | Applicable | Pinned `python:3.11-slim-buster` and `postgres:15` |
| Image versioning | Partial | Pinned base images and dependencies; no built-image registry tagging |
| Build optimization | Applicable | Layer-cached pip install; `.dockerignore` exclusions |
| Security scanning | Not implemented | Deferred — no CI/CD pipeline |
| Orchestration platform | Not applicable | Single replica; ADR-001 |
| Cluster architecture | Not applicable | No cluster |
| Auto-scaling | Not applicable | Single-replica monolith |
| CI/CD pipeline | Not implemented | Section 1.3.3 explicit non-goal |
| Build pipeline | Manual operator-driven | No automation triggers |
| Deployment pipeline | Manual `docker compose up` | No blue-green/canary/rolling |
| Resource monitoring | Not implemented | Section 5.4.1 ; no APM/metrics/RUM |
| Performance metrics | Not measured | Bounds observable from code structure only |
| Cost monitoring | Not applicable | Single-host non-cloud deployment |
| Security monitoring | Not implemented | Werkzeug stdout only |
| Compliance auditing | Not applicable | No applicable regulatory regime |
| Backup / DR | Not implemented | Bind-mount durability only; no `pg_dump` |
| Maintenance procedures | Operator-implicit | No runbooks committed |

The system instead relies on a **single deployment artifact** — the two-service Compose stack — that provides a development-grade infrastructure floor sufficient for the system's actual deployment context (solo-maintainer, public-read-only, single bounded context). The full hardening path required for production-grade infrastructure is sketched in Section 8.12 and cross-referenced to the originating recommendations in Sections 5.3.6, 5.4.6, 6.1.4.8, 6.4.6.3, and 6.5.6.

---

## 8.15 References

#### Files Examined

- `docker-compose.yml` — Two-service Compose stack definition (26 lines); confirmed schema "3", services `api` and `postgres`, port mappings (`80:5000`, `5432:5432`), restart policy asymmetry, hardcoded credentials, `./data:/data` bind-mount, `NODE_OPTIONS=--openssl-legacy-provider` env var, unused top-level `volumes: data:` declaration.
- `Dockerfile` — Single-stage image build (15 lines); base `python:3.11-slim-buster`, native deps `libpq-dev` + `gcc`, `EXPOSE 5000`, `CMD ["python3", "app.py"]` (Flask dev server, not gunicorn), no `USER` directive, no `HEALTHCHECK` instruction.
- `requirements.txt` — 23 pinned Python packages; verified Flask 2.0.1, SQLAlchemy 1.4.19, psycopg2 2.9.6, gunicorn 20.1.0 (declared but unused), python-dotenv 0.18.0 (declared but unused), Marshmallow 3.12.1, pandas 2.0.0.
- `.dockerignore` — 3 build-context exclusions (`/frontend/node_modules`, `/venv`, `/data`).
- `app.py` — 5-line root entry point invoking `app.run(host='0.0.0.0')` (port defaults to 5000).
- `api/__init__.py` — 22-line Flask bootstrap; verified hardcoded `dbURL = f'postgresql://postgres:postgres@postgres/db'` (line 12), permissive `CORS(app)`, `static_folder='../frontend/build'`, `static_url_path='/'`, `SQLALCHEMY_TRACK_MODIFICATIONS=False`, `import os` (unused).
- `frontend/package.json` — 45-line CRA manifest; CRA dev proxy `"proxy": "http://localhost:5000"` (line 44); `web-vitals: ^1.0.1` (line 17, unwired); `axios` declared but unused; key deps: `react-scripts` 4.0.3, `react` ^17.0.2, `@amcharts/amcharts4` ^4.10.19.
- `.flaskenv` — 2-line file with `FLASK_APP=app.py` and `FLASK_ENV=development` (consumed only by `flask run` in hybrid local-dev mode, not by Docker).
- `.gitignore` — 30-line standard CRA gitignore plus `__pycache__`, `venv`, `/data`.
- `README.md` — Project documentation; mentions external Billboard scraper and Spotipy enrichment (out of repo scope).

#### Folders Explored

- `/` (repository root) — Top-level Compose stack files, app entry, dependency manifests, README, `.dockerignore`, `.gitignore`, `.flaskenv`, plus `api/` and `frontend/` subtrees.
- `api/` — Backend Flask package (`__init__.py`, `routes.py`, `models.py`, `funcs.py`); no infrastructure submodules.
- `frontend/` — Frontend root (`package.json`, `package-lock.json`); subfolders `src/`, `public/`, `build/`.
- `frontend/build/` — Production deployable output (`asset-manifest.json`, `index.html`, `manifest.json`, `static/`).

#### Cross-Referenced Technical Specification Sections

- **Section 1.2 SYSTEM OVERVIEW** — Project context (read-side of pipeline); known limitations including hardcoded credentials and gunicorn discrepancy.
- **Section 1.3 SCOPE** — Explicit out-of-scope listing for CI/CD, observability, multi-environment configuration, production WSGI deployment, and automated tests.
- **Section 2.4 IMPLEMENTATION CONSIDERATIONS** — Technical constraints (hardcoded URI, Flask dev server), performance bounds, scalability blockers, security implications.
- **Section 3.4 THIRD-PARTY SERVICES** — Verified "None" disposition for cloud, monitoring, and authentication services; Google Fonts as the only external runtime resource.
- **Section 3.5 DATABASES & STORAGE** — PostgreSQL 15 configuration, ORM stack, no caching layer, default connection pooling.
- **Section 3.6 DEVELOPMENT & DEPLOYMENT** — Tool versions, build steps, Compose schema, local development workflows, CI/CD absence matrix, WSGI posture, testing absence.
- **Section 5.1 HIGH-LEVEL ARCHITECTURE** — Two-tier monolith characterization, infrastructure tier components (Container Image Build, Compose Orchestration, Persistence Volume).
- **Section 5.3 TECHNICAL DECISIONS** — Architecture style decision matrix, six ADRs (ADR-001 through ADR-006).
- **Section 5.4 CROSS-CUTTING CONCERNS** — Monitoring/observability disposition, logging strategy, error handling patterns, no SLAs, disaster recovery procedures.
- **Section 6.1 Core Services Architecture** — Two-tier topology, scalability design, resilience patterns, recommended hardening list.
- **Section 6.4 Security Architecture** — Trust boundaries, port exposure surface (the `5432:5432` mapping flagged as high severity), encryption gaps, recommended hardening sequence.
- **Section 6.5 Monitoring and Observability** — Comprehensive non-applicability matrix, basic monitoring practices in effect, recommended hardening sequence.

# 9. Appendices

This section consolidates supplementary technical information, terminology, and acronyms used throughout the Hot Stuff Technical Specification. The content here is intentionally cross-cutting: it captures small but consequential facts (configuration constants, theme tokens, external URLs, audio-feature definitions, dependency pin lists) that did not warrant a dedicated section earlier, and it provides authoritative definitions for the vocabulary and abbreviations used across all preceding sections. Where a topic is documented elsewhere in depth, this appendix points to the canonical section rather than duplicating it.

---

## 9.1 ADDITIONAL TECHNICAL INFORMATION

The following subsections record reference values, definitions, and inventories that appear throughout the source repository but are not centralized in any single earlier section. They are intended to serve as a single-page lookup table for engineers, reviewers, and future maintainers.

### 9.1.1 Project Identity and Repository Metadata

The Hot Stuff project carries multiple identifiers that surface across different surfaces (repository, npm package, PWA manifest, footer attribution). These are consolidated below to disambiguate them and to support search-and-replace operations during any future re-branding.

| Attribute | Value | Authoritative Source |
|---|---|---|
| Repository identifier | `hot-stuff` | Top-level repo folder; section 1.1 |
| Frontend npm package name | `top-100` | `frontend/package.json` (line 2) |
| Frontend package version | `0.1.0` | `frontend/package.json` (line 3) |
| Privacy flag | `"private": true` | `frontend/package.json` (line 4) |
| Public source repository URL | `https://github.com/augardiner/hot-100` | `AboutSection.js` (line 105) |
| Footer copyright marker | `AUG | 2021` | `Footer.js` (rendered globally) |
| Browser tab title | `Hot Stuff` | `frontend/public/index.html` |
| PWA `short_name` and `name` | `Hot Stuff` | `frontend/public/manifest.json` |

The discrepancy between the repository slug (`hot-stuff`), the npm package name (`top-100`), and the GitHub URL slug (`hot-100`) is preserved verbatim; these are observed identifiers and are not normalized by this specification.

### 9.1.2 External Reference Resources

The repository links to a small set of external resources from `README.md` and the static `AboutSection.js` methodology page. These are the only outbound references embedded in the codebase and are reproduced here for convenience.

| Resource | URL |
|---|---|
| Billboard Hot 100 chart | `https://www.billboard.com/charts/hot-100` |
| Wikipedia: Billboard Hot 100 | `https://en.wikipedia.org/wiki/Billboard_Hot_100` |
| Spotipy 2.18.0 documentation | `https://spotipy.readthedocs.io/en/2.18.0/` |
| Spotify Web API audio features | `https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject` |
| amCharts product site | `https://www.amcharts.com/` |
| Source repository | `https://github.com/augardiner/hot-100` |
| Google Fonts CSS host | `https://fonts.googleapis.com` |
| Google Fonts asset host (Jost typeface) | `https://fonts.gstatic.com` |

Google Fonts is the only third-party runtime dependency the deployed application contacts (see section 3.4); all other URLs in the table are documentation references displayed to end users.

### 9.1.3 Domain Reference Data

The application is anchored to a fixed temporal domain: the Billboard Hot 100 chart era. The following constants govern the date range that the UI exposes and that the underlying data covers.

| Reference Point | Value | Where It Appears |
|---|---|---|
| First number-one song | "Poor Little Fool" by Ricky Nelson | `README.md`, `AboutSection.js` (lines 28–29) |
| Date of first chart entry | August 4, 1958 | `README.md` (line 7) |
| `DatePicker` minimum date | `1958-07-27` | `frontend/src/components/tracks/DatePicker.js` |
| `DatePicker` maximum date | `2021-11-13` | `frontend/src/components/tracks/DatePicker.js` |
| `TracksSection` initial fetch literal | `'2021-11-13'` (line 37) | `frontend/src/components/tracks/TracksSection.js` |
| Chart ranking inputs (per README) | Sales (physical and digital), radio play, online streaming | `README.md` (line 5) |

The fact that the maximum selectable date and the initial fetch literal are identical (`2021-11-13`) reflects the data freeze point of the underlying scraper — this is the most recent chart week represented in the persisted dataset.

### 9.1.4 Spotify Audio Feature Definitions

The Trends tab embeds verbatim feature descriptions sourced from Spotify's API documentation, stored at `frontend/src/components/trends/features.json`. The descriptions below paraphrase what is shown to end users; consult `features.json` for the bundled text (which contains the documented `desctiption` typo preserved by `TrendsSection.js`).

| Feature | Range / Unit | Interpretation |
|---|---|---|
| Tempo | Beats per minute (BPM) | Estimated overall tempo derived from average beat duration |
| Energy | 0.0–1.0 | Perceptual measure of intensity and activity (loud, fast, noisy → high) |
| Danceability | 0.0–1.0 | Suitability for dancing based on tempo, rhythm stability, beat strength, and regularity |
| Instrumentalness | 0.0–1.0 | Probability that a track contains no vocals; values above 0.5 are likely instrumental |
| Liveness | 0.0–1.0 | Probability of audience presence in the recording; above 0.8 indicates a live performance |
| Speechiness | 0.0–1.0 | Presence of spoken words (>0.66 mostly speech, 0.33–0.66 mixed, <0.33 music) |
| Acousticness | 0.0–1.0 | Confidence that the track is acoustic |
| Valence | 0.0–1.0 | Musical positiveness (schema-only; not exposed in Trends dropdown) |
| Loudness | Decibels (dB) | Overall track loudness (schema-only; not exposed in Trends dropdown) |

`Valence` and `Loudness` are persisted in the `Tracks` table (see section 6.2) but are intentionally absent from the Trends dropdown; the documented set of seven user-selectable features is the surface contract.

### 9.1.5 Hardcoded Configuration Inventory

The application does not consume environment variables at runtime in the deployed container; configuration is embedded directly in source. The following inventory is the authoritative list of hardcoded values an operator must change to relocate, re-credential, or re-port the system.

| Configuration Key | Value | Defining File |
|---|---|---|
| Database URI | `postgresql://postgres:postgres@postgres/db` | `api/__init__.py` (line 12) |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | `False` | `api/__init__.py` (line 15) |
| Flask `static_folder` | `'../frontend/build'` | `api/__init__.py` (line 8) |
| Flask `static_url_path` | `'/'` | `api/__init__.py` (line 8) |
| Flask host bind | `0.0.0.0` (port defaults to 5000) | `app.py` |
| Compose `api` port mapping | `80:5000` | `docker-compose.yml` (line 11) |
| Compose `postgres` port mapping | `5432:5432` | `docker-compose.yml` (line 18) |
| `NODE_OPTIONS` env var | `--openssl-legacy-provider` | `docker-compose.yml` (line 9) |
| `POSTGRES_USER` | `postgres` | `docker-compose.yml` (line 20) |
| `POSTGRES_PASSWORD` | `postgres` | `docker-compose.yml` (line 21) |
| `POSTGRES_DB` | `db` | `docker-compose.yml` (line 22) |
| Compose schema version | `"3"` | `docker-compose.yml` (line 1) |
| Bind mount for `api` | `.:/app/` | `docker-compose.yml` (line 13) |
| Bind mount for `postgres` | `./data:/data` | `docker-compose.yml` (line 24) |
| Restart policy (`api` only) | `on-failure` | `docker-compose.yml` (line 4) |
| CRA dev proxy target | `http://localhost:5000` | `frontend/package.json` (line 44) |
| `.flaskenv` `FLASK_APP` | `app.py` | `.flaskenv` |
| `.flaskenv` `FLASK_ENV` | `development` | `.flaskenv` |

Section 6.4 (Security Architecture) flags the public `5432:5432` port mapping and the hardcoded `postgres/postgres` credentials as the highest-severity items in this inventory.

### 9.1.6 Visual Design Tokens

The dark-mode theme is implemented entirely through CSS Custom Properties declared in `frontend/src/styles/index.css`. These six tokens are referenced by every styled-components definition and by the global stylesheet.

| Token | Value | Purpose |
|---|---|---|
| `--dark-1` | `#171717` | Page background |
| `--dark-2` | `#262626` | Sidebar background |
| `--dark-3` | `rgba(54, 54, 54, 0.5)` | Surfaces (input, button, track row) |
| `--grey` | `rgb(189, 189, 189, 0.3)` | Muted borders |
| `--light` | `rgb(189, 189, 189, 0.985)` | Foreground text |
| `--purp` | `rgb(128, 103, 220)` | Accent (active tab, footer, hover) |

Section 7.7 describes how these tokens compose into the broader visual design system (typography, spacing, and breakpoint behavior).

### 9.1.7 PWA Manifest Values

The Progressive Web App manifest (`frontend/public/manifest.json`) is generated from the Create React App template and customized minimally. The values below define how the application presents when installed on a user's device.

| Property | Value |
|---|---|
| `short_name` and `name` | `Hot Stuff` |
| `start_url` | `.` |
| `display` | `standalone` |
| `theme_color` | `#000000` |
| `background_color` | `#ffffff` |
| Icons | `favicon.ico` (multi-size), `logo192.png` (192×192), `logo512.png` (512×512) |

The `theme_color` (`#000000`) and `background_color` (`#ffffff`) values are CRA defaults and do not match the application's actual dark-mode palette; this is documented in section 7.10 as a known UI limitation.

### 9.1.8 Date Normalization Reference

The backend's `get_query_week` helper (in `api/funcs.py`) implements Saturday-boundary alignment for any input date. Because chart weeks are dated Saturday and the annotation cutoff falls mid-week, the function applies a small decision tree before computing the canonical week date.

```mermaid
flowchart TD
    A[Input date<br/>YYYY-MM-DD] --> B{Weekday in<br/>Sun, Mon, Tue?}
    B -- "Yes" --> C[Return previous<br/>Saturday]
    B -- "No" --> D{Wednesday<br/>before 10:00 AM?}
    D -- "Yes" --> C
    D -- "No" --> E[Compute next<br/>Saturday]
    E --> F["Apply formula:<br/>(12 − weekday) % 7"]
    F --> G[Return next<br/>Saturday as ISO date]
    C --> H[str(saturday)[:10]]
    G --> H
```

| Element | Value |
|---|---|
| Saturday-offset formula | `(12 - date.weekday()) % 7` |
| Cutoff weekday set | `[6, 0, 1]` (Sunday, Monday, Tuesday → previous Saturday) |
| Wednesday boundary time | 10:00 AM (before → previous Saturday; after → next Saturday) |
| Input format | `YYYY-MM-DD` (parsed via `datetime.strptime`) |
| Output format | `str(saturday)[:10]` (truncated ISO date) |

This logic is referenced from F-013 (Chart Week Date Normalization) in section 2.1 and is the only place in the codebase where week-of-year arithmetic is performed.

### 9.1.9 Documentation Discrepancy Register

A complete register of code-vs-documentation mismatches is maintained in section 2.5.3. The table below is the consolidated cross-reference, organized in numbered form for direct citation in issue trackers and remediation tickets.

| # | Discrepancy | Code Reality |
|---|---|---|
| 1 | Rolling window labelled "3 Year" | `.rolling(5)` — five-year window |
| 2 | Initial fetch date | Hardcoded `'2021-11-13'`; `new Date()` is commented out |
| 3 | WSGI server | `python3 app.py` (Flask dev server) — `gunicorn==20.1.0` declared but never invoked |
| 4 | Environment loader | DB URI hardcoded — `python-dotenv==0.18.0` declared but never used |
| 5 | Tab indices | `0, 1, 3` (skips `2`) |
| 6 | JSON property key | `desctiption` typo preserved in both `features.json` and consuming JSX |
| 7 | `Tracks.__init__` | Omits `spotify_id` despite the column existing in the schema |
| 8 | HTTP client library | Native `fetch()` — `axios ^0.21.1` declared but never imported |
| 9 | Charting library | `@amcharts/amcharts4` only — `plotly.js` and `react-plotly.js` declared but never imported |
| 10 | Web vitals telemetry | `web-vitals ^1.0.1` declared but never wired |

### 9.1.10 Feature Catalog Quick Reference

The complete feature catalog with full requirement decomposition is maintained in section 2.1. The compact quick-reference below provides ID-to-name resolution for cross-document citations.

| Feature ID | Name | Layer |
|---|---|---|
| F-001 | Static SPA Asset Delivery | API |
| F-002 | Current Week Default Redirect | API |
| F-003 | Track Historical Lookup by Spotify ID | API |
| F-004 | Weekly Chart Snapshot Retrieval | API |
| F-005 | Case-Insensitive Artist Search | API |
| F-006 | Annual Feature Trend Analysis | API |
| F-007 | Tab-Based Navigation Shell | Frontend |
| F-008 | Weekly Track Inspection View (Tracks Tab) | Frontend |
| F-009 | Feature Trend Visualization View (Trends Tab) | Frontend |
| F-010 | Methodology Documentation View (About Tab) | Frontend |
| F-011 | Audio Feature Radar Chart | Visualization |
| F-012 | Audio Feature Trend Line Chart | Visualization |
| F-013 | Chart Week Date Normalization | Data Logic |
| F-014 | Multi-Year Rolling Average Computation | Data Logic |
| F-015 | Persistence Models and JSON Serialization | Data Layer |
| F-016 | Docker Compose Two-Service Orchestration | Infrastructure |
| F-017 | Open Cross-Origin Resource Sharing | Infrastructure |

### 9.1.11 Architecture Decision Record Index

The full text of each ADR is in section 5.3.6. The index below provides the ID-to-title resolution and current acceptance status.

| ADR ID | Title | Status |
|---|---|---|
| ADR-001 | Single-Process SPA + API | Accepted |
| ADR-002 | Pre-Aggregated `YearlyAvg` Table | Accepted |
| ADR-003 | Native `fetch` over `axios` | Accepted |
| ADR-004 | No Caching Tier | Accepted (provisional) |
| ADR-005 | Local React State Only | Accepted |
| ADR-006 | Flask Development Server in Production | Accepted (provisional) |

### 9.1.12 Pinned Python Dependencies

The complete contents of `requirements.txt`, with exact pins, are reproduced for change-management traceability. All 23 packages are pinned to a specific version (no version-range operators).

| Package | Version | Package | Version |
|---|---|---|---|
| click | 8.1.3 | numpy | 1.24.2 |
| Flask | 2.0.1 | pandas | 2.0.0 |
| Flask-Cors | 3.0.10 | psycopg2-binary | 2.9.5 |
| flask-marshmallow | 0.14.0 | psycopg2 | 2.9.6 |
| Flask-SQLAlchemy | 2.5.1 | python-dateutil | 2.8.2 |
| greenlet | 2.0.2 | python-dotenv | 0.18.0 |
| gunicorn | 20.1.0 | pytz | 2021.1 |
| itsdangerous | 2.0.1 | six | 1.16.0 |
| Jinja2 | 3.0.1 | SQLAlchemy | 1.4.19 |
| MarkupSafe | 2.1.2 | tzdata | 2023.3 |
| marshmallow | 3.12.1 | Werkzeug | 2.2.3 |
| marshmallow-sqlalchemy | 0.26.1 | — | — |

`gunicorn` and `python-dotenv` appear in this list but are not consumed by the running application (see discrepancies #3 and #4 in section 9.1.9).

### 9.1.13 Declared npm Dependencies

The frontend's `frontend/package.json` declares twelve runtime/dev dependencies. The "Status" column distinguishes packages that are actually imported in source from those that remain declared but unused.

| Package | Version Range | Status |
|---|---|---|
| `@amcharts/amcharts4` | `^4.10.19` | Active (radar and line charts) |
| `@testing-library/jest-dom` | `^5.11.4` | Declared; no tests exist |
| `@testing-library/react` | `^11.1.0` | Declared; no tests exist |
| `@testing-library/user-event` | `^12.1.10` | Declared; no tests exist |
| `axios` | `^0.21.1` | Declared; never imported |
| `plotly.js` | `^1.58.4` | Declared; never imported |
| `react` | `^17.0.2` | Active |
| `react-dom` | `^17.0.2` | Active |
| `react-plotly.js` | `^2.5.1` | Declared; never imported |
| `react-scripts` | `4.0.3` (exact pin) | Active (build pipeline) |
| `styled-components` | `^5.3.0` | Active (navigation primitives) |
| `web-vitals` | `^1.0.1` | Declared; never wired to a callback |

### 9.1.14 Out-of-Repository Pipeline Components

Three components are referenced in `README.md` and `AboutSection.js` but are not present in the repository. Operating the Hot Stuff system at full fidelity (i.e., with current chart data) requires that these be provisioned externally; see section 3.4 for the full third-party integration disposition.

| Component | Status | Documentation Reference |
|---|---|---|
| Weekly Billboard Hot 100 scraper | Not in repo | `README.md`, `AboutSection.js`, section 3.4.1 |
| Spotipy-based Spotify enrichment job | Not in repo | `README.md`, `AboutSection.js`, section 3.4.1 |
| Annual `YearlyAvg` aggregation job | Not in repo | Inferred from schema; section 4.6.3 |

### 9.1.15 Compiled Asset Observations

The production build artifact at `frontend/build/` contains a small number of observations worth recording for build-system auditing.

| Observation | Detail |
|---|---|
| `xlsx.<hash>.chunk.js` chunk | Present in `asset-manifest.json` despite `xlsx` not being declared in `package.json` (transitive dependency from a chart library) |
| `*.LICENSE.txt` sidecars | Accompany three of the larger chunks (4, 5, 6); emitted by Webpack's `TerserPlugin` license-extraction option |
| Build manifest schema | `asset-manifest.json` enumerates entrypoints and content-hashed file names for cache-busting |

### 9.1.16 Data Cardinality Estimates

The following cardinality estimates inform query planning, index selection (section 6.2), and resource sizing (section 8.10).

| Entity / Response | Typical Volume |
|---|---|
| `tracks` table at steady state | ~350,000 rows (≈67 years × 52 weeks × 100 rows) |
| `tracks` weekly growth | ~100 rows |
| `yearly_avg` table | ~70 rows total (one per year) |
| Weekly snapshot API response | ≤100 rows |
| Trend analysis API response | ≤~70 rows |

---

## 9.2 GLOSSARY

The glossary is grouped into four categories — domain terms, application/system terms, library/framework terms, and operations/infrastructure terms — to support readers approaching this specification from different angles (music data analyst, full-stack engineer, platform engineer, security reviewer).

### 9.2.1 Domain-Specific Terms

These terms relate to the music-industry domain that the application surfaces.

| Term | Definition |
|---|---|
| **Audio Feature** | Quantitative attribute computed by Spotify's API describing musical characteristics; the persisted set in `Tracks` is tempo, energy, danceability, valence, liveness, speechiness, acousticness, instrumentalness, and loudness |
| **Billboard Hot 100** | The music-industry standard record chart in the United States, published weekly by Billboard magazine; ranks songs by sales (physical and digital), radio play, and online streaming |
| **Chart Week** | A Saturday-aligned week corresponding to a single weekly Billboard chart publication; computed by `get_query_week` in `api/funcs.py` |
| **Hot Stuff** | The project name of the Billboard Hot 100 visualization application documented in this specification |
| **Rolling Average** | A moving mean computed over a fixed-size window; here, `df.rolling(5).mean()` over five consecutive years |
| **Spotify ID** | Unique identifier assigned by Spotify to a track; persisted in `Tracks.spotify_id` and queried via `/api/track/<spotify_id>` |
| **Yearly Average** | Pre-aggregated mean of an audio feature across all chart entries for a given year, persisted in the `YearlyAvg` table |

### 9.2.2 Application and System Terms

These terms describe the application's UI surfaces, architectural concepts, and runtime behaviors.

| Term | Definition |
|---|---|
| **About Tab** | Static methodology documentation page rendered by `AboutSection.js`; tab index `3` in `App.js` |
| **Application Shell** | Top-level React composition (`App.js`, `index.js`) that mounts the SPA and manages `nav` and `activeTab` state |
| **Bind Mount** | Docker volume that maps a host directory directly into a container; used here as `.:/app/` on `api` (hot reload) and `./data:/data` on `postgres` (data persistence) |
| **Chart Week Date Normalization** | The process implemented in `get_query_week` of converting any input date into the canonical Saturday date of the corresponding Billboard chart week |
| **Compose Bridge Network** | Default Docker network created by `docker-compose up`, providing DNS-based service-name resolution between `api` and `postgres` |
| **DatePicker** | React component wrapping a native `<input type='date'>` constrained between `1958-07-27` and `2021-11-13` |
| **Defense-in-Depth** | Multi-layered security approach; here, refers to `Flask-Cors` registered globally even though the production deployment is same-origin |
| **DNS-Based Service Discovery** | Compose feature that resolves the service name `postgres` to the container's IP address within the bridge network |
| **Hamburger** | Mobile-only sidebar toggle component using a 40×40 SVG with three rounded `<rect>` bars |
| **Hashed Asset** | Production build output filename containing a content hash (e.g., `static/js/main.<hash>.chunk.js`) used for long-lived browser caching |
| **Hot Reload** | Development-mode behavior where source changes propagate without full container restart; achieved via the `.:/app/` bind mount |
| **Layer Caching** | Docker build optimization where unchanged layers are reused; enabled by copying `requirements.txt` before source files |
| **Manifest** | A project-metadata file; multiple manifests exist (`package.json` for npm, `manifest.json` for PWA, `asset-manifest.json` for build artifacts) |
| **Marshmallow Dump** | One-way serialization of Python objects to JSON-safe dictionaries; the codebase never invokes the inverse `load()` method |
| **Pre-Aggregation** | Pattern of materializing computed values (here, `YearlyAvg`) at write time so that read requests avoid full-table scans |
| **PWA Standalone Display** | PWA manifest property (`display: standalone`) causing the installed app to render without browser chrome |
| **Radar Chart** | Polar-coordinate chart with multiple radial axes; used by `RadarChart.js` for the Tracks tab |
| **Read-Only Contract** | Architectural property whereby the application performs no `INSERT`, `UPDATE`, or `DELETE` operations against the database |
| **Saturday Boundary** | The date-normalization rule that aligns any input date to Billboard's Saturday-dated chart week |
| **Sidebar** | Left-edge navigation component containing three tabs; collapses to a hamburger menu below 800 px viewport width |
| **Single-Page Application (SPA)** | A web application delivered as a single HTML page that updates its content client-side without full-page reloads |
| **Static Folder** | Flask configuration (`static_folder='../frontend/build'`) pointing to the compiled React bundle that Flask serves |
| **Tracks Tab** | Date-driven weekly chart inspection view; tab index `0` in `App.js` |
| **Trends Tab** | Feature-driven longitudinal analysis view; tab index `1` in `App.js` |
| **Two-Tier Monolith** | Architectural style with combined application logic and presentation in a single process, paired with a separate data tier |

### 9.2.3 Library and Framework Terms

These terms refer to the third-party libraries and frameworks bound to specific versions in this project.

| Term | Definition |
|---|---|
| **amCharts 4** | JavaScript charting library at `^4.10.19`; provides `RadarChart`, `XYChart`, `LineSeries`, and `RadarColumnSeries` classes |
| **CRA (Create React App)** | Bootstrap toolchain pinned at `react-scripts 4.0.3`; bundles Webpack 4, Babel, Jest, ESLint, and Workbox |
| **CSS-in-JS** | Styling approach embedding CSS in JavaScript; provided here by `styled-components 5.3.0` for navigation primitives |
| **Flask** | Python micro-framework at `2.0.1`; provides routing, request/response handling, and the WSGI development server |
| **Flask-Cors** | Flask extension at `3.0.10` providing CORS middleware via the `CORS(app)` invocation |
| **Flask-Marshmallow** | Flask integration at `0.14.0` providing the `ma` instance used for schema definitions |
| **Flask-SQLAlchemy** | Flask integration at `2.5.1` providing the `db` instance and request-scoped session management |
| **Gunicorn** | Production WSGI server pinned at `20.1.0`; declared in `requirements.txt` but never invoked |
| **JSX** | JavaScript XML; React's syntax extension for embedding markup expressions in JavaScript |
| **Marshmallow** | Python schema library at `3.12.1` for object/JSON serialization |
| **Marshmallow-SQLAlchemy** | Bridge library at `0.26.1` between SQLAlchemy ORM models and Marshmallow schemas |
| **pandas** | Python data analytics library at `2.0.0`; provides `DataFrame` and rolling-window operations |
| **psycopg2** | Python PostgreSQL driver pinned at `2.9.6`; `psycopg2-binary 2.9.5` is also pinned |
| **React** | UI runtime library at `^17.0.2` |
| **React StrictMode** | Development-only React component that flags unsafe lifecycles and side effects |
| **react-scripts** | The CRA build pipeline at exact version `4.0.3` (Webpack 4-based) |
| **Spotipy** | Python library wrapping the Spotify Web API; referenced in documentation but not in `requirements.txt` (used by the out-of-repo enrichment job) |
| **SQLAlchemy** | Python ORM at `1.4.19`; defines the `Tracks` and `YearlyAvg` declarative models |
| **styled-components** | CSS-in-JS library at `5.3.0`; styles `Sidebar`, `Tab`, `SmallTab`, `Hamburger`, and `Section` |
| **Webpack 4** | The module bundler embedded in CRA 4; requires `--openssl-legacy-provider` on Node 17+ |
| **Werkzeug** | WSGI utility library at `2.2.3`; underlies Flask |

### 9.2.4 Operations and Infrastructure Terms

These terms describe the deployment posture, container orchestration, and operational primitives referenced throughout sections 8.x.

| Term | Definition |
|---|---|
| **`.dockerignore`** | File excluding paths from the Docker build context; here, excludes `frontend/node_modules`, `venv`, and `data` |
| **Compose Schema** | Docker Compose file format version `"3"` declared at the top of `docker-compose.yml` |
| **Docker Compose** | Multi-container orchestration tool that consumes `docker-compose.yml` to define and run services |
| **Docker Engine Logging Driver** | Default mechanism capturing container `stdout`/`stderr`; the only observability surface in this system |
| **Healthcheck** | A Compose/Docker primitive (NOT configured in this repository) that probes container health beyond process-exit signaling |
| **OpenSSL Legacy Provider** | Node.js option (`--openssl-legacy-provider`) required by Webpack 4 when running on Node 17 or later |
| **Slim-Buster** | The Debian Buster-based slim Python container variant used by the Dockerfile (`python:3.11-slim-buster`) |
| **WAL Archiving** | PostgreSQL Write-Ahead Log shipping for point-in-time recovery (NOT configured in this system) |
| **WSGI** | Web Server Gateway Interface — the Python web-server protocol; here, the single-threaded Flask development server |

---

## 9.3 ACRONYMS

Acronyms are grouped by subject area for ease of lookup. Where an acronym appears in multiple categories (e.g., `RBAC` in both architecture and security), it is listed once in its primary category.

### 9.3.1 Technology and Protocols

| Acronym | Expansion |
|---|---|
| API | Application Programming Interface |
| BPM | Beats Per Minute |
| CDN | Content Delivery Network |
| CSS | Cascading Style Sheets |
| CSV | Comma-Separated Values |
| DNS | Domain Name System |
| DOM | Document Object Model |
| HTML | HyperText Markup Language |
| HTTP | HyperText Transfer Protocol |
| HTTPS | HyperText Transfer Protocol Secure |
| JS | JavaScript |
| JSON | JavaScript Object Notation |
| JSX | JavaScript XML |
| REST | Representational State Transfer |
| RPC | Remote Procedure Call |
| SQL | Structured Query Language |
| SVG | Scalable Vector Graphics |
| TCP | Transmission Control Protocol |
| TLS | Transport Layer Security |
| URL | Uniform Resource Locator |
| UUID | Universally Unique Identifier |
| WOFF2 | Web Open Font Format 2 |
| WSGI | Web Server Gateway Interface |

### 9.3.2 Architecture and Patterns

| Acronym | Expansion |
|---|---|
| ABAC | Attribute-Based Access Control |
| ADR | Architecture Decision Record |
| BaaS | Backend-as-a-Service |
| CRA | Create React App |
| CRUD | Create, Read, Update, Delete |
| ERD | Entity-Relationship Diagram |
| ETL | Extract, Transform, Load |
| FaaS | Function-as-a-Service |
| FK | Foreign Key |
| ORM | Object-Relational Mapping |
| PEP | Policy Enforcement Point |
| PK | Primary Key |
| PWA | Progressive Web App |
| RBAC | Role-Based Access Control |
| RLS | Row-Level Security |
| SaaS | Software-as-a-Service |
| SDK | Software Development Kit |
| SPA | Single-Page Application |

### 9.3.3 Operations and Reliability

| Acronym | Expansion |
|---|---|
| APM | Application Performance Monitoring |
| CFS | Completely Fair Scheduler (Linux) |
| CI/CD | Continuous Integration / Continuous Deployment |
| DR | Disaster Recovery |
| EOL | End of Life |
| HA | High Availability |
| IaC | Infrastructure as Code |
| KPI | Key Performance Indicator |
| LRU | Least Recently Used |
| MTTD | Mean Time To Detection |
| MTTR | Mean Time To Recovery |
| OOM | Out Of Memory |
| PITR | Point-In-Time Recovery |
| RPO | Recovery Point Objective |
| RTO | Recovery Time Objective |
| RUM | Real-User Monitoring |
| SLA | Service Level Agreement |
| WAF | Web Application Firewall |
| WAL | Write-Ahead Log (PostgreSQL) |

### 9.3.4 Cloud and Vendor Services

| Acronym | Expansion |
|---|---|
| AWS | Amazon Web Services |
| Azure | Microsoft Azure (brand name) |
| CDK | Cloud Development Kit |
| ECS | Elastic Container Service (AWS) |
| GCP | Google Cloud Platform |
| GCS | Google Cloud Storage |
| RDS | Relational Database Service (AWS) |
| S3 | Simple Storage Service (AWS) |

### 9.3.5 Security, Compliance, and Identity

| Acronym | Expansion |
|---|---|
| CCPA | California Consumer Privacy Act |
| CORS | Cross-Origin Resource Sharing |
| CSRF | Cross-Site Request Forgery |
| GDPR | General Data Protection Regulation |
| HIPAA | Health Insurance Portability and Accountability Act |
| JWT | JSON Web Token |
| MFA | Multi-Factor Authentication |
| OAuth | Open Authorization |
| OIDC | OpenID Connect |
| PCI-DSS | Payment Card Industry Data Security Standard |
| PII | Personally Identifiable Information |
| SOC | System and Organization Controls (e.g., SOC 2) |

### 9.3.6 Development Tools and Package Management

| Acronym | Expansion |
|---|---|
| CMD | Command (Dockerfile instruction) |
| ESLint | ECMAScript Linter |
| IANA | Internet Assigned Numbers Authority |
| ID | Identifier |
| LAN | Local Area Network |
| npm | Node Package Manager (deliberately lowercase) |
| OS | Operating System |
| PyPI | Python Package Index |
| VM | Virtual Machine |

### 9.3.7 Database and Date-Format Acronyms

| Acronym | Expansion |
|---|---|
| DDL | Data Definition Language |
| DML | Data Manipulation Language |
| GIN | Generalized Inverted Index (PostgreSQL index type) |
| ISO | International Organization for Standardization |
| TOAST | The Oversized-Attribute Storage Technique (PostgreSQL) |
| YYYY-MM-DD | Year-Month-Day (ISO 8601 date format) |

---

## 9.4 References

This appendix consolidates information that appears across all preceding sections. The following enumeration lists every artifact and section consulted to compile the appendix content.

### 9.4.1 Files Examined

- `README.md` — Project domain context, external resource URLs, "3 year" rolling-average documentation claim, methodology overview
- `docker-compose.yml` — Compose schema "3", two-service definitions, port mappings, env vars, volumes, restart policy
- `Dockerfile` — Single-stage Python 3.11-slim-buster image build, native dependencies, `EXPOSE 5000`, `CMD` directive
- `requirements.txt` — Twenty-three pinned Python packages enumerated in section 9.1.12
- `app.py` — Five-line Flask entry point invoking `app.run(host='0.0.0.0')`
- `.flaskenv` — Two-line file declaring `FLASK_APP` and `FLASK_ENV` for hybrid local-dev mode
- `.dockerignore` — Three build-context exclusions
- `api/__init__.py` — Flask bootstrap with hardcoded DB URI, CORS registration, static-folder configuration
- `api/funcs.py` — Implementations of `get_query_week`, `get_rolling_avg`, and `get_weekly_data`
- `api/routes.py` — Six GET route handlers including the `func.lower(...).like(...)` artist-search pattern
- `api/models.py` — `Tracks` and `YearlyAvg` ORM models, `TrackSchema` and `YearlyAvgSchema` Marshmallow schemas
- `frontend/package.json` — React 17 dependencies, dev proxy, browserslist, ESLint config, build scripts
- `frontend/public/index.html` — Browser tab title, root `<div id="root">` mount point
- `frontend/public/manifest.json` — PWA configuration (short_name, name, theme_color, display, icons)
- `frontend/src/components/about/AboutSection.js` — Static methodology page with external links
- `frontend/src/components/trends/features.json` — Seven audio-feature title/description objects (preserves `desctiption` typo)
- `frontend/src/styles/index.css` — Six CSS Custom Property theme tokens
- `frontend/build/asset-manifest.json` — Hashed-asset manifest including the transitive `xlsx` chunk

### 9.4.2 Folders Explored

- `/` (repository root) — Top-level Compose stack files, app entry, dependency manifests, README, dotfiles, and the `api/`, `frontend/` subtrees
- `api/` — Backend Flask package containing four files (`__init__.py`, `routes.py`, `models.py`, `funcs.py`); no submodules
- `frontend/` — Frontend root (`package.json`, `package-lock.json`); subfolders `src/`, `public/`, `build/`
- `frontend/src/components/trends/` — `TrendsSection.js`, `FeatureSelect.js`, `LineChart.js`, `features.json`
- `frontend/src/components/tracks/` — `TracksSection.js`, `DatePicker.js`, `RadarChart.js`
- `frontend/build/` — Production deployable output (`asset-manifest.json`, `index.html`, `manifest.json`, `static/`)

### 9.4.3 Cross-Referenced Technical Specification Sections

- **Section 1.1 EXECUTIVE SUMMARY** — Project overview, stakeholder framing, value proposition
- **Section 1.2 SYSTEM OVERVIEW** — Project identity (`hot-stuff`, `top-100`), system topology, capabilities; corroborates 9.1.1
- **Section 1.3 SCOPE** — Out-of-scope inventory (CI/CD, observability, multi-environment configuration, automated tests)
- **Section 2.1 FEATURE CATALOG** — Source for the F-001…F-017 quick-reference reproduced in 9.1.10
- **Section 2.5.3 Documentation Discrepancy Register** — Source for the discrepancy register reproduced in 9.1.9
- **Section 3.4 THIRD-PARTY SERVICES** — Confirms Google Fonts as the only runtime third-party dependency listed in 9.1.2
- **Section 3.5 DATABASES & STORAGE** — PostgreSQL 15 configuration; supports cardinality estimates in 9.1.16
- **Section 3.6 DEVELOPMENT & DEPLOYMENT** — Build steps, Compose schema, gunicorn discrepancy
- **Section 4.6 TIMING AND SLA CONSIDERATIONS** — Operational cadence informing the out-of-repo pipeline summary in 9.1.14
- **Section 5.3.6 ADRs** — Source for the ADR index reproduced in 9.1.11
- **Section 5.4 CROSS-CUTTING CONCERNS** — Observability, logging, error handling, no SLAs, disaster-recovery posture
- **Section 6.2 Database Design** — Schema, indexes, replication absence; supports cardinality estimates in 9.1.16
- **Section 6.4 Security Architecture** — Trust boundaries, port-exposure surface, encryption gaps; references the 9.1.5 inventory
- **Section 7.7 VISUAL DESIGN SYSTEM** — Theme tokens reproduced in 9.1.6; PWA manifest reproduced in 9.1.7
- **Section 7.10 KNOWN UI LIMITATIONS** — Source for the manifest-color and CRA-template observations in 9.1.7 and 9.1.15
- **Section 8.12 PRODUCTION READINESS GAPS** — Hardening roadmap that references the configuration inventory in 9.1.5
- **Section 8.13 NETWORK ARCHITECTURE** — Port-exposure context for the configuration entries in 9.1.5
- **Section 8.15 References** — File inventory pattern adopted by this appendix