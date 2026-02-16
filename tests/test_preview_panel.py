"""
Tests for Preview Panel
"""

import unittest
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent / "src"))

from ui.preview_panel import PreviewPanel


class TestPreviewPanel(unittest.TestCase):
    """Тесты для PreviewPanel"""
    
    def test_format_size(self):
        """Тест форматирования размера файла"""
        # Bytes
        self.assertEqual(PreviewPanel._format_size(0), "0.0 B")
        self.assertEqual(PreviewPanel._format_size(500), "500.0 B")
        
        # KB
        self.assertEqual(PreviewPanel._format_size(1024), "1.0 KB")
        self.assertEqual(PreviewPanel._format_size(2560), "2.5 KB")
        
        # MB
        self.assertEqual(PreviewPanel._format_size(1024 * 1024), "1.0 MB")
        self.assertEqual(PreviewPanel._format_size(5 * 1024 * 1024), "5.0 MB")
        
        # GB
        self.assertEqual(PreviewPanel._format_size(1024 * 1024 * 1024), "1.0 GB")
        self.assertEqual(PreviewPanel._format_size(2.5 * 1024 * 1024 * 1024), "2.5 GB")
    
    def test_format_duration(self):
        """Тест форматирования длительности"""
        # Секунды
        self.assertEqual(PreviewPanel._format_duration(30), "0:30")
        self.assertEqual(PreviewPanel._format_duration(59), "0:59")
        
        # Минуты
        self.assertEqual(PreviewPanel._format_duration(60), "1:00")
        self.assertEqual(PreviewPanel._format_duration(90), "1:30")
        self.assertEqual(PreviewPanel._format_duration(599), "9:59")
        
        # Часы
        self.assertEqual(PreviewPanel._format_duration(3600), "1:00:00")
        self.assertEqual(PreviewPanel._format_duration(3665), "1:01:05")
        self.assertEqual(PreviewPanel._format_duration(7384), "2:03:04")
    
    def test_format_bitrate(self):
        """Тест форматирования битрейта"""
        # N/A
        self.assertEqual(PreviewPanel._format_bitrate(0), "N/A")
        
        # kbps
        self.assertEqual(PreviewPanel._format_bitrate(128000), "128 kbps")
        self.assertEqual(PreviewPanel._format_bitrate(500000), "500 kbps")
        
        # Mbps
        self.assertEqual(PreviewPanel._format_bitrate(1000000), "1.0 Mbps")
        self.assertEqual(PreviewPanel._format_bitrate(5500000), "5.5 Mbps")
    
    def test_format_fps(self):
        """Тест форматирования FPS"""
        # Простой формат
        self.assertEqual(PreviewPanel._format_fps("30"), "30")
        
        # Формат с дробью
        self.assertEqual(PreviewPanel._format_fps("30/1"), "30.00 fps")
        self.assertEqual(PreviewPanel._format_fps("60000/1001"), "59.94 fps")
        self.assertEqual(PreviewPanel._format_fps("24000/1001"), "23.98 fps")
        
        # Невалидный формат
        self.assertEqual(PreviewPanel._format_fps("invalid"), "invalid")


if __name__ == "__main__":
    unittest.main()
