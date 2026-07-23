import unittest
from pathlib import Path

from cugb_api.settings import load_settings


class SettingsTests(unittest.TestCase):
    def test_example_config_is_valid(self):
        settings = load_settings(Path("config.example.json"))
        self.assertEqual("https://jwc.cugb.edu.cn/xszq/", settings.source_url)
        self.assertEqual(60, settings.cache_ttl_seconds)
        self.assertEqual(8000, settings.server.port)
        self.assertEqual("https://sai.cugb.edu.cn/xyxw/", settings.ai_college.news_url)
        self.assertEqual("https://sai.cugb.edu.cn/xygg/", settings.ai_college.notices_url)
        self.assertEqual(
            "https://bm.cugb.edu.cn/xgb/jjxg/", settings.student_affairs.news_url
        )
        self.assertEqual(
            "https://bm.cugb.edu.cn/xgb/tzgg/", settings.student_affairs.notices_url
        )


if __name__ == "__main__":
    unittest.main()
