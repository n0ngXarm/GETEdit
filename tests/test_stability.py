import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from app import QApplication, Window, insert_pdf, pymupdf


class StabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.source = self.root/'source.pdf'
        with pymupdf.open() as doc:
            for text in ['ONE', 'TWO']:
                doc.new_page().insert_text((60,60),text)
            doc.save(self.source)
        self.window = Window(); self.window.add_paths([str(self.source)])

    def tearDown(self):
        self.window.changed = False; self.window.close(); self.tmp.cleanup()

    def save(self, name):
        with patch('app.QFileDialog.getSaveFileName', return_value=(str(self.root/name), 'PDF')), patch('app.QMessageBox.information'):
            self.window.export()

    def test_undo_after_save_must_warn_about_unsaved_changes(self):
        self.save('first.pdf')
        self.window.reorder_pages([1,0])
        self.save('second.pdf')
        self.window.undo()
        self.assertTrue(self.window.changed, 'Undo changed the saved order, so closing must warn')

    def test_failed_write_does_not_leave_partial_pdf(self):
        target = self.root/'output.pdf'
        def disk_full(source, destination):
            destination.write(b'incomplete')
            raise OSError('disk full')
        with patch('shutil.copyfileobj', side_effect=disk_full):
            with self.assertRaises(OSError):
                insert_pdf(self.source,self.source,2,target)
        self.assertFalse(target.exists(), 'Failed save must not leave a broken final file')

    def test_failed_import_keeps_existing_pages_and_history(self):
        before = self.window.export_bytes(); history = len(self.window.history)
        broken = self.root/'broken.pdf'; broken.write_bytes(b'not a pdf')
        with patch('app.QMessageBox.warning'):
            self.window.add_paths([str(broken)])
        self.assertEqual([p.get_text() for p in self.window.document], ['ONE\n', 'TWO\n'])
        self.assertEqual(len(self.window.history),history)

    def test_render_large_page_is_bounded(self):
        from app import PageView
        with pymupdf.open() as doc:
            page=doc.new_page(width=12000,height=12000)
            original=pymupdf.Page.get_pixmap
            scales=[]
            def track(page, **kwargs):
                scales.append(kwargs['matrix'].a)
                # Render a tiny fixture to avoid allocating current unbounded output.
                return original(page, matrix=pymupdf.Matrix(.001,.001),alpha=False)
            with patch.object(pymupdf.Page,'get_pixmap',track):
                PageView().show_page(page)
            self.assertLessEqual(scales[0]*12000,2048)

    def test_save_race_keeps_existing_destination(self):
        from storage import write_new_file
        target=self.root/'race.pdf'
        def competing_write(source,destination):
            target.write_bytes(b'other process')
            raise FileExistsError('destination created concurrently')
        with patch('storage.os.link',side_effect=competing_write):
            with self.assertRaises(FileExistsError):write_new_file(target,b'new data')
        self.assertEqual(target.read_bytes(),b'other process')
        self.assertFalse(list(self.root.glob('.getedit-*.tmp')))

    def test_export_failure_keeps_dirty_state_and_no_partial_output(self):
        with patch('app.QFileDialog.getSaveFileName',return_value=(str(self.root/'failed.pdf'),'PDF')), patch('app.QMessageBox.warning'), patch('storage.os.fsync',side_effect=OSError('disk full')):
            self.window.export()
        self.assertTrue(self.window.changed)
        self.assertFalse((self.root/'failed.pdf').exists())
        self.assertFalse(list(self.root.glob('.getedit-*.tmp')))
