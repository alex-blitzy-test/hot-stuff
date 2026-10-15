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
No test here needs a database to be running. The rejection test's two local
connection attempts are its own - a port on localhost that nothing answers
(``postgresql://...@127.0.0.1:59999/nope``) and a SQLite path inside a directory
that does not exist, both refused within milliseconds - the two tests that assert
which configuration is selected replace the start-up probe instead of connecting,
and every other assertion reads ``app.config`` values only.
'''

import importlib

import pytest
from flask import Flask

import api
from api import create_app
from api.config import DevConfig, ProdConfig, TestConfig

# A URL this module supplies itself, so the assertion that follows cannot pass
# by echoing whatever the ambient environment happened to hold.
SUPPLIED_URL = 'sqlite:///:memory:'

# The five shapes a present-but-unusable connection string arrives in, all of
# which the start-up probe has to reject: whitespace that is not a URL at all, a
# string carrying no scheme, a scheme this application has no dialect for, a
# SQLite path whose directory does not exist, and a port nothing answers on.
# Rejecting the last two needs a connection attempt, not a parse, which is the
# reason the probe connects; both fail locally and within milliseconds, so no
# database has to be reachable for this test to run.
UNUSABLE_DATABASE_URLS = [
    pytest.param('   ', id='blank'),
    pytest.param('not-a-url', id='not-a-url'),
    pytest.param('redis://localhost:6379/0', id='redis-scheme'),
    pytest.param(
        'sqlite:////nonexistent-dir-xyz/probe.db', id='sqlite-missing-dir'
    ),
    pytest.param(
        'postgresql://postgres:postgres@127.0.0.1:59999/nope',
        id='pg-port-refused',
    ),
]


def test_prod_config_fails_fast_without_database_url(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)

    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        create_app(ProdConfig)


@pytest.mark.parametrize(
    'config_class',
    [
        pytest.param(DevConfig, id='development'),
        pytest.param(ProdConfig, id='production'),
    ],
)
@pytest.mark.parametrize('unusable_url', UNUSABLE_DATABASE_URLS)
def test_unusable_database_url_is_rejected_at_startup(
    monkeypatch, config_class, unusable_url
):
    '''No unusable value survives construction, under either deployment.'''
    monkeypatch.setenv('DATABASE_URL', unusable_url)

    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        create_app(config_class)


@pytest.fixture
def no_running_database(monkeypatch):
    # The probe has its own test above. The two tests below it assert which
    # configuration was selected, which is a question about the selector and not
    # about whether a database is up, so the probe stands down for them: the
    # development default is read and compared without being connected to.
    monkeypatch.setattr(api, 'check_database_url', lambda url: None)


def test_dev_config_defaults_to_the_compose_database(
    monkeypatch, no_running_database
):
    monkeypatch.delenv('DATABASE_URL', raising=False)

    app = create_app(DevConfig)

    # The credential belongs to api/config.py and to the compose service that
    # declares it, so this pins the resolved default by its scheme and its host
    # instead of restating it here: a default that pointed anywhere other than
    # the bundled development database fails the second assertion.
    uri = app.config['SQLALCHEMY_DATABASE_URI']
    assert uri.startswith('postgresql://')
    assert uri.endswith('@postgres/db')


def test_flask_env_development_selects_dev_config(
    monkeypatch, no_running_database
):
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
