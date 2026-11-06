# Project progress

2026-11-06: Initial GETEdit source preview for Linux and Windows.
Includes Thai PDF insertion UI, page preview, save-as protection, launchers,
pinned requirements and unittest coverage. No private PDFs included.

Validation: python3 -m unittest discover -s tests -v passed on Linux.
Previous UI preview checked using Qt offscreen. Windows desktop execution
and native packaging have not been verified. No new dependencies installed.

Next: owner chooses application license; verify on Windows and Linux desktops;
prepare native distribution after approval of any required build dependencies.

2026-11-06: Added Linux Nautilus Scripts installer matching existing FILE-to-file/Allzip/Send-to-device integration. App accepts selected paths via argv or Nautilus environment. Installer uses current Python and project path, checks dependencies, and never installs packages. Existing unit tests pass; isolated installer shell syntax and Thai path UI prefill pass with Qt offscreen (exit 0). Real Nautilus click workflow not yet verified.

2026-11-06: Simplified page selection with clickable main-document thumbnails, two document previews, append button and explicit result page-count summary. Existing insertion tests pass; offscreen UI checks confirm thumbnail selection updates insertion position, both previews populate, append summary updates. Screenshot inspected. No dependencies added; Windows desktop still unverified.

2026-11-06: Replaced main/extra workflow with Add Files, multi-select, immediate merged page thumbnails, selected-page preview and before/after/append placement. Added converter.py for PDF, Qt images and optional installed LibreOffice conversion. No dependency installation. Unit tests and offscreen PDF+PNG/multiple-add/before-position checks passed. Windows and individual Office format coverage remain unverified.
Actual LibreOffice DOCX conversion with generated text fixture passed outside sandbox (exit 0). Earlier sandbox ODT conversion failed; not claiming ODT acceptance.
