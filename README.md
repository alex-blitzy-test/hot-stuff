# hot-stuff

## The Billboard Hot 100

The [Billboard Hot 100](https://www.billboard.com/charts/hot-100) is the music industry standard record chart in the United States for songs, published weekly by Billboard magazine. Chart rankings are based on sales (physical and digital), radio play, and online streaming in the United States.

The first number one song of the Billboard Hot 100 was "Poor Little Fool" by Ricky Nelson, on August 4, 1958.

[Source](https://en.wikipedia.org/wiki/Billboard_Hot_100)

## API

The API is written in Python with the Flask framework.

**Tracks:** There is a separate script, running weekly, which scrapes the Billboard site page and adds each song into the database.

**Data:** The weekly script uses the [Spotipy](https://spotipy.readthedocs.io/en/2.18.0/) library to get [Spotify Audio Features](https://developer.spotify.com/documentation/web-api/reference/#object-audiofeaturesobject) for each track, used for visualizations.

**Endpoints:**

- /api/week/\<week> : get the week's songs in rank order, best first; \<week> is YYYY-MM-DD and is resolved to the chart Saturday that closes or opens its week
- /api/artist/\<artist> : get all appeareances where the artist column contains \<artist>
- /api/track/\<spotify_id> : get all appeareances of track where the spotify_id column equals \<spotify_id>
- /api/analysis/\<feature> : get the annual average and 3 year rolling average for \<feature>
- /api/artist/\<artist>/summary : get chart-level aggregate stats for \<artist>
- /api/ : redirect to the current chart week, as a relative path so the caller keeps talking to /api/

The summary endpoint returns the artist's total weeks on chart, its unique track count, its best rank, the first and last week it appeared on chart and its average audio features; the body also echoes the artist it was asked for under `artist`.

A feature the analysis endpoint does not recognise answers 400 with an error body. Every other endpoint's path and payload are as listed above.

## Front End

The front end is written with React 18 and built with [Vite](https://vite.dev/). The Flask process serves the built front end from `frontend/dist`, on the same origin as the API, so there is no separate web server and no host to configure.

The app has four tabs: Tracks, Trends, Artists and About.

**Artists:** the Artists tab is the Artist Explorer. It searches artists as you type, debounced, and lists the matching chart appearances grouped by track name, each track showing its peak rank, the number of weeks it charted and the first and last week it appeared. Selecting a track draws that track's rank history, with rank 1 at the top, and a header card summarises the artist: total weeks on chart, unique tracks, best rank, first and last week, and average audio features.

**Client:** every request the app makes to the API goes over HTTP through one typed client module, `frontend/src/api/client.ts`, which is the only place a request is issued or a path is built. The server answers from the database; the browser never opens a database, a file or a cache.

**Visualizations:** Visualizations are created using the [amCharts](https://www.amcharts.com/) library.

**Commands:** run the front end workflow from `frontend/`:

1. `npm ci` installs the pinned dependencies from `package-lock.json`.
2. `npm run build` builds the assets Flask serves into `frontend/dist`.
3. `npx tsc --noEmit` runs the strict TypeScript type-check.
4. `npm run test` runs the Vitest and React Testing Library suite.
5. `npm run start` runs the Vite dev server, whose `/api` requests are proxied to the Flask API on `http://localhost:5000`; set `API_PROXY_TARGET` to point the proxy at an API on another port.

## Environment Variables

- `DATABASE_URL` : the database connection string, read by the application at startup. The container receives it from `docker-compose.yml`, which sets it in the `api` service's own environment, and a host-side `flask run` receives it from `.flaskenv`. Production must set it explicitly, because the application refuses to start without it. If it is set but the database cannot be reached, the application still starts and serves the static interface, and only the endpoints that read the database fail until the database becomes reachable. The production credential is supplied by the environment and is never part of the repository; the connection strings committed in `.flaskenv`, `docker-compose.yml` and `api/config.py` are the public local development placeholders for the compose database, not secrets.
- `FLASK_ENV` : selects the configuration. `development` selects the development configuration; any other value selects the production configuration, which is the one that requires `DATABASE_URL` to be set.

## Container

Build and start the stack from the repository root with `docker compose up --build -d`; the image is built in two stages and both the `api` and the `postgres` services come up, which `docker compose ps` lists. The application is served at `http://localhost/`, because the `api` service publishes host port 80 to the container's port 5000, and all four tabs work there. The `api` service takes `DATABASE_URL` from its own environment in `docker-compose.yml`. The image carries the `frontend/dist` built by its Node stage, so the container serves the built front end with no host checkout and no bind mount. The compose database starts empty and carries no chart tables, so until those tables are created and populated the data-backed endpoints answer an error and their panels show their error state. Stop the stack with `docker compose down`.

## Tests

**Python:** create the virtual environment at `venv/` with Python 3.11, which the pinned `pandas` and `numpy` wheels and the container image both require, for example `python3.11 -m venv venv`; install the test dependencies once with `venv/bin/pip install -r requirements-dev.txt`, then run the suite from the repository root with `venv/bin/python -m pytest`. The suite's `GET /` test serves the built single-page application, so run `npm run build` from `frontend/` first.

**Front End:** run `npm run test` from `frontend/`, which runs Vitest over the typed API client, the artist search's debounce behaviour and the feature select.
