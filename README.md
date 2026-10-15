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

- /api/week/\<week> : get songs ranked 0-100 for \<week> in YYYY-MM-DD format
- /api/artist/\<artist> : get all appeareances where the artist column contains \<artist>
- /api/track/\<spotify_id> : get all appeareances of track where the spotify_id column equals \<spotify_id>
- /api/analysis/\<feature> : get the annual average and 3 year rolling average for \<feature>
- /api/artist/\<artist>/summary : get chart-level aggregate stats for \<artist>

The summary endpoint returns the artist's total weeks on chart, its unique track count, its best rank, the first and last week it appeared on chart and its average audio features.

A feature the analysis endpoint does not recognise answers 400 with an error body. Every other endpoint keeps the path and the response shape it has always had.

## Front End

The front end is written with React 18 and built with [Vite](https://vite.dev/). The Flask process serves the built front end from `frontend/dist`, on the same origin as the API, so there is no separate web server and no host to configure.

The app has four tabs: Tracks, Trends, Artists and About.

**Artists:** the Artists tab is the Artist Explorer. It searches artists as you type, debounced, and lists the matching chart appearances grouped by track name, each track showing its peak rank, the number of weeks it charted and the first and last week it appeared. Selecting a track draws that track's rank history, with rank 1 at the top, and a header card summarises the artist: total weeks on chart, unique tracks, best rank, first and last week, and average audio features.

**Client:** every tab reaches the API over HTTP through one typed client module, `frontend/src/api/client.ts`, which is the only place a request is issued or a path is built. The server answers from the database; the browser never opens a database, a file or a cache.

**Visualizations:** Visualizations are created using the [amCharts](https://www.amcharts.com/) library.

**Commands:** `npm run build` from `frontend/` builds the assets Flask serves, and `npm run test` from `frontend/` runs the Vitest and React Testing Library suite.

## Environment Variables

- `DATABASE_URL` : the database connection string, read by the application at startup. The container receives it from `docker-compose.yml`, which sets it in the `api` service's own environment, and a host-side `flask run` receives it from `.flaskenv`. Production must set it explicitly, because the application refuses to start without it. The production credential is supplied by the environment and is never part of the repository; the connection strings committed in `.flaskenv`, `docker-compose.yml` and `api/config.py` are the public local development placeholders for the compose database, not secrets.
- `FLASK_ENV` : selects the configuration. `development` selects the development configuration; any other value selects the production configuration, which is the one that requires `DATABASE_URL` to be set.

## Tests

**Python:** install the test dependencies once with `venv/bin/pip install -r requirements-dev.txt`, then run the suite from the repository root with `venv/bin/python -m pytest`. The suite's `GET /` test serves the built single-page application, so run `npm run build` from `frontend/` first.

**Frontend:** run `npm run test` from `frontend/`, which runs Vitest over the typed API client, the artist search's debounce behaviour and the feature select.
