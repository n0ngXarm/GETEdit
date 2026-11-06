# Changes

## 1.0.2

- Fix first-open failure from Nautilus: preserve caller directory and resolve absolute selections/file URIs before import.
- Launchers preserve the original working directory for relative filenames.
- Allow all filename extensions in picker, detect PDF/images by content and expand text/HTML/SVG/e-book/Office inputs using existing readers.
- Unsupported binary files report an error; no attachments or content-editing features were added.

## 1.0.1

- Shorter Thai command labels with guidance matched to grid/reading mode.
- Removed duplicate heading and reduced toolbar/status padding.
- Reading sidebar stays narrow on wide screens; thumbnail rows follow page aspect ratio.
- Landscape page grids use shorter tiles instead of portrait-sized empty space.

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
