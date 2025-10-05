def format_date(year, month, day):
    """Return date in format YYYY-MM-DD"""
    return f"{str(year).zfill(4)}-{str(month).zfill(2)}-{str(day).zfill(2)}"
