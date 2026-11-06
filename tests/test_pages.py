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

    def test_add_appends_and_undo(self):
        self.window.pages.setCurrentRow(1)
        self.window.add_paths([str(self.path)])
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'THREE', 'FOUR'] * 2)
        self.window.undo()
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'THREE', 'FOUR'])

    def test_reorder_export_delete_and_undo(self):
        self.window.reorder_pages([3, 0, 1, 2])
        self.assertEqual(self.texts(), ['FOUR', 'ONE', 'TWO', 'THREE'])
        with pymupdf.open(stream=self.window.export_bytes(), filetype='pdf') as doc:
            self.assertEqual([page.get_text().strip() for page in doc], self.texts())
        self.window.pages.setCurrentRow(0)
        self.window.delete_pages()
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'THREE'])
        self.window.undo(); self.window.undo()
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'THREE', 'FOUR'])
        self.assertEqual(self.path.read_bytes(), self.original)

    def test_drag_multiple_pages_to_end(self):
        self.window.pages.clearSelection()
        for index in [0, 2]: self.window.pages.item(index).setSelected(True)
        self.window.pages.move_selection(4)
        self.assertEqual(self.texts(), ['TWO', 'FOUR', 'ONE', 'THREE'])
        self.window.undo()
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'THREE', 'FOUR'])

    def test_noop_move_does_not_add_undo(self):
        before = len(self.window.history)
        self.window.reorder_pages([0, 1, 2, 3])
        self.assertEqual(len(self.window.history), before)

    def test_drop_event_moves_to_top(self):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QDropEvent
        pages = self.window.pages
        class InternalDrop(QDropEvent):
            def source(self): return pages
        self.window.show(); self.app.processEvents()
        pages.setCurrentRow(3)
        rect = pages.visualItemRect(pages.item(0))
        event = InternalDrop(QPointF(rect.left()+10, rect.top()+2),
            Qt.DropAction.MoveAction, pages.model().mimeData(pages.selectedIndexes()),
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        pages.dropEvent(event)
        self.assertTrue(event.isAccepted())
        self.assertEqual(self.texts(), ['FOUR', 'ONE', 'TWO', 'THREE'])
        self.window.undo()
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'THREE', 'FOUR'])

    def test_grid_layout_and_drop_across_columns(self):
        from PySide6.QtCore import QPointF, Qt
        from PySide6.QtGui import QDropEvent
        from PySide6.QtWidgets import QListView
        self.window.show(); self.app.processEvents()
        self.window.set_grid_view(True); self.app.processEvents()
        pages = self.window.pages
        self.assertEqual(pages.viewMode(), QListView.ViewMode.IconMode)
        first = pages.visualItemRect(pages.item(0))
        second = pages.visualItemRect(pages.item(1))
        self.assertEqual(first.top(), second.top())
        self.assertGreater(second.left(), first.left())
        pages.setCurrentRow(3)
        class InternalDrop(QDropEvent):
            def source(self): return pages
        event = InternalDrop(QPointF(second.right()-2, second.center().y()),
            Qt.DropAction.MoveAction, pages.model().mimeData(pages.selectedIndexes()),
            Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
        pages.dropEvent(event)
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'FOUR', 'THREE'])
        self.window.set_grid_view(False)
        self.assertEqual(pages.viewMode(), QListView.ViewMode.ListMode)
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'FOUR', 'THREE'])
        self.window.undo()
        self.assertEqual(self.texts(), ['ONE', 'TWO', 'THREE', 'FOUR'])
