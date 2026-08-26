import unittest
from unittest.mock import MagicMock, patch

import launcher

DEFAULT_PROCESS = object()


class BrowserDiscoveryTests(unittest.TestCase):
    @patch("launcher.sys.platform", "linux")
    @patch("shutil.which")
    def test_linux_prefers_chromium(self, which):
        which.side_effect = (
            lambda name: "/usr/bin/chromium" if name == "chromium" else None
        )

        self.assertEqual(launcher.find_browser(), "/usr/bin/chromium")
        self.assertEqual(which.call_args_list[0].args, ("chromium",))

    @patch("launcher.sys.platform", "linux")
    @patch("shutil.which", return_value=None)
    def test_linux_returns_none_without_chromium(self, which):
        self.assertIsNone(launcher.find_browser())


class PortSelectionTests(unittest.TestCase):
    @patch("launcher.socket.socket")
    def test_uses_next_port_when_start_port_is_occupied(self, socket_factory):
        test_socket = socket_factory.return_value.__enter__.return_value
        test_socket.bind.side_effect = [OSError, None]

        self.assertEqual(launcher.find_free_port(start=8000, tries=2), 8001)

    @patch("launcher.socket.socket")
    def test_raises_when_all_candidate_ports_are_occupied(self, socket_factory):
        test_socket = socket_factory.return_value.__enter__.return_value
        test_socket.bind.side_effect = OSError

        with self.assertRaisesRegex(RuntimeError, "没有可用的端口"):
            launcher.find_free_port(start=8000, tries=2)

        self.assertEqual(test_socket.bind.call_count, 2)


class KioskCommandTests(unittest.TestCase):
    def test_build_browser_args_enables_kiosk_with_isolated_profile(self):
        self.assertTrue(hasattr(launcher, "build_browser_args"))

        args = launcher.build_browser_args(
            "/usr/bin/chromium",
            "http://localhost:8000/",
            "/tmp/roboface-browser-test",
        )

        self.assertEqual(args[0], "/usr/bin/chromium")
        self.assertIn("--kiosk", args)
        self.assertIn("--no-first-run", args)
        self.assertIn("--no-default-browser-check", args)
        self.assertIn("--disable-session-crashed-bubble", args)
        self.assertIn("--user-data-dir=/tmp/roboface-browser-test", args)
        self.assertEqual(args[-1], "http://localhost:8000/")


class RotationArgumentTests(unittest.TestCase):
    def test_rotation_defaults_to_zero(self):
        self.assertTrue(hasattr(launcher, "parse_args"))
        self.assertEqual(launcher.parse_args([]).rotation, 0)

    def test_accepts_supported_rotations(self):
        self.assertTrue(hasattr(launcher, "parse_args"))
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                args = launcher.parse_args(["--rotation", str(rotation)])
                self.assertEqual(args.rotation, rotation)

    def test_rejects_unsupported_rotation(self):
        self.assertTrue(hasattr(launcher, "parse_args"))
        with self.assertRaises(SystemExit):
            launcher.parse_args(["--rotation", "45"])


class LauncherLifecycleTests(unittest.TestCase):
    def run_main(
        self, browser="/usr/bin/chromium", process=DEFAULT_PROCESS, rotation=0
    ):
        httpd = MagicMock()
        if process is DEFAULT_PROCESS:
            process = MagicMock()
            process.wait.return_value = 0
        patches = (
            patch("launcher.find_free_port", return_value=8000),
            patch("launcher.ThreadingHTTPServer", return_value=httpd),
            patch("launcher.threading.Thread"),
            patch("launcher.threading.Event"),
            patch("launcher.wait_until_ready", return_value=True),
            patch("launcher.find_browser", return_value=browser),
            patch("launcher.tempfile.mkdtemp", return_value="/tmp/roboface-profile"),
            patch("launcher.open_fullscreen", return_value=process),
            patch("launcher.shutil.rmtree"),
            patch("launcher.log"),
        )
        entered = [item.start() for item in patches]
        try:
            result = launcher.main(rotation)
        finally:
            for item in reversed(patches):
                item.stop()
        return result, httpd, process, entered

    def test_main_waits_for_browser_then_stops_server(self):
        result, httpd, process, entered = self.run_main()

        self.assertEqual(result, 0)
        process.wait.assert_called_once_with()
        httpd.shutdown.assert_called_once_with()
        httpd.server_close.assert_called_once_with()
        entered[8].assert_called_once_with("/tmp/roboface-profile", ignore_errors=True)

    @patch("launcher.server.set_rotation")
    def test_main_sets_initial_rotation(self, set_rotation):
        result, _, _, _ = self.run_main(rotation=90)

        self.assertEqual(result, 0)
        set_rotation.assert_called_once_with(90)

    def test_main_returns_error_when_chromium_is_missing(self):
        result, httpd, _, _ = self.run_main(browser=None)

        self.assertEqual(result, 1)
        httpd.shutdown.assert_called_once_with()
        httpd.server_close.assert_called_once_with()

    def test_main_returns_error_when_chromium_fails_to_start(self):
        result, httpd, _, _ = self.run_main(process=None)

        self.assertEqual(result, 1)
        httpd.shutdown.assert_called_once_with()
        httpd.server_close.assert_called_once_with()

    def test_main_returns_error_when_chromium_exits_nonzero(self):
        process = MagicMock()
        process.wait.return_value = 2

        result, httpd, _, _ = self.run_main(process=process)

        self.assertEqual(result, 1)
        httpd.shutdown.assert_called_once_with()
        httpd.server_close.assert_called_once_with()

    def test_keyboard_interrupt_terminates_chromium(self):
        process = MagicMock()
        process.wait.side_effect = [KeyboardInterrupt, 0]
        process.poll.return_value = None

        result, httpd, _, _ = self.run_main(process=process)

        self.assertEqual(result, 0)
        process.terminate.assert_called_once_with()
        process.wait.assert_called_with(timeout=5)
        httpd.shutdown.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()