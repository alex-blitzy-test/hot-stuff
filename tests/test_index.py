'''Tests for GET /, the route that serves the built single-page application.

The rule answers with ``frontend/dist/index.html``, read through the static
folder ``../frontend/dist`` that ``create_app`` configures. That artefact is a
precondition of this module rather than something a test can produce: run
``npm run build`` (or ``cd frontend && npm run build``) before pytest, because
the suite serves the built SPA. With no index document in ``frontend/dist``
Flask answers 404 and the status assertion below fails, which is the intended
signal that the build has not run - this module never skips.
'''


def test_index_serves_the_built_spa(client):
    response = client.get('/')

    assert response.status_code == 200

    # Flask takes the media type of a static file from its extension
    assert 'text/html' in response.headers['Content-Type']

    # The mount node and the document title are the two markers Vite carries
    # into dist verbatim, so they identify the built shell without asserting
    # anything about the content-hashed asset names or script tags it emits.
    assert b'id="root"' in response.data
    assert b'Hot Stuff' in response.data
