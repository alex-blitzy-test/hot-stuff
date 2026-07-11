"""Application entry point for the hot-stuff Flask backend.

This module is the executable entry point for the backend "server" of the
hot-stuff Billboard Hot 100 analytics application. It imports the
pre-configured Flask application object ``app`` from the ``api`` package (the
application object is constructed in ``api/__init__.py``; Source:
api/__init__.py:L8) and, when the module is executed directly
(``python3 app.py``), starts Flask's built-in development server via
``app.run``.

The file is intentionally minimal: all application wiring (CORS, SQLAlchemy,
Marshmallow, and route registration) lives in the ``api`` package, and simply
importing ``app`` triggers that setup as a side effect (Source:
api/__init__.py:L1-L21).

Running the server:
    * Container (default): the image's ``CMD ["python3", "app.py"]`` runs this
      file (Source: Dockerfile), which launches the **Flask development
      server**. ``gunicorn`` is pinned in requirements.txt
      (Source: requirements.txt:L7) but is **not** invoked by the container
      ``CMD``; the development server is what actually serves requests.
    * Docker Compose: ``docker-compose up`` builds and starts this service
      together with PostgreSQL (Source: docker-compose.yml).
    * Local development: ``flask run`` using the settings in ``.flaskenv``
      (``FLASK_APP=app.py`` and ``FLASK_ENV=development``; Source: .flaskenv),
      or run this module directly with ``python3 app.py``.

Note:
    Flask's built-in development server is used here for convenience and for
    this project's container; it is not intended to serve production traffic.
"""
from api import app

if __name__ == '__main__':
    # Bind to 0.0.0.0 (all network interfaces) so the server is reachable
    # from outside the container. The image EXPOSEs port 5000
    # (Source: Dockerfile) and Compose maps host port 80 to container port
    # 5000 (Source: docker-compose.yml). No port is passed here, so Flask
    # falls back to its default port 5000.
    app.run(host='0.0.0.0')
