# SPDX-License-Identifier: AGPL-3.0-only
"""Isolated import process; MuPDF never runs in a GUI thread concurrently."""
import json
import os
import sys
from pathlib import Path
import pymupdf
from converter import convert_file


def run(paths, directory):
    folder=Path(directory)
    errors=[]; accepted=[]
    with pymupdf.open() as batch:
        for index,path in enumerate(paths):
            print(json.dumps({'index':index}),flush=True)
            try:
                data=convert_file(path)
                with pymupdf.open(stream=data,filetype='pdf') as doc:
                    if doc.needs_pass or not len(doc): raise ValueError('เอกสารไม่มีหน้าหรือมีรหัสผ่าน')
                    batch.insert_pdf(doc)
                accepted.append(str(Path(path).resolve()))
            except Exception as error:
                errors.append(Path(path).name+': '+str(error))
        if accepted: batch.save(folder/'batch.pdf')
    (folder/'result.json').write_text(json.dumps({'accepted':accepted,'errors':errors},ensure_ascii=False),encoding='utf-8')


if __name__=='__main__':
    if os.name=='posix':os.setsid()
    request=json.loads(sys.stdin.buffer.read().decode('utf-8'))
    run(request['paths'],request['directory'])
