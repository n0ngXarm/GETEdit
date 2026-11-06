import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import unittest
from pathlib import Path
from app import QApplication, Window, pymupdf

class EditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])

    def test_overlay_persistence_undo_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'source.pdf'
            with pymupdf.open() as doc:
                page=doc.new_page();page.insert_text((100,150),'ORIGINAL')
                doc.new_page().set_rotation(90);doc.save(path)
            window=Window();window.add_paths([str(path)])
            window.canvas.add_object('text',text='ข้อความไทย')
            selected=window.canvas.selected()[0];selected.setPos(80,200)
            window.canvas.scale_selected(1.2)
            self.assertEqual(window.canvas.objects()[0]['x'],80)
            window.canvas.delete_selected();self.assertFalse(window.canvas.objects())
            window.canvas.undo();self.assertEqual(len(window.canvas.objects()),1)
            window.pages.setCurrentRow(1);window.canvas.add_object('box')
            window.pages.setCurrentRow(0)
            self.assertEqual(window.canvas.objects()[0]['text'],'ข้อความไทย')
            before=path.read_bytes();data=window.export_bytes()
            with pymupdf.open(stream=data,filetype='pdf') as result:
                self.assertIn('ORIGINAL',result[0].get_text())
                self.assertEqual(result[1].rotation,90)
                self.assertTrue(result[0].get_images());self.assertTrue(result[1].get_images())
                result[0].get_pixmap().save('/tmp/getedit-export-preview.png')
            self.assertEqual(path.read_bytes(),before)
            # Inserting pages before the active page must shift its overlay with it.
            window.placement.setCurrentIndex(1);window.add_paths([str(path)])
            self.assertEqual(window.overlays[2][0]['text'],'ข้อความไทย')
            window.changed=False;window.close()
