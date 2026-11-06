"""Movable overlay objects. Original PDF content stays underneath."""
from copy import deepcopy
import pymupdf
from PySide6.QtCore import Qt, QRectF, Signal, QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QColor, QImage, QPixmap, QPainter, QPen, QFont
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsItem


class Object(QGraphicsItem):
    def __init__(self, data, changed):
        super().__init__()
        self.data = deepcopy(data)
        self.changed = changed
        self.image = QImage.fromData(data.get('image', b''))
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsMovable | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setPos(data['x'], data['y']); self.setRotation(data.get('angle', 0))

    def boundingRect(self):
        return QRectF(0, 0, self.data['w'], self.data['h'])

    def paint(self, painter, option, widget=None):
        rect = self.boundingRect()
        kind = self.data['kind']
        if kind == 'image': painter.drawImage(rect, self.image)
        elif kind == 'box':
            painter.setBrush(QColor('#fff3a6')); painter.setPen(QPen(QColor('#b47e14'), 1.5)); painter.drawRect(rect.adjusted(1,1,-1,-1))
        else:
            painter.setPen(QColor('#172536'))
            font = QFont('Sans Serif'); font.setPixelSize(self.data.get('font', 22)); painter.setFont(font)
            painter.drawText(rect, int(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap), self.data['text'])
        if self.isSelected():
            painter.setBrush(Qt.BrushStyle.NoBrush); painter.setPen(QPen(QColor('#087ac1'), 1, Qt.PenStyle.DashLine)); painter.drawRect(rect)

    def mousePressEvent(self, event):
        self.changed('before'); super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event); self.changed('after')

    def state(self):
        result = deepcopy(self.data)
        result.update(x=self.pos().x(), y=self.pos().y(), angle=self.rotation())
        return result


class Canvas(QGraphicsView):
    edited = Signal()
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setBackgroundBrush(QColor('#dce1e7'))
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setMinimumSize(300, 320)
        self.background = None
        self.page_rect = QRectF()
        self.history = []; self.future = []
        self.pending = None

    def objects(self):
        return [item.state() for item in sorted(self.scene().items(), key=lambda i:i.zValue()) if isinstance(item, Object)]

    def restore(self, states):
        for item in list(self.scene().items()):
            if isinstance(item, Object): self.scene().removeItem(item)
        for number, data in enumerate(states):
            item = Object(data, self.movement); item.setZValue(number+1); self.scene().addItem(item)

    def load(self, page, states):
        self.scene().clear(); self.background = None
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1,1), alpha=False)
        image = QImage(pix.samples,pix.width,pix.height,pix.stride,QImage.Format.Format_RGB888).copy()
        self.background = self.scene().addPixmap(QPixmap.fromImage(image)); self.background.setZValue(-1)
        self.page_rect = QRectF(0,0,pix.width,pix.height); self.scene().setSceneRect(self.page_rect)
        self.restore(states); self.history=[]; self.future=[]
        self.fitInView(self.page_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.page_rect.isEmpty(): self.fitInView(self.page_rect, Qt.AspectRatioMode.KeepAspectRatio)

    def checkpoint(self):
        self.history.append(self.objects()); self.history=self.history[-50:]; self.future=[]

    def movement(self, phase):
        if phase == 'before': self.pending = self.objects()
        elif self.pending != self.objects():
            self.history.append(self.pending); self.future=[]; self.edited.emit()

    def add_object(self, kind, text='', image=b''):
        if self.background is None: return
        self.checkpoint(); self.scene().clearSelection()
        width = min(260, self.page_rect.width()*.65)
        data = dict(kind=kind,x=30,y=30,w=width,h=90,text=text,image=image,font=22,angle=0)
        if kind=='image':
            img=QImage.fromData(image)
            data['h']=width*img.height()/max(1,img.width())
        item=Object(data,self.movement); item.setZValue(len(self.objects())+1); self.scene().addItem(item);item.setSelected(True)
        self.edited.emit()

    def selected(self):
        return [i for i in self.scene().selectedItems() if isinstance(i,Object)]

    def delete_selected(self):
        if not self.selected(): return
        self.checkpoint()
        for item in self.selected(): self.scene().removeItem(item)
        self.edited.emit()

    def scale_selected(self, factor):
        if not self.selected(): return
        self.checkpoint()
        for item in self.selected():
            item.prepareGeometryChange(); item.data['w']*=factor; item.data['h']*=factor
            if item.data['kind']=='text': item.data['font']*=factor
            item.update()
        self.edited.emit()

    def rotate_selected(self):
        if not self.selected(): return
        self.checkpoint()
        for item in self.selected(): item.setRotation(item.rotation()+15)
        self.edited.emit()

    def edit_text(self, text):
        items=self.selected()
        if len(items)!=1 or items[0].data['kind']!='text': return
        self.checkpoint();items[0].data['text']=text;items[0].update();self.edited.emit()

    def undo(self):
        if self.history:
            self.future.append(self.objects());self.restore(self.history.pop());self.edited.emit()

    def redo(self):
        if self.future:
            self.history.append(self.objects());self.restore(self.future.pop());self.edited.emit()

    def overlay_png(self):
        selected=self.selected()
        self.scene().clearSelection(); self.background.hide()
        image=QImage(int(self.page_rect.width()*2),int(self.page_rect.height()*2),QImage.Format.Format_ARGB32_Premultiplied);image.fill(Qt.GlobalColor.transparent)
        painter=QPainter(image);painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene().render(painter,QRectF(0,0,image.width(),image.height()),self.page_rect);painter.end()
        self.background.show()
        for item in selected:item.setSelected(True)
        data=QByteArray();buffer=QBuffer(data);buffer.open(QIODevice.OpenModeFlag.WriteOnly);image.save(buffer,'PNG');return bytes(data)
