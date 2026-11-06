---
name: getedit-maintenance
description: Maintain, test and package GETEdit; use for this repository's runtime, installer and release changes.
---

# GETEdit

Read root AGENTS.md and PROJECT_PROGRESS.md first. This skill applies only to this repository.

Page management only: keep page grid, copy/paste, undo/redo and source-preserving export. Read app.py, import_worker.py, converter.py, storage.py and relevant tests before edits. Frozen imports must use the separate console worker; windowed Python has no stdin/stdout. Never modify original documents. Preserve Qt-native clipboard MIME ownership and subprocess-exit tests.

Run `python -m unittest discover -s tests -v`. For installer changes, run the Windows installer workflow and inspect `scripts/verify_windows_install.py` results against the exact commit. Native setup should remain per-user and require no Python on the target machine. Preserve application licenses and corresponding source. Do not install dependencies, publish a release or change scope without authorization in the current task.

Record changed behavior, actual checks and remaining limitations in PROJECT_PROGRESS.md. Do not substitute Linux/source tests for installed Windows runtime acceptance.
