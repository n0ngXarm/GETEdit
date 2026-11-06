import tempfile
import unittest
from pathlib import Path
from converter import convert_file
from app import pymupdf
from PySide6.QtGui import QImage

class ConversionTests(unittest.TestCase):
    def test_image_and_unsupported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'ภาพ.png'
            image = QImage(200,100,QImage.Format.Format_RGB888); image.fill(0xff4488)
            self.assertTrue(image.save(str(p)))
            with pymupdf.open(stream=convert_file(p),filetype='pdf') as doc:
                self.assertEqual(len(doc),1)
                self.assertTrue(doc[0].get_images())
            with self.assertRaises(ValueError): convert_file(Path(tmp)/'unknown.exe')
