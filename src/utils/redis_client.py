"""Shared Redis client, distributed locks, and rate limiting."""

from contextlib import contextmanager
from collections.abc import Iterator

from redis import Redis

from src.utils.config import settings

redis_client = Redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=2,
    socket_timeout=3,
    health_check_interval=30,
)


@contextmanager
def distributed_lock(name: str, timeout: int = 600) -> Iterator[bool]:
    lock = redis_client.lock(name, timeout=timeout, blocking_timeout=1)
    acquired = lock.acquire(blocking=True)
    try:
        yield acquired
    finally:
        if acquired and lock.owned():
            lock.release()


def rate_limit(key: str) -> bool:
    redis_key = f"rate:{key}"
    with redis_client.pipeline() as pipeline:
        pipeline.incr(redis_key)
        pipeline.expire(redis_key, 60, nx=True)
        count, _ = pipeline.execute()
    return int(count) <= settings.rate_limit_per_minute
