"""Application entry point for the hot-stuff Flask backend.

Executable entry point for the ``hot-stuff`` Billboard Hot 100 audio-feature
analytics backend. This module imports the pre-configured Flask application
object ``app`` from the ``api`` package -- the object is constructed in the
package initializer (Source: api/__init__.py:L8) -- and, when the module is
executed directly (``python3 app.py``), starts Flask's built-in development
server by calling ``app.run`` inside the ``__main__`` guard below.

This file is exactly what the container runs: the image's
``CMD ["python3", "app.py"]`` invokes it (Source: Dockerfile), which launches
the Flask *development* server. Note that ``gunicorn`` is pinned in
``requirements.txt`` (Source: requirements.txt:L7) but is intentionally NOT
used by the container ``CMD``, so no production WSGI server is wired up by this
entry point.

How to run:
    Local (Flask CLI):
        ``flask run`` -- configuration is read from ``.flaskenv``
        (``FLASK_APP=app.py``, ``FLASK_ENV=development``). Source: .flaskenv
    Local (direct):
        ``python3 app.py`` -- executes the ``__main__`` block below, which
        calls ``app.run(host='0.0.0.0')``.
    Docker:
        ``docker-compose up`` -- builds the image and runs the container
        ``CMD`` described above. Source: docker-compose.yml
"""

from api import app

if __name__ == '__main__':
    # Bind to 0.0.0.0 (all network interfaces) so the container-hosted server
    # is reachable from outside the container. The image EXPOSEs port 5000
    # (Source: Dockerfile) and Compose maps host port 80 -> container port 5000
    # (Source: docker-compose.yml). The port is left at Flask's default of
    # 5000; no ``port=`` argument is added.
    app.run(host='0.0.0.0')
