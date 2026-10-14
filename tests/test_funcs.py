'''Tests for the three pure helpers in api/funcs.py.'''

from datetime import datetime

import pytest

import api.funcs as funcs
from api.funcs import get_query_week, get_rolling_avg, get_weekly_data

# Six consecutive chart years. The helper's window spans five rows, so the first
# four rows have no rolling mean and only the last two appear in the result.
YEARLY_TEMPOS = [
    {'year': str(year), 'tempo': float(tempo)}
    for year, tempo in zip(range(2015, 2021), range(100, 160, 10))
]

# Two chart weeks shaped as the weekly song query dumps them. The values are
# picked so that every feature mean is an exact integer percentage.
WEEK_ROWS = [
    {
        'energy': 0.85,
        'danceability': 0.55,
        'speechiness': 0.35,
        'acousticness': 0.60,
        'instrumentalness': 0.45,
        'tempo': 130.0,
    },
    {
        'energy': 0.45,
        'danceability': 0.35,
        'speechiness': 0.15,
        'acousticness': 0.20,
        'instrumentalness': 0.25,
        'tempo': 100.0,
    },
]

EXPECTED_AVERAGES = [
    {'feature': 'Energy', 'mean': 65, 'full': 100},
    {'feature': 'Danceability', 'mean': 45, 'full': 100},
    {'feature': 'Speechiness', 'mean': 25, 'full': 100},
    {'feature': 'Acousticness', 'mean': 40, 'full': 100},
    {'feature': 'Instrumentalness', 'mean': 35, 'full': 100},
]


def _frozen_datetime(frozen: datetime) -> type[datetime]:
    '''Builds a datetime whose now() and today() always report the frozen instant.

    api.funcs resolves both through its module-level `datetime` name, so patching
    that name with this subclass freezes the wall clock the helper compares
    against 10:00 without touching the real clock.
    '''

    class FrozenDateTime(datetime):

        @classmethod
        def now(cls, tz=None):
            return frozen

        @classmethod
        def today(cls):
            return frozen

    return FrozenDateTime


def test_get_query_week_buckets_every_weekday_to_its_chart_saturday():
    expected_weeks = {
        '2021-11-13': '2021-11-13',  # Saturday keeps its own week
        '2021-11-14': '2021-11-13',  # Sunday still belongs to the previous chart
        '2021-11-15': '2021-11-13',  # Monday
        '2021-11-16': '2021-11-13',  # Tuesday
        '2021-11-18': '2021-11-20',  # Thursday
        '2021-11-19': '2021-11-20',  # Friday
        '2021-11-20': '2021-11-20',  # Saturday
    }

    assert {day: get_query_week(day) for day in expected_weeks} == expected_weeks


def test_get_query_week_without_a_date_returns_a_saturday():
    assert datetime.strptime(get_query_week(None), '%Y-%m-%d').weekday() == 5


def test_get_query_week_before_ten_on_wednesday_uses_the_previous_saturday(monkeypatch):
    frozen = _frozen_datetime(datetime(2021, 11, 17, 9, 59))
    monkeypatch.setattr(funcs, 'datetime', frozen)

    assert get_query_week(None) == '2021-11-13'
    assert get_query_week('2021-11-17') == '2021-11-13'


def test_get_query_week_from_ten_on_wednesday_uses_the_next_saturday(monkeypatch):
    for hour, minute in [(10, 0), (10, 1)]:
        frozen = _frozen_datetime(datetime(2021, 11, 17, hour, minute))
        monkeypatch.setattr(funcs, 'datetime', frozen)

        assert get_query_week(None) == '2021-11-20'
        assert get_query_week('2021-11-17') == '2021-11-20'


def test_get_rolling_avg_returns_only_the_years_with_a_full_window():
    result = get_rolling_avg(YEARLY_TEMPOS)

    assert [(row['year'], row['value']) for row in result] == [
        ('2019', 140.0),
        ('2020', 150.0),
    ]
    assert [row['rolling'] for row in result] == pytest.approx([120.0, 130.0])
    assert all(set(row) == {'year', 'value', 'rolling'} for row in result)


def test_get_rolling_avg_returns_nothing_when_the_window_is_not_full():
    assert get_rolling_avg(YEARLY_TEMPOS[:4]) == []


def test_get_rolling_avg_raises_on_empty_input():
    with pytest.raises(IndexError):
        get_rolling_avg([])


def test_get_weekly_data_averages_each_feature_as_a_whole_percentage():
    result = get_weekly_data(WEEK_ROWS)

    assert result == {'averages': EXPECTED_AVERAGES, 'avgTempo': 115}
    assert all(isinstance(entry['mean'], int) for entry in result['averages'])
    assert isinstance(result['avgTempo'], int)


def test_get_weekly_data_raises_on_empty_input():
    with pytest.raises(KeyError):
        get_weekly_data([])
