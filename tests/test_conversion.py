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

    def test_multiframe_tiff_keeps_all_pages(self):
        import base64
        # Two tiny solid-color frames; no image-generation dependency is needed.
        raw='SUkqAAgAAAAKAAABBAABAAAAAgAAAAEBBAABAAAAAgAAAAIBAwADAAAAhgAAAAMBAwABAAAAAQAAAAYBAwABAAAAAgAAABEBBAABAAAAjAAAABUBAwABAAAAAwAAABYBBAABAAAAAgAAABcBBAABAAAADAAAABwBAwABAAAAAQAAAKgAAAAIAAgACAD/AAD/AAD/AAD/AAAAAAAAAAAAAElJKgAIAAAACgAAAQQAAQAAAAIAAAABAQQAAQAAAAIAAAACAQMAAwAAACYBAAADAQMAAQAAAAEAAAAGAQMAAQAAAAIAAAARAQQAAQAAACwBAAAVAQMAAQAAAAMAAAAWAQQAAQAAAAIAAAAXAQQAAQAAAAwAAAAcAQMAAQAAAAEAAAAAAAAACAAIAAgAAAD/AAD/AAD/AAD/AAAAAAAAAAA='
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'two.tiff';path.write_bytes(base64.b64decode(raw))
            with pymupdf.open(stream=convert_file(path),filetype='pdf') as doc:
                self.assertEqual(len(doc),2)
                self.assertTrue(doc[0].get_images());self.assertTrue(doc[1].get_images())

    def test_office_timeout_reports_error(self):
        import subprocess
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.docx';path.write_bytes(b'fixture')
            with patch('converter.shutil.which',return_value='soffice'),patch('converter.subprocess.run',side_effect=subprocess.TimeoutExpired('soffice',90)):
                with self.assertRaises(ValueError):convert_file(path)
