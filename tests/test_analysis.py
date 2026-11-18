"""Pruebas de afinidades e informe sin descargar modelos."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
import torch
from src import analysis

class AnalysisTests(unittest.TestCase):
    def test_user_report_explains_preferences_without_quality_numbers(self):
        rows = [{'descripcion': 'textura granulada', 'entrada': 0.1234, 'salida': 0.2345, 'diferencia': 0.1111}]
        text = analysis.render_user_report({'afinidades': rows})
        self.assertIn('en ambas imágenes', text)
        self.assertIn('otra observación', text)
        self.assertIn('no confirma cuánto ruido se eliminó', text)
        self.assertNotIn('0.1234', text)
        self.assertNotIn('0.2345', text)

    def test_same_descriptions_in_reverse_order_do_not_claim_equal_images(self):
        rows = [
            {'descripcion': 'estructuras difusas', 'entrada': .4, 'salida': .3},
            {'descripcion': 'fondo uniforme', 'entrada': .3, 'salida': .4},
            {'descripcion': 'textura granulada', 'entrada': .1, 'salida': .1},
        ]
        text = analysis.render_user_report({'afinidades': rows})
        self.assertIn('en ambas imágenes', text)
        self.assertIn('puede haber cambios en los detalles', text)
        self.assertNotIn('desenfoque', text)
        self.assertNotIn('sin ruido', text)

    def test_changed_descriptions_do_not_claim_success_or_hallucination_detection(self):
        rows = [
            {'descripcion': 'textura granulada', 'entrada': .5, 'salida': .1},
            {'descripcion': 'estructuras difusas', 'entrada': .4, 'salida': .2},
            {'descripcion': 'textura artificial', 'entrada': .1, 'salida': .5},
            {'descripcion': 'estructuras definidas', 'entrada': .2, 'salida': .4},
        ]
        text = analysis.render_user_report({'afinidades': rows})
        self.assertIn('En el resultado', text)
        self.assertIn('no confirma cuánto ruido se eliminó', text)
        self.assertIn('no confirma que haya sido inventada', text)
        self.assertNotIn('CLIP', text)
        self.assertNotIn('clase', text)
        self.assertNotIn('puntuaciones', text)

    def test_absent_reading_is_not_reported_as_unchanged_appearance(self):
        text = analysis.render_user_report({'afinidades': []})
        self.assertIn('No hay una lectura disponible', text)
        self.assertNotIn('mismas descripciones', text)
    def test_cosines_are_not_softmax_and_report_is_traceable(self):
        class Processor:
            image_processor = SimpleNamespace(to_dict=lambda: {"crop_size":224})
            def __call__(self, **kwargs):
                self.images = kwargs["images"]
                return {}
        processor = Processor()
        output = SimpleNamespace(image_embeds=torch.tensor([[1.,0.],[0.,2.]]),
                                 text_embeds=torch.tensor([[1.,0.]] * 6))
        image = Image.new("RGB", (64,64))
        with patch.object(analysis, "load_analyzer", return_value=(processor, lambda **kw: output)):
            result = analysis.analyze_images(image, image.copy())
        self.assertEqual(result["afinidades"][0]["entrada"],1)
        self.assertEqual(result["afinidades"][0]["salida"],0)
        self.assertEqual(result["afinidades"][0]["diferencia"],-1)
        self.assertEqual(len(result["afinidades"]),6)
        self.assertIn("sin demostrar mejor limpieza", analysis.render_report(result))
        self.assertEqual(len(processor.images),2)

    def test_invalid_images_rejected_before_loading(self):
        with patch.object(analysis,"load_analyzer") as loader:
            with self.assertRaises(ValueError):
                analysis.analyze_images(Image.new("RGB",(64,64)),Image.new("L",(64,64)))
            loader.assert_not_called()
