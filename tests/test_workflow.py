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
