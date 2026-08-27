import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import gpio


class GpioFallbackTests(unittest.TestCase):
    def setUp(self):
        gpio._available = None
        gpio._level = gpio.LOW
        gpio._request = None
        gpio._line_offset = None

    def test_setup_falls_back_when_gpiod_is_missing(self):
        with patch.object(gpio, "gpiod", None):
            self.assertFalse(gpio.setup())
        self.assertIs(gpio._available, False)

    def test_set_level_and_get_level_round_trip_in_memory_mode(self):
        gpio._available = False

        gpio.set_level(gpio.HIGH)
        self.assertEqual(gpio.get_level(), gpio.HIGH)

        gpio.set_level(gpio.LOW)
        self.assertEqual(gpio.get_level(), gpio.LOW)

    def test_set_level_rejects_invalid_values(self):
        gpio._available = False
        for value in (2, -1, "1", 1.0, True, None):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    gpio.set_level(value)


class GpioGpiodTests(unittest.TestCase):
    def setUp(self):
        gpio._available = None
        gpio._level = gpio.LOW
        gpio._request = None
        gpio._line_offset = None
        self.binding = MagicMock()
        self.binding.line.Direction.OUTPUT = object()
        self.binding.line.Value.INACTIVE = object()
        self.binding.line.Value.ACTIVE = object()
        self.request = self.binding.request_lines.return_value

    def test_setup_finds_named_line_and_requests_output_low(self):
        self.binding.is_gpiochip_device.side_effect = (
            lambda path: path == "/dev/gpiochip4"
        )
        chip = self.binding.Chip.return_value.__enter__.return_value
        chip.line_offset_from_id.return_value = gpio.GPIO_PIN
        entries = [
            SimpleNamespace(path="/dev/not-a-chip"),
            SimpleNamespace(path="/dev/gpiochip4"),
        ]

        with patch.object(gpio, "gpiod", self.binding):
            with patch.object(gpio.os, "scandir", return_value=entries):
                self.assertTrue(gpio.setup())

        self.binding.request_lines.assert_called_once_with(
            "/dev/gpiochip4",
            consumer="roboface",
            config={gpio.GPIO_PIN: self.binding.LineSettings.return_value},
        )
        self.binding.LineSettings.assert_called_once_with(
            direction=self.binding.line.Direction.OUTPUT,
            output_value=self.binding.line.Value.INACTIVE,
        )

    def test_setup_falls_back_when_named_line_is_missing(self):
        self.binding.is_gpiochip_device.return_value = True
        chip = self.binding.Chip.return_value.__enter__.return_value
        chip.line_offset_from_id.side_effect = OSError("not found")
        entries = [SimpleNamespace(path="/dev/gpiochip0")]

        with patch.object(gpio, "gpiod", self.binding):
            with patch.object(gpio.os, "scandir", return_value=entries):
                self.assertFalse(gpio.setup())

        self.binding.request_lines.assert_not_called()

    def test_setup_falls_back_when_gpio_devices_are_not_accessible(self):
        with patch.object(gpio, "gpiod", self.binding):
            with patch.object(
                gpio.os, "scandir", side_effect=PermissionError("denied")
            ):
                self.assertFalse(gpio.setup())

    def test_set_level_maps_high_to_active(self):
        gpio._available = True
        gpio._request = self.request
        gpio._line_offset = gpio.GPIO_PIN

        with patch.object(gpio, "gpiod", self.binding):
            gpio.set_level(gpio.HIGH)

        self.request.set_value.assert_called_once_with(
            gpio.GPIO_PIN, self.binding.line.Value.ACTIVE
        )

    def test_write_error_falls_back_and_tracks_requested_level(self):
        self.request.set_value.side_effect = OSError("busy")
        gpio._available = True
        gpio._request = self.request
        gpio._line_offset = gpio.GPIO_PIN

        with patch.object(gpio, "gpiod", self.binding):
            self.assertEqual(gpio.set_level(gpio.HIGH), gpio.HIGH)

        self.assertIs(gpio._available, False)
        self.assertEqual(gpio.get_level(), gpio.HIGH)
        self.request.release.assert_called_once_with()

    def test_cleanup_drives_low_and_releases_request(self):
        gpio._available = True
        gpio._level = gpio.HIGH
        gpio._request = self.request
        gpio._line_offset = gpio.GPIO_PIN

        with patch.object(gpio, "gpiod", self.binding):
            gpio.cleanup()

        self.request.set_value.assert_called_once_with(
            gpio.GPIO_PIN, self.binding.line.Value.INACTIVE
        )
        self.request.release.assert_called_once_with()
        self.assertIsNone(gpio._available)
        self.assertIsNone(gpio._request)
        self.assertIsNone(gpio._line_offset)
        self.assertEqual(gpio.get_level(), gpio.LOW)


if __name__ == "__main__":
    unittest.main()
