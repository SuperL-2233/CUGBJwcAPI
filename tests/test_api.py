import unittest

from cugb_jwc_api.api import ApiApplication
from cugb_jwc_api.models import Notice, Snapshot


class FakeRepository:
    def __init__(self, snapshot=None, error=None):
        self.snapshot = snapshot
        self.error = error
        self.calls = 0

    def get(self):
        self.calls += 1
        if self.error:
            raise self.error
        return self.snapshot


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.notice = Notice("测试通知", "2026-07-23", "https://example.test/1")
        self.repository = FakeRepository(
            Snapshot((self.notice,), "2026-07-23T00:00:00+00:00")
        )
        self.app = ApiApplication(self.repository, "https://example.test/notices/")

    def test_health_does_not_fetch_upstream(self):
        response = self.app.dispatch("GET", "/health")
        self.assertEqual(200, response.status)
        self.assertEqual("ok", response.payload["status"])
        self.assertEqual("notice-api", response.payload["service"])
        self.assertEqual(0, self.repository.calls)

    def test_lists_notices_with_metadata(self):
        response = self.app.dispatch("GET", "/api/v1/notices?ignored=true")
        self.assertEqual(200, response.status)
        self.assertEqual("测试通知", response.payload["data"][0]["title"])
        self.assertEqual(1, response.payload["meta"]["count"])

    def test_returns_latest_notice(self):
        response = self.app.dispatch("GET", "/api/v1/notices/latest/")
        self.assertEqual(200, response.status)
        self.assertEqual(self.notice.to_dict(), response.payload["data"])

    def test_rejects_mutating_methods(self):
        response = self.app.dispatch("POST", "/api/v1/notices")
        self.assertEqual(405, response.status)

    def test_unknown_route_returns_404(self):
        response = self.app.dispatch("GET", "/api/v1/unknown")
        self.assertEqual(404, response.status)

    def test_upstream_failure_returns_502(self):
        app = ApiApplication(
            FakeRepository(error=RuntimeError("offline")), "https://example.test/"
        )
        response = app.dispatch("GET", "/api/v1/notices")
        self.assertEqual(502, response.status)
        self.assertEqual("upstream_unavailable", response.payload["error"])


if __name__ == "__main__":
    unittest.main()
