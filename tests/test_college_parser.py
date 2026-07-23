import unittest
from pathlib import Path

from cugb_jwc_api.college_parser import parse_college_detail, parse_college_notices


class CollegeParserTests(unittest.TestCase):
    def test_parses_list_without_duplicate_links(self):
        html = Path("tests/fixtures/college_list.html").read_text(encoding="utf-8")
        notices = parse_college_notices(html, "https://college.example.test/news/")
        self.assertEqual(2, len(notices))
        self.assertEqual("学院列表第二条", notices[0].title)
        self.assertEqual("2026-07-23", notices[0].published_date)
        self.assertEqual(
            "https://college.example.test/c/2026-07-23/200002.shtml",
            notices[0].url,
        )

    def test_parses_detail_content_links_and_images(self):
        html = Path("tests/fixtures/college_detail.html").read_text(encoding="utf-8")
        detail = parse_college_detail(
            html,
            "https://college.example.test/c/2026-07-23/200002.shtml",
            notice_id="200002",
            fallback_date="2026-07-23",
        )
        self.assertEqual("学院详情标题", detail.title)
        self.assertEqual("测试作者", detail.author)
        self.assertEqual("正文第一段。\n正文第二段，包含附件。", detail.content)
        self.assertEqual("https://college.example.test/upload/file.pdf", detail.links[0].url)
        self.assertEqual(("https://college.example.test/upload/image.png",), detail.images)


if __name__ == "__main__":
    unittest.main()
