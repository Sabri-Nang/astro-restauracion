"""Comprueba condiciones Tile y barridos sin descargar pesos ni inferir."""

import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
import torch

from src.diffusion import CONTROLNET_TILE_REVISION, SafetyFilterBlockedError, load_pipeline, run_diffusion
from src.experiment import file_hash, prepare_experiment, sweep_experiment


class ControlNetDiffusionTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.source = Path(temporary.name) / "ruido.png"
        Image.new("RGB", (128, 96), (100, 120, 140)).save(self.source)
        self.pipeline = MagicMock()
        self.pipeline.device = torch.device("cpu")
        self.pipeline.unet.dtype = torch.float32
        self.pipeline.return_value = SimpleNamespace(
            images=[Image.new("RGB", (128, 96), (100, 120, 140))], nsfw_content_detected=[False],
        )

    def test_tile_conditions_on_the_exact_noisy_input_at_original_working_size(self):
        with patch("src.diffusion.load_pipeline", return_value=self.pipeline) as loader:
            prepared, output, report = run_diffusion(self.source, strength=0.1, steps=30,
                                                    controlnet_tile=True, controlnet_scale=1.0)
        loader.assert_called_once_with("auto", controlnet_tile=True)
        arguments = self.pipeline.call_args.kwargs
        self.assertIs(arguments["control_image"], arguments["image"])
        self.assertEqual(arguments["control_image"].tobytes(), prepared.tobytes())
        self.assertEqual(output.size, prepared.size)
        self.assertEqual(arguments["controlnet_conditioning_scale"], 1.0)
        self.assertEqual((arguments["control_guidance_start"], arguments["control_guidance_end"]), (0.0, 1.0))
        self.assertFalse(arguments["guess_mode"])
        self.assertEqual(report["pasos_efectivos"], 3)
        self.assertEqual(report["controlnet_tile"]["sha256_archivo_condicion"], file_hash(self.source))
        self.assertFalse(report["controlnet_tile"]["referencia_limpia_usada_como_control"])

    def test_default_pipeline_does_not_receive_controlnet_arguments(self):
        with patch("src.diffusion.load_pipeline", return_value=self.pipeline) as loader:
            _, _, report = run_diffusion(self.source)
        loader.assert_called_once_with("auto")
        self.assertNotIn("control_image", self.pipeline.call_args.kwargs)
        self.assertNotIn("controlnet_tile", report)

    def test_filter_block_is_distinct_from_other_runtime_failures(self):
        self.pipeline.return_value.nsfw_content_detected = [True]
        with patch("src.diffusion.load_pipeline", return_value=self.pipeline):
            with self.assertRaises(SafetyFilterBlockedError):
                run_diffusion(self.source, controlnet_tile=True)

    def test_invalid_control_scale_is_rejected_before_loading(self):
        with patch("src.diffusion.load_pipeline") as loader:
            for scale in (-1, 3, float("nan")):
                with self.assertRaises(ValueError):
                    run_diffusion(self.source, controlnet_tile=True, controlnet_scale=scale)
            loader.assert_not_called()

    def test_loader_uses_pinned_tile_checkpoint_and_keeps_safety_checker(self):
        load_pipeline.cache_clear()
        self.addCleanup(load_pipeline.cache_clear)
        with patch("diffusers.ControlNetModel.from_pretrained") as control_loader, patch(
            "diffusers.StableDiffusionControlNetImg2ImgPipeline.from_pretrained", return_value=self.pipeline
        ) as pipeline_loader, patch("diffusers.DDIMScheduler.from_config"):
            result = load_pipeline("cpu", controlnet_tile=True)
        self.assertIs(result, self.pipeline)
        self.assertEqual(control_loader.call_args.kwargs["revision"], CONTROLNET_TILE_REVISION)
        self.assertFalse(control_loader.call_args.kwargs["use_safetensors"])
        self.assertEqual(control_loader.call_args.kwargs["dtype"], torch.bfloat16)
        self.assertIs(pipeline_loader.call_args.kwargs["controlnet"], control_loader.return_value)
        self.assertNotIn("safety_checker", pipeline_loader.call_args.kwargs)
        self.pipeline.to.assert_called_once_with("cpu")


class ControlNetSweepTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name)
        source = self.folder / "fuente.png"
        Image.new("RGB", (128, 96), (100, 120, 140)).save(source)
        self.experiment = self.folder / "experimento"
        prepare_experiment(source, self.experiment)
        self.output = self.folder / "barrido"

    def test_four_strengths_keep_same_input_seed_steps_and_control_scale(self):
        calls = []

        def simulate(path, **kwargs):
            calls.append((path, kwargs))
            with Image.open(path) as image:
                prepared = image.copy()
            if kwargs["strength"] == 0.25:
                raise SafetyFilterBlockedError("Salida bloqueada de prueba")
            return prepared, prepared.copy(), {
                "sha256_entrada": file_hash(path), "pasos_efectivos": int(kwargs["strength"] * kwargs["steps"]),
                "segundos_inferencia": 0.0,
            }

        with patch("src.experiment.run_diffusion", side_effect=simulate):
            report = sweep_experiment(self.experiment, self.output)
        self.assertEqual([kwargs["strength"] for _, kwargs in calls], [0.1, 0.15, 0.2, 0.25])
        self.assertEqual(len({str(path) for path, _ in calls}), 1)
        for _, kwargs in calls:
            self.assertEqual((kwargs["seed"], kwargs["steps"], kwargs["device"]), (42, 30, "cuda"))
            self.assertTrue(kwargs["controlnet_tile"])
            self.assertEqual(kwargs["controlnet_scale"], 1.0)
        self.assertEqual(report["salidas_validas"], 3)
        self.assertTrue(report["ejecucion_cerrada"])
        self.assertFalse(report["completada"])
        self.assertEqual(report["resultados"][-1]["estado"], "bloqueada_filtro_seguridad")
        self.assertFalse((self.output / "intensidad_0.25/salida.png").exists())
        self.assertEqual(file_hash(self.output / "entrada_ruidosa.png"),
                         file_hash(self.experiment / "entrada_ruidosa.png"))
        with self.assertRaises(ValueError):
            sweep_experiment(self.experiment, self.output)

    def test_changed_input_is_rejected_without_loading(self):
        Image.new("RGB", (128, 96)).save(self.experiment / "entrada_ruidosa.png")
        with patch("src.experiment.run_diffusion") as model:
            with self.assertRaisesRegex(ValueError, "cambió"):
                sweep_experiment(self.experiment, self.output)
            model.assert_not_called()
        self.assertFalse(self.output.exists())

    def test_runtime_error_is_not_mislabeled_as_safety_block(self):
        with patch("src.experiment.run_diffusion", side_effect=RuntimeError("Memoria insuficiente")):
            with self.assertRaisesRegex(RuntimeError, "Memoria insuficiente"):
                sweep_experiment(self.experiment, self.output)
        record = json.loads((self.output / "barrido.json").read_text(encoding="utf-8"))
        self.assertEqual(record["fase"], "interrumpido")
        self.assertEqual(record["resultados"], [])


if __name__ == "__main__":
    unittest.main()
