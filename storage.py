# SPDX-License-Identifier: AGPL-3.0-only
"""Publish a complete new file without overwriting existing destinations."""
import io
import os
import shutil
import tempfile
from pathlib import Path


def write_new_file(path, data):
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError('ชื่อไฟล์นี้มีอยู่แล้ว กรุณาใช้ชื่อใหม่')
    descriptor, temporary = tempfile.mkstemp(prefix='.getedit-', suffix='.tmp', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            shutil.copyfileobj(io.BytesIO(data), stream)
            stream.flush()
            os.fsync(stream.fileno())
        # Same-directory hard link is atomic and fails if another process has
        # created the destination. Unlike replace(), it never clobbers a file.
        os.link(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
