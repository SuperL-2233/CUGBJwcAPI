from __future__ import annotations

import threading
import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable, TypeVar, cast

from .client import NoticeClient
from .models import DetailSnapshot, Snapshot


SnapshotType = TypeVar("SnapshotType", Snapshot, DetailSnapshot)


class NoticeRepository:
    """Thread-safe, expiring in-memory cache around the upstream client."""

    def __init__(
        self,
        client: NoticeClient,
        cache_ttl_seconds: float = 60,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.client = client
        self.cache_ttl_seconds = cache_ttl_seconds
        self.clock = clock
        self._cache: dict[str, tuple[Snapshot | DetailSnapshot, float]] = {}
        self._lock = threading.Lock()

    def get_page(self, page: int = 1) -> Snapshot:
        return self._get_cached(
            f"page:{page}",
            lambda: Snapshot(
                notices=tuple(self.client.fetch_page(page)),
                fetched_at=datetime.now(timezone.utc).isoformat(),
                page=page,
            ),
        )

    def get_detail(self, published_date: str, notice_id: str) -> DetailSnapshot:
        return self._get_cached(
            f"detail:{published_date}:{notice_id}",
            lambda: DetailSnapshot(
                detail=self.client.fetch_detail(published_date, notice_id),
                fetched_at=datetime.now(timezone.utc).isoformat(),
            ),
        )

    def _get_cached(
        self,
        key: str,
        loader: Callable[[], SnapshotType],
    ) -> SnapshotType:
        now = self.clock()
        cached = self._cache.get(key)
        if cached is not None and now < cached[1]:
            return cast(SnapshotType, cached[0])

        with self._lock:
            now = self.clock()
            cached = self._cache.get(key)
            if cached is not None and now < cached[1]:
                return cast(SnapshotType, cached[0])
            try:
                snapshot = loader()
            except Exception:
                if cached is not None:
                    return cast(SnapshotType, replace(cached[0], stale=True))
                raise
            self._cache[key] = (snapshot, now + self.cache_ttl_seconds)
            return snapshot
