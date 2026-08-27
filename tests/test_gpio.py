import os
import unittest
from unittest.mock import call, patch

import gpio


class GpioFallbackTests(unittest.TestCase):
    def setUp(self):
        gpio._available = None
        gpio._level = gpio.LOW

    @patch.object(gpio.os.path, "isdir", return_value=False)
    def test_setup_falls_back_when_sysfs_missing(self, isdir):
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


class GpioSysfsTests(unittest.TestCase):
    def setUp(self):
        gpio._available = None
        gpio._level = gpio.LOW

    @patch.object(gpio.os.path, "isdir", side_effect=lambda p: p != gpio._PIN_DIR)
    @patch.object(gpio.os, "access", return_value=True)
    @patch.object(gpio, "_write")
    def test_setup_exports_sets_output_and_low(self, write, access, isdir):
        self.assertTrue(gpio.setup())

        write.assert_has_calls(
            [
                call(gpio._EXPORT_PATH, gpio.GPIO_PIN),
                call(os.path.join(gpio._PIN_DIR, "direction"), "out"),
                call(os.path.join(gpio._PIN_DIR, "value"), gpio.LOW),
            ]
        )

    @patch.object(gpio, "_write")
    def test_set_level_writes_value(self, write):
        gpio._available = True

        gpio.set_level(gpio.HIGH)

        write.assert_called_once_with(
            os.path.join(gpio._PIN_DIR, "value"), gpio.HIGH
        )

    @patch.object(gpio, "_write")
    def test_cleanup_unexports_pin(self, write):
        gpio._available = True

        gpio.cleanup()

        write.assert_called_once_with(gpio._UNEXPORT_PATH, gpio.GPIO_PIN)
        self.assertIsNone(gpio._available)


if __name__ == "__main__":
    unittest.main()
