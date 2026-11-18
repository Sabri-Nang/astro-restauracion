"""Pruebas de comparación con valores conocidos, sin modelos ni descargas."""

import unittest
from unittest.mock import patch

from PIL import Image

from src.honesty import difference_map, highlight_changes


class DifferenceMapTests(unittest.TestCase):
    def test_highlight_only_marks_changed_pixels_without_modifying_inputs(self):
        before = Image.new("RGB", (20, 10), (10, 20, 30))
        after = before.copy()
        for x in range(10, 20):
            for y in range(10):
                after.putpixel((x, y), (110, 120, 130))
        before_bytes, after_bytes = before.tobytes(), after.tobytes()
        highlighted = highlight_changes(before, after)
        self.assertEqual(highlighted.getpixel((0, 0)), after.getpixel((0, 0)))
        self.assertEqual(highlighted.getpixel((15, 5)), (197, 154, 52))
        self.assertEqual((before.tobytes(), after.tobytes()), (before_bytes, after_bytes))

    def test_no_highlight_is_not_a_claim_of_authenticity(self):
        image = Image.new("RGB", (2, 1), (10, 20, 30))
        self.assertEqual(highlight_changes(image, image.copy()).tobytes(), image.tobytes())
        with self.assertRaises(ValueError):
            highlight_changes(image, Image.new("RGB", (3, 2)))

    def test_identical_images_are_black(self):
        image = Image.new("RGB", (8, 8), (12, 80, 200))
        result = difference_map(image, image.copy())
        self.assertEqual(result.mode, "L")
        self.assertEqual(result.size, image.size)
        self.assertEqual(result.getextrema(), (0, 0))

    def test_extremes_do_not_overflow_and_are_symmetric(self):
        black = Image.new("RGB", (1, 1), (0, 0, 0))
        white = Image.new("RGB", (1, 1), (255, 255, 255))
        self.assertEqual(difference_map(white, black).getpixel((0, 0)), 255)
        self.assertEqual(difference_map(black, white).getpixel((0, 0)), 255)

    def test_channels_are_averaged_without_rescaling_or_mutation(self):
        before = Image.new("RGB", (2, 1), (100, 100, 100))
        after = before.copy()
        after.putpixel((0, 0), (70, 160, 100))
        result = difference_map(before, after)
        self.assertEqual([result.getpixel((x, 0)) for x in range(2)], [30, 0])
        self.assertEqual(before.getpixel((0, 0)), (100, 100, 100))
        self.assertEqual(after.getpixel((0, 0)), (70, 160, 100))

    def test_incompatible_inputs_are_rejected(self):
        rgb = Image.new("RGB", (2, 2))
        with self.assertRaisesRegex(ValueError, "dimensiones"):
            difference_map(rgb, Image.new("RGB", (3, 2)))
        for mode in ("L", "RGBA", "I;16"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "RGB"):
                    difference_map(rgb, Image.new(mode, (2, 2)))
                with self.assertRaisesRegex(ValueError, "RGB"):
                    difference_map(Image.new(mode, (2, 2)), rgb)

    def test_interface_returns_comparison_and_map_without_inference(self):
        import app

        before = Image.new("RGB", (64, 64), (100, 100, 100))
        after = Image.new("RGB", (64, 64), (70, 160, 100))
        metadata = {"tipo": "prueba_simulada"}
        with patch.object(app, 'selected_engine', return_value='sd_tile'), patch.object(app, "run_diffusion", return_value=(before, after, metadata)):
            result = app.process_image("entrada.png", 0.2, 10, 42, 256)
        self.assertEqual(len(result), 5)
        self.assertEqual(result[2], (before, after))
        self.assertEqual(result[3].getextrema(), (30, 30))
        self.assertIs(result[4], metadata)
        interface = app.create_app()
        outputs = [component for component in interface.blocks.values()
                   if isinstance(component, app.gr.ImageSlider)]
        self.assertEqual(len(outputs), 1)


if __name__ == "__main__":
    unittest.main()
