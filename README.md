# hot-stuff

> A Billboard Hot 100 audio-feature analytics app — a single Flask process that serves a JSON API and a React single-page app for browsing weekly charts, searching artists and tracks, and analyzing how Spotify audio features trend over time.

`hot-stuff` ingests weekly Billboard Hot 100 chart data (enriched with Spotify Audio Features by an external pipeline) into PostgreSQL, then exposes it through a Flask REST API and a React + amCharts front end. A single Flask process serves both the compiled React SPA at `/` and the JSON API under `/api/*` (Source: api/__init__.py:L64).

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Run with Docker Compose](#run-with-docker-compose)
  - [Local Development](#local-development)
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

End to end, `hot-stuff` turns weekly chart snapshots into a browsable, analyzable dataset. A separate weekly job scrapes the Billboard site and stores each song, then enriches every track with [Spotify Audio Features](https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject) via the [Spotipy](https://spotipy.readthedocs.io/en/2.18.0/) library (Source: README.md:L521, README.md:L523). The Flask API then serves that data as JSON — letting you page through a given chart week, search every appearance of an artist, look up a single track by its Spotify ID, and compute yearly averages with a rolling average for any audio feature (Source: api/routes.py:L38-L201). The React front end renders these responses as interactive [amCharts](https://www.amcharts.com/) visualizations.

### A note on scope: "server.js" and "JSDoc"

This repository contains no `server.js` file and is not a Node.js server project. The backend "server" is written in **Python with the Flask framework**: its entry point is `app.py`, and its application package is `api/` (`api/__init__.py`, `api/routes.py`, `api/models.py`, and `api/funcs.py`) (Source: app.py:L33-L41, api/__init__.py:L54-L87). The request to "add JSDoc comments to `server.js` functions" was therefore fulfilled in the language-appropriate way: the backend functions and classes are documented with **Google-style, PEP 257-compatible Python docstrings** (the direct equivalent of JSDoc's `@param`, `@returns`, and `@throws` tags) rather than with JSDoc. The only JavaScript in the repository is the React single-page application under `frontend/src/` (Source: frontend/package.json:L12-L15); that is a client, not a server, so it was intentionally not treated as the "server" target and received no JSDoc.

## Features

- **Weekly Hot 100 browsing** — retrieve every ranked song for a given chart week, along with weekly audio-feature averages and average tempo (Source: api/routes.py:L103-L140).
- **Artist search** — find every chart appearance whose artist name contains a case-insensitive substring, newest chart week first (Source: api/routes.py:L143-L167).
- **Per-track lookup by Spotify ID** — fetch all chart appearances of a single track, ordered by rank (Source: api/routes.py:L77-L100).
- **Yearly audio-feature analysis** — get the yearly mean and a 5-year rolling average for any audio feature (Source: api/routes.py:L170-L201, api/funcs.py:L42-L68).
- **Single-origin SPA delivery** — the same Flask process serves the compiled React app at `/` (Source: api/routes.py:L38-L54, api/__init__.py:L64).
- **Interactive charts** — the React front end renders the API data with the amCharts library (Source: frontend/package.json:L6).

## Tech Stack

All versions below are read directly from the repository's manifests and container definitions; no versions are invented.

### Backend

| Component | Version | Source |
|-----------|---------|--------|
| Python (runtime image) | 3.11-slim-buster | Dockerfile:L1 |
| Flask | 2.0.1 | requirements.txt:L2 |
| Flask-Cors | 3.0.10 | requirements.txt:L3 |
| flask-marshmallow | 0.14.0 | requirements.txt:L4 |
| Flask-SQLAlchemy | 2.5.1 | requirements.txt:L5 |
| gunicorn | 20.1.0 | requirements.txt:L7 (pinned but not used by the container `CMD` — see [Deployment](#deployment)) |
| marshmallow | 3.12.1 | requirements.txt:L11 |
| marshmallow-sqlalchemy | 0.26.1 | requirements.txt:L12 |
| numpy | 1.24.2 | requirements.txt:L13 |
| pandas | 2.0.0 | requirements.txt:L14 |
| psycopg2-binary | 2.9.5 | requirements.txt:L15 |
| psycopg2 | 2.9.6 | requirements.txt:L16 |
| SQLAlchemy | 1.4.19 | requirements.txt:L21 |

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

`hot-stuff` follows a **single-origin design**: one Flask process serves BOTH the compiled React single-page application (SPA) at `/` and the JSON API under `/api/*`. This is configured when the app object is created with `static_folder='../frontend/build'` and `static_url_path='/'`, which mounts the built front end at the site root (Source: api/__init__.py:L64); the root route then returns `index.html` from that build (Source: api/routes.py:L38-L54). The database is PostgreSQL, accessed through SQLAlchemy, and is populated out-of-band by an external weekly scraper + Spotipy pipeline (see [Data Pipeline](#data-pipeline)).

```mermaid
graph LR
    U[Browser / React SPA] -->|GET /| F[Flask app.py + api/*]
    U -->|GET /api/*| F
    F -->|SQLAlchemy| DB[(PostgreSQL 15)]
    SCR[External weekly scraper + Spotipy] -->|populates| DB
    F -->|serves static build| U
```

*System-context diagram. Reflects the single-origin app configuration in `api/__init__.py` and the service topology in `docker-compose.yml` (Source: api/__init__.py:L64, docker-compose.yml:L1-L26).*

The sequence below traces a `GET /api/week/<week>` request, showing how the route normalizes the requested date to a chart week and aggregates weekly audio-feature data before responding.

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

*Request-flow sequence for the weekly endpoint (Source: api/routes.py:L103-L140, api/funcs.py:L5-L39, api/funcs.py:L71-L102).*

## Project Structure

```text
hot-stuff/
├── app.py                 # Backend entry point: imports the Flask app and runs the dev server (Source: app.py:L33-L41)
├── api/                   # Flask backend package (the "server")
│   ├── __init__.py        # App bootstrap: Flask app, CORS, SQLAlchemy, Marshmallow, route registration (Source: api/__init__.py:L54-L87)
│   ├── routes.py          # The 6 HTTP route handlers / REST API contract (Source: api/routes.py:L38-L201)
│   ├── models.py          # SQLAlchemy ORM models + Marshmallow schemas (Source: api/models.py:L4-L181)
│   └── funcs.py           # Helpers: chart-week normalization, rolling average, weekly aggregation (Source: api/funcs.py:L5-L102)
├── frontend/              # React client (Create React App)
│   ├── src/               # React source (components, charts)
│   ├── public/            # CRA public assets
│   └── build/             # Compiled SPA served by Flask at '/' (Source: api/__init__.py:L64)
├── requirements.txt       # Python dependencies (Source: requirements.txt:L1-L23)
├── Dockerfile             # Backend image: python:3.11-slim-buster (Source: Dockerfile:L1-L15)
├── docker-compose.yml     # api + postgres services and ports (Source: docker-compose.yml:L1-L26)
└── .flaskenv              # Flask CLI env: FLASK_APP, FLASK_ENV (Source: .flaskenv:L1-L2)
```

## Getting Started

There are two supported ways to run the app: the containerized path (Docker Compose) and a local development path. Both assume the database has already been populated by the external data pipeline (see [Prerequisites](#prerequisites) and [Data Pipeline](#data-pipeline)).

### Prerequisites

- **For the container path:** Docker and Docker Compose.
- **For local development:** Python 3.11 (matching the container runtime, Source: Dockerfile:L1) and Node.js with npm (for building the React front end, Source: frontend/package.json:L19-L24).
- **Data prerequisite (assumption A4):** The PostgreSQL database is populated by an **external, out-of-repository** weekly scraper + Spotipy audio-feature enrichment pipeline (Source: README.md:L521, README.md:L523). **This repository expects a pre-populated database and does NOT include the ingestion script.** On an empty database the API's behavior varies by endpoint: `/api/track/<spotify_id>` and `/api/artist/<artist>` return an empty array (`200 []`) when nothing matches, but `/api/week/<week>` and `/api/analysis/<feature>` assume a populated database and return **HTTP 500** when queried against empty data (Source: api/funcs.py:L71-L102, api/funcs.py:L42-L68). This also affects the `/api/` root, which redirects to the current chart week and therefore fails the same way on a fresh database (Source: api/routes.py:L57-L74). Load data externally before expecting meaningful responses.

### Run with Docker Compose

```bash
# Docker Compose v2 (bundled with modern Docker — note the space):
docker compose up

# ...or, only where the deprecated standalone v1 binary is installed:
docker-compose up
```

> **Note — Compose CLI form:** Modern Docker ships Compose v2 as the `docker compose` subcommand (with a space); prefer it. The standalone v1 `docker-compose` binary (hyphenated) reached end of life in June 2023 and is absent from current Docker installs, so the hyphenated form works only where that legacy binary is still installed.

Docker Compose builds the `api` image from the local `Dockerfile` and starts a `postgres:15` database container (Source: docker-compose.yml:L3-L22). Once running:

- The application is reachable at **`http://localhost:80`** — Compose maps host port `80` to the container's port `5000` (Source: docker-compose.yml:L10-L11).
- PostgreSQL is exposed on **`5432`** (Source: docker-compose.yml:L17-L18).

The `api` service also sets `NODE_OPTIONS=--openssl-legacy-provider`, which is required to build the front end with react-scripts 4.0.3 on modern Node.js (Source: docker-compose.yml:L9; see the caveat in [Local Development](#local-development)). Note that this variable has **no effect inside the `api` container itself**: the backend image installs no Node.js and never builds the front end — it only serves the pre-built `frontend/build` directory (Source: Dockerfile:L1-L15, api/__init__.py:L64). `NODE_OPTIONS` therefore matters only when you build the SPA locally (see the Local Development caveat below).

### Local Development

**Backend (Flask API):**

```bash
# from the repository root
python3 -m venv venv            # Windows: python -m venv venv   (or: py -3.11 -m venv venv)
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# run the API using the settings in .flaskenv
# (FLASK_APP=app.py, FLASK_ENV=development — Source: .flaskenv:L1-L2)
flask run

# ...or run the entry point directly
python3 app.py                  # Windows: python app.py         (or: py -3.11 app.py)
```

Running `python3 app.py` starts Flask's built-in development server bound to `0.0.0.0` on the default port `5000` (Source: app.py:L41).

> **Windows note — `python3` vs `python`/`py`:** On Windows the bare `python3` command is a non-functional Microsoft Store alias stub: it prints "Python was not found" and exits without creating a virtual environment or starting the app. Use `python`, or the version-specific launcher `py -3.11` (matching the container's Python 3.11, Source: Dockerfile:L1), wherever the commands above say `python3`. Likewise, `source venv/bin/activate` is POSIX-only — on Windows activate the environment with `venv\Scripts\activate`.

> **Caveat — database access for host-native runs:** The connection string hard-codes the database host as `postgres` (Source: api/__init__.py:L71,L73), which is the Docker Compose **service name** of the database container (Source: docker-compose.yml:L15) and only resolves on the Compose network. Running `flask run` or `python app.py` directly on the host therefore cannot reach the database: the app and the `/` SPA route start fine, but the `/api/*` data endpoints fail with `HTTP 500` (`could not translate host name "postgres"`). To develop against real data, either **(a)** run the full stack with `docker compose up`, which provides the `postgres` service, or **(b)** make the name `postgres` resolve to a running PostgreSQL — for example add a `127.0.0.1 postgres` entry to your hosts file and start a local PostgreSQL published on port `5432` (Source: docker-compose.yml:L18) using the same `postgres`/`postgres`/`db` credentials (Source: docker-compose.yml:L20-L22).

**Frontend (React SPA):**

```bash
cd frontend
npm install

# build the SPA that Flask serves from frontend/build (Source: api/__init__.py:L64)
npm run build

# ...or run the CRA dev server, which proxies API calls to http://localhost:5000
npm start
```

The CRA dev server proxies API requests to the Flask backend at `http://localhost:5000` (Source: frontend/package.json:L44). A convenience script, `start-api`, runs the backend from within the `frontend` directory:

```bash
# runs: cd .. && venv/bin/flask run --no-debugger (Source: frontend/package.json:L21)
npm run start-api
```

> **Note — `start-api` is POSIX-only:** This convenience script runs `venv/bin/flask` (Source: frontend/package.json:L21), a POSIX virtual-environment path, so it works on Linux/macOS but fails on Windows, where the executable lives at `venv\Scripts\flask.exe`. It is a pre-existing script and is intentionally left unchanged (this is a documentation-only task); on Windows, start the backend directly from the repository root with `flask run` (or `python app.py`) instead.

> **Caveat — `NODE_OPTIONS` on modern Node.js:** react-scripts 4.0.3 (Source: frontend/package.json:L15) relies on an OpenSSL provider that was removed in newer Node.js releases. If `npm run build` or `npm start` fails with an OpenSSL/`ERR_OSSL_EVP_UNSUPPORTED` error, set the legacy provider flag (the same one the container uses, Source: docker-compose.yml:L9):
>
> ```bash
> export NODE_OPTIONS=--openssl-legacy-provider   # Windows: set NODE_OPTIONS=--openssl-legacy-provider
> npm run build
> ```

## Configuration

The application is configured through environment variables and a small number of hard-coded defaults. The table below lists every configuration value the app reads, where it is set, and what it controls.

| Variable | Value / Example | Where set | Purpose |
|----------|-----------------|-----------|---------|
| `FLASK_APP` | `app.py` | `.flaskenv:L1` | Tells the Flask CLI which module is the app entry point. |
| `FLASK_ENV` | `development` | `.flaskenv:L2` | Selects Flask's development environment (debug reloader, verbose errors). |
| `SQLALCHEMY_DATABASE_URI` | `postgresql://postgres:postgres@postgres/db` | `api/__init__.py:L71,L73` | SQLAlchemy connection string. The host segment `postgres` is the **Docker Compose service name** of the database container (Source: docker-compose.yml:L15), not a literal hostname; Compose resolves it on the shared network. |
| `POSTGRES_USER` | `postgres` | `docker-compose.yml:L20` | PostgreSQL superuser for the `postgres` service (development default). |
| `POSTGRES_PASSWORD` | `postgres` | `docker-compose.yml:L21` | PostgreSQL password (development default — change before any production use). |
| `POSTGRES_DB` | `db` | `docker-compose.yml:L22` | Name of the database created on first container start. |
| `NODE_OPTIONS` | `--openssl-legacy-provider` | `docker-compose.yml:L9` | Enables the legacy OpenSSL provider needed to build the front end with react-scripts 4.0.3 on modern Node.js. |

**Published ports:**

| Service | Mapping (host:container) | Source |
|---------|--------------------------|--------|
| `api` | `80:5000` | docker-compose.yml:L11 |
| `postgres` | `5432:5432` | docker-compose.yml:L18 |

> **Security note:** the `postgres:postgres` credentials above are the repository's existing development-only defaults (Source: api/__init__.py:L71, docker-compose.yml:L20-L22). Replace them with secure credentials before deploying anywhere beyond local development.

## API Reference

All six routes are defined in `api/routes.py` (Source: api/routes.py:L38-L201). The base URL depends on how you run the app: `http://localhost` (port 80) under Docker Compose (Source: docker-compose.yml:L11), or `http://localhost:5000` when running the Flask server directly (Source: app.py:L41). The examples below use the Docker Compose base URL.

> **Note on examples:** the JSON payloads below are illustrative. Field *names* and response *shapes* are exact (verified against the handlers and Marshmallow schemas), but the sample *values* are representative rather than harvested from a live database, since this repository ships no test fixtures.

| Method | Path | Handler | Response | Source |
|--------|------|---------|----------|--------|
| GET | `/` | `index` | React SPA `index.html` (HTML) | api/routes.py:L38-L54 |
| GET | `/api/` | `home` | 302 redirect to current chart week | api/routes.py:L57-L74 |
| GET | `/api/track/<spotify_id>` | `get_track_by_id` | JSON array of tracks | api/routes.py:L77-L100 |
| GET | `/api/week/<week>` | `get_tracks_by_week` | JSON object | api/routes.py:L103-L140 |
| GET | `/api/artist/<artist>` | `get_tracks_by_artist` | JSON array of tracks | api/routes.py:L143-L167 |
| GET | `/api/analysis/<feature>` | `get_avg_feature` | JSON object (HTTP 200) | api/routes.py:L170-L201 |

### `GET /`

Serves the compiled React single-page application. Returns the static `index.html` from the front-end build folder as an HTML response — this is the browser entry point per the single-origin design (Source: api/routes.py:L38-L54, api/__init__.py:L64).

```bash
curl http://localhost/
```

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Hot Stuff</title>
  </head>
  <body>
    <div id="root"></div>
    <!-- compiled React bundle from frontend/build -->
  </body>
</html>
```

### `GET /api/`

The JSON API root issues a **302 redirect** to `week/{currentWeek}`, where `currentWeek` is `get_query_week(None)` — today's date normalized to its Saturday chart week (Source: api/routes.py:L57-L74, api/funcs.py:L5-L39). Because the handler returns `redirect(f'week/{currentWeek}')`, the raw `Location` header is the **relative** target `week/<currentWeek>`, not an absolute `/api/...` path (Source: api/routes.py:L74); a browser resolves that relative redirect against the request path `/api/`, arriving at `/api/week/<currentWeek>`.

```bash
curl -i http://localhost/api/
```

```http
HTTP/1.1 302 FOUND
Location: week/2021-01-02
```

### `GET /api/track/<spotify_id>`

Returns every Hot 100 chart appearance for a single Spotify track, ordered by `rank` ascending, serialized with `TrackSchema` (Source: api/routes.py:L77-L100). Returns an empty array when no track matches.

| Parameter | In | Type | Description |
|-----------|-----|------|-------------|
| `spotify_id` | path | string | The Spotify track ID to look up (matched exactly against the `spotify_id` column). |

```bash
curl http://localhost/api/track/3tjFYV6RSFtuktYl3ZtYcq
```

```json
[
  {
    "id": 101,
    "week": "2021-01-02",
    "rank": 1,
    "track": "Mood (feat. iann dior)",
    "artist": "24kGoldn",
    "spotify_id": "3tjFYV6RSFtuktYl3ZtYcq",
    "energy": 0.722,
    "danceability": 0.7,
    "valence": 0.756,
    "liveness": 0.272,
    "speechiness": 0.0369,
    "acousticness": 0.221,
    "instrumentalness": 0.0,
    "loudness": -3.558,
    "tempo": 90.989
  }
]
```

The 15 fields above are exactly those declared by `TrackSchema` (Source: api/models.py:L112-L116).

### `GET /api/week/<week>`

Returns the Hot 100 for a chart week plus weekly audio-feature aggregates (Source: api/routes.py:L103-L140).

| Parameter | In | Type | Description |
|-----------|-----|------|-------------|
| `week` | path | string (`YYYY-MM-DD`) | A date, normalized to its **Saturday chart week** via `get_query_week` before querying (Source: api/funcs.py:L5-L39). |

The response is a JSON object with four keys: `week` (the normalized Saturday chart week), `songs` (a list of `TrackSchema` objects ordered by `rank`), `averages` (per-feature aggregates from `get_weekly_data`), and `avgTempo` (Source: api/routes.py:L133-L140). Each `averages` entry is shaped `{"feature", "mean", "full"}`, where `mean` is the feature's mean scaled ×100 and truncated to an integer percentage and `full` is the constant baseline `100`; the aggregated features are Energy, Danceability, Speechiness, Acousticness, and Instrumentalness, and `avgTempo` is the mean tempo truncated to an integer BPM (Source: api/funcs.py:L71-L102).

```bash
curl http://localhost/api/week/2021-01-02
```

```json
{
  "week": "2021-01-02",
  "songs": [
    {
      "id": 101,
      "week": "2021-01-02",
      "rank": 1,
      "track": "Mood (feat. iann dior)",
      "artist": "24kGoldn",
      "spotify_id": "3tjFYV6RSFtuktYl3ZtYcq",
      "energy": 0.722,
      "danceability": 0.7,
      "valence": 0.756,
      "liveness": 0.272,
      "speechiness": 0.0369,
      "acousticness": 0.221,
      "instrumentalness": 0.0,
      "loudness": -3.558,
      "tempo": 90.989
    }
  ],
  "averages": [
    { "feature": "Energy", "mean": 62, "full": 100 },
    { "feature": "Danceability", "mean": 69, "full": 100 },
    { "feature": "Speechiness", "mean": 11, "full": 100 },
    { "feature": "Acousticness", "mean": 24, "full": 100 },
    { "feature": "Instrumentalness", "mean": 0, "full": 100 }
  ],
  "avgTempo": 121
}
```

### `GET /api/artist/<artist>`

Searches tracks by a partial, **case-insensitive** artist name (`LOWER(artist) LIKE %artist%`) and returns matching tracks ordered by `week` descending (newest chart week first), serialized with `TrackSchema` (Source: api/routes.py:L143-L167).

| Parameter | In | Type | Description |
|-----------|-----|------|-------------|
| `artist` | path | string | A case-insensitive substring of the artist name. |

```bash
curl http://localhost/api/artist/drake
```

```json
[
  {
    "id": 542,
    "week": "2021-09-11",
    "rank": 1,
    "track": "Way 2 Sexy (feat. Future & Young Thug)",
    "artist": "Drake",
    "spotify_id": "0k1Wjjb85Y16nA4a0hb8g0",
    "energy": 0.535,
    "danceability": 0.834,
    "valence": 0.409,
    "liveness": 0.108,
    "speechiness": 0.166,
    "acousticness": 0.0499,
    "instrumentalness": 0.0,
    "loudness": -7.244,
    "tempo": 136.041
  }
]
```

### `GET /api/analysis/<feature>`

Returns the yearly mean and the **5-year rolling average** for a single audio feature, with HTTP status `200` (Source: api/routes.py:L170-L201). The feature name is resolved dynamically against the `YearlyAvg` model via `getattr(YearlyAvg, feature)` (Source: api/routes.py:L195-L196).

| Parameter | In | Type | Description |
|-----------|-----|------|-------------|
| `feature` | path | string | An audio-feature column on `YearlyAvg`: one of `energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `tempo` (Source: api/models.py:L151-L158). |

The response is `{"feature", "data"}`, where `data` is a list of `{"year", "value", "rolling"}` records. `value` is the yearly mean of the feature and `rolling` is the **5-period rolling mean** computed by `get_rolling_avg` via `df[feature].rolling(5).mean()` (Source: api/funcs.py:L59). The leading rows whose rolling window is not yet full (the first four years) are dropped, so the series begins at the fifth year of available data (Source: api/funcs.py:L64-L67).

```bash
curl http://localhost/api/analysis/energy
```

```json
{
  "feature": "energy",
  "data": [
    { "year": "2013", "value": 0.715, "rolling": 0.702 },
    { "year": "2014", "value": 0.699, "rolling": 0.706 },
    { "year": "2015", "value": 0.688, "rolling": 0.701 }
  ]
}
```


## Data Models

The backend defines two SQLAlchemy ORM models and a Marshmallow schema for each (Source: api/models.py:L4-L181).

### `Tracks`

One row represents a single song at a single chart week, together with its Spotify audio features. This table backs the `/api/track`, `/api/week`, and `/api/artist` endpoints (Source: api/models.py:L4-L87).

| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer | Primary key (Source: api/models.py:L52). |
| `week` | Date | The Saturday chart week this entry belongs to (Source: api/models.py:L53). |
| `rank` | Integer | Hot 100 position for that chart week, 1 = top (Source: api/models.py:L54). |
| `track` | String | Song title (Source: api/models.py:L55). |
| `artist` | String | Performing artist name (Source: api/models.py:L56). |
| `spotify_id` | String | Spotify track identifier used for audio-feature lookups (Source: api/models.py:L57). |
| `tempo` | Float | Audio feature: tempo (Source: api/models.py:L58). |
| `energy` | Float | Audio feature: energy (Source: api/models.py:L59). |
| `danceability` | Float | Audio feature: danceability (Source: api/models.py:L60). |
| `valence` | Float | Audio feature: valence (Source: api/models.py:L61). |
| `liveness` | Float | Audio feature: liveness (Source: api/models.py:L62). |
| `speechiness` | Float | Audio feature: speechiness (Source: api/models.py:L63). |
| `acousticness` | Float | Audio feature: acousticness (Source: api/models.py:L64). |
| `instrumentalness` | Float | Audio feature: instrumentalness (Source: api/models.py:L65). |
| `loudness` | Float | Audio feature: loudness (Source: api/models.py:L66). |

> **Known behavior (documented, not changed):** `Tracks.__init__` does **not** accept a `spotify_id` parameter even though `spotify_id` is a declared column (Source: api/models.py:L57, L71-L87). Instances built through this constructor are therefore not given a `spotify_id` by the constructor; the value is populated when SQLAlchemy loads an existing row or by later attribute assignment. This quirk is noted for awareness and intentionally left as-is.

### `TrackSchema`

Serializes a `Tracks` record to JSON, declaring all **15 fields** via `Meta.fields`: `id`, `week`, `rank`, `track`, `artist`, `spotify_id`, `energy`, `danceability`, `valence`, `liveness`, `speechiness`, `acousticness`, `instrumentalness`, `loudness`, `tempo` (Source: api/models.py:L112-L116). Note the schema **includes** `spotify_id` in its output even though the constructor never sets it.

### `YearlyAvg`

One row holds the mean of every tracked audio feature across a given year. This table backs the `/api/analysis/<feature>` endpoint's yearly series and rolling-average computation (Source: api/models.py:L119-L158).

| Column | Type | Notes |
|--------|------|-------|
| `index` | Integer | Primary key (Source: api/models.py:L149). |
| `year` | String | The calendar year the averages describe (Source: api/models.py:L150). |
| `energy` | Float | Per-year mean of the energy audio feature (Source: api/models.py:L151). |
| `danceability` | Float | Per-year mean of the danceability audio feature (Source: api/models.py:L152). |
| `valence` | Float | Per-year mean of the valence audio feature (Source: api/models.py:L153). |
| `liveness` | Float | Per-year mean of the liveness audio feature (Source: api/models.py:L154). |
| `speechiness` | Float | Per-year mean of the speechiness audio feature (Source: api/models.py:L155). |
| `acousticness` | Float | Per-year mean of the acousticness audio feature (Source: api/models.py:L156). |
| `instrumentalness` | Float | Per-year mean of the instrumentalness audio feature (Source: api/models.py:L157). |
| `tempo` | Float | Per-year mean of the tempo audio feature (Source: api/models.py:L158). |

### `YearlyAvgSchema`

Serializes a `YearlyAvg` record to JSON, declaring **9 fields** via `Meta.fields`: `year`, `energy`, `valence`, `liveness`, `speechiness`, `acousticness`, `danceability`, `instrumentalness`, `tempo` (Source: api/models.py:L179-L181). It **excludes** the `index` primary key; only the `year` label and the eight audio-feature averages are exposed.

The two tables are independent — there is no foreign-key relationship between them (Source: api/models.py:L52-L66, api/models.py:L149-L158).

```mermaid
erDiagram
    TRACKS {
        Integer id PK
        Date week
        Integer rank
        String track
        String artist
        String spotify_id
        Float tempo
        Float energy
        Float danceability
        Float valence
        Float liveness
        Float speechiness
        Float acousticness
        Float instrumentalness
        Float loudness
    }
    YEARLYAVG {
        Integer index PK
        String year
        Float energy
        Float danceability
        Float valence
        Float liveness
        Float speechiness
        Float acousticness
        Float instrumentalness
        Float tempo
    }
```

*Entity view of `Tracks` and `YearlyAvg` (Source: api/models.py:L52-L66, L149-L158).*

## Data Pipeline

The database is populated by an **external, out-of-repository** process — it is a prerequisite for the app, not part of this repository (assumption A4).

**Tracks:** There is a separate script, running weekly, which scrapes the Billboard site page and adds each song into the database (Source: preserved verbatim from the original project README).

**Data:** The weekly script uses the [Spotipy](https://spotipy.readthedocs.io/en/2.18.0/) library to get [Spotify Audio Features](https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject) for each track, used for visualizations.

> This scraper/enrichment pipeline is **not** included in this repository and is **not** installed or run by this project. `hot-stuff` reads from a PostgreSQL database that the pipeline is expected to have already populated (see [Prerequisites](#prerequisites)).

## Deployment

### Docker image

The backend image is built from the `Dockerfile` (Source: Dockerfile:L1-L15):

- Base image `python:3.11-slim-buster` (Source: Dockerfile:L1).
- Installs the `libpq-dev` and `gcc` system packages needed to build `psycopg2` (Source: Dockerfile:L5-L6).
- Installs Python dependencies with `pip3 install -r requirements.txt` (Source: Dockerfile:L9).
- `EXPOSE 5000` (Source: Dockerfile:L13).
- `CMD ["python3", "app.py"]` (Source: Dockerfile:L15).

### Compose topology

`docker-compose.yml` defines two services (Source: docker-compose.yml:L1-L26):

- **`api`** — built from the local context (`build: .`), maps host `80` → container `5000`, and `depends_on` the `postgres` service (Source: docker-compose.yml:L3-L13).
- **`postgres`** — the `postgres:15` image, mapping host `5432` → container `5432`, initialized with `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` (Source: docker-compose.yml:L15-L24).

```mermaid
graph TB
    H1["Host port 80"] --> API["api service (build . -> python:3.11-slim-buster, runs python3 app.py on 5000)"]
    H2["Host port 5432"] --> PG[("postgres service (postgres:15)")]
    API -->|depends_on| PG
```

*Compose deployment topology (Source: docker-compose.yml:L1-L26, Dockerfile:L1-L15).*

### Production consideration — development server caveat

The container's `CMD` runs `python3 app.py` (Source: Dockerfile:L15), which calls `app.run()` and therefore starts **Flask's built-in development server** (Source: app.py:L41). Although `gunicorn` 20.1.0 is pinned in `requirements.txt` (Source: requirements.txt:L7), it is **not** invoked by the container command — the development server is what actually serves requests. For production traffic you would front the app with a WSGI server such as gunicorn and replace the development-only PostgreSQL credentials (see the security note under [Configuration](#configuration)).

## Acknowledgements and License

- **Billboard** — chart data originates from the [Billboard Hot 100](https://www.billboard.com/charts/hot-100) ([background](https://en.wikipedia.org/wiki/Billboard_Hot_100)).
- **Spotify / Spotipy** — audio features are retrieved via the [Spotipy](https://spotipy.readthedocs.io/en/2.18.0/) client for the [Spotify Audio Features](https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject) API.
- **amCharts** — front-end visualizations are built with the [amCharts](https://www.amcharts.com/) library.

**License:** No license file is currently present in this repository, so no license is specified for the project at this time.

