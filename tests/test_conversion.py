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

    def test_utf8_text_html_and_svg(self):
        fixtures={
            'notes.txt':'ทดสอบข้อความภาษาไทย\nEnglish notes',
            'table.csv':'name,value\nalpha,12\nbeta,34',
            'page.html':'<html><body><h1>Document title</h1><p>Sample text</p></body></html>',
            'drawing.svg':'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100"><rect width="200" height="100" fill="blue"/></svg>',
        }
        with tempfile.TemporaryDirectory() as tmp:
            for name,content in fixtures.items():
                path=Path(tmp)/name;path.write_text(content,encoding='utf-8')
                with self.subTest(name=name),pymupdf.open(stream=convert_file(path),filetype='pdf') as doc:
                    self.assertGreaterEqual(len(doc),1)
                    self.assertGreater(doc[0].rect.width,0)
                    if name.endswith('.txt'):self.assertIn('ภาษาไทย',doc[0].get_text())

    def test_content_detection_for_renamed_pdf_and_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'document.unknown'
            with pymupdf.open() as doc:
                doc.new_page().insert_text((60,60),'PDF CONTENT');doc.save(path)
            with pymupdf.open(stream=convert_file(path),filetype='pdf') as doc:
                self.assertIn('PDF CONTENT',doc[0].get_text())
            image_path=Path(tmp)/'picture.data'
            image=QImage(30,20,QImage.Format.Format_RGB888);image.fill(0xff8822)
            self.assertTrue(image.save(str(image_path),'PNG'))
            with pymupdf.open(stream=convert_file(image_path),filetype='pdf') as doc:
                self.assertTrue(doc[0].get_images())

    def test_comic_archive_and_fb2_book(self):
        import zipfile
        with tempfile.TemporaryDirectory() as tmp:
            image_path=Path(tmp)/'page.png'
            image=QImage(40,30,QImage.Format.Format_RGB888);image.fill(0x334455);image.save(str(image_path))
            comic=Path(tmp)/'pages.cbz'
            with zipfile.ZipFile(comic,'w') as z:
                z.write(image_path,'001.png');z.write(image_path,'002.png')
            with pymupdf.open(stream=convert_file(comic),filetype='pdf') as doc:self.assertEqual(len(doc),2)
            book=Path(tmp)/'book.fb2'
            book.write_text('<FictionBook xmlns="http://www.gribuser.ru/xml/fictionbook/2.0"><description><title-info><book-title>Title</book-title><lang>en</lang></title-info></description><body><section><p>Sample book text</p></section></body></FictionBook>')
            with pymupdf.open(stream=convert_file(book),filetype='pdf') as doc:
                self.assertIn('Sample book text',''.join(page.get_text() for page in doc))
