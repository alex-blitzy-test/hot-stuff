FROM node:22.23.3-bookworm-slim AS frontend-build

WORKDIR /app

# manifest and lockfile first, so the install layer caches against them
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# after npm ci, so this copy merges with the installed node_modules that
# .dockerignore keeps out of the build context
COPY frontend/ ./

# vite writes the production bundle to dist under this workdir
RUN npm run build


FROM python:3.11-slim-bookworm

WORKDIR /app

# the pinned psycopg2 is a source distribution, so it needs libpq, a compiler
# and the C library headers; gcc only recommends libc6-dev, which
# --no-install-recommends therefore skips and the build needs, so it is named
# here; all of them, the apt lists and pip's download cache are removed in this
# same layer, which leaves only the runtime library psycopg2 links against
# (libpq5, held as a manual install so the purge keeps it)
COPY requirements.txt requirements.txt
RUN apt-get update \
    && apt-get -y install --no-install-recommends libpq-dev gcc libc6-dev \
    && pip3 install --no-cache-dir -r requirements.txt \
    && apt-mark manual libpq5 \
    && apt-get purge -y --auto-remove libpq-dev gcc libc6-dev \
    && rm -rf /var/lib/apt/lists/*

# an unprivileged account owns /app and everything the application reads at
# runtime; WORKDIR creates /app as root, so its own entry is set here and the
# copies below carry the ownership of their contents
RUN useradd --create-home --uid 10001 appuser \
    && chown appuser:appuser /app

COPY --chown=appuser:appuser . .

# only the built bundle crosses from the build stage, so the image carries no
# node toolchain; the destination is fixed by api/__init__.py's
# static_folder='../frontend/dist'
COPY --chown=appuser:appuser --from=frontend-build /app/dist ./frontend/dist

EXPOSE 5000

USER appuser

CMD [ "python3", "app.py"]