"""
Tests for Timeline Panel
"""

import unittest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))

from ui.timeline_panel import TimelinePanel


class TestTimelinePanel(unittest.TestCase):
    """Tests for TimelinePanel static helpers"""

    def test_format_time(self):
        """Test time formatting"""
        self.assertEqual(TimelinePanel._format_time(0), "00:00:00")
        self.assertEqual(TimelinePanel._format_time(30), "00:00:30")
        self.assertEqual(TimelinePanel._format_time(90), "00:01:30")
        self.assertEqual(TimelinePanel._format_time(3665), "01:01:05")
        self.assertEqual(TimelinePanel._format_time(7384), "02:03:04")

    def test_parse_time(self):
        """Test time parsing"""
        # HH:MM:SS format
        self.assertEqual(TimelinePanel._parse_time("00:00:00"), 0)
        self.assertEqual(TimelinePanel._parse_time("00:00:30"), 30)
        self.assertEqual(TimelinePanel._parse_time("00:01:30"), 90)
        self.assertEqual(TimelinePanel._parse_time("01:01:05"), 3665)

        # MM:SS format
        self.assertEqual(TimelinePanel._parse_time("01:30"), 90)
        self.assertEqual(TimelinePanel._parse_time("10:45"), 645)

        # SS format
        self.assertEqual(TimelinePanel._parse_time("30"), 30)
        self.assertEqual(TimelinePanel._parse_time("120"), 120)

    def test_parse_time_invalid(self):
        """Test invalid time format"""
        with self.assertRaises(ValueError):
            TimelinePanel._parse_time("invalid")

        with self.assertRaises(ValueError):
            TimelinePanel._parse_time("1:2:3:4")

    def test_describe_operation(self):
        """Test operation description generation"""
        self.assertEqual(
            TimelinePanel._describe_operation({"type": "trim", "start": 10, "end": 120}),
            "Trim 00:00:10 -> 00:02:00",
        )
        self.assertEqual(
            TimelinePanel._describe_operation({"type": "concat_intro", "path": "/tmp/intro.mp4"}),
            "Add Intro: intro.mp4",
        )
        self.assertEqual(
            TimelinePanel._describe_operation({"type": "concat_outro", "path": "/tmp/outro.mp4"}),
            "Add Outro: outro.mp4",
        )


if __name__ == "__main__":
    unittest.main()
