import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import QTimer
from PySide6.QtTest import QTest
from app import QApplication, Window, pymupdf


class ImportUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app=QApplication.instance() or QApplication([])

    def test_large_document_thumbnails_are_lazy(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'large.pdf'
            with pymupdf.open() as doc:
                for _ in range(300): doc.new_page()
                doc.save(path)
            window=Window();window.add_paths([str(path)])
            ready=sum(not window.pages.item(i).icon().isNull() for i in range(300))
            self.assertLess(ready,60,'Opening a document must not render all 300 thumbnails synchronously')
            window.changed=False;window.close()

    def test_async_import_keeps_event_loop_responsive(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.pdf'
            with pymupdf.open() as doc:
                doc.new_page().insert_text((60,60),'IMPORTED');doc.save(path)
            broken=Path(folder)/'broken.pdf';broken.write_bytes(b'broken')
            window=Window();beats=[]
            timer=QTimer();timer.setInterval(5);timer.timeout.connect(lambda:beats.append(1));timer.start()
            with patch('app.QMessageBox.warning') as warning:
                window.begin_import([str(path),str(broken)])
                self.assertTrue(window.busy)
                deadline=time.monotonic()+15
                while window.busy and time.monotonic()<deadline:QTest.qWait(10)
                self.assertFalse(window.busy)
                self.assertEqual(len(window.document),1)
                self.assertIn('IMPORTED',window.document[0].get_text())
                self.assertTrue(warning.called)
            timer.stop();self.assertGreater(len(beats),1)
            window.undo();self.assertEqual(len(window.document),0)
            window.changed=False;window.close()

    def test_worker_failure_preserves_current_document(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'source.pdf'
            with pymupdf.open() as doc:
                doc.new_page().insert_text((60,60),'KEEP');doc.save(path)
            window=Window();window.add_paths([str(path)])
            with patch('app.QMessageBox.warning'):
                window.begin_import([str(path)])
                window.cancel_import()
                deadline=time.monotonic()+10
                while window.busy and time.monotonic()<deadline:QTest.qWait(10)
            self.assertFalse(window.busy)
            self.assertEqual(len(window.document),1)
            self.assertIn('KEEP',window.document[0].get_text())
            window.changed=False;window.close()

    def test_missing_python_releases_busy_state(self):
        window=Window()
        with patch('app.QMessageBox.warning'), patch('app.sys.executable','/nonexistent/getedit-python'):
            window.begin_import(['does-not-matter.pdf'])
            deadline=time.monotonic()+5
            while window.busy and time.monotonic()<deadline:QTest.qWait(10)
        self.assertFalse(window.busy)
        self.assertTrue(window.add.isEnabled())
        window.changed=False;window.close()

    def test_synchronous_failed_start_releases_state(self):
        from app import QProcess
        window=Window()
        def immediate_failure(job,*args):
            job.errorOccurred.emit(QProcess.ProcessError.FailedToStart)
        with patch('app.QMessageBox.warning'),patch.object(QProcess,'start',immediate_failure):
            window.begin_import(['ignored.pdf'])
        self.assertFalse(window.busy)
        self.assertIsNone(window.import_job)
        self.assertTrue(window.add.isEnabled())
        window.changed=False;window.close()
