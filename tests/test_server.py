import json
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import gpio
import server


class RoboFaceServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(
            ("127.0.0.1", 0), server.RoboFaceHandler
        )
        cls.base_url = f"http://127.0.0.1:{cls.httpd.server_port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        with server._state_lock:
            server._current_state = "smile"
        if hasattr(server, "_rotation_lock"):
            with server._rotation_lock:
                server._current_rotation = 0
        with gpio._lock:
            gpio._available = None
            gpio._level = gpio.LOW

    def request_json(self, path, method="GET", payload=None):
        data = None
        headers = {}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base_url + path, data=data, headers=headers, method=method
        )
        with urllib.request.urlopen(request) as response:
            return response.status, json.load(response)

    def test_offline_assets_are_served(self):
        for path, content_type in (
            ("/", "text/html"),
            ("/RoboFace.lottie", "application/octet-stream"),
            ("/vendor/dotlottie-wc.js", "application/javascript"),
            ("/vendor/dotlottie-player.wasm", "application/wasm"),
        ):
            with self.subTest(path=path):
                with urllib.request.urlopen(self.base_url + path) as response:
                    self.assertEqual(response.status, 200)
                    self.assertIn(content_type, response.headers["Content-Type"])
                    self.assertTrue(response.read())

    def test_lists_all_states(self):
        status, payload = self.request_json("/api/states")

        self.assertEqual(status, 200)
        self.assertEqual(payload["states"], server.VALID_STATES)

    def test_html_initializes_the_local_runtime_before_player(self):
        with urllib.request.urlopen(self.base_url + "/") as response:
            html = response.read().decode("utf-8")

        self.assertIn('from "./vendor/dotlottie-wc.js"', html)
        self.assertIn('setWasmUrl("./vendor/dotlottie-player.wasm")', html)
        self.assertIn('document.createElement("dotlottie-wc")', html)
        self.assertNotIn("https://", html)

    def test_html_uses_black_background_and_responsive_rotation(self):
        with urllib.request.urlopen(self.base_url + "/") as response:
            html = response.read().decode("utf-8")

        self.assertIn("background: #000", html)
        self.assertIn('fetch("/api/rotation")', html)
        self.assertIn("rotation === 90 || rotation === 270", html)
        self.assertIn('quarterTurn ? "100vh" : "100vw"', html)
        self.assertIn('quarterTurn ? "100vw" : "100vh"', html)
        self.assertIn("rotate(${rotation}deg)", html)

    def test_html_preserves_aspect_ratio_after_rotation(self):
        with urllib.request.urlopen(self.base_url + "/") as response:
            html = response.read().decode("utf-8")

        self.assertIn('setLayout({ fit: "contain", align: [0.5, 0.5] })', html)
        self.assertIn("dotLottie.resize()", html)
        self.assertIn('player.style.transform = "translate(-50%, -50%)"', html)
        self.assertIn("void player.offsetWidth", html)
        self.assertNotIn('player.style.visibility = "hidden"', html)
        reset_index = html.index('player.style.transform = "translate(-50%, -50%)"')
        layout_index = html.index("void player.offsetWidth", reset_index)
        resize_index = html.index("dotLottie.resize()", layout_index)
        rotate_index = html.index("rotate(${rotation}deg)", resize_index)
        self.assertLess(reset_index, layout_index)
        self.assertLess(layout_index, resize_index)
        self.assertLess(resize_index, rotate_index)
        self.assertIn("if (rotationPolling) return", html)
        self.assertIn("rotationPolling = true", html)
        self.assertIn("rotationPolling = false", html)

    def test_updates_current_state(self):
        status, payload = self.request_json(
            "/api/state", method="PUT", payload={"state": "daze"}
        )
        self.assertEqual((status, payload), (200, {"state": "daze"}))

        status, payload = self.request_json("/api/state")
        self.assertEqual((status, payload), (200, {"state": "daze"}))

    def test_reads_and_updates_rotation(self):
        status, payload = self.request_json("/api/rotation")
        self.assertEqual((status, payload), (200, {"rotation": 0}))

        status, payload = self.request_json(
            "/api/rotation", method="PUT", payload={"rotation": 90}
        )
        self.assertEqual((status, payload), (200, {"rotation": 90}))

        status, payload = self.request_json("/api/rotation")
        self.assertEqual((status, payload), (200, {"rotation": 90}))

    def test_reads_gpio_defaults_to_low(self):
        status, payload = self.request_json("/api/gpio")

        self.assertEqual(
            (status, payload), (200, {"pin": 17, "value": 0, "level": "low"})
        )

    def test_updates_gpio_level(self):
        status, payload = self.request_json(
            "/api/gpio", method="PUT", payload={"value": 1}
        )
        self.assertEqual(
            (status, payload), (200, {"pin": 17, "value": 1, "level": "high"})
        )

        status, payload = self.request_json("/api/gpio")
        self.assertEqual(
            (status, payload), (200, {"pin": 17, "value": 1, "level": "high"})
        )

    def test_rejects_invalid_gpio_value(self):
        for value in (2, -1, "1", 1.0, True, None):
            with self.subTest(value=value):
                with self.assertRaises(urllib.error.HTTPError) as context:
                    self.request_json(
                        "/api/gpio", method="PUT", payload={"value": value}
                    )
                self.assertEqual(context.exception.code, 400)

    def test_rejects_unsupported_rotation(self):
        with self.assertRaises(urllib.error.HTTPError) as context:
            self.request_json(
                "/api/rotation", method="PUT", payload={"rotation": 45}
            )

        self.assertEqual(context.exception.code, 400)

    def test_rejects_non_integer_rotation(self):
        for rotation in (False, 90.0, "90"):
            with self.subTest(rotation=rotation):
                with self.assertRaises(urllib.error.HTTPError) as context:
                    self.request_json(
                        "/api/rotation",
                        method="PUT",
                        payload={"rotation": rotation},
                    )
                self.assertEqual(context.exception.code, 400)

    def test_rejects_invalid_rotation_json(self):
        for data in (b"{", b"[]"):
            with self.subTest(data=data):
                request = urllib.request.Request(
                    self.base_url + "/api/rotation",
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="PUT",
                )
                with self.assertRaises(urllib.error.HTTPError) as context:
                    urllib.request.urlopen(request)
                self.assertEqual(context.exception.code, 400)

    def test_rejects_unsupported_state(self):
        with self.assertRaises(urllib.error.HTTPError) as context:
            self.request_json(
                "/api/state", method="PUT", payload={"state": "unknown"}
            )

        self.assertEqual(context.exception.code, 400)

    def test_rejects_malformed_json(self):
        request = urllib.request.Request(
            self.base_url + "/api/state",
            data=b"{",
            headers={"Content-Type": "application/json"},
            method="PUT",
        )

        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request)

        self.assertEqual(context.exception.code, 400)

    def test_rejects_non_object_json(self):
        request = urllib.request.Request(
            self.base_url + "/api/state",
            data=b"[]",
            headers={"Content-Type": "application/json"},
            method="PUT",
        )

        with self.assertRaises(urllib.error.HTTPError) as context:
            urllib.request.urlopen(request)

        self.assertEqual(context.exception.code, 400)


if __name__ == "__main__":
    unittest.main()