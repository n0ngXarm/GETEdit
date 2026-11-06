"""Local PDF page insertion. Requires PySide6 and PyMuPDF."""
import os
import sys
import tempfile
from pathlib import Path
import pymupdf
from PySide6.QtCore import Qt, QSize, QEventLoop
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QSpinBox, QFileDialog, QMessageBox, QListWidget, QListWidgetItem, QSplitter, QComboBox)


def inspect_pdf(path):
    with pymupdf.open(path) as doc:
        if doc.needs_pass:
            raise ValueError('ไฟล์นี้มีรหัสผ่าน กรุณาใช้ไฟล์ที่ปลดล็อกแล้ว')
        if not doc.is_pdf or not len(doc):
            raise ValueError('กรุณาเลือกไฟล์ PDF ที่มีหน้าเอกสาร')
        return len(doc)


def insert_pdf(main, extra, before, output):
    main, extra, output = map(Path, (main, extra, output))
    if output.resolve() in (main.resolve(), extra.resolve()):
        raise ValueError('กรุณาบันทึกเป็นไฟล์ใหม่เพื่อเก็บต้นฉบับไว้')
    if output.exists():
        raise ValueError('ชื่อไฟล์นี้มีอยู่แล้ว กรุณาตั้งชื่อใหม่')
    n, added = inspect_pdf(main), inspect_pdf(extra)
    if not 1 <= before <= n + 1:
        raise ValueError('ตำแหน่งหน้าที่แทรกไม่ถูกต้อง')
    fd, temp = tempfile.mkstemp(suffix='.pdf', dir=output.parent)
    os.close(fd)
    try:
        with pymupdf.open(main) as doc, pymupdf.open(extra) as source:
            doc.insert_pdf(source, start_at=before - 1)
            doc.save(temp)
        with pymupdf.open(temp) as result:
            if len(result) != n + added:
                raise ValueError('จำนวนหน้าผลลัพธ์ไม่ถูกต้อง')
        # Exclusive creation prevents overwriting a file created while saving.
        with open(temp, 'rb') as source, open(output, 'xb') as destination:
            import shutil
            shutil.copyfileobj(source, destination)
        return n + added
    finally:
        os.unlink(temp)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.document = pymupdf.open()
        self.sources = set()
        self.changed = False
        self.setWindowTitle('GETEdit — รวมเอกสารเป็น PDF')
        self.resize(1050, 820)
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(22, 18, 22, 18)
        title = QLabel('รวมเอกสารเป็น PDF'); title.setStyleSheet('font-size:26px; font-weight:600')
        layout.addWidget(title)
        layout.addWidget(QLabel('กดเพิ่มไฟล์ → ตรวจหน้าที่รวมแล้ว → บันทึกเป็น PDF ใหม่'))
        row = QHBoxLayout()
        self.add = QPushButton('＋ เพิ่มไฟล์ (เลือกหลายไฟล์ได้)'); self.add.clicked.connect(self.choose)
        row.addWidget(self.add)
        self.placement = QComboBox()
        self.placement.addItems(['เพิ่มท้ายเอกสาร', 'เพิ่มก่อนหน้าที่เลือก', 'เพิ่มหลังหน้าที่เลือก'])
        row.addWidget(self.placement); layout.addLayout(row)
        layout.addWidget(QLabel('รองรับ PDF • รูปภาพ • Word / Excel / PowerPoint เมื่อมี LibreOffice'))
        split = QSplitter()
        self.pages = QListWidget(); self.pages.setIconSize(QSize(105, 145)); self.pages.setMaximumWidth(290)
        self.pages.currentRowChanged.connect(self.preview); split.addWidget(self.pages)
        panel = QWidget(); box = QVBoxLayout(panel)
        self.caption = QLabel('ตัวอย่างหน้าที่เลือก'); box.addWidget(self.caption)
        self.picture = QLabel('เริ่มต้นด้วยปุ่ม ＋ เพิ่มไฟล์ ด้านบน')
        self.picture.setAlignment(Qt.AlignmentFlag.AlignCenter); self.picture.setMinimumSize(300, 320)
        box.addWidget(self.picture, 1); split.addWidget(panel); layout.addWidget(split, 1)
        self.summary = QLabel('ยังไม่มีเอกสาร'); layout.addWidget(self.summary)
        self.save = QPushButton('บันทึกเป็น PDF ใหม่'); self.save.setEnabled(False)
        self.save.clicked.connect(self.export); layout.addWidget(self.save)
        layout.addWidget(QLabel('ทุกไฟล์จะกลายเป็นหน้า PDF • ต้นฉบับยังอยู่ครบ • ทำงานในเครื่อง'))

    def choose(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'เพิ่มไฟล์ — เลือกหลายไฟล์ได้', '',
            'ไฟล์ที่รองรับ (*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.doc *.docx *.odt *.rtf *.xls *.xlsx *.ods *.ppt *.pptx *.odp);;ทุกไฟล์ (*)')
        if paths: self.add_paths(paths)

    def add_paths(self, paths):
        from converter import convert_file
        cursor = self.pages.currentRow()
        mode = self.placement.currentIndex()
        position = len(self.document) if mode == 0 or cursor < 0 else cursor + (mode == 2)
        first = position
        errors = []
        self.add.setEnabled(False)
        self.save.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for path in paths:
                self.summary.setText('กำลังเพิ่ม: ' + Path(path).name)
                QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
                try:
                    data = convert_file(path)
                    with pymupdf.open(stream=data, filetype='pdf') as source:
                        self.document.insert_pdf(source, start_at=position)
                        position += len(source)
                    self.sources.add(Path(path).resolve()); self.changed = True
                except Exception as error:
                    errors.append(Path(path).name + ': ' + str(error))
            self.refresh(first)
        finally:
            QApplication.restoreOverrideCursor()
            self.add.setEnabled(True); self.save.setEnabled(bool(len(self.document)))
        if errors: QMessageBox.warning(self, 'บางไฟล์เพิ่มไม่ได้', '\n'.join(errors))

    def refresh(self, selected):
        self.pages.blockSignals(True); self.pages.clear()
        for number, page in enumerate(self.document):
            pix = page.get_pixmap(matrix=pymupdf.Matrix(.16, .16), alpha=False)
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            self.pages.addItem(QListWidgetItem(QIcon(QPixmap.fromImage(image)), f'หน้า {number+1}'))
        self.pages.blockSignals(False)
        self.pages.setCurrentRow(min(selected, len(self.document)-1))
        self.summary.setText(f'รวมแล้ว {len(self.document)} หน้า • ลำดับทางซ้ายคือลำดับในไฟล์ที่จะบันทึก')
        self.preview()

    def preview(self, *_):
        index = self.pages.currentRow()
        if index < 0: return
        pix = self.document[index].get_pixmap(matrix=pymupdf.Matrix(1, 1), alpha=False)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
        self.picture.setPixmap(QPixmap.fromImage(image).scaled(660, 490, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        self.caption.setText(f'หน้า {index+1} จาก {len(self.document)} — ตัวอย่างผลลัพธ์จริง')

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, 'บันทึกเป็น PDF ใหม่', 'GETEdit_รวมเอกสาร.pdf', 'PDF (*.pdf)')
        if not path: return
        if not path.lower().endswith('.pdf'): path += '.pdf'
        try:
            if Path(path).exists() or Path(path).resolve() in self.sources:
                raise ValueError('กรุณาใช้ชื่อไฟล์ใหม่ เพื่อเก็บต้นฉบับไว้')
            data = self.document.tobytes()
            with open(path, 'xb') as stream: stream.write(data)
            self.changed = False
            QMessageBox.information(self, 'บันทึกเรียบร้อย', f'รวม {len(self.document)} หน้า\n{path}')
        except Exception as error:
            QMessageBox.warning(self, 'บันทึกไม่สำเร็จ', str(error))

    def closeEvent(self, event):
        if self.changed and QMessageBox.question(self, 'ยังไม่ได้บันทึก', 'ปิดโดยไม่บันทึกเอกสารที่เพิ่มหรือไม่?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            event.ignore(); return
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv); app.setStyle('Fusion')
    window = Window(); window.show()
    paths = sys.argv[1:] or os.environ.get('NAUTILUS_SCRIPT_SELECTED_FILE_PATHS', '').splitlines()
    if paths: window.add_paths(paths)
    sys.exit(app.exec())
