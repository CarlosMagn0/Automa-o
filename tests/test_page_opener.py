import json
import tempfile
import unittest
from pathlib import Path

from core.page_opener import PageConfig, load_pages


class PageConfigTests(unittest.TestCase):
    def test_accepts_https_url(self):
        PageConfig("one", "Casa", "https://example.com/bonus").validate()

    def test_rejects_credentials_in_url(self):
        with self.assertRaises(ValueError):
            PageConfig("one", "Casa", "https://user:pass@example.com/").validate()

    def test_loads_page_list(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pages.json"
            path.write_text(json.dumps([{"id":"one","name":"Casa","url":"https://example.com"}]), encoding="utf-8")
            self.assertEqual(load_pages(path)[0].id, "one")

    def test_rejects_duplicate_urls(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pages.json"
            path.write_text(json.dumps([
                {"id":"one","name":"A","url":"https://example.com"},
                {"id":"two","name":"B","url":"https://example.com"},
            ]), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_pages(path)


if __name__ == "__main__":
    unittest.main()
