"""Small reusable formatting helpers."""


def format_timestamp(seconds: float) -> str:
    minutes, remaining_seconds = divmod(int(seconds), 60)
    return f"{minutes:02d}:{remaining_seconds:02d}"
