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

# psycopg2 is pinned to a source distribution, so it needs libpq and a compiler
RUN apt-get update \
    && apt-get -y install libpq-dev gcc

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

# only the built bundle crosses from the build stage, so the image carries no
# node toolchain; the destination is fixed by api/__init__.py's
# static_folder='../frontend/dist'
COPY --from=frontend-build /app/dist ./frontend/dist

EXPOSE 5000

CMD [ "python3", "app.py"]