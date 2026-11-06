"""Local PDF page insertion. Requires PySide6 and PyMuPDF."""
import os
import sys
import tempfile
from pathlib import Path
import pymupdf
from PySide6.QtCore import Qt, QSize, QEventLoop
from PySide6.QtGui import QImage, QPixmap, QIcon, QColor, QPainter
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox, QListWidget, QListWidgetItem, QSplitter, QComboBox, QGraphicsView, QGraphicsScene, QAbstractItemView)


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


class PageView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(QColor('#dfe4eb'))
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.setMinimumSize(300, 300)
        self.fit = True

    def show_page(self, page):
        self.scene().clear()
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5), alpha=False)
        image = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888).copy()
        self.scene().addPixmap(QPixmap.fromImage(image))
        self.scene().setSceneRect(0, 0, pix.width, pix.height)
        self.fit_page()

    def clear(self):
        self.scene().clear(); self.scene().setSceneRect(0, 0, 1, 1)

    def fit_page(self):
        self.fit = True
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom(self, factor):
        scale = self.transform().m11() * factor
        if .05 < scale < 8:
            self.fit = False; self.scale(factor, factor)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit: self.fit_page()


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.document = pymupdf.open()
        self.sources = set()
        self.history = []
        self.changed = False
        self.setWindowTitle('GETEdit — เพิ่มและลบหน้า PDF')
        self.resize(1120, 840)
        self.setStyleSheet("""
            QMainWindow {background:#eef1f5; color:#25354a;}
            QLabel {color:#25354a;}
            QPushButton {padding:9px 14px; border:1px solid #c5ceda; border-radius:4px; background:#ffffff; color:#25354a;}
            QPushButton:hover {background:#e3efff; border-color:#3275bd;}
            QPushButton:disabled {color:#8a96a6; background:#edf0f4;}
            QListWidget {background:white; border:1px solid #c5ceda; padding:6px;}
            QListWidget::item {padding:9px; border-bottom:1px solid #e3e8ef;}
            QListWidget::item:selected {background:#d9eaff; color:#153b68; border:1px solid #6c9bd0;}
            QComboBox {padding:8px; background:white; color:#25354a;}
        """)
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        heading = QLabel('  GETEdit   |   เพิ่มและลบหน้า PDF')
        heading.setStyleSheet('background:#205b97; color:white; font-size:19px; font-weight:600; padding:16px;')
        layout.addWidget(heading)
        ribbon = QWidget(); ribbon.setStyleSheet('background:#f7f9fc;')
        ribbon_layout = QHBoxLayout(ribbon); ribbon_layout.setContentsMargins(16,12,16,12)
        self.add = QPushButton('＋ เพิ่มไฟล์'); self.add.clicked.connect(self.choose)
        self.add.setStyleSheet('background:#205b97; color:white; font-weight:600; padding:13px 20px;')
        ribbon_layout.addWidget(self.add)
        placement_box = QVBoxLayout(); placement_box.addWidget(QLabel('ตำแหน่งที่เพิ่ม'))
        self.placement = QComboBox()
        self.placement.addItems(['ท้ายเอกสาร', 'ก่อนหน้าที่เลือก', 'หลังหน้าที่เลือก'])
        placement_box.addWidget(self.placement); ribbon_layout.addLayout(placement_box)
        self.remove = QPushButton('ลบหน้าที่เลือก'); self.remove.clicked.connect(self.delete_pages)
        ribbon_layout.addWidget(self.remove)
        self.back = QPushButton('↶ ย้อนกลับ'); self.back.clicked.connect(self.undo)
        ribbon_layout.addWidget(self.back); ribbon_layout.addStretch()
        self.save = QPushButton('บันทึก PDF ใหม่'); self.save.clicked.connect(self.export)
        ribbon_layout.addWidget(self.save); layout.addWidget(ribbon)
        hint = QLabel('  เพิ่มไฟล์เพื่อเริ่มต้น • คลิกรูปหน้าเพื่อดู • Ctrl / Shift เลือกหลายหน้า แล้วกดลบ')
        hint.setStyleSheet('padding:10px; border-bottom:1px solid #ccd5df; background:white;')
        layout.addWidget(hint)
        split = QSplitter()
        sidebar = QWidget(); left = QVBoxLayout(sidebar); left.setContentsMargins(12,12,6,12)
        left.addWidget(QLabel('หน้าเอกสาร'))
        self.pages = QListWidget(); self.pages.setIconSize(QSize(110,150))
        self.pages.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.pages.currentRowChanged.connect(self.preview)
        self.pages.itemSelectionChanged.connect(self.update_controls)
        left.addWidget(self.pages); split.addWidget(sidebar)
        panel=QWidget(); box=QVBoxLayout(panel);box.setContentsMargins(8,12,12,12)
        view_bar=QHBoxLayout();self.caption=QLabel('ยังไม่มีเอกสาร');view_bar.addWidget(self.caption);view_bar.addStretch()
        self.viewer=PageView()
        for text, callback in [('−',lambda:self.viewer.zoom(.8)), ('＋',lambda:self.viewer.zoom(1.25)), ('พอดีหน้า',self.viewer.fit_page)]:
            button=QPushButton(text);button.clicked.connect(callback);view_bar.addWidget(button)
        box.addLayout(view_bar);box.addWidget(self.viewer,1);split.addWidget(panel)
        split.setSizes([230,890]);layout.addWidget(split,1)
        self.summary=QLabel('  เริ่มต้น: กด ＋ เพิ่มไฟล์ หรือเปิดผ่านเมนู Scripts')
        self.summary.setStyleSheet('padding:12px; background:white; border-top:1px solid #ccd5df;')
        layout.addWidget(self.summary)
        from PySide6.QtGui import QShortcut, QKeySequence
        for key, callback in [('Delete',self.delete_pages),('Ctrl+Z',self.undo),('Ctrl+O',self.choose),('Ctrl+Shift+S',self.export)]:
            shortcut=QShortcut(QKeySequence(key),self);shortcut.activated.connect(callback)
        self.update_controls()

    def update_controls(self):
        self.remove.setEnabled(bool(self.pages.selectedItems()))
        self.save.setEnabled(bool(len(self.document)))
        self.back.setEnabled(bool(self.history))

    def snapshot(self):
        return (self.document.tobytes() if len(self.document) else None, set(self.sources), self.pages.currentRow(), self.changed)

    def remember(self, state):
        self.history.append(state)
        # Keep at most ten operations and 128 MB of PDF snapshots.
        while len(self.history)>10 or (len(self.history)>1 and sum(len(s[0] or b'') for s in self.history)>128*1024*1024):
            self.history.pop(0)

    def undo(self):
        if not self.history:return
        data, sources, selected, changed=self.history.pop()
        self.document.close()
        self.document=pymupdf.open(stream=data,filetype='pdf') if data else pymupdf.open()
        self.sources=sources;self.changed=changed
        self.refresh(selected)

    def delete_pages(self):
        indices=sorted(self.pages.row(item) for item in self.pages.selectedItems())
        if not indices:return
        self.remember(self.snapshot())
        if len(indices)==len(self.document):
            self.document.close();self.document=pymupdf.open()
        else:
            self.document.delete_pages(indices)
        self.changed=True
        self.refresh(min(indices[0],len(self.document)-1))

    def choose(self):
        paths,_=QFileDialog.getOpenFileNames(self,'เพิ่มไฟล์เป็นหน้าเอกสาร — เลือกหลายไฟล์ได้','','ไฟล์ที่รองรับ (*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.doc *.docx *.odt *.rtf *.xls *.xlsx *.ods *.ppt *.pptx *.odp);;ทุกไฟล์ (*)')
        if paths:self.add_paths(paths)

    def add_paths(self, paths):
        from converter import convert_file
        cursor=self.pages.currentRow();mode=self.placement.currentIndex()
        position=len(self.document) if mode==0 or cursor<0 else cursor+(mode==2)
        first=position; state=self.snapshot(); errors=[];added=False
        self.centralWidget().setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for path in paths:
                self.summary.setText('กำลังเพิ่ม: '+Path(path).name)
                QApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents)
                try:
                    data=convert_file(path)
                    with pymupdf.open(stream=data,filetype='pdf') as source:
                        self.document.insert_pdf(source,start_at=position);position+=len(source)
                    self.sources.add(Path(path).resolve());self.changed=True;added=True
                except Exception as error:errors.append(Path(path).name+': '+str(error))
            if added:self.remember(state)
            self.refresh(first)
        finally:
            QApplication.restoreOverrideCursor();self.centralWidget().setEnabled(True);self.update_controls()
        if errors:QMessageBox.warning(self,'บางไฟล์เพิ่มไม่ได้','\n'.join(errors))

    def refresh(self, selected):
        self.pages.blockSignals(True);self.pages.clear()
        for number,page in enumerate(self.document):
            pix=page.get_pixmap(matrix=pymupdf.Matrix(.18,.18),alpha=False)
            image=QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
            self.pages.addItem(QListWidgetItem(QIcon(QPixmap.fromImage(image)),f'หน้า {number+1}'))
        self.pages.setCurrentRow(max(0,min(selected,len(self.document)-1)) if len(self.document) else -1)
        self.pages.blockSignals(False)
        self.summary.setText(f'  ทั้งหมด {len(self.document)} หน้า  |  ลำดับทางซ้ายคือลำดับที่จะบันทึก  |  เก็บไฟล์ต้นฉบับไว้ครบ')
        self.preview();self.update_controls()

    def preview(self,*_):
        index=self.pages.currentRow()
        if index<0:
            self.viewer.clear();self.caption.setText('กด ＋ เพิ่มไฟล์ เพื่อเพิ่มหน้าเอกสาร');return
        self.viewer.show_page(self.document[index])
        self.caption.setText(f'หน้า {index+1} จาก {len(self.document)}')

    def export_bytes(self):
        if not len(self.document):raise ValueError('เพิ่มหน้าเอกสารก่อนบันทึก')
        return self.document.tobytes()

    def export(self):
        if not len(self.document):return
        path,_=QFileDialog.getSaveFileName(self,'บันทึก PDF เป็นไฟล์ใหม่','GETEdit_จัดหน้า.pdf','PDF (*.pdf)')
        if not path:return
        if not path.lower().endswith('.pdf'):path+='.pdf'
        try:
            if Path(path).exists() or Path(path).resolve() in self.sources:raise ValueError('กรุณาใช้ชื่อไฟล์ใหม่ เพื่อเก็บต้นฉบับไว้')
            data=self.export_bytes()
            with open(path,'xb') as stream:stream.write(data)
            self.changed=False
            QMessageBox.information(self,'บันทึกเรียบร้อย',f'บันทึกแล้ว {len(self.document)} หน้า\n{path}')
        except Exception as error:QMessageBox.warning(self,'บันทึกไม่สำเร็จ',str(error))

    def closeEvent(self,event):
        if self.changed and QMessageBox.question(self,'ยังไม่ได้บันทึก','ปิดโดยไม่บันทึกการเพิ่ม/ลบหน้าหรือไม่?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
            event.ignore();return
        event.accept()


if __name__=='__main__':
    app=QApplication(sys.argv);app.setStyle('Fusion')
    window=Window();window.show()
    paths=sys.argv[1:] or os.environ.get('NAUTILUS_SCRIPT_SELECTED_FILE_PATHS','').splitlines()
    if paths:window.add_paths(paths)
    sys.exit(app.exec())
