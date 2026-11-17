"""Integración de fotos propias y protocolo persistente, sin pesos ni GPU."""
import hashlib
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from zipfile import ZipFile

from PIL import Image

import app
from src import diffbir_bridge as bridge
from src.export import export_result


def create_worker_files(folder, before):
    folder.mkdir(parents=True)
    for name in ('entrada_preparada.png', 'limpieza_previa.png', 'salida_diffbir.png', 'condicion_interna.png', 'condicion_reducida.png'):
        before.save(folder / name)
    return {'motor': 'diffbir_v2', 'artefactos': {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in folder.glob('*.png')
    }}


class DiffBIRAppTests(unittest.TestCase):
    def test_own_photo_uses_diffbir_without_gaussian_reference_or_sd_strength(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'ASTRORESTORE_ENGINE': 'diffbir'}):
            path = Path(temp) / 'foto_propia.png'
            Image.new('RGB', (80, 64), (17, 51, 83)).save(path)
            received = []

            def infer(image, progress):
                received.append(image.copy())
                return image, image.copy(), {'motor': 'diffbir_v2', 'referencia_usada_para_generar': False}

            with patch.object(app, 'get_session', return_value=SimpleNamespace(infer=infer)), patch.object(app, 'run_diffusion') as old:
                result = app.process_image(str(path), None, 30, 42, 256)
            old.assert_not_called()
            self.assertEqual(received[0].getpixel((0, 0)), (17, 51, 83))
            self.assertEqual(result[4]['motor'], 'diffbir_v2')
            self.assertNotIn('psnr', result[4])
            self.assertFalse(result[4]['referencia_usada_para_generar'])
            self.assertEqual(result[4]['sha256_original'], hashlib.sha256(path.read_bytes()).hexdigest())

    def test_incompatible_photo_is_rejected_before_worker_starts(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, {'ASTRORESTORE_ENGINE': 'diffbir'}):
            path = Path(temp) / 'foto.jpg'
            Image.new('RGB', (64, 64)).save(path)
            with patch.object(app, 'get_session') as session:
                with self.assertRaises(Exception):
                    app.process_image(str(path), None, 30, 42, 256)
            session.assert_not_called()

    def test_user_view_does_not_relabel_sd_strength_as_diffbir_control(self):
        with patch.dict(os.environ, {'ASTRORESTORE_ENGINE': 'diffbir'}):
            with patch.object(app, 'get_session') as session:
                interface = app.create_app()
            session.assert_not_called()
        components = interface.config['components']
        self.assertFalse(any(item['type'] == 'slider' for item in components))
        self.assertTrue(any(item['type'] == 'imageslider' for item in components))
        labels = [item['props'].get('label', '') for item in components]
        self.assertIn('Primera limpieza, antes de reconstruir detalles', labels)
        self.assertNotIn('Cuánto puede cambiar la IA tu foto', labels)

    def test_worker_result_checks_source_and_intermediate_hashes(self):
        with tempfile.TemporaryDirectory() as temp:
            before = Image.new('RGB', (64, 64), (1, 2, 3))
            folder = Path(temp) / 'resultado'
            record = create_worker_files(folder, before)
            _, after, metadata = bridge.read_worker_result(before, folder, record)
            self.assertEqual(after.tobytes(), before.tobytes())
            state = (before, after, metadata, 'foto.png')
            with patch.object(app, 'get_session') as session:
                self.assertEqual(app.first_cleaning(state).tobytes(), before.tobytes())
            session.assert_not_called()
            with (folder / 'limpieza_previa.png').open('ab') as stream:
                stream.write(b'alterado')
            with self.assertRaises(ValueError):
                bridge.read_worker_result(before, folder, record)

    def test_worker_cannot_attach_result_to_a_different_uploaded_photo(self):
        with tempfile.TemporaryDirectory() as temp:
            image = Image.new('RGB', (64, 64), (10, 20, 30))
            folder = Path(temp) / 'resultado'
            record = create_worker_files(folder, image)
            with self.assertRaisesRegex(ValueError, 'otra entrada'):
                bridge.read_worker_result(Image.new('RGB', (64, 64)), folder, record)

    def test_export_preserves_first_cleaning_and_removes_machine_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            image = Image.new('RGB', (64, 64), (20, 40, 60))
            source = root / 'original.png'
            image.save(source)
            stages = root / 'stages'
            record = create_worker_files(stages, image)
            _, _, record = bridge.read_worker_result(image, stages, record)
            with patch('src.export.ROOT', root):
                archive = export_result(image, image, record, 'Informe orientativo', source)
            with ZipFile(archive) as zipped:
                self.assertEqual(zipped.read('limpieza_previa.png'), (stages / 'limpieza_previa.png').read_bytes())
                self.assertEqual(zipped.read('original.png'), source.read_bytes())
                metadata = json.loads(zipped.read('parametros.json'))
                self.assertEqual(metadata['intermedios']['limpieza_previa.png'], 'limpieza_previa.png')
                self.assertNotIn('psnr', metadata)
                self.assertNotIn(str(stages), zipped.read('parametros.json').decode())

    def test_server_reuses_engine_for_two_photos_and_keeps_stdout_as_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            requests = []
            for index in range(2):
                path = root / f'foto{index}.png'
                Image.new('RGB', (64, 64), (index, 40, 80)).save(path)
                requests.append({'id': str(index), 'input': str(path), 'output': str(root / f'salida{index}')})
            engine = SimpleNamespace()
            calls = []

            def process(before, destination, on_phase):
                print('Log de biblioteca externa')
                calls.append(before.getpixel((0, 0)))
                on_phase('reconstruyendo')
                return before, before, before, {'motor': 'simulado_sin_inferencia'}

            engine.process = process
            protocol, logs = StringIO(), StringIO()
            with patch('src.diffusion.DiffBIRRuntime', return_value=engine) as constructor:
                with patch('sys.stdin', StringIO(''.join(json.dumps(item) + '\n' for item in requests))), patch('sys.stdout', protocol), patch('sys.stderr', logs):
                    bridge.serve(root)
            self.assertEqual(constructor.call_count, 1)
            self.assertEqual(calls, [(0, 40, 80), (1, 40, 80)])
            messages = [json.loads(line) for line in protocol.getvalue().splitlines()]
            self.assertEqual([message['id'] for message in messages if message['type'] == 'result'], ['0', '1'])
            self.assertNotIn('Log de biblioteca', protocol.getvalue())
            self.assertIn('Log de biblioteca', logs.getvalue())

    def test_failed_source_download_does_not_leave_a_broken_cache(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(bridge, 'ROOT', Path(temp)):
            session = bridge.DiffBIRSession()
            try:
                with patch.object(bridge.subprocess, 'run', side_effect=OSError('sin conexión')):
                    with self.assertRaises(OSError):
                        session._source()
                self.assertFalse((Path(temp) / '.cache/diffbir/source').exists())
                self.assertEqual(list((Path(temp) / '.cache/diffbir').iterdir()), [])
            finally:
                session.close()


if __name__ == '__main__':
    unittest.main()
