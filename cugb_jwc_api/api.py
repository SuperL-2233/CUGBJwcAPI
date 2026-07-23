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


class ApiApplication:
    _detail_route = re.compile(r"^/api/v1/notices/(\d{4}-\d{2}-\d{2})/(\d{1,20})$")

    def __init__(self, repository: NoticeRepository, source_url: str) -> None:
        self.repository = repository
        self.source_url = source_url

    def dispatch(self, method: str, target: str) -> ApiResponse:
        if method not in {"GET", "HEAD"}:
            return ApiResponse(405, {"error": "method_not_allowed"})

        parsed_target = urlsplit(target)
        path = parsed_target.path.rstrip("/") or "/"
        if path == "/health":
            return ApiResponse(200, {"status": "ok", "service": "notice-api"})

        if path == "/api/v1/notices":
            try:
                page = self._parse_page(parsed_target.query)
            except ValueError as error:
                return ApiResponse(400, {"error": "invalid_page", "message": str(error)})
            try:
                snapshot = self.repository.get_page(page)
            except ResourceNotFound:
                return ApiResponse(404, {"error": "page_not_found", "page": page})
            except Exception as error:
                return self._upstream_error(error)
            meta: dict[str, object] = {
                "source": self.source_url,
                "fetched_at": snapshot.fetched_at,
                "stale": snapshot.stale,
                "page": snapshot.page,
                "count": len(snapshot.notices),
            }
            return ApiResponse(
                200,
                {"data": [notice.to_dict() for notice in snapshot.notices], "meta": meta},
            )

        if path == "/api/v1/notices/latest":
            try:
                snapshot = self.repository.get_page(1)
            except Exception as error:
                return self._upstream_error(error)
            meta = {
                "source": self.source_url,
                "fetched_at": snapshot.fetched_at,
                "stale": snapshot.stale,
            }
            if not snapshot.notices:
                return ApiResponse(404, {"error": "no_notices", "meta": meta})
            return ApiResponse(200, {"data": snapshot.notices[0].to_dict(), "meta": meta})

        match = self._detail_route.fullmatch(path)
        if match:
            published_date, notice_id = match.groups()
            try:
                date.fromisoformat(published_date)
            except ValueError:
                return ApiResponse(400, {"error": "invalid_date"})
            try:
                snapshot = self.repository.get_detail(published_date, notice_id)
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

        return ApiResponse(404, {"error": "not_found"})

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
