"""Paridad de selección y activos entre local, notebook y paquete, sin modelos."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PIL import Image
import app


class EnvironmentParityTests(unittest.TestCase):
    def test_local_default_matches_colab_default_without_loading_models(self):
        notebook = json.loads((app.ROOT / 'colab/ejecutar_en_colab.ipynb').read_text(encoding='utf-8'))
        preparation = next(cell for cell in notebook['cells'] if cell['id'] == 'preparar')
        import ast
        tree = ast.parse(''.join(preparation['source']))
        motor = next(ast.literal_eval(node.value) for node in tree.body
                     if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == 'MOTOR' for target in node.targets))
        with patch.dict(os.environ, {}, clear=True), patch.object(app, 'get_session') as session:
            self.assertEqual(app.selected_engine(), motor)
            self.assertEqual(motor, 'diffbir')
            interface = app.create_app()
        session.assert_not_called()
        self.assertFalse(any(item['type'] == 'slider' for item in interface.config['components']))

    def test_windows_preview_does_not_enable_diffbir_or_start_worker(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'foto.png'
            Image.new('RGB', (64, 64)).save(path)
            with patch.dict(os.environ, {'ASTRORESTORE_ENGINE': 'diffbir'}), patch.object(app.sys, 'platform', 'win32'), patch.object(app, 'get_session') as session:
                result = app.inspect_upload(str(path))
            self.assertIsNotNone(result[0])
            self.assertFalse(result[3]['interactive'])
            self.assertIn('Colab con GPU', result[2])
            session.assert_not_called()

    def test_historical_engine_requires_explicit_selection(self):
        with patch.dict(os.environ, {'ASTRORESTORE_ENGINE': 'sd_tile'}), patch.object(app.sys, 'platform', 'win32'):
            self.assertEqual(app.selected_engine(), 'sd_tile')
            self.assertTrue(app.can_process_here())
            interface = app.create_app()
        text = ' '.join(str(item['props'].get('value', '')) for item in interface.config['components'])
        self.assertIn('Modo histórico', text)
        self.assertIn('no ejecuta DiffBIR', text)

    def test_startup_identity_tracks_active_engine_and_source_bytes(self):
        with patch.dict(os.environ, {'ASTRORESTORE_ENGINE': 'diffbir'}):
            identity = app.runtime_identity()
        self.assertEqual(identity['motor'], 'diffbir')
        for name, expected in identity['sha256'].items():
            self.assertEqual(hashlib.sha256((app.ROOT / name).read_text(encoding='utf-8').encode('utf-8')).hexdigest(), expected)
        self.assertIn('assets/interfaz/tema.css', identity['sha256'])
        self.assertIn('colab/diffbir/uv.lock', identity['sha256'])

    def test_identity_ignores_windows_vs_linux_line_endings(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'ASTRORESTORE_ENGINE': 'diffbir'}):
            original = app.runtime_identity()
            root = Path(temp)
            for name in original['sha256']:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                text = (app.ROOT / name).read_text(encoding='utf-8')
                target.write_bytes(text.replace('\n', '\r\n').encode('utf-8'))
            with patch.object(app, 'ROOT', root):
                windows = app.runtime_identity()
            self.assertEqual(windows, original)


if __name__ == '__main__':
    unittest.main()
