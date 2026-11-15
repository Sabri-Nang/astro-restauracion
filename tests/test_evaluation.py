"""Valida escala, casos conocidos y trazabilidad de métricas sin inferencia."""

import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image

from src.evaluation import evaluate_sweep, reference_metrics
from src.experiment import file_hash, prepare_experiment, restore_experiment, save_json


class ReferenceMetricsTests(unittest.TestCase):
    def test_identity_has_unit_ssim_and_serializable_infinite_psnr(self):
        image = Image.new("RGB", (32, 32), (80, 120, 160))
        score = reference_metrics(image, image.copy())
        self.assertEqual(score["mse_rgb_normalizado"], 0)
        self.assertEqual(score["ssim_rgb"], 1)
        self.assertTrue(score["psnr_infinito"])
        self.assertIsNone(score["psnr_db"])
        json.dumps(score, allow_nan=False)

    def test_one_level_error_uses_fixed_rgb_range(self):
        reference = Image.new("RGB", (32, 32), (128, 128, 128))
        candidate = Image.new("RGB", (32, 32), (129, 129, 129))
        score = reference_metrics(reference, candidate)
        self.assertAlmostEqual(score["mse_rgb_normalizado"], 1 / 255**2)
        self.assertAlmostEqual(score["psnr_db"], 20 * math.log10(255))
        self.assertLess(score["ssim_rgb"], 1)
        self.assertFalse(score["psnr_infinito"])

    def test_incompatible_images_and_too_small_windows_are_rejected(self):
        reference = Image.new("RGB", (32, 32))
        for candidate in (Image.new("L", (32, 32)), Image.new("RGB", (64, 32))):
            with self.assertRaises(ValueError):
                reference_metrics(reference, candidate)
        with self.assertRaisesRegex(ValueError, "11 píxeles"):
            reference_metrics(Image.new("RGB", (8, 8)), Image.new("RGB", (8, 8)))


class SweepEvaluationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        source = self.folder / "fuente.png"
        Image.new("RGB", (128, 96), (100, 120, 140)).save(source)
        self.sweep = self.folder / "barrido"
        prepare_experiment(source, self.sweep)
        with Image.open(self.sweep / "entrada_ruidosa.png") as image:
            noisy = image.copy()
        with Image.open(self.sweep / "referencia_preparada.png") as image:
            reference = image.copy()
        self.case = self.sweep / "intensidad_0.10"
        with patch("src.experiment.run_diffusion", return_value=(
            noisy, reference, {"sha256_entrada": file_hash(self.sweep / "entrada_ruidosa.png")}
        )):
            report = restore_experiment(self.sweep, self.case)
        for name in ("referencia_preparada.png", "entrada_ruidosa.png"):
            (self.case / name).write_bytes((self.sweep / name).read_bytes())
        self.record = {"tipo": "barrido_intensidades_gaussiano", "resultados": [
            {"estado": "correcto", "carpeta": self.case.name, "intensidad": 0.1,
             "sha256_salida": report["sha256_salida"]},
            {"estado": "bloqueada_filtro_seguridad", "intensidad": 0.25},
        ]}
        save_json(self.sweep / "barrido.json", self.record)
        self.output = self.folder / "evaluacion"

    def test_evaluation_keeps_baseline_skips_blocked_and_preserves_sources(self):
        before = file_hash(self.sweep / "barrido.json")
        with patch("src.experiment.run_diffusion") as model:
            result = evaluate_sweep(self.sweep, self.output)
            model.assert_not_called()
        self.assertEqual(len(result["resultados"]), 2)
        self.assertEqual(result["resultados"][0]["imagen"], "Entrada ruidosa")
        self.assertEqual(result["resultados"][1]["ssim_rgb"], 1)
        self.assertEqual(result["casos_sin_metricas"][0]["intensidad"], 0.25)
        self.assertEqual(file_hash(self.sweep / "barrido.json"), before)
        json.loads((self.output / "evaluacion.json").read_text(encoding="utf-8"))
        self.assertTrue((self.output / "metricas.csv").is_file())
        with self.assertRaisesRegex(ValueError, "ya existe"):
            evaluate_sweep(self.sweep, self.output)

    def test_modified_reference_is_rejected_before_creating_report(self):
        Image.new("RGB", (128, 96)).save(self.sweep / "referencia_preparada.png")
        with self.assertRaisesRegex(ValueError, "cambió"):
            evaluate_sweep(self.sweep, self.output)
        self.assertFalse(self.output.exists())

    def test_modified_output_is_rejected_before_creating_report(self):
        Image.new("RGB", (128, 96)).save(self.case / "salida.png")
        with self.assertRaisesRegex(ValueError, "cambió"):
            evaluate_sweep(self.sweep, self.output)
        self.assertFalse(self.output.exists())

    def test_different_case_reference_is_rejected(self):
        Image.new("RGB", (128, 96)).save(self.case / "referencia_preparada.png")
        with self.assertRaisesRegex(ValueError, "difiere"):
            evaluate_sweep(self.sweep, self.output)
        self.assertFalse(self.output.exists())

    def test_path_outside_sweep_is_rejected(self):
        self.record["resultados"][0]["carpeta"] = "../otro_ensayo"
        save_json(self.sweep / "barrido.json", self.record)
        with self.assertRaisesRegex(ValueError, "dentro del barrido"):
            evaluate_sweep(self.sweep, self.output)


if __name__ == "__main__":
    unittest.main()
