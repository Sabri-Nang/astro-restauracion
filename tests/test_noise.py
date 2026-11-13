"""Ensayos del ruido sintético y sus registros, sin pesos ni inferencias."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image

from src.experiment import file_hash, prepare_experiment, restore_experiment
from src.noise import add_gaussian_noise


class GaussianNoiseTests(unittest.TestCase):
    def test_zero_sigma_preserves_pixels_and_source(self):
        source = Image.new("RGB", (8, 8), (0, 128, 255))
        original = source.tobytes()
        result, metadata = add_gaussian_noise(source, sigma=0)
        self.assertEqual(result.tobytes(), original)
        self.assertEqual(source.tobytes(), original)
        self.assertEqual(metadata["fraccion_muestras_recortadas_inferior"], 0)

    def test_seed_is_reproducible_and_separate(self):
        image = Image.new("RGB", (64, 64), (128, 128, 128))
        first, _ = add_gaussian_noise(image, seed=123)
        repeated, _ = add_gaussian_noise(image, seed=123)
        other, _ = add_gaussian_noise(image, seed=124)
        self.assertEqual(first.tobytes(), repeated.tobytes())
        self.assertNotEqual(first.tobytes(), other.tobytes())
        self.assertEqual((first.mode, first.size), (image.mode, image.size))

    def test_distribution_before_significant_clipping(self):
        image = Image.new("RGB", (512, 512), (128, 128, 128))
        noisy, metadata = add_gaussian_noise(image, sigma=0.03)
        residual = (np.asarray(noisy, dtype=float) - 128) / 255
        self.assertAlmostEqual(float(residual.mean()), 0, delta=0.0005)
        self.assertAlmostEqual(float(residual.std()), 0.03, delta=0.0005)
        self.assertEqual(metadata["fraccion_muestras_recortadas_inferior"], 0)
        self.assertEqual(metadata["fraccion_muestras_recortadas_superior"], 0)

    def test_clipping_near_black_is_recorded(self):
        noisy, metadata = add_gaussian_noise(Image.new("RGB", (128, 128)), sigma=0.03)
        self.assertGreater(metadata["fraccion_muestras_recortadas_inferior"], 0.45)
        self.assertLess(metadata["fraccion_muestras_recortadas_inferior"], 0.55)
        self.assertEqual(metadata["fraccion_muestras_recortadas_superior"], 0)
        self.assertEqual(np.asarray(noisy).dtype, np.uint8)

    def test_invalid_parameters(self):
        image = Image.new("RGB", (64, 64))
        for sigma in (-0.01, 1.1, float("nan"), float("inf")):
            with self.subTest(sigma=sigma), self.assertRaises(ValueError):
                add_gaussian_noise(image, sigma=sigma)
        for seed in (-1, 2**32, 1.5, True):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                add_gaussian_noise(image, seed=seed)
        with self.assertRaises(ValueError):
            add_gaussian_noise(image.convert("L"))


class GaussianExperimentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.source = self.folder / "fuente.png"
        Image.new("RGB", (128, 96), (128, 128, 128)).save(self.source)
        self.experiment = self.folder / "experimento"
        self.output = self.folder / "difusion"

    def test_preparation_does_not_run_diffusion_or_overwrite(self):
        before = file_hash(self.source)
        with patch("src.experiment.run_diffusion") as model:
            report = prepare_experiment(self.source, self.experiment)
            model.assert_not_called()
        self.assertFalse(report["inferencia_ejecutada"])
        self.assertEqual(report["sha256_original"], before)
        self.assertEqual(file_hash(self.source), before)
        for name, digest in report["archivos_sha256"].items():
            self.assertEqual(file_hash(self.experiment / name), digest)
        with self.assertRaises(FileExistsError):
            prepare_experiment(self.source, self.experiment)

    def test_restoration_uses_saved_noise_and_records_both_seeds(self):
        prepare_experiment(self.source, self.experiment, noise_seed=123)
        with Image.open(self.experiment / "entrada_ruidosa.png") as image:
            noisy = image.copy()
        fake_output = Image.new("RGB", noisy.size, (128, 128, 128))
        with patch("src.experiment.run_diffusion", return_value=(noisy, fake_output, {"semilla": 42})) as model:
            report = restore_experiment(self.experiment, self.output)
        self.assertEqual(model.call_args.args[0], self.experiment / "entrada_ruidosa.png")
        self.assertEqual(model.call_args.kwargs["seed"], 42)
        self.assertEqual(report["experimento"]["ruido"]["semilla_ruido"], 123)
        self.assertTrue(report["difusion"]["ruido_artificial_agregado"])
        self.assertFalse(report["metricas_calculadas"])
        saved = json.loads((self.output / "resultado.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["sha256_salida"], file_hash(self.output / "salida.png"))
        with Image.open(self.output / "diferencias_referencia_salida.png") as residual:
            self.assertEqual(residual.getextrema(), (0, 0))
        with self.assertRaisesRegex(ValueError, "ya existe"):
            restore_experiment(self.experiment, self.output)

    def test_modified_input_is_rejected_before_inference(self):
        prepare_experiment(self.source, self.experiment)
        Image.new("RGB", (128, 96)).save(self.experiment / "entrada_ruidosa.png")
        with patch("src.experiment.run_diffusion") as model:
            with self.assertRaisesRegex(ValueError, "cambió"):
                restore_experiment(self.experiment, self.output)
            model.assert_not_called()

    def test_repreparation_cannot_change_the_evaluation_input(self):
        prepare_experiment(self.source, self.experiment)
        changed = Image.new("RGB", (64, 64))
        with patch("src.experiment.run_diffusion", return_value=(changed, changed, {})):
            with self.assertRaisesRegex(ValueError, "equivalente"):
                restore_experiment(self.experiment, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
