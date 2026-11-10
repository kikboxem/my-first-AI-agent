"""Dependency-light HTTP smoke tests; no Redis, Groq, or Ollama calls are made."""
import os
import sys
import unittest
from pathlib import Path

os.environ["VALUEPILOT_LOCAL_MODE"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from server import app


class HttpSmokeTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app, client=("127.0.0.1", 37661))

    def tearDown(self):
        self.client.close()

    def test_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_single_screen_home(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("CSV lead audit", response.text)
        self.assertIn('id="csv-pane"', response.text)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertIn("script-src", response.headers["content-security-policy"])
        self.assertNotIn("<script>", response.text)

    def test_scripts_served_locally(self):
        for path in ("/csv_audit.js", "/csv_ui.js", "/agent_ui.js", "/styles.css"):
            with self.subTest(path=path):
                result = self.client.get(path)
                self.assertEqual(result.status_code, 200)
                self.assertTrue("javascript" in result.headers["content-type"] or "text/css" in result.headers["content-type"])

    def test_no_upload_api(self):
        response = self.client.post("/api/upload", json={"file": "secret"})
        self.assertEqual(response.status_code, 404)

    def test_invalid_payload_rejected(self):
        response = self.client.post("/api/ask", json={"message": "x" * 301})
        self.assertEqual(response.status_code, 422)

    def test_nonlocal_agent_requests_rejected(self):
        with TestClient(app, client=("198.51.100.51", 1122)) as outsider:
            response = outsider.post("/api/ask", json={"message": "What time is it?"})
            self.assertEqual(response.status_code, 403)

    def test_cross_site_local_agent_requests_rejected(self):
        response = self.client.post(
            "/api/ask",
            headers={"Origin": "https://untrusted.example"},
            json={"message": "What time is it?"},
        )
        self.assertEqual(response.status_code, 403)


if __name__ == "__main__":
    unittest.main()
