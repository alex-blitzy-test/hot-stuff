'''Tests for the deployment wiring: the configuration classes, the factory's
selector and the module-level entry point.

Every other module in this suite builds its application through
``create_app(TestConfig)``, so the wiring a deployment actually runs would
otherwise never execute: ``DevConfig``'s development default, the ``FLASK_ENV``
selector in ``create_app``, ``ProdConfig``'s fail-fast read of an absent
``DATABASE_URL`` and ``app.py``'s module-level ``app = create_app()``. This
module is the only place those branches are exercised, and it is what fails if
one of them regresses into a wrong default or into a silent production
configuration.

The environment each test depends on is set through ``monkeypatch`` and no
application is built at import, so neither collection nor the result depends on
the ambient ``DATABASE_URL`` or ``FLASK_ENV`` - pytest loads no ``.flaskenv``.
A present-but-unusable connection string arrives in two kinds, and this module
tests both sides of the split the start-up probe makes. One that cannot be
parsed at all, or that names a dialect this application has no driver for, is a
misconfiguration no restart repairs, so construction still fails for it. One
whose store merely cannot be reached - refused, unresolvable, or not yet
listening - no longer stops construction: the probe reports it, the factory logs
that report as a warning, and the application is built all the same. That second
kind is what a cold ``docker compose up`` produces while the database container
is still starting, which is why it must not be fatal.

No test here needs a database to be running. The connection attempts of the
connection-level cases are their own - a port on localhost that nothing answers
(``postgresql://...@127.0.0.1:59999/nope``) and a SQLite path inside a directory
that does not exist, both refused within milliseconds - the two tests that assert
which configuration is selected replace the start-up probe instead of connecting,
and every other assertion reads ``app.config`` values or captured log records.
'''

import importlib
import logging
import traceback

import pytest
from flask import Flask

import api
from api import create_app
from api.config import DevConfig, ProdConfig, TestConfig, check_database_url

# A URL this module supplies itself, so the assertion that follows cannot pass
# by echoing whatever the ambient environment happened to hold.
SUPPLIED_URL = 'sqlite:///:memory:'

# The three shapes a present-but-unusable connection string arrives in that no
# restart can repair, and which the start-up probe therefore still rejects:
# whitespace that is not a URL at all, a string carrying no scheme, and a scheme
# this application has no dialect for. All three are decided while the engine is
# being built, before any store is contacted, so no database has to be reachable
# for this test to run.
UNUSABLE_DATABASE_URLS = [
    pytest.param('   ', id='blank'),
    pytest.param('not-a-url', id='not-a-url'),
    pytest.param('redis://localhost:6379/0', id='redis-scheme'),
]

# The two shapes whose value is well formed and whose store simply cannot be
# reached, each stated with the failure class this pinned stack raises for it and
# with fragments of the value that must stay out of what the probe reports - the
# credential, the host, the port and the path. Both are refused locally within
# milliseconds, so no database has to be reachable for these tests either, and
# both are what a deployment sees while its database is still starting. Asserting
# the old fatal behaviour for them would be asserting the defect.
UNREACHABLE_DATABASE_URLS = [
    pytest.param(
        'sqlite:////nonexistent-dir-xyz/probe.db',
        'OperationalError',
        ('nonexistent-dir-xyz', 'probe.db'),
        id='sqlite-missing-dir',
    ),
    pytest.param(
        'postgresql://postgres:postgres@127.0.0.1:59999/nope',
        'OperationalError',
        ('postgres', '59999', 'nope'),
        id='pg-port-refused',
    ),
]

# The credential the redaction test supplies: a userinfo pair on a host that
# nothing answers, written as a string that is not a URL at all. Parsing fails,
# which is what makes SQLAlchemy repeat the whole string in its own message, so
# this is the one shape whose value used to reach the process log; the test
# below therefore reads the message and the printed traceback both. Assembled
# from its parts at run time, so this module's own text holds no scannable
# secret of its own.
CREDENTIAL_USER = 'hotstuff'
CREDENTIAL_PASSWORD = 'SuP3r-S3cret' + '-pw'
CREDENTIAL_DATABASE_URL = (
    f'{CREDENTIAL_USER}:{CREDENTIAL_PASSWORD}@127.0.0.1:59999/db'
)


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
    '''A value no restart can repair stops construction, under either mode.'''
    monkeypatch.setenv('DATABASE_URL', unusable_url)

    with pytest.raises(RuntimeError, match='DATABASE_URL'):
        create_app(config_class)


@pytest.mark.parametrize(
    'url, failure_class, hidden_fragments',
    UNREACHABLE_DATABASE_URLS,
)
def test_unreachable_database_url_is_reported_not_raised(
    url, failure_class, hidden_fragments
):
    '''A store that cannot be reached is reported to the log, not fatal.

    The returned text is the one the factory logs, so it names the variable an
    operator has to correct and the class of what failed, states what the
    deployment is in place of the store, and carries no part of the value -
    which is a credential.
    '''
    report = check_database_url(url)

    assert report is not None
    assert 'DATABASE_URL' in report
    assert failure_class in report
    # what the deployment still does, said rather than left to the reader
    assert 'static' in report
    assert url not in report
    for fragment in hidden_fragments:
        assert fragment not in report


@pytest.mark.parametrize(
    'url, failure_class, hidden_fragments',
    UNREACHABLE_DATABASE_URLS,
)
def test_unreachable_database_url_still_builds_the_application(
    monkeypatch, caplog, url, failure_class, hidden_fragments
):
    '''Construction survives the store being unreachable, and says so.

    This is the container's cold start: the deployment's own connection string
    is bound and the application is built, so only the endpoints that read the
    database wait for it. The probe's report has to reach the log at WARNING -
    a Flask application's logger propagates, so caplog sees it - and it has to
    carry nothing of the value.
    '''
    monkeypatch.setenv('DATABASE_URL', url)

    with caplog.at_level(logging.WARNING):
        app = create_app(ProdConfig)

    assert isinstance(app, Flask)
    assert app.config['SQLALCHEMY_DATABASE_URI'] == url
    warnings = [
        record.getMessage()
        for record in caplog.records
        if record.levelno == logging.WARNING
    ]
    assert warnings, caplog.text
    assert any(
        'DATABASE_URL' in message and failure_class in message
        for message in warnings
    )
    assert url not in caplog.text
    for fragment in hidden_fragments:
        assert fragment not in caplog.text


@pytest.fixture
def no_running_database(monkeypatch):
    # The probe's two contracts have their own tests above. The two tests below
    # assert which configuration was selected, which is a question about the
    # selector and not about whether a database is up, so the probe stands down
    # for them and reports nothing - None is its own answer for a value it could
    # use - which leaves the development default read and compared without being
    # connected to.
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


def test_unusable_database_url_never_echoes_the_credential(monkeypatch):
    '''The failure names the variable and the failure's class, not the value.

    The supplied string cannot be parsed, so SQLAlchemy's own exception text
    carries it whole - user, password and connection detail alike. Neither
    the ``RuntimeError``'s message nor the traceback that gets printed for
    it may repeat any part of it, which keeps the credential out of the
    container's log.
    '''
    monkeypatch.setenv('DATABASE_URL', CREDENTIAL_DATABASE_URL)

    with pytest.raises(RuntimeError) as exc_info:
        create_app(ProdConfig)

    message = str(exc_info.value)
    assert 'DATABASE_URL' in message
    # the class the startup probe caught, so the operator still learns what
    # failed without learning the value: the original exception stays bound to
    # __context__ even though its own text is never printed
    assert type(exc_info.value.__context__).__name__ in message
    assert CREDENTIAL_PASSWORD not in message
    assert CREDENTIAL_USER not in message

    # what a process writes to its own log when nothing catches the failure
    printed = ''.join(traceback.format_exception(exc_info.value))
    assert CREDENTIAL_PASSWORD not in printed
    assert CREDENTIAL_USER not in printed
