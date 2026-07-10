from datetime import datetime, timedelta
import pandas as pd


def get_query_week(date):
    """Returns date of either last or next Saturday in YYYY-MM-DD format
    depending on time of the week

    Args:
        date (str | None): A date string in 'YYYY-MM-DD' form, or None to use
            today's date (used by the /api/ home route).

    Returns:
        str: A normalized Saturday chart-week label in 'YYYY-MM-DD' format.
    """

    if date:
        date = datetime.strptime(date, '%Y-%m-%d')
    else:
        # for home route
        date = datetime.today()
    date_weekday = date.weekday()
    days_till_next_sat = timedelta((12 - date_weekday) % 7)
    next_sat = date + days_till_next_sat
    last_sat = next_sat - timedelta(days=7)
    # Week normalization: compute the next Saturday via (12 - weekday) % 7 and
    # the previous Saturday (next_sat - 7 days), then snap the input date to its
    # published chart week -- return the LAST Saturday when the weekday is
    # Sunday/Monday/Tuesday (weekday in [6, 0, 1]) OR Wednesday (weekday == 2)
    # before 10:00; otherwise return the NEXT Saturday.
    if date_weekday in [
            6, 0, 1
    ] or (date_weekday == 2 and datetime.now().time() <
          datetime.now().time().replace(hour=10, minute=0)):
        return str(last_sat)[:10]
    else:
        return str(next_sat)[:10]


def get_rolling_avg(data):
    """Takes data from yearly average query and adds 5 year rolling average

    Args:
        data (list[dict]): Yearly-average query rows; each dict has a 'year'
            key plus exactly one audio-feature key.

    Returns:
        list[dict]: Records with keys 'year', 'value', and 'rolling', with
            leading NaN rolling rows dropped.
    """

    feature = [i for i in data[0].keys() if i != 'year'][0]
    df = pd.DataFrame(data)
    # Authoritative 5-period rolling average: a 5-row rolling mean over the
    # single feature column (matches the README's corrected "5-year" wording).
    df['rolling'] = df[feature].rolling(5).mean()
    # Transform: rename the single feature column to 'value', keep the added
    # 'rolling' column, convert NaNs to None, then drop the leading rows where
    # 'rolling' is NaN (the initial 4, before the 5-row window fills).
    df = df.where(pd.notnull(df), None)
    df = df.rename(columns={feature: 'value'})
    d = df.to_dict(orient='records')
    d = [i for i in d if str(i["rolling"]) != "nan"]
    return d


def get_weekly_data(data):
    """Takes weekly song data and returns average of each feature

    Args:
        data (list[dict]): Serialized Tracks rows for one chart week.

    Returns:
        dict: {'averages': [{'feature', 'mean', 'full'}], 'avgTempo': int} --
            per-feature mean scores and average tempo.
    """

    d = {}
    averages = []
    df = pd.DataFrame(data)
    for col in df[[
            'energy', 'danceability', 'speechiness', 'acousticness',
            'instrumentalness'
    ]]:
        tempObj = {}
        series = df[col]
        tempObj['feature'] = col.title()
        # x100 integer scaling: each audio-feature mean (a 0-1 fraction) is
        # multiplied by 100 and truncated to an integer percentage for charting;
        # 'full' is the constant 100 baseline used as the chart maximum.
        tempObj['mean'] = int(series.mean() * 100)
        tempObj['full'] = 100
        averages.append(tempObj)
    d['averages'] = averages
    # Tempo is averaged and truncated to an integer BPM (NOT scaled x100 like the
    # other features, since tempo is already an absolute beats-per-minute value).
    d['avgTempo'] = int(df['tempo'].mean())
    return d
