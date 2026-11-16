"""Rechaza conversiones de profundidad silenciosas sin cargar modelos."""

from pathlib import Path
import struct
import tempfile
import unittest
import zlib

from PIL import Image
from src.diffusion import prepare_image


class ImageFormatTests(unittest.TestCase):
    def test_16_bit_tiff_has_actionable_message(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "foto.tif"
            Image.new("I;16", (64, 64)).save(path)
            source = path.read_bytes()
            with self.assertRaisesRegex(ValueError, "Conservá el original"):
                prepare_image(path)
            self.assertEqual(path.read_bytes(), source)

    def test_rgb_16_bit_png_is_rejected_even_when_pillow_reports_rgb(self):
        def chunk(kind, data):
            return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data))
        header = struct.pack('!IIBBBBB', 64, 64, 16, 2, 0, 0, 0)
        pixels = (b'\x00' + b'\x00\xff' * 64 * 3) * 64
        png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(pixels)) + chunk(b'IEND', b'')
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'foto.png'
            path.write_bytes(png)
            with Image.open(path) as image:
                self.assertEqual(image.mode, 'RGB')
            with self.assertRaisesRegex(ValueError, 'niveles de color'):
                prepare_image(path)
