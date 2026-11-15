"""Pruebas de afinidades e informe sin descargar modelos."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
import torch
from src import analysis

class AnalysisTests(unittest.TestCase):
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
