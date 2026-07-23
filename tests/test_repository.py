import unittest

from cugb_jwc_api.models import Notice, NoticeDetail
from cugb_jwc_api.repository import NoticeRepository


class FakeClient:
    def __init__(self, notices):
        self.notices = notices
        self.calls = 0
        self.error = None

    def fetch_page(self, page):
        self.calls += 1
        if self.error:
            raise self.error
        return list(self.notices)

    def fetch_detail(self, published_date, notice_id):
        self.calls += 1
        if self.error:
            raise self.error
        return NoticeDetail(
            notice_id=notice_id,
            title="详情",
            published_date=published_date,
            author="",
            url=f"https://example.test/{notice_id}",
            content="正文",
        )


class RepositoryTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.0
        self.notice = Notice("测试通知", "2026-07-23", "https://example.test/1")
        self.client = FakeClient([self.notice])
        self.repository = NoticeRepository(
            self.client, cache_ttl_seconds=60, clock=lambda: self.now
        )

    def test_reuses_fresh_cache(self):
        first = self.repository.get_page(1)
        second = self.repository.get_page(1)
        self.assertIs(first, second)
        self.assertEqual(1, self.client.calls)

    def test_refreshes_expired_cache(self):
        self.repository.get_page(1)
        self.now += 61
        self.repository.get_page(1)
        self.assertEqual(2, self.client.calls)

    def test_serves_stale_cache_when_refresh_fails(self):
        fresh = self.repository.get_page(1)
        self.now += 61
        self.client.error = RuntimeError("offline")
        stale = self.repository.get_page(1)
        self.assertEqual(fresh.notices, stale.notices)
        self.assertTrue(stale.stale)

    def test_initial_failure_is_not_hidden(self):
        self.client.error = RuntimeError("offline")
        with self.assertRaisesRegex(RuntimeError, "offline"):
            self.repository.get_page(1)

    def test_caches_pages_and_details_separately(self):
        self.repository.get_page(1)
        self.repository.get_page(2)
        detail = self.repository.get_detail("2026-07-23", "100002")
        self.repository.get_detail("2026-07-23", "100002")
        self.assertEqual("正文", detail.detail.content)
        self.assertEqual(3, self.client.calls)


if __name__ == "__main__":
    unittest.main()
