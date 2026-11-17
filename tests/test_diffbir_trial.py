"""Verifica el protocolo DiffBIR sin descargar pesos ni ejecutar modelos."""
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

from src import diffbir_trial as trial


class DiffBIRTrialTests(unittest.TestCase):
    def test_preparation_preserves_known_pair_and_does_not_infer(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ensayo"
            with patch.object(trial, "download_weight") as download:
                record = trial.prepare_trial(output)
            download.assert_not_called()
            self.assertFalse(record["inferencia_scunet_ejecutada"])
            self.assertFalse(record["inferencia_difusion_ejecutada"])
            self.assertFalse(record["referencia_usada_para_generar"])
            for name, expected in trial.INPUT_HASHES.items():
                self.assertEqual(trial.digest(output / name), expected)
            self.assertEqual(record["parametros"]["control_strength"], 1)
            self.assertEqual(record["parametros"]["upscale_salida"], 1)
            with self.assertRaises(FileExistsError):
                trial.prepare_trial(output)

    def test_altered_reference_or_input_is_rejected_before_creating_output(self):
        for filename in trial.INPUT_HASHES:
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as temp:
                asset, output = Path(temp) / "asset", Path(temp) / "ensayo"
                shutil.copytree(trial.ASSET, asset)
                with (asset / filename).open("ab") as stream:
                    stream.write(b"alteracion")
                with self.assertRaises(ValueError):
                    trial.prepare_trial(output, asset)
                self.assertFalse(output.exists())

    def test_metrics_attribute_stage1_and_final_separately_without_claiming_improvement(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ensayo"
            record = trial.prepare_trial(output)
            # Simular una etapa 1 idéntica a la referencia y una final igual a la entrada ruidosa.
            for filename in ("scunet_nativo.png", "condicion_reducida.png"):
                shutil.copyfile(output / "referencia_preparada.png", output / filename)
            shutil.copyfile(output / "entrada_ruidosa.png", output / "diffbir_final.png")
            record.update(inferencia_scunet_ejecutada=True, inferencia_difusion_ejecutada=True)
            result = trial.evaluate_trial(output, record)
            by_file = {row["archivo"]: row for row in result["evaluacion"]["filas"]}
            self.assertTrue(by_file["scunet_nativo.png"]["psnr_infinito"])
            self.assertEqual(by_file["diffbir_final.png"]["delta_ssim_vs_entrada"], 0)
            self.assertLess(result["comparacion_final_vs_scunet"]["delta_ssim"], 0)
            self.assertEqual(len(by_file["diffbir_final.png"]["regiones"]), 4)
            with ZipFile(trial.archive_trial(output)) as zipped:
                self.assertEqual(zipped.read("entrada_ruidosa.png"), (trial.ASSET / "entrada_ruidosa.png").read_bytes())
                self.assertIn("recortes.png", zipped.namelist())
                self.assertIn("procedencia", json.loads(zipped.read("resultado.json")))

    def test_partial_trial_does_not_treat_unrecorded_final_as_a_result(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ensayo"
            record = trial.prepare_trial(output)
            Image.new("RGB", (256, 192)).save(output / "diffbir_final.png")
            result = trial.evaluate_trial(output, record)
            self.assertEqual(len(result["evaluacion"]["filas"]), 1)
            self.assertNotIn("comparacion_final_vs_scunet", result)

    def test_dimension_mismatch_is_not_resized_for_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ensayo"
            record = trial.prepare_trial(output)
            Image.new("RGB", (512, 384)).save(output / "diffbir_final.png")
            record["inferencia_difusion_ejecutada"] = True
            with self.assertRaises(ValueError):
                trial.evaluate_trial(output, record)

    def test_changed_protocol_stops_before_any_model_or_repository_access(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ensayo"
            record = trial.prepare_trial(output)
            record["parametros"]["control_strength"] = 0.1
            trial.write_record(output, record)
            with patch.object(trial.subprocess, "check_output") as command:
                with self.assertRaises(ValueError):
                    trial.run_trial(output, Path(temp) / "fuente")
            command.assert_not_called()

    def test_missing_cuda_records_failure_and_exports_without_downloading_weights(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ensayo"
            trial.prepare_trial(output)
            with patch.object(trial.subprocess, "check_output", side_effect=[trial.UPSTREAM_REVISION, ""]):
                with patch("torch.cuda.is_available", return_value=False):
                    with patch.object(trial, "download_weight") as download:
                        with self.assertRaisesRegex(RuntimeError, "CUDA"):
                            trial.run_trial(output, Path(temp) / "fuente")
            download.assert_not_called()
            record = json.loads((output / "resultado.json").read_text(encoding="utf-8"))
            self.assertEqual(record["estado"], "fallo_sin_resultados")
            self.assertFalse(record["inferencia_scunet_ejecutada"])
            self.assertFalse(record["inferencia_difusion_ejecutada"])
            with ZipFile(output / "prueba_diffbir.zip") as zipped:
                self.assertIn("resultado.json", zipped.namelist())
                self.assertNotIn("diffbir_final.png", zipped.namelist())

    def test_checkpoint_mapping_keeps_tensor_values(self):
        import torch
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "checkpoint.pth"
            expected = torch.arange(12, dtype=torch.float32).reshape(3, 4)
            torch.save({"state_dict": {"peso": expected}}, path)
            original_load = torch.load

            def torch22_load(filename, **kwargs):
                # El entorno local más nuevo acepta Path, pero Torch 2.2 no lo hace con mmap.
                if kwargs.get("mmap") and not isinstance(filename, str):
                    raise ValueError("f must be a string filename in order to use mmap argument")
                return original_load(filename, **kwargs)

            with patch("torch.load", side_effect=torch22_load):
                loaded, mapped = trial.load_checkpoint_cpu(path)
            self.assertTrue(mapped)
            self.assertTrue(torch.equal(loaded["state_dict"]["peso"], expected))

    def test_missing_legacy_checkpoint_dependency_has_actionable_message(self):
        with patch.object(trial.importlib, "import_module", side_effect=ModuleNotFoundError("No module named 'pkg_resources'")):
            with self.assertRaisesRegex(RuntimeError, "setuptools==80.9.0"):
                trial.check_checkpoint_dependencies()

    def test_checkpoint_preflight_checks_the_class_used_by_pickle(self):
        from types import SimpleNamespace
        with patch.object(trial.importlib, "import_module", side_effect=[SimpleNamespace(), SimpleNamespace()]) as imports:
            with self.assertRaisesRegex(RuntimeError, "ModelCheckpoint"):
                trial.check_checkpoint_dependencies()
            self.assertEqual(imports.call_args_list[-1].args[0], "pytorch_lightning.callbacks")

    def test_parent_marks_abrupt_exit_without_claiming_oom_or_diffusion_success(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ensayo"
            record = trial.prepare_trial(output)
            record.update(estado="ejecutando", inferencia_scunet_ejecutada=True)
            trial.write_record(output, record)
            result = trial.record_process_exit(output, 137)
            self.assertEqual(result["estado"], "interrumpido_con_resultados_parciales")
            self.assertEqual(result["subproceso"]["codigo_salida"], 137)
            self.assertTrue(result["subproceso"]["compatible_con_sigkill"])
            self.assertFalse(result["inferencia_difusion_ejecutada"])
            self.assertIn("causa no determinada", result["error"]["mensaje"])

    def test_parent_rejects_successful_exit_without_completed_diffusion(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ensayo"
            trial.prepare_trial(output)
            result = trial.record_process_exit(output, 0)
            self.assertEqual(result["estado"], "interrumpido_sin_resultados")
            self.assertFalse(result["inferencia_difusion_ejecutada"])

    def test_notebook_logs_and_propagates_subprocess_exit_code(self):
        import ast
        from types import SimpleNamespace
        import subprocess
        notebook = json.loads((trial.ROOT / "colab/ejecutar_en_colab.ipynb").read_text(encoding="utf-8"))
        source = ''.join(next(cell['source'] for cell in notebook['cells'] if cell['id'] == 'instalar'))
        tree = ast.parse(source)
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'ejecutar')
        worker = SimpleNamespace(stdout=iter(["mensaje del proceso\n"]), wait=lambda: 137)
        mocked_subprocess = SimpleNamespace(Popen=lambda *args, **kwargs: worker, PIPE=subprocess.PIPE,
                                           STDOUT=subprocess.STDOUT, CalledProcessError=subprocess.CalledProcessError)
        with tempfile.TemporaryDirectory() as temp:
            namespace = {"subprocess": mocked_subprocess, "proyecto": Path(temp)}
            exec(compile(ast.Module(body=[function], type_ignores=[]), '<helper-notebook>', 'exec'), namespace)
            log = Path(temp) / 'logs' / 'ensayo.log'
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                namespace['ejecutar'](['programa'], log=log)
            self.assertEqual(caught.exception.returncode, 137)
            self.assertIn('Código de salida del subproceso: 137', log.read_text(encoding='utf-8'))


if __name__ == "__main__":
    unittest.main()
