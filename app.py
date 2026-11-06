"""Local PDF page insertion. Requires PySide6 and PyMuPDF."""
import os
import sys
import tempfile
from pathlib import Path
import pymupdf
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QSpinBox, QFileDialog, QMessageBox, QListWidget, QListWidgetItem, QSplitter)


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
        self.main = self.extra = None
        self.setWindowTitle('แทรกหน้า PDF')
        self.resize(1100, 850)
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(28, 24, 28, 24)
        title = QLabel('แทรกหน้า PDF'); title.setStyleSheet('font-size:26px;font-weight:600')
        layout.addWidget(title)
        layout.addWidget(QLabel('เลือกเอกสารหลักและไฟล์ที่จะแทรก แล้วบันทึกเป็นไฟล์ใหม่'))
        self.labels = []
        for index, name in enumerate(('1. เลือก PDF หลัก', '2. เลือก PDF ที่จะแทรก')):
            button = QPushButton(name); button.clicked.connect(lambda checked=False, i=index: self.choose(i))
            layout.addWidget(button)
            label = QLabel('ยังไม่ได้เลือกไฟล์'); label.setWordWrap(True)
            layout.addWidget(label); self.labels.append(label)
        layout.addWidget(QLabel('3. คลิกรูปหน้าเอกสารเดิมที่ต้องการแทรกไว้ข้างหน้า หรือเลือกต่อท้าย'))
        row = QHBoxLayout()
        row.addWidget(QLabel('แทรกก่อนหน้าเดิม:'))
        self.position = QSpinBox(); self.position.setRange(1, 1)
        self.position.valueChanged.connect(self.preview); row.addWidget(self.position)
        append = QPushButton('ใส่ท้ายเอกสาร'); append.clicked.connect(lambda: self.position.setValue(self.position.maximum()))
        row.addWidget(append); layout.addLayout(row)
        split = QSplitter()
        self.pages = QListWidget(); self.pages.setMaximumWidth(210)
        self.pages.setIconSize(QSize(120, 160))
        self.pages.currentRowChanged.connect(lambda row: self.position.setValue(row + 1) if row >= 0 else None)
        split.addWidget(self.pages)
        self.pictures = []
        for caption in ('เอกสารเดิม: หน้านี้จะเลื่อนไปหลังไฟล์ที่แทรก', 'ไฟล์ที่จะแทรก: หน้าแรก'):
            panel = QWidget(); box = QVBoxLayout(panel)
            label = QLabel(caption); label.setWordWrap(True); box.addWidget(label)
            picture = QLabel('เลือกไฟล์เพื่อแสดงภาพเอกสาร'); picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
            picture.setMinimumSize(240, 280); box.addWidget(picture, 1)
            self.pictures.append(picture); split.addWidget(panel)
        self.picture = self.pictures[0]
        layout.addWidget(split, 1)
        self.summary = QLabel('เลือกเอกสารหลัก แล้วเลือกไฟล์ที่จะแทรก'); self.summary.setWordWrap(True)
        self.summary.setStyleSheet('padding:12px; background:#e2edf9; color:#163653; font-size:15px;')
        layout.addWidget(self.summary)
        self.save = QPushButton('บันทึก PDF เป็นไฟล์ใหม่'); self.save.setEnabled(False)
        self.save.clicked.connect(self.export); layout.addWidget(self.save)
        layout.addWidget(QLabel('ทำงานในเครื่อง • แทรกทุกหน้าของไฟล์ที่เลือก • ต้นฉบับยังอยู่ครบ'))

    def load_path(self, index, path):
        count = inspect_pdf(path)
        self.labels[index].setText(f'{path}\n{count} หน้า')
        if index == 0:
            self.main = path
            self.pages.blockSignals(True); self.pages.clear()
            with pymupdf.open(path) as doc:
                for number, page in enumerate(doc):
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(.18, .18), alpha=False)
                    image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
                    self.pages.addItem(QListWidgetItem(QIcon(QPixmap.fromImage(image)), f'หน้า {number + 1}'))
            self.pages.addItem('＋ ต่อท้ายเอกสาร')
            self.pages.blockSignals(False)
            self.position.setRange(1, count + 1)
        else: self.extra = path
        self.save.setEnabled(bool(self.main and self.extra)); self.preview()

    def choose(self, index):
        path, _ = QFileDialog.getOpenFileName(self, 'เลือก PDF', '', 'PDF (*.pdf)')
        if not path: return
        try: self.load_path(index, path)
        except Exception as error:
            QMessageBox.warning(self, 'เปิดไฟล์ไม่ได้', str(error))

    def show_page(self, label, path, number):
        with pymupdf.open(path) as doc:
            pix = doc[number].get_pixmap(matrix=pymupdf.Matrix(.8, .8), alpha=False)
            image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
            label.setPixmap(QPixmap.fromImage(image).scaled(350, 430, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))

    def preview(self):
        if not self.main: return
        try:
            count = inspect_pdf(self.main)
            index = self.position.value() - 1
            self.pages.blockSignals(True); self.pages.setCurrentRow(index); self.pages.blockSignals(False)
            if index == count:
                self.picture.setText('ใส่หลังหน้าสุดท้ายของเอกสาร')
            else:
                self.show_page(self.picture, self.main, index)
            if not self.extra:
                self.summary.setText('ขั้นตอนถัดไป: กด “2. เลือก PDF ที่จะแทรก” เพื่อเพิ่มเอกสาร')
                return
            added = inspect_pdf(self.extra)
            self.show_page(self.pictures[1], self.extra, 0)
            location = 'ท้ายเอกสาร' if index == count else f'ก่อนหน้าเดิม {index + 1} (หน้าเดิมจะเลื่อนไปหน้า {index + added + 1})'
            self.summary.setText(f'จะใส่ไฟล์ใหม่ {added} หน้า {location} → รวม {count + added} หน้า\nกดบันทึกด้านล่างเพื่อสร้างไฟล์ใหม่')
        except Exception as error:
            self.summary.setText(str(error))

    def export(self):
        suggestion = str(Path(self.main).with_name(Path(self.main).stem + '_แทรกหน้า.pdf'))
        path, _ = QFileDialog.getSaveFileName(self, 'บันทึกเป็นไฟล์ใหม่', suggestion, 'PDF (*.pdf)')
        if not path: return
        if not path.lower().endswith('.pdf'): path += '.pdf'
        try:
            count = insert_pdf(self.main, self.extra, self.position.value(), path)
            QMessageBox.information(self, 'เรียบร้อย', f'บันทึกแล้ว รวม {count} หน้า\n{path}')
        except Exception as error:
            QMessageBox.warning(self, 'บันทึกไม่สำเร็จ', str(error))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = Window()
    paths = sys.argv[1:]
    if not paths:
        paths = os.environ.get('NAUTILUS_SCRIPT_SELECTED_FILE_PATHS', '').splitlines()
    for index, path in enumerate(paths[:2]):
        try: window.load_path(index, str(Path(path).absolute()))
        except Exception as error:
            QMessageBox.warning(window, 'เปิดไฟล์ไม่ได้', str(error))
    if len(paths) > 2:
        QMessageBox.information(window, 'เลือกไฟล์', 'เปิดสองไฟล์แรกแล้ว: ไฟล์หลักและไฟล์ที่จะแทรก กรุณาตรวจสอบลำดับในหน้าต่าง')
    window.show()
    sys.exit(app.exec())
