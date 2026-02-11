from datetime import datetime, timezone

# конвертация unix timestamp в объект datetime
def timestamp_to_utc(timestamp):
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

# формат времени с наносекундами
def format_timestamp_with_nanoseconds(ts):
    # форматируем основную часть времени (до секунд)
    main_dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    main_dt_str = main_dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # дробная часть времени (наносекунды)
    ts_str = f"{ts:.9f}"
    nanoseconds_str = ts_str.split('.')[1]
    
    return f"{main_dt_str}.{nanoseconds_str}"