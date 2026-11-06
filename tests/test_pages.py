import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import unittest
from pathlib import Path
from app import QApplication, Window, pymupdf


class PageManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'ต้นฉบับ.pdf'
        with pymupdf.open() as doc:
            for text in ['ONE', 'TWO', 'THREE', 'FOUR']:
                page = doc.new_page(); page.insert_text((60, 60), text)
            doc.save(self.path)
        self.original = self.path.read_bytes()
        self.window = Window(); self.window.add_paths([str(self.path)])

    def tearDown(self):
        self.window.changed = False; self.window.close(); self.tmp.cleanup()

    def texts(self):
        return [page.get_text().strip() for page in self.window.document]

    def test_delete_selected_pages_and_undo(self):
        self.window.pages.clearSelection()
        for index in [1, 3]: self.window.pages.item(index).setSelected(True)
        self.window.delete_pages()
        self.assertEqual(self.texts(), ['ONE', 'THREE'])
        self.window.undo()
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'THREE', 'FOUR'])
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_delete_all_then_undo_and_export(self):
        self.window.pages.selectAll(); self.window.delete_pages()
        self.assertEqual(len(self.window.document), 0)
        self.assertFalse(self.window.save.isEnabled())
        self.window.undo()
        with pymupdf.open(stream=self.window.export_bytes(), filetype='pdf') as doc:
            self.assertEqual(len(doc), 4)
            self.assertEqual(doc[0].get_text().strip(), 'ONE')

    def test_add_before_and_undo(self):
        self.window.pages.setCurrentRow(1)
        self.window.placement.setCurrentIndex(1)
        self.window.add_paths([str(self.path)])
        self.assertEqual(self.texts(), ['ONE', 'ONE', 'TWO', 'THREE', 'FOUR', 'TWO', 'THREE', 'FOUR'])
        self.window.undo()
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'THREE', 'FOUR'])
