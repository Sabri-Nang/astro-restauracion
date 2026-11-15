"""Verifica conservación, reproducción y rechazo de cambios en activos gaussianos."""

import json
from pathlib import Path
import tempfile
import unittest

from PIL import Image

from src.experiment import file_hash, prepare_experiment
from src.noise_assets import archive_noise, reproduce_noise


class NoiseAssetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        self.source = self.folder / "original.png"
        Image.new("RGB", (128, 96), (100, 120, 140)).save(self.source)
        self.experiment = self.folder / "experimento"
        prepare_experiment(self.source, self.experiment)
        self.asset = self.folder / "activo"

    def test_archive_keeps_exact_files_and_reproduces_noise_from_preserved_reference(self):
        before = file_hash(self.source)
        metadata = archive_noise(self.experiment, self.source, self.asset)
        self.assertEqual(file_hash(self.source), before)
        self.assertTrue(metadata["pixeles_reproducidos_verificados"])
        for name in ("referencia_preparada.png", "entrada_ruidosa.png", "experimento.json"):
            self.assertEqual(file_hash(self.asset / name), file_hash(self.experiment / name))
        report = reproduce_noise(self.asset / "reproduccion.json", self.folder / "reproducida.png")
        self.assertTrue(report["pixeles_identicos"])
        self.assertTrue(report["png_identico"])
        with self.assertRaises(ValueError):
            archive_noise(self.experiment, self.source, self.asset)
        with self.assertRaises(ValueError):
            reproduce_noise(self.asset / "reproduccion.json", self.folder / "reproducida.png")

    def test_modified_original_is_rejected_before_archiving(self):
        Image.new("RGB", (128, 96)).save(self.source)
        with self.assertRaisesRegex(ValueError, "original"):
            archive_noise(self.experiment, self.source, self.asset)
        self.assertFalse(self.asset.exists())

    def test_modified_reference_and_seed_are_rejected_before_saving(self):
        archive_noise(self.experiment, self.source, self.asset)
        metadata_path = self.asset / "reproduccion.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        metadata["ruido"]["semilla_ruido"] = 124
        metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "píxeles"):
            reproduce_noise(metadata_path, self.folder / "no_guardada.png")
        self.assertFalse((self.folder / "no_guardada.png").exists())
        Image.new("RGB", (128, 96)).save(self.asset / "referencia_preparada.png")
        with self.assertRaisesRegex(ValueError, "referencia"):
            reproduce_noise(metadata_path, self.folder / "no_guardada.png")


if __name__ == "__main__":
    unittest.main()
