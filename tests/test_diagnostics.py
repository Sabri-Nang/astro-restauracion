"""Comprueba controles VAE y sigma cero sin pesos ni inferencias reales."""

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

import torch
from PIL import Image

from src.diagnostics import run_controls
from src.diffusion import SafetyFilterBlockedError, reconstruct_vae
from src.experiment import prepare_experiment


class VaeControlTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name) / "imagen.png"
        self.image = Image.new("RGB", (128, 96), (100, 120, 140))
        self.image.save(self.path)
        self.pipeline = MagicMock()
        self.pipeline.device = torch.device("cpu")
        self.pipeline.vae.dtype = torch.float32
        self.pipeline.vae.config.scaling_factor = 0.18215
        self.pipeline.image_processor.preprocess.return_value = torch.zeros(1, 3, 96, 128)
        self.distribution = MagicMock()
        self.distribution.sample.return_value = torch.ones(1, 4, 12, 16)
        self.distribution.mode.return_value = torch.ones(1, 4, 12, 16)
        self.pipeline.vae.encode.return_value = SimpleNamespace(latent_dist=self.distribution)
        decoded = torch.zeros(1, 3, 96, 128)
        self.pipeline.vae.decode.return_value = (decoded,)
        self.pipeline.run_safety_checker.return_value = (decoded, [False])
        self.pipeline.image_processor.postprocess.return_value = [self.image.copy()]

    def test_sample_uses_seeded_posterior_without_unet_or_scheduler(self):
        with patch("src.diffusion.load_pipeline", return_value=self.pipeline):
            prepared, _, record = reconstruct_vae(self.path, device="cpu", posterior="sample", seed=42)
        self.assertEqual(prepared.tobytes(), self.image.tobytes())
        self.assertEqual(self.distribution.sample.call_args.kwargs["generator"].initial_seed(), 42)
        self.distribution.mode.assert_not_called()
        self.pipeline.assert_not_called()
        self.pipeline.unet.assert_not_called()
        self.pipeline.scheduler.step.assert_not_called()
        self.pipeline.scheduler.add_noise.assert_not_called()
        self.pipeline.run_safety_checker.assert_called_once()
        self.assertFalse(record["unet_ejecutada"])
        self.assertFalse(record["scheduler_ejecutado"])
        self.assertEqual(record["semilla_vae"], 42)
        self.assertTrue(torch.allclose(self.pipeline.vae.decode.call_args.args[0], torch.ones(1, 4, 12, 16)))

    def test_mode_is_deterministic_and_has_no_sampling_seed(self):
        with patch("src.diffusion.load_pipeline", return_value=self.pipeline):
            _, _, record = reconstruct_vae(self.path, posterior="mode", device="cpu")
        self.distribution.mode.assert_called_once_with()
        self.distribution.sample.assert_not_called()
        self.assertIsNone(record["semilla_vae"])
        self.assertIsNone(self.pipeline.vae.decode.call_args.kwargs["generator"])

    def test_safety_filter_stays_active(self):
        self.pipeline.run_safety_checker.return_value = (torch.zeros(1, 3, 96, 128), [True])
        with patch("src.diffusion.load_pipeline", return_value=self.pipeline):
            with self.assertRaises(SafetyFilterBlockedError):
                reconstruct_vae(self.path, device="cpu")
        self.pipeline.image_processor.postprocess.assert_not_called()

    def test_invalid_posterior_is_rejected_before_loading(self):
        with patch("src.diffusion.load_pipeline") as loader:
            with self.assertRaises(ValueError):
                reconstruct_vae(self.path, posterior="otro")
            loader.assert_not_called()


class DiagnosticProtocolTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        source = self.folder / "original.png"
        Image.new("RGB", (256, 192), (100, 120, 140)).save(source)
        self.asset = self.folder / "activo"
        prepare_experiment(source, self.asset)
        self.output = self.folder / "controles"

    @staticmethod
    def simulate(path, **kwargs):
        with Image.open(path) as image:
            prepared = image.copy()
        return prepared, prepared.copy(), {"controlnet_tile": {"referencia_limpia_usada_como_control": False}}

    def test_protocol_keeps_input_and_distinguishes_zero_sigma_from_strength(self):
        with patch("src.diagnostics.reconstruct_vae", side_effect=self.simulate) as vae, patch(
            "src.diagnostics.run_diffusion", side_effect=self.simulate
        ) as diffusion:
            report = run_controls(self.asset, self.output, device="cpu")
        self.assertEqual(vae.call_count, 3)
        self.assertEqual([call.kwargs["posterior"] for call in vae.call_args_list], ["mode", "sample", "sample"])
        self.assertEqual(vae.call_args_list[2].args[0].name, "entrada_ruidosa.png")
        self.assertEqual(diffusion.call_count, 2)
        for call in diffusion.call_args_list:
            self.assertEqual(call.args[0].name, "referencia_preparada.png")
            self.assertEqual((call.kwargs["strength"], call.kwargs["steps"], call.kwargs["seed"]), (0.1, 30, 42))
        self.assertNotIn("controlnet_tile", diffusion.call_args_list[0].kwargs)
        self.assertTrue(diffusion.call_args_list[1].kwargs["controlnet_tile"])
        self.assertTrue(report["ejecucion_cerrada"])
        self.assertEqual(len(report["resultados"]), 7)
        self.assertTrue(report["resultados"][0]["frente_referencia"]["psnr_infinito"])
        tile = report["resultados"][-1]["parametros"]["controlnet_tile"]
        self.assertTrue(tile["referencia_preparada_es_entrada_y_condicion"])
        self.assertNotIn("referencia_limpia_usada_como_control", tile)
        json.loads((self.output / "controles.json").read_text(encoding="utf-8"))
        with self.assertRaises(ValueError):
            run_controls(self.asset, self.output)

    def test_filter_block_is_recorded_and_other_controls_continue(self):
        with patch("src.diagnostics.reconstruct_vae", side_effect=[
            SafetyFilterBlockedError("Bloqueo simulado"),
            self.simulate(self.asset / "referencia_preparada.png"),
            self.simulate(self.asset / "entrada_ruidosa.png"),
        ]), patch("src.diagnostics.run_diffusion", side_effect=self.simulate):
            report = run_controls(self.asset, self.output, device="cpu")
        self.assertEqual(report["resultados"][2]["estado"], "bloqueada_filtro_seguridad")
        self.assertNotIn("frente_referencia", report["resultados"][2])
        self.assertTrue(report["ejecucion_cerrada"])

    def test_changed_reference_is_rejected_without_loading_models(self):
        Image.new("RGB", (256, 192)).save(self.asset / "referencia_preparada.png")
        with patch("src.diagnostics.reconstruct_vae") as vae, patch("src.diagnostics.run_diffusion") as model:
            with self.assertRaisesRegex(ValueError, "cambió"):
                run_controls(self.asset, self.output)
            vae.assert_not_called()
            model.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_runtime_failure_is_saved_as_interruption(self):
        with patch("src.diagnostics.reconstruct_vae", side_effect=RuntimeError("Error de prueba")):
            with self.assertRaises(RuntimeError):
                run_controls(self.asset, self.output)
        report = json.loads((self.output / "controles.json").read_text(encoding="utf-8"))
        self.assertEqual(report["fase"], "interrumpido")
        self.assertFalse(report["ejecucion_cerrada"])


if __name__ == "__main__":
    unittest.main()
