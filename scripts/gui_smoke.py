# SPDX-License-Identifier: AGPL-3.0-only
"""Exercise an actual Qt drag on an available desktop using synthetic pages only."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import QApplication, Window, pymupdf
from PySide6.QtCore import QTimer, Qt, QPoint
from PySide6.QtTest import QTest

app=QApplication([]);app.setStyle('Fusion')
folder=tempfile.TemporaryDirectory(prefix='getedit-gui-')
path=Path(folder.name)/'smoke.pdf'
with pymupdf.open() as doc:
    for index in range(12):
        page=doc.new_page();page.insert_text((60,100),f'PAGE {index+1}',fontsize=32)
    doc.save(path)
window=Window();window.add_paths([str(path)]);window.show()
result={'platform':app.platformName(),'drag':False}


def finish():
    result['order']=[page.get_text().strip() for page in window.document]
    result['drag']=result['order'][:4]==['PAGE 2','PAGE 3','PAGE 4','PAGE 1']
    if result['drag']:
        window.undo()
        result['undo']=window.document[0].get_text().strip()=='PAGE 1'
        window.pages.setCurrentRow(1);window.delete_pages()
        result['delete']=len(window.document)==11
        window.undo()
        output=Path(folder.name)/'result.pdf'
        from storage import write_new_file
        write_new_file(output,window.export_bytes())
        with pymupdf.open(output) as saved:result['save']=len(saved)==12
    window.grab().save('/tmp/getedit-production-desktop.png')
    print(json.dumps(result),flush=True)
    window.changed=False;window.close();folder.cleanup()
    app.exit(0 if all(result.get(k) for k in ['drag','undo','delete','save']) else 1)


def drag():
    pages=window.pages
    pages.setCurrentRow(0)
    source=pages.visualItemRect(pages.item(0)).center()
    target_rect=pages.visualItemRect(pages.item(3))
    target=QPoint(target_rect.right()-5,target_rect.center().y())
    QTest.mousePress(pages.viewport(),Qt.MouseButton.LeftButton,pos=source)
    QTimer.singleShot(100,lambda:QTest.mouseMove(pages.viewport(),source+QPoint(25,0)))
    QTimer.singleShot(250,lambda:QTest.mouseMove(pages.viewport(),target))
    QTimer.singleShot(450,lambda:QTest.mouseRelease(pages.viewport(),Qt.MouseButton.LeftButton,pos=target))
    QTimer.singleShot(900,finish)

QTimer.singleShot(700,drag)
QTimer.singleShot(10000,finish)
sys.exit(app.exec())
