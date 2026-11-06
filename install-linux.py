# SPDX-License-Identifier: AGPL-3.0-only
"""Install only the Nautilus launcher; never install dependencies."""
import os
import shlex
import sys
from pathlib import Path


def install(data_dir=None):
    project = Path(__file__).resolve().parent
    # Check before creating a menu entry that cannot run.
    import PySide6
    import pymupdf
    data = Path(data_dir) if data_dir else Path(os.environ.get('XDG_DATA_HOME', Path.home()/'.local/share'))
    destination = data/'nautilus/scripts/GETEdit'
    launcher = ('#!/bin/sh\n# GETEdit Nautilus launcher\n'
                f'cd {shlex.quote(str(project))} || exit 1\n'
                f'exec {shlex.quote(sys.executable)} {shlex.quote(str(project/"app.py"))} "$@"\n')
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not destination.read_text().startswith('#!/bin/sh\n# GETEdit Nautilus launcher\n'):
        raise RuntimeError(f'ไม่เขียนทับสคริปต์ที่มีอยู่: {destination}')
    destination.write_text(launcher)
    destination.chmod(0o755)
    print(f'ติดตั้งแล้ว: {destination}')
    print('เลือก PDF แล้วคลิกขวา → Scripts → GETEdit')
    return destination

if __name__ == '__main__':
    install()
