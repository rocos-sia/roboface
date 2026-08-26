from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingManifestTests(unittest.TestCase):
    def test_spec_bundles_runtime_assets(self):
        path = ROOT / "roboface.spec"
        self.assertTrue(path.is_file(), "roboface.spec must exist")
        spec = path.read_text(encoding="utf-8")

        for required in (
            "index.html",
            "RoboFace.lottie",
            "vendor/dotlottie-wc.js",
            "vendor/dotlottie-player.wasm",
            "vendor/LICENSE.dotlottie-wc.txt",
        ):
            with self.subTest(required=required):
                self.assertIn(required, spec)
        self.assertIn('name="roboface-linux-arm64"', spec)

    def test_build_dependency_is_pinned(self):
        path = ROOT / "requirements-build.txt"
        self.assertTrue(path.is_file(), "requirements-build.txt must exist")
        self.assertEqual(
            path.read_text(encoding="utf-8").splitlines(),
            ["pyinstaller==6.15.0"],
        )

    def test_native_build_script_checks_platform_and_builds(self):
        path = ROOT / "build-raspberry-pi.sh"
        self.assertTrue(path.is_file(), "build-raspberry-pi.sh must exist")
        script = path.read_text(encoding="utf-8")

        for required in (
            "set -euo pipefail",
            '$(uname -s)',
            '$(uname -m)',
            "aarch64",
            ".venv-build",
            "requirements-build.txt",
            "python -m unittest discover -s tests -v",
            "pyinstaller --clean --noconfirm roboface.spec",
            "dist/roboface-linux-arm64",
            "sha256sum",
        ):
            with self.subTest(required=required):
                self.assertIn(required, script)

    def test_autostart_installer_uses_xdg_user_paths(self):
        installer_path = ROOT / "install-autostart.sh"
        test_path = ROOT / "tests" / "test_install_autostart.sh"
        self.assertTrue(installer_path.is_file(), "autostart installer must exist")
        self.assertTrue(test_path.is_file(), "autostart integration test must exist")
        installer = installer_path.read_text(encoding="utf-8")

        for required in (
            "set -euo pipefail",
            "--binary",
            "--rotation",
            "--uninstall",
            '$HOME/.local/bin',
            '$HOME/.config/autostart',
            'Exec="$escaped_binary" --rotation $rotation',
            "Terminal=false",
            "X-GNOME-Autostart-enabled=true",
            "mktemp",
            "mv -f",
        ):
            with self.subTest(required=required):
                self.assertIn(required, installer)


class DeliveryDocumentationTests(unittest.TestCase):
    def test_ci_builds_in_arm64_bookworm_and_uploads_executable(self):
        path = ROOT / ".github" / "workflows" / "build-raspberry-pi.yml"
        self.assertTrue(path.is_file(), "Raspberry Pi build workflow must exist")
        workflow = path.read_text(encoding="utf-8")

        for required in (
            "workflow_dispatch:",
            "ubuntu-24.04-arm",
            "python:3.11-bookworm",
            "./build-raspberry-pi.sh",
            "actions/upload-artifact@v4",
            "dist/roboface-linux-arm64",
            "install-autostart.sh",
        ):
            with self.subTest(required=required):
                self.assertIn(required, workflow)

    def test_readme_documents_installation_runtime_and_api(self):
        path = ROOT / "README.md"
        self.assertTrue(path.is_file(), "README.md must exist")
        readme = path.read_text(encoding="utf-8")

        for required in (
            "Raspberry Pi OS 64-bit",
            "sudo apt install -y chromium",
            "./roboface-linux-arm64",
            "./build-raspberry-pi.sh",
            "GET /api/state",
            "PUT /api/state",
            "GET /api/states",
            '"state":"daze"',
            "/tmp/roboface.log",
            "离线",
            "sudo raspi-config",
            "install-autostart.sh --binary",
            "--uninstall",
            "sudo reboot",
            "~/.config/autostart/roboface.desktop",
        ):
            with self.subTest(required=required):
                self.assertIn(required, readme)


if __name__ == "__main__":
    unittest.main()