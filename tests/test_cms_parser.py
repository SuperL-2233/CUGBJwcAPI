import unittest
from pathlib import Path
from unittest.mock import patch

from cugb_api.cms_client import CmsNoticeClient
from cugb_api.cms_parser import parse_cms_detail, parse_cms_notices


class CmsParserTests(unittest.TestCase):
    def test_parses_list_without_duplicate_links(self):
        html = Path("tests/fixtures/cms_list.html").read_text(encoding="utf-8")
        notices = parse_cms_notices(html, "https://cms.example.test/news/")
        self.assertEqual(2, len(notices))
        self.assertEqual("学院列表第二条", notices[0].title)
        self.assertEqual("2026-07-23", notices[0].published_date)
        self.assertEqual(
            "https://cms.example.test/c/2026-07-23/200002.shtml",
            notices[0].url,
        )

    def test_parses_detail_content_links_and_images(self):
        html = Path("tests/fixtures/cms_detail.html").read_text(encoding="utf-8")
        detail = parse_cms_detail(
            html,
            "https://cms.example.test/c/2026-07-23/200002.shtml",
            notice_id="200002",
            fallback_date="2026-07-23",
        )
        self.assertEqual("学院详情标题", detail.title)
        self.assertEqual("测试作者", detail.author)
        self.assertEqual("正文第一段。\n正文第二段，包含附件。", detail.content)
        self.assertEqual("https://cms.example.test/upload/file.pdf", detail.links[0].url)
        self.assertEqual(("https://cms.example.test/upload/image.png",), detail.images)

    def test_parses_detail_without_author(self):
        html = Path("tests/fixtures/cms_detail.html").read_text(encoding="utf-8")
        html = html.replace(
            "2026-07-23　发布：测试作者　点击：",
            "发布时间：2026-07-23　阅读：",
        )
        detail = parse_cms_detail(
            html,
            "https://example.test/xgb/c/2026-07-23/200002.shtml",
            notice_id="200002",
            fallback_date="2026-07-23",
        )
        self.assertEqual("", detail.author)
        self.assertEqual("2026-07-23", detail.published_date)

    def test_supports_nested_detail_path_prefix(self):
        html = Path("tests/fixtures/cms_detail.html").read_text(encoding="utf-8")
        client = CmsNoticeClient(
            "https://example.test/xgb/notices/",
            detail_path_prefix="/xgb/c",
        )
        final_url = "https://example.test/xgb/c/2026-07-23/200002.shtml"
        with patch.object(client, "_download", return_value=(html, final_url)) as download:
            detail = client.fetch_detail("2026-07-23", "200002")
        download.assert_called_once_with(final_url)
        self.assertEqual("学院详情标题", detail.title)


if __name__ == "__main__":
    unittest.main()
