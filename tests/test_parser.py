import unittest
from pathlib import Path

from cugb_api.parser import NoticeParseError, parse_notice_detail, parse_notices


class ParserTests(unittest.TestCase):
    def test_parses_notice_fields_and_resolves_relative_url(self):
        html = Path("tests/fixtures/list.html").read_text(encoding="utf-8")
        notices = parse_notices(html, "https://jwc.cugb.edu.cn/xszq/")

        self.assertEqual(2, len(notices))
        self.assertEqual("第二条 & 测试通知", notices[0].title)
        self.assertEqual("2026-07-23", notices[0].published_date)
        self.assertEqual(
            "https://jwc.cugb.edu.cn/c/2026-07-23/100002.shtml", notices[0].url
        )

    def test_rejects_page_without_notice_list(self):
        with self.assertRaises(NoticeParseError):
            parse_notices("<html><body>empty</body></html>", "https://example.test/")

    def test_parses_notice_detail_as_plain_text(self):
        html = Path("tests/fixtures/detail.html").read_text(encoding="utf-8")
        detail = parse_notice_detail(
            html,
            "https://example.test/c/2026-07-23/100002.shtml",
            notice_id="100002",
            fallback_date="2026-07-23",
        )
        self.assertEqual("测试详情标题", detail.title)
        self.assertEqual("测试作者", detail.author)
        self.assertEqual("2026-07-23", detail.published_date)
        self.assertEqual("第一段正文。\n第二段包含附件。", detail.content)
        self.assertEqual("https://example.test/download/file.pdf", detail.links[0].url)
        self.assertEqual(("https://example.test/images/example.png",), detail.images)


if __name__ == "__main__":
    unittest.main()
