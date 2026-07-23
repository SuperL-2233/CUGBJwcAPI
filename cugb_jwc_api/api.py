from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from urllib.parse import parse_qs, urlsplit

from .client import ResourceNotFound
from .repository import NoticeRepository


@dataclass(frozen=True, slots=True)
class ApiResponse:
    status: int
    payload: dict[str, object]

    def body(self) -> bytes:
        return (json.dumps(self.payload, ensure_ascii=False) + "\n").encode("utf-8")


@dataclass(frozen=True, slots=True)
class NoticeCollection:
    repository: NoticeRepository
    source_url: str


class ApiApplication:
    def __init__(
        self,
        repository: NoticeRepository,
        source_url: str,
        *,
        extra_collections: dict[str, NoticeCollection] | None = None,
    ) -> None:
        self.collections = {
            "/api/v1/notices": NoticeCollection(repository, source_url),
            **(extra_collections or {}),
        }

    def dispatch(self, method: str, target: str) -> ApiResponse:
        if method not in {"GET", "HEAD"}:
            return ApiResponse(405, {"error": "method_not_allowed"})

        parsed_target = urlsplit(target)
        path = parsed_target.path.rstrip("/") or "/"
        if path == "/health":
            return ApiResponse(200, {"status": "ok", "service": "notice-api"})

        for prefix, collection in self.collections.items():
            if path == prefix:
                return self._list(collection, prefix, parsed_target.query)
            if path == f"{prefix}/latest":
                return self._latest(collection, prefix)
            detail_match = re.fullmatch(
                rf"{re.escape(prefix)}/(\d{{4}}-\d{{2}}-\d{{2}})/(\d{{1,20}})",
                path,
            )
            if detail_match:
                return self._detail(collection, *detail_match.groups())

        return ApiResponse(404, {"error": "not_found"})

    def _list(
        self,
        collection: NoticeCollection,
        prefix: str,
        query: str,
    ) -> ApiResponse:
        try:
            page = self._parse_page(query)
        except ValueError as error:
            return ApiResponse(400, {"error": "invalid_page", "message": str(error)})
        try:
            snapshot = collection.repository.get_page(page)
        except ResourceNotFound:
            return ApiResponse(404, {"error": "page_not_found", "page": page})
        except Exception as error:
            return self._upstream_error(error)
        meta: dict[str, object] = {
            "source": collection.source_url,
            "fetched_at": snapshot.fetched_at,
            "stale": snapshot.stale,
            "page": snapshot.page,
            "count": len(snapshot.notices),
        }
        return ApiResponse(
            200,
            {
                "data": [notice.to_dict(prefix) for notice in snapshot.notices],
                "meta": meta,
            },
        )

    def _latest(self, collection: NoticeCollection, prefix: str) -> ApiResponse:
        try:
            snapshot = collection.repository.get_page(1)
        except Exception as error:
            return self._upstream_error(error)
        meta = {
            "source": collection.source_url,
            "fetched_at": snapshot.fetched_at,
            "stale": snapshot.stale,
        }
        if not snapshot.notices:
            return ApiResponse(404, {"error": "no_notices", "meta": meta})
        return ApiResponse(
            200,
            {"data": snapshot.notices[0].to_dict(prefix), "meta": meta},
        )

    def _detail(
        self,
        collection: NoticeCollection,
        published_date: str,
        notice_id: str,
    ) -> ApiResponse:
        try:
            date.fromisoformat(published_date)
        except ValueError:
            return ApiResponse(400, {"error": "invalid_date"})
        try:
            snapshot = collection.repository.get_detail(published_date, notice_id)
        except ResourceNotFound:
            return ApiResponse(404, {"error": "notice_not_found"})
        except Exception as error:
            return self._upstream_error(error)
        return ApiResponse(
            200,
            {
                "data": snapshot.detail.to_dict(),
                "meta": {
                    "fetched_at": snapshot.fetched_at,
                    "stale": snapshot.stale,
                },
            },
        )

    @staticmethod
    def _parse_page(query: str) -> int:
        values = parse_qs(query, keep_blank_values=True).get("page", ["1"])
        if len(values) != 1 or not values[0].isdigit():
            raise ValueError("page must be one integer")
        page = int(values[0])
        if not 1 <= page <= 1000:
            raise ValueError("page must be between 1 and 1000")
        return page

    @staticmethod
    def _upstream_error(error: Exception) -> ApiResponse:
        return ApiResponse(
            502,
            {
                "error": "upstream_unavailable",
                "message": str(error),
            },
        )
