'''Tests for the deployment wiring: the configuration classes, the factory's
selector and the module-level entry point.

Every other module in this suite builds its application through
``create_app(TestConfig)``, so the wiring a deployment actually runs would
otherwise never execute: ``DevConfig``'s development default, the ``FLASK_ENV``
selector in ``create_app``, ``ProdConfig``'s fail-fast read of ``DATABASE_URL``
and ``app.py``'s module-level ``app = create_app()``. This module is the only
place those branches are exercised, and it is what fails if one of them
regresses into a wrong default or into a silent production configuration.

The environment each test depends on is set through ``monkeypatch`` and no
application is built at import, so neither collection nor the result depends on
the ambient ``DATABASE_URL`` or ``FLASK_ENV`` - pytest loads no ``.flaskenv``.
Nothing here opens a socket or a database connection: the assertions read
``app.config`` values only.
'''

import importlib

import pytest
from flask import Flask

from api import create_app
from api.config import DevConfig, ProdConfig, TestConfig

# A URL this module supplies itself, so the assertion that follows cannot pass
# by echoing whatever the ambient environment happened to hold.
SUPPLIED_URL = 'sqlite:///:memory:'


def test_prod_config_fails_fast_without_database_url(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        create_app(ProdConfig)


def test_dev_config_defaults_to_the_compose_database(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)

    app = create_app(DevConfig)

    # The credential belongs to api/config.py and to the compose service that
    # declares it, so this pins the resolved default by its scheme and its host
    # instead of restating it here: a default that pointed anywhere other than
    # the bundled development database fails the second assertion.
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    assert uri.startswith('postgresql://')
    assert uri.endswith('@postgres/db')


def test_flask_env_development_selects_dev_config(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('FLASK_ENV', 'development')

    app = create_app()

    # The class attribute resolves the same development default through the
    # same descriptor, so equality proves the selector chose DevConfig rather
    # than ProdConfig, which would have raised before this point.
    assert app.config['SQLALCHEMY_DATABASE_URI'] == DevConfig.SQLALCHEMY_DATABASE_URI


@pytest.mark.parametrize(
    'flask_env',
    [pytest.param(None, id='unset'), pytest.param('production', id='production')],
)
def test_any_other_flask_env_selects_prod_config(monkeypatch, flask_env):
    '''Anything but development is a deployment, which must not default.'''
    monkeypatch.delenv('DATABASE_URL', raising=False)
    if flask_env is None:
        monkeypatch.delenv('FLASK_ENV', raising=False)
    else:
        monkeypatch.setenv('FLASK_ENV', flask_env)

    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        create_app()


def test_explicitly_passed_config_wins_over_flask_env(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.setenv('FLASK_ENV', 'development')

    app = create_app(TestConfig)

    assert app.config['SQLALCHEMY_DATABASE_URI'] == 'sqlite:///:memory:'
    assert app.config['TESTING'] is True


def test_app_module_builds_the_application_from_the_factory(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', SUPPLIED_URL)
    monkeypatch.delenv('FLASK_ENV', raising=False)

    # Imported inside the test so collection does not depend on the ambient
    # environment, and reloaded so the module-level create_app() call runs
    # against the environment set above.
    module = importlib.reload(importlib.import_module('app'))

    assert isinstance(module.app, Flask)
    assert module.app.config['SQLALCHEMY_DATABASE_URI'] == SUPPLIED_URL
    # the supplied URL is also TestConfig's, so the URI alone would not tell an
    # entry that went through the factory's selector from one that hardcoded
    # the test configuration: TESTING is left at Flask's default by every
    # configuration but TestConfig, which sets it
    assert module.app.config['TESTING'] is False
