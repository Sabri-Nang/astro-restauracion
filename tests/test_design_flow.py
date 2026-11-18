"""Estados visibles, errores recuperables y comparación de regiones sin modelos."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import gradio as gr
import app
from src.diffusion import observe_sampling_steps


class DesignFlowTests(unittest.TestCase):
    def setUp(self):
        # Los escenarios de flujo simulan una sesión con procesamiento disponible.
        capability = patch.object(app, 'can_process_here', return_value=True)
        capability.start()
        self.addCleanup(capability.stop)

    def test_progress_is_visible_before_inference_and_uses_measured_steps_only(self):
        image = Image.new('RGB', (64, 64))
        metadata = {'analisis_visual': {'afinidades': []}}
        state = (image, image, metadata, 'foto.png')

        def run(*args, progress, **kwargs):
            value, description = app.PHASES['reconstruyendo']
            progress(value, desc=description)
            progress((25, 50), desc='Generando reconstrucción')
            return image, image, (image, image), image, metadata, 'Informe', 'archivo.zip', state

        with patch.object(app, 'run_complete', side_effect=run) as engine:
            stream = app.stream_processing('foto.png', None)
            first = next(stream)
            engine.assert_not_called()
            self.assertIn('Preparando la IA', first[0])
            self.assertIn('role="status"', first[0])
            self.assertNotIn('<progress', first[0])
            rest = list(stream)
        statuses = [row[0] for row in rest]
        self.assertTrue(any('25/50 pasos (50 %)' in status for status in statuses))
        self.assertFalse(any('55 %' in status for status in statuses))
        self.assertIn('Resultado disponible', rest[-1][0])
        self.assertIs(rest[-1][1], state)
        self.assertTrue(rest[-1][-1]['interactive'])
        self.assertEqual(engine.call_count, 1)

    def test_failure_returns_persistent_message_and_restores_controls(self):
        with patch.object(app, 'run_complete', side_effect=gr.Error('No se pudo abrir la foto.')):
            rows = list(app.stream_processing('foto.png', None))
        self.assertIn('No se pudo terminar', rows[-1][0])
        self.assertIn('Tu archivo original se conserva', rows[-1][0])
        self.assertIsNone(rows[-1][1])
        self.assertTrue(rows[-1][-2]['interactive'])
        self.assertTrue(rows[-1][-1]['interactive'])

    def test_upload_validation_preserves_source_and_never_loads_models(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'foto.png'
            Image.new('RGB', (128, 64)).save(path)
            original = path.read_bytes()
            with patch.object(app, 'get_session') as session:
                valid = app.inspect_upload(str(path))
                self.assertEqual(path.read_bytes(), original)
                path.write_bytes(b'archivo ilegible')
                invalid = app.inspect_upload(str(path))
            session.assert_not_called()
            self.assertEqual(valid[0].size, (128, 64))
            self.assertTrue(valid[3]['interactive'])
            self.assertIn('Archivo listo', valid[1])
            self.assertIsNone(invalid[0])
            self.assertFalse(invalid[3]['interactive'])
            self.assertIn('No se inició la IA', invalid[2])

    def test_same_crop_and_nearest_enlargement_apply_to_both_stages(self):
        before = Image.new('RGB', (64, 64))
        after = Image.new('RGB', (64, 64))
        before.putdata([(x, y, 0) for y in range(64) for x in range(64)])
        after.putdata([(x + 2, y, 0) for y in range(64) for x in range(64)])
        state = (before, after, {}, 'foto.png')
        source_pixels = before.tobytes(), after.tobytes()
        with patch.object(app, 'get_session') as session:
            pair, text = app.workspace_pair(state, app.REVIEW_PAIRS[2], False, 'Abajo derecha', 'Ampliar píxeles ×2')
        session.assert_not_called()
        self.assertEqual(pair[0].size, (64, 64))
        self.assertEqual(pair[0].getpixel((0, 0)), (32, 32, 0))
        self.assertEqual(pair[1].getpixel((0, 0)), (34, 32, 0))
        self.assertEqual(pair[0].getpixel((1, 1)), (32, 32, 0))
        self.assertIn('Abajo derecha', text)
        self.assertEqual(source_pixels, (before.tobytes(), after.tobytes()))

    def test_sampler_observer_preserves_results_and_restores_method_after_error(self):
        token = object()

        class Sampler:
            timesteps = [1, 2]

            def p_sample(self, fail=False):
                if fail:
                    raise ValueError('fallo de prueba')
                return token

        original = Sampler.p_sample
        steps = []
        with self.assertRaises(ValueError):
            with observe_sampling_steps(Sampler, lambda done, total: steps.append((done, total))):
                self.assertIs(Sampler().p_sample(), token)
                Sampler().p_sample(fail=True)
        self.assertIs(Sampler.p_sample, original)
        self.assertEqual(steps, [(1, 2)])

    def test_retry_changes_partial_notice_to_ready_without_running_diffusion(self):
        image = Image.new('RGB', (64, 64))
        state = (image, image, {}, 'foto.png')
        with patch.object(app, 'run_diffusion') as diffusion, patch.object(app, 'get_session') as session:
            with patch.object(app, 'complete_analysis', return_value=('Lectura no disponible', {'analisis_visual': {'estado': 'error'}}, 'archivo.zip')):
                partial = app.retry_workspace(state)
            with patch.object(app, 'complete_analysis', return_value=('Lectura disponible', {'analisis_visual': {'afinidades': []}}, 'archivo.zip')):
                ready = app.retry_workspace(partial[3])
        self.assertIn('siguen sin estar disponibles', partial[0])
        self.assertIn('Resultado disponible', ready[0])
        self.assertIs(ready[3][0], image)
        diffusion.assert_not_called()
        session.assert_not_called()


if __name__ == '__main__':
    unittest.main()
