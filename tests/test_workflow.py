"""Integración y recuperación sin inferencias costosas."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile
from PIL import Image
import app
from src.export import export_result

class WorkflowTests(unittest.TestCase):
    def test_clip_failure_preserves_images_and_retry_does_not_diffuse(self):
        image=Image.new('RGB',(64,64))
        metadata={'semilla':42}
        with patch.object(app,'run_diffusion',return_value=(image,image.copy(),metadata)) as diffusion, \
             patch.object(app,'analyze_images',side_effect=OSError('sin conexión')), \
             patch.object(app,'export_result',return_value='resultado.zip'):
            result=app.run_complete('archivo.png',0.1,30,42,256,progress=lambda *a,**kw:None)
        self.assertEqual(result[6],'resultado.zip')
        self.assertIn('no disponible',result[5])
        self.assertEqual(diffusion.call_args.kwargs['controlnet_tile'],True)
        with patch.object(app,'run_diffusion') as diffusion, \
             patch.object(app,'analyze_images',return_value={'afinidades':[]}), \
             patch.object(app,'export_result',return_value='resultado.zip'):
            report,metadata,_=app.complete_analysis(result[7])
            diffusion.assert_not_called()
        self.assertNotIn('no disponible',report)
        self.assertEqual(metadata['analisis_visual']['afinidades'],[])

    def test_export_preserves_source_pixels_and_parameters(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            source=root/'subida.png'
            image=Image.new('RGB',(64,64),(4,5,6))
            image.save(source)
            with patch('src.export.ROOT',root):
                archive=export_result(image,image.copy(),{'semilla':42},'informe',source)
            with ZipFile(archive) as zipped:
                self.assertEqual(zipped.read('original.png'),source.read_bytes())
                record=json.loads(zipped.read('parametros.json'))
                self.assertEqual(record['semilla'],42)
                self.assertIn('entrada_preparada.png',record['hashes_exportados_sha256'])
                self.assertNotIn('psnr',record)
                self.assertIn('no distingue',record['mapa_diferencias'])
                self.assertIn('zonas_para_revisar.png', zipped.namelist())
                self.assertIn('para_compartir_con_aviso.png', zipped.namelist())
                self.assertEqual(record['resaltado_de_cambios']['umbral_fijo'], 12)
                self.assertIn('no es una observación', zipped.read('LEEME.txt').decode('utf-8').lower())
                with zipped.open('salida_ia.png') as exported:
                    with Image.open(exported) as saved:
                        self.assertEqual(saved.tobytes(), image.tobytes())
                        self.assertIn('IA', saved.info['Description'])

    def test_user_view_has_no_examples_or_raw_record_and_keeps_comparison(self):
        interface = app.create_app()
        components = interface.config['components']
        labels = [item['props'].get('label', '') for item in components]
        self.assertFalse(any(item['type'] == 'json' for item in components))
        self.assertNotIn('Ver parámetros y registro completo', labels)
        self.assertFalse(any(item['type'] == 'dataset' for item in components))
        self.assertTrue(any(item['type'] == 'imageslider' for item in components))

    def test_user_toggle_does_not_infer_and_preserves_raw_result(self):
        before = Image.new('RGB', (64, 64), (10, 20, 30))
        after = Image.new('RGB', (64, 64), (110, 120, 130))
        state = (before, after, {}, 'entrada.png')
        with patch.object(app, 'run_diffusion') as diffusion:
            marked = app.review_image(state, True)
            raw = app.review_image(state, False)
        diffusion.assert_not_called()
        self.assertEqual(raw.tobytes(), after.tobytes())
        self.assertNotEqual(marked.tobytes(), after.tobytes())
