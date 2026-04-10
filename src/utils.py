from datetime import datetime, timedelta, timezone


def today():
    return datetime.now(tz=timezone(timedelta(hours=3), name='MSK')).date()
