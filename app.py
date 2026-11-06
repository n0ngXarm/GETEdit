# SPDX-License-Identifier: AGPL-3.0-only
"""Local PDF page insertion. Requires PySide6 and PyMuPDF."""
import os
import sys
import json
import tempfile
from pathlib import Path
import pymupdf
from storage import write_new_file

__version__ = "1.0.1"
from PySide6.QtCore import Qt, QSize, Signal, QTimer, QProcess
from PySide6.QtGui import QImage, QPixmap, QIcon, QColor, QPainter, QPen
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox, QListWidget, QListWidgetItem, QSplitter, QGraphicsView, QGraphicsScene, QAbstractItemView, QListView)


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
    with pymupdf.open(main) as doc, pymupdf.open(extra) as source:
        doc.insert_pdf(source, start_at=before - 1)
        data = doc.tobytes()
    with pymupdf.open(stream=data, filetype='pdf') as result:
        if len(result) != n + added:
            raise ValueError('จำนวนหน้าผลลัพธ์ไม่ถูกต้อง')
    write_new_file(output, data)
    return n + added


class PageList(QListWidget):
    orderRequested = Signal(list, int)
    viewportChanged = Signal()

    def __init__(self):
        super().__init__()
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setDropIndicatorShown(True)
        self.setDragDropOverwriteMode(False)
        self.setAutoScroll(True)
        self.setToolTip('กดค้างที่รูปหน้า แล้วลากเพื่อย้ายลำดับ')
        self.press_position = None
        self.drag_position = None
        self.dragging = False
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.scroll_timer = QTimer(self); self.scroll_timer.setInterval(40)
        self.scroll_timer.timeout.connect(self.scroll_while_dragging)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.viewportChanged.emit()

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button()==Qt.MouseButton.LeftButton and self.indexAt(event.position().toPoint()).isValid():
            self.press_position=event.position().toPoint()

    def mouseMoveEvent(self, event):
        if self.press_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            position=event.position().toPoint()
            if not self.dragging and (position-self.press_position).manhattanLength()>=QApplication.startDragDistance():
                self.dragging=True;self.setCursor(Qt.CursorShape.ClosedHandCursor);self.scroll_timer.start()
            if self.dragging:
                self.drag_position=position;self.viewport().update()
            event.accept();return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        dragging=self.dragging
        destination=self.destination_at(event.position().toPoint()) if dragging else None
        self.reset_drag()
        if dragging:
            self.move_selection(destination);event.accept();return
        super().mouseReleaseEvent(event)

    def reset_drag(self):
        self.press_position=None;self.drag_position=None;self.dragging=False
        self.scroll_timer.stop();self.unsetCursor();self.viewport().update()

    def keyPressEvent(self, event):
        if event.key()==Qt.Key.Key_Escape and self.dragging:
            self.reset_drag();event.accept();return
        super().keyPressEvent(event)

    def scroll_while_dragging(self):
        if self.drag_position is None:return
        y=self.drag_position.y();bar=self.verticalScrollBar()
        step=-24 if y<32 else 24 if y>self.viewport().height()-32 else 0
        if step:bar.setValue(bar.value()+step);self.viewport().update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.dragging or self.drag_position is None or not self.count():return
        destination=self.destination_at(self.drag_position)
        row=min(destination,self.count()-1);rect=self.visualItemRect(self.item(row))
        painter=QPainter(self.viewport());painter.setPen(QPen(QColor('#1174d0'),3))
        if self.viewMode()==QListView.ViewMode.IconMode:
            x=rect.left() if destination<self.count() else rect.right()
            painter.drawLine(x,rect.top(),x,rect.bottom())
        else:
            y=rect.top() if destination<self.count() else rect.bottom()
            painter.drawLine(rect.left(),y,rect.right(),y)

    def move_selection(self, destination):
        selected = sorted(self.row(item) for item in self.selectedItems())
        if not selected: return
        remaining = [row for row in range(self.count()) if row not in selected]
        insertion = destination - sum(row < destination for row in selected)
        order = remaining[:insertion] + selected + remaining[insertion:]
        self.orderRequested.emit(order, insertion)

    def destination_at(self, position):
        target = self.indexAt(position)
        if target.isValid():
            rect = self.visualRect(target)
            after = position.x() >= rect.center().x() if self.viewMode() == QListView.ViewMode.IconMode else position.y() >= rect.center().y()
            destination = target.row() + after
        elif self.count() and self.viewMode() == QListView.ViewMode.IconMode:
            # Gaps between tiles still belong to the nearest row/column.
            def distance(row):
                rect = self.visualItemRect(self.item(row))
                dx = max(rect.left()-position.x(), 0, position.x()-rect.right())
                dy = max(rect.top()-position.y(), 0, position.y()-rect.bottom())
                return dx*dx + dy*dy
            row = min(range(self.count()), key=distance)
            rect = self.visualItemRect(self.item(row))
            destination = row + (position.y() > rect.bottom() or position.x() >= rect.center().x())
        else:
            destination = self.count()
        return destination

    def dropEvent(self, event):
        if event.source() is not self:
            event.ignore();return
        self.move_selection(self.destination_at(event.position().toPoint()))
        event.setDropAction(Qt.DropAction.MoveAction);event.accept()


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
        scale = min(1.5, 2048 / max(page.rect.width, page.rect.height, 1))
        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
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
        self.busy = False
        self.import_job = None
        self.import_folder = None
        self.close_after_import = False
        self.changed = False
        self.revision = self.saved_revision = self.serial = 0
        self.setWindowTitle(f'GETEdit {__version__} — จัดหน้า PDF')
        self.resize(1120, 840)
        self.setStyleSheet("""
            QMainWindow {background:#eef1f5; color:#25354a;}
            QLabel {color:#25354a;}
            QPushButton {padding:5px 10px; border:1px solid #c5ceda; border-radius:4px; background:#ffffff; color:#25354a;}
            QPushButton:hover {background:#e3efff; border-color:#3275bd;}
            QPushButton:checked {background:#d9eaff; border-color:#3275bd; color:#153b68;}
            QPushButton:disabled {color:#8a96a6; background:#edf0f4;}
            QListWidget {background:white; border:1px solid #c5ceda; padding:3px;}
            QListWidget::item {padding:4px; border-bottom:1px solid #e3e8ef;}
            QListWidget::item:selected {background:#d9eaff; color:#153b68; border:1px solid #6c9bd0;}
        """)
        root = QWidget(); self.setCentralWidget(root)
        layout = QVBoxLayout(root); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        ribbon = QWidget(); ribbon.setStyleSheet('background:#f7f9fc;')
        ribbon_layout = QHBoxLayout(ribbon); ribbon_layout.setContentsMargins(8,6,8,6)
        self.add = QPushButton('เพิ่มไฟล์…'); self.add.clicked.connect(self.choose)
        self.add.setStyleSheet('background:#205b97; color:white; font-weight:600; padding:6px 14px;')
        ribbon_layout.addWidget(self.add)
        self.remove = QPushButton('ลบหน้า'); self.remove.clicked.connect(self.delete_pages)
        ribbon_layout.addWidget(self.remove)
        self.back = QPushButton('เลิกทำ'); self.back.clicked.connect(self.undo)
        ribbon_layout.addWidget(self.back); ribbon_layout.addStretch()
        self.grid_button = QPushButton('ดูทุกหน้า')
        self.detail_button = QPushButton('อ่านทีละหน้า')
        for button in (self.grid_button, self.detail_button): button.setCheckable(True)
        self.grid_button.clicked.connect(lambda: self.set_grid_view(True))
        self.detail_button.clicked.connect(lambda: self.set_grid_view(False))
        ribbon_layout.addWidget(self.grid_button); ribbon_layout.addWidget(self.detail_button)
        self.save = QPushButton('บันทึกเป็น…'); self.save.clicked.connect(self.export)
        ribbon_layout.addWidget(self.save); layout.addWidget(ribbon)
        self.hint = QLabel()
        self.hint.setStyleSheet('padding:4px 8px; border-bottom:1px solid #ccd5df; background:white;')
        layout.addWidget(self.hint)
        split = QSplitter(); self.split = split
        sidebar = QWidget(); self.sidebar=sidebar; left = QVBoxLayout(sidebar); left.setContentsMargins(6,6,3,6)
        left.addWidget(QLabel('หน้าเอกสาร'))
        self.pages = PageList(); self.pages.setIconSize(QSize(110,150))
        self.pages.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.pages.orderRequested.connect(self.reorder_pages)
        self.pages.currentRowChanged.connect(self.preview)
        self.pages.itemDoubleClicked.connect(lambda *_: self.set_grid_view(False))
        self.pages.itemSelectionChanged.connect(self.update_controls)
        self.thumb_ready = set()
        self.thumb_timer = QTimer(self); self.thumb_timer.setSingleShot(True)
        self.thumb_timer.timeout.connect(self.render_thumbnails)
        self.pages.verticalScrollBar().valueChanged.connect(self.schedule_thumbnails)
        self.pages.viewportChanged.connect(self.schedule_thumbnails)
        left.addWidget(self.pages); split.addWidget(sidebar)
        panel=QWidget(); self.detail_panel=panel; box=QVBoxLayout(panel);box.setContentsMargins(4,6,6,6)
        view_bar=QHBoxLayout();self.caption=QLabel('ยังไม่มีเอกสาร');view_bar.addWidget(self.caption);view_bar.addStretch()
        self.viewer=PageView()
        for text, callback in [('−',lambda:self.viewer.zoom(.8)), ('＋',lambda:self.viewer.zoom(1.25)), ('พอดีหน้าต่าง',self.viewer.fit_page)]:
            button=QPushButton(text);button.clicked.connect(callback);view_bar.addWidget(button)
        box.addLayout(view_bar);box.addWidget(self.viewer,1);split.addWidget(panel)
        split.setSizes([230,890]);layout.addWidget(split,1)
        self.summary=QLabel('  กด “เพิ่มไฟล์…” เพื่อเริ่มจัดหน้า')
        self.summary.setStyleSheet('padding:4px 8px; background:white; border-top:1px solid #ccd5df;')
        layout.addWidget(self.summary)
        from PySide6.QtGui import QShortcut, QKeySequence
        for key, callback in [('Delete',self.delete_pages),('Ctrl+Z',self.undo),('Ctrl+O',self.choose),('Ctrl+Shift+S',self.export)]:
            shortcut=QShortcut(QKeySequence(key),self);shortcut.activated.connect(callback)
        self.set_grid_view(True)
        self.update_controls()

    def set_grid_view(self, enabled):
        self.grid_button.setChecked(enabled); self.detail_button.setChecked(not enabled)
        self.detail_panel.setVisible(not enabled)
        self.sidebar.setMinimumWidth(160)
        self.sidebar.setMaximumWidth(16777215 if enabled else 228)
        self.hint.setText('ลากรูปย่อเพื่อจัดลำดับ • ดับเบิลคลิกเพื่ออ่าน • Ctrl / Shift เลือกหลายหน้า' if enabled else 'คลิกรูปย่อด้านซ้ายเพื่อเปลี่ยนหน้า • ลากเพื่อย้าย • กด “ดูทุกหน้า” เพื่อจัดเรียงแบบตาราง')
        if enabled:
            self.pages.setViewMode(QListView.ViewMode.IconMode)
            self.pages.setFlow(QListView.Flow.LeftToRight)
            self.pages.setWrapping(True)
            self.pages.setResizeMode(QListView.ResizeMode.Adjust)
            self.pages.setIconSize(QSize(125,165))
            self.pages.setGridSize(QSize(150,self.grid_height()))
        else:
            self.pages.setViewMode(QListView.ViewMode.ListMode)
            self.pages.setFlow(QListView.Flow.TopToBottom)
            self.pages.setWrapping(False)
            self.pages.setIconSize(QSize(110,150))
            self.pages.setGridSize(QSize())
            self.split.setSizes([210,max(300,self.width()-210)])
        self.pages.setMovement(QListView.Movement.Static)
        self.pages.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop)
        self.size_page_items()
        self.pages.doItemsLayout()
        if not enabled: self.preview()
        self.schedule_thumbnails()

    def grid_height(self):
        heights=[min(165,125*page.rect.height/max(page.rect.width,1)) for page in self.document]
        return max(106,int(max(heights,default=150))+26)

    def size_page_items(self):
        grid=self.grid_button.isChecked()
        if grid:self.pages.setGridSize(QSize(150,self.grid_height()))
        grid_height=self.grid_height() if grid else 0
        for number,page in enumerate(self.document):
            height=min(145,110*page.rect.height/max(page.rect.width,1))
            self.pages.item(number).setSizeHint(QSize(140,grid_height if grid else max(68,int(height)+10)))

    def status_text(self):
        return f'{len(self.document)} หน้า • ไฟล์ต้นฉบับไม่เปลี่ยนแปลง'

    def update_controls(self):
        self.remove.setEnabled(not self.busy and bool(self.pages.selectedItems()))
        self.save.setEnabled(not self.busy and bool(len(self.document)))
        self.back.setEnabled(not self.busy and bool(self.history))

    def mark_changed(self):
        self.serial += 1
        self.revision = self.serial
        self.changed = self.revision != self.saved_revision

    def snapshot(self):
        return (self.document.tobytes() if len(self.document) else None, set(self.sources), self.pages.currentRow(), self.revision)

    def remember(self, state):
        self.history.append(state)
        # Keep at most ten operations and 128 MB of PDF snapshots.
        while len(self.history)>10 or (len(self.history)>1 and sum(len(s[0] or b'') for s in self.history)>128*1024*1024):
            self.history.pop(0)

    def undo(self):
        if self.busy or not self.history:return
        data, sources, selected, revision=self.history.pop()
        self.document.close()
        self.document=pymupdf.open(stream=data,filetype='pdf') if data else pymupdf.open()
        self.sources=sources;self.revision=revision
        self.changed = self.revision != self.saved_revision
        self.refresh(selected)

    def reorder_pages(self, order, selected=0):
        if self.busy or order == list(range(len(self.document))): return
        if sorted(order) != list(range(len(self.document))):
            raise ValueError('ลำดับหน้าไม่ถูกต้อง')
        state = self.snapshot()
        self.document.select(order)
        self.remember(state)
        self.mark_changed()
        self.refresh(selected)

    def delete_pages(self):
        if self.busy:return
        indices=sorted(self.pages.row(item) for item in self.pages.selectedItems())
        if not indices:return
        self.remember(self.snapshot())
        if len(indices)==len(self.document):
            self.document.close();self.document=pymupdf.open()
        else:
            self.document.delete_pages(indices)
        self.mark_changed()
        self.refresh(min(indices[0],len(self.document)-1))

    def choose(self):
        if self.busy:return
        paths,_=QFileDialog.getOpenFileNames(self,'เพิ่มไฟล์เป็นหน้าเอกสาร — เลือกหลายไฟล์ได้','','ไฟล์ที่รองรับ (*.pdf *.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp *.doc *.docx *.odt *.rtf *.xls *.xlsx *.ods *.ppt *.pptx *.odp);;ทุกไฟล์ (*)')
        if paths:self.begin_import(paths)

    def add_paths(self, paths):
        if self.busy:return
        from converter import convert_file
        position=len(self.document)
        first=position; state=self.snapshot(); errors=[];added=False
        self.centralWidget().setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for path in paths:
                self.summary.setText('กำลังเพิ่ม: '+Path(path).name)
                try:
                    data=convert_file(path)
                    with pymupdf.open(stream=data,filetype='pdf') as source:
                        self.document.insert_pdf(source,start_at=position);position+=len(source)
                    self.sources.add(Path(path).resolve());added=True
                except Exception as error:errors.append(Path(path).name+': '+str(error))
            if added:
                self.remember(state)
                self.mark_changed()
            self.refresh(first)
        finally:
            QApplication.restoreOverrideCursor();self.centralWidget().setEnabled(True);self.update_controls()
        if errors:QMessageBox.warning(self,'บางไฟล์เพิ่มไม่ได้','\n'.join(errors))

    def refresh(self, selected):
        self.thumb_timer.stop();self.thumb_ready.clear()
        self.pages.blockSignals(True);self.pages.clear()
        for number in range(len(self.document)):
            item=QListWidgetItem(f'หน้า {number+1}')
            item.setSizeHint(QSize(140,190));self.pages.addItem(item)
        self.pages.setCurrentRow(max(0,min(selected,len(self.document)-1)) if len(self.document) else -1)
        self.pages.blockSignals(False)
        self.size_page_items()
        self.summary.setText(self.status_text())
        self.preview();self.update_controls();self.schedule_thumbnails()

    def schedule_thumbnails(self,*_):
        if not self.busy:self.thumb_timer.start(0)

    def render_thumbnails(self):
        if self.busy:return
        viewport=self.pages.viewport().rect().adjusted(0,-205,0,205)
        pending=[i for i in range(self.pages.count()) if i not in self.thumb_ready and self.pages.visualItemRect(self.pages.item(i)).intersects(viewport)]
        for number in pending[:4]:
            try:
                page=self.document[number]
                scale=min(125/max(page.rect.width,1),165/max(page.rect.height,1))
                pix=page.get_pixmap(matrix=pymupdf.Matrix(scale,scale),alpha=False)
                image=QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
                self.pages.item(number).setIcon(QIcon(QPixmap.fromImage(image)))
            except Exception:
                self.pages.item(number).setToolTip('แสดงภาพย่อไม่ได้ ลองเปิดหน้าใหญ่เพื่อตรวจสอบ')
            self.thumb_ready.add(number)
        if len(pending)>4:self.thumb_timer.start(0)

    def begin_import(self, paths):
        if self.busy or not paths:return
        self.busy=True;self.thumb_timer.stop();self.centralWidget().setEnabled(False)
        self.summary.setText('กำลังเตรียมหน้าเอกสาร…')
        self.import_paths=[str(Path(p).resolve()) for p in paths]
        self.import_output = ""
        self.import_folder=tempfile.TemporaryDirectory(prefix='getedit-import-',ignore_cleanup_errors=True)
        self.import_job=QProcess(self)
        self.import_job.readyReadStandardOutput.connect(self.import_progress)
        self.import_job.finished.connect(self.finish_import)
        self.import_job.errorOccurred.connect(self.import_error)
        self.import_timeout=QTimer(self);self.import_timeout.setSingleShot(True)
        self.import_timeout.timeout.connect(self.cancel_import)
        self.import_timeout.start(180000)
        request=json.dumps({'paths':self.import_paths,'directory':self.import_folder.name}).encode('utf-8')
        job=self.import_job
        # Windows may emit FailedToStart synchronously from start(). Send only
        # after started, without dereferencing fields cleaned up by that signal.
        job.started.connect(lambda:self.send_import_request(job,request))
        job.start(sys.executable,[str(Path(__file__).with_name('import_worker.py'))])
        self.update_controls()

    def send_import_request(self, job, request):
        if job is self.import_job:
            job.write(request);job.closeWriteChannel()

    def import_progress(self):
        if self.import_job is None:return
        self.import_output += bytes(self.import_job.readAllStandardOutput()).decode('utf-8',errors='replace')
        while '\n' in self.import_output:
            line, self.import_output = self.import_output.split('\n',1)
            try:
                index=json.loads(line)['index']
                self.summary.setText(f'กำลังเพิ่ม {index+1}/{len(self.import_paths)}: '+Path(self.import_paths[index]).name)
                self.import_timeout.start(180000)
            except (ValueError,KeyError,IndexError,TypeError):pass

    def import_error(self,error):
        if error==QProcess.ProcessError.FailedToStart:self.finish_import(1)

    def cancel_import(self):
        if self.import_job is None:return
        pid=int(self.import_job.processId())
        if os.name=='posix' and pid:
            import signal
            try:
                if os.getpgid(pid)==pid:os.killpg(pid,signal.SIGKILL)
                else:self.import_job.kill()
            except ProcessLookupError:pass
        elif os.name=='nt' and pid:
            import subprocess
            try:subprocess.run(['taskkill','/PID',str(pid),'/T','/F'],capture_output=True,timeout=5)
            except (OSError,subprocess.TimeoutExpired):self.import_job.kill()
        else:self.import_job.kill()

    def finish_import(self, exit_code, *_):
        if self.import_job is None:return
        self.import_timeout.stop();self.import_timeout.deleteLater()
        folder=Path(self.import_folder.name)
        errors=[]
        try:
            if self.close_after_import:return
            if exit_code:raise ValueError('การแปลงไฟล์หยุดทำงานหรือใช้เวลานานเกินกำหนด เอกสารเดิมยังอยู่ครบ')
            result=json.loads((folder/'result.json').read_text(encoding='utf-8'))
            errors=result['errors']
            if result['accepted']:
                data=self.document.tobytes() if len(self.document) else None
                candidate=pymupdf.open(stream=data,filetype='pdf') if data else pymupdf.open()
                try:
                    first=len(candidate)
                    with pymupdf.open(folder/'batch.pdf') as batch:candidate.insert_pdf(batch)
                    state=self.snapshot()
                except Exception:
                    candidate.close();raise
                self.document.close();self.document=candidate
                self.sources.update(Path(p) for p in result['accepted'])
                self.remember(state);self.mark_changed();self.refresh(first)
        except Exception as error:errors.append(str(error))
        finally:
            self.import_job.deleteLater();self.import_job=None
            self.import_folder.cleanup();self.import_folder=None
            self.busy=False;self.centralWidget().setEnabled(True);self.update_controls();self.schedule_thumbnails();self.preview()
            if not self.close_after_import:self.summary.setText(self.status_text())
            if errors:QMessageBox.warning(self,'บางไฟล์เพิ่มไม่ได้','\n'.join(errors))
            if self.close_after_import:
                self.close_after_import=False;QTimer.singleShot(0,self.close)

    def preview(self,*_):
        if self.busy:return
        index=self.pages.currentRow()
        if index<0:
            self.viewer.clear();self.caption.setText('เพิ่มไฟล์เพื่อเริ่มจัดหน้า');return
        if not self.grid_button.isChecked():
            try:self.viewer.show_page(self.document[index])
            except Exception as error:
                self.viewer.clear();QMessageBox.warning(self,'แสดงหน้านี้ไม่ได้',str(error))
        self.caption.setText(f'หน้า {index+1} จาก {len(self.document)}')

    def export_bytes(self):
        if not len(self.document):raise ValueError('เพิ่มหน้าเอกสารก่อนบันทึก')
        return self.document.tobytes()

    def export(self):
        if self.busy or not len(self.document):return
        path,_=QFileDialog.getSaveFileName(self,'บันทึก PDF เป็นไฟล์ใหม่','GETEdit_จัดหน้า.pdf','PDF (*.pdf)')
        if not path:return
        if not path.lower().endswith('.pdf'):path+='.pdf'
        try:
            if Path(path).exists() or Path(path).resolve() in self.sources:raise ValueError('กรุณาใช้ชื่อไฟล์ใหม่ เพื่อเก็บต้นฉบับไว้')
            data=self.export_bytes()
            write_new_file(path, data)
            self.saved_revision = self.revision
            self.changed=False
            QMessageBox.information(self,'บันทึกเรียบร้อย',f'บันทึกแล้ว {len(self.document)} หน้า\n{path}')
        except Exception as error:QMessageBox.warning(self,'บันทึกไม่สำเร็จ',str(error))

    def closeEvent(self,event):
        if self.busy:
            event.ignore()
            if QMessageBox.question(self,'กำลังเพิ่มไฟล์','ยกเลิกการเพิ่มไฟล์และปิดโปรแกรมหรือไม่?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                self.close_after_import=True;self.cancel_import()
            return
        if self.changed and QMessageBox.question(self,'ยังไม่ได้บันทึก','ปิดโดยไม่บันทึกการจัดหน้าหรือไม่?',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
            event.ignore();return
        self.thumb_timer.stop()
        event.accept()


if __name__=='__main__':
    app=QApplication(sys.argv);app.setStyle('Fusion')
    window=Window();window.show()
    paths=sys.argv[1:] or os.environ.get('NAUTILUS_SCRIPT_SELECTED_FILE_PATHS','').splitlines()
    if paths:QTimer.singleShot(0,lambda:window.begin_import(paths))
    sys.exit(app.exec())
