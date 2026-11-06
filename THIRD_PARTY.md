# Third-party dependencies

GETEdit is licensed AGPL-3.0-only. These source packages contain the complete
application source and do not bundle dependency binaries or personal documents.
Runtime dependencies are downloaded separately by pip, with their own licenses.

- PyMuPDF 1.28.2 / MuPDF: GNU AGPL v3 or Artifex commercial license.
  GETEdit uses the AGPL option.
  https://pymupdf.io/licensing
  https://github.com/pymupdf/PyMuPDF
- PySide6 6.11.2 / Qt for Python: LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only
  according to installed package metadata. Qt modules and bundled components may
  carry additional notices supplied by the upstream package.
  https://doc.qt.io/qtforpython-6/
  https://code.qt.io/cgit/pyside/pyside-setup.git/
- LibreOffice: optional external conversion tool, not bundled or installed by
  GETEdit. https://www.libreoffice.org/about-us/licenses/

Distributors who bundle runtime libraries into binaries must include their
licenses/notices and meet corresponding source and relinking requirements.
This release is source-based and includes no frozen EXE or AppImage.
