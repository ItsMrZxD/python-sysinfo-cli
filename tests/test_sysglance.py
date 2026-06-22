"""Unit tests for sysglance. Run with: python -m unittest"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout

# Make the top-level sysglance module importable when run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import sysglance  # noqa: E402


class HumanBytesTests(unittest.TestCase):
    def test_bytes_below_one_kb(self):
        self.assertEqual(sysglance.human_bytes(0), "0 B")
        self.assertEqual(sysglance.human_bytes(1023), "1023 B")

    def test_scales_up_units(self):
        self.assertEqual(sysglance.human_bytes(1024), "1.0 KB")
        self.assertEqual(sysglance.human_bytes(1536), "1.5 KB")
        self.assertEqual(sysglance.human_bytes(1024 ** 3), "1.0 GB")


class UptimeTests(unittest.TestCase):
    def test_none_is_na(self):
        self.assertEqual(sysglance.fmt_uptime(None), "n/a")

    def test_formatting(self):
        self.assertEqual(sysglance.fmt_uptime(0), "0m")
        self.assertEqual(sysglance.fmt_uptime(60), "1m")
        self.assertEqual(sysglance.fmt_uptime(3600), "1h 0m")
        self.assertEqual(sysglance.fmt_uptime(90061), "1d 1h 1m")


class CollectTests(unittest.TestCase):
    def test_has_expected_keys(self):
        data = sysglance.collect()
        for key in (
            "user", "hostname", "os", "arch", "python",
            "cpu", "memory", "disk", "uptime_seconds",
            "network", "battery", "temperature_c",
        ):
            self.assertIn(key, data)

    def test_disk_is_populated(self):
        disk = sysglance.collect()["disk"]
        self.assertGreater(disk["total"], 0)
        self.assertEqual(disk["used"] + disk["free"] <= disk["total"] + 1, True)

    def test_cpu_block_shape(self):
        cpu = sysglance.collect()["cpu"]
        self.assertIn("model", cpu)
        self.assertIn("cores", cpu)


class OutputTests(unittest.TestCase):
    def test_json_output_is_valid(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = sysglance.main(["--json"])
        self.assertEqual(rc, 0)
        parsed = json.loads(buf.getvalue())
        self.assertIsInstance(parsed, dict)
        self.assertIn("os", parsed)

    def test_no_color_has_no_escape_codes(self):
        rows = sysglance.human_rows(sysglance.collect())
        buf = io.StringIO()
        with redirect_stdout(buf):
            sysglance.render(rows, color=False)
        self.assertNotIn("\033", buf.getvalue())

    def test_color_emits_escape_codes(self):
        rows = sysglance.human_rows(sysglance.collect())
        buf = io.StringIO()
        with redirect_stdout(buf):
            sysglance.render(rows, color=True)
        self.assertIn("\033", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
