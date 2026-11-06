# Validation for GETEdit 1.0.0

## Confirmed locally

- Fedora Linux, Python 3.14, PyMuPDF 1.28.2, PySide6 6.11.2.
- Regression suite: 24 tests passed (exit 0), including source integrity,
  drag reorder/export, multi-selection, deletion/undo, corrupt input, failed
  worker start, worker termination, atomic save failures/races, save/undo dirty
  state, bounded page rasterization and lazy 300-page thumbnail loading.
- Native Wayland Qt window: simulated pointer drag, undo, delete, undo, save and
  reopen all passed (exit 0). Synthetic pages only; not a human acceptance test.
- Actual LibreOffice DOCX conversion passed with a generated text fixture.
  All other Office format/layout combinations have not been verified.

## CI

The `Verify GETEdit` workflow runs the same regression suite on Linux and
Windows. Inspect the matching commit's Actions run for its actual result.
Windows desktop pointer interaction is not claimed by offscreen CI tests.

## Distribution limits

Source packages require Python and separately installed runtime dependencies.
No frozen EXE/AppImage or signed installer is included. PDF passwords and
preservation of existing digital signatures are outside supported editing.
AGPL-3.0-only application source is included; dependency binaries are not bundled.

Deterministic stress check: 300 initial pages, 90 mixed reorder/delete/undo operations; 273 final pages matched the reference model after export/reopen. Original file bytes unchanged. Local run passed in 8.736 seconds.

CI first found a synchronous QProcess FailedToStart cleanup race on Windows;
fixed by sending the request only from QProcess.started. Regression added.
Ubuntu runner required libegl1; owner approved installing it only in ephemeral CI.

## Release verification

Release v1.0.0 targets code commit 2a380dab0014bc583992bc4c43932ab059d4f8ef.
GitHub Actions run 42163115484 completed successfully: Linux and Windows each
passed all 24 regression tests and the 300-page/90-operation stress check.
https://github.com/n0ngXarm/GETEdit/actions/runs/42163115484

Linux source ZIP was extracted into a temporary directory and its included
regression suite executed successfully. Both ZIP manifests were checked for
required modules/license and exclusion of personal PDF/image files.
