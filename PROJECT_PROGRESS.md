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
