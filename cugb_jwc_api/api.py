from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.parse import urlsplit

from .repository import NoticeRepository


@dataclass(frozen=True, slots=True)
class ApiResponse:
    status: int
    payload: dict[str, object]

    def body(self) -> bytes:
        return (json.dumps(self.payload, ensure_ascii=False) + "\n").encode("utf-8")


class ApiApplication:
    def __init__(self, repository: NoticeRepository, source_url: str) -> None:
        self.repository = repository
        self.source_url = source_url

    def dispatch(self, method: str, target: str) -> ApiResponse:
        if method not in {"GET", "HEAD"}:
            return ApiResponse(405, {"error": "method_not_allowed"})

        path = urlsplit(target).path.rstrip("/") or "/"
        if path == "/health":
            return ApiResponse(200, {"status": "ok", "service": "notice-api"})
        if path not in {"/api/v1/notices", "/api/v1/notices/latest"}:
            return ApiResponse(404, {"error": "not_found"})

        try:
            snapshot = self.repository.get()
        except Exception as error:
            return ApiResponse(
                502,
                {
                    "error": "upstream_unavailable",
                    "message": str(error),
                },
            )

        meta: dict[str, object] = {
            "source": self.source_url,
            "fetched_at": snapshot.fetched_at,
            "stale": snapshot.stale,
        }
        if path.endswith("/latest"):
            if not snapshot.notices:
                return ApiResponse(404, {"error": "no_notices", "meta": meta})
            return ApiResponse(200, {"data": snapshot.notices[0].to_dict(), "meta": meta})

        meta["count"] = len(snapshot.notices)
        return ApiResponse(
            200,
            {"data": [notice.to_dict() for notice in snapshot.notices], "meta": meta},
        )
