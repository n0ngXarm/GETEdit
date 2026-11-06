# SPDX-License-Identifier: AGPL-3.0-only
"""Build explicit source-only release archives, excluding personal documents."""
import hashlib
import re
import zipfile
from pathlib import Path

root=Path(__file__).resolve().parents[1]
version=re.search(r'__version__ = "([^"]+)"',(root/'app.py').read_text()).group(1)
output=root/'dist';output.mkdir(exist_ok=True)
common=['app.py','converter.py','storage.py','import_worker.py','requirements.txt',
        'README.md','LICENSE','NOTICE','THIRD_PARTY.md','CHANGELOG.md','VALIDATION.md']
common += [str(path.relative_to(root)) for path in sorted((root/'tests').glob('*.py'))]
common += [str(path.relative_to(root)) for path in sorted((root/'scripts').glob('*.py'))]
checksums=[]
for platform,launchers in [('Linux',['Start-Linux.sh','install-linux.sh','install-linux.py']),('Windows',['Start-Windows.bat'])]:
    archive=output/f'GETEdit-{version}-{platform}-source.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as bundle:
        for name in common+launchers:
            path=root/name
            if not path.is_file() or path.is_symlink():raise RuntimeError(f'Invalid release input: {name}')
            bundle.write(path,'GETEdit-'+version+'/'+name)
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert not any(name.endswith(('.pdf','.png')) for name in bundle.namelist())
    checksums.append(hashlib.sha256(archive.read_bytes()).hexdigest()+'  '+archive.name)
    print(archive)
(output/'SHA256SUMS.txt').write_text('\n'.join(checksums)+'\n')
