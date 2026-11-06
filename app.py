"""Local PDF page insertion. Requires PySide6 and PyMuPDF."""
import os
import sys
import tempfile
from pathlib import Path
import pymupdf
from PySide6.QtCore import Qt, QSize, QEventLoop
from PySide6.QtGui import QImage, QPixmap, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QSpinBox, QFileDialog, QMessageBox, QListWidget, QListWidgetItem, QSplitter, QComboBox, QInputDialog)


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
        self.overlays = []
        self.active_page = -1
        self.changed = False
        self.setWindowTitle('GETEdit — จัดเอกสารและเพิ่มข้อความ / รูป')
        self.resize(1050, 820)
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(22, 18, 22, 18)
        title = QLabel('จัดเอกสาร • เพิ่มข้อความและรูป'); title.setStyleSheet('font-size:26px; font-weight:600')
        layout.addWidget(title)
        layout.addWidget(QLabel('เพิ่มไฟล์ → คลิกหน้า → เพิ่มข้อความ / รูป แล้วลากจัดวาง → บันทึก PDF ใหม่'))
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
        from editor import Canvas
        self.canvas = Canvas(); self.canvas.edited.connect(self.mark_edited)
        tools = QHBoxLayout()
        for label, callback in [('＋ ข้อความ', self.add_text), ('＋ รูป', self.add_image), ('＋ กล่อง', lambda:self.canvas.add_object('box')),
                ('แก้ข้อความ', self.edit_text), ('เล็กลง', lambda:self.canvas.scale_selected(.9)),
                ('ใหญ่ขึ้น',lambda:self.canvas.scale_selected(1.1)), ('หมุน',self.canvas.rotate_selected),
                ('ลบ',self.canvas.delete_selected), ('ย้อนกลับ',self.canvas.undo)]:
            button=QPushButton(label);button.clicked.connect(callback);tools.addWidget(button)
        box.addLayout(tools)
        box.addWidget(QLabel('คลิกสิ่งที่เพิ่มแล้วลากย้าย • เล็กลง/ใหญ่ขึ้นเพื่อปรับขนาด • Delete ลบ • Ctrl+Z ย้อนกลับ'))
        box.addWidget(self.canvas,1);split.addWidget(panel);layout.addWidget(split,1)
        from PySide6.QtGui import QShortcut, QKeySequence
        for key, callback in [('Delete',self.canvas.delete_selected),('Ctrl+Z',self.canvas.undo),('Ctrl+Shift+Z',self.canvas.redo)]:
            shortcut=QShortcut(QKeySequence(key),self.canvas);shortcut.activated.connect(callback)
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
        self.store_overlay()
        self.active_page = -1
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
                        self.overlays[position:position] = [[] for _ in source]
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

    def mark_edited(self):
        self.changed = True

    def store_overlay(self):
        if 0 <= self.active_page < len(self.overlays):
            self.overlays[self.active_page] = self.canvas.objects()

    def preview(self, *_):
        index = self.pages.currentRow()
        if index < 0 or index == self.active_page: return
        self.store_overlay()
        self.active_page = index
        self.canvas.load(self.document[index], self.overlays[index])
        self.caption.setText(f'หน้า {index+1} จาก {len(self.document)} — คลิกเพิ่มข้อความหรือรูปด้านล่าง')

    def add_text(self):
        if self.active_page < 0: return
        text, ok=QInputDialog.getMultiLineText(self,'เพิ่มข้อความ','ข้อความที่ต้องการวางบนหน้า:')
        if ok and text:self.canvas.add_object('text',text=text)

    def edit_text(self):
        items=self.canvas.selected()
        if len(items)!=1 or items[0].data['kind']!='text': return
        text,ok=QInputDialog.getMultiLineText(self,'แก้ข้อความที่เพิ่ม','ข้อความ:',items[0].data['text'])
        if ok:self.canvas.edit_text(text)

    def add_image(self):
        if self.active_page < 0: return
        path,_=QFileDialog.getOpenFileName(self,'เลือกรูปที่จะวางบนหน้า','','Images (*.png *.jpg *.jpeg *.bmp *.webp)')
        if path:
            data=Path(path).read_bytes()
            if QImage.fromData(data).isNull():
                QMessageBox.warning(self,'อ่านรูปไม่ได้','ไม่สามารถเปิดภาพนี้ได้');return
            self.canvas.add_object('image',image=data)

    def export_bytes(self):
        self.store_overlay()
        from editor import Canvas
        with pymupdf.open(stream=self.document.tobytes(),filetype='pdf') as result:
            canvas=Canvas()
            for index, states in enumerate(self.overlays):
                if not states:continue
                page=result[index]
                canvas.load(page,states)
                # Flatten only added objects; original PDF text and vectors remain.
                rotation=page.rotation
                page.set_rotation(0)
                page.insert_image(page.rect,stream=canvas.overlay_png(),rotate=(360-rotation)%360)
                page.set_rotation(rotation)
            return result.tobytes()

    def export(self):
        path, _ = QFileDialog.getSaveFileName(self, 'บันทึกเป็น PDF ใหม่', 'GETEdit_รวมเอกสาร.pdf', 'PDF (*.pdf)')
        if not path: return
        if not path.lower().endswith('.pdf'): path += '.pdf'
        try:
            if Path(path).exists() or Path(path).resolve() in self.sources:
                raise ValueError('กรุณาใช้ชื่อไฟล์ใหม่ เพื่อเก็บต้นฉบับไว้')
            data = self.export_bytes()
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
