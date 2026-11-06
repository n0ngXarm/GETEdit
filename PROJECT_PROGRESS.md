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

2026-11-06: User approved lightweight PowerPoint-like additions over original pages. Added editor.py QGraphics canvas with movable text/image/box overlays, size buttons, rotation, selected-object delete/text edit, page-local undo/redo and page persistence. Export flattens only overlays to transparent PNG while preserving original PDF content. No project-file persistence; reopening exported PDF cannot select added objects separately. Undo resets on page switch. No dependencies added. python3 -m unittest discover -s tests -v: 3 tests passed exit 0; covers overlay persistence, move/size/delete/undo, insertion shifts, rotated-page export and source integrity. Offscreen UI screenshot and exported Thai-text render inspected. Windows desktop interaction remains unverified.

2026-11-06 — Scope correction from user (supersedes overlay scope above): user wants only adding/removing PDF pages, with Office-like interaction. Removed editor.py and obsolete overlay tests; no text/image/shape object editor remains. Retained previously requested supported-file import as pages. Added ribbon-style commands, thumbnail multi-selection, selected-page removal, page-level undo for add/delete, zoom and fit-page view, source-preserving save-as. Updated README.
Validation: new page-management tests first failed with missing delete_pages/undo (exit 1), then passed after implementation. Full python3 -m unittest discover -s tests -v: 5 tests passed exit 0. QTest Delete/Ctrl+Z shortcut checks passed. Offscreen full-window screenshot inspected. No dependencies installed. Desktop click workflow for this revision and Windows execution remain unverified.

2026-11-06: User requested append-only file selection followed by hold-and-drag page reordering. Removed placement combo. Added PageList internal drag/drop for one or multiple selected thumbnails; custom QDrag avoids base-list post-drop deletion. Reordering updates the actual PDF, preview and page numbers together, supports undo, and skips no-op moves. README updated. No dependencies installed.
Validation: new reorder tests initially failed (3 missing-method errors, exit 1), then full unittest suite passed (9 tests, exit 0), including multi-page move, synthetic internal QDropEvent, export order, delete/undo after move, no-op undo history and original file integrity. Offscreen UI screenshot inspected. Actual desktop mouse drag and Windows remain unverified.
