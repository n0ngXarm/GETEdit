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

    def test_pointer_drag_and_escape_cancel(self):
        from PySide6.QtCore import Qt, QPoint
        from PySide6.QtTest import QTest
        self.window.show();self.app.processEvents()
        pages=self.window.pages;pages.setCurrentRow(0)
        source=pages.visualItemRect(pages.item(0)).center()
        rect=pages.visualItemRect(pages.item(2))
        target=QPoint(rect.right()-3,rect.center().y())
        QTest.mousePress(pages.viewport(),Qt.MouseButton.LeftButton,pos=source)
        QTest.mouseMove(pages.viewport(),source+QPoint(30,0))
        QTest.mouseMove(pages.viewport(),target)
        QTest.mouseRelease(pages.viewport(),Qt.MouseButton.LeftButton,pos=target)
        self.assertEqual(self.texts(),['TWO','THREE','ONE','FOUR'])
        self.window.undo()
        pages.setCurrentRow(0)
        source=pages.visualItemRect(pages.item(0)).center()
        QTest.mousePress(pages.viewport(),Qt.MouseButton.LeftButton,pos=source)
        QTest.mouseMove(pages.viewport(),source+QPoint(30,0))
        QTest.keyClick(pages,Qt.Key.Key_Escape)
        QTest.mouseRelease(pages.viewport(),Qt.MouseButton.LeftButton,pos=target)
        self.assertEqual(self.texts(),['ONE','TWO','THREE','FOUR'])

    def test_reading_layout_uses_compact_sidebar(self):
        self.window.resize(1920,1080);self.window.show()
        self.window.set_grid_view(False);self.app.processEvents()
        self.assertLessEqual(self.window.pages.width(),240)
        self.assertLess(self.window.pages.visualItemRect(self.window.pages.item(0)).height(),170)
        self.assertTrue(self.window.hint.isHidden())
        self.window.set_grid_view(True)
        self.assertTrue(self.window.hint.isHidden())

    def test_redo_and_new_change_clears_redo(self):
        self.window.pages.setCurrentRow(1);self.window.delete_pages()
        self.window.undo();self.window.redo()
        self.assertEqual(self.texts(),['ONE','THREE','FOUR'])
        self.window.undo()
        self.window.reorder_pages([3,0,1,2])
        self.window.redo()
        self.assertEqual(self.texts(),['FOUR','ONE','TWO','THREE'])
        self.assertFalse(self.window.forward.isEnabled())

    def test_redo_restores_saved_revision(self):
        self.window.reorder_pages([3,0,1,2])
        self.window.saved_revision=self.window.revision;self.window.changed=False
        self.window.undo();self.assertTrue(self.window.changed)
        self.window.redo();self.assertFalse(self.window.changed)

    def test_copy_paste_multiple_pages_and_undo(self):
        self.window.pages.clearSelection()
        for index in [0,2]:self.window.pages.item(index).setSelected(True)
        before=len(self.window.history)
        self.window.copy_pages()
        self.assertEqual(len(self.window.history),before)
        self.window.pages.setCurrentRow(1)
        self.window.paste_pages()
        self.assertEqual(self.texts(),['ONE','TWO','ONE','THREE','THREE','FOUR'])
        self.assertEqual(len(self.window.pages.selectedItems()),2)
        self.window.undo();self.assertEqual(self.texts(),['ONE','TWO','THREE','FOUR'])
        self.window.redo();self.assertEqual(self.texts(),['ONE','TWO','ONE','THREE','THREE','FOUR'])
        self.assertEqual(self.path.read_bytes(),self.original)

    def test_paste_into_empty_document_after_copy(self):
        self.window.pages.setCurrentRow(1);self.window.copy_pages()
        self.window.pages.selectAll();self.window.delete_pages()
        self.window.paste_pages()
        self.assertEqual(self.texts(),['TWO'])

    def test_clipboard_copy_process_exits_cleanly(self):
        import subprocess, sys
        environment=os.environ.copy();environment['QT_QPA_PLATFORM']='offscreen'
        script='from app import *; app=QApplication([]); w=Window(); w.document.new_page(); w.refresh(0); w.copy_pages(); w.changed=False; w.close()'
        result=subprocess.run([sys.executable,'-c',script],cwd=Path(__file__).resolve().parents[1],env=environment,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
