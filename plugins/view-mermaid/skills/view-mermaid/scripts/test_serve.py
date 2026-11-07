import http.client
import http.server
import json
import tempfile
import threading
import unittest
from functools import partial
from html.parser import HTMLParser
from pathlib import Path

import serve


class ScriptSources(HTMLParser):
    def __init__(self):
        super().__init__()
        self.sources = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            src = dict(attrs).get("src")
            if src:
                self.sources.append(src)


class ViewerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.source = Path(cls.tmp.name)
        (cls.source / "01-flow.mmd").write_text(
            "flowchart TD\n%% title: Luồng kiểm thử\nA --> B\n", encoding="utf-8"
        )
        cls.assets = Path(__file__).resolve().parent.parent / "assets"
        handler = partial(
            serve.Handler, source=cls.source, assets=cls.assets,
            title="Mermaid diagrams", activity=[0],
        )
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.tmp.cleanup()

    def get(self, path):
        connection = http.client.HTTPConnection(*self.server.server_address)
        try:
            connection.request("GET", path)
            response = connection.getresponse()
            return response.status, response.getheader("Content-Type"), response.read()
        finally:
            connection.close()

    def test_offline_pele_bundle_is_served(self):
        status, content_type, body = self.get("/assets/pele.global.js")
        self.assertEqual(status, 200)
        self.assertEqual(content_type, "application/javascript")
        self.assertGreater(len(body), 1000)
        self.assertEqual(body, (self.assets / "pele.global.js").read_bytes())

    def test_both_pages_load_the_offline_renderer(self):
        for path in ("/", "/full?name=01-flow.mmd"):
            with self.subTest(path=path):
                status, _, body = self.get(path)
                self.assertEqual(status, 200)
                scripts = ScriptSources()
                scripts.feed(body.decode())
                self.assertEqual(scripts.sources, ["/assets/pele.global.js"])
                for src in scripts.sources:
                    self.assertEqual(self.get(src)[0], 200)

    def test_unknown_assets_are_not_exposed(self):
        for path in ("/assets/../scripts/serve.py", "/assets/missing.js"):
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0], 404)

    def test_missing_fullscreen_diagram(self):
        self.assertEqual(self.get("/full?name=missing.mmd")[0], 404)

    def test_title_and_source_are_safely_embedded(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory)
            (source / "01-unsafe.mmd").write_text(
                'flowchart TD\n%% title: <script>alert(1)</script>\nA --> B',
                encoding="utf-8",
            )
            page = serve.render_index(source, "<unsafe>")
            self.assertIn("&lt;unsafe&gt;", page)
            self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", page)
            self.assertNotIn("<script>alert(1)</script>", page)
            embedded = serve._json_embed({"src": "</script>"})
            self.assertEqual(json.loads(embedded), {"src": "</script>"})
            self.assertNotIn("</script>", embedded)


if __name__ == "__main__":
    unittest.main()
