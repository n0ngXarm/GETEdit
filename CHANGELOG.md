# Changes

## 1.0.0

- Page-grid workflow: add files, drag one or several pages, remove pages and undo.
- Internal pointer drag works independently of the desktop's native drag protocol;
  insertion marker, edge scrolling and Escape cancellation are included.
- Import conversion runs in an isolated process; failed imports preserve the
  current document. Closing an active import asks before stopping its process tree.
- Lazy thumbnails and bounded preview resolution reduce memory use on large PDFs.
- Completed-file publication prevents partial output and overwriting existing files.
- Unsaved-change tracking stays correct after save and undo.
- Source distribution and launchers for Linux/Windows, AGPL-3.0-only license,
  regression checks and CI on both systems.
