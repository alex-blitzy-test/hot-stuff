# hot-stuff

> A **Billboard Hot 100 audio-feature analytics** application — a Python/Flask JSON API and a React single-page app (SPA) for browsing weekly charts and analyzing how [Spotify Audio Features](https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject) trend over time.

`hot-stuff` ingests weekly Billboard Hot 100 chart data (enriched with Spotify audio features) into PostgreSQL and serves it through a single Flask process that hosts both the compiled React SPA at `/` and a JSON API under `/api/*`. *Source: api/__init__.py:L50; api/routes.py:L35-L182*

> **A note on terminology (`server.js` / JSDoc).** This repository contains **no `server.js`** file, and the backend "server" is written in **Python with the Flask framework** (`app.py` plus the `api/` package), not Node.js. *Source: app.py:L29; api/__init__.py:L42-L50* The original request to "add JSDoc comments to `server.js` functions" was therefore fulfilled in the language-appropriate way: the backend modules, functions, and classes are documented with **Google-style, PEP 257-compliant Python docstrings** (mapping JSDoc's `@param` / `@returns` / `@throws` onto docstring `Args:` / `Returns:` / `Raises:`). The only JavaScript in the repository is the React single-page app under `frontend/src/`, which is a UI client rather than a server. *Source: frontend/package.json:L12,L15*

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Run with Docker Compose](#run-with-docker-compose)
  - [Local development](#local-development)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Data Models](#data-models)
- [Data Pipeline](#data-pipeline)
- [Deployment](#deployment)
- [Acknowledgements and License](#acknowledgements-and-license)

## Overview

### The Billboard Hot 100

The [Billboard Hot 100](https://www.billboard.com/charts/hot-100) is the music industry standard record chart in the United States for songs, published weekly by Billboard magazine. Chart rankings are based on sales (physical and digital), radio play, and online streaming in the United States.

The first number one song of the Billboard Hot 100 was "Poor Little Fool" by Ricky Nelson, on August 4, 1958.

[Source](https://en.wikipedia.org/wiki/Billboard_Hot_100)

### What this app does

End to end, `hot-stuff` turns raw weekly chart appearances into browsable, analyzable data. A separate weekly job scrapes the Billboard site, stores each ranked song, and uses the [Spotipy](https://spotipy.readthedocs.io/en/2.18.0/) library to attach [Spotify Audio Features](https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject) (energy, danceability, valence, and more) to every track. *Source: original project README (preserved baseline narrative); api/models.py:L4-L89* The Flask backend then exposes this data as a JSON API for browsing individual **chart weeks**, searching by artist, looking up a track by its Spotify ID, and analyzing how a given **audio feature** trends year over year (including a **rolling average**). *Source: api/routes.py:L35-L182* The React front end consumes that API and renders interactive visualizations.

## Features

- **Weekly Hot 100 browsing** — retrieve every ranked song for a given chart week, plus per-week audio-feature averages. *Source: api/routes.py:L96-L124*
- **Artist search** — case-insensitive substring match across all chart appearances for an artist, newest week first. *Source: api/routes.py:L128-L150*
- **Per-track lookup by Spotify ID** — all chart appearances of a track, ordered by rank. *Source: api/routes.py:L72-L92*
- **Yearly audio-feature analysis** — the annual average of an audio feature together with a **5-year rolling average**. *Source: api/routes.py:L155-L182; api/funcs.py:L44-L71*
- **Single-page redirect to the current week** — the API root redirects to the latest chart week. *Source: api/routes.py:L53-L68*
- **Interactive charts** — the React front end renders visualizations with the [amCharts](https://www.amcharts.com/) library. *Source: frontend/package.json:L6*

## Tech Stack

Only versions verified from the repository's manifests and container definitions are listed below.

### Backend

| Component | Version | Source |
|-----------|---------|--------|
| Python (runtime image) | 3.11-slim-buster | Dockerfile:L1 |
| Flask | 2.0.1 | requirements.txt:L2 |
| Flask-Cors | 3.0.10 | requirements.txt:L3 |
| Flask-SQLAlchemy | 2.5.1 | requirements.txt:L5 |
| flask-marshmallow | 0.14.0 | requirements.txt:L4 |
| marshmallow | 3.12.1 | requirements.txt:L11 |
| marshmallow-sqlalchemy | 0.26.1 | requirements.txt:L12 |
| SQLAlchemy | 1.4.19 | requirements.txt:L21 |
| gunicorn | 20.1.0 | requirements.txt:L7 (pinned but **not** used by the container `CMD` — see [Deployment](#deployment)) |
| psycopg2 / psycopg2-binary | 2.9.6 / 2.9.5 | requirements.txt:L16 / L15 |
| numpy | 1.24.2 | requirements.txt:L13 |
| pandas | 2.0.0 | requirements.txt:L14 |

### Database

| Component | Version | Source |
|-----------|---------|--------|
| PostgreSQL (container image) | 15 | docker-compose.yml:L16 |

### Frontend

| Component | Version | Source |
|-----------|---------|--------|
| react / react-dom | 17.0.2 | frontend/package.json:L12-L13 |
| react-scripts | 4.0.3 | frontend/package.json:L15 |
| @amcharts/amcharts4 | 4.10.19 | frontend/package.json:L6 |
| styled-components | 5.3.0 | frontend/package.json:L16 |

## Architecture

`hot-stuff` uses a **single-origin design**: one Flask process serves **both** the compiled React SPA and the JSON API. The Flask app is constructed with `static_folder='../frontend/build'` and `static_url_path='/'`, so the root route returns the SPA's `index.html`, while the API lives under `/api/*`. *Source: api/__init__.py:L50; api/routes.py:L35-L49* Cross-origin requests are enabled with `CORS(app)`. *Source: api/__init__.py:L51* Data is read from PostgreSQL through SQLAlchemy, and the database itself is populated by an external pipeline (see [Data Pipeline](#data-pipeline)).

```mermaid
graph LR
    U[Browser / React SPA] -->|GET /| F[Flask app.py + api/*]
    U -->|GET /api/*| F
    F -->|SQLAlchemy| DB[(PostgreSQL 15)]
    SCR[External weekly scraper + Spotipy] -->|populates| DB
    F -->|serves static build| U
```

*System-context diagram. Reflects Source: `api/__init__.py` and `docker-compose.yml`.*

The sequence below traces a request to `GET /api/week/<week>`, showing how the requested week is normalized to a Saturday and how the per-week aggregation is produced. *Source: api/routes.py:L96-L124; api/funcs.py:L5-L41,L74-L105*

```mermaid
sequenceDiagram
    participant C as Client
    participant R as api/routes.py
    participant Fn as api/funcs.py
    participant DB as PostgreSQL
    C->>R: GET /api/week/<week>
    R->>Fn: get_query_week(week)
    R->>DB: query Tracks for week
    R->>Fn: get_weekly_data(tracks)
    R-->>C: {week, songs, averages, avgTempo}
```

## Project Structure

```text
hot-stuff/
├── app.py                # Entry point: imports the Flask app and runs it (Source: app.py:L1-L37)
├── api/                  # Backend Flask package
│   ├── __init__.py       # Flask bootstrap: app, CORS, DB, static serving of the React build (Source: api/__init__.py:L1-L68)
│   ├── routes.py         # Six HTTP route handlers (Source: api/routes.py:L1-L182)
│   ├── models.py         # SQLAlchemy models (Tracks, YearlyAvg) + Marshmallow schemas (Source: api/models.py:L4-L171)
│   └── funcs.py          # Helpers: week normalization, rolling average, weekly aggregation (Source: api/funcs.py:L5-L105)
├── frontend/             # React single-page app (client)
│   ├── src/              # React source (components: about, navigation, tracks, trends; styles)
│   ├── public/           # Static public assets
│   ├── build/            # Compiled production build served by Flask at "/" (Source: api/__init__.py:L50)
│   └── package.json      # Frontend dependencies + scripts (Source: frontend/package.json)
├── requirements.txt      # Python dependencies (Source: requirements.txt)
├── Dockerfile            # API image: python:3.11-slim-buster (Source: Dockerfile)
├── docker-compose.yml    # api + postgres:15 services (Source: docker-compose.yml)
└── .flaskenv             # FLASK_APP / FLASK_ENV for `flask run` (Source: .flaskenv)
```

## Getting Started

### Prerequisites

- **Docker & Docker Compose** — for the containerized path, or
- **Python 3.11** and **Node.js / npm** — for local development. *Source: Dockerfile:L1; frontend/package.json*
- **A pre-populated PostgreSQL database.** This repository expects chart data to already be loaded. The database is filled by an **external, out-of-repository** weekly scraper plus a Spotipy audio-feature enrichment pipeline; that ingestion script is **not** part of this repo and is **not** installed or run by this project. *Source: original project README (preserved baseline narrative); see [Data Pipeline](#data-pipeline).* See [Data Pipeline](#data-pipeline) for details. Without externally loaded data, the API will return empty results (and endpoints that aggregate over rows, such as `/api/week/<week>` and `/api/analysis/<feature>`, require populated tables).

### Run with Docker Compose

```bash
docker-compose up
```

This builds the `api` image from the `Dockerfile` and starts a `postgres:15` container. *Source: docker-compose.yml:L5,L16* The API becomes reachable at `http://localhost:80` because Compose maps host port `80` to the container's Flask port `5000`, and PostgreSQL is published on `5432`. *Source: docker-compose.yml:L11,L18*

### Local development

**Backend (Flask API):**

```bash
# Create the virtual environment
#   macOS/Linux: python3 -m venv venv   |   Windows: python -m venv venv   (or: py -3 -m venv venv)
python3 -m venv venv
# Activate the virtual environment
#   Windows: venv\Scripts\activate      |   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt

# Option A — use the Flask CLI (reads .flaskenv: FLASK_APP=app.py, FLASK_ENV=development)
flask run

# Option B — run the module directly (binds 0.0.0.0)
#   macOS/Linux: python3 app.py   |   Windows: python app.py   (or: py -3 app.py)
python3 app.py
```

*Source: .flaskenv:L1-L2; app.py:L1-L27.* `flask run` serves on port `5000` by default; `python3 app.py` binds `host='0.0.0.0'`. *Source: app.py:L37*

> **Caveat — Python interpreter name (`python3` vs `python`).** The commands above use `python3`, which is the interpreter name on **macOS/Linux**. On **Windows**, `python3` is not a real command — it resolves to a Microsoft Store alias stub and fails — so use **`python`** (or the version launcher **`py -3`**) instead, e.g. `python -m venv venv` and `python app.py`. This mirrors the Windows / macOS-Linux split already shown above for virtual-environment activation. *Source: .flaskenv:L1-L2; app.py:L1-L37*

**Frontend (React SPA):**

```bash
cd frontend
npm install

# Produce the production build that Flask serves from frontend/build
npm run build

# ...or run the dev server (proxies API calls to http://localhost:5000)
npm start
```

*Source: frontend/package.json:L20-L22,L44.*

> **Caveat — Node.js / OpenSSL 3:** `react-scripts` 4.0.3 does not run on modern Node.js/OpenSSL 3 without a legacy flag. Set `NODE_OPTIONS=--openssl-legacy-provider` before building or starting the front end. The Docker Compose `api` service already sets this variable. *Source: frontend/package.json:L15; docker-compose.yml:L9*

The frontend `package.json` also defines a convenience script, `start-api`, that launches the backend from the `frontend/` directory: `cd .. && venv/bin/flask run --no-debugger`. *Source: frontend/package.json:L21*

> **Caveat — `start-api` assumes a macOS/Linux virtual-environment layout.** This convenience script hard-codes the UNIX venv path `venv/bin/flask`, so it works only on **macOS/Linux**. On **Windows**, virtual-environment executables live under `venv\Scripts\` (not `venv/bin/`), so the script fails there. Launch Flask directly instead — activate the environment (`venv\Scripts\activate`) and run `flask run --no-debugger`, or invoke `venv\Scripts\flask run --no-debugger`. *Source: frontend/package.json:L21*

## Configuration

All runtime configuration is supplied through environment variables and Flask config keys.

| Variable | Value / Example | Where set | Purpose |
|----------|-----------------|-----------|---------|
| `FLASK_APP` | `app.py` | `.flaskenv` | Module the Flask CLI loads for `flask run`. *Source: .flaskenv:L1* |
| `FLASK_ENV` | `development` | `.flaskenv` | Enables Flask **debug mode** — the interactive Werkzeug debugger and the auto-reloader. This applies **not only to `flask run` but also to `python3 app.py` and `docker-compose up`**, because `app.run()` defaults to `load_dotenv=True` and therefore loads the committed `.flaskenv`. Debug mode is **unsafe to expose beyond localhost** — see the debug-mode security caveat under [Deployment](#deployment). *Source: .flaskenv:L2; app.py:L37; requirements.txt:L18* |
| `SQLALCHEMY_DATABASE_URI` | `postgresql://postgres:postgres@postgres/db` | `api/__init__.py:L57` | Database connection string. The host `postgres` is the Docker Compose **service name**. *Source: api/__init__.py:L55,L57* |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | `False` | `api/__init__.py:L58` | Disables the SQLAlchemy modification-tracking overhead. *Source: api/__init__.py:L58* |
| `POSTGRES_USER` | `postgres` | `docker-compose.yml:L20` | PostgreSQL user for the container. *Source: docker-compose.yml:L20* |
| `POSTGRES_PASSWORD` | `postgres` | `docker-compose.yml:L21` | PostgreSQL password for the container. *Source: docker-compose.yml:L21* |
| `POSTGRES_DB` | `db` | `docker-compose.yml:L22` | Default database name created in the container. *Source: docker-compose.yml:L22* |
| `NODE_OPTIONS` | `--openssl-legacy-provider` | `docker-compose.yml:L9` | Legacy OpenSSL provider required for the `react-scripts` 4.0.3 build on modern Node.js. *Source: docker-compose.yml:L9; frontend/package.json:L15* |

**Published ports:** `api` maps host `80` → container `5000` *(Source: docker-compose.yml:L11)*; `postgres` maps `5432` → `5432` *(Source: docker-compose.yml:L18)*.

> **Security — development credentials only.** The database values documented above — `POSTGRES_USER=postgres`, `POSTGRES_PASSWORD=postgres`, `POSTGRES_DB=db`, and the `SQLALCHEMY_DATABASE_URI` connection string `postgresql://postgres:postgres@postgres/db` — are **local development defaults committed to this repository for convenience**. They are **not** safe for production. A production deployment **must** supply strong, unique credentials through environment variables or a dedicated secrets manager, **must not** reuse the `postgres`/`postgres` values, and should avoid committing real secrets to version control. *Source: docker-compose.yml:L19-L22; api/__init__.py:L55*

## API Reference

The API is written in Python with the Flask framework. *Source: `api/__init__.py`:L42-L50* Base URL is `http://localhost` when running via Docker Compose (host port `80`), or `http://localhost:5000` when running Flask directly. All six routes are documented below. Example JSON payloads are **illustrative** (synthesized from the handler and schema definitions); there is no bundled test dataset.

### `GET /` — serve the React SPA

Serves the compiled SPA entry point `index.html` from the static build folder. Returns **HTML**, not JSON. *Source: api/routes.py:L35-L49*

```bash
curl http://localhost/
```

```html
<!doctype html>
<html lang="en">
  <head><meta charset="utf-8" /><title>Hot Stuff</title></head>
  <body><div id="root"></div></body>
</html>
```

### `GET /api/` — redirect to the current week

Redirects (HTTP **302**) to `week/{currentWeek}`, where `currentWeek` is computed by `get_query_week(None)` (today's normalized chart week). The relative target resolves to `/api/week/<currentWeek>`. *Source: api/routes.py:L53-L68; api/funcs.py:L5-L41*

```bash
curl -i http://localhost/api/
```

```http
HTTP/1.1 302 FOUND
Location: week/2024-01-06
```

### `GET /api/track/<spotify_id>` — look up a track by Spotify ID

| Method | Path | Path parameter | Returns |
|--------|------|----------------|---------|
| GET | `/api/track/<spotify_id>` | `spotify_id` — the Spotify track ID | JSON **array** of track objects matching `spotify_id`, ordered by `rank`. *Source: api/routes.py:L72-L92* |

Each element carries all 15 `TrackSchema` fields. *Source: api/models.py:L92-L112*

```bash
curl http://localhost/api/track/0VjIjW4GlUZAMYd2vXMi3b
```

```json
[
  {
    "id": 10432,
    "week": "2021-01-02",
    "rank": 1,
    "track": "Blinding Lights",
    "artist": "The Weeknd",
    "spotify_id": "0VjIjW4GlUZAMYd2vXMi3b",
    "energy": 0.73,
    "danceability": 0.51,
    "valence": 0.33,
    "liveness": 0.09,
    "speechiness": 0.06,
    "acousticness": 0.0,
    "instrumentalness": 0.0,
    "loudness": -5.93,
    "tempo": 171.0
  }
]
```

### `GET /api/week/<week>` — songs for a chart week

| Method | Path | Path parameter | Returns |
|--------|------|----------------|---------|
| GET | `/api/week/<week>` | `week` — a date in `YYYY-MM-DD` format | JSON **object** `{ week, songs, averages, avgTempo }`. *Source: api/routes.py:L96-L124* |

The requested date is normalized to a Saturday (the chart week) by `get_query_week`. *Source: api/funcs.py:L5-L41* `songs` is an array of `TrackSchema` objects ordered by rank; `averages` contains one entry per aggregated audio feature — **Energy, Danceability, Speechiness, Acousticness, Instrumentalness** — each as `{ feature, mean, full }` where `mean` is `int(feature_mean * 100)` and `full` is always `100`; `avgTempo` is the integer mean tempo. *Source: api/funcs.py:L74-L105*

```bash
curl http://localhost/api/week/2021-01-02
```

```json
{
  "week": "2021-01-02",
  "songs": [
    {
      "id": 10432,
      "week": "2021-01-02",
      "rank": 1,
      "track": "Blinding Lights",
      "artist": "The Weeknd",
      "spotify_id": "0VjIjW4GlUZAMYd2vXMi3b",
      "energy": 0.73,
      "danceability": 0.51,
      "valence": 0.33,
      "liveness": 0.09,
      "speechiness": 0.06,
      "acousticness": 0.0,
      "instrumentalness": 0.0,
      "loudness": -5.93,
      "tempo": 171.0
    }
  ],
  "averages": [
    { "feature": "Energy", "mean": 65, "full": 100 },
    { "feature": "Danceability", "mean": 60, "full": 100 },
    { "feature": "Speechiness", "mean": 10, "full": 100 },
    { "feature": "Acousticness", "mean": 25, "full": 100 },
    { "feature": "Instrumentalness", "mean": 2, "full": 100 }
  ],
  "avgTempo": 118
}
```

### `GET /api/artist/<artist>` — search chart appearances by artist

| Method | Path | Path parameter | Returns |
|--------|------|----------------|---------|
| GET | `/api/artist/<artist>` | `artist` — substring to match | JSON **array** of tracks whose `artist` contains `<artist>` (case-insensitive `LIKE %artist%`), ordered by `week` **descending** (newest first). *Source: api/routes.py:L128-L150* |

```bash
curl http://localhost/api/artist/Drake
```

```json
[
  {
    "id": 20551,
    "week": "2021-09-11",
    "rank": 1,
    "track": "Way 2 Sexy",
    "artist": "Drake Featuring Future & Young Thug",
    "spotify_id": "1MpKZi1zTXpERJ4pParTns",
    "energy": 0.55,
    "danceability": 0.76,
    "valence": 0.42,
    "liveness": 0.11,
    "speechiness": 0.16,
    "acousticness": 0.02,
    "instrumentalness": 0.0,
    "loudness": -6.5,
    "tempo": 136.0
  }
]
```

### `GET /api/analysis/<feature>` — yearly average and rolling average for a feature

| Method | Path | Path parameter | Returns |
|--------|------|----------------|---------|
| GET | `/api/analysis/<feature>` | `feature` — an audio-feature column (`energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `tempo`) | HTTP **200** with `{ feature, data }`, where `data` is an array of `{ year, value, rolling }`. *Source: api/routes.py:L155-L182* |

`value` is the annual average of the feature and `rolling` is its **5-year rolling average** (`df[feature].rolling(5).mean()`). Because a 5-period window needs five years of history, the first four years produce no rolling value and are omitted from `data`. *Source: api/funcs.py:L44-L71*

```bash
curl http://localhost/api/analysis/energy
```

```json
{
  "feature": "energy",
  "data": [
    { "year": "1962", "value": 0.512, "rolling": 0.508 },
    { "year": "1963", "value": 0.524, "rolling": 0.514 },
    { "year": "1964", "value": 0.531, "rolling": 0.520 }
  ]
}
```

## Data Models

The backend defines two SQLAlchemy models and two Marshmallow schemas. *Source: api/models.py:L4-L171*

### `Tracks` (table)

One row per song appearance on a weekly chart. *Source: api/models.py:L4-L89*

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer | Primary key |
| `week` | Date | Chart week (a Saturday) |
| `rank` | Integer | Chart position |
| `track` | String | Song title |
| `artist` | String | Artist credit |
| `spotify_id` | String | Spotify track ID |
| `tempo` | Float | Audio feature — beats per minute |
| `energy` | Float | Audio feature |
| `danceability` | Float | Audio feature |
| `valence` | Float | Audio feature |
| `liveness` | Float | Audio feature |
| `speechiness` | Float | Audio feature |
| `acousticness` | Float | Audio feature |
| `instrumentalness` | Float | Audio feature |
| `loudness` | Float | Audio feature — decibels |

> **Known quirk (documented, not fixed):** `Tracks.__init__` does **not** accept a `spotify_id` parameter, even though `spotify_id` is a declared column. Rows created through the constructor therefore leave `spotify_id` unset, though the column is still selected and serialized when reading. This behavior is intentional to document and is left unchanged by this documentation task. *Source: api/models.py:L58,L73-L89*

### `TrackSchema`

Serializes all **15** `Tracks` fields (this **includes** `spotify_id`): `id`, `week`, `rank`, `track`, `artist`, `spotify_id`, `energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `loudness`, `tempo`. *Source: api/models.py:L92-L112*

### `YearlyAvg` (table)

Precomputed per-year averages used by the analysis endpoint. *Source: api/models.py:L115-L154*

| Column | Type | Notes |
|--------|------|-------|
| `index` | Integer | Primary key |
| `year` | String | Calendar year |
| `energy` | Float | Yearly average |
| `danceability` | Float | Yearly average |
| `valence` | Float | Yearly average |
| `liveness` | Float | Yearly average |
| `speechiness` | Float | Yearly average |
| `acousticness` | Float | Yearly average |
| `instrumentalness` | Float | Yearly average |
| `tempo` | Float | Yearly average |

### `YearlyAvgSchema`

Serializes **9** fields (**excludes** the `index` primary key): `year`, `energy`, `valence`, `liveness`, `speechiness`, `acousticness`, `danceability`, `instrumentalness`, `tempo`. *Source: api/models.py:L157-L171*

The two tables are independent (there is no enforced foreign-key relationship); `YearlyAvg` is a precomputed aggregate derived from the same underlying chart data as `Tracks`.

```mermaid
erDiagram
    TRACKS {
        int id PK
        date week
        int rank
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
        int index PK
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
```

*Entity-reference diagram for `Tracks` and `YearlyAvg`. Source: api/models.py:L4-L171.*

## Data Pipeline

The chart data consumed by this application is produced by an **external, out-of-repository** pipeline — treated here as a **prerequisite**, not a component of this repo.

- **Tracks:** A separate script, running weekly, scrapes the Billboard site page and adds each song into the database. *Source: original project README (preserved baseline narrative).*
- **Data:** The weekly script uses the [Spotipy](https://spotipy.readthedocs.io/en/2.18.0/) library to get [Spotify Audio Features](https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject) for each track, used for visualizations.

This scraper/enrichment job is **not** included in this repository and is **not** installed or executed by this project; `hot-stuff` expects the PostgreSQL database to be populated by it. See [Prerequisites](#prerequisites).

## Deployment

### Docker image

The `Dockerfile` builds the API image from `python:3.11-slim-buster`, installs the `libpq-dev` and `gcc` system packages, installs Python dependencies from `requirements.txt`, copies the project, exposes port `5000`, and starts the app with `CMD ["python3", "app.py"]`. *Source: Dockerfile:L1-L15*

### Compose topology

`docker-compose.yml` defines two services *(Source: docker-compose.yml:L2-L24)*:

- **`api`** — built from `.` (the `Dockerfile`), publishes `80:5000`, and `depends_on` `postgres`. *Source: docker-compose.yml:L3-L13*
- **`postgres`** — image `postgres:15`, publishes `5432:5432`. *Source: docker-compose.yml:L15-L22*

```mermaid
graph TB
    Client[Browser or curl]
    subgraph compose[Docker Compose]
        API[api service<br/>built from Dockerfile<br/>CMD python3 app.py<br/>maps 80 to 5000]
        PG[(postgres 15<br/>maps 5432 to 5432)]
        API -->|depends_on| PG
    end
    Client -->|http localhost 80| API
```

*Compose deployment topology. Source: docker-compose.yml; Dockerfile.*

### Production considerations — development server, debug mode, and hardening

**Development server (not production-ready).** The container command runs `python3 app.py`, which invokes Flask's **built-in development server** via `app.run()`. *Source: app.py:L37* Although `gunicorn` 20.1.0 is pinned in `requirements.txt`, it is **not** used by the container `CMD`. *Source: requirements.txt:L7; Dockerfile:L15* Flask's development server is not intended for production use; a production deployment would typically front the app with a WSGI server such as gunicorn. This is noted as a consideration only — no code or configuration is changed by this documentation.

> **⚠️ Security — the documented deployment runs with debug mode and the interactive debugger ENABLED.** Because `.flaskenv` sets `FLASK_ENV=development` *(Source: .flaskenv:L2)* and `app.run()` loads it by default (`load_dotenv=True`), the container's `python3 app.py` process starts with **debug mode on**, which activates the **interactive Werkzeug debugger** and the auto-reloader. *Source: app.py:L37; Dockerfile:L15; requirements.txt:L18* This is **not** limited to the Flask CLI — it applies to `python3 app.py`, and therefore to `docker-compose up`. On **any unhandled error** the server returns a Werkzeug **traceback page that discloses source paths and application internals**, and it mounts a **PIN-protected, in-browser code-execution console** — an arbitrary-code-execution-class exposure (the debugger in Werkzeug 2.2.3 is not restricted to trusted hosts, and the PIN is printed to the server log, so it is not a strong security boundary). *Source: requirements.txt:L23* The committed `.flaskenv` is copied into the image (`COPY . .`) and is **not** excluded by `.dockerignore` *(Source: Dockerfile:L11; .dockerignore:L1-L3)*, and Compose publishes the app on host port **80** *(Source: docker-compose.yml:L10-L11)*, so `docker-compose up` exposes this debugger on port 80. **Before any non-local exposure, debug mode MUST be disabled** — for example, set `FLASK_ENV=production` (or call `app.run(debug=False)`) and exclude `.flaskenv` from the built image. Disabling debug is a source/configuration change and is intentionally **out of scope for this documentation-only task**; this note documents the current posture without changing any code or configuration.

**Hardening checklist before exposing beyond localhost.** The current posture is development-oriented; the items below are documented here (they are not changed by this documentation):

- **Disable debug mode / the interactive debugger** — the most important item; see the caveat above. It removes the traceback disclosure and the code-execution console. *Source: .flaskenv:L2; app.py:L37*
- **Rotate credentials** — replace the committed development database credentials with strong, externally managed secrets (detailed below and in [Configuration](#configuration)). *Source: docker-compose.yml:L19-L22; api/__init__.py:L55*
- **Restrict CORS** — the app calls `CORS(app)`, which sends `Access-Control-Allow-Origin: *` (any origin) on every response; restrict this to trusted origins for production. *Source: api/__init__.py:L51*
- **Restrict the network binding and published ports** — the server binds `0.0.0.0` (all interfaces) *(Source: app.py:L37)*, and Compose publishes both the app (`80:5000`) and PostgreSQL (`5432:5432`) *(Source: docker-compose.yml:L10-L11,L17-L18)*; firewall or narrow these, and in particular do not expose the database port publicly.
- **Update the base image and dependencies** — the base image `python:3.11-slim-buster` is built on Debian 10 "Buster", which has reached end-of-life, and several pinned dependencies carry known CVEs; rebuild on a supported base image and review dependency versions before production use. *Source: Dockerfile:L1; requirements.txt* (Upgrading the base image or dependencies is out of scope for this documentation-only task.)
- **Suppress version disclosure** — responses include a `Server: Werkzeug/<version> Python/<version>` header that reveals framework and runtime versions; a production deployment behind a reverse proxy would typically suppress or normalize it. *Source: requirements.txt:L23*

The PostgreSQL credentials shipped in `docker-compose.yml` (`postgres` / `postgres`) and the `SQLALCHEMY_DATABASE_URI` in `api/__init__.py` are **development defaults only**. A production deployment must replace them with strong, externally managed secrets (for example via environment variables or a secrets manager) and must not reuse the committed `postgres`/`postgres` values. See [Configuration](#configuration) for the full variable reference. *Source: docker-compose.yml:L19-L22; api/__init__.py:L55*

## Acknowledgements and License

- **Billboard** — the [Billboard Hot 100](https://www.billboard.com/charts/hot-100) chart ([background](https://en.wikipedia.org/wiki/Billboard_Hot_100)).
- **Spotify** — [Spotify Audio Features](https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject), accessed via the [Spotipy](https://spotipy.readthedocs.io/en/2.18.0/) library.
- **amCharts** — front-end visualizations built with [amCharts](https://www.amcharts.com/).

**License:** No license file is present in this repository, so no license is currently specified.
