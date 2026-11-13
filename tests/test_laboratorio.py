"""Pruebas del laboratorio y sus vistas, sin inferencias ni pesos."""

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

import numpy as np
from PIL import Image

import laboratorio as lab
from src.honesty import amplified_difference


class DifferenceViewTests(unittest.TestCase):
    def test_visual_gain_preserves_absolute_map_and_reports_clipping(self):
        raw = Image.fromarray(np.array([[0, 2, 18]], dtype=np.uint8))
        before = raw.tobytes()
        enhanced, stats = amplified_difference(raw, 16)
        self.assertEqual([enhanced.getpixel((x, 0)) for x in range(3)], [0, 32, 255])
        self.assertEqual(raw.tobytes(), before)
        self.assertEqual(stats["maximo_mapa_absoluto"], 18)
        self.assertAlmostEqual(stats["fraccion_pixeles_recortados_en_vista"], 1 / 3)

    def test_zero_map_remains_zero_and_invalid_gain_is_rejected(self):
        raw = Image.new("L", (8, 8))
        enhanced, stats = amplified_difference(raw, 64)
        self.assertEqual(enhanced.getextrema(), (0, 0))
        self.assertEqual(stats["fraccion_pixeles_mapa_no_cero"], 0)
        for gain in (0, 65, float("nan")):
            with self.subTest(gain=gain), self.assertRaises(ValueError):
                amplified_difference(raw, gain)


class LaboratoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.source = self.folder / "propia.png"
        Image.new("RGB", (128, 96), (128, 128, 128)).save(self.source)

    def preview(self, sigma=0.03):
        return lab.preview_noise(str(self.source), sigma, 123, 256, 16)

    def test_preview_works_with_arbitrary_image_without_diffusion(self):
        with patch.object(lab, "restore_experiment") as restore:
            result = self.preview()
            restore.assert_not_called()
        self.assertEqual(len(result), 13)
        state = result[0]
        self.assertEqual(state["reference"].size, (128, 96))
        self.assertFalse(state["record"]["inferencia_ejecutada"])
        self.assertIsNone(result[4])
        self.assertIsNone(result[11])
        self.assertNotEqual(state["reference"].tobytes(), state["noisy"].tobytes())

    def test_sigma_changes_noise_and_resets_previous_output(self):
        previous = self.preview()[0]
        previous["restored"] = previous["reference"]
        previous["archive"] = "anterior.zip"
        result = self.preview(sigma=0)
        self.assertEqual(result[0]["reference"].tobytes(), result[0]["noisy"].tobytes())
        self.assertIsNone(result[4])
        self.assertIsNone(result[11])

    def test_gain_and_selection_do_not_regenerate_noise(self):
        state = self.preview()[0]
        with patch.object(lab, "add_gaussian_noise") as noise:
            raw, enhanced, stats = lab.show_map(state, lab.NOISE_MAP, 8)
            noise.assert_not_called()
        self.assertEqual(raw.tobytes(), state["maps"][lab.NOISE_MAP].tobytes())
        self.assertEqual(stats["ganancia_solo_visual"], 8)
        self.assertEqual(enhanced.size, raw.size)

    def test_changing_input_before_preview_prevents_inference(self):
        state = self.preview()[0]
        with patch.object(lab, "restore_experiment") as restore:
            with self.assertRaises(lab.gr.Error):
                lab.apply_diffusion(state, str(self.source), 0.05, 123, 256,
                                    0.2, 30, 42, "cuda", "propia", "autora", "propia", 16)
            restore.assert_not_called()

    def test_restoration_preserves_exact_preview_and_downloads_both_phases(self):
        state = self.preview()[0]
        noisy = state["noisy"]
        restored = state["reference"].copy()
        with patch.object(lab, "LAB_OUTPUTS", self.folder / "resultados"), patch(
            "src.experiment.run_diffusion", return_value=(noisy, restored, {"semilla": 42})
        ) as model:
            result = lab.apply_diffusion(state, str(self.source), 0.03, 123, 256,
                                         0.2, 30, 42, "cuda", "propia", "autora", "propia", 16)
        model.assert_called_once()
        self.assertEqual(result[0]["noisy"].tobytes(), noisy.tobytes())
        self.assertEqual(set(result[0]["maps"]), {lab.NOISE_MAP, lab.MODEL_MAP, lab.TARGET_MAP})
        self.assertTrue(result[10]["inferencia_ejecutada"])
        with ZipFile(result[11]) as archive:
            self.assertTrue({"referencia_preparada.png", "entrada_ruidosa.png", "salida.png",
                             "experimento.json", "resultado.json"}.issubset(archive.namelist()))

    def test_clear_and_invalid_input_discard_results(self):
        self.assertIsNone(lab.preview_noise(None, 0.03, 123, 256, 16)[0])
        result = lab.preview_noise(str(self.folder / "ausente.png"), 0.03, 123, 256, 16)
        self.assertIsNone(result[0])
        self.assertIsNone(result[4])
        self.assertIn("No se pudo preparar", result[-1])

    def test_interface_builds_with_automatic_preview_and_explicit_diffusion(self):
        interface = lab.create_lab()
        config = interface.get_config_file()
        self.assertIn("Laboratorio", config["title"])
        self.assertEqual(len(config["dependencies"]), 3)
        self.assertTrue(any(component["type"] == "imageslider" for component in config["components"]))


if __name__ == "__main__":
    unittest.main()
