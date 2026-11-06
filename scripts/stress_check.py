# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic page integrity check with synthetic documents only."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import random
import sys
import tempfile
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import QApplication, Window, pymupdf

started=time.monotonic();app=QApplication([]);rng=random.Random(20261106)
with tempfile.TemporaryDirectory() as folder:
    path=Path(folder)/'300-pages.pdf'
    with pymupdf.open() as doc:
        for i in range(300):
            page=doc.new_page();page.insert_text((60,60),f'PAGE {i+1}')
        doc.save(path)
    original=path.read_bytes();window=Window();window.add_paths([str(path)])
    expected=[f'PAGE {i+1}' for i in range(300)];history=[]
    for operation in range(90):
        action=rng.choice(['move','delete','undo'])
        if action=='undo' and history:
            window.undo();expected=history.pop()
        elif action=='move' and len(expected)>1:
            order=list(range(len(expected)));rng.shuffle(order)
            history.append(expected.copy());history=history[-10:]
            window.reorder_pages(order);expected=[expected[i] for i in order]
        elif action=='delete' and len(expected)>10:
            indices=rng.sample(range(len(expected)),3)
            history.append(expected.copy());history=history[-10:]
            window.pages.clearSelection()
            for index in indices:window.pages.item(index).setSelected(True)
            window.delete_pages();expected=[text for i,text in enumerate(expected) if i not in indices]
        assert [page.get_text().strip() for page in window.document]==expected,operation
    with pymupdf.open(stream=window.export_bytes(),filetype='pdf') as result:
        assert [page.get_text().strip() for page in result]==expected
    assert path.read_bytes()==original
    window.changed=False;window.close()
    print(json.dumps({'initial_pages':300,'operations':90,'final_pages':len(expected),'integrity':'PASS','elapsed_seconds':round(time.monotonic()-started,3)}))
