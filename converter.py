# SPDX-License-Identifier: AGPL-3.0-only
"""Convert supported local documents into PDF bytes without changing originals."""
import shutil
import subprocess
import tempfile
from pathlib import Path
import pymupdf

IMAGES = {'.png', '.jpg', '.jpeg', '.bmp', '.tif', '.tiff', '.webp'}
OFFICE = {'.doc', '.docx', '.odt', '.rtf', '.xls', '.xlsx', '.ods', '.ppt', '.pptx', '.odp'}


def convert_file(path):
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == '.pdf':
        with pymupdf.open(path) as doc:
            if doc.needs_pass:
                raise ValueError('ไฟล์ PDF มีรหัสผ่าน กรุณาปลดล็อกก่อน')
            if not len(doc): raise ValueError('เอกสารไม่มีหน้า')
        return path.read_bytes()
    if suffix in IMAGES:
        # Qt's decoder supports multi-frame TIFF and normalizes images for MuPDF.
        from PySide6.QtGui import QImageReader
        from PySide6.QtCore import QBuffer, QByteArray, QIODevice
        QImageReader.setAllocationLimit(128)
        reader = QImageReader(str(path)); reader.setAutoTransform(True)
        with pymupdf.open() as result:
            frames = max(1, reader.imageCount())
            for index in range(frames):
                if index and not reader.jumpToImage(index):
                    raise ValueError('อ่านหน้าภาพไม่สำเร็จ')
                image = reader.read()
                if image.isNull(): raise ValueError(reader.errorString())
                data = QByteArray(); buffer = QBuffer(data)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                if not image.save(buffer, 'PNG'): raise ValueError('แปลงภาพไม่สำเร็จ')
                width, height = image.width(), image.height()
                scale = min(540 / width, 770 / height)
                page = result.new_page(width=595, height=842)
                w, h = width * scale, height * scale
                page.insert_image(pymupdf.Rect((595-w)/2, (842-h)/2, (595+w)/2, (842+h)/2), stream=bytes(data))
            return result.tobytes()
    if suffix in OFFICE:
        executable = shutil.which('libreoffice') or shutil.which('soffice')
        if not executable:
            import os
            for variable in ('PROGRAMFILES', 'PROGRAMFILES(X86)'):
                candidate = Path(os.environ.get(variable, ''))/'LibreOffice/program/soffice.exe'
                if candidate.is_file(): executable = str(candidate); break
        if not executable:
            raise ValueError('ไฟล์ Office ต้องมี LibreOffice ในเครื่องก่อน หรือส่งออกเป็น PDF แล้วเพิ่มอีกครั้ง')
        with tempfile.TemporaryDirectory(prefix='getedit-') as tmp:
            root = Path(tmp); inputs = root/'input'; inputs.mkdir()
            copy = inputs/('document'+suffix); shutil.copy2(path, copy)
            try:
                process = subprocess.run([executable, '-env:UserInstallation='+(root/'profile').as_uri(),
                    '--headless', '--convert-to', 'pdf', '--outdir', str(root), str(copy)],
                    capture_output=True, timeout=90)
            except subprocess.TimeoutExpired as error:
                raise ValueError('LibreOffice แปลงไฟล์เกิน 90 วินาที กรุณาส่งออกเป็น PDF ก่อน') from error
            output = root/'document.pdf'
            if process.returncode or not output.is_file():
                raise ValueError('แปลงเอกสารด้วย LibreOffice ไม่สำเร็จ ลองส่งออกเป็น PDF ก่อน')
            return output.read_bytes()
    raise ValueError('ยังไม่รองรับชนิดไฟล์นี้ รองรับ PDF, รูปภาพ และเอกสาร Office เมื่อมี LibreOffice')
