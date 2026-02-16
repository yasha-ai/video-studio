"""
Tests for Timeline Panel
"""

import unittest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))

from ui.timeline_panel import TimelinePanel


class TestTimelinePanel(unittest.TestCase):
    """Тесты для TimelinePanel"""
    
    def test_format_time(self):
        """Тест форматирования времени"""
        panel = TimelinePanel(None)
        
        # Тестовые case
        self.assertEqual(panel._format_time(0), "00:00:00")
        self.assertEqual(panel._format_time(30), "00:00:30")
        self.assertEqual(panel._format_time(90), "00:01:30")
        self.assertEqual(panel._format_time(3665), "01:01:05")
        self.assertEqual(panel._format_time(7384), "02:03:04")
    
    def test_parse_time(self):
        """Тест парсинга времени"""
        panel = TimelinePanel(None)
        
        # HH:MM:SS format
        self.assertEqual(panel._parse_time("00:00:00"), 0)
        self.assertEqual(panel._parse_time("00:00:30"), 30)
        self.assertEqual(panel._parse_time("00:01:30"), 90)
        self.assertEqual(panel._parse_time("01:01:05"), 3665)
        
        # MM:SS format
        self.assertEqual(panel._parse_time("01:30"), 90)
        self.assertEqual(panel._parse_time("10:45"), 645)
        
        # SS format
        self.assertEqual(panel._parse_time("30"), 30)
        self.assertEqual(panel._parse_time("120"), 120)
    
    def test_parse_time_invalid(self):
        """Тест парсинга неверного формата"""
        panel = TimelinePanel(None)
        
        with self.assertRaises(ValueError):
            panel._parse_time("invalid")
        
        with self.assertRaises(ValueError):
            panel._parse_time("1:2:3:4")


if __name__ == "__main__":
    unittest.main()
